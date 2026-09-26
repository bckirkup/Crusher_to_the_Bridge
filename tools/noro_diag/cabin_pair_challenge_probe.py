#!/usr/bin/env python3
"""Per-pair cumulative challenge on cabin-mate pairs, norovirus arm.

Ledger CABIN-OCC-01 measurement probe: attach the
:class:`CabinPairChallengeLedger` from ``tools.covid_route_attribution``
(pathogen-agnostic — it keys doses by pathogen id) to a declared
``classic_cruise_1900`` voyage and report the per-pair hazard table at the
paired norovirus seeds. The spec comes from
``per_host_dose_challenge.build_spec`` unchanged except seed/epoch/platform
arguments, so this reads the shipped model, not a probe configuration.

Paired-seed attribution pair: 8105/8106 (the norovirus pair). The
confined-cabinmate attack rates in the provenance register (Wikswo 2011
15.4%, Chimonas 2008 24.1%) are a held-out check on the readout, never a
fitting target.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.covid_route_attribution import (  # noqa: E402
    CabinPairChallengeLedger,
    cabin_pair_challenge_table,
)
from tools.noro_diag.dose_response import load_dose_response  # noqa: E402
from tools.noro_diag.per_host_dose_challenge import build_spec  # noqa: E402


def run_seed(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    pathogen_id: str,
) -> dict[str, Any]:
    """One instrumented voyage; returns the cabin-pair challenge table."""
    alpha, beta = load_dose_response(pathogen_id, bundle)
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id=pathogen_id, alpha=None, beta=beta,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    # validated_open refuses publicly writable roots; keep the spec file in
    # a private dir under the repository, as per_host_dose_challenge does.
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), str(spec_path),
        )
        sim = ShipSimulation(picard_spec, display=False)
        ledger = CabinPairChallengeLedger()
        sim.epoch_observer = ledger.observe
        sim.run()
    table = cabin_pair_challenge_table(ledger, sim)
    return {
        "seed": seed,
        "platform": platform,
        "pathogen_id": pathogen_id,
        "epochs": epochs,
        "dose_response": {"alpha": alpha, "beta": beta},
        "cabin_pairs": table,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument(
        "--bundle", default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8105, 8106],
        help="paired seeds; the norovirus pair is 8105 8106",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = [
        run_seed(
            seed=seed, platform=args.platform, bundle=args.bundle,
            epochs=args.epochs, pathogen_id=args.pathogen_id,
        )
        for seed in args.seeds
    ]
    out_path = args.out.resolve()
    if not out_path.is_relative_to(REPO_ROOT):
        out_path = REPO_ROOT / out_path.name
    with validated_open(
        out_path, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(results, indent=1))
    print(json.dumps(results, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
