#!/usr/bin/env python3
"""Emit NORO-PROVISIONED-SENSITIVITY-01's manifest, campaign specs,
seed manifest and the committed half-fraction profile table.

Paper-1 sensitivity screen (Edison ask, Devin-designed): does the
venue02 role-specific-reporting / venue-placement result depend
materially on five uncertain inputs?  2^(5-1) Resolution-V
half-fraction (generator E = ABCD) = 16 profiles x 4 hulls x 3 venue
arms = 192 cells, seed-paired with NORO-PROVISIONED-VENUE-02 (same
seed blocks, ascending prefix per cell), on the 1.5.0 emitter
(cumulative role checkpoints days 3/7/10/12; PR #1156).

Factors (levels frozen by the plan of record, from provenance):

  A  q_source per station-voyage          0.00086 (-) / 0.0047 (+)
  B  boarding_passenger_prevalence        0.025   (-) / 0.040  (+)
  C  boarding_crew_prevalence             0.007   (-) / 0.030  (+)
  D  illness_duration.draw                point   (-) / empirical_survival (+)
  E  route_efficiency_multipliers scale   x0.5    (-) / x2.0   (+)
     on the five nonzero route keys; environmental_source stays 0.0

D rides the tier's own ``pathogen_overrides`` (deep-merged over the
manifest base by ``tier_iterators.tier_pathogen_overrides``) and is
protected from the ``shipped`` rung's ``point`` by
``boarding_axis.tier_illness_duration_draw`` — the rung would
otherwise overwrite the declaration (the trap Edison flagged; venue02
itself ran at D = point, so the (-) level IS the paired baseline).

Held fixed (= venue02): 288 epochs, ``shipped`` rung (boarding mode
screening_prevalence, age draw engine_window, symptomatic and
preboarding streams off), dose_adjustment 7.57, syndromic_comp65
observation model, FOOD-01/02 transmission + hvac block, shipped
agent-class mix, per-hull venue pins and mixed-venue weights copied
verbatim from venue02's SEED_MANIFEST.json.

Run from the repo root:

    python3 campaigns/noro/provisioned_sensitivity_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json
- campaigns/noro/provisioned_sensitivity_01/campaign.json
- campaigns/noro/provisioned_sensitivity_01_mega/campaign.json
- campaigns/noro/provisioned_sensitivity_01/SEED_MANIFEST.json
- campaigns/noro/provisioned_sensitivity_01/PROFILE_TABLE.md
"""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CAMPAIGN = "noro_provisioned_sensitivity_01"
MANIFEST_REL = (
    "picard_framework/runs/mega_cruise_campaign/"
    f"{CAMPAIGN}_manifest.json"
)
# Small hulls run the remainder (cls seeds 8171-8200) on the image built
# from the post-#1164 main; the mega campaign keeps the scout image, whose
# tag must not be re-pointed while its remainder arrays are RUNNABLE.
IMAGE_TAG = (
    "noro-provisioned-sensitivity01-r2"
    "@sha256:efc18c7df8a1ae224eaf2e10d10fc372462f949b5c26312ef41c042fbf72b18d"
)
IMAGE_TAG_MEGA = "noro-provisioned-sensitivity01"

# ---------------------------------------------------------------- factors
FACTOR_LEVELS: dict[str, dict[str, object]] = {
    "A": {"name": "q_source", "low": 0.00086, "high": 0.0047},
    "B": {"name": "boarding_passenger_prevalence", "low": 0.025, "high": 0.040},
    "C": {"name": "boarding_crew_prevalence", "low": 0.007, "high": 0.030},
    "D": {"name": "illness_duration.draw", "low": "point",
          "high": "empirical_survival"},
    "E": {"name": "route_efficiency_multipliers scale", "low": 0.5,
          "high": 2.0},
}

# Baseline route dict, verbatim from data/pathogens/active_profiles.json
# norwalk_gi.route_efficiency_multipliers.  environmental_source is 0.0
# at both levels (0 x anything = 0) and is written explicitly so the
# loaded dict is complete and auditable.
BASE_ROUTES = {
    "direct_contact": 0.35,
    "droplet": 0.1,
    "hvac_airborne": 0.05,
    "fomite": 0.3,
    "food_contamination": 0.2,
    "environmental_source": 0.0,
}
SCALED_ROUTE_KEYS = ("direct_contact", "droplet", "hvac_airborne",
                     "fomite", "food_contamination")


def route_dict(scale: float) -> dict[str, float]:
    return {
        k: (round(v * scale, 6) if k in SCALED_ROUTE_KEYS else v)
        for k, v in BASE_ROUTES.items()
    }


def half_fraction() -> list[dict]:
    """2^(5-1), generator E = ABCD, standard (Yates) order on A..D.

    Signs are +1/-1; E is the product so every row satisfies
    I = ABCDE (Resolution V: no main effect aliased with a 2fi, no 2fi
    aliased with another 2fi)."""
    rows = []
    for i, (d, c, b, a) in enumerate(product((-1, 1), repeat=4), start=1):
        e = a * b * c * d
        rows.append({"profile_id": f"p{i:02d}",
                     "A": a, "B": b, "C": c, "D": d, "E": e})
    return rows


PROFILES = half_fraction()
_SIGN = {-1: "-", 1: "+"}


def level(factor: str, sign: int) -> object:
    return FACTOR_LEVELS[factor]["high" if sign > 0 else "low"]


def profile_levels(row: dict) -> dict[str, object]:
    return {
        "q_source": level("A", row["A"]),
        "boarding_passenger_prevalence": level("B", row["B"]),
        "boarding_crew_prevalence": level("C", row["C"]),
        "illness_duration_draw": level("D", row["D"]),
        "route_scale": level("E", row["E"]),
        "route_efficiency_multipliers": route_dict(float(level("E", row["E"]))),
    }


# ------------------------------------------------------------------ hulls
# Pins / weights / seeds verbatim from
# campaigns/noro/provisioned_venue_02/SEED_MANIFEST.json.  ``n`` is the
# per-cell replication proposed from precision needs + venue02 measured
# wall clock (DESIGN.md §3); ``scout`` is the nested canary prefix;
# ``reserve`` seeds are the next ascending seeds after the prefix, held
# for retries only (never auto-submitted).
HULLS = {
    "exp": {"platform": "expedition_cruise_450", "num_agents": 450,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining"],
            "pin_mix": ["MainDining", "CasualDining", "CrewMess"],
            "w_mix": [300, 150, 60],
            "seed_block": (8000, 8999), "n": 96, "scout": 8, "reserve": 2},
    "cls": {"platform": "classic_cruise_1900", "num_agents": 1910,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "LidoBuffet",
                        "Specialty", "CrewMess"],
            "w_mix": [400, 400, 350, 80, 200],
            "seed_block": (8105, 9104), "n": 96, "scout": 8, "reserve": 2},
    "spr": {"platform": "spirit_cruise_3000", "num_agents": 3000,
            "pin_crew": ["CrewMessMain", "CrewMessOff"],
            "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "LidoBuffet",
                        "PizzaGrill", "SpecialtyA", "SpecialtyB",
                        "SpecialtyC", "CrewMessMain", "CrewMessOff"],
            "w_mix": [500, 500, 400, 120, 80, 80, 80, 250, 60],
            "seed_block": (8105, 9104), "n": 48, "scout": 8, "reserve": 2},
    "meg": {"platform": "mega_cruise_5000", "num_agents": 7000,
            "pin_crew": ["Crew_Mess_Main", "CrewMess_Fwd"],
            "pin_pax": ["MainDining_L"],
            "pin_mix": ["MainDining_L", "MainDining_U", "Windjammer",
                        "SpecRest_A", "SpecRest_B", "Pool_Bar_Grill",
                        "ComedyClub", "CafeBakery", "Crew_Mess_Main",
                        "CrewMess_Fwd"],
            "w_mix": [1400, 1100, 1600, 450, 400, 300, 300, 250,
                      700, 350],
            "seed_block": (8105, 9104), "n": 24, "scout": 8, "reserve": 2},
}
SMALL_HULLS = ("exp", "cls", "spr")
ARMS = ("crew_venue", "passenger_venue", "mixed_venue")
_ARM_TAG = {"crew_venue": "crewv", "passenger_venue": "paxv",
            "mixed_venue": "mixv"}


def seeds(hull: str) -> list[int]:
    lo, _hi = HULLS[hull]["seed_block"]
    return list(range(lo, lo + HULLS[hull]["n"]))


def reserve_seeds(hull: str) -> list[int]:
    lo, _hi = HULLS[hull]["seed_block"]
    n = HULLS[hull]["n"]
    return list(range(lo + n, lo + n + HULLS[hull]["reserve"]))


def scout_seeds(hull: str) -> list[int]:
    return seeds(hull)[: HULLS[hull]["scout"]]


# Shipped class mix, copied verbatim from crusher_labs/config.yaml
# ship_graph.agent_classes — identical stamp to venue02 so cells pair
# voyage-for-voyage with the delivered venue02 arms.
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


def _pin(hull: str, arm: str) -> list[str]:
    return HULLS[hull][{
        "crew_venue": "pin_crew",
        "passenger_venue": "pin_pax",
        "mixed_venue": "pin_mix",
    }[arm]]


def config_overrides(hull: str, arm: str, q_source: float) -> dict:
    """venue02's FOOD-01/02 transmission + hvac block and venue pin;
    the only sensitivity delta inside config_overrides is q_source (A)."""
    ps = {
        "source_id": "generic_cruise_port",
        "q_source": q_source,
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


def tier_id(hull: str, profile_id: str, arm: str) -> str:
    return f"fl_{hull}_12d_sens_{profile_id}_{_ARM_TAG[arm]}"


def tier(hull: str, row: dict, arm: str) -> tuple[str, dict]:
    lv = profile_levels(row)
    signs = "".join(f"{f}{_SIGN[row[f]]}" for f in "ABCDE")
    tid = tier_id(hull, row["profile_id"], arm)
    return tid, {
        "platform": HULLS[hull]["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [7.57],
        "surveillance_strategies": ["syndromic_comp65"],
        "epoch_durations": [288],
        "num_agents": HULLS[hull]["num_agents"],
        "description": (
            f"SENSITIVITY-01 profile {row['profile_id']} ({signs}) arm {arm} "
            f"pin {_pin(hull, arm)}: q_source {lv['q_source']}, "
            f"pax/crew prevalence {lv['boarding_passenger_prevalence']}/"
            f"{lv['boarding_crew_prevalence']}, illness draw "
            f"{lv['illness_duration_draw']}, route scale x{lv['route_scale']} "
            "— shipped rung, nsf29, 288 epochs, comp65, dose 7.57; "
            "all else = NORO-PROVISIONED-VENUE-02."
        ),
        "config_overrides": config_overrides(hull, arm, float(lv["q_source"])),
        "pathogen_overrides": {
            "norwalk_gi": {
                "illness_duration": {"draw": lv["illness_duration_draw"]},
                "route_efficiency_multipliers": lv["route_efficiency_multipliers"],
            },
        },
        "boarding_mechanism_rungs": ["shipped"],
        "boarding_prevalence_points": [{
            "passenger": lv["boarding_passenger_prevalence"],
            "crew": lv["boarding_crew_prevalence"],
        }],
        "never_symptomatic_fractions": [0.29],
        "seeds": seeds(hull) + reserve_seeds(hull),
        "sensitivity_profile": {
            "profile_id": row["profile_id"],
            "signs": {f: row[f] for f in "ABCDE"},
        },
    }


def build_manifest() -> dict:
    tiers: dict[str, dict] = {}
    for hull in HULLS:
        for row in PROFILES:
            for arm in ARMS:
                tid, spec = tier(hull, row, arm)
                tiers[tid] = spec
    return {
        "campaign": CAMPAIGN,
        "description": (
            "NORO-PROVISIONED-SENSITIVITY-01 (Paper-1 sensitivity, "
            "Child B): 2^(5-1) Resolution-V half-fraction (E = ABCD) on "
            "q_source (A), boarding passenger prevalence (B), boarding "
            "crew prevalence (C), illness_duration.draw (D), joint "
            "route-efficiency scale (E) — 16 profiles x 4 hulls x 3 "
            "venue arms = 192 cells on the venue02 spec, seed-paired "
            "with venue02 (ascending seed prefix per cell), extracted "
            "via first_paper_scalar/1.5.0 (role checkpoints days "
            "3/7/10/12).  Tier seeds list main + reserve; campaign.json "
            "blocks carry the submitted prefix (scout = first 8 seeds)."
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


def block_for(tid: str, block_seeds: list[int]) -> dict:
    return {
        "worker": "tools/noro_diag/growth_chain_census.py",
        "tier": tid,
        "seeds": block_seeds,
    }


def _blocks(hulls: tuple[str, ...]) -> dict[str, dict]:
    """``scout_<tid>`` = first 8 seeds (nested canary wave);
    ``<tid>`` = the remainder of the main prefix.  Reserve seeds are
    in the manifest tier but in no block — a retry block is added by
    hand, per the LEDGER, never automatically."""
    blocks: dict[str, dict] = {}
    for hull in hulls:
        n_scout = HULLS[hull]["scout"]
        for row in PROFILES:
            for arm in ARMS:
                tid = tier_id(hull, row["profile_id"], arm)
                blocks[f"scout_{tid}"] = block_for(tid, seeds(hull)[:n_scout])
                blocks[tid] = block_for(tid, seeds(hull)[n_scout:])
    return blocks


def build_campaign(hulls: tuple[str, ...], name: str, memory: str) -> dict:
    suffix = "_mega" if hulls == ("meg",) else ""
    return {
        "name": name,
        "pathogen": "norovirus",
        "manifest": MANIFEST_REL,
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": f"campaign/{CAMPAIGN}{suffix}/",
        "queue": "picard-campaign-queue",
        "image_tag": IMAGE_TAG_MEGA if suffix else IMAGE_TAG,
        "resources": {"vcpu": "1", "memory": memory, "shm": 512},
        "blocks": _blocks(hulls),
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def seed_manifest() -> dict:
    """Execution manifest Edison verifies on delivery."""
    return {
        "rule": (
            "Every cell takes the ascending prefix of its hull's "
            "NORO-PROVISIONED-VENUE-02 seed block (exp 8000-8999; "
            "cls/spr/meg 8105-9104), so each (hull, profile, arm) cell "
            "pairs seed-for-seed with the venue02 arm of the same hull "
            "and venue pin, and with every other profile on that hull."
        ),
        "scout_rule": (
            "Nested canary = the first 8 seeds of every cell (192 x 8 = "
            "1,536 runs), submitted first; the main remainder is "
            "submitted only after the scout readout gate."
        ),
        "reserve_rule": (
            "Reserve seeds = the next ascending seeds after the main "
            "prefix, 2 per hull x 48 cells = 96 slots per hull; used only "
            "to replace a cell's failed/truncated seed by a hand-added "
            "retry block recorded in LEDGER.md.  A cell short of its n "
            "after the reserve is published as missing, never reseeded."
        ),
        "design": {
            "generator": "E = ABCD (I = ABCDE), Resolution V",
            "factors": FACTOR_LEVELS,
            "profiles": [
                {**row, "levels": profile_levels(row)} for row in PROFILES
            ],
        },
        "hulls": {
            h: {
                "platform": HULLS[h]["platform"],
                "num_agents": HULLS[h]["num_agents"],
                "n_per_cell": HULLS[h]["n"],
                "scout_per_cell": HULLS[h]["scout"],
                "seed_range": [seeds(h)[0], seeds(h)[-1]],
                "scout_seed_range": [scout_seeds(h)[0], scout_seeds(h)[-1]],
                "reserve_seeds": reserve_seeds(h),
                "cells": len(PROFILES) * len(ARMS),
                "runs_main": HULLS[h]["n"] * len(PROFILES) * len(ARMS),
                "runs_scout": HULLS[h]["scout"] * len(PROFILES) * len(ARMS),
                "venue_pin": {
                    "crew_venue": HULLS[h]["pin_crew"],
                    "passenger_venue": HULLS[h]["pin_pax"],
                    "mixed_venue": HULLS[h]["pin_mix"],
                },
                "mixed_venue_weights": HULLS[h]["w_mix"],
            }
            for h in HULLS
        },
        "totals": {
            "cells": len(HULLS) * len(PROFILES) * len(ARMS),
            "runs_main": sum(
                HULLS[h]["n"] * len(PROFILES) * len(ARMS) for h in HULLS
            ),
            "runs_scout": sum(
                HULLS[h]["scout"] * len(PROFILES) * len(ARMS) for h in HULLS
            ),
        },
    }


def profile_table_md() -> str:
    lines = [
        "# SENSITIVITY-01 half-fraction profile table",
        "",
        "2^(5-1) Resolution-V, generator **E = ABCD** (defining relation "
        "I = ABCDE). Rows in standard order on A..D; E is the sign "
        "product. Generated by `design/build.py` — edit there, not here.",
        "",
        "| profile | A q_source | B pax prev | C crew prev | D illness draw "
        "| E route scale | q_source | pax | crew | draw | scale |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in PROFILES:
        lv = profile_levels(row)
        lines.append(
            f"| {row['profile_id']} | {_SIGN[row['A']]} | {_SIGN[row['B']]} "
            f"| {_SIGN[row['C']]} | {_SIGN[row['D']]} | {_SIGN[row['E']]} "
            f"| {lv['q_source']} | {lv['boarding_passenger_prevalence']} "
            f"| {lv['boarding_crew_prevalence']} | {lv['illness_duration_draw']} "
            f"| x{lv['route_scale']} |"
        )
    lines += [
        "",
        "Route dict at x0.5: `" + json.dumps(route_dict(0.5)) + "`",
        "",
        "Route dict at x2.0: `" + json.dumps(route_dict(2.0)) + "`",
        "",
        "Balance check: each factor has 8 (-) and 8 (+) rows; every pair "
        "of factors has 4 rows per sign combination.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    manifest = build_manifest()
    (REPO / MANIFEST_REL).write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    base = REPO / "campaigns/noro/provisioned_sensitivity_01"
    (base / "campaign.json").write_text(
        json.dumps(build_campaign(SMALL_HULLS, CAMPAIGN, "4096"), indent=1)
        + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_sensitivity_01_mega/campaign.json").write_text(
        json.dumps(build_campaign(("meg",), f"{CAMPAIGN}_mega", "8192"),
                   indent=1) + "\n", encoding="utf-8",
    )
    (base / "SEED_MANIFEST.json").write_text(
        json.dumps(seed_manifest(), indent=1) + "\n", encoding="utf-8",
    )
    (base / "PROFILE_TABLE.md").write_text(profile_table_md(), encoding="utf-8")
    sm = seed_manifest()["totals"]
    print(f"tiers {len(manifest['tiers'])}  cells {sm['cells']}  "
          f"main {sm['runs_main']}  scout {sm['runs_scout']}")


if __name__ == "__main__":
    main()
