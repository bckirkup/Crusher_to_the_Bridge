"""COVID-HAND-AB-01 readout: pool the three-arm hand-line A/B cells.

Reads the per-seed cell JSONs the Batch array wrote under
``campaign/covid_hand_ab_v1/<sha>/cells/`` and pools them by (theta, arm)
into the numbers the design's freeze block declares: takeoff-conditional
recorded-onsets and infections-total medians, the before-share leg,
during-quarantine share and route decomposition, and the seed-paired
deltas of each baseline arm (wash_reuptake, spike_decay) against the
shipped hygiene_cycle baseline.

An audit failure is a cell whose resolved echoes do not match its arm's
declaration: ``delivery.hand_reservoir_mode`` must equal the arm's
declared mode, the seed spec must carry the record's index geometry, and
the index fields must satisfy the audit invariant (onset before
boarding, shedding at day 0).

Usage:
    python3 tools/covid_hand_ab_readout.py \
        --cells campaign_results/covid_hand_ab_v1/cells \
        --design picard_framework/runs/covid_hand_ab_v1_design.json \
        --out readout.json
"""
from __future__ import annotations

import os
from functools import partial
from typing import Any

from tools.covid_screen_readout_common import (
    audit_hand_mode,
    declared_hand_mode,
    design_readout_main,
    fmt3g,
    load_cell_payloads,  # noqa: F401  (re-exported for tests)
    quantile,
    row_triggers,
    standard_row_stats,
)

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

# The shipped default arm (NORO-HAND-PRACTICE-01, PR #804): an arm whose
# overrides leave transmission.hand_reservoir_mode alone resolves this.
SHIPPED_HAND_MODE = "hygiene_cycle"
VALID_HAND_MODES = ("hygiene_cycle", "wash_reuptake", "spike_decay")

# The record's seed geometry is constant on this design (no seed_patch).
RECORD_SEED_SPEC = {"count": 1, "onset_day": -1.0, "role": "passenger"}


def _declared(arm: dict) -> dict:
    """The arm's declared hand-reservoir mode."""
    return declared_hand_mode(arm, SHIPPED_HAND_MODE)


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    failures: list[str] = audit_hand_mode(payload, declared)
    # Cells emit the spec only under ``seed_ring.seed_spec`` and only when
    # the design enables ``seed_ring_readout``; this design fixes the
    # record geometry instead, so an absent spec is not auditable here
    # (the index_* invariants below carry that check).
    spec = (payload.get("seed_ring") or {}).get("seed_spec") or payload.get(
        "seed_spec",
    )
    if spec:
        for key, want in RECORD_SEED_SPEC.items():
            if spec.get(key) != want:
                failures.append(
                    f"seed_spec.{key} is {spec.get(key)!r}, want {want!r}",
                )
    if float(payload.get("index_onset_day") or 0.0) > 0.0:
        failures.append(
            f"index_onset_day {payload.get('index_onset_day')} violates "
            "the audit invariant (must be <= 0.0)",
        )
    if not payload.get("index_shedding_at_day0"):
        failures.append("index_shedding_at_day0 is false")
    return failures


def _hand_extras(takeoff: list[dict], stats: dict) -> dict:
    """The row_extra columns: during-quarantine median and share."""
    return {
        "row_extra": (
            f"during med {fmt3g(stats['during_quarantine']['median'])} "
            f"share {fmt3g(stats['during_share']['median'])}"
        ),
    }


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + route decomposition for one row."""
    return standard_row_stats(payloads, extra_fields=_hand_extras)


def _paired_rows(
    rows: dict[tuple, list[dict]], baseline_arm_id: str,
) -> dict:
    """Seed-paired deltas of every non-baseline arm vs the baseline arm.

    The baseline is the design's first arm (hygiene_cycle), pinned by
    the caller -- the payloads' load order must not decide it. Every
    other arm reports the per-seed delta distribution on
    recorded_onsets, infections_total and before_share plus the
    takeoff-class flip count. That is the attribution read the
    design's freeze block declared.
    """
    out: dict[str, Any] = {}
    by_theta: dict[float, dict[str, dict[int, dict]]] = {}
    for (theta, arm_id), payloads in rows.items():
        seeded = {
            int((p.get("cell") or {}).get("seed")): p for p in payloads
        }
        by_theta.setdefault(float(theta), {})[str(arm_id)] = seeded
    for theta, arms in sorted(by_theta.items()):
        base = arms.get(baseline_arm_id, {})
        for arm_id, cells in arms.items():
            if arm_id == baseline_arm_id:
                continue
            deltas_rec: list[float] = []
            deltas_inf: list[float] = []
            deltas_share: list[float] = []
            flips = 0
            for seed, b in base.items():
                a = cells.get(seed)
                if a is None:
                    continue
                b_rec = float(b["observables"]["recorded_onsets"])
                a_rec = float(a["observables"]["recorded_onsets"])
                deltas_rec.append(b_rec - a_rec)
                b_inf = b.get("infections_total")
                a_inf = a.get("infections_total")
                if b_inf is not None and a_inf is not None:
                    deltas_inf.append(float(b_inf) - float(a_inf))
                if b_rec > 0 and a_rec > 0:
                    deltas_share.append(
                        float(b["observables"]["onsets_before_split_day"])
                        / b_rec
                        - float(a["observables"]["onsets_before_split_day"])
                        / a_rec,
                    )
                flips += int(
                    (b_rec >= 10.0) != (a_rec >= 10.0),
                )
            key = f"theta={theta:.4g}|{arm_id}_minus_{baseline_arm_id}"
            out[key] = {
                "paired_seeds": len(deltas_rec),
                "delta_recorded_onsets": {
                    "median": quantile(deltas_rec, 0.5),
                    "q05": quantile(deltas_rec, 0.05),
                    "q95": quantile(deltas_rec, 0.95),
                },
                "delta_infections_total": {
                    "median": quantile(deltas_inf, 0.5),
                    "q05": quantile(deltas_inf, 0.05),
                    "q95": quantile(deltas_inf, 0.95),
                },
                "delta_before_share": {
                    "median": quantile(deltas_share, 0.5),
                    "q05": quantile(deltas_share, 0.05),
                    "q95": quantile(deltas_share, 0.95),
                },
                "takeoff_class_flips": flips,
            }
    return out


def main(argv: list[str] | None = None) -> int:
    return design_readout_main(
        argv,
        repo_root=REPO_ROOT,
        declared_fn=_declared,
        audit_cell=audit_cell,
        row_stats=_row_stats,
        report_key="triggered_rows",
        row_triggers=partial(
            row_triggers,
            kind_flags=(
                ("TRUTH-IN-BAND", "truth_leg_in_band"),
                ("TIMING-IN-BAND", "timing_leg_in_band"),
                ("FIZZLE-MAJORITY", "fizzle_majority"),
            ),
            fields=(
                "takeoff_infections_total", "takeoff_before_share",
                "during_quarantine",
            ),
        ),
        paired_rows_of=lambda design: (
            lambda rows: _paired_rows(rows, design.arms[0]["arm_id"])
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
