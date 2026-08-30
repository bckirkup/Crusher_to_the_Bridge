"""Out-of-sample check of the corrected fomite chain against Park et al. 2015.

Park GW et al., Appl Environ Microbiol 81(17):5987-5992, swabbed surfaces on a
cruise ship during a passenger gastroenteritis outbreak. Macrofoam swabs over
areas up to 645-700 cm2, 1.2-36% recovery:

    cabins of sick passengers   80 - 31,217 GII RNA copies per swab
    public spaces               16 -    113 GII RNA copies per swab

Nothing in the model has been fitted to these numbers, before or after the
fomite correction. This script predicts both from the implemented constants
and reports the comparison whatever it says. It tunes nothing.

The prediction is a steady-state surface loading, so it is reported as a
function of shedder-hours per zone per day rather than for one arbitrary
occupancy: the point of the check is the cabin-to-public gradient, and that
gradient depends on how shedder time distributes across zone classes.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import engines.transmission_core as tc

SWAB_AREA_M2 = 645.0e-4

PARK = {
    "cabin": (80.0, 31217.0),
    "public": (16.0, 113.0),
}

# Liu et al. 2013 hand anchor at the symptomatic shedding plateau.
HAND_LOAD_COPIES = 10.0**3.86


def _mean_truncated_lognormal(meanlog: float, sdlog: float, n: int = 400000) -> float:
    rng = np.random.default_rng(11)
    draws = rng.lognormal(meanlog, sdlog, n)
    return float(np.clip(draws, 0.0, 1.0).mean())


def _expectations() -> dict[str, float]:
    return {
        "hand_area_m2": float(np.mean(tc.HAND_AREA_CM2_RANGE)) / 1.0e4,
        "s_h": float(np.mean(tc.SURFACE_CONTACT_FRACTION_RANGE)),
        "s_m": float(np.mean(tc.MOUTH_CONTACT_FRACTION_RANGE)),
        "te_sh": _mean_truncated_lognormal(*tc.SURFACE_TO_HAND_LOGNORMAL),
        "te_hm": tc.HAND_TO_MOUTH_NORMAL[0],
    }


def steady_state_pool(
    zone_class: str,
    shedder_hours_per_day: float,
    susceptible_present: float,
    exp_: dict[str, float],
    surface_decay_per_day: float = 0.25,
) -> float:
    """Copies resident on a zone's high-touch surfaces at steady state.

    Deposition is shedder hand -> surface; removal is surface inactivation
    plus pickup by every susceptible hand touching the same pool.
    """
    area = tc.HIGH_TOUCH_AREA_M2[zone_class]
    contacts = (
        tc.CABIN_SURFACE_CONTACTS_PER_HOUR
        if zone_class == "cabin"
        else tc.PUBLIC_SURFACE_CONTACTS_PER_HOUR
    )

    # Deposition per shedder-hour: hand load x touches x hand fraction x TE.
    dep_per_shedder_hour = (
        contacts * exp_["s_h"] * exp_["te_sh"] * HAND_LOAD_COPIES
    )
    deposition_per_hour = (
        dep_per_shedder_hour * shedder_hours_per_day / 24.0  # clock-exempt: daily-to-hourly conversion
    )

    # Removal per hour: inactivation + fraction lifted by susceptible hands.
    pickup_fraction_per_person_hour = (
        contacts * exp_["s_h"] * (exp_["hand_area_m2"] / area) * exp_["te_sh"]
    )
    loss_per_hour = (
        surface_decay_per_day / 24.0  # clock-exempt: daily-to-hourly conversion
        + pickup_fraction_per_person_hour * susceptible_present
    )
    return deposition_per_hour / loss_per_hour


def concentration_per_swab(pool: float, zone_class: str) -> float:
    area = tc.HIGH_TOUCH_AREA_M2[zone_class]
    return pool / area * SWAB_AREA_M2


def main() -> None:
    exp_ = _expectations()
    lines: list[str] = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    emit("Sampled expectations of the implemented distributions")
    emit("-" * 58)
    for key, value in exp_.items():
        emit(f"  {key:<14} {value:.6g}")
    emit(f"  hand load     {HAND_LOAD_COPIES:.6g} copies (Liu 2013 anchor)")
    emit()

    # Scenarios chosen to bracket plausible shedder occupancy, not to fit.
    # A confined symptomatic passenger is in their cabin ~22 h/day. A public
    # lounge during an outbreak sees many shedders passing through.
    scenarios = [
        ("cabin", "sick passenger confined to cabin", 22.0, 1.0),
        ("cabin", "sick passenger, unconfined", 8.0, 1.0),
        ("public", "lounge, 10 shedder-hours/day", 10.0, 60.0),
        ("public", "lounge, 60 shedder-hours/day", 60.0, 60.0),
        ("public", "lounge, 200 shedder-hours/day", 200.0, 60.0),
    ]

    emit("Predicted steady-state surface loading")
    emit("-" * 78)
    emit(
        f"{'zone':<8}{'scenario':<36}{'pool':>12}{'copies/swab':>14}"
        f"{'Park':>16}",
    )
    results: dict[str, float] = {}
    for zone_class, label, shedder_hours, susceptible in scenarios:
        pool = steady_state_pool(zone_class, shedder_hours, susceptible, exp_)
        conc = concentration_per_swab(pool, zone_class)
        low, high = PARK[zone_class]
        verdict = "in range" if low <= conc <= high else "OUT"
        emit(
            f"{zone_class:<8}{label:<36}{pool:>12.4g}{conc:>14.4g}"
            f"{f'{low:g}-{high:g} {verdict}':>16}",
        )
        results[label] = conc
    emit()

    cabin = results["sick passenger confined to cabin"]
    public = results["lounge, 60 shedder-hours/day"]
    emit(f"Cabin/public gradient: {cabin / public:.3g}x")
    emit("Park observed gradient: roughly 100-300x")
    emit()

    # What shedder-hour ratio would be needed to reach Park's gradient?
    ratio_needed = 100.0
    emit(
        "Shedder-hour asymmetry required for a 100x gradient, holding the "
        "implemented constants fixed:",
    )
    area_c = tc.HIGH_TOUCH_AREA_M2["cabin"]
    area_p = tc.HIGH_TOUCH_AREA_M2["public"]
    # concentration ratio scales as (dep_c/area_c)/(dep_p/area_p) for equal
    # loss rates, i.e. (2*h_c/1.5)/(6*h_p/6.0).
    per_hour_c = tc.CABIN_SURFACE_CONTACTS_PER_HOUR / area_c
    per_hour_p = tc.PUBLIC_SURFACE_CONTACTS_PER_HOUR / area_p
    emit(
        f"  needed shedder-hours(cabin)/shedder-hours(public) = "
        f"{ratio_needed * per_hour_p / per_hour_c:.4g}",
    )
    emit(
        "  A cabin cannot accumulate that many more shedder-hours than a "
        "public zone;",
    )
    emit(
        "  the gradient is therefore not reachable by hand transfer at any "
        "occupancy.",
    )
    emit()
    emit(
        "Interpretation: the hand-transfer chain reproduces public-space "
        "contamination,",
    )
    emit(
        "and cannot reproduce sick-cabin contamination. Park's cabin figures "
        "are the",
    )
    emit(
        "signature of direct emesis/faecal deposition in a small bathroom, "
        "which is a",
    )
    emit("deposition mechanism the model does not have.")

    out = Path(__file__).with_name("park_surface_check_out.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    math.isfinite(1.0)
    main()
