#!/usr/bin/env python3
"""COVID-MECH-V2 assay readout — RINGCAP-V1 / SUSCPOOL-V1 clause scoring
under once_per_course, paired seed-for-seed against the v15 stage-2
parent surface.

Each assay design carries a baseline arm with empty overrides (cap_on /
declared) plus its mechanism arms. The tool:

- audits every cell: the replay contract (index_onset_day == -1.0,
  index_shedding_at_day0), the resolved delivery echoes
  (presentation_draw_mode == once_per_course, hand_reservoir_mode ==
  hygiene_cycle), and the arm's own override echo — resolved
  include_fixed_rings on rings_first (spec echo plus the engine-side
  flag in delivery), resolved + realized secretor_negative on the
  f-fraction arms;
- scores each (theta, arm) row on the verbatim v11 clause (takeoff-
  conditional q05-q95 of recorded_onsets contains 197 AND takeoff
  median before_share within 0.10 of 0.173, scored only at >= 5 takeoff
  seeds);
- pairs seed-for-seed: the baseline arm against the v15 stage-2 parent
  cells (the drift audit — a no-override arm must reproduce the parent
  row on the current engine), and every mechanism arm against both the
  parent and the baseline arm (the marginal mechanism effect).

Report-immediately triggers mirror the designs' frozen grammar:
anchor-collapse on a scored mechanism row (the assay premise),
clause PASS on an admissible row (the band moved), insufficient takeoff
mass on a submitted row, baseline drift vs the parent, audit failures,
and -- with --expect-complete -- rows that never landed.

Usage:
    python3 tools/covid_mech_v2_readout.py \
        --cells campaign_results/covid_mech_v2/cells \
        --design picard_framework/runs/covid_ring_cap_v1_design.json \
        --parent-cells campaign_results/covid_theta_screen_v15_stage2/cells \
        [--expect-complete] --out telemetry_buffer/covid_mech_v2_readout.json
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
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_screen_readout_common import (  # noqa: E402
    MIN_TAKEOFF_SEEDS,
    TAKEOFF_MIN_ONSETS,
    load_cell_payloads,
    quantile,
    standard_row_stats,
)
from tools.covid_theta_v15_stage2_readout import (  # noqa: E402
    AUDIT_ECHOES,
    _clause,
    _mass_in_band,
)

# The realized secretor-negative draw is a binomial draw over ~3,711
# aboard hosts; 0.08 is ~10 sigma at the widest declared fraction and
# loose enough that only a wiring failure can trip it.
SECRETOR_DRAW_TOL = 0.08
CHILD_FAILURE_TRIGGER = 0.05

# The arms whose stale-canary (472cdf13) anchor PASSes made them the
# assay premise; a scored anchor FAIL on any of them is the declared
# "premise collapses" trigger (docs/covid/covid_mech_v1_canary_readout.md).
# FAILs on arms that never passed (f025, f075) are not premise events.
PREMISE_ARMS: dict[str, frozenset[str]] = {
    "covid_ring_cap_v1": frozenset({"rings_first"}),
    "covid_susc_pool_v1": frozenset({"f050"}),
}


def _arm_expectations(arm: dict[str, Any]) -> dict[str, Any]:
    """The declared projection one arm's payload must echo."""
    overrides = arm.get("overrides") or {}
    tx = overrides.get("transmission_overrides") or {}
    patho = (overrides.get("pathogen_overrides") or {}).get(
        "sars_cov2_resp",
    ) or {}
    return {
        "include_fixed_rings": bool(
            (tx.get("exposure_cap") or {}).get("include_fixed_rings")
        ),
        "secretor_fraction": patho.get("secretor_negative_fraction"),
        "secretor_rel_susc": patho.get(
            "secretor_negative_relative_susceptibility"
        ),
    }


def _audit_delivery(delivery: dict[str, Any], want: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for field, want_value in AUDIT_ECHOES.items():
        got = delivery.get(field)
        if got != want_value:
            failures.append(f"delivery.{field} {got!r} != {want_value!r}")
    if "include_fixed_rings" not in want:
        return failures
    engine_flag = delivery.get("exposure_cap_include_fixed_rings_engine")
    if bool(engine_flag) != want["include_fixed_rings"]:
        failures.append(
            "delivery.exposure_cap_include_fixed_rings_engine "
            f"{engine_flag!r} != declared {want['include_fixed_rings']!r}",
        )
    return failures


def _audit_cap_echo(payload: dict[str, Any], want: dict[str, Any]) -> list[str]:
    if "include_fixed_rings" not in want:
        return []
    spec_flag = payload.get("exposure_cap_include_fixed_rings")
    if spec_flag == want["include_fixed_rings"]:
        return []
    if want["include_fixed_rings"] or spec_flag is not None:
        return [
            "exposure_cap_include_fixed_rings "
            f"{spec_flag!r} != declared {want['include_fixed_rings']!r}",
        ]
    return []


def _resolved_secretor_fraction(block: dict[str, Any]) -> float:
    resolved = block.get("resolved") or {}
    if resolved.get("secretor_negative_fraction") is not None:
        return float(resolved["secretor_negative_fraction"])
    return float(resolved.get("innate_nonsusceptible_fraction") or 0.0)


def _audit_secretor_echo(
    payload: dict[str, Any], want: dict[str, Any],
) -> list[str]:
    """Declared/resolved/realized pool draw against the arm's fraction."""
    if "secretor_fraction" not in want:
        return []
    block = payload.get("secretor_negative")
    if not isinstance(block, dict):
        return ["missing secretor_negative audit echo"]
    failures: list[str] = []
    declared = block.get("declared") or {}
    if declared.get("secretor_negative_fraction") != want[
        "secretor_fraction"
    ] or declared.get(
        "secretor_negative_relative_susceptibility",
    ) != want["secretor_rel_susc"]:
        failures.append(
            "secretor_negative.declared does not echo the arm's "
            "overrides",
        )
    want_frac = float(want["secretor_fraction"] or 0.0)
    resolved_frac = _resolved_secretor_fraction(block)
    if resolved_frac != want_frac:
        failures.append(
            f"secretor_negative resolved {resolved_frac} != declared "
            f"{want_frac}",
        )
    realized = block.get("realized") or {}
    drawn = float(realized.get("drawn_fraction") or 0.0)
    if want_frac > 0.0:
        if abs(drawn - want_frac) > SECRETOR_DRAW_TOL:
            failures.append(
                f"realized draw {drawn:.4f} outside +-{SECRETOR_DRAW_TOL} "
                f"of declared {want_frac}",
            )
        if float(want["secretor_rel_susc"] or 0.0) == 0.0 and (
            realized.get("zero_susceptibility")
            != realized.get("secretor_negative_drawn")
        ):
            failures.append(
                "rel_susc 0.0 but zero-susceptibility count != drawn count",
            )
    elif drawn != 0.0:
        failures.append(f"baseline arm drew {drawn:.4f} secretor-negative")
    return failures


def _audit_cell(
    payload: dict[str, Any],
    design_id: str,
    expected: dict[str, Any],
) -> list[str]:
    """One assay cell against the replay contract + its arm's echoes."""
    failures: list[str] = []
    if payload.get("design_id") != design_id:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {design_id!r}",
        )
    if float(payload.get("index_onset_day") or 0.0) != -1.0:
        failures.append(
            f"index_onset_day {payload.get('index_onset_day')!r} != -1.0",
        )
    if not payload.get("index_shedding_at_day0"):
        failures.append("index_shedding_at_day0 not set")
    observables = payload.get("observables") or {}
    for field in ("recorded_onsets", "onsets_before_split_day"):
        if observables.get(field) is None:
            failures.append(f"observables.{field} missing")
    if payload.get("infections_total") is None:
        failures.append("infections_total missing")
    delivery = payload.get("delivery") or {}
    failures += _audit_delivery(delivery, expected)
    failures += _audit_cap_echo(payload, expected)
    failures += _audit_secretor_echo(payload, expected)
    return failures


def _before_share(payload: dict[str, Any]) -> float | None:
    obs = payload.get("observables") or {}
    rec = obs.get("recorded_onsets")
    before = obs.get("onsets_before_split_day")
    if not rec or before is None:
        return None
    return float(before) / float(rec)


def _pair_map(
    payloads: dict[str, dict],
    reference: dict[str, dict],
) -> dict[tuple, dict[str, Any]]:
    """Seed-paired (theta, arm, seed) -> {payload, ref} at same theta+seed."""
    ref_by_ts: dict[tuple[float, int], dict] = {}
    for ref in reference.values():
        cell = ref.get("cell") or {}
        if cell.get("theta") is None or cell.get("seed") is None:
            continue
        ref_by_ts[(float(cell["theta"]), int(cell["seed"]))] = ref
    paired: dict[tuple, dict[str, Any]] = {}
    for payload in payloads.values():
        cell = payload.get("cell") or {}
        theta, seed = cell.get("theta"), cell.get("seed")
        if theta is None or seed is None:
            continue
        key = (float(theta), cell.get("arm_id"), int(seed))
        paired[key] = {
            "payload": payload,
            "ref": ref_by_ts.get((float(theta), int(seed))),
        }
    return paired


def _pair_stats(
    paired: dict[tuple, dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    """Per-(theta, arm) paired deltas vs the reference cells."""
    slots: dict[tuple, dict[str, list]] = {}
    for (theta, arm_id, _seed), rec in paired.items():
        ref = rec["ref"]
        if ref is None:
            continue
        obs = rec["payload"].get("observables") or {}
        r_obs = ref.get("observables") or {}
        cur, par = obs.get("recorded_onsets"), r_obs.get("recorded_onsets")
        if cur is None or par is None:
            continue
        slot = slots.setdefault(
            (theta, arm_id),
            {"d_rec": [], "d_share": [], "d_inf": [], "flips": 0.0},
        )
        slot["d_rec"].append(float(cur) - float(par))
        share, r_share = _before_share(rec["payload"]), _before_share(ref)
        if share is not None and r_share is not None:
            slot["d_share"].append(share - r_share)
        cur_inf = rec["payload"].get("infections_total")
        ref_inf = ref.get("infections_total")
        if cur_inf is not None and ref_inf is not None:
            slot["d_inf"].append(float(cur_inf) - float(ref_inf))
        slot["flips"] += float(
            (cur >= TAKEOFF_MIN_ONSETS) != (par >= TAKEOFF_MIN_ONSETS)
        )
    out: dict[tuple, dict[str, Any]] = {}
    for key, slot in slots.items():
        out[key] = {
            "n_paired": len(slot["d_rec"]),
            "delta_recorded_onsets_median": quantile(slot["d_rec"], 0.5),
            "delta_recorded_onsets_q05": quantile(slot["d_rec"], 0.05),
            "delta_recorded_onsets_q95": quantile(slot["d_rec"], 0.95),
            "delta_before_share_median": quantile(slot["d_share"], 0.5),
            "delta_infections_total_median": quantile(slot["d_inf"], 0.5),
            "takeoff_class_flips": int(slot["flips"]),
        }
    return out


def _baseline_arm(design: Any) -> str:
    """The arm with empty overrides (cap_on / declared) — the drift cell."""
    for arm in design.arms or ():
        if not arm.get("overrides"):
            return arm["arm_id"]
    raise ValueError("design declares no empty-override baseline arm")


def _row_trigger_entries(
    theta: float,
    arm_id: str,
    stats: dict[str, Any],
    baseline_arm: str,
    anchor: float,
    admissible: set[float],
    design_id: str,
) -> list[dict[str, Any]]:
    """The frozen report-immediately grammar, one (theta, arm) row."""
    triggers: list[dict[str, Any]] = []
    clause = stats["clause"]
    row = {"theta": theta, "arm_id": arm_id, "takeoff_n": stats["takeoff_n"]}
    if stats["takeoff_n"] < MIN_TAKEOFF_SEEDS:
        triggers.append({**row, "trigger": "insufficient_takeoff_mass"})
    if theta == anchor and clause["scored"] and not clause["clause_ok"]:
        if arm_id in PREMISE_ARMS.get(design_id, frozenset()):
            triggers.append({**row, "trigger": "anchor_premise_collapsed"})
        elif arm_id != baseline_arm:
            triggers.append({**row, "trigger": "anchor_clause_fail"})
    if theta in admissible and clause["scored"] and clause["clause_ok"]:
        triggers.append({**row, "trigger": "clause_pass_at_admissible"})
    return triggers


def _print_rows(rows: dict[tuple, dict[str, Any]]) -> None:
    for (theta, arm_id), s in sorted(rows.items()):
        rec, share, clause = (
            s["takeoff_recorded_onsets"],
            s["takeoff_before_share"],
            s["clause"],
        )
        band = (
            f"{rec['q05']:g}-{rec['q95']:g}"
            if rec["q05"] is not None else "unscored"
        )
        med = share["median"]
        if not clause["scored"]:
            verdict = "unscored"
        else:
            verdict = "PASS" if clause["clause_ok"] else "FAIL"
        print(
            f"theta {theta:g} arm {arm_id} takeoff {s['takeoff_n']}/"
            f"{s['n_cells']} rec band {band} share "
            f"{med if med is not None else float('nan'):.3f} "
            f"mass_t1 {s['mass_near_t1']} clause {verdict}",
        )


def main(argv: list[str] | None = None) -> int:
    """Read out a MECH-V2 assay surface against the frozen clause."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--parent-cells", default=None)
    parser.add_argument(
        "--expect-complete", action="store_true",
        help="every declared (theta, arm) row must have cells; a missing "
             "row fires a trigger (full-array readouts only)",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    design = load_design(
        resolve_repo_path(REPO_ROOT, args.design), repo_root=REPO_ROOT,
    )
    lattice = {
        (c.theta, c.arm_id, c.seed): c for c in enumerate_cells(design)
    }
    declared = {
        arm["arm_id"]: _arm_expectations(arm) for arm in (design.arms or ())
    }
    baseline = _baseline_arm(design)
    anchor = design.thetas[0]
    admissible = set(design.thetas[1:])

    # The mech_v2 replay prefix is shared by both assays, so a cells dir
    # holds foreign-design payloads; they belong to the sibling readout.
    loaded = load_cell_payloads(args.cells)
    payloads = {
        n: p
        for n, p in loaded.items()
        if p.get("design_id") == design.design_id
    }
    foreign_design_cells = len(loaded) - len(payloads)
    audit_failures: dict[str, list[str]] = {}
    rows: dict[tuple, list[dict]] = {}
    for name, payload in sorted(payloads.items()):
        cell = payload.get("cell") or {}
        key = (
            float(cell.get("theta") or -1.0),
            cell.get("arm_id"),
            int(cell.get("seed") or -1),
        )
        expected = declared.get(key[1])
        failures = _audit_cell(
            payload, design.design_id, expected or {},
        )
        if key not in lattice:
            failures.append("cell key not in the declared lattice")
        elif expected is None:
            failures.append(f"unknown arm {key[1]!r}")
        if failures:
            audit_failures[name] = failures
        rows.setdefault((key[0], key[1]), []).append(payload)

    submitted = set(rows)
    unsubmitted = sorted(
        {(c.theta, c.arm_id) for c in lattice.values()} - submitted,
    )
    row_summaries: dict[tuple, dict[str, Any]] = {}
    triggers: list[dict[str, Any]] = []
    for key, row in sorted(rows.items()):
        stats = standard_row_stats(row, extra_fields=_mass_in_band)
        stats["n_cells"] = len(row)
        stats["seeds_declared"] = design.seeds
        stats["clause"] = _clause(stats)
        row_summaries[key] = stats
        triggers += _row_trigger_entries(
            key[0], key[1], stats, baseline, anchor, admissible,
            design.design_id,
        )
        missing_seeds = design.seeds - len(row)
        if missing_seeds / design.seeds > CHILD_FAILURE_TRIGGER:
            triggers.append({
                "theta": key[0], "arm_id": key[1],
                "trigger": "partial_row",
                "detail": f"{len(row)}/{design.seeds} seeds landed",
            })
    if args.expect_complete:
        for theta, arm_id in unsubmitted:
            triggers.append({
                "theta": theta, "arm_id": arm_id,
                "trigger": "row_never_landed",
            })

    paired_vs_parent: dict[str, Any] | None = None
    paired_vs_baseline: dict[str, Any] | None = None
    baseline_payloads = {
        n: p for n, p in payloads.items()
        if (p.get("cell") or {}).get("arm_id") == baseline
    }
    if args.parent_cells:
        parents = load_cell_payloads(args.parent_cells)
        paired_vs_parent = {
            f"theta={t:g}|arm={a}": s
            for (t, a), s in sorted(
                _pair_stats(_pair_map(payloads, parents)).items(),
            )
        }
        for (theta, arm_id), stats in _pair_stats(
            _pair_map(baseline_payloads, parents),
        ).items():
            drift = (
                stats["delta_recorded_onsets_median"] != 0.0
                or stats["takeoff_class_flips"] > 0
            )
            if drift:
                triggers.append({
                    "theta": theta, "arm_id": arm_id,
                    "trigger": "baseline_drift_vs_v15",
                    "detail": (
                        "baseline arm does not reproduce the v15 parent "
                        f"row: {stats}"
                    ),
                })
    armed = {
        n: p for n, p in payloads.items()
        if (p.get("cell") or {}).get("arm_id") != baseline
    }
    if armed and baseline_payloads:
        paired_vs_baseline = {
            f"theta={t:g}|arm={a}": s
            for (t, a), s in sorted(
                _pair_stats(_pair_map(armed, baseline_payloads)).items(),
            )
        }
    if audit_failures:
        triggers.append({
            "trigger": "audit_failures",
            "detail": f"{len(audit_failures)} cells failed the audit",
            "cells": sorted(audit_failures),
        })

    report = {
        "cells_found": len(payloads),
        "cells_expected": len(lattice),
        "foreign_design_cells_skipped": foreign_design_cells,
        "baseline_arm": baseline,
        "anchor_theta": anchor,
        "audit_failures": audit_failures,
        "unsubmitted_rows": [f"theta={t:g}|arm={a}" for t, a in unsubmitted],
        "rows": {
            f"theta={t:g}|arm={a}": s for (t, a), s in row_summaries.items()
        },
        "paired_vs_v15_stage2": paired_vs_parent,
        "paired_vs_baseline": paired_vs_baseline,
        "report_immediately": triggers,
    }
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        prepare_output_directory(
            os.path.dirname(out_path) or REPO_ROOT,
            allowed_roots=(REPO_ROOT,),
        )
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"readout written to {out_path}")
    _print_rows(row_summaries)
    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(audit_failures)} audit failures; "
        f"{len(triggers)} report-immediately triggers",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
