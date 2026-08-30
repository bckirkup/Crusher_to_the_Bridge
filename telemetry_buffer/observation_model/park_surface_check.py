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
from collections.abc import Callable
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

# norwalk_gi's acute (emetic) clinical phase is dpi 0-2.
EMETIC_WINDOW_DAYS = 3.0

# Fraction of a symptomatic host's vomiting episodes that occur in its own
# cabin rather than wherever it happens to be. THIS QUANTITY IS NOT MEASURED
# ANYWHERE AND IS NOT A MODEL PARAMETER. It is swept here only to report how
# sensitive the cabin/public gradient is to it. It must not be read off Park
# and written into the model; see the note printed at the end.
CABIN_LOCALIZATION_SWEEP = (0.50, 0.80, 0.95, 0.99, 1.00)


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

    loss_per_hour = surface_loss_per_hour(
        zone_class, susceptible_present, exp_, surface_decay_per_day,
    )
    return deposition_per_hour / loss_per_hour


def concentration_per_swab(pool: float, zone_class: str) -> float:
    area = tc.HIGH_TOUCH_AREA_M2[zone_class]
    return pool / area * SWAB_AREA_M2


def mean_episode_load() -> float:
    """Expected genome copies expelled in one vomiting episode.

    Volume is log-uniform over the measured range, so its mean is
    (hi - lo) / ln(hi / lo) rather than the midpoint.
    """
    low, high = tc.EMESIS_VOLUME_ML_RANGE
    mean_volume_ml = (high - low) / math.log(high / low)
    return mean_volume_ml * tc.EMESIS_TITRE_GEC_PER_ML


def emesis_pool_gain_per_episode(zone_class: str) -> float:
    """Copies one episode adds to a zone's high-touch pool."""
    touchable = min(
        1.0,
        tc.HIGH_TOUCH_AREA_M2[zone_class] / tc.EMESIS_DEPOSITION_AREA_M2,
    )
    aerosol_low, aerosol_high = tc.EMESIS_AEROSOL_FRACTION_RANGE
    mean_aerosol = (aerosol_high - aerosol_low) / math.log(
        aerosol_high / aerosol_low,
    )
    return mean_episode_load() * (1.0 - mean_aerosol) * touchable


def surface_loss_per_hour(
    zone_class: str,
    susceptible_present: float,
    exp_: dict[str, float],
    surface_decay_per_day: float = 0.25,
) -> float:
    """Inactivation plus pickup by every susceptible hand on the pool."""
    area = tc.HIGH_TOUCH_AREA_M2[zone_class]
    contacts = (
        tc.CABIN_SURFACE_CONTACTS_PER_HOUR
        if zone_class == "cabin"
        else tc.PUBLIC_SURFACE_CONTACTS_PER_HOUR
    )
    pickup_fraction_per_person_hour = (
        contacts * exp_["s_h"] * (exp_["hand_area_m2"] / area) * exp_["te_sh"]
    )
    return (
        surface_decay_per_day / 24.0  # clock-exempt: daily-to-hourly conversion
        + pickup_fraction_per_person_hour * susceptible_present
    )


def episodes_per_illness_day() -> float:
    """Mean episodes per day while a host is in its emetic phase.

    norwalk_gi's acute (emetic) phase is dpi 0-2, i.e. a three-day window.
    """
    low, high = tc.EMESIS_EPISODES_RANGE
    return 0.5 * (low + high) / EMETIC_WINDOW_DAYS


def _emit_emesis_section(
    emit: Callable[..., None],
    exp_: dict[str, float],
    hand_only: dict[str, float],
) -> None:
    """Add the implemented emesis term and re-report the gradient.

    The hand-chain pools above are unchanged; emesis is an additional
    deposition into the same pools, so the two add.
    """
    per_episode_cabin = emesis_pool_gain_per_episode("cabin")
    per_episode_public = emesis_pool_gain_per_episode("public")
    per_illness_day = episodes_per_illness_day()

    emit("Emesis term as implemented")
    emit("-" * 78)
    emit(f"  mean episode load        {mean_episode_load():.4g} copies")
    emit(f"  episodes per illness-day {per_illness_day:.4g}")
    emit(f"  pool gain per episode    cabin {per_episode_cabin:.4g}, "
         f"public {per_episode_public:.4g} copies")
    emit()

    # Park swabbed cabins *of sick passengers*, i.e. conditioned on an episode
    # having happened there. Report the immediate post-episode load too.
    bolus = concentration_per_swab(per_episode_cabin, "cabin")
    low, high = PARK["cabin"]
    emit(
        f"  single episode, cabin, immediately after: {bolus:.4g} copies/swab",
    )
    emit(
        f"  at Park's stated 1.2-36% swab recovery that reads as "
        f"{bolus * 0.012:.4g}-{bolus * 0.36:.4g} copies/swab, "
        f"against Park's observed {low:g}-{high:g}",
    )
    emit()

    # Time-averaged loading, swept over how localized vomiting is to the
    # host's own cabin. That fraction is unmeasured; see the closing note.
    loss_cabin = surface_loss_per_hour("cabin", 1.0, exp_)
    loss_public = surface_loss_per_hour("public", 60.0, exp_)
    lounge_shedder_equivalents = 60.0 / 24.0  # clock-exempt: shedder-hours/day to concurrent shedders

    emit(
        "Time-averaged loading with emesis, swept over cabin localization f",
    )
    emit("-" * 78)
    emit(
        f"{'f':>6} | {'cabin copies/swab':>18} | {'public copies/swab':>19} | "
        f"{'gradient':>9} | vs Park 100-300x",
    )
    per_illness_hour = per_illness_day / 24.0  # clock-exempt: daily-to-hourly conversion
    for fraction in CABIN_LOCALIZATION_SWEEP:
        cabin_rate = fraction * per_illness_hour
        public_rate = (
            (1.0 - fraction) * per_illness_hour * lounge_shedder_equivalents
        )
        cabin_pool = cabin_rate * per_episode_cabin / loss_cabin
        public_pool = public_rate * per_episode_public / loss_public
        cabin_total = (
            hand_only["sick passenger confined to cabin"]
            + concentration_per_swab(cabin_pool, "cabin")
        )
        public_total = (
            hand_only["lounge, 60 shedder-hours/day"]
            + concentration_per_swab(public_pool, "public")
        )
        gradient = cabin_total / public_total
        verdict = "IN RANGE" if 100.0 <= gradient <= 300.0 else "out of range"
        emit(
            f"{fraction:>6.2f} | {cabin_total:>18.4g} | {public_total:>19.4g} | "
            f"{gradient:>8.4g}x | {verdict}",
        )
    emit()
    emit(
        "f is the fraction of a host's vomiting episodes that occur in its "
        "own cabin.",
    )
    emit(
        "No study measures it. It is NOT a model parameter and the model does "
        "not use",
    )
    emit(
        "it: emesis is deposited wherever the host is, which is f implied by "
        "the",
    )
    emit(
        "schedule rather than declared. This sweep exists to report how much "
        "of the",
    )
    emit(
        "gradient rests on an unmeasured behavioural quantity. Reading f off "
        "Park's",
    )
    emit("gradient would be fitting, and is refused.")


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
        f"{'zone':<8} | {'scenario':<34} | {'pool':>11} | "
        f"{'copies/swab':>11} | {'Park range':>14} | verdict",
    )
    results: dict[str, float] = {}
    for zone_class, label, shedder_hours, susceptible in scenarios:
        pool = steady_state_pool(zone_class, shedder_hours, susceptible, exp_)
        conc = concentration_per_swab(pool, zone_class)
        low, high = PARK[zone_class]
        verdict = "IN RANGE" if low <= conc <= high else "out of range"
        emit(
            f"{zone_class:<8} | {label:<34} | {pool:>11.4g} | "
            f"{conc:>11.4g} | {f'{low:g}-{high:g}':>14} | {verdict}",
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
    _emit_emesis_section(emit, exp_, results)

    out = Path(__file__).with_name("park_surface_check_out.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    math.isfinite(1.0)
    main()
