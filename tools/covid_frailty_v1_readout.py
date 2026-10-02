"""FRAILTY-V1 readout: the continuous-frailty audit + the both-legs test.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_frailty_v1`` — one anchor point, 7 arms, 20 seeds — and reports,
per arm row:

* the frailty-structure audit (payload echo vs the arm's declared
  ``hazard_frailty`` corner — dose_response.frailty echoes
  {enabled, distribution, cv}, frailty_draw populated on armed cells and
  empty on D0, the inert corner's draws pinned at exactly 1.0, and
  frailty_draw.n == susceptibility_draw.n so the draw set is provably
  the challenged set),
* the conditioned legs: takeoff-conditional recorded_onsets /
  infections_total / before_share medians and q05-q95 against the
  record's 197 / 0.173 and the held-out covid.H5 band [712, 960],
* the shape discriminator: during-quarantine stratum sizes and the
  day-16 kink ratio (a kink toward 0 marks a suppression-shaped
  landing; smooth attenuation marks structure-shaped thinning),
* the seed-paired deltas vs D0_declared on recorded_onsets,
  before_share, and infections_total — on this design the shared stream
  is untouched by the arm, so the pairing is draw-matched, stronger
  than the IMM arms' ensemble-level pairing,
* the bit-identity audit: FRAIL_INERT vs D0 per-seed max |delta| —
  any nonzero divergence invalidates every armed read,
* the extended report-immediately triggers: truth or timing medians in
  band, fizzle-majority rows, during-quarantine-dominant rows, and an
  inert-corner divergence flag.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    anchor_legs,
    band_stats,
    quantile,
    resolve_design_arg,
    run_readout,
    takeoff_split,
)

REPO_ROOT = repo_root()

BASELINE_ARM = "D0_declared"
INERT_ARM = "FRAIL_INERT"
SHIPPED_ALPHA = 0.18
SHIPPED_BETA = 58.0
KINK_PRE_DAYS = (13, 14, 15)
KINK_POST_DAYS = (17, 18, 19)
KINK_RATIO_THRESHOLD = 0.5
# The frozen mean-pinning audit band: frailty_draw.mean on a cv > 0 arm
# is a ~1,000-3,000-host sample of a mean-1 draw, so [0.7, 1.3] is a
# declared wide bound, not a fit.
FRAILTY_MEAN_BAND = (0.7, 1.3)


def _declared(arm: dict) -> dict:
    """The arm's declared hazard_frailty corner (empty on D0)."""
    ov = arm.get("overrides") or {}
    hf = ov.get("hazard_frailty") or {}
    return {
        "frailty_arm": bool(hf),
        "frailty_distribution": hf.get("distribution"),
        "frailty_cv": hf.get("cv"),
    }


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    curve = payload.get("acquisition_curve")
    curve_ok = (
        isinstance(curve, dict)
        and isinstance(curve.get("total_by_day"), dict)
        and isinstance(curve.get("confined_by_day"), dict)
    )
    failures = [] if curve_ok else ["missing acquisition_curve block"]
    dr = payload.get("dose_response") or {}
    frailty_block = dr.get("frailty")
    draw = payload.get("frailty_draw") or {}
    sus = payload.get("susceptibility_draw") or {}
    if not declared["frailty_arm"]:
        if frailty_block is not None:
            failures.append("baseline dose_response carries a frailty key")
        if draw.get("n"):
            failures.append("baseline frailty_draw.n > 0")
        return failures
    _audit_armed_cell(
        failures, frailty_block, draw, sus, declared, dr, theta,
    )
    return failures


def _audit_armed_cell(
    failures: list[str],
    frailty_block: Any,
    draw: dict,
    sus: dict,
    declared: dict,
    dr: dict,
    theta: float,
) -> None:
    # Armed cell: the block echoes declared verbatim.
    if not isinstance(frailty_block, dict):
        failures.append("armed cell missing dose_response.frailty")
    else:
        _audit_armed_block(failures, frailty_block, declared)
    n = int(draw.get("n") or 0)
    if n <= 0:
        failures.append("armed cell frailty_draw.n == 0")
        return
    if n != int(sus.get("n") or -1):
        failures.append(
            f"frailty_draw.n {n} != susceptibility_draw.n {sus.get('n')} "
            "— the draw set is not the challenged set",
        )
    _audit_draw(failures, draw, declared)
    # The theta-preserved beta block must be untouched by the arm.
    _audit_scale(failures, dr, theta)


def _audit_scale(failures: list[str], dr: dict, theta: float) -> None:
    scale = float(dr.get("susceptibility_scale", -1.0))
    want_scale = theta * (SHIPPED_ALPHA + SHIPPED_BETA) / SHIPPED_ALPHA
    if scale <= 0 or abs(scale - want_scale) / want_scale > 1e-6:
        failures.append(
            f"dose_response.susceptibility_scale {scale} "
            f"!= theta-preserved {want_scale:.4g}",
        )


def _audit_armed_block(
    failures: list[str],
    frailty_block: dict,
    declared: dict,
) -> None:
    if frailty_block.get("enabled") is not True:
        failures.append("dose_response.frailty.enabled is not true")
    if frailty_block.get("distribution") != (
        declared["frailty_distribution"]
    ):
        failures.append(
            f"dose_response.frailty.distribution "
            f"{frailty_block.get('distribution')!r} != declared "
            f"{declared['frailty_distribution']!r}",
        )
    if abs(float(frailty_block.get("cv", -1.0))
           - float(declared["frailty_cv"])) > 1e-12:
        failures.append(
            f"dose_response.frailty.cv {frailty_block.get('cv')} "
            f"!= declared {declared['frailty_cv']}",
        )


def _audit_draw(
    failures: list[str],
    draw: dict,
    declared: dict,
) -> None:
    cv = float(declared["frailty_cv"])
    if cv <= 0.0:
        for key in ("mean", "q05", "q50", "q95"):
            if abs(float(draw.get(key) or 0.0) - 1.0) > 1e-12:
                failures.append(
                    f"inert corner frailty_draw.{key} {draw.get(key)} "
                    "!= 1.0",
                )
        return
    mean = draw.get("mean")
    if mean is None or not (
        FRAILTY_MEAN_BAND[0] <= float(mean) <= FRAILTY_MEAN_BAND[1]
    ):
        failures.append(
            f"frailty_draw.mean {mean} outside the declared "
            f"pinning band {FRAILTY_MEAN_BAND}",
        )
    if float(draw.get("q05", 1.0)) >= float(
        draw.get("q95", 0.0)
    ):
        failures.append(
            "cv > 0 corner has a degenerate draw (q05 >= q95)",
        )


def _day_counts(payload: dict, days: tuple[int, ...]) -> list[float]:
    curve = (payload.get("acquisition_curve") or {}).get(
        "total_by_day",
    ) or {}
    return [float(curve.get(str(d), 0.0)) for d in days]


def _kink_ratio(payload: dict) -> float | None:
    """Post- vs pre-activation daily incidence (days 17-19 vs 13-15)."""
    pre = _day_counts(payload, KINK_PRE_DAYS)
    if sum(pre) <= 0:
        return None
    post = _day_counts(payload, KINK_POST_DAYS)
    return (sum(post) / len(post)) / (sum(pre) / len(pre))


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + shape discriminator + draw echoes."""
    takeoff, vectors = takeoff_split(payloads)
    during = [
        float(p["infections_during_quarantine"]) for p in takeoff
        if p.get("infections_during_quarantine") is not None
    ]
    before = [
        float(p["infections_before_quarantine"]) for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    kinks = [k for p in takeoff if (k := _kink_ratio(p)) is not None]
    during_role: Counter[str] = Counter()
    during_zone: Counter[str] = Counter()
    for p in takeoff:
        during_role.update(p.get("during_quarantine_by_role") or {})
        during_zone.update(p.get("during_quarantine_by_zone_class") or {})

    draw_means = [
        float(p["frailty_draw"]["mean"]) for p in takeoff
        if (p.get("frailty_draw") or {}).get("mean") is not None
    ]
    draw_spreads = [
        float(p["frailty_draw"]["q95"]) - float(p["frailty_draw"]["q05"])
        for p in takeoff
        if (p.get("frailty_draw") or {}).get("q95") is not None
    ]
    draw_n = [
        float(p["frailty_draw"]["n"]) for p in takeoff
        if (p.get("frailty_draw") or {}).get("n") is not None
    ]

    med_during = quantile(during, 0.5)
    med_before = quantile(before, 0.5)
    dominant = (
        med_during is not None and med_before is not None
        and med_during > med_before
    )
    legs = anchor_legs(len(takeoff), vectors["t_inf"], vectors["t_share"])
    return {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "fizzle_majority": len(takeoff) * 2 < len(payloads),
        "recorded_onsets": band_stats(vectors["rec"]),
        "takeoff_recorded_onsets": band_stats(vectors["t_rec"]),
        "takeoff_infections_total": band_stats(vectors["t_inf"]),
        "takeoff_before_share": band_stats(vectors["t_share"]),
        "truth_leg_in_band": legs["truth_leg_in_band"],
        "timing_leg_in_band": legs["timing_leg_in_band"],
        "both_legs": legs["both_legs"],
        "during_quarantine": band_stats(during),
        "during_dominant": bool(dominant and legs["enough_takeoff"]),
        "kink_ratio": {
            "median": quantile(kinks, 0.5),
            "fraction_below_threshold": (
                sum(k < KINK_RATIO_THRESHOLD for k in kinks) / len(kinks)
                if kinks else None
            ),
        },
        "frailty_draw_mean": band_stats(draw_means),
        "frailty_draw_spread_q95_q05": {"median": quantile(draw_spreads, 0.5)},
        "frailty_draw_n": {"median": quantile(draw_n, 0.5)},
        "during_quarantine_by_role_pooled": dict(during_role),
        "during_quarantine_by_zone_class_pooled": dict(during_zone),
        "row_extra": (
            f"dur {_fmt(med_during)} "
            f"kink {_fmt(quantile(kinks, 0.5))} "
            f"fmed {_fmt(quantile(draw_means, 0.5))} "
            f"fn {_fmt(quantile(draw_n, 0.5))}"
        ),
    }


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def _before_share(payload: dict) -> float | None:
    rec = float(payload["observables"]["recorded_onsets"])
    if rec <= 0:
        return None
    return float(payload["observables"]["onsets_before_split_day"]) / rec


def _paired_delta_row(
    theta: float, arm_id: str, row: list[dict], base: list[dict],
) -> dict:
    """Seed-paired (arm - D0) deltas on the scored observables.

    The shared RNG stream is untouched by the arm, so the pairing is
    draw-matched — deltas are exact per-seed, not ensemble-level.
    """
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
        if int(p["observables"]["recorded_onsets"]) >= 10
    }
    deltas: dict[str, list[float]] = {
        "recorded_onsets": [],
        "before_share": [],
        "infections_total": [],
    }
    for p in row:
        cell = p.get("cell") or {}
        seed = int(cell.get("seed"))
        b = base_by_seed.get(seed)
        if b is None:
            continue
        if int(p["observables"]["recorded_onsets"]) < 10:
            continue
        deltas["recorded_onsets"].append(
            float(p["observables"]["recorded_onsets"])
            - float(b["observables"]["recorded_onsets"])
        )
        arm_share = _before_share(p)
        base_share = _before_share(b)
        if arm_share is not None and base_share is not None:
            deltas["before_share"].append(arm_share - base_share)
        if p.get("infections_total") is not None and (
            b.get("infections_total") is not None
        ):
            deltas["infections_total"].append(
                float(p["infections_total"]) - float(b["infections_total"])
            )
    return {
        "theta": theta,
        "arm_id": arm_id,
        "n_paired": len(deltas["recorded_onsets"]),
        **{
            f"delta_{k}": band_stats(v) for k, v in deltas.items()
        },
    }


def _inert_identity(
    theta: float, row: list[dict], base: list[dict],
) -> dict:
    """The bit-identity audit: FRAIL_INERT vs D0 per seed, exact.

    The cv 0 corner multiplies the hazard by exactly 1.0 and consumes
    zero draws on the shared stream, so every per-seed outcome must equal
    D0's. Any divergence is a wiring defect and voids every armed read.
    """
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
    }
    diverged: list[int] = []
    max_abs: dict[str, float] = {
        "recorded_onsets": 0.0,
        "infections_total": 0.0,
        "before_share": 0.0,
    }
    for p in row:
        seed = int(p["cell"]["seed"])
        b = base_by_seed.get(seed)
        if b is None:
            diverged.append(seed)
            continue
        diffs = {
            "recorded_onsets": abs(
                float(p["observables"]["recorded_onsets"])
                - float(b["observables"]["recorded_onsets"])
            ),
            "infections_total": abs(
                float(p.get("infections_total") or 0.0)
                - float(b.get("infections_total") or 0.0)
            ),
            "before_share": abs(
                (_before_share(p) or 0.0) - (_before_share(b) or 0.0)
            ),
        }
        for key, d in diffs.items():
            max_abs[key] = max(max_abs[key], d)
        if any(d > 0.0 for d in diffs.values()):
            diverged.append(seed)
    return {
        "theta": theta,
        "n_seeds": len(row),
        "identical": not diverged,
        "diverged_seeds": diverged,
        "max_abs_delta": max_abs,
    }


def _paired_rows(rows: dict[tuple, list[dict]]) -> dict:
    """Seed-paired deltas vs D0 + the inert-corner identity audit."""
    out: dict[str, Any] = {}
    for (theta, arm_id), row in sorted(rows.items()):
        if arm_id == BASELINE_ARM:
            continue
        base = rows.get((theta, BASELINE_ARM)) or []
        out[f"theta={theta:.4g}|arm={arm_id}"] = _paired_delta_row(
            theta, arm_id, row, base,
        )
        if arm_id == INERT_ARM:
            out["inert_identity"] = _inert_identity(theta, row, base)
    return out


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """The report-immediately rows."""
    kinds = [
        name
        for name, on in (
            ("TRUTH-IN-BAND", stats["truth_leg_in_band"]),
            ("TIMING-IN-BAND", stats["timing_leg_in_band"]),
            ("FIZZLE-MAJORITY", stats["fizzle_majority"]),
            ("DURING-DOMINANT", stats["during_dominant"]),
        )
        if on
    ]
    if not kinds:
        return None
    return {
        "theta": theta, "arm_id": arm_id, "triggers": kinds,
        "takeoff_infections_total": stats["takeoff_infections_total"],
        "takeoff_before_share": stats["takeoff_before_share"],
        "during_quarantine": stats["during_quarantine"],
        "kink_ratio": stats["kink_ratio"],
        "frailty_draw_mean": stats["frailty_draw_mean"],
    }


def main(argv: list[str] | None = None) -> int:
    design = load_design(
        resolve_design_arg(argv, REPO_ROOT), repo_root=REPO_ROOT,
    )
    return run_readout(
        argv,
        repo_root=REPO_ROOT,
        cells=enumerate_cells(design),
        declared_by_arm={
            arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
        },
        audit_cell=audit_cell,
        row_stats=_row_stats,
        report_key="triggered_rows",
        row_triggers=_row_triggers,
        paired_rows=_paired_rows,
    )


if __name__ == "__main__":
    raise SystemExit(main())
