"""Emit the ``boarding_posting_v1`` campaign manifest.

The manifest is generated rather than hand-written only because its seed
blocks are long; every design coordinate below is stated explicitly here and
nothing is derived from a previous manifest at run time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    REPO_ROOT
    / "picard_framework"
    / "runs"
    / "mega_cruise_campaign"
    / "boarding_posting_v1_manifest.json"
)

SHIPPED_RUNG = 4.0
SURVEILLANCE = ["syndromic_comp65"]
EPOCHS_7D = 168
EPOCHS_12D = 288

# Disjoint from hull_posting_v1 (3000-4049) and expedition_posting_v2, so a
# pooled reading of the two campaigns never shares a seed across arms.
MATCHED_SEEDS = list(range(5000, 6000))
AXIS_SEEDS = list(range(6000, 6150))

CAMPAIGN_DESCRIPTION = (
    "Measure posting frequency and the attack rate conditional on posting "
    "when infection arrives through the shipped boarding-prevalence channel "
    "instead of a fiat index case. Every posting measurement taken so far "
    "(expedition_posting_v2, hull_posting_v1) declared "
    "fiat_index_case with initial_infected 1, which withdraws the initiation "
    "block and replaces the drawn boarding cohort with exactly one seeded "
    "host. That is a mechanism choice, not a neutral default: the profiles "
    "norwalk_gi and norovirus_gii4 both ship a boarding block "
    "(mode prevalence, passenger 0.0325, crew 0.0185) and engines/initiation.py "
    "owns them, so a run without the fiat flag draws an embarking infected "
    "cohort per role and assigns each host a boarding state "
    "(never symptomatic, presymptomatic, or convalescent) with a plausible "
    "days-since-infection. This campaign is the matched A/B of those two "
    "introduction mechanisms at the shipped release rung, on the same three "
    "hulls and the same two voyage lengths as hull_posting_v1 and "
    "expedition_posting_v2, so the difference is attributable to the "
    "introduction process alone. Motivation, stated as a hypothesis and not "
    "as a prediction: a single fiat index case makes every voyage an "
    "all-or-nothing establishment lottery, which is one way to produce the "
    "archived between-voyage distribution (most voyages at the index case "
    "alone, the whole mean carried in a thin tail of large epidemics) that "
    "reproduces the observed A8 mean incidence while posting far too often "
    "at 7 days. A prevalence draw scales the number of introductions with "
    "complement and spreads them across boarding states. Its effect on "
    "posting frequency is not predicted here and may raise it: the drawn "
    "cohort is larger than one host, and whether posting falls depends on "
    "how few of those imports are presymptomatic and therefore capable of "
    "generating reported cases aboard. Both directions are reportable "
    "results. Nothing is fitted: the release rung is held at the shipped "
    "4.0, the prevalence axis is swept only across the register's own Grade B "
    "intervals, and the presymptomatic share is swept because it is Grade C "
    "and derived rather than measured. Comparators (A4 per-hull reported "
    "passenger AR, A9 fleet and length-resolved posting rates) are reported "
    "and never optimised against."
)

MATCHED_DESCRIPTION = (
    "Matched comparator cell: shipped release rung, mid compliance, "
    "boarding channel on (no fiat_index_case key, so initiation draws the "
    "embarking cohort at the profile's own prevalence and the register's "
    "default state split: never_symptomatic_fraction 0.29, the "
    "adult-challenge regime midpoint, and presymptomatic_share 0.04). "
    "One thousand voyages resolves a posting frequency of a few per "
    "thousand, and pairs 1:1 with the same cell in {prior} for the "
    "fiat-index-case arm."
)

PREVALENCE_DESCRIPTION = (
    "The two sourced boarding-prevalence intervals at their corners "
    "(passenger [0.025, 0.040] x crew [0.007, 0.030], Grade B, "
    "docs/parameter_provenance_register.md). Corners rather than midpoints, "
    "and crossed rather than paired low-low/high-high, so a posting or "
    "attack-rate response can be attributed to the passenger or the crew "
    "import separately: the ledger records that each role's prevalence "
    "drives mainly its own arm, and the crew arm's level on a short voyage "
    "is set as much by how many crew board carrying it as by anything "
    "caught aboard. No point inside an interval is licensed as a value; the "
    "axis is read, not a single run."
)

PRESYMPTOMATIC_DESCRIPTION = (
    "The boarding state split's presymptomatic share, swept because it is "
    "Grade C and derived from the profile's own shedding geometry "
    "(0.5 / (0.5 + 15 - 3) = 0.04) rather than measured. It is the "
    "coordinate that converts imported hosts into reportable index cases "
    "aboard: an import drawn convalescent has already had its illness and a "
    "never-symptomatic import never reports, so posting frequency should "
    "depend on this share more strongly than on the prevalence itself. The "
    "0.02 and 0.08 points bracket the derived value by a factor of two in "
    "each direction and are not licensed as values."
)


def matched_tier(platform: str, epochs: int, prior: str) -> dict[str, Any]:
    """One matched comparator cell: one hull, one voyage length."""
    return {
        "description": MATCHED_DESCRIPTION.format(prior=prior),
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_RUNG],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "seeds": MATCHED_SEEDS,
    }


def prevalence_tier(platform: str, epochs: int) -> dict[str, Any]:
    """The crossed corners of the two sourced prevalence intervals."""
    return {
        "description": PREVALENCE_DESCRIPTION,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_RUNG],
        "boarding_prevalence_points": [
            {"passenger": 0.025, "crew": 0.007},
            {"passenger": 0.025, "crew": 0.030},
            {"passenger": 0.040, "crew": 0.007},
            {"passenger": 0.040, "crew": 0.030},
        ],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "seeds": AXIS_SEEDS,
    }


def presymptomatic_tier(platform: str, epochs: int) -> dict[str, Any]:
    """The derived presymptomatic share, bracketed by a factor of two."""
    return {
        "description": PRESYMPTOMATIC_DESCRIPTION,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_RUNG],
        "presymptomatic_shares": [0.02, 0.04, 0.08],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "seeds": AXIS_SEEDS,
    }


def build() -> dict[str, Any]:
    """The whole manifest."""
    tiers: dict[str, Any] = {
        "c1_exp_boarding_7d": matched_tier(
            "expedition_cruise_450", EPOCHS_7D, "expedition_posting_v2",
        ),
        "c1_exp_boarding_12d": matched_tier(
            "expedition_cruise_450", EPOCHS_12D, "expedition_posting_v2",
        ),
        "c1_cls_boarding_7d": matched_tier(
            "classic_cruise_1900", EPOCHS_7D, "hull_posting_v1",
        ),
        "c1_cls_boarding_12d": matched_tier(
            "classic_cruise_1900", EPOCHS_12D, "hull_posting_v1",
        ),
        "c1_spr_boarding_7d": matched_tier(
            "spirit_cruise_3000", EPOCHS_7D, "hull_posting_v1",
        ),
        "c1_spr_boarding_12d": matched_tier(
            "spirit_cruise_3000", EPOCHS_12D, "hull_posting_v1",
        ),
        "c1_cls_prevalence_7d": prevalence_tier("classic_cruise_1900", EPOCHS_7D),
        "c1_cls_prevalence_12d": prevalence_tier("classic_cruise_1900", EPOCHS_12D),
        "c1_cls_presymptomatic_7d": presymptomatic_tier(
            "classic_cruise_1900", EPOCHS_7D,
        ),
        "c1_cls_presymptomatic_12d": presymptomatic_tier(
            "classic_cruise_1900", EPOCHS_12D,
        ),
        "c1_exp_presymptomatic_7d": presymptomatic_tier(
            "expedition_cruise_450", EPOCHS_7D,
        ),
    }
    return {
        "campaign": "boarding_posting_v1",
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
        # Copied verbatim from hull_posting_v1_manifest.json so the matched
        # cells differ from the fiat-index-case arm in the introduction
        # mechanism and in nothing else.
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


def main() -> None:
    """Write the manifest."""
    MANIFEST_PATH.write_text(
        json.dumps(build(), indent=2) + "\n", encoding="utf-8",
    )
    print(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
