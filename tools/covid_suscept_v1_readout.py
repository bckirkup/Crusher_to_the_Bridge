"""SUSCEPT-V1 readout: susceptibility-arm audit + the both-legs test.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_suscept_v1`` and reports, per (theta, arm) row:

* the susceptibility-structure audit (payload echo vs the arm's declared
  values — ship_graph_immune declared/resolved/realized, dose_response
  alpha/beta/susceptibility_scale at the cell's theta, exposure_cap
  flags, susceptibility_draw and acquisition_curve presence, and the
  REF_M0P56 channel echoes),
* takeoff-seed medians and q05-q95 of recorded_onsets, infections_total
  and before_share (the two anchors: 197 / 0.173 vs the H5 band
  [712, 960]),
* the suppression discriminator: during-quarantine stratum sizes and
  splits, the day-16 incidence kink ratio (mean daily acquisitions
  days 17-19 vs days 13-15 — a ratio collapsing toward 0 marks a
  suppression-shaped landing; a ratio tracking the baseline's own
  decline marks structure-shaped attenuation),
* the report-immediately triggers: truth median in band, timing median
  in band, fizzle-majority rows (takeoff on fewer than half the seeds),
  and during-quarantine-dominant rows.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    repo_root,
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

REPO_ROOT = repo_root()

TAKEOFF_MIN_ONSETS = 10
T1_RECORDED = 197.0
T1_BEFORE_SHARE = 0.173
BEFORE_SHARE_TOL = 0.10
H5_BAND = (712.0, 960.0)
MIN_TAKEOFF_SEEDS = 5
# The frailty arm convention: beta fixed at the profile value and the
# theta-preserved scale the arm writes (theta*(alpha+beta)/alpha).
SHIPPED_ALPHA = 0.18
SHIPPED_BETA = 58.0
KINK_PRE_DAYS = (13, 14, 15)
KINK_POST_DAYS = (17, 18, 19)
KINK_RATIO_THRESHOLD = 0.5


def _q(values: list[float], p: float) -> float | None:
    if not values:
        return None
    srt = sorted(values)
    i = min(len(srt) - 1, max(0, int(round(p * (len(srt) - 1)))))
    return float(srt[i])


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
    realized = (block.get("realized") or {})
    by_role = realized.get("by_role") or {}
    complement = realized.get("complement_by_role") or {}
    crew_split = declared["crew_immune_fraction"] is not None
    if crew_split:
        expected = {
            "passenger": int(complement.get("passenger", 0)
                             * declared["immune_fraction"]),
            "crew": int(complement.get("crew", 0)
                        * declared["crew_immune_fraction"]),
        }
        for role, want in expected.items():
            if by_role.get(role, 0) != want:
                failures.append(
                    f"ship_graph_immune.realized.by_role.{role} "
                    f"{by_role.get(role, 0)} != pool share {want}",
                )
    else:
        total = sum(by_role.values())
        want = int(sum(complement.values()) * declared["immune_fraction"])
        if total != want:
            failures.append(
                f"ship_graph_immune realized total {total} "
                f"!= pool share {want}",
            )
    return failures


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
    if not scale > 0 or abs(scale - want_scale) / want_scale > 1e-6:
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
    takeoff = [
        p for p in payloads
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
    ]
    rec = [
        float(p["observables"]["recorded_onsets"]) for p in payloads
    ]
    shares = [
        float(p["observables"]["onsets_before_split_day"])
        / float(p["observables"]["recorded_onsets"])
        for p in payloads
        if int(p["observables"]["recorded_onsets"]) > 0
    ]
    t_rec = [float(p["observables"]["recorded_onsets"]) for p in takeoff]
    t_inf = [
        float(p["infections_total"]) for p in takeoff
        if p.get("infections_total") is not None
    ]
    t_share = [
        float(p["observables"]["onsets_before_split_day"])
        / float(p["observables"]["recorded_onsets"])
        for p in takeoff
    ]
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

    med_inf = _q(t_inf, 0.5)
    med_share = _q(t_share, 0.5)
    med_during = _q(during, 0.5)
    med_before = _q(before, 0.5)
    enough = len(takeoff) >= MIN_TAKEOFF_SEEDS
    in_band = (
        med_inf is not None and H5_BAND[0] <= med_inf <= H5_BAND[1]
    )
    timing_hit = (
        med_share is not None
        and abs(med_share - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL
    )
    dominant = (
        med_during is not None and med_before is not None
        and med_during > med_before
    )
    return {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "fizzle_majority": len(takeoff) * 2 < len(payloads),
        "recorded_onsets": {
            "median": _q(rec, 0.5), "q05": _q(rec, 0.05),
            "q95": _q(rec, 0.95),
        },
        "before_share": {"median": _q(shares, 0.5)},
        "takeoff_recorded_onsets": {
            "median": _q(t_rec, 0.5), "q05": _q(t_rec, 0.05),
            "q95": _q(t_rec, 0.95),
        },
        "takeoff_infections_total": {
            "median": med_inf, "q05": _q(t_inf, 0.05),
            "q95": _q(t_inf, 0.95),
        },
        "takeoff_before_share": {
            "median": med_share, "q05": _q(t_share, 0.05),
            "q95": _q(t_share, 0.95),
        },
        "truth_leg_in_band": bool(in_band and enough),
        "timing_leg_in_band": bool(timing_hit and enough),
        "both_legs": bool(in_band and timing_hit and enough),
        "during_quarantine": {
            "median": med_during, "q05": _q(during, 0.05),
            "q95": _q(during, 0.95),
        },
        "during_dominant": bool(dominant and enough),
        "confined_during_quarantine": {
            "median": _q(confined, 0.5), "q95": _q(confined, 0.95),
        },
        "kink_ratio": {
            "median": _q(kinks, 0.5),
            "fraction_below_threshold": (
                sum(k < KINK_RATIO_THRESHOLD for k in kinks) / len(kinks)
                if kinks else None
            ),
        },
        "during_quarantine_by_role_pooled": dict(during_role),
        "during_quarantine_by_zone_class_pooled": dict(during_zone),
        "during_quarantine_by_route_pooled": dict(during_route),
    }


def _load_payloads(cells_dir: str) -> dict[str, dict]:
    """Read every cell JSON under *cells_dir* (contained to the dir)."""
    payloads: dict[str, dict] = {}
    for name in sorted(os.listdir(cells_dir)):
        if not name.endswith(".json"):
            continue
        path = resolve_child_path(cells_dir, name)
        with validated_open(
            path, allowed_roots=(cells_dir,), encoding="utf-8",
        ) as fh:
            payloads[name] = json.load(fh)
    return payloads


def _audit_all(
    payloads: dict[str, dict],
    cells: list,
    declared_by_arm: dict[str, dict],
) -> tuple[dict[str, list[str]], dict[tuple, list[dict]]]:
    """Audit each payload and bucket by (theta, arm)."""
    by_key = {(c.theta, c.arm_id, c.seed): c for c in cells}
    audit_failures: dict[str, list[str]] = {}
    rows: dict[tuple, list[dict]] = {}
    for name, payload in payloads.items():
        cell = payload.get("cell") or {}
        key = (
            float(cell.get("theta")), cell.get("arm_id"),
            int(cell.get("seed")),
        )
        if key not in by_key:
            audit_failures[name] = ["cell key not in the declared lattice"]
            continue
        declared = declared_by_arm.get(cell.get("arm_id"))
        failures = (
            audit_cell(payload, declared, key[0])
            if declared else [f"unknown arm {cell.get('arm_id')}"]
        )
        if failures:
            audit_failures[name] = failures
        rows.setdefault((key[0], key[1]), []).append(payload)
    return audit_failures, rows


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """The report-immediately rows: in-band, fizzle, during-dominant."""
    kinds = []
    if stats["truth_leg_in_band"]:
        kinds.append("TRUTH-IN-BAND")
    if stats["timing_leg_in_band"]:
        kinds.append("TIMING-IN-BAND")
    if stats["fizzle_majority"]:
        kinds.append("FIZZLE-MAJORITY")
    if stats["during_dominant"]:
        kinds.append("DURING-DOMINANT")
    if not kinds:
        return None
    return {
        "theta": theta, "arm_id": arm_id, "triggers": kinds,
        "takeoff_infections_total": stats["takeoff_infections_total"],
        "takeoff_before_share": stats["takeoff_before_share"],
        "during_quarantine": stats["during_quarantine"],
        "kink_ratio": stats["kink_ratio"],
    }


def _print_rows(report: dict) -> None:
    for label, stats in report["rows"].items():
        ti = stats["takeoff_infections_total"]
        ts = stats["takeoff_before_share"]
        tr = stats["takeoff_recorded_onsets"]
        flags = []
        if stats["truth_leg_in_band"]:
            flags.append("TRUTH-IN-BAND")
        if stats["timing_leg_in_band"]:
            flags.append("TIMING-IN-BAND")
        if stats["fizzle_majority"]:
            flags.append("FIZZLE-MAJORITY")
        if stats["during_dominant"]:
            flags.append("DURING-DOMINANT")

        def med(v: float | None) -> str:
            return "n/a" if v is None else f"{v:.3g}"

        kink = stats["kink_ratio"]["median"]
        print(
            f"  {label}: takeoff {stats['takeoff_n']}/{stats['n']} "
            f"rec med {med(tr['median'])} "
            f"[{med(tr['q05'])},{med(tr['q95'])}] "
            f"inf med {med(ti['median'])} "
            f"[{med(ti['q05'])},{med(ti['q95'])}] "
            f"bshr med {med(ts['median'])} "
            f"during med {med(stats['during_quarantine']['median'])} "
            f"kink {med(kink)} {' '.join(flags)}",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    cells_dir = resolve_repo_path(REPO_ROOT, args.cells)
    design_path = resolve_repo_path(REPO_ROOT, args.design)
    design = load_design(design_path, repo_root=REPO_ROOT)
    cells = enumerate_cells(design)
    declared_by_arm = {
        arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
    }

    payloads = _load_payloads(cells_dir)
    if not args.allow_partial and len(payloads) < len(cells):
        print(
            f"{len(payloads)} of {len(cells)} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return 2

    audit_failures, rows = _audit_all(payloads, cells, declared_by_arm)

    report = {
        "cells_found": len(payloads),
        "cells_expected": len(cells),
        "audit_failures": audit_failures,
        "rows": {},
        "triggered_rows": [],
    }
    for (theta, arm_id), row in sorted(rows.items()):
        stats = _row_stats(row)
        report["rows"][f"theta={theta:.4g}|arm={arm_id}"] = stats
        trigger = _row_triggers(theta, arm_id, stats)
        if trigger:
            report["triggered_rows"].append(trigger)

    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)

    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(audit_failures)} audit failures",
    )
    _print_rows(report)
    if report["triggered_rows"]:
        print("TRIGGERED ROWS:", json.dumps(
            report["triggered_rows"], indent=1,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
