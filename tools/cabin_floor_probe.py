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

Two confinement arms exist. ``organic`` lets the voyage's own surveillance
drive whatever confinement it produces — small outbreaks may never reach
CONFIRMED escalation, whose cabin-contact rule is what puts both members
of a stateroom pair under quarters, so an organic arm can end with zero
confined pairs and no measurable window. ``declared`` holds SOP-017
(Replayed Cabin Quarantine of All Passengers, crew exempt — the Diamond
Princess passenger/crew asymmetry) active from day 1 through voyage end
via ``scenario_schedule``, the replay calendar's mechanism for an
authority's order that binds whether or not simulated surveillance got
there; every passenger pair is then confined for the whole infectious
span, which is the household-exposure window the sourced floors describe
and the only way the check is non-vacuous for pathogens whose own
outbreak never escalates (legionella sheds to nobody, and a party-seeded
measles or ebola index infects too few to trip CONFIRMED).

The confined-window mate attack — secondaries among mates who entered
confinement uninfected — is the all-route composite the
``CabinPairChallengeLedger`` tallies across pool, plume, contact, hvac,
emesis and flush. The sourced floors it is read against live in the
CABIN-FLOOR-01 ledger entry; they are a held-out check, never a fitting
target. The paired seeds are the probe pair for this platform, 8105/8106.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
    load_pathogen_bundle,
)
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import resolve_repo_path  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.covid_route_attribution import CabinPairChallengeLedger  # noqa: E402
from tools.noro_diag.cabin_pair_challenge_probe import (  # noqa: E402
    instrumented_voyage,
    write_results,
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

# Replay calendar confinement: SOP-017 confines every passenger while all
# crew classes stay working, held from the first full simulated day (after
# embarkation churn settles) through voyage end.
DECLARED_CONFINEMENT = {
    "protocol_id": "SOP-017",
    "start_day": 1,
    "end_day": None,
}


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
    confinement: str = "organic",
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
    if confinement == "declared":
        spec_dict["config_overrides"]["scenario_schedule"] = {
            "protocols": [DECLARED_CONFINEMENT],
        }
    sim, table = instrumented_voyage(spec_dict)
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
        "confinement": confinement,
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
    parser.add_argument(
        "--confinement", choices=("organic", "declared"), default="organic",
        help="organic: the voyage's own escalation; declared: SOP-017 held "
        "over passengers day 1 to end via scenario_schedule",
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
            confinement=args.confinement,
        )
        for bundle, pid in roster
        for seed in args.seeds
    ]
    write_results(results, args.out)
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
