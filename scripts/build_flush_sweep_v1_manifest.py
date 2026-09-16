"""Emit one arm of the ``flush_sweep_v1`` campaign manifest.

Toilet-flush aerosolisation is the diarrhoeal pathway's missing air
source (design and declared uncertainty: docs/norovirus/
flush_aerosolisation_v1.md). The two primary measurements of the
aerosolised fraction disagree by four to five decades because they
measure different fractions -- Johnson 2013 counts droplet nuclei only
(~1e-9 to 8e-8), Boles 2021 captures near-field larger droplets (~1e-4
to 1e-3) -- and cruise-ship vacuum systems have no virus measurement at
all. No point value is adopted: the frozen span [1e-9, 1e-3] is swept
as a staged design (doc section 8): stage 1 brackets the analytically
predicted crossing with ``off``, 1e-9, 1e-7, 1e-5 on a 100-seed prefix,
and stage 2 places half-decade arms around the measured crossing at
the full 200 seeds. ``--seeds`` takes a PREFIX of the matched block,
never a resample, so every stage pairs run-for-run with every other
and with the item-42 archive; ``--stage-tag`` stamps the stage into
the arm tag so a 100-seed stage-1 arm can never be mistaken for a
200-seed stage-2 arm at the same fraction.

The ``off`` arm is the item-42 ``dwell_weighted`` visits configuration
exactly: ``sanitary_visit_mode = dwell_weighted`` in EVERY arm including
``off``, so the whole sweep pairs against a measured baseline and each
arm's archive names its own fraction (the item-42 lesson: never infer an
arm from a directory name). Cells, surveillance, dose, boarding rung and
seeds are held verbatim from ``sanitary_structure_v1`` so the contrast
is against measured numbers; the seeds are the first 200 of the same
matched block (8000-8199), which also pairs the ``off`` arm run-for-run
against the item-42 archive on the seeds that overlap.

Matched seeds, one image, arms differing only in the swept field. The
cabin-emitter corner sweep is a flag on the same grid
(``--no-flush-cabin-emission``), to be run only at the lowest decade the
primary grid resolves -- it writes a ``_nocab`` arm tag so the archive
cannot be confused with the primary grid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
MANIFEST_DIR = (
    REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
)
MANIFEST_PATH = MANIFEST_DIR / "flush_sweep_v1_manifest.json"

from picard_framework.runs.mega_cruise_campaign.boarding_axis import (  # noqa: E402
    IndexCaseAxis,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402

# Held verbatim from sanitary_structure_v1 / hull_compounding_v1 /
# realism_ladder_v1: the same boarding rung, dose, observation model and
# hull cells, so the contrast is against measured numbers.
SHIPPED_DOSE = 4.0
SURVEILLANCE = ["syndromic_comp65"]
EPOCHS_7D = 168
EPOCHS_12D = 288
RUNG = "reportable"

FRACTION_ARMS = (
    "off",
    "1e-9", "3e-9",
    "1e-8", "3e-8",
    "1e-7", "3e-7",
    "1e-6", "3e-6",
    "1e-5", "3e-5",
    "1e-4", "3e-4",
    "1e-3",
)
# Same arm spellings the campaign uses for its S3 prefixes.
ARM_TAGS = {f: (f if f != "off" else "off") for f in FRACTION_ARMS}

HULLS = {
    "exp": "expedition_cruise_450",
    "cls": "classic_cruise_1900",
    "spr": "spirit_cruise_3000",
}
LENGTHS = {"7d": EPOCHS_7D, "12d": EPOCHS_12D}

# The first 200 of the sanitary_structure_v1 matched block: identical
# across every arm of this sweep (the instrument), and run-for-run
# paired with the item-42 visits arm on the seeds that overlap.
MATCHED_SEEDS = list(range(8000, 8200))

CAMPAIGN_DESCRIPTION = (
    "Toilet-flush aerosolisation swept across its whole sourced span: "
    "transmission.flush_aerosol_fraction in {off, 1e-9..1e-3} on paired "
    "seeds, with sanitary_visit_mode dwell_weighted in every arm so the "
    "shared heads added in #538 are the venue the route needs. Cells are "
    "the expedition, classic and spirit hulls at declared complement, 7 "
    "and 12 days -- the same six cells as items 41 and 42. The statistics "
    "are secondaries per import, the continuous attack-rate margin, VSP "
    "posting frequency, and the flush execution witness (flush_events, "
    "flush_aerosol_emitted, flush_recipients, flush_dose_delivered), "
    "which distinguishes 'the route ran and moved nothing' from 'the "
    "route never ran'. The sweep reports which decades matter; it may "
    "not conclude that the decade best matching A9 or A4 is the true one. "
    "Nothing is calibrated to VSP/MIDRS or an A-anchor."
)

TIER_DESCRIPTION = (
    "Declared-complement cell: this hull's own layout and complement "
    "under the shipped kernel and the reportable boarding rung, with "
    "sanitary_visit_mode dwell_weighted and the flush fraction declared "
    "by the arm. Posting rate and attack rate are readable here because "
    "the complement is the hull's own."
)

ARM_DESCRIPTIONS = {
    "off": (
        "Flush arm: off -- the item-42 dwell_weighted configuration "
        "exactly. The shared heads execute and are measured inert; this "
        "is the matched baseline the whole sweep pairs against."
    ),
    "swept": (
        "Flush arm: the declared aerosolised fraction of the ~107 g bowl "
        "deposit per flush, inside the frozen [1e-9, 1e-3] refusal band "
        "spanning Johnson 2013 and Boles 2021. No point value is adopted."
    ),
    "nocab": (
        "Corner sweep: cabin-venue flush emission disabled "
        "(flush_cabin_emission false) at the same fraction -- run only "
        "where the primary grid resolves a paired contrast."
    ),
}


def _base_tier(
    platform: str,
    epochs: int,
    fraction: float,
    cabin_emission: bool,
    seeds: list[int],
) -> dict[str, Any]:
    return {
        "description": TIER_DESCRIPTION,
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [SHIPPED_DOSE],
        "surveillance_strategies": SURVEILLANCE,
        "epoch_durations": [epochs],
        "boarding_mechanism_rungs": [RUNG],
        "num_agents": declared_total(platform),
        "seeds": seeds,
        "config_overrides": {
            "transmission": {
                "sanitary_visit_mode": "dwell_weighted",
                "flush_aerosol_fraction": fraction,
                "flush_cabin_emission": cabin_emission,
            },
        },
    }


def _arm_tag(arm: str, cabin_emission: bool, stage_tag: str | None) -> str:
    """Filename/campaign tag; stage and cabin-emitter suffixes compose."""
    tag = arm
    if stage_tag is not None:
        tag = f"{tag}_{stage_tag}"
    if not cabin_emission:
        tag = f"{tag}_nocab"
    return tag


def _checked_seeds(n: int) -> list[int]:
    """First N of the matched block -- a prefix, never a resample."""
    if not 1 <= n <= len(MATCHED_SEEDS):
        raise ValueError(
            f"--seeds must be in [1, {len(MATCHED_SEEDS)}], got {n!r}"
        )
    return MATCHED_SEEDS[:n]


def _checked_stage_tag(tag: str | None) -> str | None:
    """Stage tags are lowercase alphanumeric, e.g. ``s1``/``s2``."""
    if tag is None:
        return None
    if not re.fullmatch(r"[a-z0-9]+", tag):
        raise ValueError(
            f"--stage-tag must match [a-z0-9]+, got {tag!r}"
        )
    return tag


def build(
    *,
    arm: str,
    cabin_emission: bool,
    seeds: int = len(MATCHED_SEEDS),
    stage_tag: str | None = None,
) -> dict[str, Any]:
    """Build one arm of the sweep, its coordinates stamped on every tier."""
    fraction = 0.0 if arm == "off" else float(arm)
    seed_block = _checked_seeds(seeds)
    stage_tag = _checked_stage_tag(stage_tag)
    tiers: dict[str, Any] = {}
    for hull_key, platform in HULLS.items():
        for length_key, epochs in LENGTHS.items():
            tier_id = f"fl_{hull_key}_{length_key}"
            tiers[tier_id] = _base_tier(
                platform, epochs, fraction, cabin_emission, seed_block,
            )
    tag = _arm_tag(arm, cabin_emission, stage_tag)
    description_key = (
        "nocab" if not cabin_emission else ("off" if arm == "off" else "swept")
    )
    return {
        "campaign": f"flush_sweep_v1_{tag}",
        "description": (
            f"{CAMPAIGN_DESCRIPTION} {ARM_DESCRIPTIONS[description_key]}"
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
        # Same surveillance configuration as sanitary_structure_v1, verbatim.
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
        "--flush-aerosol-fraction",
        choices=list(FRACTION_ARMS),
        required=True,
        help=(
            "aerosolised bowl-load fraction for this arm; 'off' is the "
            "item-42 visits configuration exactly"
        ),
    )
    parser.add_argument(
        "--flush-cabin-emission",
        dest="flush_cabin_emission",
        action="store_true",
        default=True,
        help="emit at own-fittings cabin venues (default)",
    )
    parser.add_argument(
        "--no-flush-cabin-emission",
        dest="flush_cabin_emission",
        action="store_false",
        help="corner sweep: disable cabin-venue emission",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=len(MATCHED_SEEDS),
        help=(
            "take the first N seeds of the matched 8000-8199 block "
            "(a prefix, never a resample); default all 200"
        ),
    )
    parser.add_argument(
        "--stage-tag",
        default=None,
        help=(
            "optional stage stamp [a-z0-9]+ appended to the arm tag, e.g. "
            "s1 -> flush_sweep_v1_1e-7_s1; keeps a 100-seed stage-1 arm "
            "distinct from a 200-seed stage-2 arm at the same fraction"
        ),
    )
    args = parser.parse_args()
    manifest = build(
        arm=args.flush_aerosol_fraction,
        cabin_emission=args.flush_cabin_emission,
        seeds=args.seeds,
        stage_tag=args.stage_tag,
    )
    tag = _arm_tag(
        args.flush_aerosol_fraction, args.flush_cabin_emission, args.stage_tag,
    )
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
