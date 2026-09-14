"""Emit the ``hull_compounding_v1`` campaign manifest.

In ``realism_ladder_v1`` the per-import secondary yield was 1.8 / 6.3 /
7.5 on the expedition / classic / spirit hulls at 7 d (and 3.6 / 17 / 23
at 12 d); per complement those are 0.0040 / 0.0033 / 0.0025 and
0.0080 / 0.0089 / 0.0077 — yield that scales almost exactly with the
number of people aboard, the signature of a mass-action exposure kernel
rather than epidemic compounding. Since imports also scale with
complement, the attack rate then goes as the complement, which is the
residual hull gradient. This campaign asks (i) whether the N-scaling
lives in the headcount or the architecture, and (ii) which admissible
contact-kernel setting removes it.

Arm A sweeps the declared ``transmission.contact_class_exponent`` axis
(phi in {0, 0.5, 1.0}, inside its (-2, 3) bounds) on all three hulls at
both voyage lengths — the scoreable arm. Arm B fixes one hull's
architecture and steps the agent count through fractions of its declared
complement — a classless mechanism probe, explicitly not a
posting-rate / attack-rate / VSP / A9 cell. Arm C replaces the shipped
``per_partner_contact`` kernel wholesale with ``density_dependent``
across its exponent axis — a mechanism contrast, not a candidate
default. Every arm keeps the ``reportable`` boarding rung, the shipped
dose, and the ``syndromic_comp65`` observation model verbatim so cells
pair seed-for-seed with the realism ladder.
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
    / "hull_compounding_v1_manifest.json"
)

from picard_framework.runs.mega_cruise_campaign.boarding_axis import (  # noqa: E402
    IndexCaseAxis,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402

SHIPPED_DOSE = 4.0
SURVEILLANCE = ["syndromic_comp65"]
EPOCHS_7D = 168
EPOCHS_12D = 288
RUNG = "reportable"

PHI_POINTS = [0.0, 0.5, 1.0]
OCCUPANCY_FRACTIONS = (0.25, 0.5, 1.0)
ALPHA_POINTS = [0.0, 0.5, 1.0]

# Arm A pairs seed-for-seed across every hull/length/phi cell.
MATCHED_SEEDS = list(range(7000, 7500))
# Arms B and C share a separate matched block.
PROBE_SEEDS = list(range(7500, 7800))

CAMPAIGN_DESCRIPTION = (
    "The hull-compounding readout: realism_ladder_v1's per-import "
    "secondary yield scaled with the complement aboard (the mass-action "
    "signature), so this campaign separates headcount from architecture "
    "and asks which admissible contact-kernel setting removes the "
    "N-scaling. Arm A sweeps transmission.contact_class_exponent at each "
    "hull's declared complement; arm B steps the agent count through "
    "fractions of a fixed hull's complement as a mechanism probe only; "
    "arm C replaces the shipped per_partner_contact kernel with "
    "density_dependent across its exponent axis. All arms keep the "
    "reportable boarding rung, dose_adjustment 4.0, and the "
    "syndromic_comp65 observation model. Nothing is calibrated to "
    "VSP/MIDRS or an A-anchor; comparators are reported, never fitted."
)

ARM_A_DESCRIPTION = (
    "Kernel sweep at declared complements: "
    "transmission.contact_class_exponent in {0.0, 0.5, 1.0} under the "
    "shipped per_partner_contact mode (phi applies under the shipped "
    "kernel; the mode is not forced). The scoreable arm — matched seeds "
    "7000-7499 pair every hull x length x phi cell 1:1."
)

ARM_B_DESCRIPTION = (
    "Occupancy probe at fixed architecture: this hull's layout run at a "
    "fraction of its declared complement under the shipped kernel. The "
    "two off-complement points are a mechanism probe ONLY — no posting "
    "rate, no attack rate, and no VSP/A9 comparison may be read off "
    "them, because a complement that is not the hull's makes every "
    "per-complement quantity classless (platform_complement's "
    "reasoning). The statistic they exist for is secondaries per import "
    "at fixed architecture. Matched seeds 7500-7799."
)

ARM_C_DESCRIPTION = (
    "Occupancy-scaling ablation: replaces the shipped "
    "per_partner_contact kernel wholesale with density_dependent at "
    "exponents {0.0, 0.5, 1.0} (alpha 0 is occupancy-independent, 1 is "
    "linear in occupancy). Because the engine reads activity_contacts "
    "only under per_partner_contact, this arm also switches that block "
    "off — part of replacing the shipped kernel, not a constant change. "
    "A mechanism contrast, not a candidate default. Matched seeds "
    "7500-7799."
)

HULLS = {
    "exp": "expedition_cruise_450",
    "cls": "classic_cruise_1900",
    "spr": "spirit_cruise_3000",
}
PROBE_HULLS = {"cls": "classic_cruise_1900", "spr": "spirit_cruise_3000"}
LENGTHS = {"7d": EPOCHS_7D, "12d": EPOCHS_12D}


def _base_tier(platform: str, epochs: int, description: str) -> dict[str, Any]:
    return {
        "description": description,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_DOSE],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "boarding_mechanism_rungs": [RUNG],
    }


def build() -> dict[str, Any]:
    """The whole manifest."""
    tiers: dict[str, Any] = {}
    for hull_key, platform in HULLS.items():
        for length_key, epochs in LENGTHS.items():
            tier = _base_tier(platform, epochs, ARM_A_DESCRIPTION)
            tier["contact_class_exponents"] = PHI_POINTS
            tier["seeds"] = MATCHED_SEEDS
            tiers[f"rl_{hull_key}_phi_{length_key}"] = tier
    for hull_key, platform in PROBE_HULLS.items():
        for fraction in OCCUPANCY_FRACTIONS:
            tier = _base_tier(platform, EPOCHS_7D, ARM_B_DESCRIPTION)
            tier["num_agents"] = int(round(fraction * declared_total(platform)))
            tier["seeds"] = PROBE_SEEDS
            tiers[f"rl_{hull_key}_occ{int(fraction * 100)}_7d"] = tier
    for hull_key, platform in HULLS.items():
        tier = _base_tier(platform, EPOCHS_7D, ARM_C_DESCRIPTION)
        tier["contact_modes"] = ["density_dependent"]
        tier["density_exponents"] = ALPHA_POINTS
        # density_dependent replaces the per_partner_contact kernel
        # wholesale; the shipped activity_contacts block is only valid
        # under that kernel, so it is disabled inside this arm.
        tier["config_overrides"] = {
            "transmission": {"activity_contacts": {"enabled": False}},
        }
        tier["seeds"] = PROBE_SEEDS
        tiers[f"rl_{hull_key}_density_7d"] = tier
    return {
        "campaign": "hull_compounding_v1",
        "description": CAMPAIGN_DESCRIPTION,
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
        # Same surveillance configuration as realism_ladder_v1, verbatim:
        # the arms are measured against the same observation model.
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
        * len(tier.get("contact_class_exponents") or [None])
        * len(tier.get("density_exponents") or [None])
        * len(tier.get("contact_modes") or [None])
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
