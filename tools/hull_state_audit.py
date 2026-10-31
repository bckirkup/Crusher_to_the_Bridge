#!/usr/bin/env python3
"""Declared-state hull audit — verify an operational state's signature.

Lockdown, collective protection, and HVAC casualty are DECLARED deviations
from normal airflow and occupancy, not baseline defects. A state spec
(``tools/hull_declared_states.json``) names each state's deviations through
generic selectors; the audit resolves them against each hull, applies the
edits to a copy of the hull's airflow/protocol config, reruns the drainage
fingerprint and/or occupancy smoke under the declared state, and verifies
the intended signature is present:

* ``hvac casualty`` — the declared AHU group loses its supply/return star
  (``hvac_duty: 0``, the shipped HD-sink pattern) and its rooms' retained
  mass rises vs the baseline drainage run;
* ``collective protection`` — citadel groups keep ducted supply while
  out-of-citadel supply groups starve and boundary-crossing ducts and
  hatches shut;
* ``lockdown`` — a schedule-forced confinement protocol holds agents on
  their home zones.

Per hull the verdict is ``verified`` (the intended signature measured),
``cannot_express`` (the state resolved to nothing — the hull lacks the
lever the state needs; that is a finding, not a defect of the audit), or
``no_signature`` (edits applied but the expected deviation absent — the
declaration did not reach the engine).

Usage:
    python3 tools/hull_state_audit.py [--platforms a,b] [--states s,t]
        [--epochs 24] [--seed 42] [--spec-file tools/hull_declared_states.json]
        [--json-out F] [--md-out F]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engines.py_contam_bridge import (  # noqa: E402
    PATH_TYPE_HVAC_SUPPLY,
    ContamTransportEngine,
    is_plenum_zone,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    load_validated_json,
    validated_open,
)
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402
from tools.hull_audit import (  # noqa: E402
    PlatformBundle,
    _zone_signature,
    load_platform,
)
from tools.hull_dynamics_audit import (  # noqa: E402
    _FILTER_EFFICIENCY,
    _crew_source,
    _manifest_agent_classes,
    _null_infection_spec,
)

_NO_ROOMS = "selector resolved no rooms"

PLATFORMS_DIR = REPO_ROOT / "data" / "platforms"
DEFAULT_STATE_SPEC = REPO_ROOT / "tools" / "hull_declared_states.json"
SHIPPED_PROTOCOLS = REPO_ROOT / "data" / "config" / "protocols.json"
_CROSS_ZONE = "cross_zone"
_ISOLATED_ZONE = "Isolated_In_Quarters"
_PLENUM_PREFIX = "_plenum_"
_RETENTION_TOL = 1e-6


# ------------------------------------------------------------ spec parsing

def load_state_spec(path: Path, *, allowed_roots: tuple = (str(REPO_ROOT),)
                    ) -> dict[str, Any]:
    with validated_open(str(path), "r",
                        allowed_roots=tuple(allowed_roots)) as fh:
        spec = json.load(fh)
    if not isinstance(spec.get("states"), dict) or not spec["states"]:
        raise ValueError(f"{path}: spec must define a non-empty 'states' object")
    return spec


def platform_state_overrides(spec: dict[str, Any], platform_id: str) -> dict[str, Any]:
    return dict((spec.get("platforms") or {}).get(platform_id) or {})


def merged_state(spec: dict[str, Any], platform_id: str,
                 state_id: str) -> dict[str, Any]:
    """State definition with the hull's per-platform overrides applied."""
    state = copy.deepcopy(spec["states"][state_id])
    for key, val in (platform_state_overrides(spec, platform_id)
                     .get(state_id) or {}).items():
        state[key] = val
    return state


def _zone_nodes(b: PlatformBundle) -> dict[str, dict[str, Any]]:
    nodes = (b.spatial or {}).get("zone_nodes") or (b.spatial or {}).get("zones")
    if isinstance(nodes, dict):
        return nodes
    return {str(z.get("id")): z for z in (nodes or [])}


def _hvac_groups(airflow: dict[str, Any]) -> list[dict[str, Any]]:
    return list(airflow.get("hvac_zones") or [])


def _group_rooms(group: dict[str, Any]) -> set[str]:
    return {str(r) for r in (group.get("rooms") or [])}


def _group_duty(group: dict[str, Any], default_duty: float) -> float:
    return float(group.get("hvac_duty", default_duty))


def _description_match(group: dict[str, Any], needles: list[str]) -> bool:
    desc = str(group.get("description") or "").lower()
    return any(str(n).lower() in desc for n in needles)


def _served_volume(b: PlatformBundle, group: dict[str, Any]) -> float:
    nodes = _zone_nodes(b)
    return sum(float(nodes.get(r, {}).get("volume_m3") or 0.0)
               for r in _group_rooms(group))


def select_groups(b: PlatformBundle, airflow: dict[str, Any],
                  sel: dict[str, Any],
                  inside_ids: set[str]) -> list[dict[str, Any]]:
    """Resolve a group selector (AND over keys; 'any' = OR of sub-selectors)."""
    if "any" in sel:
        seen: dict[str, dict[str, Any]] = {}
        for sub in sel["any"]:
            for g in select_groups(b, airflow, sub, inside_ids):
                seen[str(g.get("id"))] = g
        return list(seen.values())
    groups = _hvac_groups(airflow)
    default_duty = float(airflow.get("hvac_duty", 1.0))
    if sel.get("largest_supply_group"):
        supply = [g for g in groups if _group_duty(g, default_duty) > 0]
        if not supply:
            return []
        return [max(supply, key=lambda g: _served_volume(b, g))]
    if sel.get("inside_citadel"):
        groups = [g for g in groups if g.get("id") in inside_ids]
    if sel.get("outside_citadel"):
        groups = [g for g in groups if g.get("id") not in inside_ids]
    return [g for g in groups if _group_matches(g, sel, default_duty)]


def _group_matches(group: dict[str, Any], sel: dict[str, Any],
                   default_duty: float) -> bool:
    gid = str(group.get("id"))
    if "ids" in sel and gid not in sel["ids"]:
        return False
    if "exclude_ids" in sel and gid in sel["exclude_ids"]:
        return False
    if "with_field" in sel and sel["with_field"] not in group:
        return False
    if "without_field" in sel and sel["without_field"] in group:
        return False
    if sel.get("description_contains") and not _description_match(
            group, sel["description_contains"]):
        return False
    if sel.get("not_description_contains") and _description_match(
            group, sel["not_description_contains"]):
        return False
    if sel.get("supply_only") and _group_duty(group, default_duty) <= 0:
        return False
    return True


def _citadel_groups(b: PlatformBundle, state: dict[str, Any]
                    ) -> tuple[list[dict[str, Any]], str | None]:
    sel = state.get("citadel")
    if not sel:
        return [], "state declares no citadel selector"
    inside = select_groups(b, b.airflow, sel, set())
    if not inside:
        return [], ("citadel selector resolved no HVAC group — hull cannot "
                    "state a citadel boundary")
    return inside, None


def _state_needs_citadel(state: dict[str, Any]) -> bool:
    payload = json.dumps({k: v for k, v in state.items()
                          if k not in ("description",)})
    return "citadel" in payload or '"nbc"' in payload


# ------------------------------------------------------- airflow transform

def _config_inside(endpoint: Any, inside_ids: set[str],
                   inside_rooms: set[str]) -> bool:
    return endpoint in inside_ids or endpoint in inside_rooms


def _link_crosses(link: dict[str, Any], inside_ids: set[str],
                  inside_rooms: set[str]) -> bool:
    return (_config_inside(link.get("from"), inside_ids, inside_rooms)
            != _config_inside(link.get("to"), inside_ids, inside_rooms))


def _apply_duty_edits(b: PlatformBundle, air: dict[str, Any],
                      edits: list[dict[str, Any]], inside_ids: set[str],
                      out_edits: list[str],
                      unresolved: list[str]) -> None:
    for edit in edits or []:
        sel = edit.get("select") or {}
        targets = select_groups(b, air, sel, inside_ids)
        duty = float(edit["duty"])
        if not targets:
            unresolved.append(f"duty selector {sel} resolved no HVAC group")
            continue
        for g in targets:
            g["hvac_duty"] = duty
        names = sorted(str(g.get("id")) for g in targets)
        out_edits.append(f"hvac_duty={duty} on {len(targets)} group(s): "
                         + ", ".join(names))


def _drop_links(air: dict[str, Any], key: str, inside_ids: set[str],
                inside_rooms: set[str],
                out_edits: list[str]) -> None:
    links = list(air.get(key) or [])
    kept = [l for l in links
            if not _link_crosses(l, inside_ids, inside_rooms)]
    dropped = len(links) - len(kept)
    air[key] = kept
    if dropped:
        out_edits.append(f"dropped {dropped} boundary-crossing {key} link(s)")


def apply_airflow_state(b: PlatformBundle, block: dict[str, Any],
                        inside_groups: list[dict[str, Any]]
                        ) -> tuple[dict[str, Any], float, list[str],
                                   list[str], list[str]]:
    """Apply the state's airflow edits to a copy of the hull's airflow.

    Returns (airflow_after, filter_efficiency, edits, notes, unresolved).
    """
    air = copy.deepcopy(b.airflow)
    inside_ids = {str(g.get("id")) for g in inside_groups}
    inside_rooms: set[str] = set()
    for g in inside_groups:
        inside_rooms |= _group_rooms(g)
    edits: list[str] = []
    notes: list[str] = []
    unresolved: list[str] = []
    _apply_duty_edits(b, air, block.get("set_hvac_duty"), inside_ids,
                      edits, unresolved)
    for drop in block.get("drop_cross_zone_links") or []:
        if drop.get("crosses_citadel_boundary"):
            _drop_links(air, "cross_zone_links", inside_ids,
                        inside_rooms, edits)
    for drop in block.get("drop_adjacency") or []:
        if drop.get("crosses_citadel_boundary"):
            _drop_links(air, "adjacency", inside_ids, inside_rooms, edits)
    filt, note = _resolve_filter(block.get("filter_efficiency"),
                                 inside_groups)
    if note:
        notes.append(note)
    return air, filt, edits, notes, unresolved


def _resolve_filter(request: Any,
                    inside_groups: list[dict[str, Any]]) -> tuple[float, str | None]:
    if request is None:
        return _FILTER_EFFICIENCY, None
    if request == "nbc":
        grades = [float(g["nbc_filter_efficiency"]) for g in inside_groups
                  if "nbc_filter_efficiency" in g]
        if grades:
            return max(grades), None
        return _FILTER_EFFICIENCY, ("no declared nbc_filter_efficiency on "
                                    "citadel groups — filter kept at "
                                    "baseline 0.50")
    return float(request), None


# ------------------------------------------------------------ engine runs

def _drainage_mass(b: PlatformBundle, airflow: dict[str, Any],
                   filter_efficiency: float, epochs: int
                   ) -> tuple[ContamTransportEngine, dict[str, float]]:
    eng = ContamTransportEngine(
        b.spatial, airflow,
        filter_efficiency=filter_efficiency, natural_decay_rate=0.0,
    )
    zones = eng._real_zone_ids
    if not zones:
        raise ValueError(
            f"{b.platform_id}: no transport zones resolved — unknown platform?"
        )
    mass = dict.fromkeys(zones, 1.0)
    for _ in range(epochs):
        mass = eng.transport_step(mass, natural_decay_rate=0.0)
    return eng, mass


def _room_supply_in(eng: ContamTransportEngine) -> dict[str, dict[str, float]]:
    """Ducted inflow per room, split hvac_supply vs cross-zone."""
    out: dict[str, dict[str, float]] = {}
    for p in eng.airflow_paths:
        if p.path_type == PATH_TYPE_HVAC_SUPPLY:
            kind = "hvac_supply"
        elif p.path_type == _CROSS_ZONE:
            kind = _CROSS_ZONE
        else:
            continue
        row = out.setdefault(p.to_zone, {"hvac_supply": 0.0, _CROSS_ZONE: 0.0})
        row[kind] += p.flow_rate_m3h
    return out


def _inside_path_endpoint(zone_id: str, inside_ids: set[str],
                          inside_rooms: set[str]) -> bool:
    if is_plenum_zone(zone_id):
        return zone_id[len(_PLENUM_PREFIX):] in inside_ids
    return zone_id in inside_rooms


def _boundary_crossings(eng: ContamTransportEngine, inside_ids: set[str],
                        inside_rooms: set[str]) -> list[tuple[str, str, str]]:
    out = []
    for p in eng.airflow_paths:
        a = _inside_path_endpoint(p.from_zone, inside_ids, inside_rooms)
        z = _inside_path_endpoint(p.to_zone, inside_ids, inside_rooms)
        if a != z:
            out.append((p.from_zone, p.to_zone, p.path_type))
    return out


def _rooms_for(b: PlatformBundle, sel: dict[str, Any],
               inside_ids: set[str]) -> set[str]:
    rooms: set[str] = set()
    for g in select_groups(b, b.airflow, sel, inside_ids):
        rooms |= _group_rooms(g)
    return rooms


def _check_starved(rooms: set[str], flows: dict[str, dict[str, float]]
                   ) -> tuple[bool, str]:
    if not rooms:
        return False, _NO_ROOMS
    starved = [r for r in rooms
               if flows.get(r, {}).get("hvac_supply", 0.0) <= 0]
    residual = sorted(r for r in rooms
                      if flows.get(r, {}).get(_CROSS_ZONE, 0.0) > 0)
    detail = f"{len(starved)}/{len(rooms)} rooms have no hvac_supply"
    if residual:
        detail += f"; residual cross-zone inflow into {residual}"
    return len(starved) == len(rooms), detail


def _check_supplied(rooms: set[str], flows: dict[str, dict[str, float]]
                    ) -> tuple[bool, str]:
    if not rooms:
        return False, _NO_ROOMS
    fed = [r for r in rooms
           if flows.get(r, {}).get("hvac_supply", 0.0) > 0]
    return len(fed) == len(rooms), f"{len(fed)}/{len(rooms)} rooms supplied"


def _check_retention(rooms: set[str], mass_base: dict[str, float],
                     mass_state: dict[str, float]) -> tuple[bool, str]:
    """Starved rooms should pool mass — net retained mass rises.

    Individual rooms may fall: a room that was a net *recipient* of ducted
    mass loses that inflow when its star dies. Only the group's net pooling
    is the signature; per-room falls are reported as detail.
    """
    if not rooms:
        return False, _NO_ROOMS
    base_sum = sum(mass_base.get(r, 0.0) for r in rooms)
    state_sum = sum(mass_state.get(r, 0.0) for r in rooms)
    dropped = sorted(
        r for r in rooms
        if mass_state.get(r, 0.0) < mass_base.get(r, 0.0) - _RETENTION_TOL)
    detail = (f"net retained mass in {len(rooms)} room(s): "
              f"{base_sum:.3f} → {state_sum:.3f}")
    if dropped:
        detail += f"; fell in {dropped} (net-recipient redistribution)"
    return state_sum > base_sum + _RETENTION_TOL, detail


def check_airflow_expectations(b: PlatformBundle,
                               expect: dict[str, Any],
                               eng: ContamTransportEngine,
                               inside_ids: set[str],
                               inside_rooms: set[str],
                               mass_base: dict[str, float],
                               mass_state: dict[str, float]
                               ) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    flows = _room_supply_in(eng)
    for name, spec in expect.items():
        ok, detail = _airflow_check(name, spec, b, eng, flows,
                                    inside_ids, inside_rooms,
                                    mass_base, mass_state)
        if ok is not None:
            checks.append({"name": name, "pass": ok, "detail": detail})
    return checks


def _airflow_check(name: str, spec: Any, b: PlatformBundle,
                   eng: ContamTransportEngine,
                   flows: dict[str, dict[str, float]],
                   inside_ids: set[str], inside_rooms: set[str],
                   mass_base: dict[str, float],
                   mass_state: dict[str, float]):
    """One expectation -> (pass, detail); (None, ...) = not an airflow check."""
    if name == "starved_rooms":
        rooms = _rooms_for(b, spec.get("select") or {}, inside_ids)
        return _check_starved(rooms, flows)
    if name == "supplied_rooms":
        rooms = _rooms_for(b, spec.get("select") or {}, inside_ids)
        return _check_supplied(rooms, flows)
    if name == "no_boundary_paths" and spec:
        crossings = _boundary_crossings(eng, inside_ids, inside_rooms)
        return (not crossings,
                f"{len(crossings)} boundary-crossing path(s): "
                + ", ".join(f"{a}->{z}({t})" for a, z, t in crossings[:6]))
    if name == "elevated_retention_in":
        rooms = _rooms_for(b, spec.get("select") or {}, inside_ids)
        return _check_retention(rooms, mass_base, mass_state)
    return None, None


# ------------------------------------------------------------- occupancy

def _resolve_audit_protocol(proto: dict[str, Any],
                            b: PlatformBundle) -> dict[str, Any]:
    """Materialize a declared audit protocol: class selectors -> zone ids."""
    p = copy.deepcopy(proto)
    mods = p.setdefault("modifiers", {})
    classes = mods.pop("close_zone_class", None)
    if classes:
        wanted = {str(c) for c in classes}
        ids = {
            zid for zid, z in _zone_nodes(b).items()
            if _zone_signature(z) in wanted
        }
        mods["close_zones"] = sorted({*(mods.get("close_zones") or []), *ids})
    return p


def _materialize_protocols(state_occ: dict[str, Any], b: PlatformBundle,
                           state_id: str, workdir: Path) -> Path:
    shipped = load_validated_json(str(SHIPPED_PROTOCOLS),
                                  "protocols.schema.json",
                                  allowed_roots=(str(REPO_ROOT),))
    protos = list(shipped.get("protocols") or [])
    for raw in state_occ.get("audit_protocols") or []:
        protos.append(_resolve_audit_protocol(raw, b))
    out = workdir / f"protocols_{state_id}_{b.platform_id}.json"
    with validated_open(str(out), "w",
                        allowed_roots=(str(workdir),)) as fh:
        json.dump({"protocols": protos}, fh)
    return out


def _occupancy_spec(b: PlatformBundle, state_occ: dict[str, Any],
                    state_id: str, workdir: Path, *, epochs: int,
                    seed: int) -> dict[str, Any]:
    num_agents, _ = _crew_source(b)
    spec = _null_infection_spec(b.platform_id, epochs, num_agents, seed)
    classes = _manifest_agent_classes(b)
    if classes:
        spec["config_overrides"].setdefault("ship_graph", {})[
            "agent_classes"] = classes
    protos_path = _materialize_protocols(state_occ, b, state_id, workdir)
    spec.setdefault("catalog", {})["protocols_path"] = str(protos_path)
    sched = state_occ.get("scenario_schedule")
    if sched:
        spec["config_overrides"]["scenario_schedule"] = sched
    for key, val in (state_occ.get("config_overrides") or {}).items():
        spec["config_overrides"][key] = val
    return spec


def _state_census(spec: dict[str, Any]
                  ) -> tuple[list[Counter], list[int]]:
    """Run a no-pathogen voyage; return per-epoch counts + confined counts."""
    counts: list[Counter] = []
    confined: list[int] = []
    with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)

        def observer(sim_: Any, _work: Any) -> None:
            per_zone: Counter = Counter()
            held = 0
            for a in sim_.engine.agents:
                loc = getattr(a, "current_location", None) or "unknown"
                per_zone[loc] += 1
                home = getattr(a, "home_zone", None)
                if loc == _ISOLATED_ZONE or (home and loc == home):
                    held += 1
            counts.append(per_zone)
            confined.append(held)

        sim.epoch_observer = observer
        sim.run()
    return counts, confined


def _occ_metrics(counts: list[Counter], confined: list[int]) -> dict[str, float]:
    """Epoch 0 is excluded — schedule-forced protocols admit agents during it."""
    idx = range(1, len(counts)) or range(len(counts))
    shares = []
    mixing = []
    for i in idx:
        total = sum(counts[i].values())
        if total:
            shares.append(confined[i] / total)
        mixing.append(sum(1 for z, n in counts[i].items()
                          if n and z != _ISOLATED_ZONE))
    return {
        "confined_share": sum(shares) / len(shares) if shares else 0.0,
        "mixing_zones": sum(mixing) / len(mixing) if mixing else 0.0,
        "epochs_measured": len(mixing),
    }


def check_occupancy_expectations(expect: dict[str, Any],
                                 base: dict[str, float],
                                 state: dict[str, float]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if "min_confined_share" in expect:
        ok = state["confined_share"] >= float(expect["min_confined_share"])
        checks.append({
            "name": "min_confined_share", "pass": ok,
            "detail": (f"confined share {state['confined_share']:.3f} vs "
                       f"declared minimum {expect['min_confined_share']}"),
        })
    if "max_mixing_reduction" in expect:
        reduction = 1.0 - state["mixing_zones"] / max(base["mixing_zones"], 1e-9)
        ok = reduction >= float(expect["max_mixing_reduction"])
        checks.append({
            "name": "max_mixing_reduction", "pass": ok,
            "detail": (f"occupied-zone reduction {reduction:.3f} vs declared "
                       f"minimum {expect['max_mixing_reduction']} "
                       f"(baseline {base['mixing_zones']:.1f} → state "
                       f"{state['mixing_zones']:.1f} zones/epoch)"),
        })
    return checks


# ----------------------------------------------------------------- driver

def _expressibility(b: PlatformBundle, state: dict[str, Any]
                    ) -> list[str]:
    blockers: list[str] = []
    if state.get("occupancy"):
        num_agents, _ = _crew_source(b)
        if num_agents <= 0:
            blockers.append("no crew source — nothing to confine")
    if _state_needs_citadel(state):
        _, err = _citadel_groups(b, state)
        if err:
            blockers.append(err)
    return blockers


def _run_airflow_state(b: PlatformBundle, state: dict[str, Any],
                       inside_groups: list[dict[str, Any]], *,
                       epochs: int, cache: dict[str, Any]) -> None:
    block = state["airflow"]
    air_after, filt, edits, notes, unresolved = apply_airflow_state(
        b, block, inside_groups)
    state.setdefault("notes", []).extend(notes)
    state.setdefault("_edits", []).extend(edits)
    if unresolved:
        state.setdefault("blockers", []).extend(unresolved)
        return
    if "base_mass" not in cache:
        eng_b, cache["base_mass"] = _drainage_mass(
            b, b.airflow, _FILTER_EFFICIENCY, epochs)
        cache["base_engine"] = eng_b
    eng_state, mass_state = _drainage_mass(b, air_after, filt, epochs)
    inside_ids = {str(g.get("id")) for g in inside_groups}
    inside_rooms: set[str] = set()
    for g in inside_groups:
        inside_rooms |= _group_rooms(g)
    checks = check_airflow_expectations(
        b, state.get("expect") or {}, eng_state,
        inside_ids, inside_rooms, cache["base_mass"], mass_state)
    state.setdefault("_checks", []).extend(checks)
    zones = len(eng_state._real_zone_ids)
    state["drainage"] = {
        "filter_efficiency": filt,
        "baseline_retained_frac": round(
            sum(cache["base_mass"].values()) / max(zones, 1), 4),
        "state_retained_frac": round(
            sum(mass_state.values()) / max(zones, 1), 4),
    }


def _run_occupancy_state(b: PlatformBundle, state: dict[str, Any],
                         state_id: str, workdir: Path, *, epochs: int,
                         seed: int, cache: dict[str, Any]) -> None:
    spec = _occupancy_spec(b, state["occupancy"], state_id, workdir,
                           epochs=epochs, seed=seed)
    counts, confined = _state_census(spec)
    metrics = _occ_metrics(counts, confined)
    if "base_occ" not in cache:
        base_spec = _null_infection_spec(
            b.platform_id, epochs, _crew_source(b)[0], seed)
        classes = _manifest_agent_classes(b)
        if classes:
            base_spec["config_overrides"].setdefault("ship_graph", {})[
                "agent_classes"] = classes
        b_counts, b_confined = _state_census(base_spec)
        cache["base_occ"] = _occ_metrics(b_counts, b_confined)
    base = cache["base_occ"]
    checks = check_occupancy_expectations(state.get("expect") or {},
                                          base, metrics)
    state.setdefault("_checks", []).extend(checks)
    state["occupancy_result"] = {
        "confined_share": round(metrics["confined_share"], 4),
        "baseline_confined_share": round(base["confined_share"], 4),
        "mixing_zones": round(metrics["mixing_zones"], 2),
        "baseline_mixing_zones": round(base["mixing_zones"], 2),
        "agent_classes": "manifest" if _manifest_agent_classes(b)
                          else "default",
    }


def run_platform(b: PlatformBundle, spec: dict[str, Any],
                 state_ids: list[str], *, epochs: int, seed: int,
                 workdir: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"platform": b.platform_id, "states": {}}
    cache: dict[str, Any] = {}
    for sid in state_ids:
        state = merged_state(spec, b.platform_id, sid)
        result: dict[str, Any] = {
            "verdict": "verified",
            "blockers": _expressibility(b, state),
            "notes": [],
        }
        if result["blockers"]:
            result["verdict"] = "cannot_express"
        else:
            inside_groups, _ = _citadel_groups(b, state) if (
                _state_needs_citadel(state)) else ([], None)
            if state.get("airflow"):
                _run_airflow_state(b, state, inside_groups,
                                   epochs=epochs, cache=cache)
                result["edits"] = state.get("_edits", [])
                result["drainage"] = state.get("drainage")
                result["notes"].extend(state.get("notes", []))
                result["blockers"].extend(state.get("blockers", []))
            if state.get("occupancy") and not result["blockers"]:
                _run_occupancy_state(b, state, sid, workdir,
                                     epochs=epochs, seed=seed, cache=cache)
                result["occupancy"] = state["occupancy_result"]
            result["checks"] = state.get("_checks", [])
            if result["blockers"]:
                result["verdict"] = "cannot_express"
            elif any(not c["pass"] for c in result["checks"]):
                result["verdict"] = "no_signature"
            else:
                result["verdict"] = "verified"
        row["states"][sid] = result
    return row


# --------------------------------------------------------------- rendering

_VERDICT_ORDER = ("verified", "cannot_express", "no_signature")


def render_markdown(rows: list[dict[str, Any]], spec: dict[str, Any],
                    *, epochs: int, seed: int) -> str:
    lines = [
        "# Declared-state hull audit",
        "",
        f"{len(rows)} hull(s) × {len(rows[0]['states']) if rows else 0} "
        f"state(s), {epochs} epochs per run, seed {seed}.",
        "",
        "Verdicts: `verified` = the declared signature was measured; "
        "`cannot_express` = the hull lacks the lever the state needs (a "
        "finding on the hull, not the state); `no_signature` = edits "
        "applied but the expected deviation absent (declaration does not "
        "reach the engine).",
        "",
    ]
    for sid, state in spec["states"].items():
        lines += _render_state_section(sid, state, rows)
    return "\n".join(lines) + "\n"


def _render_state_section(sid: str, state: dict[str, Any],
                          rows: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {sid}", ""]
    if state.get("description"):
        lines += [str(state["description"]), ""]
    lines += ["| platform | verdict | checks | detail |",
              "|---|---|---|---|"]
    tallies = dict.fromkeys(_VERDICT_ORDER, 0)
    for row in rows:
        r = row["states"].get(sid)
        if r is None:
            continue
        tallies[r["verdict"]] += 1
        lines.append(_state_row(row["platform"], r))
    lines += ["",
              "Verdicts: " + "; ".join(f"{k} = {tallies[k]}"
                                       for k in _VERDICT_ORDER),
              ""]
    for row in rows:
        r = row["states"].get(sid)
        if r and r["verdict"] != "verified":
            lines += _failure_detail(row["platform"], r)
    return lines


def _state_row(platform: str, r: dict[str, Any]) -> str:
    checks = r.get("checks") or []
    passed = sum(1 for c in checks if c["pass"])
    check_cell = f"{passed}/{len(checks)}" if checks else "—"
    detail = "; ".join(r.get("blockers") or []) or _key_metrics(r)
    return f"| {platform} | {r['verdict']} | {check_cell} | {detail} |"


def _key_metrics(r: dict[str, Any]) -> str:
    bits = []
    if r.get("drainage"):
        d = r["drainage"]
        bits.append(f"retained {d['baseline_retained_frac']}→"
                    f"{d['state_retained_frac']} (filt {d['filter_efficiency']})")
    if r.get("occupancy"):
        o = r["occupancy"]
        bits.append(f"confined {o['baseline_confined_share']}→"
                    f"{o['confined_share']}; mixing "
                    f"{o['baseline_mixing_zones']}→{o['mixing_zones']} zones")
    return "; ".join(bits)


def _failure_detail(platform: str, r: dict[str, Any]) -> list[str]:
    lines = [f"### {platform} — {r['verdict']}", ""]
    for blocker in r.get("blockers") or []:
        lines.append(f"- blocker: {blocker}")
    for note in r.get("notes") or []:
        lines.append(f"- note: {note}")
    for c in r.get("checks") or []:
        mark = "pass" if c["pass"] else "FAIL"
        lines.append(f"- [{mark}] {c['name']}: {c['detail']}")
    lines.append("")
    return lines


# ------------------------------------------------------------------- main

def _write(path_str: str, text: str) -> None:
    out = Path(path_str)
    out.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(str(out), "w",
                        allowed_roots=(str(out.parent.resolve()),),
                        encoding="utf-8") as fh:
        fh.write(text)


def _platform_dirs(arg: str | None) -> list[Path]:
    if arg:
        return [PLATFORMS_DIR / p.strip() for p in arg.split(",")]
    return sorted(p for p in PLATFORMS_DIR.iterdir()
                  if (p / "spatial_layout.json").is_file()
                  and (p / "air_flow_paths.json").is_file())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platforms", default=None,
                    help="comma list; default = all dirs under data/platforms/")
    ap.add_argument("--states", default=None,
                    help="comma list of state ids; default = all in spec")
    ap.add_argument("--spec-file", default=str(DEFAULT_STATE_SPEC))
    ap.add_argument("--epochs", type=int, default=24)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    args = ap.parse_args(argv)

    spec = load_state_spec(Path(args.spec_file))
    state_ids = ([s.strip() for s in args.states.split(",")]
                 if args.states else list(spec["states"]))
    unknown = [s for s in state_ids if s not in spec["states"]]
    if unknown:
        raise ValueError(f"unknown state ids: {unknown}")

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as workdir_str:
        workdir = Path(workdir_str)
        for d in _platform_dirs(args.platforms):
            try:
                b = load_platform(d)
                row = run_platform(b, spec, state_ids, epochs=args.epochs,
                                   seed=args.seed, workdir=workdir)
            except Exception as exc:  # fleet sweep: log and continue
                row = {"platform": d.name, "states": {},
                       "error": f"{type(exc).__name__}: {exc}"}
            rows.append(row)
            if row.get("error"):
                print(f"{d.name}: ERROR {row['error']}",
                      file=sys.stderr, flush=True)
                continue
            summary = "; ".join(
                f"{sid}:{r['verdict']}" for sid, r in row["states"].items())
            print(f"{d.name}: {summary}", file=sys.stderr, flush=True)

    md = render_markdown(rows, spec, epochs=args.epochs, seed=args.seed)
    if args.md_out:
        _write(args.md_out, md)
    else:
        print(md)
    if args.json_out:
        _write(args.json_out,
               json.dumps({"rows": rows}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
