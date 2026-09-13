"""Emit the ``realism_ladder_v1`` campaign manifest.

Steps the introduction realism chain one rung at a time on matched seeds:
``renewal_stationary`` -> ``symptomatic`` -> ``reportable`` (= the shipped
profile default) on the same three hulls and two voyage lengths as
``boarding_posting_v1``, whose ``shipped`` rung is the historical arm and
is NOT re-run here (its matched cells are reused as the comparator). The
screen and denial sweeps ride the ``reportable`` baseline on the classic
hull. Every design coordinate is stated explicitly; seeds are generated
ranges, nothing is derived from a previous manifest at run time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
MANIFEST_PATH = (
    REPO_ROOT
    / "picard_framework"
    / "runs"
    / "mega_cruise_campaign"
    / "realism_ladder_v1_manifest.json"
)

SHIPPED_RUNG = 4.0
SURVEILLANCE = ["syndromic_comp65"]
EPOCHS_7D = 168
EPOCHS_12D = 288

# Matched 1:1 with boarding_posting_v1's matched cells, so each ladder rung
# pairs with the shipped arm voyage-for-voyage.
MATCHED_SEEDS = list(range(5000, 6000))
# Screen/denial arms: 200 seeds continuing the axis block the prior campaign
# used (6000-6149); the extra 50 are new ground, not replicates.
AXIS_SEEDS = list(range(6000, 6200))

LADDER_RUNGS = ["renewal_stationary", "symptomatic", "reportable"]

CAMPAIGN_DESCRIPTION = (
    "The introduction realism ladder: each rung adds one arm of the chain "
    "the shipped boarding mechanism lacked — renewal-identity import rate, "
    "stationary detectable-window ages, the dispersed illness-duration "
    "draw, the symptomatic boarding stream, and the VSP 4.1.1.2 crew "
    "pre-boarding assessment (reportable at epoch 0, no denial). Rung "
    "'shipped' is the historical arm and is supplied by boarding_posting_v1 "
    "at matched seeds; rung 'default' resolves to the shipped profile and "
    "is identical to 'reportable' for norwalk_gi. The matched cells run "
    "1,000 seeds per hull-length cell so posting-frequency and "
    "posting-conditional attack-rate moves are measured, not fitted. "
    "Secondary arms on the classic hull sweep the crew declaration screen "
    "(compliance x recall halflife, plus the c=0 no-screen corner), the "
    "denial-of-boarding response, and the VSP-silent passenger screen — "
    "all operational coordinates with no licensed point, read as axes. "
    "Nothing here is calibrated to VSP/MIDRS or an A-anchor; comparators "
    "are reported and never optimised against."
)

LADDER_DESCRIPTION = (
    "Mechanism ladder, matched seeds 5000-5999: the same cell pairs 1:1 "
    "with boarding_posting_v1's matched cell (the 'shipped' rung) and "
    "across rungs, so each step of the realism chain is attributable to "
    "the mechanism it adds."
)

CREW_SCREEN_DESCRIPTION = (
    "The crew declaration screen on the 'reportable' baseline: "
    "declaration_compliance in {0.25, 0.5, 0.75, 1.0} crossed with recall "
    "halflife in {0.5, 1, 2, inf} days, plus the single c=0 corner — 17 "
    "points. All are operational coordinates with no licensed point; the "
    "sweep measures how much of the clause's effect survives imperfect "
    "compliance and recall."
)

DENIAL_DESCRIPTION = (
    "Denial of boarding on the 'reportable' baseline: c=1, perfect recall, "
    "denial_probability in {0.5, 1.0}. VSP never states a denial response; "
    "this arm measures the truncation the industry practice would impose."
)

PASSENGER_DESCRIPTION = (
    "The VSP-silent passenger screen on the 'reportable' baseline: "
    "declaration_compliance in {0.25, 0.5, 1.0}, perfect recall, full "
    "denial (d=1.0) so the arm isolates the declaration-and-deny path "
    "that Neri 2008 recommends as industry practice."
)

HULLS = {
    "exp": "expedition_cruise_450",
    "cls": "classic_cruise_1900",
    "spr": "spirit_cruise_3000",
}
LENGTHS = {"7d": EPOCHS_7D, "12d": EPOCHS_12D}


def _base_tier(platform: str, epochs: int, description: str) -> dict[str, Any]:
    return {
        "description": description,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_RUNG],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
    }


def ladder_tier(platform: str, epochs: int) -> dict[str, Any]:
    tier = _base_tier(platform, epochs, LADDER_DESCRIPTION)
    tier["boarding_mechanism_rungs"] = LADDER_RUNGS
    tier["seeds"] = MATCHED_SEEDS
    return tier


def crew_screen_tier(platform: str, epochs: int) -> dict[str, Any]:
    tier = _base_tier(platform, epochs, CREW_SCREEN_DESCRIPTION)
    tier["boarding_mechanism_rungs"] = ["reportable"]
    tier["preboarding_crew_points"] = [
        {"compliance": c, "recall_halflife_days": h, "denial_probability": 0.0}
        for c in (0.25, 0.5, 0.75, 1.0)
        for h in (0.5, 1.0, 2.0, None)
    ] + [
        {"compliance": 0.0, "recall_halflife_days": None,
         "denial_probability": 0.0},
    ]
    tier["seeds"] = AXIS_SEEDS
    return tier


def crew_denial_tier(platform: str, epochs: int) -> dict[str, Any]:
    tier = _base_tier(platform, epochs, DENIAL_DESCRIPTION)
    tier["boarding_mechanism_rungs"] = ["reportable"]
    tier["preboarding_crew_points"] = [
        {"compliance": 1.0, "recall_halflife_days": None,
         "denial_probability": d}
        for d in (0.5, 1.0)
    ]
    tier["seeds"] = AXIS_SEEDS
    return tier


def passenger_screen_tier(platform: str, epochs: int) -> dict[str, Any]:
    tier = _base_tier(platform, epochs, PASSENGER_DESCRIPTION)
    tier["boarding_mechanism_rungs"] = ["reportable"]
    tier["preboarding_passenger_points"] = [
        {"compliance": c, "recall_halflife_days": None,
         "denial_probability": 1.0}
        for c in (0.25, 0.5, 1.0)
    ]
    tier["seeds"] = AXIS_SEEDS
    return tier


def build() -> dict[str, Any]:
    """The whole manifest."""
    tiers: dict[str, Any] = {}
    for hull_key, platform in HULLS.items():
        for length_key, epochs in LENGTHS.items():
            tiers[f"rl_{hull_key}_ladder_{length_key}"] = ladder_tier(
                platform, epochs,
            )
    for length_key, epochs in LENGTHS.items():
        tiers[f"rl_cls_crew_screen_{length_key}"] = crew_screen_tier(
            "classic_cruise_1900", epochs,
        )
        tiers[f"rl_cls_crew_denial_{length_key}"] = crew_denial_tier(
            "classic_cruise_1900", epochs,
        )
        tiers[f"rl_cls_pax_screen_{length_key}"] = passenger_screen_tier(
            "classic_cruise_1900", epochs,
        )
    return {
        "campaign": "realism_ladder_v1",
        "description": CAMPAIGN_DESCRIPTION,
        "platform": "classic_cruise_1900",
        "default_epochs": EPOCHS_7D,
        "default_num_agents": 1910,
        "embarkation_date": "2026-01-10",
        "natural_history_clock": "hours",
        "pathogen_configs": {
            "norovirus": {
                "bundle": "active_profiles",
                "pathogen_id": "norwalk_gi",
                "overrides": {"remove": ["sars_cov2_resp"]},
            },
        },
        # Same surveillance configuration as boarding_posting_v1, verbatim:
        # the ladder is measured against the same observation model.
        "surveillance_configs": {
            "syndromic_comp65": {
                "diagnostic_cascade": {"enabled": False},
                "fred_behavior": {
                    "quarantine_compliance": 0.65,
                    "compliance_by_class": {
                        "crew": 0.65,
                        "passenger_elderly": 0.54,
                        "passenger_young": 0.34,
                    },
                },
            },
        },
        "tiers": tiers,
    }


def _tier_run_count(tier: dict[str, Any]) -> int:
    """Runs a tier yields: points x rungs x epochs x surveillance x seeds."""
    from picard_framework.runs.mega_cruise_campaign.boarding_axis import (
        IndexCaseAxis,
    )
    axis = IndexCaseAxis.for_tier(tier, "norwalk_gi")
    return (
        len(axis.points)
        * len(tier["epoch_durations"])
        * len(tier["surveillance_strategies"])
        * len(tier["seeds"])
    )


def main() -> None:
    """Write the manifest and print the per-tier run counts."""
    manifest = build()
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    total = 0
    for tier_id, tier in manifest["tiers"].items():
        count = _tier_run_count(tier)
        total += count
        print(f"{tier_id}: {count}")
    print(f"TOTAL: {total} runs")
    print(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
