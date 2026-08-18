"""Post-process sentinel_synthetic_recovery_v1 zips: extract, Stan, recovery table.

Usage::

    python -m picard_framework.analysis.sentinel_recovery_postprocess \\
      results/sentinel_synthetic_recovery_v1 \\
      --out results/sentinel_synthetic_recovery_v1/analysis
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import defaultdict
from typing import Any, Mapping

from picard_framework.analysis._fit_exit import (
    add_allow_skipped_argument,
    fit_exit_code,
    worst_exit_code,
)
from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    iter_result_zips,
    load_zip_json,
    read_json,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel_recovery_priors import recovery_fleet_priors
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sampler_options import SamplerOptions
from picard_framework.analysis.stan.fit_sentinel_fleet import fit_sentinel_fleet
from simulation_utils.paths import validate_path_component, validated_open

_PORT_ALIASES = {"miami": "USMIA"}
_HOME_PORT_TRUTH = 0.0
_PORT_DAY_TYPE = "port_day"
RECOVERY_COLUMNS = (
    "cell_id",
    "hazard_profile",
    "fleet_config",
    "R_onboard_true",
    "n_voyages",
    "fit_status",
    "port_id",
    "lambda_true",
    "lambda_mean",
    "lambda_q05",
    "lambda_q95",
    "lambda_covered",
    "R_mean",
    "R_q05",
    "R_q95",
    "R_covered",
)


def r_onboard_tag(value: float) -> str:
    """Match campaign run-id fragments, e.g. 0.5 → R0p5."""
    return "R" + str(float(value)).replace(".", "p")


def cell_id(hazard: str, fleet: str, r_onboard: float) -> str:
    """Filesystem-safe id for one (hazard × fleet × R) recovery cell."""
    return validate_path_component(
        f"{hazard}__{fleet}__{r_onboard_tag(r_onboard)}",
        label="cell_id",
    )


def _posix_join(*parts: str) -> str:
    """Join path segments with ``/`` so manifests are portable to Linux."""
    chunks: list[str] = []
    for part in parts:
        chunks.extend(
            piece for piece in str(part).replace("\\", "/").split("/") if piece
        )
    return "/".join(chunks)


def interval_covers(true: float, q05: float, q95: float) -> bool:
    """True when ``true`` lies in the closed 90% interval."""
    return float(q05) <= float(true) <= float(q95)


def remap_port_id(port_id: str) -> str:
    """Map line-list slugs onto itinerary UN-LOCODEs."""
    return _PORT_ALIASES.get(str(port_id), str(port_id))


def remap_hours(hours: dict[str, Any] | None) -> dict[str, float]:
    """Merge aliased port keys, summing hours."""
    out: dict[str, float] = {}
    for key, value in (hours or {}).items():
        port = remap_port_id(str(key))
        out[port] = out.get(port, 0.0) + float(value)
    return out


def port_day_ids(voyage: dict[str, Any]) -> set[str]:
    """UN-LOCODEs the fleet model treats as port calls (not home-port days)."""
    ids: set[str] = set()
    for stop in voyage.get("itinerary") or []:
        if not isinstance(stop, dict):
            continue
        if str(stop.get("type") or "") != _PORT_DAY_TYPE:
            continue
        port_id = remap_port_id(str(stop.get("port_id") or "").strip())
        if port_id:
            ids.add(port_id)
    return ids


def _filter_port_map(mapping: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if key in allowed}


def _allowed_or_all(mapping: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    return mapping if not allowed else _filter_port_map(mapping, allowed)


def _remap_truth(
    records: list[Any] | None,
    allowed: set[str],
) -> list[dict[str, Any]]:
    truth: list[dict[str, Any]] = []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        item = dict(rec)
        item["port_id"] = remap_port_id(str(item.get("port_id") or ""))
        if allowed and item["port_id"] not in allowed:
            continue
        truth.append(item)
    return truth


def remap_exposure(totals: dict[str, Any] | None) -> dict[str, Any]:
    """Merge aliased exposure cells by summing numeric fields."""
    out: dict[str, dict[str, float]] = {}
    for key, cell in (totals or {}).items():
        if not isinstance(cell, dict):
            continue
        port = remap_port_id(str(key))
        acc = out.setdefault(
            port,
            {
                "person_hours_passenger": 0.0,
                "person_hours_crew": 0.0,
                "n_passengers_ashore": 0.0,
                "n_crew_ashore": 0.0,
            },
        )
        for field, value in cell.items():
            acc[str(field)] = acc.get(str(field), 0.0) + float(value)
        out[port] = acc
    return out


def prepare_observations(
    raw: dict[str, Any],
    run_id: str,
    allowed_ports: set[str] | None = None,
) -> dict[str, Any]:
    """Unique ship/voyage ids plus itinerary port-day keys for the fitters."""
    payload = dict(raw)
    payload["voyage_id"] = run_id
    payload["ship_id"] = run_id
    allowed = allowed_ports or set()
    payload["clinical_cases"] = [
        {
            **case,
            "hours_ashore": _allowed_or_all(remap_hours(case.get("hours_ashore")), allowed),
        }
        for case in (raw.get("clinical_cases") or [])
        if isinstance(case, dict)
    ]
    payload["exposure_totals"] = _allowed_or_all(
        remap_exposure(raw.get("exposure_totals")), allowed,
    )
    truth = _remap_truth(raw.get("truth_introductions"), allowed)
    if truth:
        payload["truth_introductions"] = truth
    return payload


def voyage_record_from_zip(zip_path: str) -> dict[str, Any] | None:
    """Pull one voyage's fit inputs from a campaign zip."""
    summary = load_zip_json(zip_path, "summary.json")
    spec = load_zip_json(zip_path, "run_spec.json")
    observations = load_zip_json(zip_path, "sentinel_line_list.json")
    if not isinstance(summary, dict) or not isinstance(spec, dict):
        return None
    if not isinstance(observations, dict):
        return None
    params = summary.get("parameters")
    if not isinstance(params, dict):
        return None
    run_id = str(params.get("run_id") or "")
    voyage = (spec.get("config_overrides") or {}).get("voyage")
    if not run_id or not isinstance(voyage, dict):
        return None
    return {
        "run_id": run_id,
        "params": params,
        "itinerary": {"schema_version": "1.0", "voyage": voyage},
        "observations": prepare_observations(
            observations, run_id, port_day_ids(voyage),
        ),
    }


def cell_key(params: dict[str, Any]) -> tuple[str, str, float]:
    """Grouping key for one recovery cell."""
    return (
        str(params.get("hazard_profile") or "unknown"),
        str(params.get("fleet_config") or "unknown"),
        float(params.get("R_onboard") or 0.0),
    )


def extract_voyages(results_dir: str, out_dir: str) -> dict[str, list[dict[str, Any]]]:
    """Write per-voyage JSON and return voyages grouped by cell id."""
    voyages_root = ensure_out_dir(os.path.join(out_dir, "voyages"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for zip_path in iter_result_zips(results_dir):
        rec = voyage_record_from_zip(zip_path)
        if rec is None:
            continue
        run_id = validate_path_component(rec["run_id"], label="run_id")
        dest = ensure_out_dir(os.path.join(voyages_root, run_id))
        write_json(os.path.join(dest, "itinerary.json"), rec["itinerary"])
        write_json(os.path.join(dest, "observations.json"), rec["observations"])
        write_json(os.path.join(dest, "meta.json"), rec["params"])
        hazard, fleet, r_val = cell_key(rec["params"])
        cid = cell_id(hazard, fleet, r_val)
        grouped[cid].append(
            {
                "run_id": run_id,
                "hazard_profile": hazard,
                "fleet_config": fleet,
                "R_onboard": r_val,
                "port_hazards": dict(rec["params"].get("port_hazards") or {}),
                "itinerary": os.path.join("voyages", run_id, "itinerary.json"),
                "observations": os.path.join("voyages", run_id, "observations.json"),
            },
        )
    write_json(
        os.path.join(out_dir, "cells.json"),
        {cid: [v["run_id"] for v in voyages] for cid, voyages in grouped.items()},
    )
    return grouped


def write_cell_manifests(
    grouped: dict[str, list[dict[str, Any]]],
    out_dir: str,
) -> list[dict[str, Any]]:
    """Write one fleet manifest per cell; return cell descriptors."""
    manifest_root = ensure_out_dir(os.path.join(out_dir, "manifests"))
    cells: list[dict[str, Any]] = []
    for cid, voyages in sorted(grouped.items()):
        rels = [
            {"itinerary": v["itinerary"], "observations": v["observations"]}
            for v in voyages
        ]
        # Manifest paths resolve relative to the manifest file, so point at
        # sibling ../voyages/<run_id>/ rather than the analysis root.
        payload = {
            "schema_version": "1.0.0",
            "campaign": "sentinel_synthetic_recovery_v1",
            "cell_id": cid,
            "n_voyages": len(voyages),
            "voyages": [
                {
                    "itinerary": _posix_join("..", rel["itinerary"]),
                    "observations": _posix_join("..", rel["observations"]),
                }
                for rel in rels
            ],
        }
        path = os.path.join(manifest_root, f"{cid}.json")
        write_json(path, payload)
        first = voyages[0]
        cells.append(
            {
                "cell_id": cid,
                "hazard_profile": first["hazard_profile"],
                "fleet_config": first["fleet_config"],
                "R_onboard": first["R_onboard"],
                "port_hazards": first["port_hazards"],
                "n_voyages": len(voyages),
                "manifest": path,
                "fit_dir": os.path.join(out_dir, "fits", cid),
            },
        )
    return cells


def cells_from_out(out_dir: str) -> list[dict[str, Any]]:
    """Rebuild cell descriptors from a previous extract (no zip walk)."""
    payload = read_json(os.path.join(out_dir, "cells.json"))
    if not isinstance(payload, dict):
        raise SystemExit(f"cells.json missing or invalid under {out_dir}")
    cells: list[dict[str, Any]] = []
    for cid, run_ids in sorted(payload.items()):
        if not isinstance(run_ids, list) or not run_ids:
            continue
        run_id = validate_path_component(str(run_ids[0]), label="run_id")
        meta = read_json(os.path.join(out_dir, "voyages", run_id, "meta.json"))
        if not isinstance(meta, dict):
            continue
        hazard, fleet, r_val = cell_key(meta)
        cell = validate_path_component(str(cid), label="cell_id")
        cells.append(
            {
                "cell_id": cell,
                "hazard_profile": hazard,
                "fleet_config": fleet,
                "R_onboard": r_val,
                "port_hazards": dict(meta.get("port_hazards") or {}),
                "n_voyages": len(run_ids),
                "manifest": os.path.join(out_dir, "manifests", f"{cell}.json"),
                "fit_dir": os.path.join(out_dir, "fits", cell),
            },
        )
    return cells


def _read_csv(path: str) -> list[dict[str, str]]:
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline="",
    ) as fh:
        return list(csv.DictReader(fh))


def _true_lambda(port_id: str, hazards: dict[str, Any]) -> float:
    if port_id in hazards:
        return float(hazards[port_id])
    return _HOME_PORT_TRUTH


def _field_float(row: Mapping[str, Any], key: str) -> float:
    return float(row[key]) if key in row else float("nan")


def _score_port(
    cell: Mapping[str, Any],
    status: Mapping[str, Any],
    port: Mapping[str, Any],
    *,
    r_true: float,
    r_mean: float,
    r_lo: float,
    r_hi: float,
    r_covered: bool,
    truth: Mapping[str, Any],
) -> dict[str, Any]:
    port_id = str(port.get("port_id") or "")
    lam_true = _true_lambda(port_id, dict(truth))
    lam_lo = _field_float(port, "hazard_q05")
    lam_hi = _field_float(port, "hazard_q95")
    covered = not math.isnan(lam_lo) and interval_covers(
        lam_true, lam_lo, lam_hi,
    )
    return {
        "cell_id": cell["cell_id"],
        "hazard_profile": cell["hazard_profile"],
        "fleet_config": cell["fleet_config"],
        "R_onboard_true": r_true,
        "n_voyages": cell["n_voyages"],
        "fit_status": str(status.get("status") or "missing"),
        "port_id": port_id,
        "lambda_true": lam_true,
        "lambda_mean": _field_float(port, "hazard_mean"),
        "lambda_q05": lam_lo,
        "lambda_q95": lam_hi,
        "lambda_covered": covered,
        "R_mean": r_mean,
        "R_q05": r_lo,
        "R_q95": r_hi,
        "R_covered": r_covered,
    }


def _onboard_r_interval(onboard: dict[str, Any]) -> tuple[float, float, float]:
    ships = onboard.get("ships") or []
    if not ships:
        return (float("nan"), float("nan"), float("nan"))
    means = [float(s["r_onboard_mean"]) for s in ships]
    lo = [float(s["r_onboard_q05"]) for s in ships]
    hi = [float(s["r_onboard_q95"]) for s in ships]
    return (
        sum(means) / len(means),
        sum(lo) / len(lo),
        sum(hi) / len(hi),
    )


def score_cell(cell: dict[str, Any], status: dict[str, Any]) -> list[dict[str, Any]]:
    """One recovery row per port in the fitted cell."""
    fit_dir = cell["fit_dir"]
    hazards_path = os.path.join(fit_dir, "fleet_port_hazards.csv")
    onboard_path = os.path.join(fit_dir, "onboard_summary.json")
    r_mean = r_lo = r_hi = float("nan")
    if os.path.isfile(onboard_path):
        with validated_open(
            onboard_path, allowed_roots=allowed_roots(), encoding="utf-8",
        ) as fh:
            onboard = json.load(fh)
        r_mean, r_lo, r_hi = _onboard_r_interval(onboard)
    r_true = float(cell["R_onboard"])
    r_covered = not math.isnan(r_lo) and interval_covers(r_true, r_lo, r_hi)
    port_rows = _read_csv(hazards_path) if os.path.isfile(hazards_path) else []
    truth = cell["port_hazards"]
    ports = port_rows or [{"port_id": pid} for pid in sorted(truth)]
    return [
        _score_port(
            cell,
            status,
            port,
            r_true=r_true,
            r_mean=r_mean,
            r_lo=r_lo,
            r_hi=r_hi,
            r_covered=r_covered,
            truth=truth,
        )
        for port in ports
    ]


def _load_fit_status(fit_dir: str) -> dict[str, Any] | None:
    """Return a previous fit_status.json payload when present."""
    path = os.path.join(fit_dir, "fit_status.json")
    if not os.path.isfile(path):
        return None
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8",
    ) as fh:
        payload = json.load(fh)
    return payload if isinstance(payload, dict) else None


def fit_cell(
    cell: dict[str, Any],
    *,
    engine: str,
    sampler: SamplerOptions,
    force: bool,
    pathogen: str | None = None,
) -> dict[str, Any]:
    """Run the fleet attribution model for one recovery cell."""
    if not force:
        previous = _load_fit_status(cell["fit_dir"])
        if previous and previous.get("status") in {"ok", "smoke"}:
            return previous
    ensure_out_dir(cell["fit_dir"])
    return fit_sentinel_fleet(
        cell["manifest"],
        cell["fit_dir"],
        # None resolves through the incubation catalog's default_pathogen
        # rather than naming a pathogen in code (Law 2).
        pathogen=pathogen,
        engine=engine,
        sampler=sampler,
        priors=recovery_fleet_priors(fleet_config=str(cell["fleet_config"])),
        wastewater=False,
    )


def write_report(out_dir: str, rows: list[dict[str, Any]]) -> str:
    """Coverage summary markdown for the recovery grid."""
    scored = [r for r in rows if r["fit_status"] in {"ok", "smoke"}]
    n = len(scored)
    n_cov = sum(1 for r in scored if r["lambda_covered"])
    r_cells = {(r["cell_id"], r["R_covered"]) for r in scored}
    n_r = sum(1 for _cid, covered in r_cells if covered)
    lines = [
        "# Sentinel synthetic recovery",
        "",
        f"- Port-hazard rows scored: {n}",
        f"- λ_p in 90% CrI: {n_cov}/{n}" if n else "- λ_p in 90% CrI: n/a",
        f"- Cells with R_onboard in 90% CrI: {n_r}/{len(r_cells)}" if r_cells else "",
        "",
        "| cell | port | true λ | mean | 90% CrI | covered |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in scored:
        cri = f"[{row['lambda_q05']:.4g}, {row['lambda_q95']:.4g}]"
        lines.append(
            f"| {row['cell_id']} | {row['port_id']} | {row['lambda_true']:.4g} | "
            f"{row['lambda_mean']:.4g} | {cri} | {row['lambda_covered']} |"
        )
    path = os.path.join(out_dir, "report.md")
    with validated_open(
        path, "w", allowed_roots=allowed_roots(), encoding="utf-8",
    ) as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def _select_cells(
    cells: list[dict[str, Any]],
    wanted: set[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    chosen = [c for c in cells if not wanted or c["cell_id"] in wanted]
    if limit is not None:
        chosen = chosen[: max(0, int(limit))]
    return chosen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", help="directory of campaign result zips")
    parser.add_argument(
        "--out", default="results/sentinel_synthetic_recovery_v1/analysis",
    )
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument(
        "--fits-only",
        action="store_true",
        help="reuse existing voyages/manifests instead of re-extracting zips",
    )
    parser.add_argument(
        "--engine", choices=("auto", "stan", "numpy"), default="auto",
    )
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--iter-sampling", type=int, default=400)
    parser.add_argument("--iter-warmup", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--cell", action="append", default=[], help="fit only these cell ids")
    parser.add_argument("--max-cells", type=int, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="refit cells even when fit_status.json already reports ok",
    )
    parser.add_argument(
        "--pathogen",
        default=None,
        help="delay catalog entry to fit under; default is the catalog default",
    )
    add_allow_skipped_argument(parser)
    args = parser.parse_args(argv)

    results_dir = safe_path(args.results)
    out_dir = ensure_out_dir(args.out)
    if args.fits_only:
        cells = cells_from_out(out_dir)
        print(f"reusing extract cells={len(cells)}", flush=True)
    else:
        print("Extracting voyages…", flush=True)
        grouped = extract_voyages(results_dir, out_dir)
        cells = write_cell_manifests(grouped, out_dir)
        print(
            f"cells={len(cells)} voyages={sum(c['n_voyages'] for c in cells)}",
            flush=True,
        )
    if args.extract_only:
        return 0

    engine = args.engine
    if engine == "auto" and not cmdstan_available():
        print("CmdStan not available; using numpy reference walker", flush=True)
        engine = "numpy"
    sampler = SamplerOptions(
        chains=args.chains,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed,
        show_progress=True,
    )
    wanted = set(args.cell)
    rows: list[dict[str, Any]] = []
    cell_statuses: list[dict[str, Any]] = []
    for cell in _select_cells(cells, wanted, args.max_cells):
        print(f"Fitting {cell['cell_id']} n={cell['n_voyages']}…", flush=True)
        status = fit_cell(
            cell,
            engine=engine,
            sampler=sampler,
            force=args.force,
            pathogen=args.pathogen,
        )
        print(f"  {status.get('status')}", flush=True)
        cell_statuses.append(status)
        rows.extend(score_cell(cell, status))
    write_csv(os.path.join(out_dir, "recovery.csv"), rows, RECOVERY_COLUMNS)
    report = write_report(out_dir, rows)
    print(f"report: {report}", flush=True)
    # A recovery sweep whose cells produced no posterior has measured nothing;
    # exiting 0 would let a campaign shard report success on empty coverage.
    return worst_exit_code(
        fit_exit_code(s, allow_skipped=args.allow_skipped_fit) for s in cell_statuses
    )


if __name__ == "__main__":
    raise SystemExit(main())
