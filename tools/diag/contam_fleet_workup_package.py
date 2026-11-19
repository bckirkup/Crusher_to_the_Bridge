#!/usr/bin/env python3
"""Build the offline package of the 77-hull airflow workup from cohort reductions.

Each ``--cohort NAME=DIR`` is one Batch job's reduction: the output of
``contam_fleet_workup_reduce.py`` plus the job receipt ``job.json``
(``receipt`` subcommand). The corrected four-hull canary is one cohort and
each fleet job is one more; no timing sample is pooled across cohorts and
every table row carries its cohort.

The package holds whole-hull aggregates only. The raw records
(``cells.jsonl``), solver files and logs stay out; from each raw record only
the two aggregate metric blocks and the solved-field digest are carried, as
``repeat_metrics.csv``, so the reduction can be repeated offline by
``verify.py`` (a copy of ``contam_fleet_workup_verify.py``).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import statistics
import sys
import tarfile
import tempfile
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from simulation_utils.paths import prepare_output_directory, validated_open  # noqa: E402
from tools.diag import contam_fleet_workup_verify as verifier  # noqa: E402

CANARY_DIR = os.path.join(_REPO_ROOT, "campaigns", "contam", "fleet_workup_canary_01")
FLEET_DIR = os.path.join(_REPO_ROOT, "campaigns", "contam", "fleet_workup_fleet_01")
FROZEN_DIR = os.path.join(CANARY_DIR, "design", "frozen")
CRITERIA_PATH = os.path.join(CANARY_DIR, "design", "canary_criteria.json")
SELECTION_PATH = os.path.join(FLEET_DIR, "design", "fleet_selection.json")
README_TEMPLATE = os.path.join(FLEET_DIR, "package_readme.md")
VERIFIER_PATH = os.path.join(_REPO_ROOT, "tools", "diag", "contam_fleet_workup_verify.py")
CANARY_COHORT = "canary_run2"
ENVIRONMENT = "environment.json"
GATES = "smoke_gates.json"
REDUCED_TABLES = ("results_long", "coverage_observed", "timing_raw", "timing_summary",
                  "contrasts", "reference_baselines", "repeat_consistency")
BLOCKS = verifier.BLOCKS
_ROOTS = (_REPO_ROOT, tempfile.gettempdir())


def _open(path: str, mode: str = "r", **kwargs: Any) -> Any:
    return validated_open(path, mode, allowed_roots=_ROOTS, **kwargs)


def _read_json(path: str) -> Any:
    with _open(path, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with _open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _write_csv(path: str, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with _open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _fmt(row.get(c)) for c in columns})


def _read_csv(path: str) -> list[dict[str, str]]:
    with _open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ── one cohort ────────────────────────────────────────────────────────────


def check_cohort_dir(directory: str) -> None:
    """The reduction's own SHA256SUMS must hold before anything is read."""
    with _open(os.path.join(directory, "SHA256SUMS"), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            if sha256_file(os.path.join(directory, name)) != digest:
                raise SystemExit(f"{directory}: {name} does not match its SHA256SUMS")


def repeat_metrics(cohort: str, directory: str) -> list[dict[str, Any]]:
    """Aggregate metric blocks of every raw record; nothing else of the record."""
    out = []
    with _open(os.path.join(directory, "cells.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            cell = record.get("cell")
            if not cell:
                continue
            digest = cell["realization"].get("field_sha256") or ""
            for block in BLOCKS:
                for name, metric in sorted(cell["blocks"][block].items()):
                    out.append({
                        "cohort": cohort, "row_id": record["row_id"],
                        "repeat_kind": record["repeat_kind"],
                        "repeat_index": record["repeat_index"], "block": block, "metric": name,
                        "value": metric["value"], "unit": metric["unit"],
                        "status": metric["status"], "reason": metric["reason"],
                        "field_sha256": digest,
                    })
    return out


def cohort_row(cohort: str, directory: str, hulls: list[str]) -> dict[str, Any]:
    env = _read_json(os.path.join(directory, ENVIRONMENT))
    job = _read_json(os.path.join(directory, "job.json"))
    gates = _read_json(os.path.join(directory, GATES))
    audit = _read_json(os.path.join(directory, "audit.json"))
    external = _read_json(os.path.join(directory, "external_files.json"))["contamx"]
    attempts = job["attempts"]
    loads = [float(r["loadavg_1m"]) for r in _read_csv(os.path.join(directory, "timing_raw.csv"))]
    return {
        "cohort": cohort, "stage": "canary" if cohort == CANARY_COHORT else "fleet",
        "hulls": ";".join(hulls), "hull_count": len(hulls),
        "batch_job_id": job["job_id"],
        "job_definition": job["job_definition"].rsplit("/", 1)[-1],
        "image_digest": job["image"].rsplit("@", 1)[-1],
        "runner_commit": env["runner"].get("engine_git_sha_env") or env["runner"].get("head"),
        "attempts": len(attempts), "exit_code": attempts[-1]["exit_code"],
        "started_at_ms": job["started_at_ms"], "stopped_at_ms": job["stopped_at_ms"],
        "instance_id": env["host"].get("instance-id"),
        "instance_type": env["host"].get("instance-type"),
        "cpu_model": env["cpu"]["model"], "cpu_affinity": env["cpu"]["affinity"],
        "thread_env_all_1": set(env["thread_env"].values()) == {"1"},
        "loadavg_1m_max": max(loads),
        "raw_artifact_sha256": job["raw_artifact"]["sha256"],
        "raw_artifact_key": job["raw_artifact"]["uri"].split("/", 3)[-1],
        "criteria_sha256": env["criteria_sha256"],
        "selection_sha256": (env.get("selection") or {}).get("sha256"),
        "contamx_binary_sha256": external["binary"]["sha256"],
        "contamx_archive_sha256": external["archive"]["sha256"],
        "contamx_version": external["binary"]["version"],
        "inputs_unchanged": bool(env.get("inputs_unchanged")),
        "gate_checks": gates["checks"] if isinstance(gates["checks"], int) else len(gates["checks"]),
        "gate_failed": gates["failed"] if isinstance(gates["failed"], int) else len(gates["failed"]),
        "audit_passed": bool(audit["passed"]), "audit_checks": len(audit["checks"]),
        "environment_sha256": sha256_file(os.path.join(directory, ENVIRONMENT)),
        "job_sha256": sha256_file(os.path.join(directory, "job.json")),
        "gates_sha256": sha256_file(os.path.join(directory, GATES)),
        "cells_sha256": sha256_file(os.path.join(directory, "cells.jsonl")),
    }


# ── package ───────────────────────────────────────────────────────────────


def _timing_overview(summary: list[dict[str, str]]) -> list[str]:
    """Per cohort, lane class and phase: spread of the per-row cold medians."""
    groups: dict[tuple[str, str, str], list[float]] = {}
    for row in summary:
        if row["repeat_kind"] not in ("measured", "cached") or not int(row["n"]):
            continue
        lane = "native" if row["lane"] == verifier.NATIVE else "contamx (all three lanes)"
        phase = row["phase"] if row["repeat_kind"] == "measured" else "downstream (cached)"
        groups.setdefault((row["cohort"], lane, phase), []).append(float(row["wall_median_ns"]) / 1e6)
    lines = ["| cohort | lane class | phase | rows | min ms | median ms | max ms |",
             "|---|---|---|---|---|---|---|"]
    for (cohort, lane, phase), values in sorted(groups.items()):
        lines.append(f"| {cohort} | {lane} | {phase} | {len(values)} | {min(values):.2f} | "
                     f"{statistics.median(values):.2f} | {max(values):.2f} |")
    return lines


def _coverage_overview(coverage: list[dict[str, str]]) -> list[str]:
    counts: dict[tuple[str, str], int] = {}
    for row in coverage:
        key = (row["observed_status"], row["reason"] if row["planned_status"] != "planned_execute" else "")
        counts[key] = counts.get(key, 0) + 1
    lines = ["| observed status | rows | reason (non-executed rows) |", "|---|---|---|"]
    lines += [f"| {status} | {n} | {reason} |" for (status, reason), n in sorted(counts.items())]
    return lines


def _cohort_overview(cohorts: list[dict[str, Any]]) -> list[str]:
    lines = ["| cohort | hulls | Batch job | host | CPU | runner | image digest | wall min | "
             "max load (1 m) | gates | raw artifact SHA-256 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in cohorts:
        wall = (int(c["stopped_at_ms"]) - int(c["started_at_ms"])) / 60000.0
        lines.append(
            f"| {c['cohort']} | {c['hull_count']} | `{c['batch_job_id']}` | {c['instance_id']} "
            f"({c['instance_type']}) | {c['cpu_model']} | `{str(c['runner_commit'])[:12]}` | "
            f"`{c['image_digest'][7:19]}…` | {wall:.1f} | {float(c['loadavg_1m_max']):.2f} | "
            f"{c['gate_checks']} / {c['gate_failed']} failed | `{c['raw_artifact_sha256']}` |")
    return lines


def write_readme(out_dir: str, tables: dict[str, list[dict[str, Any]]]) -> None:
    with _open(README_TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    summary = _read_csv(os.path.join(out_dir, "data", "timing_summary.csv"))
    coverage = _read_csv(os.path.join(out_dir, "data", "coverage_observed.csv"))
    fill = {
        "<<COHORTS>>": "\n".join(_cohort_overview(tables["cohorts"])),
        "<<COVERAGE>>": "\n".join(_coverage_overview(coverage)),
        "<<TIMING>>": "\n".join(_timing_overview(summary)),
    }
    for key, value in fill.items():
        if key not in text:
            raise SystemExit(f"README template lacks {key}")
        text = text.replace(key, value)
    with _open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(text)


def _expected(cohorts: list[dict[str, Any]], out_dir: str) -> dict[str, Any]:
    selection = _read_json(SELECTION_PATH)
    pinned = ["design/SHA256SUMS", "design/run_matrix.csv", "design/coverage.csv",
              "design/input_manifest.json", "design/protocol.json", "design/canary_criteria.json",
              "design/fleet_selection.json"]
    return {
        "id": "CONTAM-FLEET-WORKUP-PACKAGE-01",
        "design_commit": selection["design_commit"], "input_commit": selection["input_commit"],
        "counts": {"canary": _read_json(CRITERIA_PATH)["canary"],
                   "fleet": selection["expected_fleet"],
                   "union": selection["expected_union_with_canary"]},
        "excluded_no_bundle": selection["excluded_no_bundle"],
        "cohort_hulls": {c["cohort"]: c["hulls"].split(";") for c in cohorts},
        "cohort_receipts": {c["cohort"]: [c["batch_job_id"], c["image_digest"],
                                          c["raw_artifact_sha256"]] for c in cohorts},
        "sha256": {name: sha256_file(os.path.join(out_dir, name)) for name in pinned},
    }


def build(cohort_dirs: dict[str, str], out_dir: str) -> None:
    """Write the unpacked package into ``out_dir`` (emptied first)."""
    out_dir = prepare_output_directory(out_dir, allowed_roots=_ROOTS)
    for sub in ("data", "design"):
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)
    tables: dict[str, list[dict[str, Any]]] = {name: [] for name in REDUCED_TABLES}
    tables.update({"repeat_metrics": [], "cohorts": [], "gates_summary": [], "code_sha256": []})
    readout = ["# Per-hull readout tables (generated)", "",
               "Hulls appear by cohort, alphabetically inside a cohort; nothing is ranked. "
               "`blank (status)` is a quantity the lane does not resolve, not a zero. Timings "
               "of different cohorts come from different hosts and are not comparable as one "
               "sample.", ""]
    for cohort, directory in cohort_dirs.items():
        check_cohort_dir(directory)
        for name in REDUCED_TABLES:
            tables[name] += [{"cohort": cohort, **row}
                             for row in _read_csv(os.path.join(directory, f"{name}.csv"))]
        hulls = sorted({r["hull"] for r in _read_csv(os.path.join(directory, "coverage_observed.csv"))})
        tables["repeat_metrics"] += repeat_metrics(cohort, directory)
        tables["cohorts"].append(cohort_row(cohort, directory, hulls))
        gates = _read_json(os.path.join(directory, GATES))
        tables["gates_summary"] += [{"cohort": cohort, "gate": gate, **counts}
                                    for gate, counts in sorted(gates["summary"].items())]
        env = _read_json(os.path.join(directory, ENVIRONMENT))
        tables["code_sha256"] += [{"cohort": cohort, "path": path, "sha256": digest}
                                  for path, digest in sorted(env["code_sha256"].items())]
        with _open(os.path.join(directory, "readout_tables.md"), encoding="utf-8") as fh:
            body = fh.read().split("\n## ", 1)[1]
        readout += [f"# Cohort {cohort}", "", "## " + body]
    for name, columns in verifier.COLUMNS.items():
        _write_csv(os.path.join(out_dir, name), columns, tables[name.split("/")[1][:-4]])
    for name in ("SHA256SUMS", "coverage.csv", "dry_run_summary.json", "input_manifest.json",
                 "protocol.json", "run_matrix.csv"):
        shutil.copyfile(os.path.join(FROZEN_DIR, name), os.path.join(out_dir, "design", name))
    shutil.copyfile(CRITERIA_PATH, os.path.join(out_dir, "design", "canary_criteria.json"))
    shutil.copyfile(SELECTION_PATH, os.path.join(out_dir, "design", "fleet_selection.json"))
    shutil.copyfile(VERIFIER_PATH, os.path.join(out_dir, "verify.py"))
    with _open(os.path.join(out_dir, "per_hull_readout.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(readout))
    with _open(os.path.join(out_dir, "EXPECTED.json"), "w", encoding="utf-8") as fh:
        json.dump(_expected(tables["cohorts"], out_dir), fh, indent=1, sort_keys=True)
        fh.write("\n")
    write_readme(out_dir, tables)
    write_sums(out_dir)


def _files(out_dir: str) -> list[str]:
    names = []
    for folder, _dirs, files in os.walk(out_dir):
        names += [os.path.relpath(os.path.join(folder, f), out_dir).replace(os.sep, "/")
                  for f in files]
    return sorted(names)


def write_sums(out_dir: str) -> None:
    lines = [f"{sha256_file(os.path.join(out_dir, n))}  {n}\n"
             for n in _files(out_dir) if n != "SHA256SUMS"]
    with _open(os.path.join(out_dir, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def archive(out_dir: str, path: str, top: str) -> str:
    """Byte-reproducible ``tar.gz`` of the package; returns its SHA-256."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in _files(out_dir):
            with _open(verifier.inside(out_dir, name), "rb") as fh:
                data = fh.read()
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    with _open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
        gz.write(buffer.getvalue())
    digest = sha256_file(path)
    with _open(path + ".sha256", "w", encoding="utf-8") as fh:
        fh.write(f"{digest}  {os.path.basename(path)}\n")
    return digest


def receipt(describe_path: str, raw_path: str, raw_uri: str, runner_commit: str, base: str) -> dict[str, Any]:
    """``job.json`` of one job from ``aws batch describe-jobs`` and its raw artifact."""
    job = _read_json(describe_path)["jobs"][0]
    container = job["container"]
    return {
        "array": "arrayProperties" in job and bool(job["arrayProperties"]),
        "attempts": [{
            "container_instance_arn": a["container"].get("containerInstanceArn"),
            "exit_code": a["container"].get("exitCode"),
            "log_stream": a["container"].get("logStreamName"),
            "started_at_ms": a.get("startedAt"), "stopped_at_ms": a.get("stoppedAt"),
            "status_reason": a.get("statusReason"),
        } for a in job["attempts"]],
        "command": container["command"], "created_at_ms": job["createdAt"],
        "image": container["image"],
        "image_build": {"base": base, "dockerfiles": ["Dockerfile", "deploy/aws/Dockerfile.campaign"],
                        "image_digest": container["image"].rsplit("@", 1)[-1],
                        "runner_commit": runner_commit},
        "job_definition": job["jobDefinition"], "job_id": job["jobId"], "job_name": job["jobName"],
        "job_queue": job["jobQueue"],
        "raw_artifact": {"sha256": sha256_file(raw_path), "uri": raw_uri},
        "resource_requirements": container["resourceRequirements"],
        "source": "aws batch describe-jobs, read after the job stopped",
        "started_at_ms": job["startedAt"], "status": job["status"],
        "stopped_at_ms": job["stoppedAt"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("build")
    make.add_argument("--cohort", action="append", required=True, metavar="NAME=DIR")
    make.add_argument("--out", required=True)
    make.add_argument("--archive", required=True)
    rec = sub.add_parser("receipt")
    for name in ("--describe", "--raw", "--raw-uri", "--runner-commit", "--base", "--out"):
        rec.add_argument(name, required=True)
    args = parser.parse_args(argv)
    if args.command == "receipt":
        doc = receipt(args.describe, args.raw, args.raw_uri, args.runner_commit, args.base)
        with _open(args.out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
            fh.write("\n")
        return 0
    cohorts = {name: path for name, path in (item.split("=", 1) for item in args.cohort)}
    build(cohorts, args.out)
    top = os.path.basename(args.archive).removesuffix(".tar.gz")
    print(f"{archive(args.out, args.archive, top)}  {args.archive}")
    return verifier.verify(args.out, _ROOTS)


if __name__ == "__main__":
    raise SystemExit(main())
