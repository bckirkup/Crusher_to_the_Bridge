"""SUSCEPT-V1 readout: susceptibility-arm audit + the both-legs test.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_suscept_v1`` and reports, per (theta, arm) row:

* the susceptibility-structure audit (payload echo vs the arm's declared
  values — ship_graph_immune declared/resolved/realized, dose_response
  alpha/beta/susceptibility_scale at the cell's theta, exposure_cap
  flags, susceptibility_draw and acquisition_curve presence, and the
  REF_M0P56 channel echoes),
* the suppression discriminator: during-quarantine stratum sizes and
  pooled role/zone/route splits, the confined-passenger count, and the
  day-16 kink ratio (mean daily acquisitions days 17-19 vs days 13-15 —
  collapsing toward 0 marks a suppression-shaped landing; tracking the
  baseline's own decline marks structure-shaped attenuation),
* the extended report-immediately triggers: truth or timing medians in
  band, fizzle-majority rows (takeoff on fewer than half the seeds), and
  during-quarantine-dominant rows.
"""

from __future__ import annotations

import os
import sys
from collections import Counter

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

# The frailty arm convention: beta fixed at the profile value and the
# theta-preserved scale the arm writes (theta*(alpha+beta)/alpha).
SHIPPED_ALPHA = 0.18
SHIPPED_BETA = 58.0
KINK_PRE_DAYS = (13, 14, 15)
KINK_POST_DAYS = (17, 18, 19)
KINK_RATIO_THRESHOLD = 0.5


def _declared(arm: dict) -> dict:
    """The arm's declared susceptibility structure + channel blocks."""
    ov = arm.get("overrides") or {}
    sg = ov.get("ship_graph_overrides") or {}
    frailty = ov.get("dose_response_frailty") or {}
    cap = (ov.get("transmission_overrides") or {}).get("exposure_cap")
    om = (
        (ov.get("pathogen_overrides") or {})
        .get("sars_cov2_resp", {})
        .get("observation_model", {})
    )
    return {
        # The fit pins immune_fraction 0.0; a pooled arm declares only
        # the depth and leaves crew_immune_fraction absent (role-blind).
        "immune_fraction": float(sg.get("immune_fraction", 0.0)),
        "crew_immune_fraction": sg.get("crew_immune_fraction"),
        "frailty_alpha": float(frailty.get("alpha", SHIPPED_ALPHA)),
        "frailty_beta": float(frailty.get("beta", SHIPPED_BETA)),
        "frailty_arm": bool(frailty),
        "cap_enabled": True if cap is None else bool(cap.get("enabled", True)),
        "include_fixed_rings": (
            None if cap is None else cap.get("include_fixed_rings")
        ),
        "onset_recording": om.get("onset_recording"),
        "eligibility": om.get("syndrome_case_eligibility_by_severity"),
    }


def _audit_immune_echo(payload: dict, declared: dict) -> list[str]:
    """ship_graph_immune declared/resolved/realized vs the arm."""
    block = payload.get("ship_graph_immune")
    if not isinstance(block, dict):
        return ["missing ship_graph_immune block"]
    failures: list[str] = []
    dec = block.get("declared") or {}
    res = block.get("resolved") or {}
    for key in ("immune_fraction", "crew_immune_fraction"):
        if dec.get(key) != declared[key]:
            failures.append(
                f"ship_graph_immune.declared.{key} {dec.get(key)} "
                f"!= declared {declared[key]}",
            )
        resolved_key = (
            "crew_immune_ratio" if key == "crew_immune_fraction"
            else "immune_ratio"
        )
        if res.get(resolved_key) != declared[key]:
            failures.append(
                f"ship_graph_immune.resolved.{resolved_key} "
                f"{res.get(resolved_key)} != declared {declared[key]}",
            )
    realized = block.get("realized") or {}
    failures.extend(_audit_realized(
        realized.get("by_role") or {},
        realized.get("complement_by_role") or {},
        declared,
    ))
    return failures


def _audit_realized(
    by_role: dict, complement: dict, declared: dict,
) -> list[str]:
    """Realized draw counts must match the declared pool share."""
    if declared["crew_immune_fraction"] is not None:
        expected = {
            "passenger": int(complement.get("passenger", 0)
                             * declared["immune_fraction"]),
            "crew": int(complement.get("crew", 0)
                        * declared["crew_immune_fraction"]),
        }
        return [
            f"ship_graph_immune.realized.by_role.{role} "
            f"{by_role.get(role, 0)} != pool share {want}"
            for role, want in expected.items()
            if by_role.get(role, 0) != want
        ]
    total = sum(by_role.values())
    want = int(sum(complement.values()) * declared["immune_fraction"])
    if total != want:
        return [
            f"ship_graph_immune realized total {total} "
            f"!= pool share {want}",
        ]
    return []


def _audit_frailty_echo(
    payload: dict, declared: dict, theta: float,
) -> list[str]:
    """dose_response echo + susceptibility_draw on every arm."""
    failures: list[str] = []
    dr = payload.get("dose_response") or {}
    if dr.get("model") != "beta_poisson":
        failures.append(f"dose_response.model {dr.get('model')!r}")
    alpha = declared["frailty_alpha"]
    beta = declared["frailty_beta"]
    want_scale = theta * (alpha + beta) / alpha
    if abs(float(dr.get("alpha", -1)) - alpha) > 1e-9:
        failures.append(
            f"dose_response.alpha {dr.get('alpha')} != declared {alpha}",
        )
    if abs(float(dr.get("beta", -1)) - beta) > 1e-9:
        failures.append(
            f"dose_response.beta {dr.get('beta')} != declared {beta}",
        )
    scale = float(dr.get("susceptibility_scale", -1.0))
    if scale <= 0 or abs(scale - want_scale) / want_scale > 1e-6:
        failures.append(
            f"dose_response.susceptibility_scale {scale} "
            f"!= theta-preserved {want_scale:.4g}",
        )
    draw = payload.get("susceptibility_draw") or {}
    if not draw.get("n"):
        failures.append("susceptibility_draw empty — no challenged hosts")
    elif not 0.0 < float(draw.get("mean", -1)) <= scale * 1.001:
        failures.append(
            f"susceptibility_draw.mean {draw.get('mean')} "
            f"outside (0, {scale:.4g}]",
        )
    return failures


def _audit_cap_echo(payload: dict, declared: dict) -> list[str]:
    """Resolved cap state + declared ring-inclusion flag."""
    failures: list[str] = []
    if bool(payload.get("exposure_cap_active")) != declared["cap_enabled"]:
        failures.append(
            f"exposure_cap_active {payload.get('exposure_cap_active')} "
            f"!= declared enabled {declared['cap_enabled']}",
        )
    if payload.get("exposure_cap_include_fixed_rings") != (
        declared["include_fixed_rings"]
    ):
        failures.append(
            "exposure_cap_include_fixed_rings "
            f"{payload.get('exposure_cap_include_fixed_rings')} "
            f"!= declared {declared['include_fixed_rings']}",
        )
    return failures


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    curve = payload.get("acquisition_curve")
    curve_ok = (
        isinstance(curve, dict)
        and isinstance(curve.get("total_by_day"), dict)
        and isinstance(curve.get("confined_by_day"), dict)
    )
    failures = [] if curve_ok else ["missing acquisition_curve block"]
    failures += _audit_immune_echo(payload, declared)
    failures += _audit_frailty_echo(payload, declared, theta)
    failures += _audit_cap_echo(payload, declared)
    if declared["onset_recording"] is not None and (
        payload.get("onset_recording") != declared["onset_recording"]
    ):
        failures.append("onset_recording echo != declared block")
    if declared["eligibility"] is not None and (
        payload.get("onset_eligibility_by_severity")
        != declared["eligibility"]
    ):
        failures.append(
            "onset_eligibility_by_severity echo != declared ladder",
        )
    return failures


def _day_counts(payload: dict, days: tuple[int, ...]) -> list[float]:
    curve = (payload.get("acquisition_curve") or {}).get("total_by_day") or {}
    return [float(curve.get(str(d), 0.0)) for d in days]


def _kink_ratio(payload: dict) -> float | None:
    """Post- vs pre-activation daily incidence (days 17-19 vs 13-15)."""
    pre = _day_counts(payload, KINK_PRE_DAYS)
    if sum(pre) <= 0:
        return None
    post = _day_counts(payload, KINK_POST_DAYS)
    return (sum(post) / len(post)) / (sum(pre) / len(pre))


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + the suppression discriminator."""
    takeoff, vectors = takeoff_split(payloads)
    during = [
        float(p["infections_during_quarantine"]) for p in takeoff
        if p.get("infections_during_quarantine") is not None
    ]
    before = [
        float(p["infections_before_quarantine"]) for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    confined = [
        float(p["confined_passenger_infections_during_quarantine"])
        for p in takeoff
        if p.get("confined_passenger_infections_during_quarantine")
        is not None
    ]
    kinks = [k for p in takeoff if (k := _kink_ratio(p)) is not None]
    during_role: Counter[str] = Counter()
    during_zone: Counter[str] = Counter()
    during_route: Counter[str] = Counter()
    for p in takeoff:
        during_role.update(p.get("during_quarantine_by_role") or {})
        during_zone.update(p.get("during_quarantine_by_zone_class") or {})
        during_route.update(p.get("during_quarantine_by_route") or {})

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
        "before_share": {"median": quantile(vectors["shares"], 0.5)},
        "takeoff_recorded_onsets": band_stats(vectors["t_rec"]),
        "takeoff_infections_total": band_stats(vectors["t_inf"]),
        "takeoff_before_share": band_stats(vectors["t_share"]),
        "truth_leg_in_band": legs["truth_leg_in_band"],
        "timing_leg_in_band": legs["timing_leg_in_band"],
        "both_legs": legs["both_legs"],
        "during_quarantine": band_stats(during),
        "during_dominant": bool(dominant and legs["enough_takeoff"]),
        "confined_during_quarantine": {
            "median": quantile(confined, 0.5),
            "q95": quantile(confined, 0.95),
        },
        "kink_ratio": {
            "median": quantile(kinks, 0.5),
            "fraction_below_threshold": (
                sum(k < KINK_RATIO_THRESHOLD for k in kinks) / len(kinks)
                if kinks else None
            ),
        },
        "during_quarantine_by_role_pooled": dict(during_role),
        "during_quarantine_by_zone_class_pooled": dict(during_zone),
        "during_quarantine_by_route_pooled": dict(during_route),
        "row_extra": (
            f"during med {_fmt(med_during)} "
            f"kink {_fmt(quantile(kinks, 0.5))}"
        ),
    }


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """The report-immediately rows: in-band, fizzle, during-dominant."""
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
