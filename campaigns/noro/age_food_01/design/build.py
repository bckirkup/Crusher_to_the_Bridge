#!/usr/bin/env python3
"""Emit NORO-AGE-FOOD-01's manifest and campaign specs.

Design-of-record: docs/norovirus/noro_age_food_01_sweep_design.md.
Run from the repo root:

    python3 campaigns/noro/age_food_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_age_food_01_manifest.json
- campaigns/noro/age_food_01/campaign.json          (exp/cls/spr + canaries)
- campaigns/noro/age_food_01_mega/campaign.json     (mega cells, own jobdef
                                                     memory class)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

HULLS = {
    "exp": {"platform": "expedition_cruise_450", "num_agents": 450,
            "seeds": list(range(8000, 9000))},
    "cls": {"platform": "classic_cruise_1900", "num_agents": 1910,
            "seeds": list(range(8105, 9105))},
    "spr": {"platform": "spirit_cruise_3000", "num_agents": 3000,
            "seeds": list(range(8105, 9105))},
    "meg": {"platform": "mega_cruise_5000", "num_agents": 7000,
            "seeds": list(range(8000, 8288))},
}

SENIOR_BUNDLE = "data/scenarios/agent_profiles/senior_cruise_dp2020.json"
FAMILY_BUNDLE = "data/scenarios/agent_profiles/family_cruise_u18.json"

# Family arm: raise passenger_family to 0.25 so the bundle's 0.56 under-18
# draw lands ~20% of passengers under 18 (0.25 x 0.56 = 0.14 of all agents
# over a 0.70 passenger share).  Every other class entry is the shipped
# crusher_labs/config.yaml row verbatim — fractions still sum to 1.0.
FAMILY_AGENT_CLASSES = [
    {"class_id": "passenger_general", "role_group": "passenger",
     "fraction": 0.35, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "passenger_family", "role_group": "passenger",
     "fraction": 0.25, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "passenger_elderly", "role_group": "passenger",
     "fraction": 0.10, "home_zone_preference": "PC_",
     "free_zone_preference": "", "duty_zone": ""},
    {"class_id": "crew_general", "role_group": "crew",
     "fraction": 0.10, "home_zone_preference": "CC_",
     "free_zone_preference": "", "duty_zone": "",
     "schedule": {"template": "crew_general", "night_watch_fraction": 0.05}},
    {"class_id": "crew_medical", "role_group": "crew",
     "fraction": 0.05, "home_zone_preference": "CC_",
     "free_zone_preference": "Medical", "duty_zone": "Medical_Center",
     "schedule": {"template": "crew_medical", "night_watch_fraction": 0.05}},
    {"class_id": "crew_engineering", "role_group": "crew",
     "fraction": 0.10, "home_zone_preference": "CC_",
     "free_zone_preference": "Engine", "duty_zone": "Engine",
     "schedule": {"template": "crew_engineering", "night_watch_fraction": 0.05}},
    {"class_id": "crew_galley", "role_group": "crew",
     "fraction": 0.05, "home_zone_preference": "CC_",
     "free_zone_preference": "", "duty_zone": "Galley",
     "schedule": {"template": "crew_galley", "night_watch_fraction": 0.05}},
]

AGE_OVERRIDES = {
    "gen": {},
    "snr": {"social": {"agent_profile_bundle": SENIOR_BUNDLE}},
    "fam": {"social": {"agent_profile_bundle": FAMILY_BUNDLE},
            "ship_graph": {"agent_classes": FAMILY_AGENT_CLASSES}},
}

# Food arms.  off = whole-mechanism labelled baseline (mode: "off" draws
# nothing on any stream — bit-identical to the pre-mechanism engine).
# l1/l2/ship = the NORO-FOOD-02 lot_event_probability ladder.
# p05/p20 = the food_safety_posture covariate at the l1 lot rung, with
# lot_posture_coupling on: posture then multiplies every common-source event
# channel (handler/diner AND the lot draw) — the fully-coupled alternative
# to FOOD-02's deliberately-decoupled lot arm; the design doc records why.
FOOD_OVERRIDES = {
    "off": {"mode": "off"},
    "l1": {"lot_event_probability": [0.001, 0.0075]},
    "l2": {"lot_event_probability": [0.002, 0.015]},
    "ship": {"lot_event_probability": [0.02, 0.15]},
    "p05": {"lot_event_probability": [0.001, 0.0075],
            "food_safety_posture": 0.5, "lot_posture_coupling": True},
    "p20": {"lot_event_probability": [0.001, 0.0075],
            "food_safety_posture": 2.0, "lot_posture_coupling": True},
}

# Cells per hull: 3 ages x {off, l1, l2, ship} lot rungs = 12, plus
# 3 ages x {p05, p20} posture = 6 -> 18 cells on exp/cls/spr.
LOT_RUNGS = ("off", "l1", "l2", "ship")
POSTURE_RUNGS = ("p05", "p20")
AGES = ("gen", "snr", "fam")
# Mega: "a few" — the interaction at the anchor rung and the shipped
# declaration, not the full ladder.
MEGA_CELLS = [(age, food) for age in AGES for food in ("l1", "ship")]


def base_transmission_overrides() -> dict:
    """The FOOD-01/FOOD-02 transmission + hvac block, unchanged."""
    return {
        "transmission": {
            "sanitary_visit_mode": "dwell_weighted",
            "flush_aerosol_fraction": 0.0,
            "flush_cabin_emission": True,
            "cabin_air_mode": "cabin_compartment",
        },
        "hvac": {"pathogen_pool_transport": "airflow"},
    }


def tier_config(age: str, food: str) -> dict:
    cfg = base_transmission_overrides()
    cfg["transmission"]["common_source"] = FOOD_OVERRIDES[food]
    for key, block in AGE_OVERRIDES[age].items():
        cfg[key] = block
    return cfg


def tier(hull: str, age: str, food: str) -> tuple[str, dict]:
    tier_id = f"fl_{hull}_12d_scr_{age}_{food}"
    return tier_id, {
        "platform": HULLS[hull]["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [7.57],
        "surveillance_strategies": ["syndromic_comp65"],
        "epoch_durations": [288],
        "num_agents": HULLS[hull]["num_agents"],
        "description": (
            f"age arm {age} x food arm {food}; scr mid diagonal "
            "(bp32.5c18.5), nsf29, 288 epochs, comp65, dose 7.57 — fixed "
            "coordinates identical to NORO-FOOD-01/02 so cells pair "
            "voyage-for-voyage."
        ),
        "config_overrides": tier_config(age, food),
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [
            {"passenger": 0.0325, "crew": 0.0185},
        ],
        "never_symptomatic_fractions": [0.29],
        "seeds": HULLS[hull]["seeds"],
    }


def build_manifest() -> dict:
    tiers: dict[str, dict] = {}
    for hull in ("exp", "cls", "spr"):
        for age in AGES:
            for food in LOT_RUNGS + POSTURE_RUNGS:
                tid, spec = tier(hull, age, food)
                tiers[tid] = spec
    for age, food in MEGA_CELLS:
        tid, spec = tier("meg", age, food)
        tiers[tid] = spec
    return {
        "campaign": "noro_age_food_01",
        "description": (
            "NORO-AGE-FOOD-01: age-composition x food arms on the post-HOST-AGE, "
            "post-FOOD-COMMON-SOURCE engine. 3 age arms — gen (shipped default "
            "bundle), snr (Diamond-Princess-derived senior skew, ~60% of "
            "passengers >=65), fam (reweighted family bundle + raised family "
            "class share, ~20% of passengers under 18) — x 4 lot rungs "
            "(off / l1 / l2 / shipped, the FOOD-02 ladder) + 2 posture arms "
            "(food_safety_posture 0.5 / 2.0 with lot_posture_coupling at l1). "
            "scr mid diagonal bp32.5c18.5, nsf29, 288 epochs, comp65, dose 7.57; "
            "seeds pair with NORO-FOOD-02 / NORO-OUTBREAK-02/03/04 "
            "(exp 8000-8999, cls+spr 8105-9104, mega 8000-8287)."
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


def build_campaign() -> dict:
    blocks: dict[str, dict] = {}
    for hull in ("exp", "cls", "spr"):
        for age in AGES:
            for food in LOT_RUNGS + POSTURE_RUNGS:
                tid = f"fl_{hull}_12d_scr_{age}_{food}"
                blocks[tid] = block_for(tid, HULLS[hull]["seeds"])
    # Canary blocks: the two arms whose overrides are new to the fleet, on
    # the cheapest hull.  >=20 seeds at one cell per the campaign gate.
    blocks["canary_exp_snr_l1"] = block_for(
        "fl_exp_12d_scr_snr_l1", list(range(8000, 8024)),
    )
    blocks["canary_exp_fam_l1"] = block_for(
        "fl_exp_12d_scr_fam_l1", list(range(8000, 8008)),
    )
    return {
        "name": "noro_age_food_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_age_food_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_age_food_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-age-food01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def build_campaign_mega() -> dict:
    blocks = {
        f"fl_meg_12d_scr_{age}_{food}": block_for(
            f"fl_meg_12d_scr_{age}_{food}", HULLS["meg"]["seeds"],
        )
        for age, food in MEGA_CELLS
    }
    return {
        "name": "noro_age_food_01_mega",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_age_food_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_age_food_01_mega/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-age-food01-mega",
        # MEGA-IMPACT-01's proven container class.
        "resources": {"vcpu": "1", "memory": "6144", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_age_food_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/age_food_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/age_food_01_mega/campaign.json").write_text(
        json.dumps(build_campaign_mega(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
