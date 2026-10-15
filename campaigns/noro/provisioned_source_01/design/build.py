#!/usr/bin/env python3
"""Emit NORO-PROVISIONED-SOURCE-01's manifest and campaign specs.

Design-of-record: docs/norovirus/noro_provisioned_source_01_sweep_design.md.
Mechanism contract: docs/provisioned_source_01_design.md.
Run from the repo root:

    python3 campaigns/noro/provisioned_source_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_provisioned_source_01_manifest.json
- campaigns/noro/provisioned_source_01/campaign.json
- campaigns/noro/provisioned_source_01_mega/campaign.json

NOTE: the campaign does not submit until the implementation leg lands the
provisioned_source mechanism and its witness fields (design §5.3-5) and the
image pins a SHA containing them — the arm dicts below are the frozen
interface the implementation leg builds against.
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
            "seeds": list(range(8105, 9105))},
}
SMALL_HULLS = ("exp", "cls", "spr")

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

# Common-source machinery, PROVISIONED-SOURCE-01 arm set (design §3.1).
#
# off = whole-mechanism labelled baseline (mode: "off" draws nothing —
# bit-identical to every prior off cell).  ind = the v1 "independent"
# labelled baseline on the CURRENT engine — the per-hull signature
# denominator every rung is read against.  ship/mint = fiat bridge
# anchors under lot_mint_model "fiat" — the labelled pre-mechanism
# baseline mode, bit-identity gate vs the landed MINT-RATE-01/
# SHAPES-01 cells at shared seeds (mega omits them: vacuous, no
# bridge target — design §3.3).  ps_ship = the shipped default
# configuration under the new mechanism (registry source
# generic_cruise_port at the declared default interval).  q01..q30 =
# scalar rungs on q_source: each consumes zero voyage-rate uniforms
# (the lo==hi early return), so all seven rungs share one stream
# layout per seed and contaminated-station sets nest by q (integrity
# gate design §5.3-1).  N_lots is derived, not declared — the census
# resolves 21/35/63/70 per hull from the platform's served Dining
# zones x COMMON_SOURCE_LOT_ITEM_LINES (contract §1.2).
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
_FIAT_OBJECTS = dict(
    _OBJECT_MODES, lot_mint_model="fiat",
)


def _ps(q):
    return dict(
        _OBJECT_MODES,
        lot_mint_model="provisioned_source",
        provisioned_source={
            "source_id": "generic_cruise_port",
            "q_source": q,
        },
    )


FOOD_OVERRIDES = {
    "off": {"mode": "off"},
    # v1 labelled baseline at this image — the per-hull signature
    # denominator.
    "ind": dict(_INDEPENDENT_MODES),
    # Fiat bridge anchors — shipped U(0.001,0.02) (vacuous, in-band)
    # and powered U(0.02,0.15) (over-posting, full signature); the
    # bit-identity gate to landed MINT-RATE-01/SHAPES-01 cells.
    "ship": dict(_FIAT_OBJECTS, lot_object_probability=[0.001, 0.02]),
    "mint": dict(_FIAT_OBJECTS, lot_object_probability=[0.02, 0.15]),
    # The shipped default configuration under the new mechanism —
    # the declared default interval the source registry resolves
    # (contract §1.3), not a rung.
    "ps_ship": _ps([0.0002, 0.0005]),
    # Scalar rungs — the q_source ladder (design §3.1/§3.2).
    "q01": _ps(0.0001),
    "q02": _ps(0.0002),
    "q03": _ps(0.0003),
    "q05": _ps(0.0005),
    "q08": _ps(0.0008),
    "q15": _ps(0.0015),
    "q30": _ps(0.0030),
}

ARMS_SMALL = (
    "off", "ind",
    "ship", "mint",
    "ps_ship",
    "q01", "q02", "q03", "q05", "q08", "q15", "q30",
)
ARMS_MEGA = (
    "off", "ind",
    "ps_ship",
    "q01", "q02", "q03", "q05", "q08", "q15", "q30",
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
            f"provisioned-source arm {arm}; scr mid diagonal "
            "(bp32.5c18.5), nsf29, 288 epochs, comp65, dose 7.57 — "
            "fixed coordinates identical to NORO-FOOD-01/02, "
            "AGE-FOOD-01, SCORE-01, ENTRAIN-01, FOOD-SHAPES-01 and "
            "MINT-RATE-01 so cells pair voyage-for-voyage."
        ),
        "config_overrides": base_overrides(arm),
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [SHIPPED_PREVALENCE],
        "never_symptomatic_fractions": [0.29],
        "seeds": HULLS[hull]["seeds"],
    }


def build_manifest() -> dict:
    tiers: dict[str, dict] = {}
    for hull in SMALL_HULLS:
        for arm in ARMS_SMALL:
            tid, spec = tier(hull, arm)
            tiers[tid] = spec
    for arm in ARMS_MEGA:
        tid, spec = tier("meg", arm)
        tiers[tid] = spec
    return {
        "campaign": "noro_provisioned_source_01",
        "description": (
            "NORO-PROVISIONED-SOURCE-01: the provisioned-source "
            "mechanism eval — provisioned_lot mints become a derived "
            "draw, objects-per-voyage = Binomial(N_lots, q_source) "
            "with N_lots the served-venue x item-line station census "
            "(exp 21 / cls 35 / spr 63 / mega 70) and q_source a "
            "hull-invariant upstream contamination prevalence.  The "
            "testable claim (contract §5): station-N scales like the "
            "measured required-object scale, so ONE q puts all three "
            "small hulls in the D1 posting band — the admissible "
            "region becomes hull-free in q (frozen prediction: q03 "
            "lands +0.59/+0.61/+0.68 pp).  Scalar rungs "
            "1e-4/2e-4/3e-4/5e-4/8e-4/1.5e-3/3e-3 bracket the common "
            "window and trace mega's extrapolated band "
            "(q ~ [1.5e-3, 4.1e-3]); contaminated-station sets nest "
            "by q per seed (integrity gate).  off/ind baselines; "
            "ship/mint fiat bridges (bit-identity vs landed cells, "
            "small hulls only); ps_ship the shipped-default check.  "
            "3 small hulls x 12 arms + mega x 10 arms, 1,000 seeds "
            "each = 46,000 voyages on the SCORE-01 seed lists and "
            "fixed coordinates (exp 8000-8999, cls/spr/mega "
            "8105-9104).  Does not submit until the mechanism + "
            "witness fields land and the image pins a SHA "
            "containing them (design §5.3-5)."
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
    for hull in SMALL_HULLS:
        for arm in ARMS_SMALL:
            tid = f"fl_{hull}_12d_scr_{arm}"
            blocks[tid] = block_for(tid, HULLS[hull]["seeds"])
    # Canary blocks (design §6): the smallest set gating the mode
    # echoes, the mechanism machinery, the nested-set spot-check and
    # the shipped-default block — then STOP.  mint (48): fiat bridge,
    # interval echo, objects fire (E ~= 4.1, P(0) ~= 0.014),
    # bit-identity spot-check vs landed cells.  q30 (24): mechanism
    # machinery — scalar q echo "0.003", n_stations=21 census echo,
    # objects bind census stations (E ~= 1.5, P(0) ~= 0.22 —
    # zero-object does not fail).  q03 (24): scalar echo + nested-set
    # spot-check vs q30 at shared seeds (q03 station sets subset of
    # q30).  ps_ship (8): registry resolution + interval echo
    # [2e-4,5e-4].  ind (8): independent-modes echo.  off (4):
    # zero-witness.
    blocks["canary_exp_mint"] = block_for(
        "fl_exp_12d_scr_mint", list(range(8000, 8048)),
    )
    blocks["canary_exp_q30"] = block_for(
        "fl_exp_12d_scr_q30", list(range(8000, 8024)),
    )
    blocks["canary_exp_q03"] = block_for(
        "fl_exp_12d_scr_q03", list(range(8000, 8024)),
    )
    blocks["canary_exp_ps_ship"] = block_for(
        "fl_exp_12d_scr_ps_ship", list(range(8000, 8008)),
    )
    blocks["canary_exp_ind"] = block_for(
        "fl_exp_12d_scr_ind", list(range(8000, 8008)),
    )
    blocks["canary_exp_off"] = block_for(
        "fl_exp_12d_scr_off", list(range(8000, 8004)),
    )
    return {
        "name": "noro_provisioned_source_01",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_provisioned_source_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_provisioned_source_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-provisioned-source01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def build_campaign_mega() -> dict:
    blocks: dict[str, dict] = {}
    for arm in ARMS_MEGA:
        tid = f"fl_meg_12d_scr_{arm}"
        blocks[tid] = block_for(tid, HULLS["meg"]["seeds"])
    # canary_meg_q30 (12, design §6): mega arming on the new mode —
    # n_stations=70 census echo, E ~= 2.5 objects (P(0) ~= 0.08),
    # rss_samples read for the jobdef-memory declaration.
    blocks["canary_meg_q30"] = block_for(
        "fl_meg_12d_scr_q30", list(range(8105, 8117)),
    )
    return {
        "name": "noro_provisioned_source_01_mega",
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_provisioned_source_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": "campaign/noro_provisioned_source_01_mega/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-provisioned-source01",
        "resources": {"vcpu": "1", "memory": "8192", "shm": 512},
        "blocks": blocks,
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_provisioned_source_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_source_01/campaign.json").write_text(
        json.dumps(build_campaign(), indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_source_01_mega/campaign.json").write_text(
        json.dumps(build_campaign_mega(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
