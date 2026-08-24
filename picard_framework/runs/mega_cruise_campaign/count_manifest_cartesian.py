"""Light Cartesian count for campaign manifests (no Picard spec expansion).

Usage:
  python -m picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian \\
    picard_framework/runs/mega_cruise_campaign/boundary_surface_v1_manifest.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.runs.mega_cruise_campaign import variant_campaign  # noqa: E402


def tier_cartesian(manifest: dict[str, Any], tier: dict[str, Any]) -> int:
    """Arithmetic run count for one tier (generator-aware for sr/vd/vs)."""
    tid_hint = ""
    for k, v in (manifest.get("tiers") or {}).items():
        if v is tier:
            tid_hint = k
            break

    if tid_hint.startswith("vs") or "voyage_days" in tier:
        return variant_campaign.tier_run_count(manifest, tier)

    plats = tier.get("platforms") or (
        [tier["platform"]] if "platform" in tier else [manifest["platform"]]
    )
    surv = tier.get("surveillance_strategies") or [tier.get("surveillance", "none")]
    seeds = tier["seeds"]

    if "R_onboard_values" in tier or "shore_exposure" in tier:
        return len(plats) * len(tier["R_onboard_values"]) * len(seeds)

    if tid_hint.startswith("sr") or "parameter_vectors" in tier:
        n_vec = len(tier["parameter_vectors"])
        return len(plats) * n_vec * len(surv) * len(seeds)

    if tid_hint.startswith("vd") or "factor" in tier or "factors" in tier:
        if "factor" in tier and "values" in tier:
            n_knobs = len(tier["values"])
        elif "factors" in tier:
            n_knobs = math.prod(len(v) for v in tier["factors"].values())
        else:
            n_knobs = 1
        return len(plats) * n_knobs * len(surv) * len(seeds)

    doses = tier.get("dose_adjustments") or [tier.get("dose_adjustment")]
    inits = tier.get("initial_infected_values") or [tier.get("initial_infected")]
    imm = tier.get("pre_immunity_fractions") or [None]
    dens = tier.get("density_exponents") or [None]
    cmodes = tier.get("contact_modes") or [None]
    epochs = tier.get("epoch_durations") or [None]
    return (
        len(plats)
        * len(doses)
        * len(inits)
        * len(dens)
        * len(cmodes)
        * len(imm)
        * len(epochs)
        * len(surv)
        * len(seeds)
    )


def summarize(manifest: dict[str, Any]) -> tuple[int, int]:
    wave1 = wave2 = 0
    for tid, tier in manifest["tiers"].items():
        c = tier_cartesian(manifest, tier)
        deferred = bool(tier.get("deferred"))
        if deferred:
            wave2 += c
        else:
            wave1 += c
        print(f"{tid}: {c} deferred={deferred}")
    return wave1, wave2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path, help="Path to campaign manifest JSON")
    args = p.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    wave1, wave2 = summarize(manifest)
    print(f"wave1={wave1} wave2={wave2} total={wave1 + wave2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
