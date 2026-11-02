#!/usr/bin/env python3
"""Emit NORO-PROVISIONED-VENUE-01's manifest and campaign specs.

Edison PHASE2_PILOT_SPEC (approved scope): the provisioned-lot venue
placement counterfactual — does relocating provisioned food-source
lots from crew-mess venues to the largest passenger dining venue
reverse the crew-heavy threshold-crossing pattern? 4 hulls x 2
placement arms x 4 seeds = 32 runs on the q30 (q_source = 0.003)
provisioned-source spec, extracted via first_paper_scalar/1.4.0.

Placement-only intervention (spec SS2.7): source count, seeded epoch,
dose and kind stay fixed — the same per-station contamination draws
run, then each minted station's zone re-maps onto the arm's pin set
(engines/transmission_core.py ``station_zone_pin``; the census is
never restricted so n_lots cannot shrink).  Round-robin across
multi-zone pin sets, in mint (census) order — deterministic, no
extra RNG consumption, non-placement dimensions stay seed-paired
with the delivered q30 baseline arm.

Run from the repo root:

    python3 campaigns/noro/provisioned_venue_01/design/build.py

Writes (deterministically — every field is declared here):

- picard_framework/runs/mega_cruise_campaign/noro_provisioned_venue_01_manifest.json
- campaigns/noro/provisioned_venue_01/campaign.json
- campaigns/noro/provisioned_venue_01_mega/campaign.json
- campaigns/noro/provisioned_venue_01/SEED_MANIFEST.json (execution
  manifest Edison verifies on delivery)

NOTE: the campaign does not submit until the venue-pin seam merges
and the image pins a SHA containing it (campaign-preflight skill).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

# Per-hull venue pins (served-venue x item-line station census
# verified 2026-11-02, DESIGN.md SS2): crew-mess aliases for the
# crew_venue arm, the spec-pinned largest passenger dining venue for
# passenger_venue.  Spec's "expedition_cruise_300" resolves to
# expedition_cruise_450 — CrewMess/MainDining exist verbatim only on
# the 450 hull (the 300 uses Crew_Mess/Main_Dining_Room) and the
# delivered 38k baseline ran on 450; documented per spec's
# substitution rule.  mega: Windjammer seats 1600 > MainDining_L
# 1400, but the spec explicitly pins MainDining_L — kept, documented.
HULLS = {
    "exp": {"platform": "expedition_cruise_450", "num_agents": 450,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining"],
            "seeds": [8869, 8326, 8494, 8557]},
    "cls": {"platform": "classic_cruise_1900", "num_agents": 1910,
            "pin_crew": ["CrewMess"], "pin_pax": ["MainDining_L"],
            "seeds": [8892, 8452, 8498, 8983]},
    "spr": {"platform": "spirit_cruise_3000", "num_agents": 3000,
            "pin_crew": ["CrewMessMain", "CrewMessOff"],
            "pin_pax": ["MainDining_L"],
            "seeds": [8620, 8894, 8869, 8143]},
    "meg": {"platform": "mega_cruise_5000", "num_agents": 7000,
            "pin_crew": ["Crew_Mess_Main", "CrewMess_Fwd"],
            "pin_pax": ["MainDining_L"],
            "seeds": [8548, 8461, 8199, 8577]},
}
SMALL_HULLS = ("exp", "cls", "spr")

ARMS = ("crew_venue", "passenger_venue")

# Shipped class mix, copied verbatim from crusher_labs/config.yaml
# ship_graph.agent_classes — identical stamp to
# campaigns/noro/provisioned_source_01/design/build.py so cells pair
# voyage-for-voyage with the delivered q30 baseline arm.
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
    return HULLS[hull]["pin_crew" if arm == "crew_venue" else "pin_pax"]


def base_overrides(hull: str, arm: str) -> dict:
    """The FOOD-01/FOOD-02 transmission + hvac block on the q30
    provisioned-source spec, plus the venue pin — the only delta vs
    the delivered q30 baseline arm is the pin + arm label."""
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
                "provisioned_source": {
                    "source_id": "generic_cruise_port",
                    "q_source": 0.003,
                    "station_zone_pin": _pin(hull, arm),
                    "source_venue_arm": arm,
                },
            },
        },
        "hvac": {"pathogen_pool_transport": "airflow"},
        "ship_graph": {"agent_classes": BASE_AGENT_CLASSES},
    }


def tier(hull: str, arm: str) -> tuple[str, dict]:
    tier_id = f"fl_{hull}_12d_scr_q30_{'crewv' if arm == 'crew_venue' else 'paxv'}"
    return tier_id, {
        "platform": HULLS[hull]["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [7.57],
        "surveillance_strategies": ["syndromic_comp65"],
        "epoch_durations": [288],
        "num_agents": HULLS[hull]["num_agents"],
        "description": (
            f"provisioned-source q30 venue-pin arm {arm}; pin "
            f"{_pin(hull, arm)} — scr mid diagonal (bp32.5c18.5), "
            "nsf29, 288 epochs, comp65, dose 7.57 — fixed "
            "coordinates identical to the delivered "
            "NORO-PROVISIONED-SOURCE-01 q30 baseline."
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
        "campaign": "noro_provisioned_venue_01",
        "description": (
            "NORO-PROVISIONED-VENUE-01 (Edison PHASE2_PILOT_SPEC): "
            "the provisioned-lot venue placement counterfactual — "
            "crew_mess vs largest passenger dining venue on the q30 "
            "(q_source=0.003) provisioned-source spec.  "
            "Placement-only: identical census draws, minted-station "
            "zones re-mapped onto the arm's pin set, count "
            "preserved.  4 hulls x 2 arms x 4 native-crosser seeds "
            "= 32 cells; seeds picked nearest the delivered 38k's "
            "posting-conditional medians (SEED_MANIFEST.json).  "
            "Extraction via first_paper_scalar/1.4.0 "
            "(source_venue_arm, actual_venues_used, n_lots_placed).  "
            "Does not submit until the venue-pin seam merges and "
            "the image pins a SHA containing it."
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
            tid = f"fl_{hull}_12d_scr_q30_{'crewv' if arm == 'crew_venue' else 'paxv'}"
            blocks[tid] = block_for(tid, HULLS[hull]["seeds"])
        # Canary: one cell per arm on the first picked seed — both
        # pins exercise on every hull before the 32-cell array.
        blocks[f"canary_{hull}_crewv"] = block_for(
            f"fl_{hull}_12d_scr_q30_crewv", HULLS[hull]["seeds"][:1],
        )
        blocks[f"canary_{hull}_paxv"] = block_for(
            f"fl_{hull}_12d_scr_q30_paxv", HULLS[hull]["seeds"][:1],
        )
    return blocks


def build_campaign(hulls: tuple[str, ...], name: str,
                   memory: str) -> dict:
    suffix = "_mega" if hulls == ("meg",) else ""
    return {
        "name": name,
        "pathogen": "norovirus",
        "manifest": ("picard_framework/runs/mega_cruise_campaign/"
                     "noro_provisioned_venue_01_manifest.json"),
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": f"campaign/noro_provisioned_venue_01{suffix}/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-provisioned-venue01",
        "resources": {"vcpu": "1", "memory": memory, "shm": 512},
        "blocks": _blocks(hulls),
        "readout": "tools/noro_diag/outbreak_anchor_readout.py",
    }


def seed_manifest() -> dict:
    """Execution manifest Edison verifies on delivery: exact seeds +
    the selection rule + per-seed baseline rows."""
    picks = json.loads(
        (REPO / "campaigns/noro/provisioned_venue_01/"
         "seed_picks.json").read_text(encoding="utf-8"),
    )
    return {
        "rule": (
            "Among the delivered NORO-PROVISIONED-SOURCE-01 q30 "
            "native-crosser seeds (scan row posted=true, "
            "_scan_rows/fl_<hull>_12d_scr_q30.jsonl), rank by "
            "|rep_pax_n-med_pax|/max(med_pax,1) + "
            "|rep_crew_n-med_crew|/max(med_crew,1), tie-break seed "
            "ascending; take the first 4."
        ),
        "crosser_pool": {
            h: picks[h]["n_posted"] for h in HULLS
        },
        "conditional_medians": {
            h: {"rep_pax_n": picks[h]["median_rep_pax_n"],
                "rep_crew_n": picks[h]["median_rep_crew_n"]}
            for h in HULLS
        },
        "hulls": {
            h: {
                "platform": HULLS[h]["platform"],
                "venue_pin": {
                    "crew_venue": HULLS[h]["pin_crew"],
                    "passenger_venue": HULLS[h]["pin_pax"],
                },
                "seeds": [
                    {k: s[k] for k in (
                        "seed", "rep_pax_n", "rep_crew_n",
                        "rep_pax_ar", "rep_crew_ar", "n_acquired",
                        "key")}
                    for s in picks[h]["seeds"]
                ],
            }
            for h in HULLS
        },
    }


def main() -> None:
    manifest = build_manifest()
    (REPO / "picard_framework/runs/mega_cruise_campaign/"
     "noro_provisioned_venue_01_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_01/campaign.json").write_text(
        json.dumps(
            build_campaign(SMALL_HULLS, "noro_provisioned_venue_01",
                           "4096"),
            indent=1,
        ) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_01_mega/"
     "campaign.json").write_text(
        json.dumps(
            build_campaign(("meg",), "noro_provisioned_venue_01_mega",
                           "8192"),
            indent=1,
        ) + "\n", encoding="utf-8",
    )
    (REPO / "campaigns/noro/provisioned_venue_01/"
     "SEED_MANIFEST.json").write_text(
        json.dumps(seed_manifest(), indent=1) + "\n", encoding="utf-8",
    )
    n_cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
    print(f"manifest: {len(manifest['tiers'])} tiers, {n_cells} cells")


if __name__ == "__main__":
    main()
