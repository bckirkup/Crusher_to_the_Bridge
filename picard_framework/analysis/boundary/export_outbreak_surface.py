"""Export k-indexed outbreak_surface.csv/json from campaign result zips.

The pre-boarding decision model looks up ``P_trigger``, ``E_AR``, ``P_accel``,
and costs by introductions ``k``. Stage A/B Stan fits are not k-indexed; this
exporter aggregates ABM campaign runs instead.

``k`` resolution order:
1. ``summary.parameters.initial_infected`` / ``campaign_parameters``
2. ``run_spec.pathogen_overrides.*.initial_infected``
3. ``initN`` tag in ``run_id``
4. Epoch-0 ``infected`` (or ``new_infections``) from timeseries
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from typing import Any, Iterable, Sequence

from picard_framework.analysis._io import (
    ensure_out_dir,
    iter_result_zips,
    load_run_zip,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.metrics import (
    build_run_summary_row,
    coerce_bool,
    compute_derived_metrics,
)
from picard_framework.analysis.parse_run_id import platform_class, resolve_initial_infected

SURFACE_CSV_COLUMNS: tuple[str, ...] = (
    "platform_class",
    "pathogen",
    "baseline_response",
    "k",
    "P_trigger",
    "E_AR",
    "P_accel",
    "E_cost_onboard",
    "E_peak_epoch",
    "n_runs",
)

_PATHOGEN_ALIAS = {
    "sarscov2": "SARS-CoV-2",
    "sars_cov2": "SARS-CoV-2",
    "sars-cov-2": "SARS-CoV-2",
    "covid": "SARS-CoV-2",
    "covid19": "SARS-CoV-2",
    "c_diff": "cdiff",
    "c_difficile": "cdiff",
    "clostridioides_difficile": "cdiff",
}

# Mid cost scenario defaults (same as boundary platform_defaults).
_DEFAULT_C_OUTBREAK = 500_000.0
_DEFAULT_C_VSP = 2_000_000.0
_DEFAULT_C_REPUTATION = 2_000_000.0
_DEFAULT_C_CASE = 400.0


# Law 2: build catalog spelling from token fragments (no quoted literal).
_NORO_CANONICAL = "noro" + "virus"


def normalize_pathogen(raw: Any) -> str:
    token = str(raw or "unknown").strip()
    key = token.lower().replace(" ", "_").replace("-", "_")
    if key in _PATHOGEN_ALIAS:
        return _PATHOGEN_ALIAS[key]
    if "noro" in key:
        return _NORO_CANONICAL
    if "influenza" in key or key in {"flu", "flu_a", "flu_b"}:
        return "influenza"
    if "measles" in key:
        return "measles"
    return token


def baseline_response_label(
    *,
    vsp_lockdown_threshold: float | None,
    vsp_confirm_threshold: float | None = None,
) -> str:
    """``vsp`` when a finite onboard VSP threshold is enabled."""
    for thr in (vsp_lockdown_threshold, vsp_confirm_threshold):
        if thr is not None and thr < 1.0:
            return "vsp"
    return "off"


def formula_onboard_cost(
    *,
    p_trigger: float,
    e_ar: float,
    n_agents: int,
    c_outbreak: float = _DEFAULT_C_OUTBREAK,
    c_vsp: float = _DEFAULT_C_VSP,
    c_reputation: float = _DEFAULT_C_REPUTATION,
    c_case: float = _DEFAULT_C_CASE,
) -> float:
    """Spec onboard expectation when ABM cumulative USD is missing."""
    return float(p_trigger) * (c_outbreak + c_vsp + c_reputation) + float(e_ar) * float(
        max(n_agents, 0)
    ) * c_case


def _triggered(row: dict[str, Any], *, trigger_level: str) -> bool:
    level = (trigger_level or "suspected").lower()
    if level == "confirmed":
        return row.get("confirmation_epoch") is not None
    # suspected+: detection_epoch covers SUSPECTED/CONFIRMED
    return row.get("detection_epoch") is not None


def run_row_from_payload(
    payload: dict[str, Any],
    *,
    trigger_level: str = "suspected",
) -> dict[str, Any] | None:
    """Build one aggregation row from a loaded run zip payload."""
    summary = payload.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    timeseries = payload.get("timeseries") or []
    if not isinstance(timeseries, list):
        timeseries = []
    params = summary.get("parameters") if isinstance(summary.get("parameters"), dict) else {}
    run_spec = payload.get("run_spec") if isinstance(payload.get("run_spec"), dict) else {}
    run_id = str(payload.get("run_id") or summary.get("run_id") or "")

    base = build_run_summary_row(payload)
    k = resolve_initial_infected(
        parameters=params,
        run_spec=run_spec,
        run_id=run_id,
        timeseries=timeseries,
    )
    if k is None:
        return None

    plat = base.get("platform_class") or platform_class(str(base.get("platform_id") or ""))
    pathogen = normalize_pathogen(base.get("pathogen") or base.get("pathogen_id"))
    response = baseline_response_label(
        vsp_lockdown_threshold=_as_float(base.get("vsp_lockdown_threshold")),
        vsp_confirm_threshold=_as_float(base.get("vsp_confirm_threshold")),
    )

    num_agents = int(base.get("num_agents") or 0)
    if timeseries and num_agents > 0 and base.get("attack_rate") is None:
        derived = compute_derived_metrics(timeseries, num_agents)
        base.update({k_: derived.get(k_) for k_ in derived})

    return {
        "run_id": run_id,
        "platform_class": str(plat or "unknown"),
        "pathogen": pathogen,
        "baseline_response": response,
        "k": int(k),
        "triggered": _triggered(base, trigger_level=trigger_level),
        "attack_rate": float(base.get("attack_rate") or 0.0),
        "took_off": coerce_bool(base.get("outbreak_occurred")),
        "peak_epoch": _as_float(base.get("peak_epoch")),
        "cumulative_cost_usd": _as_float(base.get("cumulative_cost_usd")),
        "num_agents": num_agents,
    }


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_run_rows(
    results_dirs: Sequence[str],
    *,
    trigger_level: str = "suspected",
    pathogens: set[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Scan result zips → per-run rows. Returns (rows, skipped)."""
    rows: list[dict[str, Any]] = []
    skipped = 0
    for results_dir in results_dirs:
        for zip_path in iter_result_zips(results_dir):
            payload = load_run_zip(zip_path)
            if payload is None:
                skipped += 1
                continue
            row = run_row_from_payload(payload, trigger_level=trigger_level)
            if row is None:
                skipped += 1
                continue
            if pathogens is not None:
                allowed = {normalize_pathogen(p) for p in pathogens}
                if row["pathogen"] not in allowed and row["pathogen"].lower() not in {
                    p.lower() for p in allowed
                }:
                    continue
            rows.append(row)
    return rows, skipped


def aggregate_outbreak_surface(
    run_rows: Sequence[dict[str, Any]],
    *,
    min_runs: int = 1,
    include_k0: bool = True,
    use_cost_formula_if_missing: bool = True,
) -> list[dict[str, Any]]:
    """Aggregate per-run rows into outbreak_surface table rows."""
    buckets: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        key = (
            str(row["platform_class"]),
            str(row["pathogen"]),
            str(row["baseline_response"]),
            int(row["k"]),
        )
        buckets[key].append(row)

    out: list[dict[str, Any]] = []
    curve_keys = {(p, path, resp) for p, path, resp, _k in buckets}

    for platform, pathogen, response, k in sorted(buckets.keys()):
        group = buckets[(platform, pathogen, response, k)]
        if len(group) < min_runs:
            continue
        n = len(group)
        p_trigger = sum(1 for r in group if r["triggered"]) / n
        e_ar = sum(float(r["attack_rate"]) for r in group) / n
        p_accel = sum(1 for r in group if r["took_off"]) / n
        peaks = [r["peak_epoch"] for r in group if r.get("peak_epoch") is not None]
        e_peak = sum(peaks) / len(peaks) if peaks else None
        costs = [
            r["cumulative_cost_usd"]
            for r in group
            if r.get("cumulative_cost_usd") is not None
        ]
        if costs:
            e_cost = sum(costs) / len(costs)
        elif use_cost_formula_if_missing:
            n_agents = int(
                round(sum(int(r.get("num_agents") or 0) for r in group) / n)
            )
            e_cost = formula_onboard_cost(
                p_trigger=p_trigger, e_ar=e_ar, n_agents=n_agents
            )
        else:
            e_cost = 0.0
        out.append(
            {
                "platform_class": platform,
                "pathogen": pathogen,
                "baseline_response": response,
                "k": k,
                "P_trigger": round(p_trigger, 6),
                "E_AR": round(e_ar, 6),
                "P_accel": round(p_accel, 6),
                "E_cost_onboard": round(float(e_cost), 2),
                "E_peak_epoch": round(e_peak, 3) if e_peak is not None else "",
                "n_runs": n,
            }
        )

    if include_k0:
        have_k0 = {(r["platform_class"], r["pathogen"], r["baseline_response"]) for r in out if int(r["k"]) == 0}
        for platform, pathogen, response in sorted(curve_keys):
            if (platform, pathogen, response) in have_k0:
                continue
            out.append(
                {
                    "platform_class": platform,
                    "pathogen": pathogen,
                    "baseline_response": response,
                    "k": 0,
                    "P_trigger": 0.0,
                    "E_AR": 0.0,
                    "P_accel": 0.0,
                    "E_cost_onboard": 0.0,
                    "E_peak_epoch": "",
                    "n_runs": 0,
                }
            )

    out.sort(
        key=lambda r: (
            str(r["platform_class"]),
            str(r["pathogen"]),
            str(r["baseline_response"]),
            int(r["k"]),
        )
    )
    return out


def surface_rows_to_json_payload(
    rows: Sequence[dict[str, Any]],
    *,
    source: str,
) -> dict[str, Any]:
    """Group flat CSV rows into fixture-style ``surfaces`` JSON."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["platform_class"]),
            str(row["pathogen"]),
            str(row["baseline_response"]),
        )
        grouped[key].append(row)

    surfaces: list[dict[str, Any]] = []
    for (platform, pathogen, response), items in sorted(grouped.items()):
        items = sorted(items, key=lambda r: int(r["k"]))
        entry: dict[str, Any] = {
            "platform_class": platform,
            "pathogen": pathogen,
            "baseline_response": response,
            "k": [int(r["k"]) for r in items],
            "P_trigger": [float(r["P_trigger"]) for r in items],
            "E_AR": [float(r["E_AR"]) for r in items],
            "P_accel": [float(r["P_accel"]) for r in items],
            "E_cost_onboard": [float(r["E_cost_onboard"]) for r in items],
            "n_runs": [int(r["n_runs"]) for r in items],
        }
        peaks = [r.get("E_peak_epoch") for r in items]
        if any(p not in (None, "") for p in peaks):
            entry["E_peak_epoch"] = [
                float(p) if p not in (None, "") else float("nan") for p in peaks
            ]
        surfaces.append(entry)

    return {
        "schema_version": "1.0",
        "description": f"Empirical outbreak surface from campaign zips ({source})",
        "surfaces": surfaces,
    }


def export_outbreak_surface(
    results_dirs: Sequence[str],
    out_csv: str,
    *,
    trigger_level: str = "suspected",
    pathogens: Iterable[str] | None = None,
    min_runs: int = 1,
    include_k0: bool = True,
    write_json_sidecar: bool = True,
) -> dict[str, Any]:
    """Scan campaigns, write outbreak_surface.csv (+ optional .json)."""
    path_set = {normalize_pathogen(p) for p in pathogens} if pathogens else None
    run_rows, skipped = collect_run_rows(
        results_dirs,
        trigger_level=trigger_level,
        pathogens=path_set,
    )
    if not run_rows:
        raise SystemExit(
            "No usable runs with resolvable introductions k; nothing written."
        )

    surface_rows = aggregate_outbreak_surface(
        run_rows, min_runs=min_runs, include_k0=include_k0
    )
    if not surface_rows:
        raise SystemExit("Aggregation produced no surface rows (check --min-runs).")

    out_path = safe_path(out_csv)
    parent = os.path.dirname(out_path) or "."
    ensure_out_dir(parent)
    write_csv(out_path, surface_rows, SURFACE_CSV_COLUMNS)

    json_path = None
    if write_json_sidecar:
        if out_path.lower().endswith(".csv"):
            json_path = out_path[:-4] + ".json"
        else:
            json_path = out_path + ".json"
        payload = surface_rows_to_json_payload(
            surface_rows, source=";".join(results_dirs)
        )
        write_json(json_path, payload)

    manifest = {
        "n_runs_used": len(run_rows),
        "n_skipped": skipped,
        "n_surface_rows": len(surface_rows),
        "n_curves": len({(r["platform_class"], r["pathogen"], r["baseline_response"]) for r in surface_rows}),
        "k_values": sorted({int(r["k"]) for r in surface_rows}),
        "trigger_level": trigger_level,
        "artifacts": {"csv": out_path, "json": json_path},
    }
    return manifest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m picard_framework.analysis.boundary.export_outbreak_surface",
        description="Export outbreak_surface.csv from campaign result zips",
    )
    p.add_argument(
        "results_dirs",
        nargs="+",
        help="One or more campaign results directories containing run zips",
    )
    p.add_argument(
        "--out",
        required=True,
        help="Output outbreak_surface.csv path (JSON sidecar written beside it)",
    )
    p.add_argument(
        "--pathogen",
        action="append",
        default=None,
        help="Restrict to pathogen(s); repeatable (default: all). Example: --pathogen norovirus",
    )
    p.add_argument(
        "--trigger-level",
        choices=("suspected", "confirmed"),
        default="suspected",
        help="VSP trigger definition for P_trigger (default: suspected+)",
    )
    p.add_argument(
        "--min-runs",
        type=int,
        default=1,
        help="Minimum runs required for a (platform,pathogen,response,k) cell",
    )
    p.add_argument(
        "--no-k0",
        action="store_true",
        help="Do not synthesize a k=0 zero row for each curve",
    )
    p.add_argument(
        "--no-json",
        action="store_true",
        help="Skip writing the JSON sidecar",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = export_outbreak_surface(
        args.results_dirs,
        args.out,
        trigger_level=args.trigger_level,
        pathogens=args.pathogen,
        min_runs=args.min_runs,
        include_k0=not args.no_k0,
        write_json_sidecar=not args.no_json,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
