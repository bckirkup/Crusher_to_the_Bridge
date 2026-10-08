#!/usr/bin/env python3
"""Emit NORO-FOOD-SCORE-01's manifest and campaign spec.

Design-of-record: docs/norovirus/noro_food_score_01_sweep_design.md.
Run from the repo root:

    python3 campaigns/noro/noro_food_score_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_food_score_01_manifest.json
- campaigns/noro/noro_food_score_01/campaign.json
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
}

# Shipped class mix, copied verbatim from crusher_labs/config.yaml
# ship_graph.agent_classes — fractions sum to 1.0.  Declared on every
# tier so _fill_demographic_params stamps agent_class_fractions into
# every arm's run parameters (it only echoes a declared override); the
# resolved config is unchanged, so voyages are bit-identical to the
# un-declared mix.
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
     "fraction": 0.05, "home_zone_preference": "CC_",
     "free_zone_preference": "Medical", "duty_zone": "Medical_Center",
     "schedule": {"template": "crew_medical", "night_watch_fraction": 0.05}},
    {"class_id": "crew_engineering", "role_group": "crew",
     "fraction": 0.10, "home_zone_preference": "CC_",
     "free_zone_preference": "Engine", "duty_zone": "Engine",
     "schedule": {"template": "crew_engineering",
                  "night_watch_fraction": 0.05}},
    {"class_id": "crew_galley", "role_group": "crew",
     "fraction": 0.05, "home_zone_preference": "CC_",
     "free_zone_preference": "", "duty_zone": "Galley",
     "schedule": {"template": "crew_galley", "night_watch_fraction": 0.05}},
]

# Common-source arms.  off = whole-mechanism labelled baseline
# (mode: "off" spawns no stream — bit-identical to the pre-mechanism
# engine).  ind = the per-arm "independent" labelled baseline: the v1
# code path at v1 shipped constants (lot_event_probability U[0.02,0.15]
# etc.) on the CURRENT engine — the contrast runs in-campaign, not
# against an old commit.  ol1/ol2/ol3/ship = all three arms under
# "object" mode with a lot_object_probability rung (ship = the shipped
# declared interval — the scored configuration).  Handler/diner arms
# stay at shipped object intervals on every object rung — not swept.
_OBJECT_MODES = {
    "lot_mode": "object",
    "handler_mode": "object",
    "diner_mode": "object",
}
_INDEPENDENT_MODES = {
    "lot_mode": "independent",
    "handler_mode": "independent",
    "diner_mode": "independent",
}
FOOD_OVERRIDES = {
    "off": {"mode": "off"},
    "ind": dict(_INDEPENDENT_MODES),
    "ol1": dict(_OBJECT_MODES, lot_object_probability=[0.0005, 0.0025]),
    "ol2": dict(_OBJECT_MODES, lot_object_probability=[0.001, 0.006]),
    "ol3": dict(_OBJECT_MODES, lot_object_probability=[0.002, 0.012]),
    "ship": dict(_OBJECT_MODES, lot_object_probability=[0.001, 0.02]),
}
ARMS = ("off", "ind", "ol1", "ol2", "ol3", "ship")


def base_overrides(arm: str) -> dict:
    """The FOOD-01/FOOD-02 transmission + hvac block, unchanged, plus
    the shipped class mix (declared for the stamp, resolved config
    identical — see BASE_AGENT_CLASSES above)."""
    return {
        "transmission": {
            "sanitary_visit_mode": "dwell_weighted",
            "flush_aerosol_fraction": 0.0,
            "flush_cabin_emission": True,
            "cabin_air_mode": "cabin_compartment",
            "common_source": FOOD_OVERRIDES[arm],
        },
        "hvac": {"pathogen_pool_transport": "airflow"},
        "ship_graph": {"agent_classes": BASE_AGENT_CLASSES},
    }


def tier(hull: str, arm: str) -> tuple[str, dict]:
    tier_id = f"fl_{hull}_12d_scr_{arm}"
    return tier_id, {
        "platform": HULLS[hull]["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [7.57],
        "surveillance_strategies": ["syndromic_comp65"],
        "epoch_durations": [288],
        "num_agents": HULLS[hull]["num_agents"],
        "description": (
            f"common-source arm {arm}; scr mid diagonal "
            "(bp32.5c18.5), nsf29, 288 epochs, comp65, dose 7.57 — fixed "
            "coordinates identical to NORO-FOOD-01/02 and "
            "AGE-FOOD-01 so cells pair voyage-for-voyage."
        ),
        "config_overrides": base_overrides(arm),
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
        for arm in ARMS:
            tid, spec = tier(hull, arm)
            tiers[tid] = spec
    return {
        "campaign": "noro_food_score_01",
        "description": (
            "NORO-FOOD-SCORE-01: scores the shipped FOOD-COMMON-SOURCE-02 "
            "contamination-object mechanism against the spec's four "
            "diagnostics (posting frequency, posted-conditional reported "
            "pax AR, hull-scaling compression, outbreak shape) on 3 hulls "
            "x 6 arms: off (whole-mechanism baseline), ind (all arms "
            "\"independent\" = the v1 baseline on the current engine), "
            "and 4 object-mode rungs on lot_object_probability "
            "([0.0005,0.0025] / [0.001,0.006] / [0.002,0.012] / shipped "
            "[0.001,0.02]); handler/diner arms at shipped object "
            "intervals throughout. scr mid diagonal bp32.5c18.5, nsf29, "
            "288 epochs, comp65, dose 7.57; seeds pair with "
            "NORO-FOOD-01/02, NORO-OUTBREAK-02/03/04 and AGE-FOOD-01 "
            "(exp 8000-8999, cls+spr 8105-9104)."
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
        for arm in ARMS:
            tid = f"fl_{hull}_12d_scr_{arm}"
            blocks[tid] = block_for(tid, HULLS[hull]["seeds"])
    # Canary blocks: one per baseline/labelled arm plus the scored
    # configuration, on the cheapest hull.  >=20 seeds at one cell per
    # the campaign gate (ship gets 24).  Lot objects at E ~1.05% are
    # rare — the ship canary's lot gate is the override echo plus
    # handler/diner objects, not a lot firing (zero lot objects in 24
    # seeds has P ~ 78%).
    blocks["canary_exp_ship"] = block_for(
        "fl_exp_12d_scr_ship", list(range(8000, 8024)),
    )
    blocks["canary_exp_ind"] = block_for(
        "fl_exp_12d_scr_ind", list(range(8000, 8012)),
    )
    blocks["canary_exp_off"] = block_for(
        "fl_exp_12d_scr_off", list(range(8000, 8008)),
    )
    return {
        "name": "noro_food_score_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_food_score_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_food_score_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-food-score01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_food_score_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/noro_food_score_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
