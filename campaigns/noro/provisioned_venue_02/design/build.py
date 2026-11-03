#!/usr/bin/env python3
"""Emit NORO-PROVISIONED-VENUE-02's manifest and campaign specs.

Edison Phase-2 calibration: stable conditional distributions for the
venue-placement counterfactual piloted in NORO-PROVISIONED-VENUE-01 —
4 hulls x 3 placement arms x the FULL 1,000-seed q30 set per hull =
12,000 runs on the q30 (q_source = 0.003) provisioned-source spec,
extracted via first_paper_scalar/1.4.0 and delivered to Edison.

Arms: ``crew_venue`` (crew-mess pins, verbatim from VENUE-01),
``passenger_venue`` (largest passenger dining venue), and
``mixed_venue`` — proportional allocation across every served dining
venue by seat capacity, the realistic upstream-distribution default.
The mixed arm uses ``provisioned_source.station_zone_pin`` covering
every served Dining zone plus the Phase-2
``station_zone_pin_weights`` seam (seat counts) — per-station
weighted placement on a dedicated SeedSequence parallel to the
census stream, so n_lots and the shared draw stream stay seed-paired
with the unpinned baseline.

The reuse question Edison posed is settled by measurement (see
DESIGN.md): the delivered 4,000 q30 runs distribute lots ~uniformly
across served venues (each venue contributes the same 7 item-line
stations), NOT capacity-proportionally — measured deviation up to
25 pp per venue — so the q30 cohort is the distributed arm and all
three conditions run fresh.

Seeds: the full delivered NORO-PROVISIONED-SOURCE-01 q30 seed sets
(exp 8000-8999, cls/spr/meg 8105-9104), so all three arms pair
seed-for-seed with the delivered baseline.

Run from the repo root:

    python3 campaigns/noro/provisioned_venue_02/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_provisioned_venue_02_manifest.json
- campaigns/noro/provisioned_venue_02/campaign.json
- campaigns/noro/provisioned_venue_02_mega/campaign.json
- campaigns/noro/provisioned_venue_02/SEED_MANIFEST.json

NOTE: the campaign does not submit until the weighted-pin seam merges
and the image pins a SHA containing it (campaign-preflight skill).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

# Per-hull venue pins and seat weights (served-venue x item-line
# station census verified 2026-11-02 in VENUE-01 DESIGN.md §2, and
# re-read from data/platforms/<platform>/spatial_layout.json
# max_occupancy).  crew_venue/passenger_venue pins are verbatim from
# NORO-PROVISIONED-VENUE-01; mixed_venue pins every served Dining
# zone weighted by seat capacity (galley-type zones carry no dining
# cohort and never enter the served census).
HULLS = {
    "exp": {"platform": "expedition_cruise_450", "num_agents": 450,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining"],
            "pin_mix": ["MainDining", "CasualDining", "CrewMess"],
            "w_mix": [300, 150, 60],
            "seeds": list(range(8000, 9000)),
            "canary_seed": 8169},
    "cls": {"platform": "classic_cruise_1900", "num_agents": 1910,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "LidoBuffet",
                        "Specialty", "CrewMess"],
            "w_mix": [400, 400, 350, 80, 200],
            "seeds": list(range(8105, 9105)),
            "canary_seed": 8169},
    "spr": {"platform": "spirit_cruise_3000", "num_agents": 3000,
            "pin_crew": ["CrewMessMain", "CrewMessOff"],
            "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "LidoBuffet",
                        "PizzaGrill", "SpecialtyA", "SpecialtyB",
                        "SpecialtyC", "CrewMessMain", "CrewMessOff"],
            "w_mix": [500, 500, 400, 120, 80, 80, 80, 250, 60],
            "seeds": list(range(8105, 9105)),
            "canary_seed": 8152},
    "meg": {"platform": "mega_cruise_5000", "num_agents": 7000,
            "pin_crew": ["Crew_Mess_Main", "CrewMess_Fwd"],
            "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "Windjammer",
                        "SpecRest_A", "SpecRest_B", "Pool_Bar_Grill",
                        "ComedyClub", "CafeBakery", "Crew_Mess_Main",
                        "CrewMess_Fwd"],
            "w_mix": [1400, 1100, 1600, 450, 400, 300, 300, 250,
                      700, 350],
            "seeds": list(range(8105, 9105)),
            "canary_seed": 8152},
}
SMALL_HULLS = ("exp", "cls", "spr")

ARMS = ("crew_venue", "passenger_venue", "mixed_venue")
_ARM_TAG = {"crew_venue": "crewv", "passenger_venue": "paxv",
            "mixed_venue": "mixv"}

# Shipped class mix, copied verbatim from crusher_labs/config.yaml
# ship_graph.agent_classes — identical stamp to
# campaigns/noro/provisioned_source_01/design/build.py and the
# VENUE-01 pilot so cells pair voyage-for-voyage with the delivered
# q30 baseline arm.
BASE_AGENT_CLASSES = [
    {"class_id": "passenger_general", "role_group": "passenger",
     "fraction": 0.50, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "passenger_family", "role_group": "passenger",
     "fraction": 0.10, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "passenger_elderly", "role_group": "passenger",
     "fraction": 0.10, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "crew_general", "role_group": "crew",
     "fraction": 0.10, "home_zone_preference": "CC_",
     "free_zone_preference": "", "duty_zone": "",
     "schedule": {"template": "crew_general", "night_watch_fraction": 0.05}},
    {"class_id": "crew_medical", "role_group": "crew",
     "fraction": 0.05, "home_zone_preference": "Medical", "duty_zone": "Medical_Center",
     "schedule": {"template": "crew_medical", "night_watch_fraction": 0.05}},
    {"class_id": "crew_engineering", "role_group": "crew",
     "fraction": 0.10, "home_zone_preference": "Engine", "duty_zone": "Engine",
     "schedule": {"template": "crew_engineering",
                  "night_watch_fraction": 0.05}},
    {"class_id": "crew_galley", "role_group": "crew",
     "fraction": 0.05, "home_zone_preference": "", "duty_zone": "Galley",
     "schedule": {"template": "crew_galley", "night_watch_fraction": 0.05}},
]

SHIPPED_PREVALENCE = {"passenger": 0.0325, "crew": 0.0185}


def _pin(hull: str, arm: str) -> list[str]:
    return HULLS[hull][{
        "crew_venue": "pin_crew",
        "passenger_venue": "pin_pax",
        "mixed_venue": "pin_mix",
    }[arm]]


def base_overrides(hull: str, arm: str) -> dict:
    """The FOOD-01/FOOD-02 transmission + hvac block on the q30
    provisioned-source spec, plus the venue pin (+ capacity weights
    on mixed_venue) — the only delta vs the delivered q30 baseline
    arm is the pin, its weights, and the arm label."""
    ps = {
        "source_id": "generic_cruise_port",
        "q_source": 0.003,
        "station_zone_pin": _pin(hull, arm),
        "source_venue_arm": arm,
    }
    if arm == "mixed_venue":
        ps["station_zone_pin_weights"] = HULLS[hull]["w_mix"]
    return {
        "transmission": {
            "sanitary_visit_mode": "dwell_weighted",
            "flush_aerosol_fraction": 0.0,
            "flush_cabin_emission": True,
            "cabin_air_mode": "cabin_compartment",
            "common_source": {
                "mode": "on",
                "lot_mode": "object",
                "handler_mode": "object",
                "diner_mode": "object",
                "lot_mint_model": "provisioned_source",
                "provisioned_source": ps,
            },
        },
        "hvac": {"pathogen_pool_transport": "airflow"},
        "ship_graph": {"agent_classes": BASE_AGENT_CLASSES},
    }


def tier(hull: str, arm: str) -> tuple[str, dict]:
    tier_id = f"fl_{hull}_12d_scr_q30_{_ARM_TAG[arm]}"
    pin = _pin(hull, arm)
    pin_desc = (
        f"pin {pin} weights {HULLS[hull]['w_mix']}"
        if arm == "mixed_venue" else f"pin {pin}"
    )
    return tier_id, {
        "platform": HULLS[hull]["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [7.57],
        "surveillance_strategies": ["syndromic_comp65"],
        "epoch_durations": [288],
        "num_agents": HULLS[hull]["num_agents"],
        "description": (
            f"provisioned-source q30 venue-pin arm {arm}; {pin_desc} "
            "— scr mid diagonal (bp32.5c18.5), nsf29, 288 epochs, "
            "comp65, dose 7.57 — fixed coordinates identical to the "
            "delivered NORO-PROVISIONED-SOURCE-01 q30 baseline and "
            "the VENUE-01 pilot."
        ),
        "config_overrides": base_overrides(hull, arm),
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [SHIPPED_PREVALENCE],
        "never_symptomatic_fractions": [0.29],
        "seeds": HULLS[hull]["seeds"],
    }


def build_manifest() -> dict:
    tiers: dict[str, dict] = {}
    for hull in HULLS:
        for arm in ARMS:
            tid, spec = tier(hull, arm)
            tiers[tid] = spec
    return {
        "campaign": "noro_provisioned_venue_02",
        "description": (
            "NORO-PROVISIONED-VENUE-02 (Edison Phase-2 calibration): "
            "stable conditional distributions for the venue-placement "
            "counterfactual — crew_venue / passenger_venue / "
            "mixed_venue on the q30 (q_source=0.003) "
            "provisioned-source spec.  mixed_venue pins every served "
            "Dining zone weighted by seat capacity "
            "(station_zone_pin_weights).  4 hulls x 3 arms x the full "
            "1,000-seed q30 set per hull = 12,000 cells + 12 canary "
            "cells (1 max-lot seed x 3 arms per hull).  Extraction via "
            "first_paper_scalar/1.4.0 (source_venue_arm, "
            "actual_venues_used, n_lots_placed).  Does not submit "
            "until the weighted-pin seam merges and the image pins a "
            "SHA containing it."
        ),
        "platform": "classic_cruise_1900",
        "default_epochs": 168,
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


def block_for(tid: str, seeds: list[int]) -> dict:
    return {
        "worker": "tools/noro_diag/growth_chain_census.py",
        "tier": tid,
        "seeds": seeds,
    }


def _blocks(hulls: tuple[str, ...]) -> dict[str, dict]:
    blocks: dict[str, dict] = {}
    for hull in hulls:
        for arm in ARMS:
            tid = f"fl_{hull}_12d_scr_q30_{_ARM_TAG[arm]}"
            blocks[tid] = block_for(tid, HULLS[hull]["seeds"])
        # Canary: one max-lot q30 seed per arm — every pin exercises
        # on every hull before the 12k array.
        for arm in ARMS:
            blocks[f"canary_{hull}_{_ARM_TAG[arm]}"] = block_for(
                f"fl_{hull}_12d_scr_q30_{_ARM_TAG[arm]}",
                [HULLS[hull]["canary_seed"]],
            )
    return blocks


def build_campaign(hulls: tuple[str, ...], name: str,
                   memory: str) -> dict:
    suffix = "_mega" if hulls == ("meg",) else ""
    return {
        "name": name,
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_provisioned_venue_02_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": f"campaign/noro_provisioned_venue_02{suffix}/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-provisioned-venue02",
        "resources": {"vcpu": "1", "memory": memory, "shm": 512},
        "blocks": _blocks(hulls),
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def seed_manifest() -> dict:
    """Execution manifest Edison verifies on delivery: exact seed
    sets + the reuse measurement that settled the arm count."""
    return {
        "rule": (
            "Every arm reuses the delivered NORO-PROVISIONED-SOURCE-01 "
            "q30 seed set verbatim (exp 8000-8999; cls/spr/meg "
            "8105-9104), so crew_venue/passenger_venue/mixed_venue "
            "pair seed-for-seed with the delivered q30 baseline."
        ),
        "reuse_verdict": (
            "The delivered q30 arm is NOT capacity-proportional: its "
            "census contributes 7 item-line stations per served venue "
            "uniformly, and the measured realized venue shares across "
            "the 4,000 delivered runs track 1/N_venues (max |measured "
            "- capacity| = 25.0 pp on exp CrewMess). The q30 cohort is "
            "the distributed arm; mixed_venue runs fresh on the "
            "weighted pin."
        ),
        "canary_seeds": {
            h: HULLS[h]["canary_seed"] for h in HULLS
        },
        "hulls": {
            h: {
                "platform": HULLS[h]["platform"],
                "n_seeds": len(HULLS[h]["seeds"]),
                "seed_range": [
                    HULLS[h]["seeds"][0], HULLS[h]["seeds"][-1],
                ],
                "venue_pin": {
                    "crew_venue": HULLS[h]["pin_crew"],
                    "passenger_venue": HULLS[h]["pin_pax"],
                    "mixed_venue": HULLS[h]["pin_mix"],
                },
                "mixed_venue_weights": HULLS[h]["w_mix"],
            }
            for h in HULLS
        },
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_provisioned_venue_02_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_02/campaign.json").write_text(
        json.dumps(
            build_campaign(SMALL_HULLS, "noro_provisioned_venue_02",
                           "4096"),
            indent=1,
        ) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_02_mega/"
     "campaign.json").write_text(
        json.dumps(
            build_campaign(("meg",), "noro_provisioned_venue_02_mega",
                           "8192"),
            indent=1,
        ) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_02/"
     "SEED_MANIFEST.json").write_text(
        json.dumps(seed_manifest(), indent=1) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
