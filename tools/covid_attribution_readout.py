"""Read the covid_quarantine_attribution_v1 cells against the frozen criterion.

Writes one CSV row per cell and prints, per Theta and arm, the two medians the
design declares (all-seed and conditional-on-takeoff-in-both-arms) with the
verdict the frozen thresholds imply. Nothing here re-runs a simulation.

Usage:
    python3 tools/covid_attribution_readout.py \
        --cells results/covid_quarantine_attribution_v1/cells \
        --design picard_framework/runs/covid_quarantine_attribution_v1_design.json \
        --csv docs/covid/covid_quarantine_attribution_v1_surface.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROUTES = ("direct_contact", "droplet", "hvac_airborne", "fomite")
ZONES = ("cabin", "crew_mess", "galley", "corridor", "other")
ROLES = ("passenger", "crew")


def _rows(cells_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(cells_dir.glob("*.json")):
        c = json.loads(path.read_text())
        row = {
            "theta": c["cell"]["theta"],
            "arm_id": c["arm_id"],
            "seed": c["cell"]["seed"],
            "infections_total": c["infections_total"],
            "attack_rate": c["attack_rate"],
            "recorded_onsets": c["observables"]["recorded_onsets"],
            "onsets_before_split_day": c["observables"]["onsets_before_split_day"],
            "infections_before_quarantine": c["infections_before_quarantine"],
            "infections_during_quarantine": c["infections_during_quarantine"],
            "infections_after_quarantine": c["infections_after_quarantine"],
            "confined_passenger_infections_during_quarantine": c[
                "confined_passenger_infections_during_quarantine"
            ],
            "confined_at_activation": c["quarantine_witness"]["confined_at_activation"],
            "ledger_events_during": sum(c["during_quarantine_by_role"].values()),
        }
        for k in ROLES:
            row[f"during_role_{k}"] = c["during_quarantine_by_role"].get(k, 0)
        for k in ZONES:
            row[f"during_zone_{k}"] = c["during_quarantine_by_zone_class"].get(k, 0)
        for k in ROUTES:
            row[f"during_route_{k}"] = c["during_quarantine_by_route"].get(k, 0)
        rows.append(row)
    return rows


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _verdict(a0: float | None, arm: float | None, all_a0: float, all_arm: float,
             n_both: int) -> str:
    if a0 is None or arm is None or n_both == 0:
        return "not eligible (no takeoff overlap)"
    if a0 == 0:
        return "not eligible (A0 conditional median 0)"
    change = (arm - a0) / a0
    if change <= -0.5 and all_arm < all_a0:
        tag = "LOAD-BEARING"
    elif abs(change) < 0.2:
        tag = "non-load-bearing"
    else:
        tag = "indeterminate"
    return f"{tag} ({change:+.0%}, n_both={n_both})"


def _report(rows: list[dict], takeoff: int) -> None:
    by = defaultdict(dict)
    for r in rows:
        by[(r["theta"], r["arm_id"])][r["seed"]] = r
    thetas = sorted({k[0] for k in by})
    arms = sorted({k[1] for k in by})
    for theta in thetas:
        a0 = by[(theta, "A0_declared")]
        to0 = {s for s, r in a0.items() if r["recorded_onsets"] >= takeoff}
        print(f"\n== theta {theta:g}: A0 takeoff {len(to0)}/{len(a0)} ==")
        print(f"{'arm':32s} takeoff  med_all  med_cond(arm)  med_cond(A0 same seeds)  verdict")
        for arm in arms:
            d = by[(theta, arm)]
            to = {s for s, r in d.items() if r["recorded_onsets"] >= takeoff}
            both = sorted(to & to0)
            key = "infections_during_quarantine"
            all_a0 = _median([r[key] for r in a0.values()])
            all_arm = _median([r[key] for r in d.values()])
            cond_arm = _median([d[s][key] for s in both])
            cond_a0 = _median([a0[s][key] for s in both])
            verdict = _verdict(cond_a0, cond_arm, all_a0, all_arm, len(both))
            print(
                f"{arm:32s} {len(to):2d}/{len(d):<2d}  {all_arm!s:>7}  "
                f"{cond_arm!s:>13}  {cond_a0!s:>23}  {verdict}",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    design = json.loads(args.design.read_text())
    takeoff = int(design["takeoff_recorded_onsets"])
    rows = _rows(args.cells)
    if len(rows) != int(design["cells"]):
        raise SystemExit(f"expected {design['cells']} cells, found {len(rows)}")
    with args.csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.csv}")
    _report(rows, takeoff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
