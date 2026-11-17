#!/usr/bin/env python3
"""Readout for the expedition p06 supply-contamination solver screen."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import zipfile
from pathlib import Path
from typing import Any

BLOCK_MAP = {
    "exp_station_lots_discrete": ("station_lots_contaminated", "discrete"),
    "exp_station_lots_continuous": ("station_lots_contaminated", "continuous"),
    "exp_quiet_station_lots_discrete": ("station_lots_quiet", "discrete"),
    "exp_quiet_station_lots_continuous": ("station_lots_quiet", "continuous"),
    "exp_single_line_receipt_discrete": ("single_line_receipt_contaminated", "discrete"),
    "exp_single_line_receipt_continuous": ("single_line_receipt_contaminated", "continuous"),
    "exp_declared_receipts_discrete": ("declared_receipts_contaminated", "discrete"),
    "exp_declared_receipts_continuous": ("declared_receipts_contaminated", "continuous"),
}

STRATA = [
    "station_lots_contaminated",
    "station_lots_quiet",
    "single_line_receipt_contaminated",
    "declared_receipts_contaminated",
]
SOLVERS = ["discrete", "continuous"]

RATE_METRICS = [
    ("pax_reported_ar", "passenger reported-case AR"),
    ("crew_reported_ar", "crew reported-case AR"),
    ("pax_ever_ill_ar", "passenger ever-ill AR"),
    ("crew_ever_ill_ar", "crew ever-ill AR"),
    ("pax_infection_ar", "passenger infection AR"),
    ("crew_infection_ar", "crew infection AR"),
]


def _percentile(values: list[float], q: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def _stats(values: list[float | None]) -> dict[str, Any]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"n": 0, "median": None, "q1": None, "q3": None, "mean": None, "min": None, "max": None}
    q1 = _percentile(vals, 0.25)
    med = _percentile(vals, 0.5)
    q3 = _percentile(vals, 0.75)
    return {
        "n": len(vals),
        "median": med,
        "q1": q1,
        "q3": q3,
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
    }


def _sign_test_p(diffs: list[float]) -> float | None:
    nz = [d for d in diffs if abs(d) > 1e-12]
    n = len(nz)
    if n == 0:
        return None
    k = sum(1 for d in nz if d > 0)
    tail = min(k, n - k)
    p = sum(math.comb(n, i) for i in range(tail + 1)) / (2**n)
    return min(1.0, 2.0 * p)


def _diff_stats(diffs: list[float]) -> dict[str, Any]:
    finite = [float(d) for d in diffs if d is not None]
    n_pos = sum(1 for d in finite if d > 1e-12)
    n_neg = sum(1 for d in finite if d < -1e-12)
    return {
        "n": len(finite),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "n_zero": len(finite) - n_pos - n_neg,
        "median": _percentile(finite, 0.5),
        "q1": _percentile(finite, 0.25),
        "q3": _percentile(finite, 0.75),
        "mean": statistics.fmean(finite) if finite else None,
        "sign_test_p": _sign_test_p(finite),
    }


def _seed_from_run_id(run_id: str) -> int | None:
    marker = "_s"
    if marker in run_id:
        tail = run_id.rsplit(marker, 1)[-1]
        if tail.isdigit():
            return int(tail)
    return None


def _cell_from_zip(zip_path: Path, block: str, stratum: str, solver: str) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as zf:
        summary = json.loads(zf.read("summary.json"))
    params = summary.get("parameters") or {}
    derived = summary.get("derived") or {}
    mech = summary.get("mechanisms") or {}
    seed = params.get("seed")
    if seed is None:
        seed = _seed_from_run_id(str(params.get("run_id") or zip_path.name))
    vsp_epoch = derived.get("vsp_trigger_epoch")
    vsp_day = None
    if vsp_epoch is not None:
        vsp_day = max(1, int(vsp_epoch) // 24 + 1)  # clock-exempt: readout day = SimClock.day_index(epoch)+1 on the pinned hours clock
    return {
        "block": block,
        "stratum": stratum,
        "solver": solver,
        "seed": int(seed),
        "tier_id": params.get("tier_id"),
        "engine_git_sha": params.get("engine_git_sha"),
        "posted": vsp_epoch is not None,
        "vsp_epoch": vsp_epoch,
        "vsp_day": vsp_day,
        "attack_rate": derived.get("attack_rate"),
        "peak_prevalence": derived.get("peak_prevalence"),
        "peak_epoch": derived.get("peak_epoch"),
        "pax_reported_ar": derived.get("reported_case_attack_rate_passenger"),
        "crew_reported_ar": derived.get("reported_case_attack_rate_crew"),
        "pax_ever_ill_ar": derived.get("ever_ill_attack_rate_passenger"),
        "crew_ever_ill_ar": derived.get("ever_ill_attack_rate_crew"),
        "pax_infection_ar": derived.get("infection_attack_rate_passenger"),
        "crew_infection_ar": derived.get("infection_attack_rate_crew"),
        "common_source_events": mech.get("common_source_events"),
        "common_source_takers": mech.get("common_source_takers"),
    }


def load_cells(results_dir: Path) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for block, (stratum, solver) in BLOCK_MAP.items():
        block_dir = results_dir / block
        if not block_dir.is_dir():
            raise SystemExit(f"missing block directory: {block_dir}")
        for zip_path in sorted(block_dir.glob("*.zip")):
            cells.append(_cell_from_zip(zip_path, block, stratum, solver))
    return cells


def _group(cells: list[dict[str, Any]]) -> dict[tuple[str, str], dict[int, dict[str, Any]]]:
    grouped: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault((cell["stratum"], cell["solver"]), {})[cell["seed"]] = cell
    return grouped


def _expected_seed_sets(seed_selection_path: Path) -> dict[tuple[str, str], set[int]]:
    data = json.loads(seed_selection_path.read_text(encoding="utf-8"))
    supply = data.get("supply_arms") or {}
    arm_to_stratum = {
        "station_lots": "station_lots_contaminated",
        "single_line_receipt": "single_line_receipt_contaminated",
        "declared_receipts": "declared_receipts_contaminated",
    }
    expected: dict[tuple[str, str], set[int]] = {}
    for solver in data.get("solver_arms") or SOLVERS:
        for arm, stratum in arm_to_stratum.items():
            seeds = (supply.get(arm) or {}).get("seeds") or []
            expected[(stratum, solver)] = {int(seed) for seed in seeds}
        quiet = data.get("quiet_controls") or {}
        if quiet.get("arm") == "station_lots":
            expected[("station_lots_quiet", solver)] = {
                int(seed) for seed in quiet.get("seeds") or []
            }
    return expected


def _cell_accounting(
    cells: list[dict[str, Any]],
    expected: dict[tuple[str, str], set[int]],
) -> dict[str, Any]:
    observed: dict[tuple[str, str], set[int]] = {}
    duplicates = 0
    for cell in cells:
        key = (cell["stratum"], cell["solver"])
        seeds = observed.setdefault(key, set())
        if cell["seed"] in seeds:
            duplicates += 1
        seeds.add(cell["seed"])
    missing_cells = []
    missing = 0
    for key in sorted(expected):
        absent = sorted(expected[key] - observed.get(key, set()))
        if absent:
            missing += len(absent)
            missing_cells.append(
                {"stratum": key[0], "solver": key[1], "seeds": absent}
            )
    return {
        "n_cells": len(cells),
        "n_unique_cells": sum(len(seeds) for seeds in observed.values()),
        "n_duplicate_cells": duplicates,
        "n_failed": missing,
        "missing_cells": missing_cells,
    }


def _arm_summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    posted = [c for c in cells if c["posted"]]
    out: dict[str, Any] = {
        "n": len(cells),
        "posted_n": len(posted),
        "posted_freq": (len(posted) / len(cells)) if cells else None,
        "metrics": {},
    }
    for key, _label in RATE_METRICS:
        out["metrics"][key] = _stats([c[key] for c in cells])
    out["metrics"]["pax_reported_ar_posted"] = _stats(
        [c["pax_reported_ar"] for c in posted]
    )
    out["vsp_epoch_posted"] = _stats([c["vsp_epoch"] for c in posted])
    out["vsp_day_posted"] = _stats([c["vsp_day"] for c in posted])
    out["attack_rate"] = _stats([c["attack_rate"] for c in cells])
    out["peak_prevalence"] = _stats([c["peak_prevalence"] for c in cells])
    out["common_source_events"] = _stats([c["common_source_events"] for c in cells])
    out["common_source_takers"] = _stats([c["common_source_takers"] for c in cells])
    return out


def _paired(stratum: str, grouped: dict[tuple[str, str], dict[int, dict[str, Any]]]) -> dict[str, Any]:
    d = grouped.get((stratum, "discrete"), {})
    c = grouped.get((stratum, "continuous"), {})
    seeds = sorted(set(d) & set(c))
    pairs = {"n_pairs": len(seeds), "seeds": seeds, "metrics": {}, "posting": {}}
    posted_pairs = [s for s in seeds if d[s]["posted"] and c[s]["posted"]]
    pairs["posting"] = {
        "both_posted": len(posted_pairs),
        "discrete_only": sum(1 for s in seeds if d[s]["posted"] and not c[s]["posted"]),
        "continuous_only": sum(1 for s in seeds if c[s]["posted"] and not d[s]["posted"]),
        "neither": sum(1 for s in seeds if not d[s]["posted"] and not c[s]["posted"]),
    }
    metric_specs = [(key, label) for key, label in RATE_METRICS] + [
        ("attack_rate", "overall attack_rate"),
        ("peak_prevalence", "peak prevalence"),
        ("common_source_events", "common_source_events"),
        ("common_source_takers", "common_source_takers"),
    ]
    for key, label in metric_specs:
        diffs = [c[s][key] - d[s][key] for s in seeds]
        pairs["metrics"][key] = {"label": label, **_diff_stats(diffs)}
    pairs["metrics"]["posted"] = {
        "label": "posted (vsp_trigger_epoch is not None)",
        **_diff_stats([float(c[s]["posted"]) - float(d[s]["posted"]) for s in seeds]),
    }
    pairs["pax_reported_ar_posted_both"] = _diff_stats(
        [c[s]["pax_reported_ar"] - d[s]["pax_reported_ar"] for s in posted_pairs]
    )
    pairs["vsp_epoch_both_posted"] = _diff_stats(
        [c[s]["vsp_epoch"] - d[s]["vsp_epoch"] for s in posted_pairs]
    )
    pairs["vsp_epoch_both_posted"]["n"] = len(posted_pairs)
    return pairs


def _fmt(x: Any, digits: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{100*x:.1f}%"


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# noro_supply_solver_screen_01 readout",
        "",
        f"**Measured at:** `{payload['measured_sha']}`",
        f"S3 prefix: `{payload['s3_prefix']}`",
        f"Image: `{payload['image']}`",
        f"Cells: {payload['n_cells']} run zips ({payload['n_unique_cells']} unique, {payload['n_duplicate_cells']} duplicate), {payload['n_failed']} failed/missing.",
        "",
        "Posting means `vsp_trigger_epoch is not None` (either-channel reported-case VSP rule). ARs are fractions; tables show percents where labelled.",
        "",
    ]
    for stratum in STRATA:
        arms = payload["strata"][stratum]["arms"]
        pairs = payload["strata"][stratum]["paired"]
        lines += [
            f"## {stratum}",
            "",
            _md_table(
                ["solver", "n", "posted", "posted-conditional pax reported AR (median [IQR])", "VSP epoch median [IQR]", "VSP day median [IQR]"],
                [
                    [
                        solver,
                        arms[solver]["n"],
                        f"{arms[solver]['posted_n']} ({_pct(arms[solver]['posted_freq'])})",
                        f"{_pct(arms[solver]['metrics']['pax_reported_ar_posted']['median'])} [{_pct(arms[solver]['metrics']['pax_reported_ar_posted']['q1'])}, {_pct(arms[solver]['metrics']['pax_reported_ar_posted']['q3'])}]",
                        f"{_fmt(arms[solver]['vsp_epoch_posted']['median'], 1)} [{_fmt(arms[solver]['vsp_epoch_posted']['q1'],1)}, {_fmt(arms[solver]['vsp_epoch_posted']['q3'],1)}]",
                        f"{_fmt(arms[solver]['vsp_day_posted']['median'], 1)} [{_fmt(arms[solver]['vsp_day_posted']['q1'],1)}, {_fmt(arms[solver]['vsp_day_posted']['q3'],1)}]",
                    ]
                    for solver in SOLVERS
                ],
            ),
            "",
            f"Paired posting cells: both {pairs['posting']['both_posted']}, discrete-only {pairs['posting']['discrete_only']}, continuous-only {pairs['posting']['continuous_only']}, neither {pairs['posting']['neither']}.",
            "",
            _md_table(
                ["endpoint", "paired n", "median diff (continuous - discrete)", "IQR", "sign p", "positive/negative/zero"],
                [
                    [
                        "posted",
                        pairs["metrics"]["posted"]["n"],
                        _fmt(pairs["metrics"]["posted"]["median"], 3),
                        f"[{_fmt(pairs['metrics']['posted']['q1'],3)}, {_fmt(pairs['metrics']['posted']['q3'],3)}]",
                        _fmt(pairs["metrics"]["posted"]["sign_test_p"], 3),
                        f"{pairs['metrics']['posted']['n_positive']}/{pairs['metrics']['posted']['n_negative']}/{pairs['metrics']['posted']['n_zero']}",
                    ],
                    [
                        "pax reported AR (both posted)",
                        pairs["pax_reported_ar_posted_both"]["n"],
                        _pct(pairs["pax_reported_ar_posted_both"]["median"]),
                        f"[{_pct(pairs['pax_reported_ar_posted_both']['q1'])}, {_pct(pairs['pax_reported_ar_posted_both']['q3'])}]",
                        _fmt(pairs["pax_reported_ar_posted_both"]["sign_test_p"], 3),
                        f"{pairs['pax_reported_ar_posted_both']['n_positive']}/{pairs['pax_reported_ar_posted_both']['n_negative']}/{pairs['pax_reported_ar_posted_both']['n_zero']}",
                    ],
                    [
                        "VSP epoch (both posted)",
                        pairs["vsp_epoch_both_posted"]["n"],
                        _fmt(pairs["vsp_epoch_both_posted"]["median"], 1),
                        f"[{_fmt(pairs['vsp_epoch_both_posted']['q1'],1)}, {_fmt(pairs['vsp_epoch_both_posted']['q3'],1)}]",
                        _fmt(pairs["vsp_epoch_both_posted"]["sign_test_p"], 3),
                        f"{pairs['vsp_epoch_both_posted']['n_positive']}/{pairs['vsp_epoch_both_posted']['n_negative']}/{pairs['vsp_epoch_both_posted']['n_zero']}",
                    ],
                ],
            ),
            "",
            "Role partition (all paired seeds; median [IQR] per arm, then paired diff):",
            "",
        ]
        role_rows = []
        range_rows = [
            [
                "posted-conditional pax reported AR",
                f"{_pct(arms['discrete']['metrics']['pax_reported_ar_posted']['min'])}–{_pct(arms['discrete']['metrics']['pax_reported_ar_posted']['max'])}",
                f"{_pct(arms['continuous']['metrics']['pax_reported_ar_posted']['min'])}–{_pct(arms['continuous']['metrics']['pax_reported_ar_posted']['max'])}",
            ],
            [
                "VSP epoch (posted)",
                f"{_fmt(arms['discrete']['vsp_epoch_posted']['min'], 1)}–{_fmt(arms['discrete']['vsp_epoch_posted']['max'], 1)}",
                f"{_fmt(arms['continuous']['vsp_epoch_posted']['min'], 1)}–{_fmt(arms['continuous']['vsp_epoch_posted']['max'], 1)}",
            ],
            [
                "VSP day (posted)",
                f"{_fmt(arms['discrete']['vsp_day_posted']['min'], 1)}–{_fmt(arms['discrete']['vsp_day_posted']['max'], 1)}",
                f"{_fmt(arms['continuous']['vsp_day_posted']['min'], 1)}–{_fmt(arms['continuous']['vsp_day_posted']['max'], 1)}",
            ],
        ]
        for key, label in RATE_METRICS:
            d = pairs["metrics"][key]
            role_rows.append([
                label,
                _pct(arms["discrete"]["metrics"][key]["median"]),
                _pct(arms["continuous"]["metrics"][key]["median"]),
                _pct(d["median"]),
                _fmt(d["sign_test_p"], 3),
                f"{d['n_positive']}/{d['n_negative']}/{d['n_zero']}",
            ])
            ds = arms["discrete"]["metrics"][key]
            cs = arms["continuous"]["metrics"][key]
            range_rows.append([
                label,
                f"{_pct(ds['min'])}–{_pct(ds['max'])}",
                f"{_pct(cs['min'])}–{_pct(cs['max'])}",
            ])
        lines += [_md_table(["metric", "discrete median", "continuous median", "median diff", "sign p", "+/-/0"], role_rows), ""]
        lines += [
            "Ranges (min–max):",
            "",
            _md_table(["metric", "discrete range", "continuous range"], range_rows),
            "",
        ]
        lines += [
            "Secondary witnesses (medians):",
            "",
            _md_table(
                ["metric", "discrete", "continuous", "paired median diff", "sign p"],
                [
                    [
                        "overall attack_rate",
                        _pct(arms["discrete"]["attack_rate"]["median"]),
                        _pct(arms["continuous"]["attack_rate"]["median"]),
                        _pct(pairs["metrics"]["attack_rate"]["median"]),
                        _fmt(pairs["metrics"]["attack_rate"]["sign_test_p"], 3),
                    ],
                    [
                        "peak prevalence",
                        _fmt(arms["discrete"]["peak_prevalence"]["median"], 1),
                        _fmt(arms["continuous"]["peak_prevalence"]["median"], 1),
                        _fmt(pairs["metrics"]["peak_prevalence"]["median"], 1),
                        _fmt(pairs["metrics"]["peak_prevalence"]["sign_test_p"], 3),
                    ],
                    [
                        "common_source_events",
                        _fmt(arms["discrete"]["common_source_events"]["median"], 1),
                        _fmt(arms["continuous"]["common_source_events"]["median"], 1),
                        _fmt(pairs["metrics"]["common_source_events"]["median"], 1),
                        _fmt(pairs["metrics"]["common_source_events"]["sign_test_p"], 3),
                    ],
                    [
                        "common_source_takers",
                        _fmt(arms["discrete"]["common_source_takers"]["median"], 1),
                        _fmt(arms["continuous"]["common_source_takers"]["median"], 1),
                        _fmt(pairs["metrics"]["common_source_takers"]["median"], 1),
                        _fmt(pairs["metrics"]["common_source_takers"]["sign_test_p"], 3),
                    ],
                ],
            ),
            "",
        ]
    lines += [
        "## Notes",
        "",
        "- This is a screen, not anchor fitting: the frozen rule is an uncertainty-qualified association; overlapping ranges or few posted cells make a stratum uninformative.",
        "- Quiet controls are station_lots seeds with zero contaminated provisioned lots in the census; they test whether the solver arm alone manufactures posting.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("out/noro_supply_solver_screen_01"))
    parser.add_argument("--json", type=Path, default=Path("campaigns/noro/supply_solver_screen_01/readout.json"))
    parser.add_argument("--md", type=Path, default=Path("docs/norovirus/supply_solver_screen_01_readout.md"))
    parser.add_argument("--sha", default="unknown")
    parser.add_argument("--s3-prefix", default="s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/")
    parser.add_argument("--image", default="994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver01@sha256:f25d74cd225bc4ade19a012ba801b25f91289f80f3c3778bfd6c27c343a0053a")
    parser.add_argument("--seed-selection", type=Path, default=None)
    args = parser.parse_args()

    cells = load_cells(args.results)
    grouped = _group(cells)
    seed_selection = args.seed_selection or args.results / "seed_selection.json"
    accounting = _cell_accounting(cells, _expected_seed_sets(seed_selection))
    strata_payload: dict[str, Any] = {}
    for stratum in STRATA:
        arms = {
            solver: _arm_summary(list(grouped.get((stratum, solver), {}).values()))
            for solver in SOLVERS
        }
        strata_payload[stratum] = {"arms": arms, "paired": _paired(stratum, grouped)}

    payload = {
        "measured_sha": args.sha,
        "s3_prefix": args.s3_prefix,
        "image": args.image,
        **accounting,
        "strata": strata_payload,
        "cells": cells,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text(build_markdown(payload), encoding="utf-8")
    print(f"wrote {args.json}")
    print(f"wrote {args.md}")
    print(f"cells={len(cells)} failed={payload['n_failed']}")
    for stratum in STRATA:
        arms = strata_payload[stratum]["arms"]
        print(
            stratum,
            "discrete_posted", arms["discrete"]["posted_n"], "/", arms["discrete"]["n"],
            "continuous_posted", arms["continuous"]["posted_n"], "/", arms["continuous"]["n"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
