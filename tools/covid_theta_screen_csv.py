#!/usr/bin/env python3
"""Flatten a boarding-screen surface JSON into the per-(Θ, age) CSV of record,
and optionally pair each cell by seed against a parent design's cells.

    python3 tools/covid_theta_screen_csv.py surface.json --out surface.csv
    python3 tools/covid_theta_screen_csv.py surface.json --out surface.csv \
        --cells results/v10/cells --parent-cells results/v9/cells \
        --pairs-out pairs.csv

The surface CSV carries the same columns as
``docs/covid/covid_theta_screen_v9_surface.csv``. The pairs CSV has one row per
(Θ, age, seed) present in ``--cells``: this run's ``infections_total``,
``attack_rate`` and ``recorded_onsets`` beside the parent's at the same seed,
or blanks where the parent has no such cell. Reporting only; nothing here
selects or fits.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

SURFACE_COLUMNS = (
    "theta",
    "infection_age_days",
    "index_geometry_pass_fraction",
    "recorded_onsets_p10",
    "recorded_onsets_p90",
    "recorded_onsets_median",
    "before_share_median",
    "campaign_positives_p10",
    "campaign_positives_p90",
    "campaign_specimens_median",
    "attack_q10",
    "attack_q50",
    "attack_q90",
    "takeoff_probability",
    "onset_mass_near_target",
    "vsp_threshold_crossing_fraction",
    "index_geometry_ok",
    "t1_ok",
    "t3_ok",
    "recorded_onsets_per_seed",
)


def _surface_row(entry: dict[str, Any]) -> dict[str, Any]:
    onsets = entry.get("recorded_onsets") or {}
    attack = entry.get("attack_rate_quantiles") or {}
    per_seed = entry.get("recorded_onsets_per_seed") or []
    return {
        "theta": entry.get("theta"),
        "infection_age_days": entry.get("infection_age_days"),
        "index_geometry_pass_fraction": entry.get("index_geometry_pass_fraction"),
        "recorded_onsets_p10": entry.get("recorded_onsets_p10"),
        "recorded_onsets_p90": entry.get("recorded_onsets_p90"),
        "recorded_onsets_median": onsets.get("median"),
        "before_share_median": entry.get("before_share_median"),
        "campaign_positives_p10": entry.get("campaign_positives_p10"),
        "campaign_positives_p90": entry.get("campaign_positives_p90"),
        "campaign_specimens_median": entry.get("campaign_specimens_median"),
        "attack_q10": attack.get("q10"),
        "attack_q50": attack.get("q50"),
        "attack_q90": attack.get("q90"),
        "takeoff_probability": entry.get("takeoff_probability"),
        "onset_mass_near_target": entry.get("onset_mass_near_target"),
        "vsp_threshold_crossing_fraction": entry.get(
            "vsp_threshold_crossing_fraction",
        ),
        "index_geometry_ok": entry.get("index_geometry_ok"),
        "t1_ok": entry.get("t1_ok"),
        "t3_ok": entry.get("t3_ok"),
        "recorded_onsets_per_seed": " ".join(str(int(x)) for x in sorted(per_seed)),
    }


def write_surface_csv(surface: dict[str, Any], out: Path) -> int:
    rows = [_surface_row(e) for e in surface.get("surface", [])]
    rows.sort(key=lambda r: (float(r["theta"]), float(r["infection_age_days"])))
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SURFACE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _load_cells(cells_dir: Path) -> dict[tuple[float, float, int], dict[str, Any]]:
    out: dict[tuple[float, float, int], dict[str, Any]] = {}
    for path in sorted(cells_dir.glob("*.json")):
        payload = json.loads(path.read_text())
        cell = payload.get("cell") or {}
        key = (
            float(cell["theta"]),
            float(cell["infection_age_days"]),
            int(cell["seed"]),
        )
        out[key] = payload
    return out


def _cell_triplet(payload: dict[str, Any] | None) -> tuple[Any, Any, Any]:
    if payload is None:
        return ("", "", "")
    observables = payload.get("observables") or {}
    return (
        payload.get("infections_total"),
        payload.get("attack_rate"),
        observables.get("recorded_onsets"),
    )


PAIR_COLUMNS = (
    "theta",
    "infection_age_days",
    "seed",
    "infections_total",
    "attack_rate",
    "recorded_onsets",
    "index_onset_day",
    "index_shedding_at_day0",
    "invalid_reason",
    "parent_infections_total",
    "parent_attack_rate",
    "parent_recorded_onsets",
)


def write_pairs_csv(cells_dir: Path, parent_dir: Path | None, out: Path) -> int:
    cells = _load_cells(cells_dir)
    parent = _load_cells(parent_dir) if parent_dir else {}
    rows = []
    for key in sorted(cells):
        payload = cells[key]
        total, rate, onsets = _cell_triplet(payload)
        p_total, p_rate, p_onsets = _cell_triplet(parent.get(key))
        rows.append({
            "theta": key[0],
            "infection_age_days": key[1],
            "seed": key[2],
            "infections_total": total,
            "attack_rate": rate,
            "recorded_onsets": onsets,
            "index_onset_day": payload.get("index_onset_day"),
            "index_shedding_at_day0": payload.get("index_shedding_at_day0"),
            "invalid_reason": payload.get("invalid_reason"),
            "parent_infections_total": p_total,
            "parent_attack_rate": p_rate,
            "parent_recorded_onsets": p_onsets,
        })
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIR_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface", help="surface JSON from fit_covid_theta.py screen")
    parser.add_argument("--out", required=True, help="surface CSV path")
    parser.add_argument("--cells", default=None, help="this run's cell directory")
    parser.add_argument("--parent-cells", default=None, help="parent design's cells")
    parser.add_argument("--pairs-out", default=None, help="paired-seed CSV path")
    args = parser.parse_args(argv)

    surface = json.loads(Path(args.surface).read_text())
    n_rows = write_surface_csv(surface, Path(args.out))
    print(f"wrote {n_rows} surface rows to {args.out}")
    if args.pairs_out:
        if not args.cells:
            parser.error("--pairs-out requires --cells")
        n_pairs = write_pairs_csv(
            Path(args.cells),
            Path(args.parent_cells) if args.parent_cells else None,
            Path(args.pairs_out),
        )
        print(f"wrote {n_pairs} paired rows to {args.pairs_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
