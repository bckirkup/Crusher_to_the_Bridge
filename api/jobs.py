"""In-memory job lifecycle for the Crusher simulation REST service.

Jobs run :class:`~picard_framework.ShipSimulation` instances on a bounded
thread pool so the HTTP service stays responsive while voyages execute.
Job state lives in process memory; restart loses it (documented v1 limit).
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from picard_framework import PicardRunSpec, ShipSimulation
from simulation_utils.paths import validate_json_document

PICARD_SPEC_SCHEMA = "picard_run_spec.schema.json"
API_JOBS_DIR = os.path.join("telemetry_buffer", "api_jobs")

JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
TERMINAL_STATUSES: frozenset[str] = frozenset({"succeeded", "failed", "cancelled"})
_ACTIVE_STATUSES: frozenset[str] = frozenset({"queued", "running"})

_TELEMETRY_KEYS = ("simulation_history", "ground_truth", "lab_notebook")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStateError(RuntimeError):
    """Raised when a lifecycle request conflicts with the job's state."""


@dataclass
class JobRecord:
    """Server-side view of one submitted simulation run."""

    job_id: str
    spec: dict[str, Any]
    status: JobStatus = "queued"
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    num_epochs: int = 0
    epochs_completed: int = 0
    cancel_requested: bool = False
    error: str = ""
    result: dict[str, Any] | None = None
    telemetry: dict[str, str] = field(default_factory=dict)

    def to_status_dict(self) -> dict[str, Any]:
        """Status envelope without the result payload."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at or None,
            "finished_at": self.finished_at or None,
            "num_epochs": self.num_epochs,
            "epochs_completed": self.epochs_completed,
            "cancel_requested": self.cancel_requested,
            "error": self.error or None,
            "telemetry": dict(self.telemetry),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        """Status envelope plus the full run result once available."""
        detail = self.to_status_dict()
        detail["result"] = self.result
        return detail


def _job_telemetry_paths(job_id: str) -> dict[str, str]:
    """Per-job repo-relative telemetry output paths (telemetry writers refuse /tmp)."""
    base = os.path.join(API_JOBS_DIR, job_id)
    return {key: os.path.join(base, f"{key}.json") for key in _TELEMETRY_KEYS}


def _assign_job_telemetry(spec: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Return a spec copy with per-job telemetry paths where the caller left them unset."""
    merged = dict(spec)
    run = dict(merged.get("run") or {})
    defaults = _job_telemetry_paths(job_id)
    for key, default in defaults.items():
        if not run.get(key):
            run[key] = default
    merged["run"] = run
    return merged


class JobManager:
    """Submit, track, and cancel ``ShipSimulation`` runs on a worker pool."""

    def __init__(self, repo_root: str, *, max_workers: int = 2) -> None:
        self._repo_root = repo_root
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="crusher-api",
        )
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def submit(self, spec: dict[str, Any]) -> JobRecord:
        """Validate *spec*, enqueue a job, and return its record.

        Raises :class:`ValueError` for schema violations and unrunnable specs.
        """
        validate_json_document(spec, PICARD_SPEC_SCHEMA, source="POST /v1/runs")
        PicardRunSpec.from_picard_dict(self._repo_root, spec)

        job_id = uuid.uuid4().hex[:12]
        merged_spec = _assign_job_telemetry(spec, job_id)
        run_block = merged_spec.get("run") or {}
        record = JobRecord(
            job_id=job_id,
            spec=merged_spec,
            created_at=_utc_now(),
            num_epochs=int(run_block.get("num_epochs", 24)),
            telemetry={
                key: run_block[key] for key in _TELEMETRY_KEYS if run_block.get(key)
            },
        )
        with self._lock:
            self._jobs[job_id] = record
        self._pool.submit(self._execute, record)
        return record

    def get(self, job_id: str) -> JobRecord:
        record = self._jobs.get(job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    def list(self) -> list[JobRecord]:
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel(self, job_id: str) -> JobRecord:
        """Request cancellation; queued jobs cancel immediately."""
        record = self.get(job_id)
        with self._lock:
            if record.status in TERMINAL_STATUSES:
                raise JobStateError(f"job {job_id} already {record.status}")
            record.cancel_requested = True
            if record.status == "queued":
                self._mark_finished(record, "cancelled")
        return record

    def remove(self, job_id: str) -> JobRecord:
        """Drop a terminal job's record."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise KeyError(job_id)
            if record.status in _ACTIVE_STATUSES:
                raise JobStateError(
                    f"job {job_id} is {record.status}; cancel it before deleting",
                )
            del self._jobs[job_id]
        return record

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _mark_finished(self, record: JobRecord, status: JobStatus) -> None:
        record.status = status
        record.finished_at = _utc_now()

    def _execute(self, record: JobRecord) -> None:
        if record.cancel_requested:
            with self._lock:
                self._mark_finished(record, "cancelled")
            return
        with self._lock:
            record.status = "running"
            record.started_at = _utc_now()
        try:
            self._drive_simulation(record)
        except Exception as exc:  # noqa: BLE001 — job boundary: report, don't crash the pool
            with self._lock:
                record.error = f"{type(exc).__name__}: {exc}"
                self._mark_finished(record, "failed")

    def _drive_simulation(self, record: JobRecord) -> None:
        spec = PicardRunSpec.from_picard_dict(self._repo_root, record.spec)
        sim = ShipSimulation(spec, display=False)
        sim.initialize()
        while sim.epoch + 1 < spec.num_epochs:
            if record.cancel_requested:
                with self._lock:
                    self._mark_finished(record, "cancelled")
                return
            sim.step()
            record.epochs_completed = sim.epoch + 1
        sim.finalize(display=False)
        state = sim.state
        with self._lock:
            record.result = {
                "num_epochs": spec.num_epochs,
                "final_trigger_status": state.trigger_status if state else "",
                "history": list(state.simulation_history) if state else [],
            }
            self._mark_finished(record, "succeeded")
