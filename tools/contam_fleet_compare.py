#!/usr/bin/env python3
"""
contam_fleet_compare.py – fleet-wide native vs ContamX solver comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs the arm/scenario matrix in ``data/config/contam_compare/fleet_arms.json``
over every platform in ``data/platforms/`` (or a subset), comparing the
native :class:`ContamTransportEngine` against the real NIST ContamX solver
on both **speed** (field-solve + trajectory wall-clock) and **results**
(per-epoch concentration divergence, retained fraction, per-zone dose
integrals).

Two ContamX lanes are measured:

- ``contamx_committed`` — baseline only; the platform's committed authentic
  ``contam/platform.prj`` solved as-is (skipped when no PRJ is committed).
- ``contamx_export`` — every arm; the (possibly mutated) airflow JSON is
  re-exported to a commissioned PRJ and solved, so a knob arm reaches the
  solver in the same shape the native engine sees.

Engine-level arms (``set_oa`` / ``set_filter``) reuse the baseline exported
flow field: ``oa_fraction`` and ``filter_efficiency`` are applied by the
Crusher-side ContamX bridge and propagator, so re-solving would be
wasted work. ``set_oa`` still mutates the JSON copy the *native* engine
reads (its per-zone ``oa_fraction`` keys) so both engines see the knob.

Per arm the report records, besides raw divergence, the **knob-response
parity**: whether the two solvers agree on the direction and magnitude of
the arm's effect relative to its own baseline (per-zone dose deltas and
retained-fraction deltas) — the operational question "if the ship moves
this knob, do the models agree what happens".

ContamX is optional: without a binary the suite reports native-only
metrics (exit 0) so CI and offline operators can run it.

Usage::

    python3 tools/contam_fleet_compare.py                    # whole fleet
    python3 tools/contam_fleet_compare.py --platforms destroyer_baseline
    python3 tools/contam_fleet_compare.py --platforms all --repeats 1 \
        --arms baseline ahu_casualty --scenarios respiratory
    python3 tools/contam_fleet_compare.py --md-out docs/contam_fleet_table.md
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.contamw34_prj import path_map_from_prj  # noqa: E402

_DEFAULT_SPEC = "data/config/contam_compare/fleet_arms.json"
_SPATIAL = "spatial_layout.json"
_AIRFLOW = "air_flow_paths.json"
_FIELD_OPS = frozenset({"set_duty", "scale_ach", "drop_links"})
_EPS = 1e-9
_MAX_EPOCHS = 5000


# ── spec / platform loading ──────────────────────────────────────────────

def _load_json(path: str) -> dict[str, Any]:
    full = resolve_repo_path(REPO_ROOT, path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _platform_ids(selected: list[str] | None) -> list[str]:
    base = os.path.join(REPO_ROOT, "data", "platforms")
    if selected and selected != ["all"]:
        return [validate_path_component(p, label="platform id") for p in selected]
    ids = [
        d for d in sorted(os.listdir(base))
        if os.path.isfile(os.path.join(base, d, _SPATIAL))
        and os.path.isfile(os.path.join(base, d, _AIRFLOW))
    ]
    return ids


def _load_platform(platform_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = os.path.join("data", "platforms", platform_id)
    return _load_json(os.path.join(base, _SPATIAL)), _load_json(
        os.path.join(base, _AIRFLOW)
    )


def _committed_prj_path(platform_id: str) -> str:
    return os.path.join(
        "data", "platforms", platform_id, "contam", "platform.prj"
    )


# ── arm mutations ─────────────────────────────────────────────────────────

def _largest_supply_group(airflow: dict[str, Any],
                          volume: dict[str, float]) -> dict[str, Any] | None:
    """Supply group (duty>0) serving the largest summed room volume."""
    default_duty = float(airflow.get("hvac_duty", 1.0))
    supply = [
        g for g in airflow.get("hvac_zones", [])
        if float(g.get("hvac_duty", default_duty)) > 0.0
    ]
    if not supply:
        return None
    return max(
        supply,
        key=lambda g: sum(volume.get(r, 0.0) for r in g.get("rooms", [])),
    )


def _op_set_oa(
    air: dict[str, Any], op: dict[str, Any],
    engine_args: dict[str, Any], edits: list[str],
    volume: dict[str, float],
) -> None:
    val = float(op["value"])
    air["oa_fraction"] = val
    for g in air.get("hvac_zones", []):
        g["oa_fraction"] = val
    engine_args["oa_fraction"] = val
    edits.append(f"oa_fraction={val} on all groups")


def _op_set_duty(
    air: dict[str, Any], op: dict[str, Any],
    engine_args: dict[str, Any], edits: list[str],
    volume: dict[str, float],
) -> None:
    val = float(op["value"])
    targets = _duty_targets(air, op, volume)
    for g in targets:
        g["hvac_duty"] = val
    if op.get("select") != "largest_supply_group":
        air["hvac_duty"] = val
    edits.append(
        f"hvac_duty={val} on {len(targets)} group(s): "
        + ", ".join(sorted(str(g.get("id")) for g in targets))
    )


def _op_scale_ach(
    air: dict[str, Any], op: dict[str, Any],
    engine_args: dict[str, Any], edits: list[str],
    volume: dict[str, float],
) -> None:
    factor = float(op["factor"])
    for g in air.get("hvac_zones", []):
        g["ach"] = float(g.get("ach", 0.0)) * factor
    edits.append(f"ach x{factor} on all groups")


def _op_drop_links(
    air: dict[str, Any], op: dict[str, Any],
    engine_args: dict[str, Any], edits: list[str],
    volume: dict[str, float],
) -> None:
    key = str(op["key"])
    dropped = len(air.get(key) or [])
    air[key] = []
    edits.append(f"dropped {dropped} {key}")


def _op_set_filter(
    air: dict[str, Any], op: dict[str, Any],
    engine_args: dict[str, Any], edits: list[str],
    volume: dict[str, float],
) -> None:
    engine_args["filter_efficiency"] = float(op["value"])
    edits.append(f"filter_efficiency={op['value']}")


_OP_HANDLERS = {
    "set_oa": _op_set_oa,
    "set_duty": _op_set_duty,
    "scale_ach": _op_scale_ach,
    "drop_links": _op_drop_links,
    "set_filter": _op_set_filter,
}


def _apply_arm_ops(
    airflow: dict[str, Any], ops: list[dict[str, Any]],
    volume: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply arm ops to a copy of *airflow*; returns (airflow, engine_args)."""
    air = copy.deepcopy(airflow)
    engine_args: dict[str, Any] = {}
    edits: list[str] = []
    for op in ops:
        name = str(op.get("op"))
        handler = _OP_HANDLERS.get(name)
        if handler is None:
            raise ValueError(f"unknown arm op {name!r}")
        handler(air, op, engine_args, edits, volume)
    return air, {"engine_args": engine_args, "edits": edits}


def _duty_targets(
    air: dict[str, Any], op: dict[str, Any], volume: dict[str, float],
) -> list[dict[str, Any]]:
    if op.get("select") == "largest_supply_group":
        group = _largest_supply_group(air, volume)
        return [group] if group is not None else []
    return list(air.get("hvac_zones", []))


def _arm_needs_field(arm: dict[str, Any]) -> bool:
    return any(str(o.get("op")) in _FIELD_OPS for o in arm.get("ops", []))


# ── injection site ────────────────────────────────────────────────────────

def _injection_zone(spatial: dict[str, Any],
                    airflow: dict[str, Any]) -> str:
    """Largest-volume real zone served by an HVAC group; fallback largest."""
    zones = {z["id"]: z for z in spatial.get("zones", [])}
    volume = {zid: float(z.get("volume_m3", 0.0)) for zid, z in zones.items()}
    served = {
        r for g in airflow.get("hvac_zones", [])
        for r in g.get("rooms", []) if r in zones
    }
    pool = served or set(zones)
    if not pool:
        raise ValueError("platform has no zones")
    return max(pool, key=lambda zid: volume.get(zid, 0.0))


# ── engine construction + trajectories ───────────────────────────────────

def _native_engine(
    spatial: dict[str, Any], airflow: dict[str, Any], *,
    decay: float, filt: float,
) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=filt,
        natural_decay_rate=decay,
    )


def _solve_prj(prj_text: str, entries: list[dict[str, Any]],
               tmp_dir: str, binary: str) -> dict[int, float]:
    """Write *prj_text* + path map into *tmp_dir*, solve, return flows."""
    prj_path = os.path.join(tmp_dir, "platform.prj")
    map_path = os.path.join(tmp_dir, "path_map.json")
    with validated_open(prj_path, "w", allowed_roots=(REPO_ROOT, tmp_dir),
                        encoding="utf-8") as fh:
        fh.write(prj_text)
    with validated_open(map_path, "w", allowed_roots=(REPO_ROOT, tmp_dir),
                        encoding="utf-8") as fh:
        json.dump(entries, fh)
    sim_path = run_contamx(
        prj_path, binary, allowed_roots=(REPO_ROOT, tmp_dir),
    )
    return SimResults(sim_path, allowed_roots=(REPO_ROOT, tmp_dir)) \
        .path_volumetric_flow_m3h()


def _contamx_field(
    spatial: dict[str, Any], airflow: dict[str, Any], *,
    tmp_dir: str, binary: str, prj_rel: str | None,
) -> dict[str, Any]:
    """Solved field (entries + flows) from a committed or exported PRJ."""
    if prj_rel is not None:
        full = resolve_repo_path(REPO_ROOT, prj_rel)
        with validated_open(full, "r", allowed_roots=(REPO_ROOT,),
                            encoding="utf-8") as fh:
            prj_text = fh.read()
        # Committed GA prjs mangle zone names to the CONTAMW 15-char field;
        # normalize endpoints to JSON ids or the committed lane drops them.
        overrides = load_hobbyist_overrides(
            os.path.dirname(os.path.dirname(full))
        )
        entries = path_map_from_prj(
            prj_text,
            [z["id"] for z in spatial.get("zones", [])],
            declared_aliases=overrides.get("zone_aliases"),
        )
    else:
        prj_text, entries = export_prj_with_path_map(
            spatial, airflow, ahs_terminal_mode="commissioned",
        )
    flows = _solve_prj(prj_text, entries, tmp_dir, binary)
    return {"entries": entries, "flows": flows}


def _contamx_engine(
    spatial: dict[str, Any], field: dict[str, Any], *,
    oa: float, filt: float, decay: float,
) -> ContamXTransportEngine:
    return ContamXTransportEngine(
        spatial_layout=spatial,
        path_map=field["entries"],
        path_flows_m3h=field["flows"],
        filter_efficiency=filt,
        natural_decay_rate=decay,
        path_map_entries=field["entries"],
        oa_fraction=oa,
    )


def _run_trajectory(
    engine: ContamTransportEngine, initial_mass: dict[str, float],
    epochs: int,
) -> tuple[list[dict[str, float]], dict[str, float]]:
    mass = dict(initial_mass)
    traj: list[dict[str, float]] = []
    for _ in range(min(max(int(epochs), 0), _MAX_EPOCHS)):
        mass = engine.transport_step(mass)
        traj.append({
            zid: (engine.zone_nodes[zid].concentration(m)
                  if zid in engine.zone_nodes else 0.0)
            for zid, m in mass.items()
        })
    return traj, mass


# ── metrics ───────────────────────────────────────────────────────────────

def _divergence(
    native: list[dict[str, float]], contamx: list[dict[str, float]],
) -> dict[str, Any]:
    per_epoch: list[dict[str, float]] = []
    for n_frame, x_frame in zip(native, contamx, strict=True):
        zones = set(n_frame) | set(x_frame)
        diffs = [abs(n_frame.get(z, 0.0) - x_frame.get(z, 0.0)) for z in zones]
        per_epoch.append({
            "l1": sum(diffs),
            "linf": max(diffs) if diffs else 0.0,
        })
    return {
        "final_l1": per_epoch[-1]["l1"] if per_epoch else 0.0,
        "final_linf": per_epoch[-1]["linf"] if per_epoch else 0.0,
        "mean_l1": statistics.fmean(e["l1"] for e in per_epoch)
        if per_epoch else 0.0,
    }


def _dose_per_zone(traj: list[dict[str, float]]) -> dict[str, float]:
    dose: dict[str, float] = {}
    for frame in traj:
        for zid, conc in frame.items():
            dose[zid] = dose.get(zid, 0.0) + conc
    return dose


def _timing(samples: list[float]) -> dict[str, float]:
    return {
        "repeats": len(samples),
        "seconds_mean": statistics.fmean(samples),
        "seconds_min": min(samples),
        "seconds_max": max(samples),
        "seconds_stdev": (
            statistics.pstdev(samples) if len(samples) > 1 else 0.0
        ),
    }


def _response_parity(
    native_dose: dict[str, float], native_base: dict[str, float],
    cx_dose: dict[str, float], cx_base: dict[str, float],
) -> dict[str, Any]:
    """Do the solvers agree on the arm-vs-baseline effect direction/size?"""
    zones = set(native_dose) | set(cx_dose) | set(native_base) | set(cx_base)
    agree = both_moved = moved_any = 0
    ratios: list[float] = []
    for zid in zones:
        base_n = native_base.get(zid, 0.0)
        base_x = cx_base.get(zid, 0.0)
        d_n = native_dose.get(zid, 0.0) - base_n
        d_x = cx_dose.get(zid, 0.0) - base_x
        eps_n = max(1e-3 * abs(base_n), _EPS)
        eps_x = max(1e-3 * abs(base_x), _EPS)
        m_n, m_x = abs(d_n) > eps_n, abs(d_x) > eps_x
        moved_any += int(m_n or m_x)
        if m_n and m_x:
            both_moved += 1
            agree += int((d_n > 0) == (d_x > 0))
            if abs(d_n) > _EPS:
                ratios.append(abs(d_x) / abs(d_n))
    return {
        "zones_moved_native": sum(
            abs(native_dose.get(z, 0.0) - native_base.get(z, 0.0))
            > max(1e-3 * abs(native_base.get(z, 0.0)), _EPS) for z in zones
        ),
        "zones_moved_contamx": sum(
            abs(cx_dose.get(z, 0.0) - cx_base.get(z, 0.0))
            > max(1e-3 * abs(cx_base.get(z, 0.0)), _EPS) for z in zones
        ),
        "zones_moved_either": moved_any,
        "zones_moved_both": both_moved,
        "sign_agreement_frac": (agree / both_moved) if both_moved else None,
        "magnitude_ratio_median": (
            statistics.median(ratios) if ratios else None
        ),
    }


def _engine_params(
    arm_meta: dict[str, Any], scen: dict[str, Any],
    baseline_filt: float, baseline_oa: float,
) -> dict[str, float]:
    """Merge scenario decay with arm engine-level overrides."""
    engine_args = arm_meta.get("engine_args") or {}
    return {
        "decay": float(scen.get("natural_decay_rate", 0.0)),
        "filt": float(engine_args.get("filter_efficiency", baseline_filt)),
        "oa": float(engine_args.get("oa_fraction", baseline_oa)),
    }


# ── per-cell runs ─────────────────────────────────────────────────────────

def _timed_traj(
    build_fn, initial_mass: dict[str, float], epochs: int, repeats: int,
) -> dict[str, Any]:
    """Time engine build + trajectory separately, over *repeats*."""
    solve_samples: list[float] = []
    traj_samples: list[float] = []
    traj: list[dict[str, float]] = []
    mass: dict[str, float] = {}
    engine: ContamTransportEngine | None = None
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        engine = build_fn()
        solve_samples.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        traj, mass = _run_trajectory(engine, initial_mass, epochs)
        traj_samples.append(time.perf_counter() - t0)
    assert engine is not None
    return {
        "build_seconds": _timing(solve_samples),
        "trajectory_seconds": _timing(traj_samples),
        "traj": traj,
        "final_mass": mass,
        "n_paths": len(engine.airflow_paths),
    }


def _timed_field(
    spatial: dict[str, Any], airflow: dict[str, Any], *,
    tmp_dir: str, binary: str, prj_rel: str | None, repeats: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Solve a ContamX field *repeats* times; return (field, timing)."""
    samples: list[float] = []
    field: dict[str, Any] | None = None
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        field = _contamx_field(
            spatial, airflow,
            tmp_dir=tempfile.mkdtemp(dir=tmp_dir),
            binary=binary, prj_rel=prj_rel,
        )
        samples.append(time.perf_counter() - t0)
    assert field is not None
    return field, _timing(samples)


def _cell_summary(
    run: dict[str, Any], traj: list[dict[str, float]],
    final_mass: dict[str, float], injected: float,
) -> dict[str, Any]:
    retained = (sum(final_mass.values()) / injected) if injected else 0.0
    return {
        "build_seconds": run["build_seconds"],
        "trajectory_seconds": run["trajectory_seconds"],
        "n_paths": run["n_paths"],
        "retained_fraction": retained,
        "dose_per_zone": _dose_per_zone(traj),
    }


def _run_cell(
    spatial: dict[str, Any], air: dict[str, Any], *,
    params: dict[str, float], initial_mass: dict[str, float],
    epochs: int, repeats: int, cx_field: dict[str, Any] | None,
    binary: str | None,
) -> dict[str, Any]:
    """One scenario on one arm: native cell + (optional) ContamX cell."""
    injected = sum(initial_mass.values())
    native_run = _timed_traj(
        lambda: _native_engine(
            spatial, air, decay=params["decay"], filt=params["filt"],
        ),
        initial_mass, epochs, repeats,
    )
    native_traj = native_run.pop("traj")
    native_mass = native_run.pop("final_mass")
    out: dict[str, Any] = {
        "native": _cell_summary(native_run, native_traj, native_mass,
                                injected),
    }
    if binary is not None and cx_field is not None:
        cx_run = _timed_traj(
            lambda: _contamx_engine(
                spatial, cx_field, oa=params["oa"],
                filt=params["filt"], decay=params["decay"],
            ),
            initial_mass, epochs, repeats,
        )
        cx_traj = cx_run.pop("traj")
        cx_mass = cx_run.pop("final_mass")
        out["contamx"] = _cell_summary(cx_run, cx_traj, cx_mass, injected)
        out["divergence"] = _divergence(native_traj, cx_traj)
    return out


# ── per-platform run ──────────────────────────────────────────────────────

def run_platform(
    platform_id: str, spec: dict[str, Any], *,
    arms: list[str], scenarios: list[str], repeats: int, epochs: int,
    binary: str | None, tmp_root: str,
) -> dict[str, Any]:
    spatial, airflow = _load_platform(platform_id)
    volume = {
        z["id"]: float(z.get("volume_m3", 0.0))
        for z in spatial.get("zones", [])
    }
    inject_zone = _injection_zone(spatial, airflow)
    inject_mass = float(spec.get("inject_mass", 1.0e6))
    initial_mass = {
        z["id"]: (inject_mass if z["id"] == inject_zone else 0.0)
        for z in spatial.get("zones", [])
    }
    baseline_filt = float(spec.get("baseline_filter_efficiency", 0.5))
    baseline_oa = float(airflow.get("oa_fraction", 0.2))
    prj_rel = _committed_prj_path(platform_id)
    has_prj = os.path.isfile(resolve_repo_path(REPO_ROOT, prj_rel))
    tmp_dir = tempfile.mkdtemp(dir=tmp_root)

    report: dict[str, Any] = {
        "platform": platform_id,
        "n_zones": len(spatial.get("zones", [])),
        "n_hvac_groups": len(airflow.get("hvac_zones", [])),
        "has_committed_prj": has_prj,
        "injection_zone": inject_zone,
        "inject_mass": inject_mass,
        "arms": {},
        "errors": [],
    }
    base_doses: dict[str, dict[str, Any]] = {}
    ordered = (["baseline"] if "baseline" in arms else []) + [
        a for a in arms if a != "baseline"
    ]
    for arm_id in ordered:
        arm = spec["arms"][arm_id]
        _apply = _apply_arm_ops(airflow, arm.get("ops", []), volume)
        air_mut, arm_meta = _apply[0], _apply[1]
        needs_field = _arm_needs_field(arm)
        ctx = _ArmCtx(
            spatial=spatial, air_mut=air_mut, spec=spec,
            initial_mass=initial_mass, epochs=epochs, repeats=repeats,
            tmp_dir=tmp_dir, binary=binary, scenarios=scenarios,
            base_doses=base_doses, baseline_filt=baseline_filt,
            baseline_oa=baseline_oa,
        )
        report["arms"][arm_id] = _run_arm(
            ctx, arm_id, arm_meta, needs_field=needs_field,
            prj_rel=prj_rel if has_prj else None,
        )
    return report


@dataclasses.dataclass(frozen=True)
class _ArmCtx:
    """Shared per-platform per-arm run context."""

    spatial: dict[str, Any]
    air_mut: dict[str, Any]
    spec: dict[str, Any]
    initial_mass: dict[str, float]
    epochs: int
    repeats: int
    tmp_dir: str
    binary: str | None
    scenarios: list[str]
    base_doses: dict[str, dict[str, Any]]
    baseline_filt: float
    baseline_oa: float


def _solve_arm_field(
    ctx: _ArmCtx, arm_id: str, needs_field: bool,
    errors: list[Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve the arm's ContamX field; records solve errors, never raises."""
    try:
        return _resolve_arm_field(
            ctx.spatial, ctx.air_mut, arm_id=arm_id,
            needs_field=needs_field, tmp_dir=ctx.tmp_dir,
            binary=ctx.binary, repeats=ctx.repeats,
            base_doses=ctx.base_doses,
        )
    except (ContamXUnavailable, ValueError, OSError) as exc:
        errors.append(f"ContamX field solve failed: {exc}")
        return None, None


def _solve_committed_field(
    ctx: _ArmCtx, prj_rel: str, errors: list[Any],
) -> dict[str, Any] | None:
    """Baseline-arm committed-.prj solve + timing into the arm report."""
    try:
        committed, timing = _timed_field(
            ctx.spatial, ctx.air_mut, tmp_dir=ctx.tmp_dir,
            binary=ctx.binary, prj_rel=prj_rel, repeats=ctx.repeats,
        )
    except (ContamXUnavailable, ValueError, OSError) as exc:
        errors.append(f"committed prj solve failed: {exc}")
        return None
    ctx.base_doses["committed_field"] = committed
    return {"committed_field_seconds": timing}


def _attach_committed_cell(
    ctx: _ArmCtx, cell: dict[str, Any], params: dict[str, float],
) -> None:
    committed = ctx.base_doses.get("committed_field")
    if committed is None:
        return
    cell["contamx_committed"] = _committed_cell(
        ctx.spatial, committed, params=params,
        initial_mass=ctx.initial_mass, epochs=ctx.epochs,
        repeats=ctx.repeats,
    )
    cell["divergence_committed"] = _divergence_pair(
        cell, "contamx_committed",
    )


def _run_arm_scenario(
    ctx: _ArmCtx, arm_id: str, arm_meta: dict[str, Any],
    scen_id: str, cx_field: dict[str, Any] | None,
    errors: list[Any],
) -> dict[str, Any] | None:
    scen = ctx.spec["scenarios"][scen_id]
    params = _engine_params(
        arm_meta, scen, ctx.baseline_filt, ctx.baseline_oa,
    )
    try:
        cell = _run_cell(
            ctx.spatial, ctx.air_mut, params=params,
            initial_mass=ctx.initial_mass, epochs=ctx.epochs,
            repeats=ctx.repeats, cx_field=cx_field, binary=ctx.binary,
        )
    except (ContamXUnavailable, ValueError, OSError) as exc:
        errors.append({"cell": scen_id, "error": str(exc)})
        return None
    if arm_id == "baseline" and ctx.binary is not None:
        _attach_committed_cell(ctx, cell, params)
    _record_baseline(cell, arm_id, scen_id, ctx.base_doses)
    if arm_id != "baseline":
        cell["response_parity"] = _arm_response(
            cell, ctx.base_doses, scen_id,
        )
    return cell


def _run_arm(
    ctx: _ArmCtx, arm_id: str, arm_meta: dict[str, Any], *,
    needs_field: bool, prj_rel: str | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"edits": arm_meta["edits"], "cells": {}}
    errors = out.setdefault("errors", [])
    cx_field = field_timing = None
    if ctx.binary is not None:
        cx_field, field_timing = _solve_arm_field(
            ctx, arm_id, needs_field, errors,
        )
        if cx_field is None:
            errors.append("ContamX field unavailable for this arm")
    if arm_id == "baseline" and prj_rel is not None and ctx.binary:
        committed_meta = _solve_committed_field(ctx, prj_rel, errors)
        if committed_meta is not None:
            out.update(committed_meta)
    for scen_id in ctx.scenarios:
        cell = _run_arm_scenario(
            ctx, arm_id, arm_meta, scen_id, cx_field, errors,
        )
        if cell is not None:
            out["cells"][scen_id] = cell
    if field_timing is not None:
        out["field_seconds"] = field_timing
    return out


def _resolve_arm_field(
    spatial: dict[str, Any], air_mut: dict[str, Any], *,
    arm_id: str, needs_field: bool, tmp_dir: str, binary: str,
    repeats: int, base_doses: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Arm's ContamX field: fresh solve for field ops, baseline reuse else."""
    if not needs_field:
        cached = base_doses.get("baseline_field")
        if cached is not None:
            return cached, {"reused": "baseline"}
    field, timing = _timed_field(
        spatial, air_mut, tmp_dir=tmp_dir, binary=binary,
        prj_rel=None, repeats=repeats,
    )
    if arm_id == "baseline":
        base_doses["baseline_field"] = field
    return field, timing


def _committed_cell(
    spatial: dict[str, Any], committed: dict[str, Any], *,
    params: dict[str, float], initial_mass: dict[str, float],
    epochs: int, repeats: int,
) -> dict[str, Any]:
    run = _timed_traj(
        lambda: _contamx_engine(
            spatial, committed, oa=params["oa"],
            filt=params["filt"], decay=params["decay"],
        ),
        initial_mass, epochs, repeats,
    )
    traj = run.pop("traj")
    mass = run.pop("final_mass")
    return _cell_summary(run, traj, mass, sum(initial_mass.values()))


def _divergence_pair(
    cell: dict[str, Any], lane: str,
) -> dict[str, Any] | None:
    native = cell["native"]["dose_per_zone"]
    cx = cell[lane]["dose_per_zone"]
    zones = set(native) | set(cx)
    diffs = [abs(native.get(z, 0.0) - cx.get(z, 0.0)) for z in zones]
    return {
        "dose_l1": sum(diffs),
        "dose_linf": max(diffs) if diffs else 0.0,
    }


def _record_baseline(
    cell: dict[str, Any], arm_id: str, scen_id: str,
    base_doses: dict[str, dict[str, Any]],
) -> None:
    if arm_id != "baseline":
        return
    entry = base_doses.setdefault(scen_id, {})
    entry["native_dose"] = cell["native"]["dose_per_zone"]
    entry["native_retained"] = cell["native"]["retained_fraction"]
    if "contamx" in cell:
        entry["contamx_dose"] = cell["contamx"]["dose_per_zone"]
        entry["contamx_retained"] = cell["contamx"]["retained_fraction"]


def _arm_response(
    cell: dict[str, Any], base_doses: dict[str, dict[str, Any]],
    scen_id: str,
) -> dict[str, Any] | None:
    base = base_doses.get(scen_id) or {}
    if "native_dose" not in base:
        return None
    parity = _response_parity(
        cell["native"]["dose_per_zone"], base["native_dose"],
        cell.get("contamx", {}).get("dose_per_zone", {}),
        base.get("contamx_dose", {}),
    )
    parity["retained_delta_native"] = (
        cell["native"]["retained_fraction"] - base["native_retained"]
    )
    if "contamx" in cell and "contamx_retained" in base:
        parity["retained_delta_contamx"] = (
            cell["contamx"]["retained_fraction"] - base["contamx_retained"]
        )
    return parity


# ── fleet driver + report ─────────────────────────────────────────────────

def _print_platform_summary(report: dict[str, Any]) -> None:
    pid = report["platform"]
    n_z, n_g = report["n_zones"], report["n_hvac_groups"]
    base = (report["arms"].get("baseline") or {}).get("cells", {})
    base = base.get("respiratory") or next(iter(base.values()), {})
    nat = base.get("native") or {}
    cx = base.get("contamx") or {}
    print(f"\n=== {pid} (zones={n_z} ahs={n_g} "
          f"prj={'yes' if report['has_committed_prj'] else 'no'}) ===")
    print(
        f"  native  build {nat.get('build_seconds', {}).get('seconds_mean', float('nan')):.3f}s "
        f"traj {nat.get('trajectory_seconds', {}).get('seconds_mean', float('nan')):.3f}s | "
        f"contamx build {cx.get('build_seconds', {}).get('seconds_mean', float('nan')):.3f}s "
        f"traj {cx.get('trajectory_seconds', {}).get('seconds_mean', float('nan')):.3f}s"
    )
    div = base.get("divergence")
    if div:
        print(f"  baseline divergence: mean L1={div['mean_l1']:.4g} "
              f"final L1={div['final_l1']:.4g} "
              f"retained n/x={nat.get('retained_fraction', 0.0):.3f}/"
              f"{cx.get('retained_fraction', 0.0):.3f}")
    for arm_id, arm in report["arms"].items():
        for err in arm.get("errors", []):
            print(f"  ERROR {arm_id}: {err}")


def _write_outputs(
    reports: list[dict[str, Any]], spec: dict[str, Any], *,
    out_dir: str, md_out: str, binary: str | None,
) -> str:
    prepare_output_directory(out_dir, allowed_roots=(REPO_ROOT,))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contamx_binary": binary,
        "spec": spec.get("description"),
        "platforms": reports,
    }
    path = os.path.join(out_dir, f"fleet_compare_{stamp}.json")
    with validated_open(path, "w", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=1)
    latest = os.path.join(out_dir, "fleet_compare_latest.json")
    with validated_open(latest, "w", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=1)
    if md_out:
        _write_markdown(reports, md_out, binary)
    return path


def _write_markdown(
    reports: list[dict[str, Any]],
    md_out: str, binary: str | None,
) -> None:
    lines = [
        "# Fleet native vs ContamX comparison — generated table",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}  ",
        f"ContamX binary: `{binary or 'unavailable'}`  ",
        f"Spec: `{_DEFAULT_SPEC}`",
        "",
        "| platform | zones | AHS | prj | native build s | native traj s | "
        "contamx field s | contamx traj s | mean L1 | retained n/x |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        cells = (r["arms"].get("baseline") or {}).get("cells", {})
        base = cells.get("respiratory") or next(iter(cells.values()), {})
        nat = base.get("native") or {}
        cx = base.get("contamx") or {}
        div = base.get("divergence") or {}
        field_t = (r["arms"].get("baseline") or {}).get("field_seconds") or {}
        lines.append(
            f"| {r['platform']} | {r['n_zones']} | {r['n_hvac_groups']} | "
            f"{'yes' if r['has_committed_prj'] else 'no'} | "
            f"{(nat.get('build_seconds') or {}).get('seconds_mean', float('nan')):.3f} | "
            f"{(nat.get('trajectory_seconds') or {}).get('seconds_mean', float('nan')):.3f} | "
            f"{field_t.get('seconds_mean', float('nan')):.3f} | "
            f"{(cx.get('trajectory_seconds') or {}).get('seconds_mean', float('nan')):.3f} | "
            f"{div.get('mean_l1', float('nan')):.4g} | "
            f"{nat.get('retained_fraction', float('nan')):.3f}/"
            f"{cx.get('retained_fraction', float('nan')):.3f} |"
        )
    lines.append("")
    full = resolve_repo_path(REPO_ROOT, md_out)
    prepare_output_directory(
        os.path.dirname(full) or REPO_ROOT, allowed_roots=(REPO_ROOT,),
    )
    with validated_open(full, "w", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _attach_ids(spec: dict[str, Any]) -> dict[str, Any]:
    for arm_id, arm in spec.get("arms", {}).items():
        arm["arm_id"] = arm_id
    return spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fleet native vs ContamX solver comparison.",
    )
    parser.add_argument(
        "--spec", default=_DEFAULT_SPEC,
        help="Arm/scenario spec JSON (default fleet_arms.json).",
    )
    parser.add_argument(
        "--platforms", nargs="+", default=None,
        help="Platform ids or 'all' (default: every data/platforms/*).",
    )
    parser.add_argument("--arms", nargs="+", default=None,
                        help="Subset of spec arms (default all).")
    parser.add_argument("--scenarios", nargs="+", default=None,
                        help="Subset of spec scenarios (default all).")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument(
        "--out", default="telemetry_buffer/contam_fleet_compare",
        help="Report output directory (gitignored).",
    )
    parser.add_argument("--md-out", default="",
                        help="Optional repo-relative markdown table path.")
    args = parser.parse_args(argv)

    spec = _attach_ids(_load_json(args.spec))
    arms = args.arms or list(spec["arms"])
    scenarios = args.scenarios or list(spec["scenarios"])
    for arm_id in arms:
        if arm_id not in spec["arms"]:
            raise SystemExit(f"unknown arm {arm_id!r}; "
                             f"valid: {sorted(spec['arms'])}")
    for scen_id in scenarios:
        if scen_id not in spec["scenarios"]:
            raise SystemExit(f"unknown scenario {scen_id!r}; "
                             f"valid: {sorted(spec['scenarios'])}")
    epochs = int(args.epochs or spec.get("epochs", 12))
    repeats = int(args.repeats or spec.get("repeats", 3))
    platforms = _platform_ids(args.platforms)
    binary = find_contamx()
    print(f"Repo: {REPO_ROOT}")
    print(f"ContamX binary: {binary or '(not found — native-only runs)'}")
    print(f"Platforms: {len(platforms)}  arms: {arms}  "
          f"scenarios: {scenarios}  repeats: {repeats}  epochs: {epochs}")

    reports: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="contam_fleet_") as tmp_root:
        for platform_id in platforms:
            try:
                report = run_platform(
                    platform_id, spec, arms=arms, scenarios=scenarios,
                    repeats=repeats, epochs=epochs, binary=binary,
                    tmp_root=tmp_root,
                )
            except (ContamXUnavailable, ValueError, OSError, KeyError) as exc:
                report = {
                    "platform": platform_id,
                    "n_zones": 0, "n_hvac_groups": 0,
                    "has_committed_prj": False,
                    "injection_zone": "", "inject_mass": 0.0,
                    "arms": {},
                    "errors": [{"cell": "platform", "error": str(exc)}],
                }
            _print_platform_summary(report)
            reports.append(report)
    path = _write_outputs(
        reports, spec, out_dir=args.out, md_out=args.md_out, binary=binary,
    )
    print(f"\nWrote report: {path}")
    n_err = sum(len(r["errors"]) for r in reports)
    n_err += sum(
        len(arm.get("errors", []))
        for r in reports for arm in r["arms"].values()
    )
    if n_err:
        print(f"Cell errors: {n_err} (see report)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
