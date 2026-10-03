#!/usr/bin/env python3
"""COVID-MECH-V2 fleet-shape readout — the SUSCPOOL-V1 generic-voyage
check, scored against the covid.H3 window verbatim.

The fleet design is report-only by declaration: no row is admitted or
rejected. The tool

- audits every cell: the delivery echoes (presentation_draw_mode ==
  once_per_course, hand_reservoir_mode == hygiene_cycle), the payload
  fields the attack-rate channel needs (observables.recorded_onsets,
  aboard_total, infections_total), and each arm's own override echo —
  resolved + realized secretor_negative on the f-fraction arms;
- pools the cells with ``merge_screen`` into the per-(theta, arm)
  surface rows the design asks for: median attack rate, IQR, takeoff
  fraction, P(attack >= 0.10), plus the v11 fleet_shape_ok selector and
  the design's own per-seed delta_vs_baseline;
- places each arm row beside the v15 stage-1 comparator at the same
  theta and computes the lattice offset of the arm's median on the v15
  surface (the declared upward-sign-flip trigger: a hard
  non-susceptible pool cannot raise the attack);
- pairs seed-for-seed: the baseline arm against the v15 stage-1 parent
  cells (drift audit) and the mechanism arms against both the parent
  and the baseline arm (marginal effect).

Report-immediately triggers: an arm median more than one lattice notch
above its v15 comparator, a missing or wrong resolved secretor echo,
missing cells under --expect-complete, audit failures.

Usage:
    python3 tools/covid_mech_v2_fleet_readout.py \
        --cells campaign_results/covid_mech_v2_fleet/cells \
        --design picard_framework/runs/covid_susc_pool_v1_fleet_design.json \
        --parent-design picard_framework/runs/covid_theta_screen_v15_design.json \
        --parent-cells campaign_results/covid_theta_screen_v15/cells \
        [--expect-complete] --out telemetry_buffer/covid_mech_v2_fleet.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
    merge_screen,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_mech_v2_readout import (  # noqa: E402
    _arm_expectations,
    _audit_cap_echo,
    _audit_delivery,
    _audit_secretor_echo,
)
from tools.covid_screen_readout_common import (  # noqa: E402
    load_cell_payloads,
    quantile,
)


def _attack_rate(payload: dict[str, Any]) -> float | None:
    """Recorded attack rate = recorded_onsets / aboard_total."""
    obs = payload.get("observables") or {}
    rec = obs.get("recorded_onsets")
    aboard = payload.get("aboard_total")
    if rec is None or not aboard:
        return None
    return float(rec) / float(aboard)


def _audit_fleet_cell(
    payload: dict[str, Any],
    design_id: str,
    expected: dict[str, Any],
) -> list[str]:
    """One fleet cell: the generic-voyage contract + the arm's echoes.

    Generic voyages do not carry the replay index-geometry contract
    (index_onset_day / index_shedding_at_day0 are DP-boarding fields), so
    the audit is the delivery echoes, the attack-rate numerator, and the
    arm's override echoes.
    """
    failures: list[str] = []
    if payload.get("design_id") != design_id:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {design_id!r}",
        )
    observables = payload.get("observables") or {}
    if observables.get("recorded_onsets") is None:
        failures.append("observables.recorded_onsets missing")
    if not payload.get("aboard_total"):
        failures.append("aboard_total missing")
    if payload.get("infections_total") is None:
        failures.append("infections_total missing")
    delivery = payload.get("delivery") or {}
    failures += _audit_delivery(delivery, expected)
    failures += _audit_cap_echo(payload, expected)
    failures += _audit_secretor_echo(payload, expected)
    return failures


def _v15_rows_by_theta(surface: dict[str, Any]) -> dict[float, dict]:
    """The parent surface's one arm, indexed by theta."""
    return {
        float(e["theta"]): e
        for e in surface.get("surface") or []
        if e.get("theta") is not None
    }


def _median_attack(entry: dict[str, Any] | None) -> float | None:
    if not entry:
        return None
    stats = entry.get("recorded_attack_rate") or {}
    return stats.get("median")


def _lattice_offset(
    arm_median: float,
    theta_index: int,
    thetas: list[float],
    parent_by_theta: dict[float, dict],
) -> int | None:
    """How far up the v15 lattice the arm median reaches.

    offset = max j with parent_median(theta_j) <= arm_median, minus i.
    offset 0 = level with the same-theta parent; positive = upward shift
    (a sign flip for a non-susceptible pool); negative = sag. None when
    the parent surface lacks the comparator row.
    """
    if thetas[theta_index] not in parent_by_theta:
        return None
    above = -1
    for j, th in enumerate(thetas):
        p_med = _median_attack(parent_by_theta.get(th))
        if p_med is not None and p_med <= arm_median:
            above = j
    return above - theta_index


def _delta_stats(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {"n": 0}
    return {
        "n": len(deltas),
        "median": quantile(deltas, 0.5),
        "q25": quantile(deltas, 0.25),
        "q75": quantile(deltas, 0.75),
        "min": min(deltas),
        "max": max(deltas),
    }


def _seed_paired_attack(
    payloads: dict[str, dict],
    reference: dict[str, dict],
) -> dict[float, dict[str, Any]]:
    """Per-seed attack-rate deltas payload - reference at same theta+seed."""
    ref_by_ts: dict[tuple[float, int], dict] = {}
    for ref in reference.values():
        cell = ref.get("cell") or {}
        if cell.get("theta") is not None and cell.get("seed") is not None:
            ref_by_ts[(float(cell["theta"]), int(cell["seed"]))] = ref
    by_theta: dict[float, list[float]] = {}
    takeoff_flips: dict[float, int] = {}
    for payload in payloads.values():
        cell = payload.get("cell") or {}
        theta, seed = cell.get("theta"), cell.get("seed")
        if theta is None or seed is None:
            continue
        ref = ref_by_ts.get((float(theta), int(seed)))
        if ref is None:
            continue
        rate, ref_rate = _attack_rate(payload), _attack_rate(ref)
        if rate is None or ref_rate is None:
            continue
        th = float(theta)
        by_theta.setdefault(th, []).append(rate - ref_rate)
        obs = payload.get("observables") or {}
        p_rec, r_rec = (
            obs.get("recorded_onsets"),
            (ref.get("observables") or {}).get("recorded_onsets"),
        )
        if p_rec is not None and r_rec is not None and (
            (p_rec >= 10) != (r_rec >= 10)
        ):
            takeoff_flips[th] = takeoff_flips.get(th, 0) + 1
    return {
        th: {
            **_delta_stats(deltas),
            "takeoff_class_flips": takeoff_flips.get(th, 0),
        }
        for th, deltas in by_theta.items()
    }


def _fleet_rows(
    design: Any,
    payloads: dict[str, dict],
    parent_surface: dict[str, Any],
    arm_filter: set[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Surface rows beside their v15 comparators + notch triggers."""
    surface = merge_screen(design, payloads, allow_partial=True)
    parent_by_theta = _v15_rows_by_theta(parent_surface)
    thetas = sorted(float(t) for t in design.thetas)
    rows: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []
    for entry in surface.get("surface") or []:
        arm = entry.get("arm_id")
        if arm_filter and arm not in arm_filter:
            continue
        theta = float(entry["theta"])
        parent = parent_by_theta.get(theta)
        median = _median_attack(entry)
        offset = None
        if median is not None and theta in parent_by_theta:
            offset = _lattice_offset(
                median, thetas.index(theta), thetas, parent_by_theta,
            )
        rows.append({
            "theta": theta,
            "arm_id": arm,
            "n_seeds": len(entry.get("seeds") or []),
            "takeoff_probability": entry.get("takeoff_probability"),
            "recorded_attack_rate": entry.get("recorded_attack_rate"),
            "attack_rate_quantiles": entry.get(
                "recorded_attack_rate_quantiles",
            ),
            "p_recorded_ge_0p015": entry.get("p_recorded_ge_0p015"),
            "p_recorded_ge_0p10": entry.get("p_recorded_ge_0p10"),
            "p_recorded_le_0p01": entry.get("p_recorded_le_0p01"),
            "fleet_shape_ok": entry.get("fleet_shape_ok"),
            "delta_vs_baseline": entry.get("delta_vs_baseline"),
            "v15_comparator": {
                "median_attack": _median_attack(parent),
                "mean_attack": (
                    (parent.get("recorded_attack_rate") or {}).get("mean")
                    if parent else None
                ),
                "takeoff_probability": (
                    parent.get("takeoff_probability") if parent else None
                ),
                "fleet_shape_ok": (
                    parent.get("fleet_shape_ok") if parent else None
                ),
            },
            "lattice_notches_up": offset,
        })
        if offset is not None and offset >= 1 and arm != design.baseline_arm_id:
            triggers.append({
                "trigger": "upward_lattice_notch",
                "theta": theta,
                "arm_id": arm,
                "detail": (
                    f"arm median {median:.5g} sits {offset} notch(es) "
                    "above its same-theta v15 comparator -- fewer "
                    "susceptibles cannot raise the attack; a sign flip "
                    "is a mechanism defect, not a result"
                ),
            })
    return rows, triggers


def _missing_cells(
    design: Any,
    payloads: dict[str, dict],
    arm_filter: set[str] | None,
) -> list[str]:
    expected = {
        c.key for c in enumerate_cells(design)
        if arm_filter is None or c.arm_id in arm_filter
    }
    return sorted(expected - set(payloads))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--parent-design", default=None)
    parser.add_argument("--parent-cells", default=None)
    parser.add_argument("--arms", nargs="*", default=None)
    parser.add_argument("--expect-complete", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    design = load_design(
        resolve_repo_path(REPO_ROOT, args.design), repo_root=REPO_ROOT,
    )
    arm_filter = set(args.arms) if args.arms else None
    loaded = load_cell_payloads(args.cells)
    payloads = {
        n: p for n, p in loaded.items()
        if p.get("design_id") == design.design_id
    }
    foreign = len(loaded) - len(payloads)

    expected_by_arm = {
        a["arm_id"]: _arm_expectations(a) for a in design.arms
    }
    audit_failures: dict[str, list[str]] = {}
    for name, payload in payloads.items():
        arm = (payload.get("cell") or {}).get("arm_id")
        failures = _audit_fleet_cell(
            payload, design.design_id, expected_by_arm.get(arm) or {},
        )
        if failures:
            audit_failures[name] = failures

    missing = _missing_cells(design, payloads, arm_filter)
    if args.expect_complete and missing:
        audit_failures["_missing"] = missing

    parent_surface: dict[str, Any] = {}
    parents: dict[str, dict] = {}
    parent_payloads: dict[str, dict] = {}
    if args.parent_cells and args.parent_design:
        parent_design = load_design(
            resolve_repo_path(REPO_ROOT, args.parent_design),
            repo_root=REPO_ROOT,
        )
        parents = load_cell_payloads(args.parent_cells)
        parents = {
            n: p for n, p in parents.items()
            if p.get("design_id") == parent_design.design_id
        }
        # The fleet design pairs against the FIRST seeds of the v15
        # block by declaration, so the comparator rows must pool the
        # same seed subset -- a 200-seed v15 row against a 50-seed arm
        # row is apples/oranges.
        fleet_seeds = {
            c.seed for c in enumerate_cells(design)
        }
        parent_payloads = {
            n: p for n, p in parents.items()
            if (p.get("cell") or {}).get("seed") in fleet_seeds
        }
        parent_surface = merge_screen(
            parent_design, parent_payloads, allow_partial=True,
        )

    rows, triggers = _fleet_rows(design, payloads, parent_surface, arm_filter)

    by_arm: dict[str, dict[str, dict]] = {}
    for name, payload in payloads.items():
        arm = (payload.get("cell") or {}).get("arm_id")
        by_arm.setdefault(arm, {})[name] = payload

    baseline_arm = design.baseline_arm_id
    baseline_payloads = by_arm.get(baseline_arm, {})
    pairing: dict[str, Any] = {}
    parent_ref = parent_payloads if parents else {}
    if parent_ref:
        pairing["baseline_vs_v15"] = _seed_paired_attack(
            baseline_payloads, parent_ref,
        )
    pairing["arm_vs_baseline"] = {
        arm: _seed_paired_attack(arm_payloads, baseline_payloads)
        for arm, arm_payloads in by_arm.items()
        if arm != baseline_arm
    }
    if parent_ref:
        pairing["arm_vs_v15"] = {
            arm: _seed_paired_attack(arm_payloads, parent_ref)
            for arm, arm_payloads in by_arm.items()
            if arm != baseline_arm
        }

    drift = pairing.get("baseline_vs_v15") or {}
    drifted = [
        th for th, s in drift.items()
        if s.get("n") and abs(s.get("median") or 0.0) > 1e-12
    ]
    if drifted:
        triggers.append({
            "trigger": "baseline_drift_vs_v15",
            "detail": (
                f"baseline arm does not reproduce the v15 stage-1 parent "
                f"seed-for-seed at thetas {drifted}"
            ),
        })
    if audit_failures:
        triggers.append({
            "trigger": "audit_failures",
            "n_cells": len(audit_failures),
            "detail": json.dumps(
                {k: v for k, v in list(audit_failures.items())[:5]},
            ),
        })

    report = {
        "design_id": design.design_id,
        "cells_found": len(payloads),
        "foreign_design_cells_skipped": foreign,
        "audit_failures": audit_failures,
        "rows": rows,
        "pairing": pairing,
        "report_immediately": triggers,
    }
    print(
        f"{len(payloads)} cells; {len(audit_failures)} audit failures; "
        f"{len(triggers)} triggers",
    )
    for row in rows:
        attack = row.get("recorded_attack_rate") or {}
        print(
            f"theta={row['theta']:.4g} arm={row['arm_id']} "
            f"median={attack.get('median')} mean={attack.get('mean')} "
            f"takeoff={row.get('takeoff_probability')} "
            f"v15_median={row['v15_comparator']['median_attack']} "
            f"notches_up={row['lattice_notches_up']} "
            f"fleet_shape_ok={row['fleet_shape_ok']}",
        )
    if triggers:
        print("REPORT_IMMEDIATELY:", json.dumps(triggers, indent=1))

    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        prepare_output_directory(
            os.path.dirname(out_path) or REPO_ROOT,
            allowed_roots=(REPO_ROOT,),
        )
        with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,)) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
