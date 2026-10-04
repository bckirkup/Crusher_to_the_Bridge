#!/usr/bin/env python3
"""CG-FLOOR-01 corner-probe readout: delivery strength at the declared floor.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_cg_floor_v1`` — two rows (Theta 1e6 and 7.9e6, the measured
leg-crossings) x two arms x 20 seeds — and reports, per row:

* the audit: ``delivery.caregiver.mode`` resolves ``on`` and
  ``delivery.participation_propensity.mode`` resolves ``party`` on every
  cell, ``propensity_draw.units_drawn`` > 0, the fixed echoes
  (``presentation_draw_mode`` once_per_course, ``hand_reservoir_mode``
  hygiene_cycle), and the index-geometry invariant;
* the corner echo: on CG_LOW cells
  ``delivery.caregiver.roles.tending.tending_copresence_multiplier``
  must echo ``[1.5, 1.5]`` and ``tending_hours_per_day`` ``[2.0, 2.0]``
  — the pinned declared-floor ranges — while D0_declared cells must echo
  the shipped ``[1.5, 3.0]`` / ``[2.0, 6.0]``. A missing or mismatched
  echo means the override never reached the engine: a design defect,
  not a sim result;
* the v11-lineage clause per row, verbatim: among takeoff seeds
  (recorded_onsets >= 10), the q05-q95 interval of recorded_onsets
  contains 197 AND the takeoff-seed median before_share is within 0.10
  of 0.173 — scored only at >= 5 takeoff seeds;
* the seed-paired deltas CG_LOW vs the in-design D0_declared row at the
  same theta (recorded_onsets, before_share, infections_total) — the
  leg-elasticity read;
* the caregiver witness per row: the pooled ``caregiver`` route tally
  (aboard window / during quarantine) and the caregiver share of pooled
  aboard-window acquisitions — the proxy for the dated-onset route
  share the derivation doc asks for (payloads carry route tallies on
  acquisitions, not on dated onsets — stated limitation);
* the replication check: each in-design D0_declared cell must bit-match
  its measured shipped-default counterpart (floor 1e6 cells / bracket
  7.9e6 cells) modulo ``cell.index`` and ``design_id`` bookkeeping; a
  divergence is an image/drift defect.

The DELIVERY-BOUNDED / DELIVERY-STRUCTURAL / SUB-IGNITION verdict is
declared in the design's frozen grammar and stated in the readout doc —
this tool emits the row-resolved clause map, deltas, witnesses, and the
replication block it is scored from.

Usage:
    python3 tools/covid_cg_floor_v1_readout.py \\
        --cells campaign_results/covid_cg_floor_v1/cells \\
        --design picard_framework/runs/covid_cg_floor_v1_design.json \\
        --out telemetry_buffer/covid_cg_floor_v1_readout.json
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    DP_RECORD_SEED_SPEC,
    audit_caregiver_echo,
    audit_fixed_delivery_echoes,
    audit_index_geometry,
    audit_propensity_echo,
    caregiver_route_witness,
    clause_row_triggers,
    declared_propensity_caregiver_block,
    design_readout_main,
    load_cell_payloads,
    paired_rows_against_baseline,
    propensity_row_stats,
)

REPO_ROOT = repo_root()

DESIGN_ID = "covid_cg_floor_v1"
BASELINE_ARM = "D0_declared"
CORNER_ARM = "CG_LOW"

# The shipped R2 tending intervals the corner pins at their low ends.
SHIPPED_TENDING = {
    "tending_copresence_multiplier": [1.5, 3.0],
    "tending_hours_per_day": [2.0, 6.0],
}

# The measured shipped-default rows the in-design D0_declared rows must
# replicate, keyed by theta. Bit-identity modulo bookkeeping keys is the
# image/drift witness.
REPLICATION_REFS = {
    1e6: "campaign_results/covid_theta_refit_floor_v1/cells",
    7.9e6: "campaign_results/covid_theta_refit_bracket_v1/cells",
}
REPLICATION_IGNORED_KEYS = {"design_id", "index"}
REPLICATION_DIFF_SAMPLE = 20


def declared_corner_block(arm: dict) -> dict:
    """Propensity/caregiver modes + the arm's expected tending ranges."""
    declared = declared_propensity_caregiver_block(arm)
    tending = (
        (
            (arm.get("overrides") or {}).get("transmission_overrides")
            or {}
        ).get("caregiver") or {}
    ).get("tending") or {}
    declared["tending"] = {
        key: [float(x) for x in (tending.get(key) or default)]
        for key, default in SHIPPED_TENDING.items()
    }
    return declared


def audit_tending_echo(
    failures: list[str], delivery: dict, declared: dict,
) -> None:
    """delivery.caregiver.roles.tending echoes the arm's tending ranges."""
    block = (delivery.get("caregiver") or {}).get("roles")
    if not isinstance(block, dict) or not isinstance(
        block.get("tending"), dict,
    ):
        failures.append(
            "delivery.caregiver.roles.tending missing — the role block "
            "did not resolve (design defect)",
        )
        return
    got_block = block["tending"]
    for key, want in declared["tending"].items():
        got = got_block.get(key)
        got_f = [float(x) for x in got] if isinstance(got, list) else None
        if got_f != want:
            failures.append(
                f"tending.{key} resolved {got!r}, expected {want!r} "
                "(design defect)",
            )


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    audit_propensity_echo(failures, payload, delivery, declared)
    audit_caregiver_echo(failures, delivery, declared)
    audit_tending_echo(failures, delivery, declared)
    audit_fixed_delivery_echoes(failures, delivery)
    audit_index_geometry(failures, payload, DP_RECORD_SEED_SPEC)
    cell = payload.get("cell") or {}
    if cell.get("arm_id") not in {BASELINE_ARM, CORNER_ARM}:
        failures.append(
            f"cell.arm_id {cell.get('arm_id')!r} not in "
            f"{sorted({BASELINE_ARM, CORNER_ARM})}",
        )
    if payload.get("design_id") != DESIGN_ID:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {DESIGN_ID!r}",
        )
    return failures


def _aboard_share(stats: dict) -> float | None:
    """Caregiver share of pooled aboard-window acquisitions (proxy for
    the dated-onset route share the payloads do not carry)."""
    pooled = stats.get("aboard_window_by_route_pooled") or {}
    total = sum(float(v) for v in pooled.values())
    if not total:
        return None
    return float(pooled.get("caregiver", 0)) / total


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + the caregiver witnesses."""
    stats = propensity_row_stats(payloads)
    stats["caregiver_route_pooled"] = caregiver_route_witness(stats)
    stats["aboard_window_caregiver_share"] = _aboard_share(stats)
    return stats


def _row_triggers(theta: float, arm_id: str, stats: dict) -> dict | None:
    """Report-immediately rows: a clause pass or timing/fizzle flag."""
    return clause_row_triggers(theta, arm_id, stats)


_MISSING = object()


def _leaf_diffs(
    a: Any, b: Any, path: str, diffs: list[tuple[str, Any, Any]],
) -> None:
    """Recursive leaf diff, ignoring REPLICATION_IGNORED_KEYS anywhere."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in REPLICATION_IGNORED_KEYS:
                continue
            _leaf_diffs(
                a.get(key, _MISSING), b.get(key, _MISSING),
                f"{path}.{key}" if path else key, diffs,
            )
        return
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _leaf_diffs(x, y, f"{path}[{i}]", diffs)
        return
    if a is _MISSING or b is _MISSING or a != b:
        diffs.append((path, a, b))


def replication_check(
    cells_dir: str,
    ref_dirs: dict[float, str] | None = None,
) -> dict:
    """D0_declared rows vs the measured shipped-default cells, seed-paired.

    Each in-design D0 cell at a ref theta pairs with the same-seed ref
    cell; bit-identity is checked modulo REPLICATION_IGNORED_KEYS
    (``design_id``, ``index``). Returns one block per theta.
    """
    ref_dirs = ref_dirs or REPLICATION_REFS
    own: dict[tuple[float, int], dict] = {}
    for p in load_cell_payloads(cells_dir).values():
        cell = p.get("cell") or {}
        if cell.get("arm_id") != BASELINE_ARM:
            continue
        own[(float(cell["theta"]), int(cell["seed"]))] = p

    out: dict[str, Any] = {}
    for theta, ref_dir in sorted(ref_dirs.items()):
        label = f"theta={theta:.4g}"
        ref_path = os.path.join(REPO_ROOT, ref_dir)
        if not os.path.isdir(ref_path):
            out[label] = {"skipped": f"ref dir missing: {ref_dir}"}
            continue
        refs = {
            int(p["cell"]["seed"]): p
            for p in load_cell_payloads(ref_path).values()
            if (p.get("cell") or {}).get("arm_id") == BASELINE_ARM
            and abs(float(p["cell"]["theta"]) - theta) < 1e-9
        }
        n_identical = 0
        n_paired = 0
        max_abs_delta = 0.0
        samples: list[dict] = []
        for (t, seed), p in sorted(own.items()):
            if abs(t - theta) > 1e-9 or seed not in refs:
                continue
            n_paired += 1
            diffs: list[tuple[str, Any, Any]] = []
            _leaf_diffs(p, refs[seed], "", diffs)
            if not diffs:
                n_identical += 1
            for path, a, b in diffs:
                if (
                    isinstance(a, (int, float))
                    and isinstance(b, (int, float))
                ):
                    max_abs_delta = max(max_abs_delta, abs(a - b))
            for path, a, b in diffs[: max(0, REPLICATION_DIFF_SAMPLE - len(samples))]:
                samples.append(
                    {"seed": seed, "path": path,
                     "got": a if a is not _MISSING else "<missing>",
                     "ref": b if b is not _MISSING else "<missing>"},
                )
        out[label] = {
            "ref_dir": ref_dir,
            "n_paired": n_paired,
            "n_identical": n_identical,
            "bit_identical": n_paired > 0 and n_identical == n_paired,
            "max_abs_delta": max_abs_delta,
            "diff_sample": samples,
        }
    return out


def _post_report(report: dict, cells_dir: str) -> None:
    """Append the D0 replication block to the report and print it."""
    rep = replication_check(str(cells_dir))
    report["replication"] = rep
    for label, row in rep.items():
        if "skipped" in row:
            print(f"{label}: replication skipped — {row['skipped']}")
        else:
            print(
                f"{label}: {row['n_identical']}/{row['n_paired']} "
                f"bit-identical, max|delta| {row['max_abs_delta']:.4g}",
            )


def main(argv: list[str] | None = None) -> int:
    spec = {
        "repo_root": REPO_ROOT,
        "declared_fn": declared_corner_block,
        "audit_cell": audit_cell,
        "row_stats": _row_stats,
        "report_key": "triggered_rows",
        "row_triggers": _row_triggers,
        "paired_rows_of": lambda _design: paired_rows_against_baseline(
            CORNER_ARM, BASELINE_ARM,
        ),
        "post_report": _post_report,
    }
    return design_readout_main(argv, **spec)


if __name__ == "__main__":
    raise SystemExit(main())
