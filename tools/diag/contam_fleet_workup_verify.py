#!/usr/bin/env python3
"""Offline verifier of the fleet airflow-workup package. Standard library only.

Run from anywhere: ``python3 verify.py [package_dir]``. It needs no network,
no cloud account and no repository. It checks, in order: the file set and
every SHA-256; the column sets (aggregate fields only); that the row IDs are
the frozen matrix exactly once; the planned counts; that unsupported
quantities are blank with a reason and never a number; the timing phase
labels and repeat counts; and it recomputes every derived table
(``results_long``, ``repeat_consistency``, ``timing_summary``, ``contrasts``,
``reference_baselines``) from the per-repeat aggregate records and compares.
Exit 0 only when every check passes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import sys
import tempfile
from typing import Any

NATIVE = "native_prescribed"
COMMISSIONED = "contamx_commissioned_export"
EXECUTE = "planned_execute"
GOOD = ("ok", "unchanged")
BLOCKS = ("solved_airflow", "downstream_mixing")
UNRESOLVED = ("outdoor_air_total_m3h", "exhaust_total_m3h")
# The corrected canary run (run 2). The earlier run's solve / import split was
# mislabelled; a package carrying any other canary job is refused.
CANARY_RECEIPT = {
    "batch_job_id": "ac1b56e1-2080-40cc-be8f-b8473ceca793",
    "raw_artifact_sha256": "b99690680cd30331d4af0ad9e3afba5543d4499668e19c42205cf272f5a7ac8b",
    "image_digest": "sha256:e59acd8d426a1304387929dd9c91bb85946b28c0c2357eb7a997e7e16a28e0c3",
    "runner_commit": "d06d685011ebc05ebe49ed35aacc43b7f6fc2706",
}
PHASES = {
    NATIVE: {"input_read", "native_construct", "field_reduce", "downstream", "end_to_end",
             "process_total"},
    "contamx": {"input_read", "contamx_export", "contamx_solve", "contamx_import",
                "field_reduce", "downstream", "end_to_end", "process_total"},
}
COLUMNS = {
    "data/results_long.csv": (
        "cohort", "row_id", "hull", "lane", "setting_id", "block", "metric", "value", "unit",
        "observed_status", "reason", "platform_git_tree", "runner_commit"),
    "data/coverage_observed.csv": (
        "cohort", "row_id", "hull", "lane", "setting_id", "planned_status", "observed_status",
        "observed_status_solved_airflow", "observed_status_downstream_mixing", "reason",
        "cold_cells_completed", "solver_invocations_timed", "cached_repeats_completed"),
    "data/timing_raw.csv": (
        "cohort", "row_id", "repeat_kind", "repeat_index", "phase", "wall_ns", "cpu_parent_ns",
        "cpu_child_ns", "censored", "observed_status", "loadavg_1m"),
    "data/timing_summary.csv": (
        "cohort", "row_id", "hull", "lane", "setting_id", "repeat_kind", "phase", "n",
        "timeouts", "wall_median_ns", "wall_min_ns", "wall_max_ns", "wall_iqr_ns",
        "wall_mad_ns", "cpu_parent_median_ns", "cpu_child_median_ns"),
    "data/contrasts.csv": (
        "cohort", "hull", "setting_id", "block", "metric", "unit", "native", "contamx",
        "contamx_minus_native", "contamx_over_native", "native_minus_baseline",
        "contamx_minus_baseline", "native_status", "contamx_status"),
    "data/reference_baselines.csv": (
        "cohort", "hull", "lane", "block", "metric", "unit", "value", "harmonized_value",
        "value_minus_harmonized", "status"),
    "data/repeat_consistency.csv": (
        "cohort", "row_id", "records", "distinct_field_sha256", "max_metric_rel_diff"),
    "data/repeat_metrics.csv": (
        "cohort", "row_id", "repeat_kind", "repeat_index", "block", "metric", "value", "unit",
        "status", "reason", "field_sha256"),
    "data/cohorts.csv": (
        "cohort", "stage", "hulls", "hull_count", "batch_job_id", "job_definition",
        "image_digest", "runner_commit", "attempts", "reporting_attempt", "exit_code", "started_at_ms",
        "stopped_at_ms", "instance_id", "instance_type", "cpu_model", "cpu_affinity",
        "thread_env_all_1", "loadavg_1m_max", "raw_artifact_sha256", "raw_artifact_key",
        "criteria_sha256", "selection_sha256", "contamx_binary_sha256",
        "contamx_archive_sha256", "contamx_version", "inputs_unchanged", "gate_checks",
        "gate_failed", "audit_passed", "audit_checks", "environment_sha256", "job_sha256",
        "gates_sha256", "cells_sha256"),
    "data/gates_summary.csv": ("cohort", "gate", "passed", "failed"),
    "data/code_sha256.csv": ("cohort", "path", "sha256"),
}


EXPECTED_FILE = "EXPECTED.json"
CRITERIA_FILE = "design/canary_criteria.json"
SELECTION_FILE = "design/fleet_selection.json"
SUMS_FILE = "SHA256SUMS"


def _prefix(base: str) -> str:
    return base if base.endswith(os.sep) else base + os.sep


def package_root(path: str, extra_roots: tuple[str, ...] = ()) -> str:
    """Canonical package directory; it must sit under the working directory,
    this script's directory, the temporary directory or a caller's own root."""
    resolved = os.path.realpath(path)
    bases = [os.path.realpath(b) for b in (
        os.getcwd(), os.path.dirname(__file__), tempfile.gettempdir(), *extra_roots)]
    for base in bases:
        if resolved == base or resolved.startswith(_prefix(base)):
            return resolved
    raise SystemExit(f"{path} is outside the working, script and temporary directories")


def inside(root: str, name: str) -> str:
    """Canonical path of a package member; refuses anything outside ``root``."""
    base = os.path.realpath(root)
    resolved = os.path.realpath(os.path.join(base, name))
    if not resolved.startswith(_prefix(base)):
        raise ValueError(f"{name} resolves outside the package")
    return resolved


def read_json(root: str, name: str) -> Any:
    with open(inside(root, name), encoding="utf-8") as fh:
        return json.load(fh)


OTHER_FILES = (
    "README.md", EXPECTED_FILE, "per_hull_readout.md", "verify.py",
    "design/SHA256SUMS", "design/coverage.csv", "design/dry_run_summary.json",
    "design/input_manifest.json", "design/protocol.json", "design/run_matrix.csv",
    CRITERIA_FILE, SELECTION_FILE,
)


class Checks:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append((name, bool(passed), detail))

    def report(self) -> int:
        for name, passed, detail in self.results:
            print(f"{'PASS' if passed else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        failed = [n for n, p, _d in self.results if not p]
        print(f"{len(self.results) - len(failed)} of {len(self.results)} checks passed")
        return 1 if failed else 0


def sha256(root: str, name: str) -> str:
    digest = hashlib.sha256()
    with open(inside(root, name), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(root: str, name: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(inside(root, name), encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def num(text: str) -> float | None:
    return None if text == "" else float(text)


def same(a: float | None, b: float | None) -> bool:
    return a == b if a is None or b is None else a == b or abs(a - b) <= 1e-12 * max(abs(a), abs(b))


def rel_diff(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return abs(a - b) / scale if scale > 0.0 else 0.0


def minus(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


# ── files ─────────────────────────────────────────────────────────────────


def check_files(root: str, checks: Checks) -> bool:
    listed = {}
    with open(inside(root, SUMS_FILE), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.rstrip("\n").split("  ", 1)
            listed[name] = digest
    present = set()
    for folder, _dirs, files in os.walk(root):
        for name in files:
            present.add(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/"))
    present.discard(SUMS_FILE)
    allowed = set(COLUMNS) | set(OTHER_FILES)
    checks.add("file set is exactly the documented set", present == allowed == set(listed),
               f"extra={sorted(present - allowed)} missing={sorted(allowed - present)}")
    bad = [n for n in sorted(present & set(listed)) if sha256(root, n) != listed[n]]
    checks.add("every file matches SHA256SUMS", not bad, f"mismatch={bad}" if bad else "")
    expected = read_json(root, EXPECTED_FILE)
    design_bad = []
    with open(inside(root, "design/SHA256SUMS"), encoding="utf-8") as fh:
        for line in fh:
            digest, name = line.split()
            if sha256(root, "design/" + name) != digest:
                design_bad.append(name)
    checks.add("frozen design files match the design's own SHA256SUMS", not design_bad)
    pins = expected["sha256"]
    pin_bad = [n for n, d in pins.items() if sha256(root, n) != d]
    checks.add("design, criteria and selection match the pinned hashes", not pin_bad, str(pin_bad))
    return present == allowed and not bad


def check_columns(root: str, checks: Checks) -> dict[str, list[dict[str, str]]]:
    tables = {}
    wrong = []
    for name, columns in COLUMNS.items():
        header, rows = read_csv(root, name)
        if tuple(header) != columns:
            wrong.append(name)
        tables[name.split("/")[1][:-4]] = rows
    checks.add("every table has exactly its documented aggregate columns", not wrong, str(wrong))
    return tables


# ── coverage and counts ───────────────────────────────────────────────────


def check_coverage(root: str, t: dict[str, Any], expected: dict[str, Any], checks: Checks) -> None:
    _h, matrix = read_csv(root, "design/run_matrix.csv")
    cov = t["coverage_observed"]
    ids = [r["row_id"] for r in cov]
    checks.add("no duplicate row ID in coverage", len(ids) == len(set(ids)))
    checks.add("row IDs are the frozen matrix exactly once",
               sorted(ids) == sorted(r["row_id"] for r in matrix))
    plan = {r["row_id"]: r for r in matrix}
    checks.add("planned status, hull, lane and setting agree with the matrix", all(
        r["row_id"] in plan and all(plan[r["row_id"]][k] == r[k]
                                    for k in ("hull", "lane", "setting_id", "planned_status"))
        for r in cov))
    executed = [r for r in cov if r["planned_status"] == EXECUTE]
    union = expected["counts"]["union"]
    got = {
        "rows_total": len(cov), "rows_planned_execute": len(executed),
        "rows_executed_ok": sum(r["observed_status"] in GOOD for r in cov),
        "cold_cell_executions": sum(int(r["cold_cells_completed"]) for r in cov),
        "contamx_solver_invocations": sum(int(r["solver_invocations_timed"]) for r in cov),
        "cached_cell_executions": sum(int(r["cached_repeats_completed"]) for r in cov),
    }
    want = {**{k: union[k] for k in got if k in union}, "rows_executed_ok": union["rows_planned_execute"]}
    checks.add("planned counts are met", got == want, f"got={got}")
    checks.add("non-executed rows keep their planned status and a reason", all(
        r["observed_status"] == r["planned_status"] and r["reason"]
        and r["cold_cells_completed"] == "0"
        for r in cov if r["planned_status"] != EXECUTE))
    _h, coverage = read_csv(root, "design/coverage.csv")
    in_scope = sorted(r["platform"] for r in coverage if r["in_scope"] == "1")
    excluded = sorted(r["platform"] for r in coverage if r["in_scope"] != "1")
    checks.add("hulls are the 77 bundled hulls", sorted({r["hull"] for r in cov}) == in_scope
               and len(in_scope) == 77)
    checks.add("the five no-bundle platforms are excluded with a reason",
               excluded == sorted(expected["excluded_no_bundle"]) and len(excluded) == 5)
    cohort_of: dict[str, set[str]] = {}
    for r in cov:
        cohort_of.setdefault(r["hull"], set()).add(r["cohort"])
    declared = {c["cohort"]: sorted(c["hulls"].split(";")) for c in t["cohorts"]}
    observed: dict[str, list[str]] = {}
    for hull, names in cohort_of.items():
        for name in names:
            observed.setdefault(name, []).append(hull)
    checks.add("each hull was measured in exactly one cohort, as declared",
               all(len(v) == 1 for v in cohort_of.values())
               and {k: sorted(v) for k, v in observed.items()} == declared
               and declared == {k: sorted(v) for k, v in expected["cohort_hulls"].items()})
    for name in ("results_long", "timing_raw", "timing_summary", "repeat_consistency",
                 "repeat_metrics"):
        stray = [r for r in t[name] if r["row_id"] not in plan
                 or cohort_of[plan[r["row_id"]]["hull"]] != {r["cohort"]}]
        checks.add(f"{name} joins to the matrix and to its hull's cohort", not stray)
    for name in ("contrasts", "reference_baselines"):
        stray = [r for r in t[name] if cohort_of.get(r["hull"]) != {r["cohort"]}]
        checks.add(f"{name} joins to its hull's cohort", not stray)


def check_cohorts(root: str, t: dict[str, Any], expected: dict[str, Any], checks: Checks) -> None:
    cohorts = t["cohorts"]
    criteria = read_json(root, CRITERIA_FILE)
    selection = read_json(root, SELECTION_FILE)
    selection_sha = sha256(root, SELECTION_FILE)
    rosters = {c["cohort"]: c["hulls"].split(";") for c in cohorts}
    want = {"canary_run2": sorted(criteria["canary"]["hulls"]),
            **{f"fleet_cohort{c['cohort']}": c["hulls"] for c in selection["cohorts"]}}
    checks.add("one corrected canary cohort and eight fleet cohorts, with the frozen rosters",
               rosters == want and len(want) == 9)
    canary = [c for c in cohorts if c["cohort"] == "canary_run2"]
    checks.add("the canary cohort is the corrected run 2, by job, artifact, image and runner",
               len(canary) == 1 and all(canary[0][k] == v for k, v in CANARY_RECEIPT.items()))
    checks.add("fleet cohorts ran under the packaged selection; the canary predates it", all(
        c["selection_sha256"] == ("" if c["stage"] == "canary" else selection_sha)
        for c in cohorts))
    checks.add("every cohort: gates passed, audit passed, inputs unchanged, one thread, exit 0",
               all(c["gate_failed"] == "0" and c["audit_passed"] == "1"
                   and c["inputs_unchanged"] == "1" and c["thread_env_all_1"] == "1"
                   and c["exit_code"] == "0" for c in cohorts))
    # A Spot host can be reclaimed mid-job. The retry starts from nothing in a new
    # container, so all of a cohort's records must come from its last attempt.
    checks.add("every cohort's records come from its last Batch attempt alone",
               all(c["reporting_attempt"] == c["attempts"] for c in cohorts))
    checks.add("one solver binary and one criteria file across cohorts",
               len({c["contamx_binary_sha256"] for c in cohorts}) == 1
               and len({c["criteria_sha256"] for c in cohorts}) == 1)
    checks.add("job IDs and raw artifacts are distinct per cohort",
               len({c["batch_job_id"] for c in cohorts}) == len(cohorts)
               and len({c["raw_artifact_sha256"] for c in cohorts}) == len(cohorts))
    checks.add("cohort identities match the pinned receipt", {
        c["cohort"]: [c["batch_job_id"], c["image_digest"], c["raw_artifact_sha256"]]
        for c in cohorts} == expected["cohort_receipts"])
    gates = {}
    for g in t["gates_summary"]:
        gates.setdefault(g["cohort"], [0, 0])
        gates[g["cohort"]][0] += int(g["passed"])
        gates[g["cohort"]][1] += int(g["failed"])
    checks.add("gate summary sums to each cohort's gate count with no failure", all(
        gates[c["cohort"]] == [int(c["gate_checks"]), 0] for c in cohorts))


# ── values ────────────────────────────────────────────────────────────────


def check_blanks(t: dict[str, Any], checks: Checks) -> None:
    results = t["results_long"]
    keys = [(r["row_id"], r["block"], r["metric"]) for r in results]
    checks.add("one result per row, block and metric", len(keys) == len(set(keys)))
    checks.add("a value appears only with status ok or unchanged",
               all(r["observed_status"] in GOOD for r in results if r["value"] != ""))
    checks.add("every blank carries a status that is not ok, and a reason", all(
        r["observed_status"] not in GOOD and r["reason"] for r in results if r["value"] == ""))
    unresolved = [r for r in results if r["lane"] != NATIVE and r["block"] == "solved_airflow"
                  and r["metric"] in UNRESOLVED]
    checks.add("solver-unresolved outdoor-air and exhaust totals are blank, not zero",
               bool(unresolved) and all(r["value"] == "" and r["reason"] for r in unresolved))
    checks.add("blocks are solved_airflow and downstream_mixing only",
               {r["block"] for r in results} == set(BLOCKS))


def _representative(reps: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    """Metrics of the last measured repeat (the smoke cell if nothing was timed)."""
    for kinds in (("measured",), ("warmup", "smoke")):
        chosen = [r for r in reps if r["repeat_kind"] in kinds]
        if chosen:
            last = max(int(r["repeat_index"]) for r in chosen) if kinds == ("measured",) else None
            if last is None:
                pick = (chosen[-1]["repeat_kind"], chosen[-1]["repeat_index"])
            else:
                pick = ("measured", str(last))
            return {(r["block"], r["metric"]): r for r in chosen
                    if (r["repeat_kind"], r["repeat_index"]) == pick}
    return {}


def _by_row(t: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    by_row: dict[str, list[dict[str, str]]] = {}
    for r in t["repeat_metrics"]:
        by_row.setdefault(r["row_id"], []).append(r)
    return by_row


def _repeat_shape_ok(reps: list[dict[str, str]]) -> bool:
    kinds: dict[str, set[str]] = {}
    for r in reps:
        kinds.setdefault(r["repeat_kind"], set()).add(r["repeat_index"])
    return {k: len(v) for k, v in kinds.items()} == {"smoke": 1, "warmup": 1, "measured": 5}


def _status_wrong(r: dict[str, str], metrics: dict[Any, dict[str, str]],
                  base: dict[Any, dict[str, str]] | None, tol: float) -> bool:
    """Whether a result's ok / unchanged status disagrees with its lane baseline."""
    m = metrics[(r["block"], r["metric"])]
    if m["status"] != "ok":
        return r["observed_status"] != m["status"]
    moved = r["setting_id"] == "baseline" or base is None or any(
        v["value"] != "" and base[k]["value"] != ""
        and rel_diff(float(v["value"]), float(base[k]["value"])) > tol
        for k, v in metrics.items() if k[0] == r["block"])
    return r["observed_status"] != ("ok" if moved else "unchanged")


def check_recompute_results(t: dict[str, Any], tol: dict[str, float], checks: Checks) -> None:
    by_row = _by_row(t)
    rep = {row_id: _representative(reps) for row_id, reps in by_row.items()}
    executed = {r["row_id"] for r in t["coverage_observed"] if r["planned_status"] == EXECUTE}
    checks.add("per-repeat records exist for exactly the executed rows", set(rep) == executed)
    checks.add("each executed row has 1 smoke, 1 warm-up and 5 measured repeats",
               all(_repeat_shape_ok(reps) for reps in by_row.values()))
    have = {(r["row_id"], r["block"], r["metric"]) for r in t["results_long"]
            if r["row_id"] in rep}
    want = {(row_id, *key) for row_id, metrics in rep.items() for key in metrics}
    checks.add("results_long carries every metric of every executed row, and no other",
               have == want, f"missing={len(want - have)} extra={len(have - want)}")
    per_lane: dict[bool, set[tuple[str, str]]] = {}
    for r in t["results_long"]:
        per_lane.setdefault(r["lane"] == NATIVE, set()).add((r["block"], r["metric"]))
    rows: dict[str, set[tuple[str, str]]] = {}
    lane_of = {}
    for r in t["results_long"]:
        rows.setdefault(r["row_id"], set()).add((r["block"], r["metric"]))
        lane_of[r["row_id"]] = r["lane"] == NATIVE
    covered = {r["row_id"] for r in t["coverage_observed"]}
    checks.add("every matrix row, executed or not, lists its lane's full metric set",
               set(rows) == covered and all(m == per_lane[lane_of[i]] for i, m in rows.items()))
    wrong_value = wrong_status = 0
    for r in t["results_long"]:
        metrics = rep.get(r["row_id"])
        m = (metrics or {}).get((r["block"], r["metric"]))
        if m is None:
            wrong_value += r["value"] != ""
            continue
        wrong_value += (r["value"] != (m["value"] if m["status"] == "ok" else "")) or r["unit"] != m["unit"]
        base = rep.get("|".join([*r["row_id"].split("|")[:2], "baseline"]))
        wrong_status += _status_wrong(r, metrics, base, tol["unchanged_rel"])
    checks.add("results_long values are the last measured repeat of each row", wrong_value == 0,
               f"{wrong_value} differ")
    checks.add("ok / unchanged statuses recompute against each lane's own baseline",
               wrong_status == 0, f"{wrong_status} differ")
    check_recompute_consistency(t, by_row, tol, checks)


def _consistency_wrong(c: dict[str, str], reps: list[dict[str, str]], limit: float) -> bool:
    cells: dict[tuple[str, str], dict[tuple[str, str], dict[str, str]]] = {}
    for r in reps:
        cells.setdefault((r["repeat_kind"], r["repeat_index"]), {})[(r["block"], r["metric"])] = r
    first = next(iter(cells.values()))
    worst = max((rel_diff(float(v["value"]), float(first[k]["value"]))
                 for cell in cells.values() for k, v in cell.items()
                 if v["value"] != "" and first[k]["value"] != ""), default=0.0)
    shas = {r["field_sha256"] for r in reps} - {""}
    return (int(c["records"]) != len(cells) or int(c["distinct_field_sha256"]) != len(shas)
            or not same(float(c["max_metric_rel_diff"]), worst) or worst > limit or len(shas) > 1)


def check_recompute_consistency(t: dict[str, Any], by_row: dict[str, list[dict[str, str]]],
                                tol: dict[str, float], checks: Checks) -> None:
    bad = sum(_consistency_wrong(c, by_row[c["row_id"]], tol["repeat_metric_rel"])
              for c in t["repeat_consistency"])
    checks.add("repeat_consistency recomputes and every repeat reproduces its row's metrics",
               bad == 0 and len(t["repeat_consistency"]) == len(by_row), f"{bad} differ")


def _value(index: dict[tuple[str, str, str], dict[str, str]], row_id: str, block: str,
           metric: str) -> tuple[float | None, str]:
    r = index.get((row_id, block, metric))
    if r is None:
        return None, "missing"
    return num(r["value"]), r["observed_status"]


def check_recompute_contrasts(t: dict[str, Any], checks: Checks) -> None:
    index = {(r["row_id"], r["block"], r["metric"]): r for r in t["results_long"]}
    bad = 0
    for c in t["contrasts"]:
        hull, setting, block, metric = c["hull"], c["setting_id"], c["block"], c["metric"]
        native, _ = _value(index, f"{hull}|{NATIVE}|{setting}", block, metric)
        contamx, _ = _value(index, f"{hull}|{COMMISSIONED}|{setting}", block, metric)
        n_base, _ = _value(index, f"{hull}|{NATIVE}|baseline", block, metric)
        c_base, _ = _value(index, f"{hull}|{COMMISSIONED}|baseline", block, metric)
        diff = minus(contamx, native)
        want = {"native": native, "contamx": contamx, "contamx_minus_native": diff,
                "contamx_over_native": contamx / native if diff is not None and native else None,
                "native_minus_baseline": minus(native, n_base),
                "contamx_minus_baseline": minus(contamx, c_base)}
        bad += not all(same(num(c[k]), v) for k, v in want.items())
    rows = sum(1 for r in t["results_long"] if r["lane"] == COMMISSIONED)
    checks.add("contrasts recompute from results_long (harmonized ContamX vs native, and each "
               "lane vs its own baseline)", bad == 0 and len(t["contrasts"]) == rows,
               f"{bad} differ")
    bad = 0
    for r in t["reference_baselines"]:
        value, _ = _value(index, f"{r['hull']}|{r['lane']}|baseline", r["block"], r["metric"])
        harmonized, _ = _value(index, f"{r['hull']}|{COMMISSIONED}|baseline", r["block"], r["metric"])
        bad += not (same(num(r["value"]), value) and same(num(r["harmonized_value"]), harmonized)
                    and same(num(r["value_minus_harmonized"]), minus(value, harmonized))
                    and r["lane"] not in (NATIVE, COMMISSIONED))
    refs = {(r["hull"], r["lane"]) for r in t["reference_baselines"]}
    checks.add("the two untouched as-shipped baselines are separate references that recompute",
               bad == 0 and len({lane for _h, lane in refs}) == 2
               and len({h for h, _l in refs}) == 77, f"{bad} differ")


# ── timing ────────────────────────────────────────────────────────────────


def _spread(values: list[int]) -> dict[str, float]:
    median = statistics.median(values)
    iqr = 0.0
    if len(values) >= 2:
        q = statistics.quantiles(values, n=4, method="inclusive")
        iqr = q[2] - q[0]
    return {"wall_median_ns": median, "wall_min_ns": min(values), "wall_max_ns": max(values),
            "wall_iqr_ns": iqr, "wall_mad_ns": statistics.median([abs(v - median) for v in values])}


def _phases(lane: str) -> set[str]:
    return PHASES[NATIVE if lane == NATIVE else "contamx"]


def _label_wrong(r: dict[str, str], lane: dict[str, str]) -> bool:
    if r["repeat_kind"] == "cached":
        return r["phase"] != "downstream"
    return r["repeat_kind"] not in ("warmup", "measured") or r["phase"] not in _phases(lane[r["row_id"]])


def _shape_wrong(row_id: str, lane: str, count: dict[tuple[str, str, str], int]) -> bool:
    return count.get((row_id, "cached", "downstream")) != 5 or any(
        count.get((row_id, "warmup", p)) != 1 or count.get((row_id, "measured", p)) != 5
        for p in _phases(lane))


def _summary_wrong(s: dict[str, str], items: list[dict[str, str]]) -> bool:
    want: dict[str, Any] = {"n": len(items), **_spread([int(i["wall_ns"]) for i in items])}
    for column, source in (("cpu_parent_median_ns", "cpu_parent_ns"),
                           ("cpu_child_median_ns", "cpu_child_ns")):
        values = [int(i[source]) for i in items if i[source] != ""]
        want[column] = statistics.median(values) if values else None
    return (not all(same(num(s[k]), None if v is None else float(v)) for k, v in want.items())
            or len({i["cohort"] for i in items}) != 1 or s["cohort"] != items[0]["cohort"])


def check_timing(t: dict[str, Any], checks: Checks) -> None:
    lane = {r["row_id"]: r["lane"] for r in t["coverage_observed"]}
    executed = {r["row_id"] for r in t["coverage_observed"] if r["planned_status"] == EXECUTE}
    raw = t["timing_raw"]
    checks.add("timing phase labels are the documented ones for each lane",
               not any(_label_wrong(r, lane) for r in raw))
    count: dict[tuple[str, str, str], int] = {}
    for r in raw:
        key = (r["row_id"], r["repeat_kind"], r["phase"])
        count[key] = count.get(key, 0) + 1
    checks.add("every executed row has 1 warm-up, 5 measured and 5 cached timings per phase",
               {k[0] for k in count} == executed
               and not any(_shape_wrong(i, lane[i], count) for i in executed))
    solved = {k[0] for k in count if k[2] == "contamx_solve"}
    checks.add("native rows have no solver phase; ContamX solve is timed apart from import",
               all((i in solved) == (lane[i] != NATIVE) for i in executed))
    checks.add("no timeout, no censored sample, every timed cell ok",
               all(r["censored"] == "0" and r["observed_status"] == "ok" for r in raw))
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for r in raw:
        if r["repeat_kind"] != "warmup":
            groups.setdefault((r["row_id"], r["repeat_kind"], r["phase"]), []).append(r)
    summary = {(s["row_id"], s["repeat_kind"], s["phase"]): s for s in t["timing_summary"]}
    bad = int(set(summary) != set(groups))
    bad += sum(_summary_wrong(summary[key], items) for key, items in groups.items()
               if key in summary)
    checks.add("timing_summary recomputes from timing_raw; no summary pools two cohorts",
               bad == 0, f"{bad} differ")


def verify(root: str, extra_roots: tuple[str, ...] = ()) -> int:
    root = package_root(root, extra_roots)
    checks = Checks()
    if not check_files(root, checks):
        return checks.report()
    tables = check_columns(root, checks)
    expected = read_json(root, EXPECTED_FILE)
    criteria = read_json(root, CRITERIA_FILE)
    stages = (
        ("coverage", lambda: check_coverage(root, tables, expected, checks)),
        ("cohorts", lambda: check_cohorts(root, tables, expected, checks)),
        ("blanks", lambda: check_blanks(tables, checks)),
        ("results", lambda: check_recompute_results(tables, criteria["tolerances"], checks)),
        ("contrasts", lambda: check_recompute_contrasts(tables, checks)),
        ("timing", lambda: check_timing(tables, checks)),
    )
    for name, stage in stages:
        # A table damaged badly enough to break a join is a failure, not a crash.
        try:
            stage()
        except (KeyError, ValueError, IndexError, StopIteration) as exc:
            checks.add(f"{name} checks could run to completion", False, repr(exc))
    return checks.report()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    raise SystemExit(verify(sys.argv[1] if len(sys.argv) > 1 else here))
