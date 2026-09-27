#!/usr/bin/env python3
"""Fold growth-chain census payloads into the NORO-GROWTH-01 link table.

Reads ``growth_census.json.gz`` payloads written by
``growth_chain_census.py``, restricts to ignited voyages (an emesis emit
record from an import host), and produces the link-by-link census the
ledger needs:

* L1 -- secondary shedding: emit/deposit record of challenge-acquired
  hosts vs the emitting imports, normalised per infected epoch and per
  symptomatic epoch.
* L2 -- deposit landing: deposited mass by source class and unit class,
  and where that mass went (pickup consume vs cleaning/decay/removal).
* L3 -- pickup into susceptible hands: delivered mass by channel and
  source class, co-presence census (unit-epochs holding acquired-sourced
  mass with susceptibles present), and pickup-gate closures.
* L4 -- conversion: dose-response hazard summed over challenges whose
  delivered mass carried acquired-sourced share (the naive expected
  tertiary count) vs observed acquisitions.
* L5 -- the named link: the first link whose acquired-side throughput is
  exactly zero or orders below the import side's, with the by-design vs
  defect classification evidence.

Usage::

    python3 tools/noro_diag/growth_chain_readout.py \
        --runs-dir canary_growth --tier fl_spr_12d
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.transmission_core import TransmissionCore  # noqa: E402

_is_cabin = TransmissionCore._is_cabin_compartment

GEN_IMPORT = "import"
GEN_ACQUIRED = "acquired"
GEN_UNKNOWN = "unknown"

# Source-share threshold: a pickup/dose/hazard counts as acquired-sourced
# when at least half the mass it drew from was deposited by an acquired
# host. Below that the acquisition would have happened anyway.
ACQUIRED_SHARE_MIN = 0.5


def _load_payloads(runs_dir: Path, tier: str) -> list[dict[str, Any]]:
    """Read every growth_census payload under ``<runs_dir>/<tier>/*.zip``."""
    import zipfile

    payloads: list[dict[str, Any]] = []
    for zip_path in sorted(Path(runs_dir).rglob(f"{tier}/*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            payload = json.loads(
                gzip.decompress(archive.read("growth_census.json.gz")),
            )
        payloads.append(payload)
    return payloads


def _unit_class(classes: dict[str, str], unit: str) -> str:
    if unit and _is_cabin(unit):
        return "cabin_fittings"
    if classes.get(unit) == "Sanitary":
        return "shared_head"
    return "other_zone"


def _emitting_imports(payload: dict[str, Any]) -> set[int]:
    """Gen-0 hosts that filed an emesis patch.

    The emit-row census only records emits that append a deposition
    record; a parallel emit path files the patch (``emesis_patch_gec``)
    silently. Patch depositor ids and the host's own patch total both
    mark an emitting import.
    """
    emitting: set[int] = set()
    for row in payload["hosts"]:
        if row["gen"] == 0 and (
            row["emesis_emitted"] > 0 or row["emesis_patch_gec"] > 0
        ):
            emitting.add(row["agent_id"])
    dep_gens = {row["agent_id"]: row["gen"] for row in payload["hosts"]}
    for row in payload.get("patch_pickups", []):
        if dep_gens.get(row.get("depositor"), -1) == 0:
            emitting.add(row["depositor"])
    return emitting


def _host_groups(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    emitting = _emitting_imports(payload)
    acquired_ids = {
        row["agent_id"] for row in payload.get("acquisitions", [])
    }
    groups: dict[str, list[dict[str, Any]]] = {
        "index": [], "import": [], "acquired": [], "unresolved": [],
    }
    for row in payload["hosts"]:
        aid = row["agent_id"]
        if aid in emitting:
            groups["index"].append(row)
        elif aid in acquired_ids:
            groups["acquired"].append(row)
        elif row["gen"] == 0:
            groups["import"].append(row)
        elif row["infected_epochs"] > 0:
            groups["unresolved"].append(row)
    return groups


def _mean(rows: list[float]) -> float:
    return sum(rows) / len(rows) if rows else 0.0


def _shedding_link(payload: dict[str, Any]) -> dict[str, Any]:
    """L1: emit/deposit record of acquired hosts vs the index imports."""
    groups = _host_groups(payload)
    out: dict[str, Any] = {}
    for name, rows in groups.items():
        infected = [r for r in rows if r["infected_epochs"] > 0]
        sym_epochs = sum(r["symptomatic_epochs"] for r in infected)
        inf_epochs = sum(r["infected_epochs"] for r in infected)
        out[name] = {
            "n": len(infected),
            "sym_epochs": sym_epochs,
            "emesis_scheduled": sum(r["emesis_scheduled"] for r in infected),
            "emesis_emitted": sum(r["emesis_emitted"] for r in infected),
            "emesis_patch_gec": sum(r["emesis_patch_gec"] for r in infected),
            "shedding_gec": sum(r["shedding_gec"] for r in infected),
            "shedding_per_inf_epoch": (
                sum(r["shedding_gec"] for r in infected) / inf_epochs
                if inf_epochs else 0.0
            ),
            "deposit_gec": sum(r["deposit_gec"] for r in infected),
            "deposit_per_sym_epoch": (
                sum(r["deposit_gec"] for r in infected) / sym_epochs
                if sym_epochs else 0.0
            ),
            "stool_events": sum(r["stool_events"] for r in infected),
            "confined_epochs": sum(r["confined_epochs"] for r in infected),
            "hand_peak_max": max(
                (r["hand_peak_gec"] for r in infected), default=0.0,
            ),
        }
    return out


def _landing_link(payload: dict[str, Any]) -> dict[str, Any]:
    """L2: deposited mass by source class x unit class, plus removals."""
    classes = payload["meta"]["zone_classes"]
    by_dest: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    for row in payload["deposits"]:
        by_dest[_unit_class(classes, row.get("unit") or "")][
            row["gen_class"]
        ] += row["mass"]
    removals = {
        cause: dict(by_gen) for cause, by_gen in
        payload["removal_totals"].items()
    }
    return {
        "deposited_by_unit_class": {
            unit: dict(by_gen) for unit, by_gen in by_dest.items()
        },
        "removals": removals,
        "patch_delivered_acquired_gec": sum(
            row["delivered"] for row in payload["patch_pickups"]
            if row.get("depositor_gen", -1) > 0
        ),
        "patch_delivered_import_gec": sum(
            row["delivered"] for row in payload["patch_pickups"]
            if row.get("depositor_gen", -1) == 0
        ),
        "patch_pickup_calls": len(payload["patch_pickups"]),
        "patch_rows": payload["patch_pickups"],
        "patch_sweeps": _patch_sweep_summary(payload),
    }


def _patch_sweep_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Per-depositor-class sweep census: patches present, susceptibles
    present -- the 'mass sat with nobody to touch it' half of L3."""
    out: dict[str, dict[str, float]] = {
        GEN_IMPORT: defaultdict(float),
        GEN_ACQUIRED: defaultdict(float),
    }
    for row in payload.get("patch_sweeps", []):
        for dep_class in set(row["depositor_gens"]):
            if dep_class not in out:
                continue
            slot = out[dep_class]
            slot["sweep_epochs"] += 1
            slot["mass_gec"] += row["patch_mass_gec"]
            slot["occupants"] += row["occupants"]
            slot["susceptible"] += row["susceptible"]
            if row["susceptible"] == 0:
                slot["zero_susceptible_epochs"] += 1
                slot["zero_susceptible_mass_gec"] += row["patch_mass_gec"]
    return {cls: dict(slot) for cls, slot in out.items()}


def _pickup_link(payload: dict[str, Any]) -> dict[str, Any]:
    """L3: delivered mass to susceptible hands by channel and source."""
    by_channel: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    counts: dict[str, int] = defaultdict(int)
    acquired_pickups = 0
    for row in payload["pickups"]:
        channel = row["channel"]
        counts[channel] += 1
        by_channel[channel]["delivered"] += row["delivered"]
        by_channel[channel]["dose"] += row["dose"]
        by_channel[channel]["delivered_acquired"] += (
            row["delivered"] * row["source_acquired_share"]
        )
        if row["source_acquired_share"] >= ACQUIRED_SHARE_MIN:
            acquired_pickups += 1
    co_presence = {
        "unit_epochs_with_acquired_mass": 0,
        "unit_epochs_acquired_mass_and_susceptible": 0,
        "susceptibles_present": 0,
    }
    for row in payload["unit_epochs"]:
        if row.get("mass_acquired", 0.0) > 0.0:
            co_presence["unit_epochs_with_acquired_mass"] += 1
            if row["susceptible"] > 0:
                co_presence[
                    "unit_epochs_acquired_mass_and_susceptible"
                ] += 1
                co_presence["susceptibles_present"] += row["susceptible"]
    closed_by_caller: dict[str, int] = defaultdict(int)
    closed_mass = 0.0
    for row in payload["gate_closed"]:
        closed_by_caller[row["caller"]] += 1
        closed_mass += row["mass"]
    return {
        "pickup_counts": dict(counts),
        "delivered_by_channel": {
            channel: dict(totals) for channel, totals in by_channel.items()
        },
        "acquired_sourced_pickups": acquired_pickups,
        "co_presence": co_presence,
        "gate_closed_by_caller": dict(closed_by_caller),
        "gate_closed_mass_gec": closed_mass,
        "gate_open_by_caller": payload.get("gate_open_by_caller", {}),
    }


def _target_acquired_share(
    payload: dict[str, Any],
) -> dict[tuple[int, int], float]:
    """(epoch, target) -> acquired-sourced fraction of delivered mass."""
    share: dict[tuple[int, int], float] = {}
    totals: dict[tuple[int, int], float] = {}
    for row in payload["pickups"]:
        key = (row["epoch"], row["target"])
        share[key] = (
            share.get(key, 0.0)
            + row["delivered"] * row["source_acquired_share"]
        )
        totals[key] = totals.get(key, 0.0) + row["delivered"]
    return {
        key: (share[key] / totals[key] if totals[key] > 0 else 0.0)
        for key in totals
    }


def _conversion_link(payload: dict[str, Any]) -> dict[str, Any]:
    """L4: expected tertiaries (naive hazard sum) vs observed."""
    src_share = _target_acquired_share(payload)
    hazard_acquired = 0.0
    hazard_total = 0.0
    for row in payload["hazards"]:
        hazard_total += row["hazard"]
        if row["target_gen"] != -1:
            continue  # already-infected hosts re-challenged
        key = (row["epoch"], row["agent_id"])
        if src_share.get(key, 0.0) >= ACQUIRED_SHARE_MIN:
            hazard_acquired += row["hazard"]
    acquisitions = payload["acquisitions"]
    from_acquired = [
        row for row in acquisitions
        if row.get("delivered_src_acquired_gec", 0.0)
        > row.get("delivered_src_import_gec", 0.0)
    ]
    return {
        "hazard_total": hazard_total,
        "hazard_acquired_sourced": hazard_acquired,
        "n_acquisitions": len(acquisitions),
        "n_acquired_sourced": len(from_acquired),
        "acquisitions": acquisitions,
    }


def _named_link(run: dict[str, Any]) -> dict[str, Any]:
    """L5: first link whose acquired throughput is ~zero."""
    l1, l2, l3, l4 = run["l1"], run["l2"], run["l3"], run["l4"]
    acquired = l1["acquired"]
    named = "none (chain intact end-to-end)"
    if acquired["n"] == 0:
        named = "L0: no secondaries at all (ignition produced none)"
    elif acquired["shedding_gec"] <= 0.0 and acquired["deposit_gec"] <= 0.0:
        named = "L1: secondaries never shed (shedding+deposit both zero)"
    elif sum(
        v.get(GEN_ACQUIRED, 0.0)
        for v in l2["deposited_by_unit_class"].values()
    ) <= 0.0:
        named = "L2: acquired-sourced mass never lands in pools"
    elif l3["acquired_sourced_pickups"] == 0:
        named = "L3: no susceptible picked up acquired-sourced mass"
    elif l4["hazard_acquired_sourced"] <= 0.0:
        named = "L4: acquired-sourced doses never reached a challenge"
    elif l4["n_acquired_sourced"] == 0:
        named = "L4: challenge drew on acquired mass but converted none"
    return {
        "named": named,
        "hazard_witness_expected_tertiaries": l4[
            "hazard_acquired_sourced"
        ],
        "observed_acquired_sourced": l4["n_acquired_sourced"],
    }


def summarise_run(payload: dict[str, Any]) -> dict[str, Any]:
    run = {
        "run_id": payload.get("run_id"),
        "seed": payload["meta"]["seed"],
        "l1": _shedding_link(payload),
        "l2": _landing_link(payload),
        "l3": _pickup_link(payload),
        "l4": _conversion_link(payload),
    }
    run["l5"] = _named_link(run)
    return run


def _fmt(x: float, sig: int = 3) -> str:
    if x == 0:
        return "0"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:.{sig}g}"


_L1_KEYS = (
    "n", "sym_epochs", "emesis_scheduled", "emesis_emitted",
    "emesis_patch_gec", "shedding_gec", "deposit_gec", "stool_events",
    "confined_epochs",
)

_L4_KEYS = (
    "hazard_total", "hazard_acquired_sourced", "n_acquisitions",
    "n_acquired_sourced",
)


def _pooled_l1(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        cls: {
            key: sum(r["l1"][cls][key] for r in runs) for key in _L1_KEYS
        }
        for cls in ("index", "import", "acquired", "unresolved")
    }


def _merge_nested(slot_map: dict, source: dict) -> None:
    """Sum ``source[key][inner]`` into ``slot_map[key][inner]``."""
    for key, inner in source.items():
        slot = slot_map.setdefault(key, defaultdict(float))
        for inner_key, val in inner.items():
            slot[inner_key] += val


def _merge_flat(slot: dict, source: dict) -> None:
    for key, val in source.items():
        slot[key] += val


def _accumulate_run(pooled: dict[str, Any], run: dict[str, Any]) -> None:
    l2 = run["l2"]
    _merge_nested(
        pooled["l2_deposited_by_unit_class"], l2["deposited_by_unit_class"],
    )
    _merge_nested(pooled["l2_removals"], l2["removals"])
    _merge_nested(pooled["l2_patch_sweeps"], l2["patch_sweeps"])
    pooled["l2_patch_delivered"]["import"] += l2[
        "patch_delivered_import_gec"
    ]
    pooled["l2_patch_delivered"]["acquired"] += l2[
        "patch_delivered_acquired_gec"
    ]
    l3 = pooled["l3"]
    _merge_flat(l3["pickup_counts"], run["l3"]["pickup_counts"])
    _merge_nested(
        l3["delivered_by_channel"], run["l3"]["delivered_by_channel"],
    )
    l3["acquired_sourced_pickups"] += run["l3"][
        "acquired_sourced_pickups"
    ]
    _merge_flat(l3["co_presence"], run["l3"]["co_presence"])
    _merge_flat(
        l3["gate_closed_by_caller"], run["l3"]["gate_closed_by_caller"],
    )
    l3["gate_closed_mass_gec"] += run["l3"]["gate_closed_mass_gec"]
    _merge_flat(
        l3["gate_open_by_caller"], run["l3"]["gate_open_by_caller"],
    )
    for key in _L4_KEYS:
        pooled["l4"][key] += run["l4"][key]


def _freeze_defaultdicts(pooled: dict[str, Any]) -> None:
    for key in (
        "l2_deposited_by_unit_class", "l2_removals", "l2_patch_sweeps",
    ):
        pooled[key] = {k: dict(v) for k, v in pooled[key].items()}
    pooled["l3"] = {
        key: (dict(val) if isinstance(val, defaultdict) else val)
        for key, val in pooled["l3"].items()
    }
    pooled["l3"]["delivered_by_channel"] = {
        ch: dict(totals)
        for ch, totals in pooled["l3"]["delivered_by_channel"].items()
    }


def readout(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    runs = [
        summarise_run(p) for p in payloads if _emitting_imports(p)
    ]
    pooled = {
        "n_runs": len(payloads),
        "n_ignited": len(runs),
        "n_skipped_cold": len(payloads) - len(runs),
        "l1": _pooled_l1(runs),
        "l2_deposited_by_unit_class": {},
        "l2_removals": {},
        "l2_patch_sweeps": {},
        "l2_patch_delivered": {"import": 0.0, "acquired": 0.0},
        "l3": {
            "pickup_counts": defaultdict(int),
            "delivered_by_channel": defaultdict(lambda: defaultdict(float)),
            "acquired_sourced_pickups": 0,
            "co_presence": defaultdict(int),
            "gate_closed_by_caller": defaultdict(int),
            "gate_closed_mass_gec": 0.0,
            "gate_open_by_caller": defaultdict(int),
        },
        "l4": {
            "hazard_total": 0.0,
            "hazard_acquired_sourced": 0.0,
            "n_acquisitions": 0,
            "n_acquired_sourced": 0,
        },
        "named_links": [r["l5"]["named"] for r in runs],
    }
    for run in runs:
        _accumulate_run(pooled, run)
    _freeze_defaultdicts(pooled)
    return {"runs": runs, "pooled": pooled}


def _markdown(pooled: dict[str, Any]) -> str:
    lines = [
        f"ignited voyages: {pooled['n_ignited']}/{pooled['n_runs']}",
        "",
        "### L1 shedding census (pooled)",
        *(
            ["| class | n | sym epochs | sched | emitted | patch GEC |"
             " shed GEC | deposit GEC | stool | confined |",
             "|---|---|---|---|---|---|---|---|---|"]
            + [
                f"| {cls} | {v['n']} | {v['sym_epochs']} |"
                f" {v['emesis_scheduled']} | {v['emesis_emitted']} |"
                f" {_fmt(v['emesis_patch_gec'])} |"
                f" {_fmt(v['shedding_gec'])} | {_fmt(v['deposit_gec'])} |"
                f" {v['stool_events']} | {v['confined_epochs']} |"
                for cls, v in pooled["l1"].items()
            ]
        ),
        "",
        "### L2 deposited mass by unit class (GEC)",
        *[
            f"| {unit} | import {_fmt(v.get('import', 0.0))} |"
            f" acquired {_fmt(v.get('acquired', 0.0))} |"
            f" unknown {_fmt(v.get('unknown', 0.0))} |"
            for unit, v in pooled["l2_deposited_by_unit_class"].items()
        ],
        "",
        "### L2 removals by cause (GEC)",
        *[
            f"| {cause} | import {_fmt(v.get('import', 0.0))} |"
            f" acquired {_fmt(v.get('acquired', 0.0))} |"
            f" unknown {_fmt(v.get('unknown', 0.0))} |"
            for cause, v in pooled["l2_removals"].items()
        ],
        "",
        "### L2 patch sweeps (per depositor class)",
        *[
            f"| {cls} | sweeps {v.get('sweep_epochs', 0):.0f} |"
            f" mass {_fmt(v.get('mass_gec', 0.0))} |"
            f" susceptibles {v.get('susceptible', 0):.0f} |"
            f" zero-susceptible sweeps "
            f"{v.get('zero_susceptible_epochs', 0):.0f} |"
            f" mass unseen {_fmt(v.get('zero_susceptible_mass_gec', 0.0))} |"
            for cls, v in pooled["l2_patch_sweeps"].items()
        ],
        f"- patch delivered: import "
        f"{_fmt(pooled['l2_patch_delivered']['import'])} GEC,"
        f" acquired {_fmt(pooled['l2_patch_delivered']['acquired'])} GEC",
        "",
        "### L3 pickups",
        f"- pickup counts: {pooled['l3']['pickup_counts']}",
        f"- acquired-sourced pickups: "
        f"{pooled['l3']['acquired_sourced_pickups']}",
        f"- co-presence: {pooled['l3']['co_presence']}",
        f"- gate closed: {pooled['l3']['gate_closed_by_caller']} "
        f"(mass {_fmt(pooled['l3']['gate_closed_mass_gec'])} GEC)",
        f"- gate open: {pooled['l3']['gate_open_by_caller']}",
        "",
        "### L4 conversion",
        f"- hazard total: {_fmt(pooled['l4']['hazard_total'])}",
        f"- hazard on acquired-sourced doses: "
        f"{_fmt(pooled['l4']['hazard_acquired_sourced'])}",
        f"- acquisitions: {pooled['l4']['n_acquisitions']}, "
        f"of which acquired-sourced: {pooled['l4']['n_acquired_sourced']}",
        "",
        "### Named link per run",
        *[
            f"- seed {run['seed']}: {run['l5']['named']}"
            for run in pooled.get("runs", [])
        ],
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    payloads = _load_payloads(args.runs_dir, args.tier)
    result = readout(payloads)
    result["pooled"]["runs"] = result["runs"]
    print(_markdown(result["pooled"]))
    if args.json_out:
        args.json_out.write_text(  # NOSONAR -- operator-specified report path in a local diagnostic tool
            json.dumps(result, indent=1),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
