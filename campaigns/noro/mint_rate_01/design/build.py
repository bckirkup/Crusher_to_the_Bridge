#!/usr/bin/env python3
"""Emit NORO-MINT-RATE-01's manifest and campaign spec.

Design-of-record: docs/norovirus/noro_mint_rate_01_sweep_design.md.
Run from the repo root:

    python3 campaigns/noro/mint_rate_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_mint_rate_01_manifest.json
- campaigns/noro/mint_rate_01/campaign.json
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

# Common-source machinery, MINT-RATE-01 arm set (design §3.2).
#
# off = whole-mechanism labelled baseline (mode: "off" draws nothing —
# bit-identical to every prior off cell).  ind = the v1 "independent"
# labelled baseline on the CURRENT engine — under the shipped two_mode
# default its lot events draw the implicated band; it is the per-hull
# signature denominator every rung is read against.  ship = the scored
# shipped configuration (objects + two_mode + emergent/per_object +
# shipped mint U(0.001,0.02)) — the bracket bottom anchor and the
# SHAPES-01 `ship` bridge.  mint = the powered top anchor
# U(0.02,0.15) — the measured over-posting end carrying the full
# signature — and the SHAPES-01 `mint` bridge.  p005..p024 = scalar
# rungs on the voyage gate: the per-voyage draw is exactly p
# (E[presence] exact; the margin is linear in E[p] — design §4), so
# the ladder reads the posting-vs-presence slope without interval
# dispersion.  Scalar specs consume zero voyage-rate uniforms, so all
# five rungs gate on the same stream position per seed — minted sets
# are nested by gate value (integrity gate §5.4-3).
_OBJECT_MODES = {
    "lot_mode": "object",
    # The measured cells ran the fiat grammar — pin it so a rebuild
    # reproduces them under the shipped default.
    "lot_mint_model": "fiat",
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
    # v1 labelled baseline at this image — under shipped two_mode its
    # provisioned_lot events draw the implicated band; the per-hull
    # signature denominator.
    "ind": dict(_INDEPENDENT_MODES),
    # Scored shipped configuration — bracket bottom anchor, and the
    # bit-identity bridge to the SHAPES-01 `ship` cells at `45b2bf18`
    # (verbatim arm dict + shared seed list; condition §3.4).
    "ship": dict(_SHIP_OBJECTS),
    # Powered top anchor — the measured over-posting end, signature
    # carrier; bit-identity bridge to the SHAPES-01 `mint` cells.
    "mint": dict(_SHIP_OBJECTS, lot_object_probability=[0.02, 0.15]),
    # Scalar rungs — the mint-rate ladder (design §3.2/§3.3).
    "p005": dict(_SHIP_OBJECTS, lot_object_probability=0.005),
    "p008": dict(_SHIP_OBJECTS, lot_object_probability=0.008),
    "p012": dict(_SHIP_OBJECTS, lot_object_probability=0.012),
    "p017": dict(_SHIP_OBJECTS, lot_object_probability=0.017),
    "p024": dict(_SHIP_OBJECTS, lot_object_probability=0.024),
}

ARMS = (
    "off", "ind",
    "ship", "mint",
    "p005", "p008", "p012", "p017", "p024",
)

SHIPPED_PREVALENCE = {"passenger": 0.0325, "crew": 0.0185}


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
            f"mint-rate arm {arm}; scr mid diagonal "
            "(bp32.5c18.5), nsf29, 288 epochs, comp65, dose 7.57 — "
            "fixed coordinates identical to NORO-FOOD-01/02, "
            "AGE-FOOD-01, SCORE-01, ENTRAIN-01 and FOOD-SHAPES-01 so "
            "cells pair voyage-for-voyage."
        ),
        "config_overrides": base_overrides(arm),
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [SHIPPED_PREVALENCE],
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
        "campaign": "noro_mint_rate_01",
        "description": (
            "NORO-MINT-RATE-01: the mint-rate ladder on the object "
            "grammar — channel presence (the provisioned_lot voyage "
            "gate lot_object_probability) is the measured operative "
            "margin (SHAPES-01: powered U(0.02,0.15) over-posts at ind "
            "level carrying the full signature; shipped U(0.001,0.02) "
            "is in-band but vacuous at ~6 minted voyages/1,000).  The "
            "campaign brackets between them: scalar rungs "
            "0.005/0.008/0.012/0.017/0.024 locate the gate where the "
            "D1 posting marginal lands in-band per hull, and the "
            "pooled in-band rungs read whether the D2/D3/D4 signature "
            "survives at that rate (verdict mint-vs-ind per hull — "
            "ind itself misses the 0.04 edge on cls/spr).  "
            "off/ind/ship/mint baselines and SHAPES-01 bridges; "
            "cadence/extent measured nulls (shipped defaults); "
            "two_mode shipped-on; extra_lot U(0.02,0.25) stays "
            "(x1.163 object multiplicity only).  3 hulls x 9 arms x "
            "1,000 seeds = 27,000 voyages on the SCORE-01 seed lists "
            "and fixed coordinates (exp 8000-8999, cls+spr "
            "8105-9104); mega excluded — objects never armed there."
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
    # Canary blocks (design §7): the smallest set gating the arm
    # echoes and the powered object gate, all on the cheapest hull —
    # then STOP.  mint (48): >=1 provisioned_lot object (E ~= 4.1 at
    # the U(0.02,0.15) midpoint; P(0) ~= 0.014), interval echo,
    # implicated-band titres, per_object single titre.  p024 (24):
    # scalar echo "0.024"; conditional object witness (E ~= 0.7,
    # P(0) ~= 0.50 — zero-lot does not fail).  p005 (24): scalar echo
    # "0.005"; conditional (E ~= 0.14, P(0) ~= 0.87 — non-failing).
    # ind (8): independent-modes echo, object_id-null rows.  ship (8):
    # shipped-config witness echo.  off (4): zero-witness.
    blocks["canary_exp_mint"] = block_for(
        "fl_exp_12d_scr_mint", list(range(8000, 8048)),
    )
    blocks["canary_exp_p024"] = block_for(
        "fl_exp_12d_scr_p024", list(range(8000, 8024)),
    )
    blocks["canary_exp_p005"] = block_for(
        "fl_exp_12d_scr_p005", list(range(8000, 8024)),
    )
    blocks["canary_exp_ind"] = block_for(
        "fl_exp_12d_scr_ind", list(range(8000, 8008)),
    )
    blocks["canary_exp_ship"] = block_for(
        "fl_exp_12d_scr_ship", list(range(8000, 8008)),
    )
    blocks["canary_exp_off"] = block_for(
        "fl_exp_12d_scr_off", list(range(8000, 8004)),
    )
    return {
        "name": "noro_mint_rate_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_mint_rate_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_mint_rate_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-mint-rate01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_mint_rate_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/mint_rate_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
