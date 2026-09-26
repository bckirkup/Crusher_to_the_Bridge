#!/usr/bin/env python3
"""CABIN-FLOOR-01: per-pathogen confined-cabinmate mate attack vs sourced floors.

A thin per-pathogen variant of
``tools/noro_diag/cabin_pair_challenge_probe.py``. Each arm isolates one
pathogen profile aboard a declared ``classic_cruise_1900`` voyage — every
other member of its bundle is removed, the campaign's
``isolate_arm_overrides`` convention — and states two passenger index cases
at epoch 0 through ``initiation.explicit_seeds`` (the scenario's stated
index-case mechanism), additive to the profile's own boarding draw so the
prevalence arms are unchanged apart from the stated pair. Profiles whose
import is a low-probability party draw (measles 0.02, vibrio 0.03, andes
0.005, ebola 0.002 per voyage) or has no boarding block at all (legionella)
would otherwise carry no index on almost any seed and the confined check
would be vacuous by construction. ``initial_infected`` is nulled per arm
because the initiation engine refuses an explicit seed over a profile that
still carries one (legionella ships ``0``).

The confined-window mate attack — secondaries among mates who entered
confinement uninfected — is the all-route composite the
``CabinPairChallengeLedger`` tallies across pool, plume, contact, hvac,
emesis and flush. The sourced floors it is read against live in the
CABIN-FLOOR-01 ledger entry; they are a held-out check, never a fitting
target. The paired seeds are the probe pair for this platform, 8105/8106.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
    load_pathogen_bundle,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.covid_route_attribution import (  # noqa: E402
    CabinPairChallengeLedger,
    cabin_pair_challenge_table,
)
from tools.noro_diag.per_host_dose_challenge import build_spec  # noqa: E402

EDISON = "edison_10pathogen_profiles"
ACTIVE = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID

# Every real pathogen profile in the Edison roster plus the active bundle;
# each is (bundle_id, pathogen_id). The two bundles share sars_cov2_resp and
# influenza_a as distinct profile payloads, so both are exercised.
ROSTER: tuple[tuple[str, str], ...] = (
    *((EDISON, pid) for pid in (
        "norovirus_gii4",
        "sars_cov2_resp",
        "influenza_a",
        "measles_virus",
        "legionella_pneumophila",
        "vibrio_cholerae_parahaemolyticus",
        "campylobacter_jejuni",
        "clostridioides_difficile",
        "andes_hantavirus",
        "ebola_virus",
    )),
    *((ACTIVE, pid) for pid in (
        "norwalk_gi",
        "sars_cov2_resp",
        "influenza_a",
    )),
)

DEFAULT_SEEDS = (8105, 8106)


def _party_size(profile: dict[str, Any]) -> int:
    """The declared party size when the profile imports as a party, else 2."""
    party = (profile.get("boarding") or {}).get("party") or {}
    return int(party.get("size") or 0) or 2


def run_arm(
    *,
    bundle: str,
    pathogen_id: str,
    seed: int,
    platform: str,
    epochs: int,
) -> dict[str, Any]:
    """One isolated, instrumented voyage for one pathogen at one seed."""
    profiles = load_pathogen_bundle(
        resolve_repo_path(str(REPO_ROOT), asset_defaults.pathogen_bundle_rel(bundle)),
    )
    profile = profiles[pathogen_id]
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id=pathogen_id, alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    spec_dict["pathogen_overrides"] = isolate_arm_overrides(
        bundle, pathogen_id, {pathogen_id: {"initial_infected": None}},
    )
    spec_dict["config_overrides"]["initiation"] = {
        "explicit_seeds": [{
            "pathogen": pathogen_id,
            "count": _party_size(profile),
            "role": "passenger",
            "epoch": 0,
        }],
    }
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
    infected = sum(
        1 for agent in sim.engine.agents
        if pathogen_id in agent.infections
    )
    channel_totals = {
        channel: sum(
            row["channel_dose"].get(channel, 0.0)
            for row in table["rows"]
            if row["confined_epochs"] > 0
        )
        for channel in CabinPairChallengeLedger.CHANNELS
    }
    return {
        "bundle": bundle,
        "pathogen_id": pathogen_id,
        "seed": seed,
        "platform": platform,
        "num_epoch_steps": epochs,
        "explicit_seed_count": _party_size(profile),
        "infections_total": infected,
        "dose_response": profile.get("dose_response"),
        "pairs_observed": table["pairs_observed"],
        "mate_index_pairs": table["mate_index_pairs"],
        "mate_slots": table["mate_slots"],
        "mate_secondaries": table["mate_secondaries"],
        "observed_mate_case_attack": table["observed_mate_case_attack"],
        "confined_index_pairs": table["confined_index_pairs"],
        "confined_slots": table["confined_slots"],
        "confined_secondaries": table["confined_secondaries"],
        "observed_mate_case_attack_confined": (
            table["observed_mate_case_attack_confined"]
        ),
        "lambda_confined_median": table["lambda_confined_quantiles"]["median"],
        "implied_sar_confined_median": table["implied_sar_confined_median"],
        "confined_channel_dose_totals": channel_totals,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS),
        help="paired seeds; this platform's pair is 8105 8106",
    )
    parser.add_argument(
        "--arm", action="append", default=None,
        help="pathogen_id to run (repeatable); default runs the whole roster",
    )
    parser.add_argument(
        "--bundle", default=None,
        help="restrict --arm to this bundle (edison/active share two ids)",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roster = [
        (bundle, pid) for bundle, pid in ROSTER
        if (args.arm is None or pid in args.arm)
        and (args.bundle is None or bundle == args.bundle)
    ]
    if not roster:
        raise SystemExit(
            f"--arm/--bundle matched nothing in the roster: {args.arm!r}/{args.bundle!r}",
        )
    results = [
        run_arm(
            bundle=bundle, pathogen_id=pid, seed=seed,
            platform=args.platform, epochs=args.epochs,
        )
        for bundle, pid in roster
        for seed in args.seeds
    ]
    out_path = args.out.resolve()
    if not out_path.is_relative_to(REPO_ROOT):
        out_path = REPO_ROOT / out_path.name
    with validated_open(
        out_path, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(results, indent=1))
    for row in results:
        print(
            f"{row['pathogen_id']} ({row['bundle']}) seed {row['seed']}: "
            f"infected={row['infections_total']} "
            f"confined_pairs={row['confined_index_pairs']} "
            f"attack={row['observed_mate_case_attack_confined']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
