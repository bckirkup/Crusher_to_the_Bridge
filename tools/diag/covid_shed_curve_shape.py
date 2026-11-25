#!/usr/bin/env python3
"""Read-only shape readout of the ``sars_cov2_resp`` shedding curve (COVID-SHED-CURVE-01).

Assembles the curve the engine emits on the symptom-onset axis: the
presymptomatic gate, the clamp of negative day indices to entry 0, then one
entry per whole day since onset (``KorkinAgent._shedding_curve_point``).
Prints relative emission per day, cumulative shares and decade slopes.
Changes nothing; reads ``data/pathogens/active_profiles.json`` only.

Whole-day arithmetic, valid for this profile only: its presymptomatic window
is a whole number of days and its shedding duration equals the curve length.
Other profiles (fractional windows, clearance before the curve ends) are
refused rather than misreported.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

PATHOGEN_ID = "sars_cov2_resp"
PROFILES = Path(__file__).resolve().parents[2] / "data/pathogens/active_profiles.json"


def load_profile(pathogen_id: str) -> dict:
    data = json.loads(PROFILES.read_text())
    for profile in data["pathogens"]:
        if profile["pathogen_id"] == pathogen_id:
            return profile
    raise SystemExit(f"{pathogen_id} not in {PROFILES}")


def assembled(profile: dict) -> list[tuple[int, float]]:
    """(day since onset, log10 relative to peak) for each emitting day."""
    curve = profile["shedding_curve_log10"]
    peak = max(curve)
    window = float(profile.get("presymptomatic_shedding_days", 0.0))
    if window != math.floor(window) or profile.get("shedding_duration_days") != len(curve):
        raise SystemExit("whole-day readout does not apply to this profile")
    first_day = -int(window)
    return [
        (day, curve[min(max(day, 0), len(curve) - 1)] - peak)
        for day in range(first_day, len(curve))
    ]


def share(days: list[tuple[int, float]], lo: float, hi: float) -> float:
    total = sum(10**rel for _, rel in days)
    return sum(10**rel for day, rel in days if lo <= day < hi) / total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leave-day", type=int, default=2,
                        help="whole day since onset the index leaves (DP: 2)")
    args = parser.parse_args()
    profile = load_profile(PATHOGEN_ID)
    days = assembled(profile)
    inf = float("inf")
    print("day_since_onset  log10_rel_peak  share_of_total")
    for day, rel in days:
        print(f"{day:>15d}  {rel:>14.1f}  {share(days, day, day + 1):.3e}")
    peak_day = max(days, key=lambda d: d[1])[0]
    print(f"peak_day_since_onset {peak_day}")
    print(f"share_before_onset {share(days, -inf, 0):.3e}")
    print(f"share_before_minus3d {share(days, -inf, -3):.3e}")
    print(f"share_onset_day_and_next {share(days, 0, 2):.3e}")
    print(f"share_before_leave_day {share(days, -inf, args.leave_day):.3e}")
    print(f"share_first_7d_post_onset {share(days, 0, 7):.6f}")
    print(f"share_after_day9 {share(days, 10, inf):.3e}")
    for width in (1.0, 2.0):
        n = sum(1 for _, rel in days if rel >= -width)
        print(f"days_within_{width:g}_log10_of_peak {n}")
    rel = dict(days)
    last = days[-1][0]
    print(f"rise_log10_per_day_onset_to_peak {(rel[peak_day] - rel[0]) / peak_day:.3f}")
    print(f"decay_log10_per_day_peak_to_end {(rel[last] - rel[peak_day]) / (last - peak_day):.3f}")
    print(f"decay_log10_per_day_steepest {min(rel[d + 1] - rel[d] for d in range(peak_day, last)):.3f}")


if __name__ == "__main__":
    main()
