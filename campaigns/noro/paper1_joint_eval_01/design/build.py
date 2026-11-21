#!/usr/bin/env python3
"""Deterministic builder for noro_paper1_joint_eval_01 (Paper-1 WP2).

Writes ``../manifest.json`` and ``../campaign.json``. Every tier's
``config_overrides`` is the freeze contract's section 2 block, parsed from
the contract and carried verbatim -- this file adds, removes and edits no
key in it. The frozen design (strata, seed rule, go/no-go criteria) is in
``../DESIGN.md``; the numbers here are that document's numbers.

Two stages:

* Stage A (always emitted): the boarding census that assigns seeds to
  strata, the tail-resolution cells and the labelled-baseline arm.
* Stage B (emitted only when ``seed_selection.json`` exists): the 36 bridge
  tiers. Seed identities come from the census, which is a Batch stage gated
  on the declared freeze, so they cannot be written at authoring time.

``--check`` exits non-zero if the committed files differ from a rebuild.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CAMPAIGN_DIR = HERE.parent
REPO_ROOT = CAMPAIGN_DIR.parents[2]
CONTRACT = "docs/norovirus/paper1_freeze_design_contract_2026_11_20.md"
BLOCK_MARKER = "<!-- paper1-frozen-config-block -->"
SELECTION = HERE / "seed_selection.json"
NAME = "noro_paper1_joint_eval_01"
REL = "campaigns/noro/paper1_joint_eval_01"

# Contract section 2.5: hulls and emitted complements.
HULLS = {
    "exp": ("expedition_cruise_450", 450),
    "cls": ("classic_cruise_1900", 1910),
    "spr": ("spirit_cruise_3000", 3000),
    "meg": ("mega_cruise_5000", 7000),
}
EPOCHS = (168, 288, 504)
# Contract section 5 seed counts (proposals under Edison's review).
STRATA = {"quiet": 300, "near": 100, "outbreak": 20}
TAIL_SEEDS = 1000
TAIL_EPOCHS = 288
DOSE = 7.57
SURVEILLANCE = "syndromic_comp65"

# Boarding census: fixed budget, dedicated ranges that overlap no earlier
# campaign (supply_seed_scan_01 ends at 1,037,199).
CENSUS_SEEDS_PER_HULL = 20000
CENSUS_CHUNK = 100
CENSUS_START = {"exp": 2000000, "cls": 2100000, "spr": 2200000, "meg": 2300000}
TAIL_START = {"exp": 2400000, "cls": 2410000, "spr": 2420000, "meg": 2430000}

# Go/no-go criteria, fixed before any cell runs. Not fitted to any anchor.
CRITERIA = {
    "posting_definition": "derived.vsp_trigger_epoch is not None",
    "quiet_max_posting_rate": 0.02,
    "outbreak_min_posting_rate": 0.50,
    "near_min_posting_rate": 0.10,
    "near_max_posting_rate": 0.90,
    "comparable_ratio": 0.5,
    "interval": "Clopper-Pearson two-sided 95%",
    "scope": "every hull x length cell; overall go needs all 12",
}
SELECTION_RULE = {
    "census": "1 epoch, 100 agents, frozen block, arm station_lots (no "
              "added keys), worker tools/noro_diag/supply_seed_scan.py",
    "contaminated": "provisioned_source.n_contaminated > 0",
    "burden": "sum over contaminated lots of "
              "lot_servings * lot_titre_gec_per_g * 150 g",
    "quiet": "first 300 uncontaminated seeds in ascending seed order",
    "outbreak": "20 contaminated seeds of highest burden (ties: lower seed)",
    "near": "100 contaminated seeds of lowest burden (ties: lower seed), "
            "disjoint from outbreak",
    "pairing": "one seed list per hull and stratum, reused at 168/288/504",
    "shortfall": "a stratum that cannot be filled from the fixed census "
                 "budget is reported with its achieved count and bound; "
                 "the census is not extended and no seed is hand-picked",
}
# Labelled baseline: a prior campaign's tier re-run verbatim on its own
# seeds; reference fingerprints are computed from that campaign's archive
# at the gated stage (readout.py --reference-root).
BASELINE = {
    "manifest": "campaigns/noro/supply_solver_screen_01/manifest.json",
    "tier": "fl_exp_12d_sens_p06_paxv_station_lots_continuous",
    "id": "je_bl_exp_solver01_station_continuous",
    "seeds_from": "campaigns/noro/supply_solver_screen_01/campaign.json",
    "block": "exp_station_lots_continuous",
}


def load_block() -> dict[str, Any]:
    text = (REPO_ROOT / CONTRACT).read_text(encoding="utf-8")
    match = re.search(
        re.escape(BLOCK_MARKER) + r"\s*```json\n(.*?)```", text, re.S,
    )
    if match is None:
        raise SystemExit(f"frozen block not found in {CONTRACT}")
    return json.loads(match.group(1))


def block_sha(block: dict[str, Any]) -> str:
    canonical = json.dumps(block, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def tier(
    hull: str, epochs: int, seeds: list[int], meta: dict[str, Any],
    block: dict[str, Any],
) -> dict[str, Any]:
    platform, num_agents = HULLS[hull]
    return {
        "platform": platform,
        "pathogen": "norovirus",
        "dose_adjustments": [DOSE],
        "surveillance_strategies": [SURVEILLANCE],
        "epoch_durations": [epochs],
        "num_agents": num_agents,
        "description": (
            f"Paper-1 WP2 joint evaluation: {platform}, {epochs} epochs, "
            f"{meta['arm']} {meta.get('stratum', '')}".strip()
            + "; config_overrides = freeze contract section 2 block verbatim."
        ),
        "config_overrides": json.loads(json.dumps(block)),
        "seeds": seeds,
        "joint_eval": {"hull": platform, "epochs": epochs, **meta},
    }


def load_selection() -> dict[str, Any] | None:
    if not SELECTION.is_file():
        return None
    return json.loads(SELECTION.read_text(encoding="utf-8"))


def bridge_tiers(
    selection: dict[str, Any], block: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out = {}
    for hull in HULLS:
        for epochs in EPOCHS:
            for stratum in STRATA:
                seeds = [int(s) for s in selection[hull][stratum]]
                out[f"je_{hull}_{epochs // 24}d_{stratum}"] = tier(
                    hull, epochs, seeds,
                    {"arm": "bridge", "stratum": stratum}, block,
                )
    return out


def baseline_tier() -> tuple[dict[str, Any], list[int]]:
    source = json.loads(
        (REPO_ROOT / BASELINE["manifest"]).read_text(encoding="utf-8"),
    )
    spec = json.loads(json.dumps(source["tiers"][BASELINE["tier"]]))
    seeds = json.loads(
        (REPO_ROOT / BASELINE["seeds_from"]).read_text(encoding="utf-8"),
    )["blocks"][BASELINE["block"]]["seeds"]
    spec["seeds"] = [int(s) for s in seeds]
    spec["joint_eval"] = {
        "arm": "baseline",
        "hull": spec["platform"],
        "epochs": spec["epoch_durations"][0],
        "source": f"{BASELINE['manifest']}#{BASELINE['tier']}",
        "note": "prior tier verbatim; does NOT carry the frozen block",
        "reference_fingerprints": {},
    }
    return spec, spec["seeds"]


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    block = load_block()
    selection = load_selection()
    tiers: dict[str, dict[str, Any]] = {}
    blocks: dict[str, dict[str, Any]] = {}
    worker = f"{REL}/cell.py"
    for hull in HULLS:
        census_id = f"je_census_{hull}"
        tiers[census_id] = tier(
            hull, 1, [CENSUS_START[hull]], {"arm": "census"}, block,
        )
        blocks[f"census_{hull}"] = {
            "worker": "tools/noro_diag/supply_seed_scan.py",
            "artifact": "supply_seed_scan_chunk{seed}.jsonl",
            "seeds": list(range(CENSUS_SEEDS_PER_HULL // CENSUS_CHUNK)),
            "args": {
                "tier": census_id, "arm": "station_lots", "hull": hull,
                "seed_start": CENSUS_START[hull],
                "seed_count": CENSUS_SEEDS_PER_HULL,
                "chunk_size": CENSUS_CHUNK, "epochs": 1, "num_agents": 100,
                "artifact_stem": f"je_census_{hull}",
            },
        }
        tail_id = f"je_{hull}_{TAIL_EPOCHS // 24}d_tail"
        tail_seeds = list(range(TAIL_START[hull], TAIL_START[hull] + TAIL_SEEDS))
        tiers[tail_id] = tier(
            hull, TAIL_EPOCHS, tail_seeds, {"arm": "tail"}, block,
        )
        blocks[tail_id] = {"worker": worker, "tier": tail_id, "seeds": tail_seeds}
    base_spec, base_seeds = baseline_tier()
    tiers[BASELINE["id"]] = base_spec
    blocks[BASELINE["id"]] = {
        "worker": worker, "tier": BASELINE["id"], "seeds": base_seeds,
    }
    if selection is not None:
        for tier_id, spec in bridge_tiers(selection, block).items():
            tiers[tier_id] = spec
            blocks[tier_id] = {
                "worker": worker, "tier": tier_id, "seeds": spec["seeds"],
            }
    manifest = {
        "campaign": NAME,
        "description": (
            "Paper-1 WP2 joint four-hull evaluation: 4 hulls x "
            "{168,288,504} epochs x {quiet, near, outbreak} bridge strata "
            "on census-selected paired seeds, plus tail-resolution cells "
            "and a labelled baseline. Design: "
            f"{REL}/DESIGN.md."
        ),
        "platform": "classic_cruise_1900",
        "default_epochs": 288,
        "default_num_agents": 1910,
        "embarkation_date": "2026-01-10",
        "natural_history_clock": "hours",
        "pathogen_configs": {"norovirus": {
            "bundle": "active_profiles", "pathogen_id": "norwalk_gi",
            "overrides": {"remove": ["sars_cov2_resp"]},
        }},
        "surveillance_configs": {SURVEILLANCE: {
            "diagnostic_cascade": {"enabled": False},
            "fred_behavior": {
                "quarantine_compliance": 0.65,
                "compliance_by_class": {
                    "crew": 0.65, "passenger_elderly": 0.54,
                    "passenger_young": 0.34,
                },
            },
        }},
        "joint_eval": {
            "contract": CONTRACT,
            "block_sha256": block_sha(block),
            "stage_b_emitted": selection is not None,
            "strata_seed_counts": STRATA,
            "selection_rule": SELECTION_RULE,
            "criteria": CRITERIA,
        },
        "tiers": tiers,
    }
    campaign = {
        "name": NAME,
        "pathogen": "norovirus",
        "manifest": f"{REL}/manifest.json",
        "pathogen_id": "norwalk_gi",
        "epochs": 288,
        "s3_prefix": f"campaign/{NAME}/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-paper1-joint-eval01",
        "resources": {"vcpu": "1", "memory": "8192", "shm": 512},
        "blocks": blocks,
        "readout": f"{REL}/readout.py",
    }
    return manifest, campaign


def render(obj: dict[str, Any]) -> str:
    return json.dumps(obj, indent=1) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest, campaign = build()
    targets = {
        CAMPAIGN_DIR / "manifest.json": render(manifest),
        CAMPAIGN_DIR / "campaign.json": render(campaign),
    }
    if args.check:
        stale = [
            p.name for p, text in targets.items()
            if not p.is_file() or p.read_text(encoding="utf-8") != text
        ]
        print("stale: " + ", ".join(stale) if stale else "build reproduces")
        return 1 if stale else 0
    for path, text in targets.items():
        path.write_text(text, encoding="utf-8")
    runs = sum(len(b["seeds"]) for b in campaign["blocks"].values())
    print(f"{len(manifest['tiers'])} tiers, {len(campaign['blocks'])} "
          f"blocks, {runs} array children")
    return 0


if __name__ == "__main__":
    sys.exit(main())
