#!/usr/bin/env python3
"""Deterministic builder for noro_paper1_joint_eval_01 (Paper-1 WP2).

Writes ``../manifest.json`` and ``../campaign.json``. The frozen design is
``../DESIGN.md``; the numbers here are that document's numbers.

Baseline and arms. The freeze contract's section 2 block is the invariant
baseline, parsed from the contract and stored once in the manifest
(``joint_eval.baseline_block``). Every tier is an arm: it declares the leaf
paths on which it differs (``changed_paths``; for every bridge, pilot and
census tier exactly one, the hull's ``ship_graph.agent_classes``, which
places the platform's declared passengers and crew) and carries the complete effective nested object, because
``merge_config_overrides`` is one level deep. ``build()`` refuses to emit a
tier whose effective config differs from the baseline anywhere it did not
declare. ``cell.py`` repeats the check and then validates the
engine-resolved config after the runner has applied every axis.

Stages:

* Stage A (always emitted): the boarding census and the reproduction arm.
* Stage B (emitted only when ``seed_selection.json`` exists): the small
  bridge (36 tiers) and the joint-outcome pilot (8 tiers). Seed identities
  come from the census, a Batch stage gated on the declared freeze.

``--check`` exits non-zero if the committed files differ from a rebuild.
``--select DIR`` applies the frozen selection rule to census JSONL rows and
writes ``seed_selection.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
CAMPAIGN_DIR = HERE.parent
REPO_ROOT = CAMPAIGN_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.platform_complement import declared_complement  # noqa: E402

CONTRACT = "docs/norovirus/paper1_freeze_design_contract_2026_11_20.md"
BLOCK_MARKER = "<!-- paper1-frozen-config-block -->"
SELECTION = HERE / "seed_selection.json"
NAME = "noro_paper1_joint_eval_01"
REL = "campaigns/noro/paper1_joint_eval_01"
ABSENT = "<absent>"

# platform, total agents, and role counts. ``intended_roles`` is the
# platform's declared nominal_complement, which every block arm reaches
# through its declared ``ship_graph.agent_classes`` difference (class_mix
# below). ``template_roles`` is what the shipped 70/30 class template placed
# before that difference was declared (measured at initialise, two seeds
# per hull); kept as the record of why the difference exists.
HULLS: dict[str, dict[str, Any]] = {
    "exp": {"platform": "expedition_cruise_450", "num_agents": 450,
            "intended_roles": {"passenger": 300, "crew": 150},
            "template_roles": {"passenger": 316, "crew": 134}},
    "cls": {"platform": "classic_cruise_1900", "num_agents": 1910,
            "intended_roles": {"passenger": 1350, "crew": 560},
            "template_roles": {"passenger": 1338, "crew": 572}},
    "spr": {"platform": "spirit_cruise_3000", "num_agents": 3000,
            "intended_roles": {"passenger": 2100, "crew": 900},
            "template_roles": {"passenger": 2100, "crew": 900}},
    "meg": {"platform": "mega_cruise_5000", "num_agents": 7000,
            "intended_roles": {"passenger": 5000, "crew": 2000},
            "template_roles": {"passenger": 4900, "crew": 2100}},
}
CLASS_MIX_PATH = "ship_graph.agent_classes"
# Voyage epochs -> day label used in tier ids (hours clock).
VOYAGE_DAYS = {168: 7, 288: 12, 504: 21}
EPOCHS = tuple(VOYAGE_DAYS)
DOSE = 7.57
SURVEILLANCE = "syndromic_comp65"

# Small complete bridge: diagnostic, census-selected, paired across lengths.
BRIDGE_STRATA = ("quiet", "near", "outbreak")
BRIDGE_SEEDS = 20
# Joint-outcome pilot: independently sampled evaluation seeds, 288 epochs.
PILOT_EPOCHS = 288
PILOT_SOURCE_STRATA = ("uncontaminated", "contaminated")
PILOT_SEEDS = 20

# Boarding census: fixed budget, dedicated ranges that overlap no earlier
# campaign (supply_seed_scan_01 ends at 1,037,199).
CENSUS_SEEDS_PER_HULL = 20000
CENSUS_CHUNK = 100
CENSUS_START = {"exp": 2000000, "cls": 2100000, "spr": 2200000, "meg": 2300000}

SELECTION_RULE = {
    "census": "1 epoch, 100 agents, baseline block, arm station_lots (adds "
              "no key), worker tools/noro_diag/supply_seed_scan.py",
    "sampling_frame": "per hull, the 20,000 consecutive census seeds; a "
                      "seed is one voyage draw under the baseline block",
    "source_strata": "contaminated: provisioned_source[norwalk_gi].n_contaminated "
                     "> 0; "
                     "uncontaminated: == 0",
    "burden": "sum over provisioned_lot objects of "
              "lot_servings * lot_titre_gec_per_g * 150 g",
    "diagnostic_quiet": "first 20 uncontaminated seeds, ascending seed",
    "diagnostic_outbreak": "20 contaminated seeds of highest burden "
                           "(ties: lower seed)",
    "diagnostic_near": "20 contaminated seeds of lowest burden (ties: "
                       "lower seed), disjoint from outbreak",
    "evaluation": "per source stratum, the 20 frame seeds of lowest "
                  "sha256('noro_paper1_joint_eval_01:<seed>') -- an equal-"
                  "probability sample without replacement; inclusion "
                  "probability n_s / N_s and weight N_s / n_s are written "
                  "to seed_selection.json",
    "pairing": "one diagnostic seed list per hull and stratum, reused at "
               "168/288/504",
    "status": "diagnostic seeds are purposive and carry no population "
              "weight; only evaluation seeds support population estimates",
    "shortfall": "a stratum the fixed census cannot fill is run at its "
                 "achieved count and reported; the census is not extended "
                 "and no seed is hand-picked",
}

# The bridge gate is technical completion only. No outcome voids the freeze.
TECHNICAL_COMPLETION = {
    "intended_inputs_used": "every archive: voyage length equals the "
                            "tier's epochs, arm changed_paths equal the "
                            "declaration, effective config resolved with "
                            "no mismatch, effective hash equals the "
                            "manifest tier's, intended role counts on "
                            "initialised agents and in the payload, engine "
                            "commit recorded and single-valued per tier",
    "outcomes_extractable": "every archive: all six families 'present'",
    "attempts_accounted": "the seeds read are exactly the tier's seeds, "
                          "each once; a failed child is listed with its "
                          "reason, retried at most once on the same seed, "
                          "never replaced by a new seed",
    "pairs_meaningful": "within hull and stratum the three lengths hold "
                        "the same seed set and all three are read; the "
                        "reproduction arm is compared seed by seed",
}
# Diagnostic bands for the ordering readout. Declared, not fitted; they
# label a measured result and select a continuation, never a verdict.
DIAGNOSTIC_BANDS = {
    "posting_definition": "derived.vsp_trigger_epoch is not None",
    "quiet_max_posting_rate": 0.02,
    "outbreak_min_posting_rate": 0.50,
    "near_min_posting_rate": 0.10,
    "near_max_posting_rate": 0.90,
    "interval": "Clopper-Pearson two-sided 95%",
    "cell_in": "quiet <= quiet_max, outbreak >= outbreak_min, and "
               "quiet < near < outbreak with near inside [near_min, near_max]",
    "cell_out": "an interval excludes its band: quiet lower bound > "
                "quiet_max, outbreak upper bound < outbreak_min, or the "
                "near interval lies wholly outside [near_min, near_max]",
    "cell_undetermined": "neither in nor out",
    "hull_status": "in if all three lengths are in; out if any length is "
                   "out; otherwise undetermined",
}
CONTINUATION = {
    "precondition": "evaluated only when technical completion holds",
    "justified_defect_fix": "the reproduction arm does not reproduce, or "
                            "an input check failed. Requires a named "
                            "defect with paired-seed evidence before any "
                            "fix; never opened by an outcome alone",
    "reconstruction": "every hull is out",
    "population_geometry": "some hulls are out and others are not "
                           "(includes a zero-event large hull)",
    "uncertainty": "no hull is out and at least one is undetermined",
    "precision": "every hull is in: allocate replication from the pilots",
    "precedence": ["justified_defect_fix", "reconstruction",
                   "population_geometry", "uncertainty", "precision"],
}
PRECISION = {
    "zero_event_convention": "k = 0 of n: exact (Clopper-Pearson) "
                             "one-sided 95% upper bound 1 - 0.05^(1/n); "
                             "0/300 -> 0.994%, 0/20 -> 13.9%. Stated with "
                             "its sampling frame: hull, voyage length, "
                             "source stratum, census seed range",
    "bridge_n20": "two-sided 95% half-width about +/-0.23 at a rate of "
                  "0.5; the bridge resolves ordering, not rates",
    "targets": {
        "posting_probability": "two-sided 95% half-width <= 0.10 per hull "
                               "x length (about 100 seeds near 0.5)",
        "quiet_bound": "one-sided 95% upper bound <= 1% (300 zero-event "
                       "evaluation seeds in the uncontaminated stratum)",
        "first_role_split": "half-width <= 0.10 among posted voyages",
        "size_tail": "tail frequencies from >= 1,000 seeds per cell",
        "curves_environment": "descriptive (median and IQR of timing); "
                              "no precision target",
    },
    "allocation": "per hull, Neyman allocation across source strata from "
                  "the pilot: n_s proportional to W_s * sqrt(p_s(1-p_s)), "
                  "W_s = N_s / N from the census; a stratum with p_s = 0 "
                  "in the pilot is sized by the quiet_bound target",
    "population_estimate": "stratified (Horvitz-Thompson) over evaluation "
                           "seeds: sum_s W_s * p_s; diagnostic seeds are "
                           "excluded",
    "temporal_pilot": "from the bridge's paired lengths: if every 504-"
                      "epoch run's role-report series is bit-identical "
                      "over its first 168 and 288 epochs to the same "
                      "seed's shorter runs, replication runs 504 only and "
                      "truncates; otherwise each length is replicated",
    "batches": "bridge, pilot and each replication block are fixed-size "
               "batches declared before submission; a batch is analysed "
               "once, when every child is accounted for; no interim look "
               "changes a batch size and earlier batches are not "
               "re-analysed under new rules",
}
# Reproduction arm: a prior campaign's tier re-run on its own seeds.
REPRODUCTION = {
    "manifest": "campaigns/noro/supply_solver_screen_01/manifest.json",
    "tier": "fl_exp_12d_sens_p06_paxv_station_lots_continuous",
    "id": "fl_je_repro_exp_solver01_station_continuous",
    "seeds_from": "campaigns/noro/supply_solver_screen_01/campaign.json",
    "block": "exp_station_lots_continuous",
    "hull": "exp",
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


def leaf_items(tree: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out.extend(leaf_items(value, f"{path}."))
        else:
            out.append((path, value))
    return out


def changed_paths(
    baseline: dict[str, Any], effective: dict[str, Any],
) -> list[dict[str, Any]]:
    base = dict(leaf_items(baseline))
    arm = dict(leaf_items(effective))
    return [
        {"path": path, "baseline": base.get(path, ABSENT),
         "arm": arm.get(path, ABSENT)}
        for path in sorted(set(base) | set(arm))
        if base.get(path, ABSENT) != arm.get(path, ABSENT)
    ]


def materialize(
    block: dict[str, Any], changes: dict[str, Any],
) -> dict[str, Any]:
    """Baseline plus declared leaf changes, as complete nested objects."""
    effective = json.loads(json.dumps(block))
    for dotted, value in changes.items():
        node = effective
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    declared = sorted(changes)
    actual = [c["path"] for c in changed_paths(block, effective)]
    if actual != declared:
        raise SystemExit(f"arm changes {declared} materialised as {actual}")
    return effective


def shipped_classes() -> list[dict[str, Any]]:
    """``ship_graph.agent_classes`` as shipped in crusher_labs/config.yaml."""
    text = (REPO_ROOT / "crusher_labs" / "config.yaml").read_text(
        encoding="utf-8",
    )
    return yaml.safe_load(text)["ship_graph"]["agent_classes"]


def class_mix(hull: str) -> list[dict[str, Any]]:
    """The shipped class list re-weighted to the hull's declared roles.

    Within each role the shipped proportions are kept; each class gets a
    whole number of agents (largest remainder, ties to the earlier class)
    and its fraction is that count over the complement, so the engine
    places exactly the platform's declared passengers and crew.
    """
    spec = HULLS[hull]
    passengers, crew = declared_complement(spec["platform"])
    if {"passenger": passengers, "crew": crew} != spec["intended_roles"]:
        raise SystemExit(f"{hull}: intended roles differ from the platform")
    classes = json.loads(json.dumps(shipped_classes()))
    for role, total in spec["intended_roles"].items():
        members = [c for c in classes if c["role_group"] == role]
        share = sum(c["fraction"] for c in members)
        raw = [c["fraction"] / share * total for c in members]
        counts = [int(x) for x in raw]
        order = sorted(
            range(len(members)), key=lambda i: (counts[i] - raw[i], i),
        )
        for i in order[:total - sum(counts)]:
            counts[i] += 1
        for member, count in zip(members, counts):
            member["fraction"] = count / spec["num_agents"]
    return classes


def tier(
    hull: str, epochs: int, seeds: list[int], meta: dict[str, Any],
    block: dict[str, Any], changes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = HULLS[hull]
    effective = materialize(
        block, {CLASS_MIX_PATH: class_mix(hull), **(changes or {})},
    )
    label = " ".join(
        str(meta[k]) for k in ("arm", "stratum", "source_stratum") if k in meta
    )
    return {
        "platform": spec["platform"],
        "pathogen": "norovirus",
        "dose_adjustments": [DOSE],
        "surveillance_strategies": [SURVEILLANCE],
        "epoch_durations": [epochs],
        "num_agents": spec["num_agents"],
        "description": (
            f"Paper-1 WP2 joint evaluation: {spec['platform']}, {epochs} "
            f"epochs, {label}; baseline = freeze contract section 2 block, "
            f"plus the hull's declared {CLASS_MIX_PATH}."
        ),
        "config_overrides": effective,
        "seeds": seeds,
        "joint_eval": {
            "hull": spec["platform"], "epochs": epochs, **meta,
            "changed_paths": changed_paths(block, effective),
            "intended_roles": spec["intended_roles"],
            "template_roles": spec["template_roles"],
        },
    }


def load_selection() -> dict[str, Any] | None:
    if not SELECTION.is_file():
        return None
    return json.loads(SELECTION.read_text(encoding="utf-8"))


def stage_b_tiers(
    selection: dict[str, Any], block: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out = {}
    for hull in HULLS:
        picks = selection["hulls"][hull]
        for epochs in EPOCHS:
            for stratum in BRIDGE_STRATA:
                seeds = [int(s) for s in picks["diagnostic"][stratum]]
                out[f"fl_je_{hull}_{VOYAGE_DAYS[epochs]}d_{stratum}"] = tier(
                    hull, epochs, seeds,
                    {"arm": "bridge", "stratum": stratum}, block,
                )
        for source in PILOT_SOURCE_STRATA:
            sample = picks["evaluation"][source]
            out[f"fl_je_{hull}_{VOYAGE_DAYS[PILOT_EPOCHS]}d_eval_{source}"] = tier(
                hull, PILOT_EPOCHS, [int(s) for s in sample["seeds"]],
                {"arm": "pilot", "source_stratum": source,
                 "frame_n": sample["frame_n"],
                 "inclusion_probability": sample["inclusion_probability"],
                 "source_weight": sample["source_weight"]},
                block,
            )
    return out


def reproduction_tier(block: dict[str, Any]) -> dict[str, Any]:
    source = json.loads(
        (REPO_ROOT / REPRODUCTION["manifest"]).read_text(encoding="utf-8"),
    )
    spec = json.loads(json.dumps(source["tiers"][REPRODUCTION["tier"]]))
    seeds = json.loads(
        (REPO_ROOT / REPRODUCTION["seeds_from"]).read_text(encoding="utf-8"),
    )["blocks"][REPRODUCTION["block"]]["seeds"]
    spec["seeds"] = [int(s) for s in seeds]
    hull = HULLS[REPRODUCTION["hull"]]
    spec["joint_eval"] = {
        "arm": "reproduction",
        "hull": spec["platform"],
        "epochs": spec["epoch_durations"][0],
        "source": f"{REPRODUCTION['manifest']}#{REPRODUCTION['tier']}",
        "changed_paths": changed_paths(block, spec["config_overrides"]),
        "tier_axis_differences": sorted(
            k for k in spec
            if k in ("pathogen_overrides", "boarding_mechanism_rungs",
                     "boarding_prevalence_points",
                     "never_symptomatic_fractions", "sensitivity_profile")
        ),
        # A prior draw re-run verbatim: it keeps the class list it ran with,
        # so the template split is what it intends.
        "intended_roles": hull["template_roles"],
        "template_roles": hull["template_roles"],
        "reference_fingerprints": {},
    }
    return spec


def _burden(row: dict[str, Any]) -> float:
    return sum(
        float(o.get("lot_servings") or 0)
        * float(o.get("lot_titre_gec_per_g") or 0) * 150.0
        for o in row.get("objects") or []
        if o.get("source_kind") == "provisioned_lot"
    )


def _n_contaminated(row: dict[str, Any]) -> int:
    """Contaminated stations; the census keys the block by pathogen id."""
    source = row.get("provisioned_source") or {}
    if "n_contaminated" in source:
        return int(source["n_contaminated"] or 0)
    return sum(
        int((entry or {}).get("n_contaminated") or 0)
        for entry in source.values() if isinstance(entry, dict)
    )


def _hash_rank(seed: int) -> str:
    return hashlib.sha256(f"{NAME}:{seed}".encode()).hexdigest()


def select_hull(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply SELECTION_RULE to one hull's census rows."""
    rows = sorted(rows, key=lambda r: int(r["seed"]))
    dirty = [r for r in rows if _n_contaminated(r) > 0]
    dirty_seeds = {int(r["seed"]) for r in dirty}
    clean = [int(r["seed"]) for r in rows if int(r["seed"]) not in dirty_seeds]
    ranked = sorted(dirty, key=lambda r: (-_burden(r), int(r["seed"])))
    outbreak = [int(r["seed"]) for r in ranked[:BRIDGE_SEEDS]]
    rest = sorted(ranked[BRIDGE_SEEDS:], key=lambda r: (_burden(r), int(r["seed"])))
    frames = {"uncontaminated": clean, "contaminated": sorted(dirty_seeds)}
    evaluation = {}
    for source, frame in frames.items():
        sample = sorted(sorted(frame, key=_hash_rank)[:PILOT_SEEDS])
        evaluation[source] = {
            "seeds": sample,
            "frame_n": len(frame),
            "inclusion_probability": len(sample) / len(frame) if frame else None,
            "source_weight": len(frame) / len(rows) if rows else None,
        }
    return {
        "census_n": len(rows),
        "diagnostic": {
            "quiet": clean[:BRIDGE_SEEDS],
            "near": sorted(int(r["seed"]) for r in rest[:BRIDGE_SEEDS]),
            "outbreak": sorted(outbreak),
        },
        "evaluation": evaluation,
    }


def select(census_dir: Path) -> dict[str, Any]:
    hulls = {}
    for hull in HULLS:
        rows = [
            json.loads(line)
            for path in sorted(census_dir.glob(f"**/je_census_{hull}_chunk*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        errors = [r for r in rows if r.get("error")]
        frame = list(range(
            CENSUS_START[hull], CENSUS_START[hull] + CENSUS_SEEDS_PER_HULL,
        ))
        if errors or sorted(int(r["seed"]) for r in rows) != frame:
            raise SystemExit(
                f"{hull}: census is not the declared frame ({len(rows)} "
                f"rows, {len({int(r['seed']) for r in rows})} distinct "
                f"seeds, {len(errors)} errors); selection needs every "
                "frame seed exactly once",
            )
        hulls[hull] = select_hull(rows)
    return {"campaign": NAME, "rule": SELECTION_RULE, "hulls": hulls}


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    block = load_block()
    selection = load_selection()
    tiers: dict[str, dict[str, Any]] = {}
    blocks: dict[str, dict[str, Any]] = {}
    worker = f"{REL}/cell.py"
    for hull in HULLS:
        census_id = f"fl_je_census_{hull}"
        tiers[census_id] = tier(
            hull, 1, [CENSUS_START[hull]], {"arm": "census"}, block,
        )
        blocks[f"census_{hull}"] = {
            "worker": "tools/noro_diag/supply_seed_scan.py",
            "artifact": f"je_census_{hull}_chunk{{seed:06d}}.jsonl",
            "seeds": list(range(CENSUS_SEEDS_PER_HULL // CENSUS_CHUNK)),
            "args": {
                "tier": census_id, "arm": "station_lots", "hull": hull,
                "seed_start": CENSUS_START[hull],
                "seed_count": CENSUS_SEEDS_PER_HULL,
                "chunk_size": CENSUS_CHUNK, "epochs": 1, "num_agents": 100,
                "artifact_stem": f"je_census_{hull}",
            },
        }
    tiers[REPRODUCTION["id"]] = reproduction_tier(block)
    if selection is not None:
        tiers.update(stage_b_tiers(selection, block))
    for tier_id, spec in tiers.items():
        if spec["joint_eval"]["arm"] != "census":
            blocks[tier_id] = {
                "worker": worker, "tier": tier_id, "seeds": spec["seeds"],
            }
    manifest = {
        "campaign": NAME,
        "description": (
            "Paper-1 WP2 joint four-hull evaluation: a small complete "
            "bridge (4 hulls x {168,288,504} epochs x 3 diagnostic strata "
            "x 20 census-selected paired seeds), a joint-outcome pilot on "
            "independently sampled evaluation seeds, and a reproduction "
            f"arm. Design: {REL}/DESIGN.md."
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
            "baseline_block": block,
            "baseline_sha256": block_sha(block),
            "stage_b_emitted": selection is not None,
            "bridge_seeds_per_stratum": BRIDGE_SEEDS,
            "pilot_seeds_per_source_stratum": PILOT_SEEDS,
            "selection_rule": SELECTION_RULE,
            "technical_completion": TECHNICAL_COMPLETION,
            "diagnostic_bands": DIAGNOSTIC_BANDS,
            "continuation": CONTINUATION,
            "precision": PRECISION,
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
    parser.add_argument("--select", type=Path, default=None, metavar="DIR")
    args = parser.parse_args()
    if args.select is not None:
        SELECTION.write_text(render(select(args.select)), encoding="utf-8")
        print(f"wrote {SELECTION}")
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
