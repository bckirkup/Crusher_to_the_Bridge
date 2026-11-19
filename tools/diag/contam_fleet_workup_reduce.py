#!/usr/bin/env python3
"""Offline reducer and audit of the fleet-workup canary raw records.

Reads the raw artifact written by ``contam_fleet_workup_run.py`` and writes
the checksum-verifiable package: ``results_long.csv`` (two labelled blocks),
``coverage_observed.csv``, ``timing_raw.csv``, ``timing_summary.csv``,
``contrasts.csv``, ``reference_baselines.csv``, ``repeat_consistency.csv``,
``audit.json`` and ``SHA256SUMS``, beside unchanged copies of the frozen
design. Aggregate only: one value per hull x lane x setting x metric.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import statistics
import sys
import tempfile
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from simulation_utils.paths import prepare_output_directory, validated_open  # noqa: E402
from tools.diag.contam_fleet_workup_gates import rel_diff  # noqa: E402

CAMPAIGN_DIR = os.path.join(_REPO_ROOT, "campaigns", "contam", "fleet_workup_canary_01")

_ROOTS = (_REPO_ROOT, tempfile.gettempdir())


def _open(path: str, mode: str = "r", **kwargs: Any) -> Any:
    """Open a file confined to the repository or the temporary directory."""
    return validated_open(path, mode, allowed_roots=_ROOTS, **kwargs)

FROZEN_DIR = os.path.join(CAMPAIGN_DIR, "design", "frozen")
CRITERIA_PATH = os.path.join(CAMPAIGN_DIR, "design", "canary_criteria.json")
RAW_FILES = ("cells.jsonl", "smoke_gates.json", "environment.json", "external_files.json")
DESIGN_FILES = ("coverage.csv", "input_manifest.json", "protocol.json", "run_matrix.csv")
BLOCKS = ("solved_airflow", "downstream_mixing")
NATIVE = "native_prescribed"
COMMISSIONED = "contamx_commissioned_export"
EXECUTE = "planned_execute"
OK, UNCHANGED = "ok", "unchanged"
TIMED_KINDS = ("warmup", "measured")
PROCESS_PHASE = "process_total"

RESULT_COLUMNS = ("row_id", "hull", "lane", "setting_id", "block", "metric", "value", "unit",
                  "observed_status", "reason", "platform_git_tree", "runner_commit")
COVERAGE_COLUMNS = ("row_id", "hull", "lane", "setting_id", "planned_status", "observed_status",
                    "observed_status_solved_airflow", "observed_status_downstream_mixing",
                    "reason", "cold_cells_completed", "solver_invocations_timed",
                    "cached_repeats_completed")
TIMING_COLUMNS = ("row_id", "repeat_kind", "repeat_index", "phase", "wall_ns", "cpu_parent_ns",
                  "cpu_child_ns", "censored", "observed_status", "loadavg_1m")
SUMMARY_COLUMNS = ("row_id", "hull", "lane", "setting_id", "repeat_kind", "phase", "n",
                   "timeouts", "wall_median_ns", "wall_min_ns", "wall_max_ns", "wall_iqr_ns",
                   "wall_mad_ns", "cpu_parent_median_ns", "cpu_child_median_ns")
CONTRAST_COLUMNS = ("hull", "setting_id", "block", "metric", "unit", "native", "contamx",
                    "contamx_minus_native", "contamx_over_native", "native_minus_baseline",
                    "contamx_minus_baseline", "native_status", "contamx_status")
REFERENCE_COLUMNS = ("hull", "lane", "block", "metric", "unit", "value", "harmonized_value",
                     "value_minus_harmonized", "status")
CONSISTENCY_COLUMNS = ("row_id", "records", "distinct_field_sha256", "max_metric_rel_diff")


def _read_json(path: str) -> Any:
    with _open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_cells(path: str) -> list[dict[str, Any]]:
    with _open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_matrix(hulls: list[str]) -> list[dict[str, str]]:
    with _open(os.path.join(FROZEN_DIR, "run_matrix.csv"), encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["hull"] in hulls]


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_csv(path: str, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with _open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _fmt(row.get(c)) for c in columns})


# ── representative record and status per row ──────────────────────────────


def by_row(cells: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for record in cells:
        out.setdefault(record["row_id"], []).append(record)
    return out


def representative(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The last completed measured repeat; the smoke cell when nothing was timed."""
    for kinds in (("measured",), ("warmup", "smoke")):
        done = [r for r in records if r["repeat_kind"] in kinds and r.get("cell")]
        if done:
            return done[-1]
    return None


def block_changed(cell: dict[str, Any], base: dict[str, Any], block: str, tol: float) -> bool:
    """Whether any numeric metric of ``block`` differs from the lane baseline."""
    for name, metric in cell["cell"]["blocks"][block].items():
        other = base["cell"]["blocks"][block][name]["value"]
        if metric["value"] is None or other is None:
            continue
        if rel_diff(float(metric["value"]), float(other)) > tol:
            return True
    return False


def row_status(
    row: dict[str, str], records: list[dict[str, Any]], base: dict[str, Any] | None, tol: float,
) -> dict[str, str]:
    """Observed status of one row, overall and per block."""
    if row["planned_status"] != EXECUTE:
        status = dict.fromkeys(BLOCKS, row["planned_status"])
        return {**status, "overall": row["planned_status"], "reason": row["reason"]}
    bad = [r for r in records if r["observed_status"] != OK]
    rep = representative(records)
    if bad or rep is None:
        state = bad[0]["observed_status"] if bad else "failed"
        reason = bad[0]["reason"] if bad else "no completed cell"
        return {**dict.fromkeys(BLOCKS, state), "overall": state, "reason": reason}
    status = {}
    for block in BLOCKS:
        moved = row["setting_id"] == "baseline" or base is None or block_changed(rep, base, block, tol)
        status[block] = OK if moved else UNCHANGED
    overall = OK if OK in status.values() else UNCHANGED
    return {**status, "overall": overall, "reason": ""}


class Reduction:
    """Rows, records, baselines and statuses of one canary run."""

    def __init__(self, raw_dir: str) -> None:
        self.criteria = _read_json(CRITERIA_PATH)
        self.environment = _read_json(os.path.join(raw_dir, "environment.json"))
        self.gates = _read_json(os.path.join(raw_dir, "smoke_gates.json"))
        self.manifest = _read_json(os.path.join(FROZEN_DIR, "input_manifest.json"))
        self.rows = load_matrix(self.criteria["canary"]["hulls"])
        self.cells = load_cells(os.path.join(raw_dir, "cells.jsonl"))
        self.records = by_row(self.cells)
        self.tol = float(self.criteria["tolerances"]["unchanged_rel"])
        self.rep = {
            rid: representative(recs) for rid, recs in self.records.items()
        }
        self.status = {
            row["row_id"]: row_status(
                row, self.records.get(row["row_id"], []), self.baseline(row), self.tol,
            )
            for row in self.rows
        }
        runner = self.environment["runner"]
        self.runner_commit = runner.get("engine_git_sha_env") or runner.get("head") or ""

    def baseline(self, row: dict[str, str]) -> dict[str, Any] | None:
        return self.rep.get(f"{row['hull']}|{row['lane']}|baseline")

    def metric_template(self, lane: str) -> dict[str, dict[str, str]]:
        """Metric names and units of a lane, from any completed cell of it."""
        for row in self.rows:
            rep = self.rep.get(row["row_id"])
            if rep and (row["lane"] == NATIVE) == (lane == NATIVE):
                return {
                    block: {n: m["unit"] for n, m in rep["cell"]["blocks"][block].items()}
                    for block in BLOCKS
                }
        return {block: {} for block in BLOCKS}


# ── tables ────────────────────────────────────────────────────────────────


def _result_row(red: Reduction, row: dict[str, str], block: str, name: str) -> dict[str, Any]:
    status = red.status[row["row_id"]]
    out = {
        "row_id": row["row_id"], "hull": row["hull"], "lane": row["lane"],
        "setting_id": row["setting_id"], "block": block, "metric": name,
        "platform_git_tree": red.manifest["hulls"][row["hull"]].get("platform_git_tree", ""),
        "runner_commit": red.runner_commit,
        "value": None, "observed_status": status[block], "reason": status["reason"],
    }
    rep = red.rep.get(row["row_id"])
    if status[block] in (OK, UNCHANGED) and rep is not None:
        metric = rep["cell"]["blocks"][block][name]
        if metric["status"] == OK:
            out["value"] = metric["value"]
            out["reason"] = metric["reason"]
        else:
            out.update(observed_status=metric["status"], reason=metric["reason"])
    return out


def results_long(red: Reduction) -> list[dict[str, Any]]:
    out = []
    for row in red.rows:
        template = red.metric_template(row["lane"])
        for block in BLOCKS:
            for name, unit in sorted(template[block].items()):
                out.append({**_result_row(red, row, block, name), "unit": unit})
    return out


def coverage_observed(red: Reduction) -> list[dict[str, Any]]:
    out = []
    for row in red.rows:
        records = red.records.get(row["row_id"], [])
        timed = [r for r in records if r["repeat_kind"] in TIMED_KINDS]
        status = red.status[row["row_id"]]
        out.append({
            "row_id": row["row_id"], "hull": row["hull"], "lane": row["lane"],
            "setting_id": row["setting_id"], "planned_status": row["planned_status"],
            "observed_status": status["overall"],
            "observed_status_solved_airflow": status["solved_airflow"],
            "observed_status_downstream_mixing": status["downstream_mixing"],
            "reason": status["reason"],
            "cold_cells_completed": sum(bool(r.get("cell")) for r in timed),
            "solver_invocations_timed": 0 if row["lane"] == NATIVE else len(timed),
            "cached_repeats_completed": sum(len(r["cell"]["cached"]) for r in timed if r.get("cell")),
        })
    return out


def timing_raw(red: Reduction) -> list[dict[str, Any]]:
    out = []
    for record in red.cells:
        if record["repeat_kind"] not in TIMED_KINDS:
            continue
        common = {"row_id": record["row_id"], "observed_status": record["observed_status"],
                  "censored": int(record.get("censored", 0)), "loadavg_1m": record["loadavg_1m"]}
        head = {**common, "repeat_kind": record["repeat_kind"],
                "repeat_index": record["repeat_index"]}
        cell = record.get("cell")
        # The last measured interpreter also runs the cached repeats; they are
        # not part of a cold cell, so their wall time is taken out of its total.
        cached_ns = sum(c["wall_ns"] for c in cell["cached"]) if cell else 0
        out.append({**head, "phase": PROCESS_PHASE,
                    "wall_ns": record["process_wall_ns"] - cached_ns})
        if not cell:
            continue
        for phase, clocks in sorted(cell["phases"].items()):
            out.append({**head, "phase": phase, **clocks})
        for index, clocks in enumerate(cell["cached"]):
            out.append({**common, "repeat_kind": "cached", "repeat_index": index,
                        "phase": "downstream", **clocks})
    return out


def _spread(values: list[int]) -> dict[str, Any]:
    median = statistics.median(values)
    if len(values) >= 2:
        quartiles = statistics.quantiles(values, n=4, method="inclusive")
        iqr = quartiles[2] - quartiles[0]
    else:
        iqr = 0
    return {"wall_median_ns": median, "wall_min_ns": min(values), "wall_max_ns": max(values),
            "wall_iqr_ns": iqr,
            "wall_mad_ns": statistics.median([abs(v - median) for v in values])}


def timing_summary(red: Reduction, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Robust summaries over measured and cached repeats; warm-ups excluded."""
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in raw:
        if item["repeat_kind"] != "warmup":
            groups.setdefault((item["row_id"], item["repeat_kind"], item["phase"]), []).append(item)
    lookup = {r["row_id"]: r for r in red.rows}
    out = []
    # A timed-out cell leaves only its process_total record, so timeouts are
    # counted there and reported on every phase of the row.
    timeouts: dict[tuple[str, str], int] = {}
    for item in raw:
        if item["phase"] == PROCESS_PHASE and item["censored"]:
            key = (item["row_id"], item["repeat_kind"])
            timeouts[key] = timeouts.get(key, 0) + 1
    for (row_id, kind, phase), items in groups.items():
        kept = [i for i in items if not i["censored"] and i["observed_status"] == OK]
        row = lookup[row_id]
        if not kept:
            out.append({"row_id": row_id, "hull": row["hull"], "lane": row["lane"],
                        "setting_id": row["setting_id"], "repeat_kind": kind, "phase": phase,
                        "n": 0, "timeouts": timeouts.get((row_id, kind), 0)})
            continue
        cpu = [i["cpu_parent_ns"] for i in kept if i.get("cpu_parent_ns") is not None]
        child = [i["cpu_child_ns"] for i in kept if i.get("cpu_child_ns") is not None]
        out.append({
            "row_id": row_id, "hull": row["hull"], "lane": row["lane"],
            "setting_id": row["setting_id"], "repeat_kind": kind, "phase": phase,
            "n": len(kept), "timeouts": timeouts.get((row_id, kind), 0),
            **_spread([int(i["wall_ns"]) for i in kept]),
            "cpu_parent_median_ns": statistics.median(cpu) if cpu else None,
            "cpu_child_median_ns": statistics.median(child) if child else None,
        })
    return out


def _value(red: Reduction, row_id: str, block: str, name: str) -> tuple[float | None, str]:
    rep = red.rep.get(row_id)
    status = red.status.get(row_id)
    if rep is None or status is None or status[block] not in (OK, UNCHANGED):
        return None, status[block] if status else "missing"
    metric = rep["cell"]["blocks"][block].get(name)
    if metric is None:
        return None, "not_applicable"
    return metric["value"], status[block] if metric["status"] == OK else metric["status"]


def _minus(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def contrasts(red: Reduction) -> list[dict[str, Any]]:
    """ContamX (harmonized) against native, and each lane against its baseline."""
    out = []
    settings = [r for r in red.rows if r["lane"] == COMMISSIONED]
    template = red.metric_template(COMMISSIONED)
    for row in settings:
        hull, setting = row["hull"], row["setting_id"]
        for block in BLOCKS:
            for name, unit in sorted(template[block].items()):
                native, n_status = _value(red, f"{hull}|{NATIVE}|{setting}", block, name)
                contamx, c_status = _value(red, row["row_id"], block, name)
                n_base, _ = _value(red, f"{hull}|{NATIVE}|baseline", block, name)
                c_base, _ = _value(red, f"{hull}|{COMMISSIONED}|baseline", block, name)
                diff = _minus(contamx, native)
                out.append({
                    "hull": hull, "setting_id": setting, "block": block, "metric": name,
                    "unit": unit, "native": native, "contamx": contamx,
                    "contamx_minus_native": diff,
                    "contamx_over_native": contamx / native if diff is not None and native else None,
                    "native_minus_baseline": _minus(native, n_base),
                    "contamx_minus_baseline": _minus(contamx, c_base),
                    "native_status": n_status, "contamx_status": c_status,
                })
    return out


def reference_baselines(red: Reduction) -> list[dict[str, Any]]:
    """As-committed and authored baselines beside the harmonized one; never pooled."""
    out = []
    template = red.metric_template(COMMISSIONED)
    for row in red.rows:
        if row["lane"] in (NATIVE, COMMISSIONED):
            continue
        for block in BLOCKS:
            for name, unit in sorted(template[block].items()):
                value, status = _value(red, row["row_id"], block, name)
                harmonized, _ = _value(red, f"{row['hull']}|{COMMISSIONED}|baseline", block, name)
                out.append({"hull": row["hull"], "lane": row["lane"], "block": block,
                            "metric": name, "unit": unit, "value": value,
                            "harmonized_value": harmonized,
                            "value_minus_harmonized": _minus(value, harmonized),
                            "status": status})
    return out


def _cell_diff(cell: dict[str, Any], first: dict[str, Any]) -> float:
    """Largest relative metric difference between two repeats of one row."""
    worst = 0.0
    for block in BLOCKS:
        for name, metric in cell["blocks"][block].items():
            other = first["blocks"][block][name]["value"]
            if metric["value"] is not None and other is not None:
                worst = max(worst, rel_diff(float(metric["value"]), float(other)))
    return worst


def repeat_consistency(red: Reduction) -> list[dict[str, Any]]:
    """Whether every repeat of a row reproduced the same field and metrics."""
    out = []
    for row_id, records in sorted(red.records.items()):
        done = [r["cell"] for r in records if r.get("cell")]
        worst = max((_cell_diff(cell, done[0]) for cell in done[1:]), default=0.0)
        shas = {c["realization"].get("field_sha256") for c in done} - {None}
        out.append({"row_id": row_id, "records": len(done),
                    "distinct_field_sha256": len(shas), "max_metric_rel_diff": worst})
    return out


# ── readout tables ────────────────────────────────────────────────────────

BASELINE_METRICS = (
    ("solved_airflow", "supply_total_m3h"), ("solved_airflow", "return_total_m3h"),
    ("solved_airflow", "outdoor_air_total_m3h"), ("solved_airflow", "exhaust_total_m3h"),
    ("solved_airflow", "ambient_inward_total_m3h"), ("solved_airflow", "ambient_outward_total_m3h"),
    ("solved_airflow", "interzone_gross_m3h"), ("solved_airflow", "hull_balance_residual_m3h"),
    ("solved_airflow", "max_abs_zone_balance_residual_m3h"),
    ("solved_airflow", "pressure_abs_dp_median_pa"), ("solved_airflow", "pressure_abs_dp_p95_pa"),
    ("solved_airflow", "pressure_abs_dp_max_pa"),
    ("downstream_mixing", "outdoor_air_derived_m3h"),
    ("downstream_mixing", "effective_outdoor_air_fraction_of_supply"),
    ("downstream_mixing", "nonrecirculated_return_m3h"),
    ("downstream_mixing", "boundary_sink_total_m3h"),
    ("downstream_mixing", "clean_air_equivalent_no_filter_m3h"),
    ("downstream_mixing", "clean_air_equivalent_with_filter_m3h"),
    ("downstream_mixing", "whole_hull_air_change_1_per_h"),
    ("downstream_mixing", "uniform_tracer_material_time_h"),
    ("downstream_mixing", "uniform_tracer_closure_error"),
)
RESPONSE_METRICS = (
    ("solved_airflow", "supply_total_m3h"), ("solved_airflow", "ambient_inward_total_m3h"),
    ("solved_airflow", "interzone_gross_m3h"), ("solved_airflow", "pressure_abs_dp_p95_pa"),
    ("downstream_mixing", "effective_outdoor_air_fraction_of_supply"),
    ("downstream_mixing", "whole_hull_air_change_1_per_h"),
    ("downstream_mixing", "uniform_tracer_material_time_h"),
)
COLD_PHASES = ("native_construct", "contamx_export", "contamx_solve", "contamx_import",
               "field_reduce", "downstream", "end_to_end", PROCESS_PHASE)


def _num(value: Any, status: str = "") -> str:
    if value is None:
        return f"blank ({status})" if status else "—"
    return f"{float(value):.6g}"


def _table(header: list[str], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return [*lines, ""]


def _baseline_table(red: Reduction, hull: str) -> list[str]:
    lanes = [r["lane"] for r in red.rows if r["hull"] == hull and r["setting_id"] == "baseline"]
    body = []
    for block, name in BASELINE_METRICS:
        cells = [_num(*_value(red, f"{hull}|{lane}|baseline", block, name)) for lane in lanes]
        body.append([block, name, *cells])
    return _table(["block", "metric", *lanes], body)


def _response_table(red: Reduction, hull: str) -> list[str]:
    header = ["setting", "lane", "solved", "downstream"]
    header += [f"{name} (level − baseline)" for _b, name in RESPONSE_METRICS]
    body = []
    for row in red.rows:
        if row["hull"] != hull or row["setting_id"] == "baseline" or row["lane"] not in (NATIVE, COMMISSIONED):
            continue
        status = red.status[row["row_id"]]
        deltas = []
        for block, name in RESPONSE_METRICS:
            value, state = _value(red, row["row_id"], block, name)
            base, _ = _value(red, f"{hull}|{row['lane']}|baseline", block, name)
            deltas.append(_num(_minus(value, base), state if value is None else ""))
        body.append([row["setting_id"], row["lane"], status["solved_airflow"],
                     status["downstream_mixing"], *deltas])
    return _table(header, body)


def _timing_tables(red: Reduction, summary: list[dict[str, Any]], hull: str) -> list[str]:
    index = {(s["row_id"], s["repeat_kind"], s["phase"]): s for s in summary}
    lanes = [r for r in red.rows if r["hull"] == hull and r["setting_id"] == "baseline"]

    def cell(row_id: str, kind: str, phase: str) -> str:
        item = index.get((row_id, kind, phase))
        if item is None or not item["n"]:
            return "—"
        return f"{item['wall_median_ns'] / 1e6:.2f} ({item['wall_iqr_ns'] / 1e6:.2f})"

    cold = [[phase, *[cell(r["row_id"], "measured", phase) for r in lanes]] for phase in COLD_PHASES]
    cached = [["downstream (cached)", *[cell(r["row_id"], "cached", "downstream") for r in lanes]]]
    spans = []
    for lane in (NATIVE, COMMISSIONED):
        ends = [s["wall_median_ns"] / 1e6 for s in summary
                if s["hull"] == hull and s["lane"] == lane and s["n"]
                and s["repeat_kind"] == "measured" and s["phase"] == "end_to_end"]
        if ends:
            spans.append([lane, str(len(ends)), f"{min(ends):.2f}", f"{max(ends):.2f}"])
    header = ["phase, wall ms: median (IQR), n=5", *[r["lane"] for r in lanes]]
    return [
        "Cold, measured repeats, baseline setting:", "", *_table(header, cold),
        "Cached, same interpreter, engine built (never compared with cold):", "",
        *_table(header, cached),
        "End-to-end cold median across all executed settings:", "",
        *_table(["lane", "rows", "min ms", "max ms"], spans),
    ]


def readout_markdown(red: Reduction, summary: list[dict[str, Any]]) -> str:
    """Per-hull aggregate tables; generated, so every number traces to a CSV."""
    lines = ["# Canary readout tables (generated)", "",
             "Generated by `tools/diag/contam_fleet_workup_reduce.py` from `cells.jsonl`. "
             "Hulls are listed alphabetically; nothing is ranked. `blank (status)` is a "
             "quantity the lane does not resolve, not a zero.", ""]
    for hull in sorted({r["hull"] for r in red.rows}):
        lines += [f"## {hull}", "", "### Baseline, all lanes", "", *_baseline_table(red, hull),
                  "### Setting responses (each lane against its own baseline)", "",
                  *_response_table(red, hull), "### Run time", "",
                  *_timing_tables(red, summary, hull)]
    return "\n".join(lines)


# ── audit ─────────────────────────────────────────────────────────────────


def audit(red: Reduction, tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Offline checks of the reduced package against the frozen design."""
    coverage = tables["coverage_observed.csv"]
    results = tables["results_long.csv"]
    timed = [c for c in red.cells if c["repeat_kind"] in TIMED_KINDS]
    planned = red.criteria["canary"]
    executed = [r for r in red.rows if r["planned_status"] == EXECUTE]
    expect_cold = sum(int(r["warmup_reps"]) + int(r["measured_reps"]) for r in executed)
    expect_cached = sum(int(r["cached_reps"]) for r in executed)
    numeric_only_when_ok = all(
        (r["value"] is not None) <= (r["observed_status"] in (OK, UNCHANGED)) for r in results
    )
    env = red.environment
    checks = {
        "every_row_id_once": sorted(c["row_id"] for c in coverage) == sorted(r["row_id"] for r in red.rows),
        "rows_total": len(coverage) == planned["rows_total"],
        "rows_executed_ok": sum(c["observed_status"] in (OK, UNCHANGED) for c in coverage)
        == planned["rows_planned_execute"],
        "cold_cells": len(timed) == expect_cold,
        "solver_invocations_timed": sum(c["solver_invocations_timed"] for c in coverage)
        == planned["contamx_solver_invocations"],
        "cached_repeats": sum(c["cached_repeats_completed"] for c in coverage) == expect_cached,
        "no_timeouts_or_failures": all(c["observed_status"] == OK for c in red.cells),
        "value_only_when_ok_or_unchanged": numeric_only_when_ok,
        "non_executed_rows_blank": all(
            r["value"] is None for r in results
            if red.status[r["row_id"]]["overall"] not in (OK, UNCHANGED)
        ),
        "smoke_gates_passed": bool(red.gates["passed"]),
        "inputs_unchanged": bool(env.get("inputs_unchanged")),
        "threads_single": set(env["thread_env"].values()) == {"1"},
        "repeats_reproduce_metrics": all(
            c["max_metric_rel_diff"] <= red.criteria["tolerances"]["repeat_metric_rel"]
            and c["distinct_field_sha256"] <= 1
            for c in tables["repeat_consistency.csv"]
        ),
        "tracer_kept": all(
            c["passed"] for c in red.gates["checks"] if c["gate"] == "tracer_closure"
        ),
    }
    return {
        "passed": all(checks.values()), "checks": checks,
        "counts": {"cold_cells": len(timed), "cold_cells_expected": expect_cold,
                   "smoke_cells": sum(c["repeat_kind"] == "smoke" for c in red.cells),
                   "cached_repeats_expected": expect_cached},
        "runner_commit": red.runner_commit,
        "design_commit": red.criteria["design_commit"],
        "input_commit": red.criteria["input_commit"],
    }


def write_sums(out_dir: str) -> None:
    lines = []
    for name in sorted(os.listdir(out_dir)):
        if name == "SHA256SUMS":
            continue
        with _open(os.path.join(out_dir, name), "rb") as fh:
            lines.append(f"{hashlib.sha256(fh.read()).hexdigest()}  {name}\n")
    with _open(os.path.join(out_dir, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def reduce(raw_dir: str, out_dir: str) -> dict[str, Any]:
    """Write the package for one raw directory; returns the audit."""
    red = Reduction(raw_dir)
    prepare_output_directory(out_dir, allowed_roots=_ROOTS)
    raw = timing_raw(red)
    tables = {
        "results_long.csv": (RESULT_COLUMNS, results_long(red)),
        "coverage_observed.csv": (COVERAGE_COLUMNS, coverage_observed(red)),
        "timing_raw.csv": (TIMING_COLUMNS, raw),
        "timing_summary.csv": (SUMMARY_COLUMNS, timing_summary(red, raw)),
        "contrasts.csv": (CONTRAST_COLUMNS, contrasts(red)),
        "reference_baselines.csv": (REFERENCE_COLUMNS, reference_baselines(red)),
        "repeat_consistency.csv": (CONSISTENCY_COLUMNS, repeat_consistency(red)),
    }
    for name, (columns, rows) in tables.items():
        write_csv(os.path.join(out_dir, name), columns, rows)
    with _open(os.path.join(out_dir, "readout_tables.md"), "w", encoding="utf-8") as fh:
        fh.write(readout_markdown(red, tables["timing_summary.csv"][1]))
    verdict = audit(red, {name: rows for name, (_c, rows) in tables.items()})
    with _open(os.path.join(out_dir, "audit.json"), "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for name in RAW_FILES:
        if os.path.abspath(raw_dir) != os.path.abspath(out_dir):
            shutil.copyfile(os.path.join(raw_dir, name), os.path.join(out_dir, name))
    for name in DESIGN_FILES:
        shutil.copyfile(os.path.join(FROZEN_DIR, name), os.path.join(out_dir, name))
    shutil.copyfile(CRITERIA_PATH, os.path.join(out_dir, "canary_criteria.json"))
    write_sums(out_dir)
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, help="directory with the unpacked raw artifact")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    verdict = reduce(args.raw, args.out)
    print(json.dumps(verdict, indent=1, sort_keys=True))
    return 0 if verdict["passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
