#!/usr/bin/env python3
"""Check the emesis aerosol path against Alsved 2019, out of sample (#39).

`docs/norovirus/norovirus_open_ledger.md` records that
``EMESIS_AEROSOL_FRACTION_RANGE`` has never been checked against a measured
airborne concentration, and that Alsved et al. 2019 (*CID*, 5-215 copies/m3
beside 26 hospital norovirus patients, positivity associated with vomiting in
the previous 3 hours) is a **check** rather than a source. The check is one
the rebuild made possible and invalidated at the same time: the airborne
norovirus emission is no longer a fraction of continuous shedding, it is a
per-event fraction of the expelled bolus under
``airborne_emission_mode = emesis_conditioned``, so the quantity that can be
compared to a concentration only exists after #352 and the C4 split.

Nothing here selects a value. The aerosol fraction, the per-subject shed
total, the episode count and the airborne half-life are read from the shipped
profile and the engine constants; the comparison is one-way. Two forms are
reported because they fail in different places:

1. **As implemented.** The concentration an occupant of the model's
   well-mixed ``Cabin_Corridor`` zone sees after one episode. The zone is a
   corridor of about ten cabins, not a patient room, so a low answer here is
   a statement about the dilution volume the structure chose.

2. **Implied room volume.** The volume at which the same per-episode aerosol
   mass would reproduce 5-215 copies/m3. This needs no room volume as an
   input, which matters because Alsved's room volumes were not retrieved
   (the paper reports sampling *close to* patients; Bonifait 2015 gives 1 m).
   If the implied volume brackets a patient room, the measured fraction is
   consistent with the measured concentration and the model's shortfall is
   dilution, not the fraction.

The 3-hour window is Alsved's own conditioning window, so concentrations are
reported both at the instant of the episode and as the mean over the 3 hours
that follow, decayed at the profile's airborne half-life. The shipped clock
runs one epoch per day, which is reported alongside: the engine applies that
half-life once per 24-hour epoch, so the reservoir an inhalation dose is
drawn from is not the 3-hour post-episode reservoir Alsved sampled.

Usage::

    python3 scripts/alsved_airborne_check.py --out reports/c7_alsved_airborne_check.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.transmission_core import (  # noqa: E402
    BALCONY_AEROSOL_REDUCTION,
    EMESIS_AEROSOL_FRACTION_RANGE,
    EMESIS_EPISODES_RANGE,
    EMESIS_TOTAL_SHED_GEC_RANGE,
)
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

# Alsved et al. 2019, Clinical Infectious Diseases, Results: "The
# concentrations of airborne norovirus ranged from 5-215 copies/m3".
# Origin code R (results text), evidence grade B (direct measurement in an
# analogous setting: occupied hospital rooms rather than cabins).
ALSVED_COPIES_PER_M3 = (5.0, 215.0)
# Alsved Results: positivity was associated with vomiting within 3 hours
# (odds ratio 8.1, P = .04).
ALSVED_WINDOW_HOURS = 3.0

PROFILES = REPO_ROOT / "data/pathogens/active_profiles.json"
LAYOUT = REPO_ROOT / "data/platforms/mega_cruise_5000/spatial_layout.json"


def profile_interval(
    profile: dict[str, object],
    key: str,
    default: tuple[float, float],
) -> tuple[float, float]:
    """One measured interval from the shipped profile, or the engine default."""
    raw = profile.get(key)
    if raw is None:
        return default
    low, high = raw  # type: ignore[misc]
    return float(low), float(high)


def episode_aerosol_mass_gec(profile: dict[str, object]) -> tuple[float, float]:
    """Aerosolised copies from one episode, at the interval endpoints.

    The engine draws the per-subject cumulative shed once per illness and
    splits it equally over the episodes drawn with it, so the smallest
    per-episode load is the interval floor over the largest episode count and
    the largest is the interval ceiling over one episode. Both endpoints then
    take the aerosol fraction at the matching end, which makes this a span of
    the mechanism rather than a distribution: no draw is simulated and no
    endpoint is preferred.
    """
    shed_low, shed_high = profile_interval(
        profile, "emesis_total_shed_gec_range", EMESIS_TOTAL_SHED_GEC_RANGE,
    )
    episodes_low, episodes_high = profile_interval(
        profile, "emesis_episodes_range", EMESIS_EPISODES_RANGE,
    )
    fraction_low, fraction_high = profile_interval(
        profile, "emesis_aerosol_fraction_range", EMESIS_AEROSOL_FRACTION_RANGE,
    )
    return (
        (shed_low / episodes_high) * fraction_low,
        (shed_high / max(episodes_low, 1.0)) * fraction_high,
    )


def window_mean_factor(half_life_hours: float, window_hours: float) -> float:
    """Mean of an exponentially decaying reservoir over a window, as a factor.

    The reservoir at time t is C0 * 2**(-t / half_life); its mean over
    [0, window] is that factor times C0. Reported so the comparison is against
    a 3-hour mean rather than an instantaneous peak, because Alsved's samples
    were collected over intervals inside that window.
    """
    if half_life_hours <= 0.0 or window_hours <= 0.0:
        return 1.0
    decay = math.log(2.0) / half_life_hours
    return (1.0 - math.exp(-decay * window_hours)) / (decay * window_hours)


def cabin_corridor_volumes() -> dict[str, float]:
    """Cabin-corridor zone volumes, smallest and largest, from the platform."""
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    volumes = [
        float(zone.get("volume_m3", 0.0))
        for zone in layout.get("zones", [])
        if zone.get("type") == "Cabin_Corridor"
    ]
    if not volumes:
        raise ValueError("platform declares no Cabin_Corridor zones")
    return {"min_m3": min(volumes), "max_m3": max(volumes)}


def as_implemented(
    mass_gec: tuple[float, float],
    volumes: dict[str, float],
    mean_factor: float,
    ventilation_factor: float,
) -> dict[str, dict[str, float]]:
    """Zone concentrations the structure actually produces, per episode."""
    mass_low, mass_high = mass_gec
    report: dict[str, dict[str, float]] = {}
    for label, volume in (("largest_zone", volumes["max_m3"]), ("smallest_zone", volumes["min_m3"])):
        instant_low = mass_low * ventilation_factor / volume
        instant_high = mass_high * ventilation_factor / volume
        report[label] = {
            "volume_m3": volume,
            "instant_copies_per_m3_low": instant_low,
            "instant_copies_per_m3_high": instant_high,
            "window_mean_copies_per_m3_low": instant_low * mean_factor,
            "window_mean_copies_per_m3_high": instant_high * mean_factor,
        }
    return report


def implied_volume(
    mass_gec: tuple[float, float],
    mean_factor: float,
) -> dict[str, float]:
    """Room volume at which the model's episode mass reproduces Alsved.

    Reported as a span because both the episode mass and the measured
    concentration are intervals: the smallest volume pairs the least
    aerosolised mass with the highest measured concentration, the largest
    pairs the most mass with the lowest concentration.
    """
    mass_low, mass_high = mass_gec
    measured_low, measured_high = ALSVED_COPIES_PER_M3
    return {
        "low_m3": (mass_low * mean_factor) / measured_high,
        "high_m3": (mass_high * mean_factor) / measured_low,
    }


def containment(
    reported: dict[str, dict[str, float]],
) -> dict[str, dict[str, bool | float]]:
    """Whether each as-implemented span overlaps the measured range."""
    measured_low, measured_high = ALSVED_COPIES_PER_M3
    verdict: dict[str, dict[str, bool | float]] = {}
    for label, point in reported.items():
        low = point["window_mean_copies_per_m3_low"]
        high = point["window_mean_copies_per_m3_high"]
        verdict[label] = {
            "overlaps_measured": high >= measured_low and low <= measured_high,
            "ratio_high_to_measured_low": high / measured_low,
            "ratio_high_to_measured_high": high / measured_high,
        }
    return verdict


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command line for the check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--window-hours", type=float, default=ALSVED_WINDOW_HOURS)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the check and write the result as JSON."""
    args = parse_args(argv)
    bundle = json.loads(PROFILES.read_text(encoding="utf-8"))
    profiles = {
        entry["pathogen_id"]: entry for entry in bundle["pathogens"]
    }
    profile = profiles[args.pathogen_id]
    if profile.get("airborne_emission_mode") != "emesis_conditioned":
        raise ValueError(
            f"{args.pathogen_id} is not emesis_conditioned; the per-event "
            "aerosol mass this check compares does not exist for it",
        )
    half_life = float(profile.get("airborne_half_life_hours", 1.1))
    mean_factor = window_mean_factor(half_life, args.window_hours)
    mass_gec = episode_aerosol_mass_gec(profile)
    volumes = cabin_corridor_volumes()
    reported = as_implemented(
        mass_gec, volumes, mean_factor, BALCONY_AEROSOL_REDUCTION,
    )
    payload = {
        "pathogen_id": args.pathogen_id,
        "measured": {
            "source": "Alsved et al. 2019, Clin Infect Dis",
            "copies_per_m3": list(ALSVED_COPIES_PER_M3),
            "window_hours": args.window_hours,
            "origin": "R",
            "grade": "B",
        },
        "model_inputs": {
            "emesis_total_shed_gec_range": list(
                profile_interval(
                    profile,
                    "emesis_total_shed_gec_range",
                    EMESIS_TOTAL_SHED_GEC_RANGE,
                ),
            ),
            "emesis_episodes_range": list(
                profile_interval(
                    profile, "emesis_episodes_range", EMESIS_EPISODES_RANGE,
                ),
            ),
            "emesis_aerosol_fraction_range": list(
                profile_interval(
                    profile,
                    "emesis_aerosol_fraction_range",
                    EMESIS_AEROSOL_FRACTION_RANGE,
                ),
            ),
            "airborne_half_life_hours": half_life,
            "ventilation_factor": BALCONY_AEROSOL_REDUCTION,
        },
        "episode_aerosol_mass_gec": {
            "low": mass_gec[0],
            "high": mass_gec[1],
        },
        "window_mean_factor": mean_factor,
        "as_implemented": reported,
        "containment": containment(reported),
        "implied_room_volume_m3": implied_volume(mass_gec, mean_factor),
    }
    report = json.dumps(payload, indent=2)
    if args.out is not None:
        destination = resolve_repo_path(str(REPO_ROOT), str(args.out))
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with validated_open(
            destination,
            "w",
            allowed_roots=(str(REPO_ROOT),),
            encoding="utf-8",
        ) as handle:
            handle.write(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
