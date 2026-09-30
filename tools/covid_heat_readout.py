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
  takeoff seeds, the quarantine stratum sizes, and the day-16 onset
  kink (mean daily recorded onsets days 13-15 vs 16-18 — a softened
  kink means the cooling arm shifts incidence earlier rather than
  clipping the tail),
* the report-immediately triggers: in-band truth/timing landings,
  fizzle-majority rows (takeoff on fewer than half the seeds), and
  during-quarantine-dominant rows.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell. The audit+score CLI skeleton is shared with the other conditioned
readouts in tools/covid_screen_readout_common.py.
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
# crusher_labs/config.yaml ships transmission.activity_contacts
# enabled:true with this authored CONTACT-ARCH-01 unit table -- so the
# resolved table is the shipped default, not a null, on every arm that
# leaves the block alone.
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


def _audit_contact_rates(
    got_contacts: dict | None, want_rates: dict | None,
) -> list[str]:
    """activity_contacts echo vs the arm's expected resolved table."""
    if want_rates is None:
        if got_contacts is not None:
            return [
                "delivery.activity_contacts present on an arm whose "
                "declared block resolves to None",
            ]
        return []
    got_rates = got_contacts or {}
    failures: list[str] = []
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
    return failures + _audit_contact_rates(
        delivery.get("activity_contacts"), declared["activity_contacts"],
    )


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


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
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


def _kink_ratio(p: dict) -> float | None:
    """Post/pre mean daily recorded onsets across the day-16 SOP-017
    boundary for one takeoff seed (None when pre-window is silent)."""
    curve = p.get("onset_curve") or {}

    def _mean(days: tuple[int, ...]) -> float:
        total = sum(
            sum((curve.get(str(d)) or {}).values()) for d in days
        )
        return float(total) / len(days)

    pre = _mean(KINK_PRE_DAYS)
    post = _mean(KINK_POST_DAYS)
    if pre <= 0:
        return None
    return post / pre


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + route decomposition for one row."""
    takeoff, vectors = takeoff_split(payloads)
    during = [
        float(p["infections_during_quarantine"]) for p in takeoff
        if p.get("infections_during_quarantine") is not None
    ]
    before = [
        float(p["infections_before_quarantine"]) for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    during_share = [
        float(p["infections_during_quarantine"])
        / float(p["infections_total"])
        for p in takeoff
        if p.get("infections_during_quarantine") is not None
        and p.get("infections_total")
    ]
    aboard_route: Counter[str] = Counter()
    during_route: Counter[str] = Counter()
    during_zone: Counter[str] = Counter()
    during_role: Counter[str] = Counter()
    kinks = [k for p in takeoff if (k := _kink_ratio(p)) is not None]
    for p in takeoff:
        aboard_route.update(
            (p.get("seed_ring") or {}).get("aboard_window_by_route") or {}
        )
        during_route.update(p.get("during_quarantine_by_route") or {})
        during_zone.update(
            p.get("during_quarantine_by_zone_class") or {}
        )
        during_role.update(p.get("during_quarantine_by_role") or {})

    med_during = quantile(during, 0.5)
    med_before = quantile(before, 0.5)
    med_share = quantile(during_share, 0.5)
    med_kink = quantile(kinks, 0.5)
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
        "infections_before_quarantine": band_stats(before),
        "during_quarantine": band_stats(during),
        "during_share": {"median": med_share},
        "during_dominant": bool(dominant and legs["enough_takeoff"]),
        "day16_kink": {
            "post_over_pre_median": med_kink,
            "post_over_pre_q05": quantile(kinks, 0.05),
            "post_over_pre_q95": quantile(kinks, 0.95),
        },
        "aboard_window_by_route_pooled": dict(aboard_route),
        "during_quarantine_by_route_pooled": dict(during_route),
        "during_quarantine_by_zone_class_pooled": dict(during_zone),
        "during_quarantine_by_role_pooled": dict(during_role),
        "row_extra": (
            f"during med {_fmt(med_during)} "
            f"share {_fmt(med_share)} kink {_fmt(med_kink)}"
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
        "day16_kink": stats["day16_kink"],
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
