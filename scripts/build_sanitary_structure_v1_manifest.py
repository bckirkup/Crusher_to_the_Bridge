"""Emit the two arms of the ``sanitary_structure_v1`` campaign manifest.

#538 gave every hull the shared heads it never had: sanitary blocks
provisioned from VSP/IPC/MLC rules, exhaust-only one-way air, and a
dwell-weighted visit mechanism shipped **default-off** so the baseline
stayed bit-identical. Nothing has moved yet. This campaign is the matched
contrast that says whether the structure matters at all, measured before
any flush emission term exists — so that a later flush route is added to a
structure whose own contribution is already known, rather than to an
unmeasured one.

The arms are ``transmission.sanitary_visit_mode``:

* ``none`` — heads exist in the layout and in the air network, but no host
  ever enters one. Stool events stay where they were. This is the engine
  default and the matched baseline.
* ``dwell_weighted`` — hosts visit the head serving their current zone
  (or their cabin fitting when home), dwell-weighted per Chung 2009 /
  Gwynne 2019, and the existing sourced stool draw is **rerouted** into
  the resolved venue rather than duplicated.

Both arms declare the mode explicitly. Neither inherits the engine
default, so the archive records which mechanism produced it and a later
change of default cannot silently re-label these runs — the discipline the
droplet-deletion arms established.

Every hull runs at its **declared complement**: the complement figures are
lower-berth, and published industry occupancy is 100-108.5% of lower
berth, so the declared complement is a slightly light but class-legitimate
sailing. No occupancy fractions appear here, because an off-complement
headcount makes every per-complement quantity classless (the Arm B
caveat), and this campaign needs posting and attack rate to be readable.

Seeds are a fresh matched block. They are NOT reused from
``hull_compounding_v1`` (7000-7499) or its route rerun (7500-7799),
because those cells carry a swept contact kernel and an off-complement
headcount respectively; implying a pairing across that difference would be
a confound. The instrument here is the within-campaign paired contrast:
each seed produces one ``none`` voyage and one ``dwell_weighted`` voyage
in the same cell, so the difference is the visit mechanism and nothing
else.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
MANIFEST_DIR = (
    REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
)
MANIFEST_PATH = MANIFEST_DIR / "sanitary_structure_v1_manifest.json"

from picard_framework.runs.mega_cruise_campaign.boarding_axis import (  # noqa: E402
    IndexCaseAxis,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402

# Held verbatim from hull_compounding_v1 / realism_ladder_v1: the same
# boarding rung, dose, and observation model, so the readouts compare
# like with like even where the seeds do not pair.
SHIPPED_DOSE = 4.0
SURVEILLANCE = ["syndromic_comp65"]
EPOCHS_7D = 168
EPOCHS_12D = 288
RUNG = "reportable"

ARM_TAGS = {
    "none": "baseline",
    "dwell_weighted": "visits",
}
ARM_DESCRIPTIONS = {
    "none": (
        "Sanitary arm: none — the shared heads added in #538 exist in the "
        "layout and the air network, but no host enters one and stool "
        "events are not rerouted. The engine default and the matched "
        "baseline; declared explicitly rather than inherited."
    ),
    "dwell_weighted": (
        "Sanitary arm: dwell_weighted — hosts visit the head serving "
        "their current zone (cabin fitting when home) on a dwell-weighted "
        "draw from its own rng stream, and the existing sourced stool "
        "draw is rerouted into the resolved venue rather than duplicated. "
        "The arm under test. No flush emission term exists in either arm."
    ),
}

HULLS = {
    "exp": "expedition_cruise_450",
    "cls": "classic_cruise_1900",
    "spr": "spirit_cruise_3000",
}
LENGTHS = {"7d": EPOCHS_7D, "12d": EPOCHS_12D}

# One matched block, shared by both arms and every cell.
MATCHED_SEEDS = list(range(8000, 8500))

CAMPAIGN_DESCRIPTION = (
    "The shared-restroom structure measured on its own, before any flush "
    "emission term exists: transmission.sanitary_visit_mode none vs "
    "dwell_weighted on paired seeds, on the expedition, classic and "
    "spirit hulls at their declared complements, at 7 and 12 days. The "
    "statistics are secondaries per import, the continuous attack-rate "
    "margin, VSP posting frequency, the fomite share of establishments, "
    "and the sanitary execution witness (visits, person-seconds, stool "
    "visits, unresolved venues) — the last of which distinguishes 'the "
    "mechanism ran and was inert' from 'the mechanism never ran', which "
    "no outcome field can. Nothing is calibrated to VSP/MIDRS or an "
    "A-anchor; comparators are reported, never fitted."
)

TIER_DESCRIPTION = (
    "Declared-complement cell: this hull's own layout and complement "
    "under the shipped kernel and the reportable boarding rung, with the "
    "sanitary visit mode declared by the arm. Posting rate and attack "
    "rate are readable here because the complement is the hull's own."
)


def _base_tier(platform: str, epochs: int, mode: str) -> dict[str, Any]:
    return {
        "description": TIER_DESCRIPTION,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_DOSE],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "boarding_mechanism_rungs": [RUNG],
        "num_agents": declared_total(platform),
        "seeds": MATCHED_SEEDS,
        "config_overrides": {
            "transmission": {"sanitary_visit_mode": mode},
        },
    }


def build(*, sanitary_visit_mode: str) -> dict[str, Any]:
    """Build one arm of the contrast, with its mode stamped on every tier."""
    tiers: dict[str, Any] = {}
    for hull_key, platform in HULLS.items():
        for length_key, epochs in LENGTHS.items():
            tier_id = f"san_{hull_key}_{length_key}"
            tiers[tier_id] = _base_tier(platform, epochs, sanitary_visit_mode)
    tag = ARM_TAGS[sanitary_visit_mode]
    return {
        "campaign": f"sanitary_structure_v1_{tag}",
        "description": (
            f"{CAMPAIGN_DESCRIPTION} {ARM_DESCRIPTIONS[sanitary_visit_mode]}"
        ),
        "platform": "classic_cruise_1900",
        "default_epochs": EPOCHS_7D,
        "default_num_agents": declared_total("classic_cruise_1900"),
        "embarkation_date": "2026-01-10",
        "natural_history_clock": "hours",
        "pathogen_configs": {
            "norovirus": {
                "bundle": "active_profiles",
                "pathogen_id": "norwalk_gi",
                "overrides": {"remove": ["sars_cov2_resp"]},
            },
        },
        # Same surveillance configuration as realism_ladder_v1, verbatim.
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
    """Runs a tier yields over every swept axis it declares."""
    axis = IndexCaseAxis.for_tier(tier, "norwalk_gi")
    return (
        len(axis.points)
        * len(tier["epoch_durations"])
        * len(tier["surveillance_strategies"])
        * len(tier["seeds"])
    )


def main() -> None:
    """Write the selected arm's manifest and print per-tier run counts."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sanitary-visit-mode",
        choices=sorted(ARM_TAGS),
        required=True,
        help=(
            "which arm to write; both arms declare "
            "transmission.sanitary_visit_mode explicitly"
        ),
    )
    args = parser.parse_args()
    manifest = build(sanitary_visit_mode=args.sanitary_visit_mode)
    tag = ARM_TAGS[args.sanitary_visit_mode]
    output_path = MANIFEST_PATH.with_name(
        MANIFEST_PATH.name.replace("_manifest.json", f"_{tag}_manifest.json"),
    )
    output_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    total = 0
    for tier_id, tier in manifest["tiers"].items():
        count = _tier_run_count(tier)
        total += count
        print(f"{tier_id}: {count}")
    print(f"TOTAL: {total} runs")
    print(f"wrote {output_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
