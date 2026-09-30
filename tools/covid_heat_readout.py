"""HEAT-V1 readout: delivery audit echoes + the both-legs test + route
decomposition per (theta, arm).

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_heat_v1`` and reports, per (theta, arm) row:

* the delivery-machinery audit (payload.delivery echo vs the arm's
  declared constants — airborne_half_life_hours, the merged
  route_efficiency_multipliers map, pathogen_pool_transport, the
  exposure_cap block + engine-active flag, activity_contacts — plus the
  constant-geometry seed_ring check and REF_M0P56's channel echoes),
* takeoff-seed medians and q05-q95 of recorded_onsets, infections_total
  and before_share (the two anchors: 197 / 0.173 vs the H5 band
  [712, 960]),
* the route decomposition: aboard_window_by_route and
  during_quarantine_by_route / by_zone_class / by_role pooled over
  takeoff seeds, the quarantine stratum shares, and the day-16 onset
  kink (recorded onsets days 13-15 vs 16-18),
* the report-immediately triggers: in-band truth/timing landings, rows
  fizzling on more than half the seeds (takeoff < 5), and rows where
  during-quarantine infections become the dominant stratum.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell. The audit+score CLI skeleton is shared with the other conditioned
readouts in tools/covid_screen_readout.py.
"""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation_utils.paths import repo_root  # noqa: E402
from tools import covid_screen_readout as _common  # noqa: E402

REPO_ROOT = repo_root()

TAKEOFF_MIN_ONSETS = _common.TAKEOFF_MIN_ONSETS
T1_RECORDED = _common.T1_RECORDED
T1_BEFORE_SHARE = _common.T1_BEFORE_SHARE
BEFORE_SHARE_TOL = _common.BEFORE_SHARE_TOL
H5_BAND = _common.H5_BAND
MIN_TAKEOFF_SEEDS = _common.MIN_TAKEOFF_SEEDS

_q = _common.q

# Shipped delivery constants (data/pathogens/active_profiles.json
# sars_cov2_resp + crusher_labs/config.yaml, verified at design time).
# The D0_declared echo audits these against whatever the image shipped.
SHIPPED_HALF_LIFE_HOURS = 1.1
SHIPPED_ROUTE_EFFICIENCIES = {
    "direct_contact": 0.25,
    "droplet": 0.3,
    "hvac_airborne": 0.3,
    "fomite": 0.1,
    "food_contamination": 0.0,
    "environmental_source": 0.05,
}
SHIPPED_POOL_TRANSPORT = "airflow"
# crusher_labs/config.yaml ships transmission.activity_contacts enabled:true
# with this authored CONTACT-ARCH-01 unit table -- so the resolved table is
# the shipped default, not a null, on every arm that leaves the block alone.
SHIPPED_ACTIVITY_RATES = {
    "cabin": 0.25,
    "corridor": 0.25,
    "work_service": 2.9,
    "work_other": 0.5,
    "dining_table": 2.0,
    "dining_venue": 2.0,
    "leisure": 1.0,
    "other": 0.0,
}
# The record's seed geometry is constant on this design (no seed_patch).
RECORD_SEED_SPEC = {"count": 1, "onset_day": -1.0, "role": "passenger"}
KINK_PRE_DAYS = (13, 14, 15)
KINK_POST_DAYS = (16, 17, 18)


def _declared(arm: dict) -> dict:
    """The arm's declared delivery constants + channel expectations."""
    ov = arm.get("overrides") or {}
    patho = (ov.get("pathogen_overrides") or {}).get("sars_cov2_resp", {})
    tx = ov.get("transmission_overrides") or {}
    om = patho.get("observation_model", {})
    route_eff = dict(SHIPPED_ROUTE_EFFICIENCIES)
    route_eff.update(ov.get("profile_route_efficiency_multipliers") or {})
    return {
        "half_life": float(
            patho.get("airborne_half_life_hours", SHIPPED_HALF_LIFE_HOURS)
        ),
        "route_eff": route_eff,
        "pool_transport": ov.get(
            "pathogen_pool_transport", SHIPPED_POOL_TRANSPORT
        ),
        "exposure_cap": dict(tx.get("exposure_cap") or {}),
        "activity_contacts": _expected_contacts(tx),
        "onset_recording": om.get("onset_recording"),
        "eligibility": om.get("syndrome_case_eligibility_by_severity"),
    }


def _expected_contacts(tx: dict) -> dict | None:
    """The arm's expected resolved activity_contacts rates table.

    Block absent -> the shipped unit table (enabled:true in shipped
    config); enabled:false -> None; enabled:true -> the declared rates.
    """
    block = tx.get("activity_contacts")
    if not block:
        return dict(SHIPPED_ACTIVITY_RATES)
    if not bool(block.get("enabled", False)):
        return None
    return dict(block.get("rates_per_hour") or {})


def _audit_seed_echoes(ring: dict) -> list[str]:
    """seed_spec echoes the record's seed on every arm (no seed_patch)."""
    failures: list[str] = []
    spec = ring.get("seed_spec") or {}
    for key, want in RECORD_SEED_SPEC.items():
        if spec.get(key) != want:
            failures.append(
                f"seed_spec.{key} {spec.get(key)} != record {want}"
            )
    if ring.get("seeded_count") != RECORD_SEED_SPEC["count"]:
        failures.append(
            f"seeded_count {ring.get('seeded_count')} "
            f"!= record {RECORD_SEED_SPEC['count']}",
        )
    bad = [
        h for h in ring.get("seeded_hosts") or []
        if h.get("role") != RECORD_SEED_SPEC["role"]
    ]
    if bad:
        failures.append(
            f"{len(bad)} seeded host(s) with role outside "
            f"{RECORD_SEED_SPEC['role']!r}",
        )
    return failures


def _audit_delivery_echoes(payload: dict, declared: dict) -> list[str]:
    """payload.delivery vs the arm's declared delivery constants."""
    failures: list[str] = []
    delivery = payload.get("delivery")
    if not isinstance(delivery, dict):
        return ["missing delivery echo block"]

    got_hl = delivery.get("airborne_half_life_hours")
    if got_hl is None or abs(float(got_hl) - declared["half_life"]) > 1e-9:
        failures.append(
            f"delivery.airborne_half_life_hours {got_hl} "
            f"!= declared {declared['half_life']}",
        )
    got_eff = {
        str(k): float(v) for k, v in (
            delivery.get("route_efficiency_multipliers") or {}
        ).items()
    }
    if got_eff != declared["route_eff"]:
        failures.append(
            f"delivery.route_efficiency_multipliers {got_eff} "
            f"!= declared {declared['route_eff']}",
        )
    if delivery.get("pathogen_pool_transport") != declared["pool_transport"]:
        failures.append(
            f"delivery.pathogen_pool_transport "
            f"{delivery.get('pathogen_pool_transport')} "
            f"!= declared {declared['pool_transport']}",
        )
    cap = delivery.get("exposure_cap") or {}
    if cap != declared["exposure_cap"]:
        failures.append(
            f"delivery.exposure_cap {cap} != declared "
            f"{declared['exposure_cap']}",
        )
    # On this catalogued hull the engine-active flag must track the
    # resolved enabled bit (shipped true; explicit false on CAP_OFF).
    want_active = bool(cap.get("enabled", True))
    if bool(delivery.get("exposure_cap_active")) != want_active:
        failures.append(
            f"delivery.exposure_cap_active "
            f"{delivery.get('exposure_cap_active')} != resolved "
            f"{want_active}",
        )
    got_contacts = delivery.get("activity_contacts")
    want_rates = declared["activity_contacts"]
    if want_rates is None:
        if got_contacts is not None:
            failures.append(
                "delivery.activity_contacts present on an arm whose "
                "declared block resolves to None",
            )
    else:
        got_rates = got_contacts or {}
        for act, want in want_rates.items():
            got = got_rates.get(act)
            per_role_ok = isinstance(got, dict) and all(
                abs(float(v) - float(want)) < 1e-9 for v in got.values()
            )
            scalar_ok = isinstance(got, (int, float)) and (
                abs(float(got) - float(want)) < 1e-9
            )
            if not (per_role_ok or scalar_ok):
                failures.append(
                    f"delivery.activity_contacts.{act} {got} "
                    f"!= declared {want}",
                )
    return failures


def _audit_channel_echoes(payload: dict, declared: dict) -> list[str]:
    """exposure-cap flag echo and the REF arm's channel echoes."""
    failures: list[str] = []
    want_fr = (declared["exposure_cap"] or {}).get("include_fixed_rings")
    if payload.get("exposure_cap_include_fixed_rings") != want_fr:
        failures.append(
            "exposure_cap_include_fixed_rings "
            f"{payload.get('exposure_cap_include_fixed_rings')} "
            f"!= declared {want_fr}",
        )
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


def audit_cell(payload: dict, declared: dict) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    ring = payload.get("seed_ring")
    failures = (
        ["missing seed_ring block"]
        if not isinstance(ring, dict)
        else _audit_seed_echoes(ring)
    )
    return (
        failures
        + _audit_delivery_echoes(payload, declared)
        + _audit_channel_echoes(payload, declared)
    )


def _pooled_counter(payloads: list[dict], *keys: str) -> dict[str, int]:
    """Sum a nested counter field across takeoff-seed payloads."""
    pooled: Counter[str] = Counter()
    for p in payloads:
        node = p
        for key in keys:
            node = (node or {}).get(key)
        for route, count in (node or {}).items():
            pooled[str(route)] += int(count)
    return dict(pooled)


def _kink_stats(payloads: list[dict]) -> dict:
    """Recorded onset kink at the SOP-017 boundary: per-seed mean daily
    recorded onsets on days 13-15 vs 16-18, and the post/pre ratio."""
    pre_vals: list[float] = []
    post_vals: list[float] = []
    ratios: list[float] = []
    for p in payloads:
        curve = p.get("onset_curve") or {}

        def _mean(days: tuple[int, ...]) -> float:
            total = sum(
                sum((curve.get(str(d)) or {}).values()) for d in days
            )
            return float(total) / len(days)

        pre = _mean(KINK_PRE_DAYS)
        post = _mean(KINK_POST_DAYS)
        pre_vals.append(pre)
        post_vals.append(post)
        if pre > 0:
            ratios.append(post / pre)
    return {
        "pre_mean_daily_med": _q(pre_vals, 0.5),
        "post_mean_daily_med": _q(post_vals, 0.5),
        "post_over_pre_med": _q(ratios, 0.5),
        "post_over_pre_q05": _q(ratios, 0.05),
        "post_over_pre_q95": _q(ratios, 0.95),
    }


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians/quantiles + route decomposition for
    one (theta, arm) row."""
    split = _common.takeoff_split(payloads)
    takeoff = split["takeoff"]
    t_before = [
        float(p["infections_before_quarantine"]) for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    t_during = [
        float(p["infections_during_quarantine"]) for p in takeoff
        if p.get("infections_during_quarantine") is not None
    ]
    t_during_share = [
        float(p["infections_during_quarantine"])
        / float(p["infections_total"])
        for p in takeoff
        if p.get("infections_during_quarantine") is not None
        and p.get("infections_total")
    ]
    med_before = _q(t_before, 0.5)
    med_during = _q(t_during, 0.5)
    stats = _common.scored_row(split)
    stats["fizzled_over_half"] = stats["takeoff_n"] < MIN_TAKEOFF_SEEDS
    stats["strata"] = {
        "infections_before_quarantine_med": med_before,
        "infections_during_quarantine_med": med_during,
        "during_share_med": _q(t_during_share, 0.5),
        "during_dominant": bool(
            med_during is not None
            and med_before is not None
            and med_during > med_before
        ),
    }
    stats["route_decomposition"] = {
        "aboard_window_by_route_pooled": _pooled_counter(
            takeoff, "seed_ring", "aboard_window_by_route",
        ),
        "during_quarantine_by_route_pooled": _pooled_counter(
            takeoff, "during_quarantine_by_route",
        ),
        "during_quarantine_by_zone_class_pooled": _pooled_counter(
            takeoff, "during_quarantine_by_zone_class",
        ),
        "during_quarantine_by_role_pooled": _pooled_counter(
            takeoff, "during_quarantine_by_role",
        ),
    }
    stats["day16_kink"] = _kink_stats(takeoff)
    return stats


def _row_line(stats: dict) -> str:
    ti = stats["takeoff_infections_total"]
    ts = stats["takeoff_before_share"]
    tr = stats["takeoff_recorded_onsets"]
    flags = []
    if stats["truth_leg_in_band"]:
        flags.append("TRUTH-IN-BAND")
    if stats["timing_leg_in_band"]:
        flags.append("TIMING-IN-BAND")
    if stats["fizzled_over_half"]:
        flags.append("FIZZLE>HALF")
    if stats["strata"]["during_dominant"]:
        flags.append("DURING-DOMINANT")
    med = _common.med
    return (
        f"takeoff {stats['takeoff_n']}/{stats['n']} "
        f"rec med {med(tr['median'])} "
        f"[{med(tr['q05'])},{med(tr['q95'])}] "
        f"inf med {med(ti['median'])} "
        f"[{med(ti['q05'])},{med(ti['q95'])}] "
        f"bshr med {med(ts['median'])} "
        f"during-share {med(stats['strata']['during_share_med'])} "
        f"{' '.join(flags)}"
    )


def _collect(report: dict, theta: float, arm_id: str, stats: dict) -> None:
    report.setdefault("in_band_landings", [])
    report.setdefault("fizzle_rows", [])
    report.setdefault("during_dominant_rows", [])
    label = f"theta={theta:.4g}|arm={arm_id}"
    if stats["truth_leg_in_band"] or stats["timing_leg_in_band"]:
        report["in_band_landings"].append(
            {
                "theta": theta, "arm_id": arm_id,
                "truth_leg_in_band": stats["truth_leg_in_band"],
                "timing_leg_in_band": stats["timing_leg_in_band"],
                "takeoff_infections_total": (
                    stats["takeoff_infections_total"]
                ),
                "takeoff_before_share": stats["takeoff_before_share"],
            },
        )
    if stats["fizzled_over_half"]:
        report["fizzle_rows"].append(label)
    if stats["strata"]["during_dominant"]:
        report["during_dominant_rows"].append(label)


def main(argv: list[str] | None = None) -> int:
    report = _common.run_readout(
        argv,
        root=REPO_ROOT,
        description=__doc__,
        declared_fn=_declared,
        audit_fn=audit_cell,
        row_stats_fn=_row_stats,
        row_line_fn=_row_line,
        collect_fn=_collect,
    )
    if report is None:
        return 2
    _common.print_extras(
        report,
        ["in_band_landings", "fizzle_rows", "during_dominant_rows"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
