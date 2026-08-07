#!/usr/bin/env python3
"""Build C13b Contam paired manifest: small vessels × airborne pathogens.

Matched to C12 recalibration native controls (same run_ids). Thin slice:

  platforms: expedition_cruise_450, classic_cruise_1900
  pathogens: sarscov2, influenza, measles  (higher HVAC route weights)
  doses: mid-grid per pathogen (see SLICE)
  surveillance: none_true, immunity 0.0, first 10 seeds
  Contam runs: 120

Usage (repo root)::

    python scripts/build_c13b_contam_airborne_small_manifest.py
    python scripts/build_c13b_contam_airborne_small_manifest.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT_STR = str(REPO_ROOT)
_SCRIPTS_DIR = str(REPO_ROOT / "scripts")
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from contam_manifest_io import (  # noqa: E402
    load_source_manifest,
    require_repo_file,
    write_manifest,
)

CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
DEFAULT_SOURCE = CAMPAIGN_DIR / "c12_recalibration_manifest.json"
DEFAULT_OUT = CAMPAIGN_DIR / "c13b_contam_airborne_small_manifest.json"

SMALL_PLATFORMS = ["expedition_cruise_450", "classic_cruise_1900"]
THIN_SEED_COUNT = 10
THIN_SURV = ["none_true"]
THIN_IMMUNITY = [0.0]

# Mid doses with outbreak variability on expedition (from C12 native ARs).
SLICE: dict[str, dict[str, Any]] = {
    "sarscov2": {
        "source_tier": "a2_sarscov2_recal",
        "out_tier": "a2_sarscov2_contam_small",
        "doses": [6.0, 6.5],
    },
    "influenza": {
        "source_tier": "a2_influenza_recal",
        "out_tier": "a2_influenza_contam_small",
        "doses": [5.0, 5.5],
    },
    "measles": {
        "source_tier": "a2_measles_recal",
        "out_tier": "a2_measles_contam_small",
        "doses": [4.5, 5.0],
    },
}


def build_manifest(
    source: dict[str, Any],
    *,
    seed_count: int = THIN_SEED_COUNT,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    plats = list(platforms or SMALL_PLATFORMS)
    surv_cfgs = source.get("surveillance_configs") or {}
    none_cfg = surv_cfgs.get("none_true")
    if none_cfg is None:
        raise SystemExit("Source manifest missing surveillance_configs.none_true")

    pathogen_cfgs_src = source.get("pathogen_configs") or {}
    pathogen_cfgs: dict[str, Any] = {}
    tiers: dict[str, Any] = {}

    for pathogen, meta in SLICE.items():
        src_tier_id = meta["source_tier"]
        if src_tier_id not in source.get("tiers", {}):
            raise SystemExit(f"Source missing tier {src_tier_id!r}")
        if pathogen not in pathogen_cfgs_src:
            raise SystemExit(f"Source missing pathogen_configs.{pathogen}")
        src_tier = source["tiers"][src_tier_id]
        seeds = list(src_tier["seeds"][:seed_count])
        if len(seeds) < seed_count:
            raise SystemExit(
                f"{src_tier_id} has only {len(seeds)} seeds; need {seed_count}",
            )
        pathogen_cfgs[pathogen] = pathogen_cfgs_src[pathogen]
        tiers[meta["out_tier"]] = {
            "description": (
                f"C13b Contam small-vessel arm for {pathogen}: matched to "
                f"C12 {src_tier_id} native controls "
                f"(platforms {plats}, doses {meta['doses']}, "
                f"none_true, imm0, {seed_count} seeds)."
            ),
            "pathogen": pathogen,
            "platforms": plats,
            "dose_adjustments": list(meta["doses"]),
            "density_exponents": list(src_tier.get("density_exponents") or [0.75]),
            "pre_immunity_fractions": list(THIN_IMMUNITY),
            "surveillance_strategies": list(THIN_SURV),
            "seeds": seeds,
            "hvac": {"transport_engine": "contamx"},
        }

    return {
        "campaign": "c13b_contam_airborne_small_matched",
        "description": (
            "Local ContamX paired campaign on smaller vessels with airborne "
            "pathogens (sarscov2 / influenza / measles) vs C12 recalibration "
            "native controls. Only hvac.transport_engine differs."
        ),
        "platform": source.get("platform", "mega_cruise_5000"),
        "default_epochs": int(source.get("default_epochs", 168)),
        "default_num_agents": int(source.get("default_num_agents", 7000)),
        "pathogen_configs": pathogen_cfgs,
        "surveillance_configs": {"none_true": none_cfg},
        "tiers": tiers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build C13b Contam airborne/small-vessel paired manifest.",
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed-count", type=int, default=THIN_SEED_COUNT)
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=SMALL_PLATFORMS,
        help="Smaller vessel platform ids",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        require_repo_file(_REPO_ROOT_STR, args.source)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    source = load_source_manifest(_REPO_ROOT_STR, args.source)
    manifest = build_manifest(
        source,
        seed_count=int(args.seed_count),
        platforms=list(args.platforms),
    )

    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        generate_tier_runs,
    )

    total = 0
    for tier_id in manifest["tiers"]:
        runs = list(generate_tier_runs(manifest, tier_id))
        total += len(runs)
        hvac = (runs[0][1].get("config_overrides") or {}).get("hvac") if runs else {}
        print(
            f"  {tier_id}: {len(runs)} runs  "
            f"transport={hvac.get('transport_engine')!r}  "
            f"sample={runs[0][0] if runs else None}",
        )
    expected = (
        len(args.platforms)
        * sum(len(m["doses"]) for m in SLICE.values())
        * int(args.seed_count)
    )
    print(f"  TOTAL={total} (expect {expected})")

    if total != expected:
        print(f"  ERROR: run count mismatch ({total} != {expected})")
        return 1

    if args.dry_run:
        return 0

    try:
        written = write_manifest(_REPO_ROOT_STR, args.out, manifest)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"  wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
