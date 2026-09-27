#!/usr/bin/env python3
"""Fold the NORO-RHYTHM-01 paired A/B run zips into the ledger readout.

Reads a results root shaped ``<arm>/<tier>/<run_id>.zip`` where each zip
carries ``summary.json`` (the standard probe block) and ``rhythm.json.gz``
(the rhythm payload). Emits a machine JSON + a markdown readout covering:

- takeoff/establishment (ignition, takeoff, posting rates + Wilson CIs,
  paired-seed discordance),
- secondary-vomit landing partition (immune-cabin vs non-immune occupancy,
  shared-venue landings — the GROWTH-01 defect metric),
- growth-chain depth (concurrent-peak distribution, per-generation
  reproduction on ignited voyages),
- anchor readout via ``score_anchors`` (A1/A5 attack-rate anchors, VSP
  posting rate, reported-rate channel),
- clock correlation (emesis timing vs post-prandial marks; corridor
  occupancy at catalog event endings vs day-matched epochs),
- defect witnesses (ashore agents dosed, flag not consumed, unmodulated
  emesis).

Usage::

    tools/noro_diag/rhythm_ab_readout.py --results-root <dir> --out <md>
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    validated_open,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
for _p in (str(REPO_ROOT), str(_CAMPAIGN_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TAKEOFF_PEAK_PREVALENCE = 10
_ARMS = ("off", "on")
_CABIN_ZONE_TYPES = ("Cabin", "Cabin_Corridor")


def _wilson(count: int, n: int) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = count / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _rate_row(count: int, n: int) -> dict[str, Any]:
    lo, hi = _wilson(count, n)
    return {
        "count": count,
        "n": n,
        "rate": count / n if n else None,
        "ci95": [lo, hi],
    }


def _load_zip(path: Path) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        with zipfile.ZipFile(path) as zf:
            summary = json.loads(zf.read("summary.json"))
            rhythm: dict[str, Any] = {}
            if "rhythm.json.gz" in zf.namelist():
                import gzip

                rhythm = json.loads(
                    gzip.decompress(zf.read("rhythm.json.gz")).decode("utf-8"),
                )
            return summary, rhythm
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"readout: skipping {path}: {exc}", file=sys.stderr)
        return None


def _cell_dir(results_root: Path, arm: str, tier: str) -> Path:
    return results_root / arm / tier


def load_cells(results_root: Path) -> dict[tuple[str, str], list[tuple[Path, dict[str, Any], dict[str, Any]]]]:
    cells: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for arm in _ARMS:
        arm_dir = results_root / arm
        if not arm_dir.is_dir():
            continue
        for tier_dir in sorted(arm_dir.iterdir()):
            if not tier_dir.is_dir():
                continue
            for zip_path in sorted(tier_dir.glob("*.zip")):
                loaded = _load_zip(zip_path)
                if loaded is None:
                    continue
                summary, rhythm = loaded
                cells[(arm, tier_dir.name)].append((zip_path, summary, rhythm))
    return cells


def _ignition_counts(
    runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    n = len(runs)
    ignited = sum(1 for _, _, r in runs if r.get("ignited"))
    took_off = sum(
        1
        for _, s, _ in runs
        if (s.get("derived") or {}).get("peak_prevalence", 0)
        >= TAKEOFF_PEAK_PREVALENCE
    )
    posted = sum(
        1
        for _, s, _ in runs
        if (s.get("derived") or {}).get("vsp_trigger_epoch") is not None
    )
    acquired = [r.get("n_acquired", 0) for _, _, r in runs]
    emitted = [r.get("n_emesis_emitted", 0) for _, _, r in runs]
    return {
        "n_runs": n,
        "ignited": _rate_row(ignited, n),
        "took_off": _rate_row(took_off, n),
        "posted": _rate_row(posted, n),
        "acquired_median": median(acquired) if acquired else None,
        "emitted_median": median(emitted) if emitted else None,
    }


def _paired_discordance(
    off_runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
    on_runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
) -> dict[str, int]:
    off_ign = {
        p.stem: bool(r.get("ignited")) for p, _, r in off_runs
    }
    on_ign = {
        p.stem: bool(r.get("ignited")) for p, _, r in on_runs
    }
    shared = sorted(set(off_ign) & set(on_ign))
    return {
        "n_paired": len(shared),
        "off_only": sum(1 for k in shared if off_ign[k] and not on_ign[k]),
        "on_only": sum(1 for k in shared if on_ign[k] and not off_ign[k]),
        "both": sum(1 for k in shared if on_ign[k] and off_ign[k]),
        "neither": sum(1 for k in shared if not on_ign[k] and not off_ign[k]),
    }


def _landing_partition(
    runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    emesis_rows: list[dict[str, Any]] = []
    for _, _, r in runs:
        emesis_rows.extend(r.get("emesis_rows") or [])
    secondary = [row for row in emesis_rows if row.get("gen_class") == "acquired"]
    cabin = [row for row in secondary if row.get("zone_type") in _CABIN_ZONE_TYPES]
    cabin_immune = [row for row in cabin if row.get("n_susceptible") == 0]
    shared_venue = [
        row
        for row in secondary
        if row.get("zone_type") not in _CABIN_ZONE_TYPES
    ]
    return {
        "emesis_total": len(emesis_rows),
        "secondary_emesis": len(secondary),
        "secondary_cabin": len(cabin),
        "secondary_cabin_immune_occupancy": len(cabin_immune),
        "immune_cabin_share": (
            len(cabin_immune) / len(cabin) if cabin else None
        ),
        "shared_venue_landings": len(shared_venue),
        "shared_venue_share": (
            len(shared_venue) / len(secondary) if secondary else None
        ),
    }


def _growth_depth(
    runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    ignited = [
        (s, r)
        for _, s, r in runs
        if r.get("ignited") and r.get("epoch_rows")
    ]
    peaks = [
        max(row.get("infected", 0) for row in r["epoch_rows"])
        for _, r in ignited
    ]
    gen_hist: dict[int, int] = defaultdict(int)
    gen_infected: dict[int, int] = defaultdict(int)
    for _, r in ignited:
        for acq in r.get("acquisition_rows") or []:
            gen_hist[int(acq.get("gen", -1))] += 1
        infected_ids = {acq.get("agent_id") for acq in r.get("acquisition_rows") or []}
        for acq in r.get("acquisition_rows") or []:
            if acq.get("agent_id") in infected_ids:
                gen_infected[int(acq.get("gen", -1))] += 1
    per_gen_r: dict[str, float] = {}
    for gen in sorted(gen_hist):
        if gen < 0 or gen_infected.get(gen - 1, 0) <= 0:
            continue
        per_gen_r[str(gen)] = gen_hist[gen] / gen_infected[gen - 1]
    return {
        "n_ignited": len(ignited),
        "concurrent_peak_median": median(peaks) if peaks else None,
        "concurrent_peak_max": max(peaks) if peaks else 0,
        "concurrent_peak_distribution": {
            str(p): peaks.count(p) for p in sorted(set(peaks))
        },
        "generation_histogram": {str(g): gen_hist[g] for g in sorted(gen_hist)},
        "per_generation_reproduction": per_gen_r,
        "max_generation": max(gen_hist) if gen_hist else None,
    }


def _clock_correlation(
    runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    emit_calls: dict[str, int] = defaultdict(int)
    corridor_at_egress: list[int] = []
    corridor_at_non_egress: list[int] = []
    emesis_minute_hist_pp: dict[int, int] = defaultdict(int)
    emesis_minute_hist_other: dict[int, int] = defaultdict(int)
    for _, _, r in runs:
        if not r.get("rhythm_attached"):
            continue
        for state, n in (r.get("emit_calls") or {}).items():
            emit_calls[state] += int(n)
        egress_epochs: set[int] = set()
        for day in r.get("dealt_days") or []:
            for ev in day.get("events") or []:
                if ev.get("egress_min") is not None:
                    voyage_minute = (
                        int(day["voyage_day"]) * 1440 + int(ev["egress_min"])
                    )
                    egress_epochs.add(voyage_minute // 60)
        for row in r.get("emesis_rows") or []:
            minute = int(row.get("epoch", 0)) * 60 % 1440
            hour_bin = minute // 60
            if row.get("post_prandial") is True:
                emesis_minute_hist_pp[hour_bin] += 1
            else:
                emesis_minute_hist_other[hour_bin] += 1
        for erow in r.get("epoch_rows") or []:
            epoch = int(erow.get("epoch", 0))
            corridor = sum(
                int(count)
                for zone, count in (erow.get("zones") or {}).items()
                if "corridor" in str(zone).lower()
            )
            if epoch in egress_epochs:
                corridor_at_egress.append(corridor)
            else:
                corridor_at_non_egress.append(corridor)
    pp = emit_calls.get("post_prandial", 0)
    non_pp = emit_calls.get("outside_window", 0) + emit_calls.get("off", 0)
    return {
        "emit_calls": dict(emit_calls),
        "emesis_post_prandial": pp,
        "emesis_non_post_prandial": non_pp,
        "post_prandial_share": (pp / (pp + non_pp)) if pp + non_pp else None,
        "emesis_hour_hist_post_prandial": {
            str(h): emesis_minute_hist_pp[h] for h in sorted(emesis_minute_hist_pp)
        },
        "emesis_hour_hist_other": {
            str(h): emesis_minute_hist_other[h] for h in sorted(emesis_minute_hist_other)
        },
        "corridor_occupancy_at_egress_mean": (
            sum(corridor_at_egress) / len(corridor_at_egress)
            if corridor_at_egress
            else None
        ),
        "corridor_occupancy_baseline_mean": (
            sum(corridor_at_non_egress) / len(corridor_at_non_egress)
            if corridor_at_non_egress
            else None
        ),
        "corridor_egress_epoch_count": len(corridor_at_egress),
        "corridor_baseline_epoch_count": len(corridor_at_non_egress),
    }


def _defect_witnesses(
    runs: list[tuple[Path, dict[str, Any], dict[str, Any]]],
    arm: str,
) -> dict[str, Any]:
    attached = sum(1 for _, _, r in runs if r.get("rhythm_attached"))
    commitments = [r.get("commitments_total", 0) for _, _, r in runs]
    ashore_dosed = [r.get("ashore_dosed_epochs", 0) for _, _, r in runs]
    emit_calls: dict[str, int] = defaultdict(int)
    for _, _, r in runs:
        for state, n in (r.get("emit_calls") or {}).items():
            emit_calls[state] += int(n)
    return {
        "runs_attached": attached,
        "runs_total": len(runs),
        "commitments_total": sum(commitments),
        "runs_with_commitments": sum(1 for c in commitments if c > 0),
        "ashore_dosed_epochs_total": sum(ashore_dosed),
        "runs_with_ashore_dosing": sum(1 for a in ashore_dosed if a > 0),
        "emit_calls": dict(emit_calls),
        "arm": arm,
    }


def _anchor_cell(results_root: Path, arm: str, tier: str) -> dict[str, Any] | None:
    cell_dir = _cell_dir(results_root, arm, tier)
    if not cell_dir.is_dir():
        return None
    try:
        from telemetry_buffer.observation_model.score_anchors import (
            read_rows,
            summarise_cell,
        )
    except ImportError:
        return None
    rows = read_rows(cell_dir, {})
    if not rows:
        return None
    hull = rows[0].get("hull", tier)
    strategy = rows[0].get("strategy", "")
    dose = rows[0].get("dose_adjustment", 0.0)
    cell = summarise_cell(rows)
    cell["cell_key"] = [arm, hull, strategy, dose]
    return cell


def build_readout(results_root: Path) -> dict[str, Any]:
    cells = load_cells(results_root)
    tiers = sorted({tier for _, tier in cells})
    takeoff: dict[str, Any] = {}
    discordance: dict[str, Any] = {}
    landing: dict[str, Any] = {}
    growth: dict[str, Any] = {}
    clock: dict[str, Any] = {}
    defects: dict[str, Any] = {}
    anchors: dict[str, Any] = {}
    for tier in tiers:
        off_runs = cells.get(("off", tier), [])
        on_runs = cells.get(("on", tier), [])
        takeoff[tier] = {
            "off": _ignition_counts(off_runs),
            "on": _ignition_counts(on_runs),
        }
        discordance[tier] = _paired_discordance(off_runs, on_runs)
        landing[tier] = {
            "off": _landing_partition(off_runs),
            "on": _landing_partition(on_runs),
        }
        growth[tier] = {
            "off": _growth_depth(off_runs),
            "on": _growth_depth(on_runs),
        }
        clock[tier] = {
            "on": _clock_correlation(on_runs),
        }
        defects[tier] = {
            "off": _defect_witnesses(off_runs, "off"),
            "on": _defect_witnesses(on_runs, "on"),
        }
        anchors[tier] = {
            arm: _anchor_cell(results_root, arm, tier) for arm in _ARMS
        }
    return {
        "results_root": str(results_root),
        "takeoff": takeoff,
        "paired_discordance": discordance,
        "landing_partition": landing,
        "growth_chain": growth,
        "clock_correlation": clock,
        "defect_witnesses": defects,
        "anchors": anchors,
    }


def _fmt_pct(rate: float | None) -> str:
    return f"{rate * 100:.1f}%" if rate is not None else "n/a"


def _fmt_ci(row: dict[str, Any]) -> str:
    if not row.get("n"):
        return "n/a"
    lo, hi = row.get("ci95") or (0.0, 0.0)
    return f"{row['count']}/{row['n']} ({_fmt_pct(row['rate'])}, CI {_fmt_pct(lo)}–{_fmt_pct(hi)})"


def render_markdown(readout: dict[str, Any]) -> str:
    lines: list[str] = []
    for tier, arms in readout["takeoff"].items():
        lines.append(f"#### {tier}")
        lines.append("| arm | ignited | takeoff | posted | median acquired |")
        lines.append("|---|---|---|---|---|")
        for arm in _ARMS:
            t = arms[arm]
            lines.append(
                f"| {arm} | {_fmt_ci(t['ignited'])} | {_fmt_ci(t['took_off'])}"
                f" | {_fmt_ci(t['posted'])} | {t['acquired_median']} |",
            )
        d = readout["paired_discordance"][tier]
        lines.append(
            f"\npaired ignition discordance (n={d['n_paired']}):"
            f" off-only {d['off_only']}, on-only {d['on_only']},"
            f" both {d['both']}, neither {d['neither']}",
        )
        lp = readout["landing_partition"][tier]
        lines.append(
            "\nsecondary-vomit landing partition: "
            f"off immune-cabin share {_fmt_pct(lp['off']['immune_cabin_share'])}"
            f" ({lp['off']['secondary_cabin_immune_occupancy']}/"
            f"{lp['off']['secondary_cabin']}), "
            f"on {_fmt_pct(lp['on']['immune_cabin_share'])}"
            f" ({lp['on']['secondary_cabin_immune_occupancy']}/"
            f"{lp['on']['secondary_cabin']}); "
            f"shared-venue share off {_fmt_pct(lp['off']['shared_venue_share'])}"
            f" on {_fmt_pct(lp['on']['shared_venue_share'])}",
        )
        g = readout["growth_chain"][tier]
        lines.append(
            "\ngrowth: off peak-median "
            f"{g['off']['concurrent_peak_median']} max "
            f"{g['off']['concurrent_peak_max']} | on peak-median "
            f"{g['on']['concurrent_peak_median']} max "
            f"{g['on']['concurrent_peak_max']} | per-gen R off "
            f"{g['off']['per_generation_reproduction']} on "
            f"{g['on']['per_generation_reproduction']}",
        )
        dw = readout["defect_witnesses"][tier]
        lines.append(
            "\ndefects: off ashore-dosed-epochs "
            f"{dw['off']['ashore_dosed_epochs_total']} | on "
            f"{dw['on']['ashore_dosed_epochs_total']} | on-arm runs attached "
            f"{dw['on']['runs_attached']}/{dw['on']['runs_total']} | emit calls "
            f"{dw['on']['emit_calls']}",
        )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    readout = build_readout(args.results_root)
    report = render_markdown(readout)
    print(report)
    if args.out:
        out_dir = prepare_output_directory(
            str(args.out.parent), allowed_roots=(str(REPO_ROOT),),
        )
        out_path = Path(out_dir) / args.out.name
        with validated_open(
            str(out_path), "w", encoding="utf-8",
            allowed_roots=(str(REPO_ROOT),),
        ) as fh:
            fh.write(report + "\n")
    if args.json_out:
        json_dir = prepare_output_directory(
            str(args.json_out.parent), allowed_roots=(str(REPO_ROOT),),
        )
        json_path = Path(json_dir) / args.json_out.name
        with validated_open(
            str(json_path), "w", encoding="utf-8",
            allowed_roots=(str(REPO_ROOT),),
        ) as fh:
            fh.write(json.dumps(readout, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
