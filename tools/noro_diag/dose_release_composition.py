#!/usr/bin/env python3
"""Chain-composed environmental release behind ``dose_adjustment`` (NORO-DOSE-REFIT-01).

Purpose
-------
``dose_adjustment`` (alias ``environmental_faecal_release_log10_g_per_epoch``,
resolved by ``environmental_release_log10_per_day``) asserts ``-log10`` grams
of stool-equivalent material released to the environment per ill host-day.
On the post-#724 engine no dose-bearing consumer reads the quantity on the
shipped modes (``per_partner_contact`` doses from donor hand load, emesis has
its own Kirby emitter, the droplet/environmental-reservoir channels are zero
or absent for ``norwalk_gi``), so the constant is a *claim about the model*
rather than a tuning knob: this script computes what the deposit chain
actually releases per ill host-day from the engine's own constants, so the
asserted value can be restated truthfully.

Composition
-----------
The release per ill host-day is:

    release = E[propensity] x stool_events_per_day x hand_target_grams

where:

* ``hand_target_grams`` = ``10^(HAND_LOAD_LOG10_GEC + curve -
  HAND_LOAD_REFERENCE_PEAK_LOG10)`` GEC of load per recontamination,
  expressed in stool-equivalent grams by dividing through the day-T titre:
  ``10^(3.86 + T - 11) / 10^T = 10^-7.14`` g — titre-independent.
* ``E[propensity]`` = mean of ``HAND_CARRIAGE_PROPENSITY_BETA`` — the
  Bernoulli-thinning probability that a defecation recontaminates the hand.
* ``stool_events_per_day`` — the profile's ``baseline``/``diarrhoeal``
  rates, weighted by the illness-duration table's acute share.

The emesis chain is reported separately: on the shipped engine emesis mass
is emitted by ``_emit_emesis`` (Kirby titre/volume constants) and never
reads ``dose_adjustment``, so folding it into the release constant would
double-count it. Its expectation is printed for the ledger's comparison.

Nothing here fits a parameter to an output; everything is composed from
constants with provenance rows already in the register.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    HAND_CARRIAGE_PROPENSITY_BETA,
    HAND_LOAD_LOG10_GEC,
    HAND_LOAD_REFERENCE_PEAK_LOG10,
)
from engines.transmission_core import (  # noqa: E402
    EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE,
    EMESIS_DETECTABLE_MIN_EPISODES,
    EMESIS_EPISODES_RANGE,
    EMESIS_TITRE_GEC_PER_ML_RANGE,
    EMESIS_VOLUME_ML_RANGE,
    emesis_episode_weights,
)
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

PATHOGEN_ID = "norwalk_gi"


def _load_profile(bundle: str) -> dict[str, Any]:
    """The norwalk_gi profile dict from a pathogen bundle JSON."""
    path = resolve_repo_path(
        str(REPO_ROOT), f"data/pathogens/{bundle}.json",
    )
    with validated_open(
        str(path), "r", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        bundle_doc = json.load(handle)
    for entry in bundle_doc["pathogens"]:
        if entry.get("pathogen_id") == PATHOGEN_ID:
            return entry
    raise SystemExit(f"{PATHOGEN_ID} not in bundle {bundle}")


def _loguniform_mean(low: float, high: float) -> float:
    """Expectation of exp(U(log lo, log hi))."""
    return (high - low) / (math.log(high) - math.log(low))


def _illness_acute_share(profile: dict[str, Any]) -> tuple[float, float, float]:
    """Fraction of a symptomatic illness spent at the diarrhoeal rate.

    The survival table gives P(illness lasts >= day); E[days ill] is its
    sum. The emetic/diarrhoeal window is the clinical phase carrying the
    ``vomiting`` feature (dpi 0..dpi_max+1).
    """
    phases = (
        profile.get("clinical_presentation", {}).get("phases") or []
    )
    emetic_days = max(
        (
            float(phase.get("dpi_max", 0)) + 1.0 - float(
                phase.get("dpi_min", 0),
            )
            for phase in phases
            if "vomiting" in phase.get("features", [])
        ),
        default=0.0,
    )
    survival = profile.get("illness_duration", {}).get("survival") or []
    mean_illness_days = sum(
        float(point.get("probability", 0.0)) for point in survival
    )
    acute_days = min(emetic_days, mean_illness_days)
    return (
        acute_days,
        mean_illness_days,
        acute_days / mean_illness_days if mean_illness_days else 0.0,
    )


def _emesis_expectation() -> dict[str, float]:
    """E[emesis mass per vomiting illness] in GEC and stool-equivalent g."""
    low, high = EMESIS_EPISODES_RANGE
    weights = emesis_episode_weights(int(low), int(high))
    mean_episodes = sum(
        k * w for k, w in enumerate(weights, start=int(low))
    )
    uncensored_share = sum(
        w
        for k, w in enumerate(weights, start=int(low))
        if k >= EMESIS_DETECTABLE_MIN_EPISODES
    )
    mean_volume_ml = _loguniform_mean(*EMESIS_VOLUME_ML_RANGE)
    mean_titre_unc = _loguniform_mean(*EMESIS_TITRE_GEC_PER_ML_RANGE)
    mean_titre_cens = _loguniform_mean(
        *EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE,
    )
    mean_titre = (
        uncensored_share * mean_titre_unc
        + (1.0 - uncensored_share) * mean_titre_cens
    )
    episode_gec = mean_volume_ml * mean_titre
    illness_gec = mean_episodes * episode_gec
    # Stool-equivalent grams at the reference peak titre.
    gram_equiv = illness_gec / 10.0 ** HAND_LOAD_REFERENCE_PEAK_LOG10
    return {
        "mean_episodes": mean_episodes,
        "uncensored_share": uncensored_share,
        "mean_volume_ml": mean_volume_ml,
        "mean_titre_gec_per_ml": mean_titre,
        "mean_load_per_episode_gec": episode_gec,
        "mean_load_per_vomiting_illness_gec": illness_gec,
        "mean_load_per_vomiting_illness_g_stool_equiv": gram_equiv,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default="norwalk_only")
    args = parser.parse_args(argv)
    profile = _load_profile(args.bundle)

    a, b = HAND_CARRIAGE_PROPENSITY_BETA
    propensity_mean = a / (a + b)
    propensity_p5 = float(
        __import__("scipy.stats", fromlist=["beta"]).beta.ppf(
            0.05, a, b,
        ),
    )
    propensity_p95 = float(
        __import__("scipy.stats", fromlist=["beta"]).beta.ppf(
            0.95, a, b,
        ),
    )
    # 10^(3.86 + T - 11) GEC of hand load == 10^-7.14 g of stool at the
    # reference peak — the titre cancels when the load is expressed in the
    # stool mass that produced it.
    hand_target_g = 10.0 ** (
        HAND_LOAD_LOG10_GEC - HAND_LOAD_REFERENCE_PEAK_LOG10
    )
    events = profile["stool_events_per_day"]
    baseline_rate = float(events["baseline"])
    diarrhoeal_rate = float(events["diarrhoeal"])
    acute_days, mean_illness_days, _ = _illness_acute_share(
        profile,
    )
    shedding_days = float(profile.get("shedding_duration_days", 15))
    mean_events = (
        acute_days * diarrhoeal_rate
        + (shedding_days - acute_days) * baseline_rate
    ) / shedding_days

    def release_g_per_day(propensity: float) -> float:
        return propensity * mean_events * hand_target_g

    central = release_g_per_day(propensity_mean)
    symptomatic_day = propensity_mean * diarrhoeal_rate * hand_target_g
    asymptomatic_day = propensity_mean * baseline_rate * hand_target_g
    out = {
        "pathogen_id": PATHOGEN_ID,
        "bundle": args.bundle,
        "asserted_quantity": (
            "-log10 grams of stool-equivalent released to the environment "
            "per ill host-day (resolved per-day despite the per-epoch "
            "spelling of the alias key)"
        ),
        "hand_chain": {
            "hand_target_g_stool_equiv": hand_target_g,
            "propensity_beta": list(HAND_CARRIAGE_PROPENSITY_BETA),
            "propensity_mean": propensity_mean,
            "propensity_p5": propensity_p5,
            "propensity_p95": propensity_p95,
            "stool_events_per_day": {
                "baseline": baseline_rate,
                "diarrhoeal": diarrhoeal_rate,
                "acute_days": acute_days,
                "mean_illness_days": mean_illness_days,
                "shedding_window_days": shedding_days,
                "window_mean": mean_events,
            },
            "release_g_per_ill_day": {
                "acute_day": symptomatic_day,
                "non_acute_day": asymptomatic_day,
                "window_mean": central,
                "p5_propensity": release_g_per_day(propensity_p5),
                "p95_propensity": release_g_per_day(propensity_p95),
            },
        },
        "emesis_chain_separate_emitter": _emesis_expectation(),
        "derived_dose_adjustment": {
            "window_mean": -math.log10(central),
            "acute_day": -math.log10(symptomatic_day),
            "non_acute_day": -math.log10(asymptomatic_day),
            "interval": [
                -math.log10(release_g_per_day(propensity_p95)),
                -math.log10(release_g_per_day(propensity_p5)),
            ],
        },
    }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
