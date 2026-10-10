#!/usr/bin/env python3
"""Emit NORO-ENTRAIN-01's manifest and campaign spec.

Design-of-record: docs/norovirus/noro_entrain_01_sweep_design.md.
Run from the repo root:

    python3 campaigns/noro/noro_entrain_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_entrain_01_manifest.json
- campaigns/noro/noro_entrain_01/campaign.json
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

# Common-source machinery.  off = whole-mechanism labelled baseline
# (mode: "off" spawns no stream — bit-identical to the pre-mechanism
# engine).  ind = the per-arm "independent" labelled baseline: the v1
# code path at v1 shipped constants on the CURRENT engine — the
# contrast runs in-campaign, not against an old commit.  ship = all
# three arms under "object" mode at the shipped declared intervals —
# the scored configuration every lever arm modifies.
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
_SHIP_OBJECTS = dict(
    _OBJECT_MODES, lot_object_probability=[0.001, 0.02],
)
FOOD_OVERRIDES = {
    "off": {"mode": "off"},
    "ind": dict(_INDEPENDENT_MODES),
    "ship": dict(_SHIP_OBJECTS),
    # Lever A — event shape arms (lot-arm knobs only; agent-object
    # extent is emergent from the shedding course and needs the
    # cs_extent contract, design §4.3).
    # a_ext: extent multiplier — minted-life draw (1,4)->(4,7) days at
    # shipped demand, servings, titre, start-window.
    "a_ext": dict(_SHIP_OBJECTS, lot_shelf_life_days=[4, 7]),
    # a_thin: diluted spread — per-window take share
    # (0.10,0.60)->(0.04,0.20): smaller per-window servings, longer
    # exhaustion-limited life.
    "a_thin": dict(_SHIP_OBJECTS, item_take_share=[0.04, 0.20]),
}
# Lever B arms run the shipped common-source config; their lever is
# boarding / immunity, not the object layer.
for _b_arm in ("bc40", "bc80", "bi50", "bmix"):
    FOOD_OVERRIDES[_b_arm] = dict(_SHIP_OBJECTS)

# Lever B — arriving-shedder proxy.  crew boarding prevalence raised
# to declared points (passenger pinned at the shipped 0.0325); the
# shipped crew point is 0.0185.
CREW_PREVALENCE = {
    "bc40": 0.040,
    "bc80": 0.080,
    "bmix": 0.080,
}
SHIPPED_PREVALENCE = {"passenger": 0.0325, "crew": 0.0185}

# Lever B — immunity carryover: crew-only embarkation-immunity
# fraction (ship_graph.crew_immune_fraction -> engine.crew_immune_ratio,
# IMMUNE-ROLE-01).  Shipped = unset -> role-blind 0.2 pool.
CREW_IMMUNE_FRACTION = {
    "bi50": 0.5,
    "bmix": 0.5,
}

ARMS = (
    "off", "ind", "ship",
    "a_ext", "a_thin",
    "bc40", "bc80", "bi50", "bmix",
)


def base_overrides(arm: str) -> dict:
    """The FOOD-01/FOOD-02 transmission + hvac block, unchanged, plus
    the shipped class mix (declared for the stamp, resolved config
    identical — see BASE_AGENT_CLASSES above); Lever B arms add the
    crew-only immunity fraction on the ship_graph surface."""
    ship_graph = {"agent_classes": BASE_AGENT_CLASSES}
    if arm in CREW_IMMUNE_FRACTION:
        ship_graph["crew_immune_fraction"] = CREW_IMMUNE_FRACTION[arm]
    return {
        "transmission": {
            "sanitary_visit_mode": "dwell_weighted",
            "flush_aerosol_fraction": 0.0,
            "flush_cabin_emission": True,
            "cabin_air_mode": "cabin_compartment",
            "common_source": FOOD_OVERRIDES[arm],
        },
        "hvac": {"pathogen_pool_transport": "airflow"},
        "ship_graph": ship_graph,
    }


def prevalence_point(arm: str) -> dict:
    return {
        "passenger": SHIPPED_PREVALENCE["passenger"],
        "crew": CREW_PREVALENCE.get(arm, SHIPPED_PREVALENCE["crew"]),
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
            f"entrain arm {arm}; scr mid diagonal "
            f"(bp{SHIPPED_PREVALENCE['passenger'] * 1000:g}c"
            f"{prevalence_point(arm)['crew'] * 1000:g}), nsf29, 288 "
            "epochs, comp65, dose 7.57 — fixed coordinates identical "
            "to NORO-FOOD-01/02, AGE-FOOD-01 and SCORE-01 so cells "
            "pair voyage-for-voyage."
        ),
        "config_overrides": base_overrides(arm),
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [prevalence_point(arm)],
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
        "campaign": "noro_entrain_01",
        "description": (
            "NORO-ENTRAIN-01: two levers aimed at raising VSP posting "
            "appropriately per hull, on the SCORE-01 measurement "
            "frame.  Lever A (event shape): a_ext lot_shelf_life_days "
            "(4,7), a_thin item_take_share (0.04,0.20) on the shipped "
            "object config.  Lever B (entrainment proxy): bc40/bc80 "
            "crew boarding prevalence 0.040/0.080, bi50 crew-only "
            "embarkation immunity 0.5, bmix the net-sign cell "
            "(0.080 + 0.5).  Baselines off/ind/ship re-run on the "
            "campaign image for free pairing.  3 hulls x 9 arms x "
            "1,000 seeds; scr mid diagonal bp32.5, nsf29, 288 epochs, "
            "comp65, dose 7.57; seeds pair with NORO-FOOD-01/02, "
            "NORO-OUTBREAK-02/03/04, AGE-FOOD-01 and SCORE-01 (exp "
            "8000-8999, cls+spr 8105-9104).  Mega excluded — objects "
            "never armed there, v1 saturates short of its wire."
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
    # Canary blocks: the smallest set gating the levers' witness
    # fields, all on the cheapest hull — then STOP (design §8).
    # bc80: arriving-shedder echo (drawn_by_role/composition) +
    # early handler-object seeding attribution.  a_ext: the
    # shelf-life override reaching the engine (perished past the
    # shipped 4-day cap / windows_covered > 8).  ship: shipped-config
    # witness on the campaign image.  off: zero-witness.
    blocks["canary_exp_bc80"] = block_for(
        "fl_exp_12d_scr_bc80", list(range(8000, 8024)),
    )
    blocks["canary_exp_a_ext"] = block_for(
        "fl_exp_12d_scr_a_ext", list(range(8000, 8012)),
    )
    blocks["canary_exp_ship"] = block_for(
        "fl_exp_12d_scr_ship", list(range(8000, 8008)),
    )
    blocks["canary_exp_off"] = block_for(
        "fl_exp_12d_scr_off", list(range(8000, 8004)),
    )
    return {
        "name": "noro_entrain_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_entrain_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_entrain_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-entrain01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_entrain_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/noro_entrain_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
