#!/usr/bin/env python3
"""Emit NORO-FOOD-SHAPES-01's manifest and campaign spec.

Design-of-record: docs/norovirus/noro_food_shapes_01_sweep_design.md.
Run from the repo root:

    python3 campaigns/noro/food_shapes_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_food_shapes_01_manifest.json
- campaigns/noro/food_shapes_01/campaign.json
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

# Common-source machinery, FOOD-SHAPES-01 arm set (design §3.2).
#
# off = whole-mechanism labelled baseline (mode: "off" draws nothing —
# bit-identical to every prior off cell).  ind/ind_bg = the per-arm
# "independent" labelled baseline (v1 path on the CURRENT engine);
# under the shipped two_mode default its lot events already draw the
# implicated band — ind_bg restores the single-mode draw, which is
# both the powered titre-margin read on the converting channel and
# the bit-identity bridge to the ENTRAIN-01 `ind` cells.  ship = all
# three arms under "object" mode at shipped declared intervals plus
# the shipped two_mode draw — the scored configuration every margin
# arm modifies.  bg = ship with the labelled "background" titre
# baseline: verbatim the pre-#990 single-mode draw at the same stream
# position — the titre axis at shipped mint AND the bit-identity
# bridge to the ENTRAIN-01 `ship` cells at `dbbd5395`.
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
# The mint axis: the object-mode voyage gate re-expressed on the v1
# event-mode voyage-gate interval verbatim (the interval
# lot_event_probability draws under "independent").  Channel presence
# at `ind` frequency on the object grammar — declared, not fit.
_MINT_V1 = {"lot_object_probability": [0.02, 0.15]}

FOOD_OVERRIDES = {
    "off": {"mode": "off"},
    # v1 labelled baseline on the current engine — under the shipped
    # two_mode default its provisioned_lot events draw the implicated
    # band (the titre resolver is a per-site rule, mode-agnostic).
    "ind": dict(_INDEPENDENT_MODES),
    # ind + the single-mode titre draw: the powered titre-margin read
    # on the converting channel AND the bit-identity bridge to the
    # ENTRAIN-01 `ind` cells at `dbbd5395`.
    "ind_bg": dict(_INDEPENDENT_MODES, titre_draw_mode="background"),
    # Scored shipped configuration — objects + two_mode (default) +
    # emergent/per_object + shipped mint.
    "ship": dict(_SHIP_OBJECTS),
    # Titre margin on objects at shipped mint; bit-identity bridge to
    # the ENTRAIN-01 `ship` cells (verbatim pre-#990 draw).
    "bg": dict(_SHIP_OBJECTS, titre_draw_mode="background"),
    # Mint margin alone on the shipped shape.
    "mint": dict(_SHIP_OBJECTS, **_MINT_V1),
    # {titre} x {mint} corner — the powered titre read on objects.
    "bg_mint": dict(
        _SHIP_OBJECTS, titre_draw_mode="background", **_MINT_V1,
    ),
    # Cadence margin (seeded-draw shape) at shipped mint: titre and
    # take-share re-mint per served window off the object's own
    # stream partition; under two_mode the re-mints resolve through
    # the same site rule — inside the implicated band.
    "redraw": dict(_SHIP_OBJECTS, lot_state_redraw="per_window"),
    # Cadence margin at powered mint — and the campaign's conjunction
    # cell: cadence + mint + implicated denominator together.
    "redraw_mint": dict(
        _SHIP_OBJECTS, lot_state_redraw="per_window", **_MINT_V1,
    ),
    # Iso-dose extent legs at two_mode + shipped mint (declared
    # extent; the ENTRAIN-01 §4.3 contract arms landed here because
    # the pairing surface must be the two_mode image).
    "fx_wide": dict(
        _SHIP_OBJECTS,
        lot_extent_mode="declared", lot_extent_windows=[12, 24],
    ),
    "fx_narrow": dict(
        _SHIP_OBJECTS,
        lot_extent_mode="declared", lot_extent_windows=[2, 4],
    ),
}

ARMS = (
    "off", "ind", "ind_bg",
    "ship", "bg",
    "mint", "bg_mint",
    "redraw", "redraw_mint",
    "fx_wide", "fx_narrow",
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
            f"shapes arm {arm}; scr mid diagonal "
            "(bp32.5c18.5), nsf29, 288 epochs, comp65, dose 7.57 — "
            "fixed coordinates identical to NORO-FOOD-01/02, "
            "AGE-FOOD-01, SCORE-01 and ENTRAIN-01 so cells pair "
            "voyage-for-voyage."
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
        "campaign": "noro_food_shapes_01",
        "description": (
            "NORO-FOOD-SHAPES-01: the two measured missing margins — "
            "the implicated titre denominator (two_mode, shipped "
            "default) and the cadence dose shape (per_window re-mints "
            "+ declared extent, the landed cs_extent contract) — "
            "crossed with voyage-gate mint-rate (channel absence is "
            "measured: 2/1,620 unposted object-arm cells minted a "
            "lot).  Discriminating subset: off/ind/ind_bg baselines; "
            "ship/bg at shipped mint; mint/bg_mint the "
            "{titre}x{mint} factorial; redraw/redraw_mint the "
            "{cadence}x{mint} factorial and the conjunction cell; "
            "fx_wide/fx_narrow the iso-dose extent legs.  "
            "lot_object_probability elevated to (0.02,0.15) — the "
            "v1 lot_event voyage-gate interval re-expressed on the "
            "object grammar.  3 hulls x 11 arms x 1,000 seeds; scr "
            "mid diagonal bp32.5c18.5, nsf29, 288 epochs, comp65, "
            "dose 7.57; seeds pair with NORO-FOOD-01/02, "
            "NORO-OUTBREAK-02/03/04, AGE-FOOD-01, SCORE-01 and "
            "ENTRAIN-01 (exp 8000-8999, cls+spr 8105-9104).  Mega "
            "excluded — objects never armed there, v1 saturates "
            "short of its wire."
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
    # Canary blocks: the smallest set gating the new witness fields,
    # all on the cheapest hull — then STOP (design §8).
    # redraw_mint (48): elevated-mint echo (>=1 provisioned_lot
    # object; E ~= 4 at the (0.02,0.15) gate), redraw "per_window" +
    # extent_mode "emergent" on object rows, per-window titre
    # re-mints landing inside the implicated band (two_mode routing
    # proof).  bg_mint (24): titre_draw_mode "background" echo + >=1
    # lot object (mint echo).  fx_wide (24): lot_extent_mode
    # "declared" + lot_extent_windows (12,24) echoes; conditional
    # object witness (extent_mode/extent_windows/extent_met) — a
    # zero-lot canary does not fail at shipped mint (P ~= 0.78).
    # ship (8): shipped-config witness on the campaign image.
    # off (4): zero-witness.
    blocks["canary_exp_redraw_mint"] = block_for(
        "fl_exp_12d_scr_redraw_mint", list(range(8000, 8048)),
    )
    blocks["canary_exp_bg_mint"] = block_for(
        "fl_exp_12d_scr_bg_mint", list(range(8000, 8024)),
    )
    blocks["canary_exp_fx_wide"] = block_for(
        "fl_exp_12d_scr_fx_wide", list(range(8000, 8024)),
    )
    blocks["canary_exp_ship"] = block_for(
        "fl_exp_12d_scr_ship", list(range(8000, 8008)),
    )
    blocks["canary_exp_off"] = block_for(
        "fl_exp_12d_scr_off", list(range(8000, 8004)),
    )
    return {
        "name": "noro_food_shapes_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_food_shapes_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_food_shapes_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-food-shapes01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_food_shapes_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/food_shapes_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
