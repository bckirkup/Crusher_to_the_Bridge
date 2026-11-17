#!/usr/bin/env python3
"""Readout for the mega p06 supply-contamination solver screen."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import zipfile
from pathlib import Path
from typing import Any

# campaign block -> (readout stratum key, solver). Quiet blocks are renamed to
# match the screen02 readout strata convention (station_lots_quiet).
BLOCKS = {
    "meg_station_lots_discrete": ("meg_station_lots_discrete", "discrete"),
    "meg_station_lots_continuous": ("meg_station_lots_continuous", "continuous"),
    "meg_single_line_receipt_discrete": ("meg_single_line_receipt_discrete", "discrete"),
    "meg_single_line_receipt_continuous": ("meg_single_line_receipt_continuous", "continuous"),
    "meg_declared_receipts_discrete": ("meg_declared_receipts_discrete", "discrete"),
    "meg_declared_receipts_continuous": ("meg_declared_receipts_continuous", "continuous"),
    "meg_quiet_station_lots_discrete": ("meg_station_lots_quiet_discrete", "discrete"),
    "meg_quiet_station_lots_continuous": ("meg_station_lots_quiet_continuous", "continuous"),
}

PAIRS = {
    "meg_station_lots": ("meg_station_lots_discrete", "meg_station_lots_continuous"),
    "meg_station_lots_quiet": ("meg_quiet_station_lots_discrete", "meg_quiet_station_lots_continuous"),
    "meg_single_line_receipt": ("meg_single_line_receipt_discrete", "meg_single_line_receipt_continuous"),
    "meg_declared_receipts": ("meg_declared_receipts_discrete", "meg_declared_receipts_continuous"),
}

STRATA_ROWS = [
    ("meg", "station_lots", "discrete", "meg_station_lots_discrete"),
    ("meg", "station_lots", "continuous", "meg_station_lots_continuous"),
    ("meg", "station_lots_quiet", "discrete", "meg_station_lots_quiet_discrete"),
    ("meg", "station_lots_quiet", "continuous", "meg_station_lots_quiet_continuous"),
    ("meg", "single_line_receipt", "discrete", "meg_single_line_receipt_discrete"),
    ("meg", "single_line_receipt", "continuous", "meg_single_line_receipt_continuous"),
    ("meg", "declared_receipts", "discrete", "meg_declared_receipts_discrete"),
    ("meg", "declared_receipts", "continuous", "meg_declared_receipts_continuous"),
]

PAIR_ROWS = [
    ("meg_declared_receipts", "meg", "declared_receipts"),
    ("meg_single_line_receipt", "meg", "single_line_receipt"),
    ("meg_station_lots", "meg", "station_lots"),
    ("meg_station_lots_quiet", "meg", "station_lots_quiet"),
]

PAIR_METRICS = [
    ("pax_ar", "pax_reported_ar"),
    ("crew_ar", "crew_reported_ar"),
    ("attack_rate", "attack_rate"),
    ("vsp_epoch", "vsp_epoch"),
]

POSTED_FIELDS = [
    "ar_median_posted",
    "ar_range_posted",
    "pax_ar_median_posted",
    "pax_ar_range_posted",
    "crew_ar_median_posted",
    "crew_ar_range_posted",
    "vsp_epoch_median_posted",
    "vsp_epoch_range_posted",
    "pax_inf_ar_median_posted",
    "crew_inf_ar_median_posted",
]

INTERPRETATION = "Interpretation: on the mega p06 cell the frozen stratified supply seeds almost never reach the VSP wire. `station_lots` posted 1/16 on each solver arm (the same seed posted on both), `single_line_receipt` and `declared_receipts` posted 0/10, and quiet controls posted 0/8. Because only one seed posted on both solvers, the paired continuous-minus-discrete sign tests are uninformative (n=1), so this screen cannot separate the solvers on mega; the measured mega result is that supply contamination at these burdens is a weak posting driver on the 7000-agent hull. The open decision is whether mega needs a different seed/burden stratum or whether supply contamination should be down-weighted as a posting mechanism at this complement."


def _r4(value: Any) -> Any:
    if value is None:
        return None
    return round(value, 4)


def _median(values: list[Any]) -> Any:
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def _median_range(values: list[Any]) -> tuple[Any, Any]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None
    return _r4(statistics.median(vals)), [_r4(min(vals)), _r4(max(vals))]


def _sign_test_p(nonzero: list[float]) -> float | None:
    n = len(nonzero)
    if n == 0:
        return None
    k = sum(1 for d in nonzero if d > 0)
    tail = min(k, n - k)
    p = sum(math.comb(n, i) for i in range(tail + 1)) / (2**n)
    return min(1.0, 2.0 * p)


def _paired_metric(diffs: list[Any]) -> dict[str, Any]:
    vals = [d for d in diffs if d is not None]
    nz = [d for d in vals if abs(d) > 1e-12]
    if not nz:
        return {"n_nonzero": 0, "p": None}
    pos = sum(1 for d in nz if d > 0)
    neg = sum(1 for d in nz if d < 0)
    return {
        "n_nonzero": len(nz),
        "positive": pos,
        "negative": neg,
        "median_diff": _r4(statistics.median(nz)),
        "p": _r4(_sign_test_p(nz)),
    }


def _seed_from_params(params: dict[str, Any], zip_path: Path) -> int:
    seed = params.get("seed")
    if seed is not None:
        return int(seed)
    run_id = str(params.get("run_id") or zip_path.name)
    tail = run_id.rsplit("_s", 1)[-1]
    if not tail.isdigit():
        raise ValueError(f"cannot parse seed from {zip_path.name}")
    return int(tail)


def _cell_from_zip(zip_path: Path, block: str, stratum: str, solver: str) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as zf:
        summary = json.loads(zf.read("summary.json"))
    params = summary.get("parameters") or {}
    derived = summary.get("derived") or {}
    return {
        "block": block,
        "stratum": stratum,
        "solver": solver,
        "seed": _seed_from_params(params, zip_path),
        "posted": derived.get("vsp_trigger_epoch") is not None,
        "vsp_epoch": derived.get("vsp_trigger_epoch"),
        "attack_rate": derived.get("attack_rate"),
        "pax_reported_ar": derived.get("reported_case_attack_rate_passenger"),
        "crew_reported_ar": derived.get("reported_case_attack_rate_crew"),
        "pax_infection_ar": derived.get("infection_attack_rate_passenger"),
        "crew_infection_ar": derived.get("infection_attack_rate_crew"),
    }


def load_cells(results_dir: Path) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for block, (stratum, solver) in BLOCKS.items():
        block_dir = results_dir / block
        if not block_dir.is_dir():
            raise SystemExit(f"missing block directory: {block_dir}")
        for zip_path in sorted(block_dir.glob("*.zip")):
            cells.append(_cell_from_zip(zip_path, block, stratum, solver))
    return cells


def _accounting(cells: list[dict[str, Any]], campaign_path: Path) -> dict[str, Any]:
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    expected = {
        block: {int(seed) for seed in (spec.get("seeds") or [])}
        for block, spec in (campaign.get("blocks") or {}).items()
        if block in BLOCKS
    }
    observed: dict[str, list[int]] = {}
    for cell in cells:
        observed.setdefault(cell["block"], []).append(cell["seed"])
    missing_cells: list[dict[str, Any]] = []
    unexpected_cells: list[dict[str, Any]] = []
    duplicates = 0
    for block in BLOCKS:
        seeds = observed.get(block, [])
        obs = set(seeds)
        duplicates += len(seeds) - len(obs)
        exp = expected.get(block, set())
        missing = sorted(exp - obs)
        unexpected = sorted(obs - exp)
        if missing:
            missing_cells.append({"block": block, "seeds": missing})
        if unexpected:
            unexpected_cells.append({"block": block, "seeds": unexpected})
    return {
        "n_cells": len(cells),
        "n_unique_cells": len({(c["block"], c["seed"]) for c in cells}),
        "n_duplicate_cells": duplicates,
        "n_failed": sum(len(m["seeds"]) for m in missing_cells),
        "missing_cells": missing_cells,
        "unexpected_cells": unexpected_cells,
    }


def _arm_fields(cells: list[dict[str, Any]]) -> dict[str, Any]:
    posted = [c for c in cells if c["posted"]]
    out: dict[str, Any] = {
        "n": len(cells),
        "posted_n": len(posted),
        "posted_rate": _r4(len(posted) / len(cells) if cells else None),
    }
    for key in POSTED_FIELDS:
        out[key] = None
    if not posted:
        return out
    out["ar_median_posted"], out["ar_range_posted"] = _median_range(
        [c["attack_rate"] for c in posted]
    )
    out["pax_ar_median_posted"], out["pax_ar_range_posted"] = _median_range(
        [c["pax_reported_ar"] for c in posted]
    )
    out["crew_ar_median_posted"], out["crew_ar_range_posted"] = _median_range(
        [c["crew_reported_ar"] for c in posted]
    )
    out["vsp_epoch_median_posted"], out["vsp_epoch_range_posted"] = _median_range(
        [c["vsp_epoch"] for c in posted]
    )
    out["pax_inf_ar_median_posted"] = _r4(_median([c["pax_infection_ar"] for c in posted]))
    out["crew_inf_ar_median_posted"] = _r4(_median([c["crew_infection_ar"] for c in posted]))
    return out


def _paired_summary(discrete_cells: list[dict[str, Any]], continuous_cells: list[dict[str, Any]]) -> dict[str, Any]:
    discrete = {c["seed"]: c for c in discrete_cells}
    continuous = {c["seed"]: c for c in continuous_cells}
    seeds = sorted(set(discrete) & set(continuous))
    both = [s for s in seeds if discrete[s]["posted"] and continuous[s]["posted"]]
    out: dict[str, Any] = {"n_pairs": len(seeds), "posted_both": len(both)}
    for key, field in PAIR_METRICS:
        diffs = []
        for seed in both:
            a = discrete[seed][field]
            b = continuous[seed][field]
            if a is not None and b is not None:
                diffs.append(b - a)
        out[key] = _paired_metric(diffs)
    return out


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    return str(value)


def _median_range_str(stats: dict[str, Any], median_key: str, range_key: str) -> str:
    median = stats.get(median_key)
    if median is None:
        return "— —"
    rng = stats.get(range_key) or [None, None]
    return f"{_fmt(median)} [{_fmt(rng[0])}, {_fmt(rng[1])}]"


def _paired_metric_str(stats: dict[str, Any]) -> str:
    if not stats or stats.get("n_nonzero", 0) == 0:
        return "—"
    return f"{_fmt(stats.get('median_diff'))} (p={_fmt(stats.get('p'))}, n={stats.get('n_nonzero')})"


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# NORO supply solver screen 03 readout",
        "",
        f"**Measured at:** `{payload['measured_sha']}`",
        f"S3 prefix: `{payload['s3_prefix']}`",
        f"Image: `{payload['image']}`",
        f"Cells: {payload['n_cells']} run zips ({payload['n_unique_cells']} unique, {payload['n_duplicate_cells']} duplicate, {payload['n_failed']} failed/missing).",
        "",
        "Endpoints: posting = `vsp_trigger_epoch is not None`; ARs below are posted-conditional unless noted. Days use 24 epochs/day.",
        "",
        "## Strata (posted-conditional medians)",
        "| hull | supply arm | solver | n | posted | AR median [range] | pax reported AR median [range] | crew reported AR median [range] | VSP epoch median [range] |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for hull, supply_arm, solver, stratum_key in STRATA_ROWS:
        stats = payload["strata"][stratum_key]
        lines.append(
            "| {hull} | {arm} | {solver} | {n} | {posted}/{n} | {ar} | {pax} | {crew} | {vsp} |".format(
                hull=hull,
                arm=supply_arm,
                solver=solver,
                n=stats["n"],
                posted=stats["posted_n"],
                ar=_median_range_str(stats, "ar_median_posted", "ar_range_posted"),
                pax=_median_range_str(stats, "pax_ar_median_posted", "pax_ar_range_posted"),
                crew=_median_range_str(stats, "crew_ar_median_posted", "crew_ar_range_posted"),
                vsp=_median_range_str(stats, "vsp_epoch_median_posted", "vsp_epoch_range_posted"),
            )
        )
    lines += [
        "",
        "## Paired continuous - discrete (sign test)",
        "",
        "| hull | supply arm | pairs | posted both | pax AR median diff (p) | crew AR median diff (p) | AR median diff (p) | VSP epoch median diff (p) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for pair_key, hull, supply_arm in PAIR_ROWS:
        stats = payload["paired_continuous_minus_discrete"][pair_key]
        lines.append(
            "| {hull} | {arm} | {pairs} | {both} | {pax} | {crew} | {ar} | {vsp} |".format(
                hull=hull,
                arm=supply_arm,
                pairs=stats["n_pairs"],
                both=stats["posted_both"],
                pax=_paired_metric_str(stats["pax_ar"]),
                crew=_paired_metric_str(stats["crew_ar"]),
                ar=_paired_metric_str(stats["attack_rate"]),
                vsp=_paired_metric_str(stats["vsp_epoch"]),
            )
        )
    if INTERPRETATION:
        lines += ["", "## Interpretation", "", INTERPRETATION]
    lines += [
        "",
        "## Notes",
        "",
        "- This is a screen, not anchor fitting: the frozen rule is an uncertainty-qualified association; overlapping ranges or few posted cells make a stratum uninformative.",
        "- Quiet controls are station_lots seeds with zero contaminated provisioned lots in the census; they test whether the solver arm alone manufactures posting.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("out/noro_supply_solver_screen_03"))
    parser.add_argument("--json", type=Path, default=Path("campaigns/noro/supply_solver_screen_03/readout.json"))
    parser.add_argument("--md", type=Path, default=Path("docs/norovirus/supply_solver_screen_03_readout.md"))
    parser.add_argument("--sha", default="unknown")
    parser.add_argument(
        "--s3-prefix",
        default="s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/",
    )
    parser.add_argument(
        "--image",
        default="994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver03@sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a",
    )
    parser.add_argument("--campaign", type=Path, default=Path("campaigns/noro/supply_solver_screen_03/campaign.json"))
    args = parser.parse_args()

    cells = load_cells(args.results)
    by_block: dict[str, list[dict[str, Any]]] = {}
    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        by_block.setdefault(cell["block"], []).append(cell)
        by_stratum.setdefault(cell["stratum"], []).append(cell)
    accounting = _accounting(cells, args.campaign)
    strata = {
        stratum_key: _arm_fields(by_stratum.get(stratum_key, []))
        for _, _, _, stratum_key in STRATA_ROWS
    }
    paired = {
        pair_key: _paired_summary(by_block.get(discrete_block, []), by_block.get(continuous_block, []))
        for pair_key, (discrete_block, continuous_block) in PAIRS.items()
    }
    payload = {
        "measured_sha": args.sha,
        "s3_prefix": args.s3_prefix,
        "image": args.image,
        **accounting,
        "strata": strata,
        "paired_continuous_minus_discrete": paired,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text(build_markdown(payload), encoding="utf-8")
    print(f"wrote {args.json}")
    print(f"wrote {args.md}")
    print(f"cells={len(cells)} failed={payload['n_failed']} unique={payload['n_unique_cells']}")
    for pair_key, stats in paired.items():
        print(pair_key, "pairs", stats["n_pairs"], "posted_both", stats["posted_both"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
