#!/usr/bin/env python3
"""Serial driver of the four-hull fleet-workup canary (aggregate only).

One process, one cell at a time, one thread. It checks the frozen design,
the hull inputs and the ContamX executable by SHA-256, runs an untimed
configuration smoke on every executed canary row and evaluates the frozen
gates (``design/canary_criteria.json``), and only then, in ``canary`` mode,
times each row as the protocol prescribes: one warm-up and five measured cold
repeats, each a fresh interpreter, then five cached downstream repeats.

``smoke`` mode stops after the gates and times nothing; it is the only mode
meant for a workstation. In ``canary`` mode a failed gate or a refused pin
exits 0 with the evidence in the artifact and no timed cell, because a Batch
retry would upload nothing. Raw records go to ``cells.jsonl``; the offline
reducer is ``tools/diag/contam_fleet_workup_reduce.py``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
import tarfile
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.diag import contam_fleet_workup_gates as gates  # noqa: E402

CAMPAIGN_DIR = os.path.join(_REPO_ROOT, "campaigns", "contam", "fleet_workup_canary_01")
FROZEN_DIR = os.path.join(CAMPAIGN_DIR, "design", "frozen")
CRITERIA_PATH = os.path.join(CAMPAIGN_DIR, "design", "canary_criteria.json")
CELL = os.path.join(_REPO_ROOT, "tools", "diag", "contam_fleet_workup_cell.py")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
EXECUTE = "planned_execute"
NATIVE = "native_prescribed"
_PROCESS_GRACE_S = 120.0
_METADATA_TIMEOUT_S = 2.0


class RunError(RuntimeError):
    """The canary cannot run as frozen; nothing is timed."""


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:  # noqa: PTH123
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:  # noqa: PTH123
        return json.load(fh)


# ── frozen design, inputs, solver ─────────────────────────────────────────


def verify_design(criteria: dict[str, Any]) -> dict[str, str]:
    """SHA-256 of every frozen design file, checked against the pins."""
    observed = {}
    for name, expected in sorted(criteria["frozen_design_sha256"].items()):
        observed[name] = sha256_file(os.path.join(FROZEN_DIR, name))
        if observed[name] != expected:
            raise RunError(f"frozen design file {name} is {observed[name]}, not {expected}")
    return observed


def canary_rows(criteria: dict[str, Any]) -> list[dict[str, str]]:
    """The canary's matrix rows, in matrix order, with the counts checked."""
    with open(os.path.join(FROZEN_DIR, "run_matrix.csv"), encoding="utf-8", newline="") as fh:  # noqa: PTH123
        rows = [r for r in csv.DictReader(fh) if r["hull"] in criteria["canary"]["hulls"]]
    executed = [r for r in rows if r["planned_status"] == EXECUTE]
    solves = sum(int(r["contamx_solves_planned"]) for r in executed)
    counts = {"rows_total": len(rows), "rows_planned_execute": len(executed),
              "contamx_solver_invocations": solves}
    for key, value in counts.items():
        if value != criteria["canary"][key]:
            raise RunError(f"canary {key} is {value}, frozen {criteria['canary'][key]}")
    return rows


def verify_inputs(hulls: list[str]) -> dict[str, str]:
    """SHA-256 of every canary hull input and shared input, against the manifest."""
    manifest = _read_json(os.path.join(FROZEN_DIR, "input_manifest.json"))
    files = list(manifest["shared_inputs"])
    for hull in hulls:
        files += manifest["hulls"][hull]["files"]
    observed = {}
    for entry in files:
        observed[entry["path"]] = sha256_file(os.path.join(_REPO_ROOT, entry["path"]))
        if observed[entry["path"]] != entry["sha256"]:
            raise RunError(f"input {entry['path']} does not match the frozen manifest")
    return observed


def _download(uri: str, dest: str) -> None:
    if uri.startswith("s3://"):
        import boto3

        bucket, _, key = uri[len("s3://"):].partition("/")
        boto3.client("s3").download_file(bucket, key, dest)
        return
    if not uri.startswith("https://"):
        raise RunError(f"unsupported ContamX archive URI {uri!r}")
    with urllib.request.urlopen(uri, timeout=120) as response, open(dest, "wb") as fh:  # noqa: S310, PTH123
        fh.write(response.read())


def provision_contamx(args: argparse.Namespace, pins: dict[str, Any], work: str) -> dict[str, Any]:
    """Locate or fetch the pinned ContamX executable; refuse any other bytes."""
    record: dict[str, Any] = {"source_url": pins["source_url"], "license": pins["license"]}
    binary = args.binary
    if args.contamx_uri:
        archive = os.path.join(work, "contamx.tar.gz")
        _download(args.contamx_uri, archive)
        record["archive"] = {"uri": args.contamx_uri, "sha256": sha256_file(archive),
                             "size_bytes": os.path.getsize(archive)}
        if record["archive"]["sha256"] != pins["archive_sha256"]:
            raise RunError("ContamX archive SHA-256 does not match the pin")
        with tarfile.open(archive) as tar:
            member = tar.getmember(pins["archive_member"])
            with tar.extractfile(member) as src, open(os.path.join(work, "contamx3"), "wb") as fh:  # noqa: PTH123
                fh.write(src.read())
        binary = os.path.join(work, "contamx3")
        os.chmod(binary, 0o755)  # noqa: S103 - executable for the job user
    if not binary or not os.path.isfile(binary):
        raise RunError("no ContamX executable: pass --binary or --contamx-uri")
    record["binary"] = {"sha256": sha256_file(binary), "size_bytes": os.path.getsize(binary),
                        "version": pins["version"]}
    if record["binary"]["sha256"] != pins["binary_sha256"]:
        raise RunError("ContamX executable SHA-256 does not match the pin")
    record["path"] = binary
    return record


# ── environment fingerprint ───────────────────────────────────────────────


def _cpu_facts() -> dict[str, Any]:
    model, physical = "", set()
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:  # noqa: PTH123
            block: dict[str, str] = {}
            for line in fh:
                if ":" in line:
                    key, _, value = line.partition(":")
                    block[key.strip()] = value.strip()
                elif block:
                    physical.add((block.get("physical id"), block.get("core id")))
                    model = model or block.get("model name", "")
                    block = {}
    except OSError:
        model = ""  # no /proc on this host; the fingerprint records a blank model
    return {"model": model, "logical": os.cpu_count(), "physical": len(physical) or None,
            "affinity": len(os.sched_getaffinity(0))}


def _memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError):
        return None


def _http_text(url: str, headers: dict[str, str] | None = None, method: str = "GET") -> str | None:
    try:
        request = urllib.request.Request(url, headers=headers or {}, method=method)  # noqa: S310
        with urllib.request.urlopen(request, timeout=_METADATA_TIMEOUT_S) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except Exception:  # noqa: BLE001 - metadata is best effort
        return None


def _host_metadata() -> dict[str, Any]:
    out: dict[str, Any] = {"hostname": platform.node()}
    ecs = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if ecs:
        raw = _http_text(ecs)
        if raw:
            doc = json.loads(raw)
            out["container"] = {k: doc.get(k) for k in ("Image", "ImageID", "DockerId")}
    base = "http://169.254.169.254/latest"
    token = _http_text(f"{base}/api/token",
                       {"X-aws-ec2-metadata-token-ttl-seconds": "60"}, "PUT")
    if token:
        for key in ("instance-id", "instance-type", "placement/availability-zone"):
            out[key] = _http_text(f"{base}/meta-data/{key}", {"X-aws-ec2-metadata-token": token})
    return out


def _git_fingerprint() -> dict[str, Any]:
    out: dict[str, Any] = {"engine_git_sha_env": os.environ.get("ENGINE_GIT_SHA")}
    try:
        out["head"] = subprocess.run(  # noqa: S603, S607
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, capture_output=True,
            text=True, check=True).stdout.strip()
        out["dirty"] = bool(subprocess.run(  # noqa: S603, S607
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=_REPO_ROOT,
            capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        out["head"], out["dirty"] = None, None
    return out


def code_sha256() -> dict[str, str]:
    """SHA-256 of the runner files, so image content is checkable against git."""
    names = ("tools/diag/contam_fleet_workup_cell.py", "tools/diag/contam_fleet_workup_run.py",
             "tools/diag/contam_fleet_workup_gates.py", "tools/diag/contam_fleet_workup_reduce.py",
             "campaigns/contam/fleet_workup_canary_01/design/canary_criteria.json",
             "campaigns/contam/fleet_workup_canary_01/entry.py", "uv.lock")
    return {
        name: sha256_file(os.path.join(_REPO_ROOT, name))
        for name in names if os.path.isfile(os.path.join(_REPO_ROOT, name))
    }


def fingerprint() -> dict[str, Any]:
    import numpy
    import scipy

    return {
        "runner": _git_fingerprint(),
        "code_sha256": code_sha256(),
        "python": {"version": platform.python_version(),
                   "implementation": platform.python_implementation()},
        "numpy": numpy.__version__, "scipy": scipy.__version__,
        "os": {"system": platform.system(), "release": platform.release(),
               "version": platform.version(), "machine": platform.machine()},
        "cpu": _cpu_facts(), "memory_bytes": _memory_bytes(),
        "thread_env": {name: os.environ.get(name) for name in THREAD_VARS},
        "host": _host_metadata(),
        "batch": {k: os.environ.get(k) for k in (
            "AWS_BATCH_JOB_ID", "AWS_BATCH_JOB_ATTEMPT", "AWS_BATCH_JQ_NAME",
            "AWS_BATCH_CE_NAME")},
        "loadavg_start": list(os.getloadavg()),
        "utc_start": datetime.now(timezone.utc).isoformat(),
    }


# ── cells ─────────────────────────────────────────────────────────────────


def _cell_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in THREAD_VARS:
        env[name] = "1"
    return env


def run_cell(
    row: dict[str, str], binary: str, timeout_s: float, cached_repeats: int, work: str,
) -> dict[str, Any]:
    """One cold cell in a fresh interpreter; returns its record plus process timing."""
    out_path = os.path.join(work, "cell.json")
    if os.path.exists(out_path):
        os.remove(out_path)
    command = [sys.executable, CELL, "--row-id", row["row_id"], "--hull", row["hull"],
               "--lane", row["lane"], "--parameter", row["parameter"],
               "--level", row["level"], "--timeout-s", str(timeout_s),
               "--cached-repeats", str(cached_repeats), "--out", out_path]
    if row["lane"] != NATIVE:
        command += ["--binary", binary]
    record: dict[str, Any] = {"row_id": row["row_id"], "observed_status": "ok", "reason": ""}
    start = time.perf_counter_ns()
    try:
        done = subprocess.run(  # noqa: S603
            command, cwd=_REPO_ROOT, env=_cell_env(), capture_output=True, text=True,
            timeout=timeout_s + _PROCESS_GRACE_S, check=False)
    except subprocess.TimeoutExpired:
        record.update(observed_status="timeout", reason="cell exceeded the solver timeout",
                      censored=1)
        done = None
    record["process_wall_ns"] = time.perf_counter_ns() - start
    record["loadavg_1m"] = os.getloadavg()[0]
    if done is not None and (done.returncode != 0 or not os.path.isfile(out_path)):
        timed_out = "TimeoutExpired" in done.stderr
        record.update(observed_status="timeout" if timed_out else "failed",
                      reason=done.stderr.strip().splitlines()[-1][:300] if done.stderr.strip() else "no output",
                      censored=int(timed_out))
    elif done is not None:
        record["cell"] = _read_json(out_path)
    return record


def lane_order(rows: list[dict[str, str]], repeat_index: int) -> list[dict[str, str]]:
    """Lanes alternate first position by repeat index (even: native first)."""
    native = [r for r in rows if r["lane"] == NATIVE]
    others = [r for r in rows if r["lane"] != NATIVE]
    return native + others if repeat_index % 2 == 0 else others + native


def settings_in_order(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    """``(hull, setting_id)`` with hulls sorted and settings in matrix order."""
    seen: list[tuple[str, str]] = []
    for hull in sorted({r["hull"] for r in rows}):
        for row in rows:
            key = (row["hull"], row["setting_id"])
            if row["hull"] == hull and key not in seen:
                seen.append(key)
    return seen


def _append(fh: Any, record: dict[str, Any]) -> None:
    fh.write(json.dumps(record, sort_keys=True) + "\n")
    fh.flush()


def run_smoke(
    rows: list[dict[str, str]], binary: str, timeout_s: float, work: str, fh: Any,
) -> dict[str, dict[str, Any]]:
    """One untimed cell per executed row; records keyed by row id."""
    cells: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["planned_status"] != EXECUTE:
            continue
        record = run_cell(row, binary, timeout_s, 0, work)
        record.update(repeat_kind="smoke", repeat_index=0)
        _append(fh, record)
        cells[row["row_id"]] = record
    return cells


def run_timed(
    rows: list[dict[str, str]], binary: str, timeout_s: float, work: str, fh: Any,
) -> int:
    """Warm-up, measured and cached repeats in the frozen order; cell count."""
    executed = [r for r in rows if r["planned_status"] == EXECUTE]
    count = 0
    for hull, setting in settings_in_order(executed):
        group = [r for r in executed if (r["hull"], r["setting_id"]) == (hull, setting)]
        plan = [("warmup", i) for i in range(int(group[0]["warmup_reps"]))]
        plan += [("measured", i) for i in range(int(group[0]["measured_reps"]))]
        for position, (kind, index) in enumerate(plan):
            last = position == len(plan) - 1
            for row in lane_order(group, position):
                cached = int(row["cached_reps"]) if last else 0
                record = run_cell(row, binary, timeout_s, cached, work)
                record.update(repeat_kind=kind, repeat_index=index)
                _append(fh, record)
                count += 1
    return count


# ── main ──────────────────────────────────────────────────────────────────


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:  # noqa: PTH123
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")


def _pack(out_dir: str, names: list[str], artifact: str) -> None:
    with tarfile.open(artifact, "w:gz") as tar:
        for name in names:
            data = open(os.path.join(out_dir, name), "rb").read()  # noqa: PTH123, SIM115
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def execute(args: argparse.Namespace, work: str) -> int:
    criteria = _read_json(CRITERIA_PATH)
    os.makedirs(args.out, exist_ok=True)
    for name in THREAD_VARS:
        os.environ[name] = "1"
    env = fingerprint()
    env["criteria_sha256"] = sha256_file(CRITERIA_PATH)
    env["design_sha256"] = verify_design(criteria)
    rows = canary_rows(criteria)
    hulls = criteria["canary"]["hulls"]
    env["inputs_sha256_before"] = verify_inputs(hulls)
    contamx = provision_contamx(args, criteria["contamx"], work)
    timeout_s = float(criteria["solver_timeout_s"])
    names = ["cells.jsonl", "smoke_gates.json", "environment.json", "external_files.json"]
    with open(os.path.join(args.out, "cells.jsonl"), "w", encoding="utf-8") as fh:  # noqa: PTH123
        smoke = run_smoke(rows, contamx["path"], timeout_s, work, fh)
        verdict = gates.evaluate(rows, smoke, criteria)
        _write_json(os.path.join(args.out, "smoke_gates.json"), verdict)
        timed = 0
        if verdict["passed"] and args.mode == "canary":
            timed = run_timed(rows, contamx["path"], timeout_s, work, fh)
    env["inputs_sha256_after"] = verify_inputs(hulls)
    env["inputs_unchanged"] = env["inputs_sha256_after"] == env["inputs_sha256_before"]
    env.update(mode=args.mode, smoke_cells=len(smoke), timed_cells=timed,
               gates_passed=verdict["passed"], loadavg_end=list(os.getloadavg()),
               utc_end=datetime.now(timezone.utc).isoformat())
    _write_json(os.path.join(args.out, "environment.json"), env)
    contamx.pop("path")
    _write_json(os.path.join(args.out, "external_files.json"), {"contamx": contamx})
    _pack(args.out, names, os.path.join(args.out, args.artifact))
    print(json.dumps({"gates_passed": verdict["passed"], "failed_gates": verdict["failed"],
                      "smoke_cells": len(smoke), "timed_cells": timed}))
    return 0 if verdict["passed"] or args.mode == "canary" else 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "canary"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--binary", default=None)
    parser.add_argument("--contamx-uri", default=None)
    parser.add_argument("--artifact", default="canary_raw.tar.gz")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="contam_fleet_workup_run_") as work:
        try:
            return execute(args, work)
        except RunError as exc:
            # A refused run still leaves evidence: on Batch a nonzero exit is
            # retried and uploads nothing, so the blocker is the artifact.
            os.makedirs(args.out, exist_ok=True)
            _write_json(os.path.join(args.out, "blocker.json"),
                        {"blocked": True, "reason": str(exc), "timed_cells": 0})
            _pack(args.out, ["blocker.json"], os.path.join(args.out, args.artifact))
            print(f"BLOCKED: {exc}")
            return 0 if args.mode == "canary" else 2


if __name__ == "__main__":
    raise SystemExit(main())
