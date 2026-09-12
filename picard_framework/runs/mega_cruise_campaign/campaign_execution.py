#!/usr/bin/env python3
"""Campaign execution: resume/S3/sharding/CLI and Picard run loop.

Spec generation (including ``sr*`` / ``vd*`` families) stays in
``campaign_runner.py``. ``campaign_runner.main`` delegates here.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.initiation import LEGACY_MANIFEST  # noqa: E402

# Late-bound access to generation + shared mutable campaign state.
from picard_framework.runs.mega_cruise_campaign import campaign_runner as _cr  # noqa: E402
from simulation_utils.epidemic_labels import epidemic_took_off  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    confine_to_base,
    prepare_output_directory,
    resolve_child_path,
    validate_path_component,
    validated_open,
)


def parse_s3_prefix(s3_prefix: str) -> tuple[str, str]:
    """Split ``s3://bucket/path`` into ``(bucket, key_prefix)``."""
    parsed = urlparse(s3_prefix)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise SystemExit(
            f"--s3-prefix must look like s3://bucket/path, got {s3_prefix!r}",
        )
    return parsed.netloc, parsed.path.lstrip("/")


class S3Uploader:
    """Thin boto3 wrapper. Imported lazily so non-S3 runs need no boto3."""

    def __init__(self, s3_prefix: str) -> None:
        self.bucket, self.key_prefix = parse_s3_prefix(s3_prefix)
        try:
            import boto3  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - depends on env
            raise SystemExit(
                "boto3 is required for --s3-prefix uploads "
                "(pip install boto3).",
            ) from exc
        self._client = boto3.client("s3")

    def _key(self, name: str) -> str:
        return f"{self.key_prefix.rstrip('/')}/{name}" if self.key_prefix else name

    def upload_file(self, local_path: Path, name: str) -> str:
        key = self._key(name)
        self._client.upload_file(str(local_path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download_file(self, name: str, local_path: Path) -> bool:
        """Download ``name`` under the prefix to ``local_path``.

        Returns True on success, False if the object is missing. Other S3
        errors propagate so credential/network failures are visible.
        """
        key = self._key(name)
        try:
            from botocore.exceptions import ClientError as client_error  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            client_error = Exception  # type: ignore[misc, assignment]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self.bucket, key, str(local_path))
            return True
        except client_error as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        except Exception as exc:  # noqa: BLE001
            # boto3 may raise different missing-key flavors depending on version.
            msg = str(exc).lower()
            if "nosuchkey" in msg or "not found" in msg or "404" in msg:
                return False
            raise

    def object_exists(self, name: str) -> bool:
        """Return True if ``name`` exists under the S3 prefix."""
        key = self._key(name)
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


def _shard_suffix(shard_index: int, shard_count: int | None) -> str:
    return f"shard-{shard_index}" if shard_count is not None else "single"


def _resolve_relative_path(parent: str, relative: str) -> str:
    """Resolve a relative archive path one validated component at a time."""
    current = parent
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute():
        raise ValueError(f"Invalid relative archive path: {relative!r}")
    for part in parts:
        current = resolve_child_path(
            current,
            validate_path_component(part, label="archive path component"),
        )
    return current


class ShardBundle:
    """Accumulate completed run directories and publish one shard bundle."""

    def __init__(self, shard_index: int, shard_count: int | None) -> None:
        self.suffix = _shard_suffix(shard_index, shard_count)
        root = _cr._ensure_output_root()
        accumulation_base = confine_to_base(
            root, os.path.join(root, "_shard_runs"),
        )
        prepare_output_directory(
            accumulation_base,
            allowed_roots=_cr._allowed_roots(root),
        )
        self.accumulation_root = resolve_child_path(
            accumulation_base, self.suffix,
        )
        prepare_output_directory(
            self.accumulation_root,
            allowed_roots=_cr._allowed_roots(root),
        )
        self.zip_path = resolve_child_path(root, f"{self.suffix}.zip")
        self.manifest_path = resolve_child_path(
            root, f"{self.suffix}.manifest.json",
        )
        self.entries: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def _write_manifest(self) -> None:
        with validated_open(
            self.manifest_path,
            "w",
            allowed_roots=_cr._allowed_roots(),
            encoding="utf-8",
        ) as fh:
            json.dump(list(self.entries.values()), fh, indent=2)
            fh.write("\n")

    def _merge_manifest(self, entries: object) -> None:
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            run_id = entry.get("run_id")
            if not isinstance(run_id, str):
                continue
            try:
                safe_id = _cr._safe_run_id(run_id)
            except ValueError:
                continue
            parameters = entry.get("parameters") or {}
            derived = entry.get("derived") or {}
            self.entries[safe_id] = {
                "run_id": safe_id,
                "parameters": parameters if isinstance(parameters, dict) else {},
                "derived": derived if isinstance(derived, dict) else {},
            }

    def load_local_manifest(self) -> None:
        if not os.path.isfile(self.manifest_path):
            return
        try:
            with validated_open(
                self.manifest_path,
                allowed_roots=_cr._allowed_roots(),
                encoding="utf-8",
            ) as fh:
                self._merge_manifest(json.load(fh))
        except (OSError, TypeError, ValueError):
            print("  (local shard manifest is unreadable; starting with no entries)")

    def record_run(self, run_id: str) -> None:
        safe_id = _cr._safe_run_id(run_id)
        summary_path = resolve_child_path(
            resolve_child_path(self.accumulation_root, safe_id),
            "summary.json",
        )
        parameters: dict[str, Any] = {}
        derived: dict[str, Any] = {}
        try:
            with validated_open(
                summary_path,
                allowed_roots=_cr._allowed_roots(),
                encoding="utf-8",
            ) as fh:
                summary = json.load(fh)
            parameters = summary.get("parameters") or {}
            derived = summary.get("derived") or {}
            if not isinstance(parameters, dict):
                parameters = {}
            if not isinstance(derived, dict):
                derived = {}
        except (OSError, TypeError, ValueError):
            # Missing summaries are valid for lightweight test runners.
            pass
        self.entries[safe_id] = {
            "run_id": safe_id,
            "parameters": parameters,
            "derived": derived,
        }
        self._write_manifest()

    def _archive_members(self) -> Iterator[tuple[str, str]]:
        if not os.path.isdir(self.accumulation_root):
            return
        for run_id in sorted(os.listdir(self.accumulation_root)):
            run_root = os.path.join(self.accumulation_root, run_id)
            if not os.path.isdir(run_root):
                continue
            try:
                safe_id = _cr._safe_run_id(run_id)
            except ValueError:
                continue
            run_root = resolve_child_path(self.accumulation_root, safe_id)
            for dirpath, _dirnames, filenames in os.walk(run_root):
                for filename in sorted(filenames):
                    relative = os.path.relpath(
                        os.path.join(dirpath, filename), run_root,
                    )
                    file_path = _resolve_relative_path(run_root, relative)
                    yield file_path, f"{safe_id}/{relative}"

    def _pack_full(self, members: list[tuple[str, str]]) -> None:
        temp_path = resolve_child_path(
            _cr._ensure_output_root(), f"{self.suffix}.zip.tmp",
        )
        try:
            with zipfile.ZipFile(
                temp_path, "w", zipfile.ZIP_DEFLATED,
            ) as zf:
                for file_path, archive_name in members:
                    zf.write(file_path, archive_name)
            os.replace(temp_path, self.zip_path)
        except Exception:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
            raise

    def _existing_run_ids(
        self,
        members: list[tuple[str, str]],
    ) -> set[str] | None:
        expected_by_run: dict[str, set[str]] = {}
        for _file_path, archive_name in members:
            run_id, _separator, _relative = archive_name.partition("/")
            expected_by_run.setdefault(run_id, set()).add(archive_name)
        try:
            with zipfile.ZipFile(self.zip_path) as zf:
                names = zf.namelist()
        except (zipfile.BadZipFile, OSError):
            return None
        if len(names) != len(set(names)):
            return None
        expected_names = {archive_name for _path, archive_name in members}
        existing_by_run: dict[str, set[str]] = {}
        for name in names:
            run_id, separator, _relative = name.partition("/")
            if not separator:
                return None
            try:
                safe_id = _cr._safe_run_id(run_id)
            except ValueError:
                return None
            if safe_id != run_id or name not in expected_names:
                return None
            existing_by_run.setdefault(run_id, set()).add(name)
        for run_id, existing_names in existing_by_run.items():
            if existing_names != expected_by_run.get(run_id, set()):
                return None
        return set(existing_by_run)

    def _pack(self) -> None:
        members = list(self._archive_members())
        existing_run_ids = self._existing_run_ids(members)
        if existing_run_ids is None:
            self._pack_full(members)
            return
        by_run: dict[str, list[tuple[str, str]]] = {}
        for member in members:
            run_id = member[1].partition("/")[0]
            by_run.setdefault(run_id, []).append(member)
        new_run_ids = sorted(set(by_run) - existing_run_ids)
        if not new_run_ids:
            return
        try:
            with zipfile.ZipFile(self.zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
                for run_id in new_run_ids:
                    for file_path, archive_name in by_run[run_id]:
                        zf.write(file_path, archive_name)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            self._pack_full(members)

    def flush(self, uploader: Any) -> None:
        self._pack()
        if uploader is None:
            return
        uploaded = True
        for path, name in (
            (self.zip_path, f"{self.suffix}.zip"),
            (self.manifest_path, f"{self.suffix}.manifest.json"),
        ):
            try:
                uploader.upload_file(Path(path), name)
            except Exception as exc:  # noqa: BLE001
                uploaded = False
                print(f"  (s3 upload failed for {name}: {exc})")
        if uploaded:
            print(
                f"  fused {self.suffix}.zip + manifest "
                f"({len(self.entries)} runs) -> s3",
            )

    def _unpack(self, zip_path: str) -> None:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for member in zf.infolist():
                    target = _resolve_relative_path(
                        self.accumulation_root, member.filename,
                    )
                    if member.is_dir():
                        prepare_output_directory(
                            target, allowed_roots=_cr._allowed_roots(),
                        )
                        continue
                    parent = os.path.dirname(target)
                    prepare_output_directory(
                        parent, allowed_roots=_cr._allowed_roots(),
                    )
                    with validated_open(
                        target,
                        "wb",
                        allowed_roots=_cr._allowed_roots(),
                    ) as destination:
                        destination.write(zf.read(member))
        except zipfile.BadZipFile:
            print(f"  (s3 shard zip is invalid: {zip_path})")

    def download(self, uploader: Any) -> None:
        root = _cr._ensure_output_root()
        zip_download = resolve_child_path(root, f"{self.suffix}.zip")
        manifest_download = resolve_child_path(
            root, f"{self.suffix}.manifest.json",
        )
        try:
            zip_present = uploader.download_file(
                f"{self.suffix}.zip", Path(zip_download),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (s3 shard zip download failed: {exc})")
            zip_present = False
        if zip_present:
            self._unpack(zip_download)
        try:
            manifest_present = uploader.download_file(
                f"{self.suffix}.manifest.json", Path(manifest_download),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (s3 shard manifest download failed: {exc})")
            manifest_present = False
        if not manifest_present:
            return
        try:
            with validated_open(
                manifest_download,
                allowed_roots=_cr._allowed_roots(),
                encoding="utf-8",
            ) as fh:
                self._merge_manifest(json.load(fh))
        except (OSError, TypeError, ValueError):
            print("  (s3 shard manifest is unreadable; starting with no entries)")

    def completed_run_ids(self) -> set[str]:
        return set(self.entries)


def extract_timeseries(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract a compact per-epoch epidemic/contamination series from history.

    Keeps only the scalar fields needed for epidemic curves, detection lag,
    contamination spread and cost-effectiveness analysis — not the full
    per-agent / per-zone records — so it stays ~50 KB per run.

    ``new_infections`` is the per-epoch incidence estimator
    ``max(0, (I+R)_t − (I+R)_{t−1})``.
    """
    series: list[dict[str, Any]] = []
    prev_ever_infected = 0
    for epoch_idx, rec in enumerate(history):
        s = rec.get("summary", {})
        cost = rec.get("cost_accounting", {})
        spaces = rec.get("spaces", {})
        reported_case_counter = rec.get(
            "infection_counters", {},
        ).get("passenger_reported_case_rate", {})

        infected = int(s.get("infected", 0) or 0)
        recovered = int(s.get("recovered", 0) or 0)
        ever_infected = infected + recovered
        new_infections = max(0, ever_infected - prev_ever_infected)
        prev_ever_infected = ever_infected

        n_contaminated = 0
        max_conc = 0.0
        max_conc_zone = ""
        total_mass = 0.0
        for zname, zdata in spaces.items():
            conc = zdata.get("concentration_per_m3", 0.0)
            mass = zdata.get("pathogen_mass", 0.0)
            if isinstance(mass, dict):
                mass = sum(mass.values())
            total_mass += mass
            if conc > 1.0:
                n_contaminated += 1
            if conc > max_conc:
                max_conc = conc
                max_conc_zone = zname

        series.append({
            "epoch": epoch_idx,
            "susceptible": s.get("susceptible", 0),
            "infected": s.get("infected", 0),
            "symptomatic": s.get("symptomatic", 0),
            "recovered": s.get("recovered", 0),
            "immune": s.get("immune", 0),
            "quarantined": s.get("quarantined", 0),
            "isolated": s.get("isolated", 0),
            "new_infections": new_infections,
            "total_pathogen_mass": round(total_mass, 2),
            "n_zones_contaminated": n_contaminated,
            "max_concentration": round(max_conc, 4),
            "max_conc_zone": max_conc_zone,
            "cumulative_cost_usd": cost.get("total_financial_usd", 0),
            "cumulative_ois": cost.get("operational_impact_cumulative", 0),
            "cumulative_reported_cases": s.get("cumulative_reported_cases", 0),
            "cumulative_reported_cases_passenger": s.get(
                "cumulative_reported_cases_passenger", 0,
            ),
            "cumulative_reported_cases_crew": s.get(
                "cumulative_reported_cases_crew", 0,
            ),
            "cumulative_reported_noise_cases": s.get(
                "cumulative_reported_noise_cases", 0,
            ),
            "cumulative_ever_ill": s.get("cumulative_ever_ill", 0),
            "cumulative_ever_ill_passenger": s.get(
                "cumulative_ever_ill_passenger", 0,
            ),
            "cumulative_ever_ill_crew": s.get("cumulative_ever_ill_crew", 0),
            "cumulative_ever_infected": s.get("cumulative_ever_infected", 0),
            "cumulative_ever_infected_passenger": s.get(
                "cumulative_ever_infected_passenger", 0,
            ),
            "cumulative_ever_infected_crew": s.get(
                "cumulative_ever_infected_crew", 0,
            ),
            "passenger_complement": s.get("passenger_complement"),
            "crew_complement": s.get("crew_complement"),
            "infection_attack_rate_passenger": s.get(
                "infection_attack_rate_passenger", 0.0,
            ),
            "infection_attack_rate_crew": s.get(
                "infection_attack_rate_crew", 0.0,
            ),
            "reported_case_rate_passenger": reported_case_counter.get(
                "value", s.get("reported_case_rate_passenger", 0.0),
            ),
            "reported_case_rate_crew": s.get("reported_case_rate_crew", 0.0),
            "passenger_reported_case_rate_newly_confined": reported_case_counter.get(
                "newly_confined", 0,
            ),
            "passenger_reported_case_rate_exceeded": bool(
                reported_case_counter.get("exceeded", False),
            ),
            "ever_ill_rate_passenger": s.get("ever_ill_rate_passenger", 0.0),
            "ever_ill_rate_crew": s.get("ever_ill_rate_crew", 0.0),
            "trigger_status": rec.get(
                "trigger_status",
                rec.get("reactive_protocols", {}).get("trigger_status", "none"),
            ),
        })
    return series


def _detection_epochs(
    ts: list[dict[str, Any]],
) -> tuple[int | None, int | None]:
    detection_epoch = None
    confirmation_epoch = None
    for e in ts:
        status = e.get("trigger_status", "none")
        if status in ("SUSPECTED", "CONFIRMED") and detection_epoch is None:
            detection_epoch = e["epoch"]
        if status == "CONFIRMED" and confirmation_epoch is None:
            confirmation_epoch = e["epoch"]
    return detection_epoch, confirmation_epoch


def _reported_case_counter_exceeded(epoch: dict[str, Any]) -> bool:
    """Return the emitted passenger reported-case threshold state."""
    if epoch.get("passenger_reported_case_rate_exceeded", False):
        return True
    counters = epoch.get("infection_counters") or {}
    counter = counters.get("passenger_reported_case_rate") or {}
    return bool(counter.get("exceeded", False))


def _validate_role_complements(
    final: dict[str, Any],
    num_agents: int,
) -> tuple[int | None, int | None]:
    """Validate and return emitted role complements, if present."""
    passenger_complement = final.get("passenger_complement")
    crew_complement = final.get("crew_complement")
    complements_present = (
        passenger_complement is not None or crew_complement is not None
    )
    if complements_present and (
        isinstance(passenger_complement, bool)
        or not isinstance(passenger_complement, int)
        or passenger_complement <= 0
        or isinstance(crew_complement, bool)
        or not isinstance(crew_complement, int)
        or crew_complement <= 0
        or passenger_complement + crew_complement != num_agents
    ):
        raise ValueError(
            "timeseries role complements must be positive integers summing "
            f"to num_agents ({num_agents})",
        )
    if not complements_present:
        return None, None
    return passenger_complement, crew_complement


def compute_derived_metrics(ts: list[dict[str, Any]], num_agents: int) -> dict[str, Any]:
    """Compute publication-ready scalar metrics from an epoch time series."""
    if not ts:
        return {}

    infected_by_epoch = [e["infected"] for e in ts]
    peak_infected = max(infected_by_epoch)
    peak_epoch = infected_by_epoch.index(peak_infected)

    final = ts[-1]
    passenger_complement, crew_complement = _validate_role_complements(
        final,
        num_agents,
    )
    recovered = int(final.get("recovered", 0) or 0)
    infected_final = int(final.get("infected", 0) or 0)
    ever_infected = infected_final + recovered
    attack_rate = ever_infected / num_agents if num_agents > 0 else 0
    outbreak_occurred = epidemic_took_off(ts)
    detection_epoch, confirmation_epoch = _detection_epochs(ts)
    vsp_trigger_epoch = next(
        (
            e["epoch"] for e in ts
            if _reported_case_counter_exceeded(e)
        ),
        None,
    )
    r_eff_at_peak = None
    if peak_epoch > 0 and infected_by_epoch[peak_epoch - 1] > 0:
        new_at_peak = ts[peak_epoch].get("new_infections", 0)
        r_eff_at_peak = new_at_peak / infected_by_epoch[peak_epoch - 1]
    derived = {
        "attack_rate": round(attack_rate, 4),
        "reported_case_attack_rate_passenger": round(
            float(final.get("reported_case_rate_passenger", 0.0) or 0.0),
            4,
        ),
        "ever_ill_attack_rate_passenger": round(
            float(final.get("ever_ill_rate_passenger", 0.0) or 0.0), 4,
        ),
        "infection_attack_rate_passenger": round(
            float(final.get("infection_attack_rate_passenger", 0.0) or 0.0),
            4,
        ),
        "infection_attack_rate_crew": round(
            float(final.get("infection_attack_rate_crew", 0.0) or 0.0),
            4,
        ),
        "ever_ill_attack_rate_crew": round(
            float(final.get("ever_ill_rate_crew", 0.0) or 0.0), 4,
        ),
        "reported_case_attack_rate_crew": round(
            float(final.get("reported_case_rate_crew", 0.0) or 0.0), 4,
        ),
        "vsp_trigger_epoch": vsp_trigger_epoch,
        "peak_prevalence": peak_infected,
        "peak_epoch": peak_epoch,
        "outbreak_occurred": outbreak_occurred,
        "detection_epoch": detection_epoch,
        "confirmation_epoch": confirmation_epoch,
        "detection_lag": (
            peak_epoch - detection_epoch if detection_epoch is not None else None
        ),
        "total_quarantine_person_epochs": sum(e.get("quarantined", 0) for e in ts),
        "r_effective_at_peak": (
            round(r_eff_at_peak, 3) if r_eff_at_peak is not None else None
        ),
        "final_susceptible_fraction": round(
            final.get("susceptible", 0) / max(num_agents, 1), 4,
        ),
    }
    if passenger_complement is not None:
        derived["passenger_complement"] = passenger_complement
        derived["crew_complement"] = crew_complement
    return derived


def _spec_num_agents(spec: dict[str, Any]) -> int:
    """Best-effort resolve the ship population size from a run spec."""
    cfg = spec.get("config_overrides") or {}
    return int(cfg.get("ship_graph", {}).get("num_agents", 7000))


def _arm_sentinel_line_list(spec: dict[str, Any], run_dir: str) -> None:
    """Collect the sentinel ledger when anything downstream reads it.

    Shore exposure arms it because the importation fit needs hours ashore, and
    variant surveillance arms it because the observed half of every
    phylodynamic observable lives here: armed on truth alone, a Paper 3 run
    reports what was circulating and nothing about what surveillance saw.
    """
    overrides = spec.get("config_overrides") or {}
    voyage = overrides.get("voyage") or {}
    shore = voyage.get("shore_exposure") if isinstance(voyage, dict) else None
    variant = overrides.get("variant_surveillance")
    wanted = (isinstance(shore, dict) and shore.get("enabled")) or (
        isinstance(variant, dict) and variant.get("enabled")
    )
    if not wanted:
        return
    spec["run"]["sentinel_line_list"] = os.path.join(run_dir, "sentinel_line_list.json")


def _arm_lineage_census(spec: dict[str, Any], run_dir: str) -> None:
    """Collect the lineage census when strains are tracked (compact-safe).

    The truth channel the observed lineages are scored against, so it is armed
    by ``variant_surveillance`` rather than by shore exposure: a Paper 3 arm
    without it can report what was sequenced and not what was there.
    """
    variant = (spec.get("config_overrides") or {}).get("variant_surveillance")
    if not isinstance(variant, dict) or not variant.get("enabled"):
        return
    spec["run"]["lineage_census"] = os.path.join(run_dir, "lineage_census.json")


def run_simulation(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    output_root: Path | None = None,
    accumulation_suffix: str = "single",
) -> bool:
    """Run one simulation, write summary zip, return success.

    ``output_root`` overrides where the run dir / zip are written (used by the
    subprocess child so it targets the parent's output directory); it defaults
    to the module-level ``OUTPUT_ROOT``.
    """
    safe_id = _cr._safe_run_id(run_id)
    root_str = (
        os.path.realpath(str(output_root))
        if output_root is not None
        else _cr._ensure_output_root()
    )
    roots = _cr._allowed_roots(root_str)
    prepare_output_directory(root_str, allowed_roots=roots)
    run_dir = _cr._run_workdir(safe_id, output_root=root_str)
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir)
    prepare_output_directory(run_dir, allowed_roots=roots)

    # Always copy so we can set retention / telemetry paths without mutating caller.
    spec = dict(spec)
    spec["run"] = dict(spec.get("run") or {})
    if full_telemetry:
        spec["run"]["write_ground_truth"] = True
        spec["run"]["history_retention"] = "full"
        spec["run"]["simulation_history"] = os.path.join(run_dir, "simulation_history.json")
        spec["run"]["lab_notebook"] = os.path.join(run_dir, "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = os.path.join(run_dir, "ground_truth.json")
        if isinstance(spec.get("campaign_parameters"), dict):
            spec["campaign_parameters"] = dict(spec["campaign_parameters"])
            spec["campaign_parameters"]["history_retention"] = "full"
    else:
        # Campaign default: compact in-RAM history (summary / spaces / cost only).
        spec["run"].setdefault("history_retention", "compact")
        spec["run"].setdefault("write_ground_truth", False)
    _arm_sentinel_line_list(spec, run_dir)
    _arm_lineage_census(spec, run_dir)

    spec_path = resolve_child_path(run_dir, "run_spec.json")
    with validated_open(spec_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    try:
        from picard_framework.run_spec import PicardRunSpec
        from picard_framework.simulation.ship_simulation import ShipSimulation

        picard_spec = PicardRunSpec.from_picard_json(_cr._REPO_ROOT_STR, spec_path)
        sim = ShipSimulation(picard_spec, display=False)
        result = sim.run()
        if full_telemetry:
            sim.finalize(display=False)

        profiles_path = resolve_child_path(
            run_dir, "resolved_pathogen_profiles.json",
        )
        with validated_open(
            profiles_path, "w", allowed_roots=roots, encoding="utf-8",
        ) as fh:
            json.dump(
                {
                    "pathogen_ids": sorted(sim.pathogen_profiles),
                    "profiles": sim.pathogen_profiles,
                    # How this run started: a drawn boarding cohort, explicit
                    # seeds, both, or the legacy per-profile index case. The
                    # key always exists, so analysis never has to infer it.
                    "initiation": getattr(
                        getattr(sim, "engine", None),
                        "initiation_manifest",
                        None,
                    ) or dict(LEGACY_MANIFEST),
                },
                fh,
                indent=2,
            )

        last = result.history[-1] if result.history else {}
        ts = extract_timeseries(result.history)
        ts_path = resolve_child_path(run_dir, "timeseries.json")
        with validated_open(ts_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            json.dump(ts, fh)

        summary = {
            "run_id": safe_id,
            "parameters": _cr.parameters_from_spec(spec),
            "num_epochs": result.num_epochs,
            "trigger_status": result.final_trigger_status,
            "pathogen_ids": sorted(sim.pathogen_profiles),
            "summary": last.get("summary", {}),
            "cost_accounting": last.get("cost_accounting", {}),
            "derived": compute_derived_metrics(ts, _spec_num_agents(spec)),
        }
        summary_path = resolve_child_path(run_dir, "summary.json")
        with validated_open(summary_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

        zip_name = validate_path_component(f"{safe_id}.zip", label="zip artifact")
        zip_path = resolve_child_path(root_str, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _dirnames, filenames in os.walk(run_dir):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    zf.write(fpath, os.path.relpath(fpath, run_dir))
        accumulation_base = confine_to_base(
            root_str, os.path.join(root_str, "_shard_runs"),
        )
        prepare_output_directory(accumulation_base, allowed_roots=roots)
        accumulation_root = resolve_child_path(
            accumulation_base,
            validate_path_component(
                accumulation_suffix, label="shard suffix",
            ),
        )
        prepare_output_directory(accumulation_root, allowed_roots=roots)
        accumulation_dir = resolve_child_path(accumulation_root, safe_id)
        if os.path.isdir(accumulation_dir):
            shutil.rmtree(accumulation_dir)
        if keep_workdir:
            shutil.copytree(run_dir, accumulation_dir)
        else:
            shutil.move(run_dir, accumulation_dir)
        return True

    except Exception as exc:
        err_path = resolve_child_path(run_dir, "error.txt")
        with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
            fh.write(traceback.format_exc())
        return False


def _poll_child(proc: subprocess.Popen[str], timeout: int) -> tuple[bool, int | None]:
    deadline = time.monotonic() + timeout
    peak_rss_kb: int | None = None
    timed_out = False
    while True:
        hwm = _cr._read_vmhwm_kb(proc.pid)
        if hwm is not None:
            peak_rss_kb = hwm if peak_rss_kb is None else max(peak_rss_kb, hwm)
        if proc.poll() is not None:
            break
        if time.monotonic() >= deadline:
            proc.kill()
            timed_out = True
            break
        time.sleep(0.5)
    return timed_out, peak_rss_kb


def _write_subprocess_stderr(
    safe_id: str,
    roots: tuple[str, ...],
    *,
    timed_out: bool,
    timeout: int,
    returncode: int | None,
    stdout: str,
    stderr: str,
) -> None:
    err_path = _cr._output_artifact(f"{safe_id}.subprocess_stderr.txt")
    with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        if timed_out:
            fh.write(f"TimeoutExpired after {timeout}s\n")
            if stdout or stderr:
                fh.write("\n--- stdout ---\n")
                fh.write(stdout)
                fh.write("\n--- stderr ---\n")
                fh.write(stderr)
            return
        fh.write(f"returncode={returncode}\n\n")
        fh.write("--- stdout ---\n")
        fh.write(stdout)
        fh.write("\n--- stderr ---\n")
        fh.write(stderr)


def run_simulation_subprocess(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    timeout: int = 3600,
    accumulation_suffix: str = "single",
) -> bool:
    """Run one simulation in a fresh child process, then reclaim its memory.

    Repeated 7000-agent simulations leak RSS when run in a single process;
    isolating each run in a short-lived subprocess lets the OS reclaim all
    memory on exit, keeping the campaign under Fargate's memory limit.

    Polls ``/proc/<pid>/status`` ``VmHWM`` while the child runs so peak RSS
    is recorded for 2 GB Fargate sizing evidence (CloudWatch + sidecars).
    """
    safe_id = _cr._safe_run_id(run_id)
    roots = _cr._allowed_roots()
    spec_name = validate_path_component(f"{safe_id}.run_spec.json", label="spec artifact")
    spec_path = _cr._output_artifact(spec_name)
    with validated_open(spec_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(spec, fh)

    cmd = [
        sys.executable,
        str(_cr.CAMPAIGN_DIR / "campaign_runner.py"),
        "--single", spec_path, _cr._output_root_str(),
        "--accumulation-suffix", accumulation_suffix,
    ]
    if full_telemetry:
        cmd.append("--full-telemetry")
    if keep_workdir:
        cmd.append("--keep-workdir")

    returncode: int | None = None
    timed_out = False
    peak_rss_kb: int | None = None
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=_cr._REPO_ROOT_STR,
            env={
                **os.environ,
                "PYTHONPATH": _cr._REPO_ROOT_STR,
                # Windows consoles default to cp1252; LCARS banners use U+2500.
                "PYTHONIOENCODING": os.environ.get("PYTHONIOENCODING", "utf-8"),
                "PYTHONUTF8": os.environ.get("PYTHONUTF8", "1"),
            },
        )
        timed_out, peak_rss_kb = _poll_child(proc, timeout)
        try:
            out_err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out_err = proc.communicate()
            timed_out = True
        stdout, stderr = out_err[0] or "", out_err[1] or ""
        returncode = proc.returncode
        zip_path = _cr._output_artifact(f"{safe_id}.zip")
        ok = (not timed_out) and returncode == 0 and os.path.isfile(zip_path)
        if timed_out or not ok:
            _write_subprocess_stderr(
                safe_id, roots, timed_out=timed_out, timeout=timeout,
                returncode=returncode, stdout=stdout, stderr=stderr,
            )
    except Exception:
        ok = False
        raise
    finally:
        if not keep_workdir and os.path.isfile(spec_path):
            os.remove(spec_path)

    _cr._write_run_sidecars(
        safe_id,
        returncode=returncode,
        timeout=timeout,
        timed_out=timed_out,
        peak_rss_kb=peak_rss_kb,
        ok=ok,
    )
    return ok


def _run_single(
    spec_path: str,
    outdir: str,
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    accumulation_suffix: str = "single",
) -> int:
    """Child-process entry: run exactly one simulation into ``outdir``."""
    out_base = os.path.realpath(outdir)
    roots = _cr._allowed_roots(out_base)
    safe_spec = _cr._confine_campaign_path(spec_path, out_base)
    prepare_output_directory(out_base, allowed_roots=roots)
    with validated_open(safe_spec, allowed_roots=roots, encoding="utf-8") as fh:
        spec = json.load(fh)
    run_id = spec.get("description")
    if not run_id:
        raise SystemExit(f"--single spec {safe_spec} missing 'description' run id")
    safe_id = _cr._safe_run_id(str(run_id))
    ok = run_simulation(
        safe_id, spec,
        full_telemetry=full_telemetry, keep_workdir=keep_workdir,
        output_root=Path(out_base),
        accumulation_suffix=accumulation_suffix,
    )
    return 0 if ok else 1


def _campaign_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mega cruise campaign runner")
    parser.add_argument("--tier", default=None, help="Tier id or short prefix (t1…t16, c1…c6, a2)")
    parser.add_argument("--dry-run", action="store_true", help="Count runs without executing")
    parser.add_argument("--resume", action="store_true", help="Skip completed run_ids")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=f"Only re-run run_ids listed in {_cr.FAILED_RUNS_FILENAME} (clears their leftovers first). "
        "Implies skipping completed runs.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max runs to execute")
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs for all runs")
    parser.add_argument("--platform", default=None, help="Override platform_id")
    parser.add_argument("--num-agents", type=int, default=None, help="Override ship_graph.num_agents")
    parser.add_argument(
        "--natural-history-clock",
        choices=("hours", "legacy_epoch_day"),
        default=None,
        help=(
            "Select the natural-history clock arm. Manifests may declare their own "
            "(vs* Paper 3 campaigns must); a disagreement is refused, not resolved."
        ),
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Fast local smoke: destroyer_baseline, 2 epochs, 20 agents, t1, limit 1",
    )
    parser.add_argument(
        "--full-telemetry",
        action="store_true",
        help="Write full history/lab notebook into each run zip (much slower/larger)",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep unzipped run directories under telemetry_buffer/mega_cruise_campaign/",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_cr.MANIFEST_PATH,
        help="Path to campaign_manifest.json (or calibration_manifest_v1.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Redirect zips and resume logs (default: telemetry_buffer/"
        "mega_cruise_campaign). Use a separate tree for Contam matched arms.",
    )
    parser.add_argument(
        "--include-deferred",
        action="store_true",
        help="Include tiers marked deferred:true when selecting --tier all "
        "(explicit --tier c2 still works without this flag).",
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=None,
        help="Total number of shards (e.g. AWS Batch array size). "
        "A run executes only when global_index %% shard_count == shard_index.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=None,
        help="This shard's index in [0, shard_count). Defaults to env "
        "AWS_BATCH_JOB_ARRAY_INDEX when present.",
    )
    parser.add_argument(
        "--s3-prefix",
        default=None,
        help=f"s3://bucket/path to upload the fused shard zip, manifest, and "
        f"{_cr.COMPLETED_LOG.name}.",
    )
    parser.add_argument(
        "--s3-log-every",
        type=int,
        default=25,
        help=f"Upload the fused shard zip, manifest, and {_cr.COMPLETED_LOG.name} "
        "every N successful runs (default 25).",
    )
    parser.add_argument(
        "--single",
        nargs=2,
        metavar=("SPEC", "OUTDIR"),
        default=None,
        help="Child mode: run one simulation from SPEC (a run_spec.json) into OUTDIR.",
    )
    parser.add_argument(
        "--accumulation-suffix",
        default="single",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run each simulation in-process instead of an isolated subprocess "
        "(faster for debugging; leaks memory across many large runs).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Per-run subprocess timeout in seconds (default 3600; "
        "~30 min 7000-agent runs need headroom beyond the old 600s cap).",
    )
    return parser


def _apply_smoke_defaults(args: argparse.Namespace) -> None:
    if not args.smoke:
        return
    args.tier = args.tier or "t1"
    args.platform = args.platform or "destroyer_baseline"
    args.epochs = args.epochs if args.epochs is not None else 2
    args.num_agents = args.num_agents if args.num_agents is not None else 20
    args.limit = args.limit if args.limit is not None else 1


def _resolve_shard(args: argparse.Namespace) -> tuple[int | None, int]:
    if args.shard_index is None:
        env_idx = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
        if env_idx is not None:
            args.shard_index = int(env_idx)
    shard_count = args.shard_count
    shard_index = args.shard_index if args.shard_index is not None else 0
    if shard_count is None:
        return None, shard_index
    if shard_count < 1:
        raise SystemExit("--shard-count must be >= 1")
    if not 0 <= shard_index < shard_count:
        raise SystemExit(
            f"--shard-index {shard_index} out of range for "
            f"--shard-count {shard_count}",
        )
    return shard_count, shard_index


def _collect_all_runs(
    manifest: dict[str, Any],
    tiers: list[str],
    args: argparse.Namespace,
) -> list[tuple[str, str, dict[str, Any]]]:
    all_runs: list[tuple[str, str, dict[str, Any]]] = []
    for tier_id in tiers:
        runs = list(_cr.generate_tier_runs(
            manifest,
            tier_id,
            platform=args.platform,
            epochs_override=args.epochs,
            num_agents_override=args.num_agents,
            natural_history_clock=args.natural_history_clock,
        ))
        all_runs.extend((tier_id, run_id, spec) for run_id, spec in runs)
        print(f"\n{'=' * 60}")
        print(f"  {tier_id}: {len(runs)} runs")
        print(f"{'=' * 60}")
    return all_runs


def _campaign_gate(
    *,
    global_index: int,
    run_id: str,
    args: argparse.Namespace,
    shard_count: int | None,
    shard_index: int,
    executed: int,
    done: set[str],
    retry_only: set[str] | None,
    bundle: ShardBundle | None = None,
) -> str:
    if shard_count is not None and global_index % shard_count != shard_index:
        return "ignore"
    if args.limit is not None and executed >= args.limit:
        return "stop"
    if run_id in done:
        return "skip"
    if retry_only is not None and run_id not in retry_only:
        return "skip"
    if (
        (args.resume or args.retry_failed)
        and bundle is not None
        and run_id in bundle.completed_run_ids()
    ):
        return "skip_s3"
    return "run"


def _record_run_ok(bundle: ShardBundle, run_id: str) -> None:
    bundle.record_run(run_id)
    print(" OK")


def _perform_campaign_run(
    *,
    run_id: str,
    spec: dict[str, Any],
    args: argparse.Namespace,
    global_index: int,
    n_runs: int,
    shard_total: int,
    shard_index: int,
    shard_count: int | None,
    total: int,
    succeeded: int,
    failed: int,
    skipped: int,
    executed: int,
    uploader: Any,
    bundle: ShardBundle,
    t0: float,
) -> bool:
    if args.retry_failed:
        _cr.clear_failed_artifacts(run_id)
    elapsed = time.time() - t0
    rate = max(executed, 1) / max(elapsed, 1e-6)
    eta_min = max(shard_total - total, 0) / max(rate, 1e-6) / 60.0
    print(
        f"  [g{global_index + 1}/{n_runs}] {run_id}  "
        f"({succeeded}ok {failed}err {skipped}skip  "
        f"~{eta_min:.0f}min left)",
        end="",
        flush=True,
    )
    if args.in_process:
        ok = run_simulation(
            run_id, spec,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            accumulation_suffix=_shard_suffix(shard_index, shard_count),
        )
    else:
        ok = run_simulation_subprocess(
            run_id, spec,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            timeout=args.timeout,
            accumulation_suffix=_shard_suffix(shard_index, shard_count),
        )
    if not ok:
        _cr.mark_failed(run_id)
        print(" FAIL")
        return False
    _cr.mark_completed(run_id)
    _record_run_ok(bundle, run_id)
    if (
        uploader is not None
        and args.s3_log_every > 0
        and (succeeded + 1) % args.s3_log_every == 0
    ):
        _upload_completed_log(uploader, shard_index, shard_count)
        bundle.flush(uploader)
    return True


def _execute_assigned_runs(
    *,
    all_runs: list[tuple[str, str, dict[str, Any]]],
    args: argparse.Namespace,
    shard_count: int | None,
    shard_index: int,
    shard_total: int,
    done: set[str],
    retry_only: set[str] | None,
    uploader: Any,
    bundle: ShardBundle,
    t0: float,
) -> int:
    total = succeeded = failed = skipped = executed = 0
    for global_index, (_tier_id, run_id, spec) in enumerate(all_runs):
        gate = _campaign_gate(
            global_index=global_index,
            run_id=run_id,
            args=args,
            shard_count=shard_count,
            shard_index=shard_index,
            executed=executed,
            done=done,
            retry_only=retry_only,
            bundle=bundle,
        )
        if gate == "ignore":
            continue
        if gate == "stop":
            break
        total += 1
        if gate == "skip":
            skipped += 1
            continue
        if gate == "skip_s3":
            _cr.mark_completed(run_id)
            done.add(run_id)
            skipped += 1
            continue
        ok = _perform_campaign_run(
            run_id=run_id,
            spec=spec,
            args=args,
            global_index=global_index,
            n_runs=len(all_runs),
            shard_total=shard_total,
            shard_index=shard_index,
            shard_count=shard_count,
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            executed=executed,
            uploader=uploader,
            bundle=bundle,
            t0=t0,
        )
        executed += 1
        if ok:
            succeeded += 1
        else:
            failed += 1
    if uploader is not None:
        _upload_completed_log(uploader, shard_index, shard_count)
    bundle.flush(uploader)
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Campaign: {total} listed, {succeeded} ok, {failed} err, {skipped} skip")
    print(f"  Time: {elapsed / 3600:.2f}h ({elapsed / max(executed, 1):.1f}s/run)")
    print(f"  Output: {_cr.OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 1 if failed else 0


def _print_deferred_tiers(
    manifest: dict[str, Any],
    tiers: list[str],
    args: argparse.Namespace,
) -> None:
    deferred_skipped = [
        tid for tid, t in sorted(manifest["tiers"].items())
        if _cr._tier_is_deferred(t) and tid not in tiers
    ]
    if not deferred_skipped or (args.tier and args.tier not in ("all", "*")):
        return
    print(
        "  Skipping deferred tiers (pin dose then --tier <id> "
        f"or --include-deferred): {', '.join(deferred_skipped)}",
    )


def _print_dry_run(
    all_runs: list[tuple[str, str, dict[str, Any]]],
    tiers: list[str],
    shard_count: int | None,
    shard_index: int,
    shard_total: int,
) -> int:
    print(f"\n{'=' * 60}")
    print(f"  DRY RUN — {len(all_runs)} runs total across {len(tiers)} tier(s)")
    if shard_count is not None:
        print(f"  DRY RUN — {shard_total} runs would run on shard {shard_index}")
    print(f"  Output: {_cr.OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _campaign_parser().parse_args(argv)
    if args.single:
        spec_path, outdir = args.single
        return _run_single(
            spec_path, outdir,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            accumulation_suffix=args.accumulation_suffix,
        )
    if args.output_dir is not None:
        _cr.set_output_root(args.output_dir)
    _apply_smoke_defaults(args)
    manifest = _cr.load_manifest(args.manifest)
    args.natural_history_clock = _cr._resolve_manifest_clock(manifest, args)
    _cr._ensure_clock_arm(
        args.natural_history_clock or _cr.DEFAULT_NATURAL_HISTORY_CLOCK,
        explicit=args.natural_history_clock is not None,
        persist=not args.dry_run,
    )
    shard_count, shard_index = _resolve_shard(args)
    uploader = S3Uploader(args.s3_prefix) if args.s3_prefix else None
    bundle = ShardBundle(shard_index, shard_count)
    if args.resume or args.retry_failed:
        bundle.load_local_manifest()
    if uploader is not None and (args.resume or args.retry_failed):
        _download_completed_log(uploader, shard_index, shard_count)
        bundle.download(uploader)
    done = _cr.completed_runs() if (args.resume or args.retry_failed) else set()
    retry_only = _cr.failed_runs() if args.retry_failed else None
    if args.retry_failed and not retry_only:
        print(f"  --retry-failed: {_cr.FAILED_RUNS_FILENAME} is empty; nothing to retry.")
        return 0
    tiers = _cr.resolve_tier_ids(
        manifest, args.tier, include_deferred=args.include_deferred,
    )
    _print_deferred_tiers(manifest, tiers, args)
    all_runs = _collect_all_runs(manifest, tiers, args)
    shard_total = sum(
        1 for gi in range(len(all_runs))
        if shard_count is None or gi % shard_count == shard_index
    )
    if shard_count is not None:
        print(
            f"\n  Shard {shard_index}/{shard_count}: "
            f"{shard_total} of {len(all_runs)} runs assigned to this shard",
        )
    if args.dry_run:
        return _print_dry_run(all_runs, tiers, shard_count, shard_index, shard_total)
    return _execute_assigned_runs(
        all_runs=all_runs,
        args=args,
        shard_count=shard_count,
        shard_index=shard_index,
        shard_total=shard_total,
        done=done,
        retry_only=retry_only,
        uploader=uploader,
        bundle=bundle,
        t0=time.time(),
    )


def _resume_log_key(shard_index: int, shard_count: int | None) -> str:
    return f"_resume/completed_runs.{_shard_suffix(shard_index, shard_count)}.txt"


def _upload_completed_log(
    uploader: S3Uploader,
    shard_index: int,
    shard_count: int | None,
) -> None:
    """Upload this shard's completed_runs.txt under a shard-scoped key."""
    log_path = _cr._output_artifact(_cr.COMPLETED_LOG.name)
    if not os.path.isfile(log_path):
        return
    try:
        uploader.upload_file(
            Path(log_path), _resume_log_key(shard_index, shard_count),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  (completed_runs.txt upload failed: {exc})")


def _download_completed_log(
    uploader: S3Uploader,
    shard_index: int,
    shard_count: int | None,
) -> None:
    """Seed local completed_runs.txt from S3 so Spot retries skip finished runs."""
    key = _resume_log_key(shard_index, shard_count)
    log_path = Path(_cr._output_artifact(_cr.COMPLETED_LOG.name))
    try:
        ok = uploader.download_file(key, log_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  (completed_runs.txt download failed: {exc})")
        return
    if ok:
        n = len(_cr.completed_runs())
        print(f"  Resumed from s3://…/{key} ({n} completed run_ids)")
    else:
        print(f"  No prior resume log at s3://…/{key}")




if __name__ == "__main__":
    raise SystemExit(main())
