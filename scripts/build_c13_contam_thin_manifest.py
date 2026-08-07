#!/usr/bin/env python3
"""Build the C13 Contam thin matched-campaign manifest from C12c finecal.

Thin slice (80 Contam runs; native controls already in results/c12c):
  4 platforms x doses [10.4, 10.6] x none_true x first 10 C12c seeds.

Usage (repo root)::

    python scripts/build_c13_contam_thin_manifest.py
    python scripts/build_c13_contam_thin_manifest.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT_STR = str(REPO_ROOT)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)

CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
DEFAULT_SOURCE = CAMPAIGN_DIR / "c12c_fine_calibration_manifest.json"
DEFAULT_OUT = CAMPAIGN_DIR / "c13_contam_thin_manifest.json"

THIN_DOSES = [10.4, 10.6]
THIN_SURV = ["none_true"]
THIN_SEED_COUNT = 10
SOURCE_TIER = "a2_noro_finecal"
OUT_TIER = "a2_noro_contam_thin"


def build_manifest(
    source: dict[str, Any],
    *,
    doses: list[float] = THIN_DOSES,
    seed_count: int = THIN_SEED_COUNT,
) -> dict[str, Any]:
    if SOURCE_TIER not in source.get("tiers", {}):
        raise SystemExit(f"Source manifest missing tier {SOURCE_TIER!r}")
    fine = dict(source["tiers"][SOURCE_TIER])
    seeds = list(fine["seeds"][:seed_count])
    if len(seeds) < seed_count:
        raise SystemExit(
            f"Source tier has only {len(seeds)} seeds; need {seed_count}",
        )
    surv_cfgs = source.get("surveillance_configs") or {}
    none_cfg = surv_cfgs.get("none_true")
    if none_cfg is None:
        raise SystemExit("Source manifest missing surveillance_configs.none_true")

    pathogen_cfgs = source.get("pathogen_configs") or {}
    noro = pathogen_cfgs.get("norovirus")
    if noro is None:
        raise SystemExit("Source manifest missing pathogen_configs.norovirus")

    tier: dict[str, Any] = {
        "description": (
            "C13 Contam thin arm: matched to C12c finecal native controls "
            f"(doses {doses}, none_true, {seed_count} seeds). "
            "Run ContamX only; pair on shared run_id."
        ),
        "pathogen": fine["pathogen"],
        "platforms": list(fine["platforms"]),
        "dose_adjustments": list(doses),
        "density_exponents": list(fine.get("density_exponents") or [0.75]),
        "pre_immunity_fractions": list(fine.get("pre_immunity_fractions") or [0.0]),
        "surveillance_strategies": list(THIN_SURV),
        "seeds": seeds,
        "hvac": {"transport_engine": "contamx"},
    }

    return {
        "campaign": "c13_contam_thin_matched",
        "description": (
            "Local ContamX thin matched campaign vs C12c finecal native "
            "controls (no native re-run)."
        ),
        "platform": source.get("platform", "mega_cruise_5000"),
        "default_epochs": int(source.get("default_epochs", 168)),
        "default_num_agents": int(source.get("default_num_agents", 7000)),
        "pathogen_configs": {"norovirus": noro},
        "surveillance_configs": {"none_true": none_cfg},
        "tiers": {OUT_TIER: tier},
    }


def _resolve_repo_cli_path(path: Path) -> str:
    """Confine a CLI path under the repository root (Sonar S8707)."""
    from simulation_utils.paths import resolve_repo_path

    return resolve_repo_path(_REPO_ROOT_STR, str(path))


def _load_source_manifest(source_arg: Path) -> dict[str, Any]:
    from simulation_utils.paths import validated_open

    source_path = _resolve_repo_cli_path(source_arg)
    with validated_open(
        source_path, allowed_roots=(_REPO_ROOT_STR,), encoding="utf-8",
    ) as fh:
        return json.load(fh)


def _write_manifest(out_arg: Path, manifest: dict[str, Any]) -> str:
    import os

    from simulation_utils.paths import prepare_output_directory, validated_open

    out_path = _resolve_repo_cli_path(out_arg)
    prepare_output_directory(
        os.path.dirname(out_path), allowed_roots=(_REPO_ROOT_STR,),
    )
    with validated_open(
        out_path, "w", allowed_roots=(_REPO_ROOT_STR,), encoding="utf-8",
    ) as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build C13 Contam thin manifest from C12c finecal.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"C12c finecal manifest (default: {DEFAULT_SOURCE.name})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT.name})",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=THIN_SEED_COUNT,
        help=f"Number of leading C12c seeds to keep (default {THIN_SEED_COUNT})",
    )
    parser.add_argument(
        "--doses",
        type=float,
        nargs="+",
        default=THIN_DOSES,
        help="Dose adjustments to keep (default 10.4 10.6)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected run count without writing the file",
    )
    args = parser.parse_args(argv)

    try:
        source_path = _resolve_repo_cli_path(args.source)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not Path(source_path).is_file():
        raise SystemExit(f"Source manifest not found: {args.source}")

    source = _load_source_manifest(args.source)
    manifest = build_manifest(
        source, doses=list(args.doses), seed_count=int(args.seed_count),
    )

    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        generate_tier_runs,
    )

    runs = list(generate_tier_runs(manifest, OUT_TIER))
    n_plat = len(manifest["tiers"][OUT_TIER]["platforms"])
    n_dose = len(manifest["tiers"][OUT_TIER]["dose_adjustments"])
    n_seed = len(manifest["tiers"][OUT_TIER]["seeds"])
    expected = n_plat * n_dose * n_seed  # none_true only
    print(f"  tier={OUT_TIER} runs={len(runs)} (expect {expected})")
    sample = runs[0][1] if runs else {}
    hvac = (sample.get("config_overrides") or {}).get("hvac") or {}
    print(f"  transport_engine={hvac.get('transport_engine')!r}")
    print(f"  sample_run_id={runs[0][0] if runs else None}")

    if len(runs) != expected:
        print(f"  ERROR: run count mismatch ({len(runs)} != {expected})")
        return 1

    if args.dry_run:
        return 0

    try:
        written = _write_manifest(args.out, manifest)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"  wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
