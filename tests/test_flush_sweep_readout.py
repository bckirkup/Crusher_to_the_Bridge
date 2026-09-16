"""Flush-sweep stage-1 readout: graded behaviour and invariants.

Per ci-test-design: no golden outputs. Expectations are the arm-label
refusal (an arm's identity is its archived ``flush_aerosol_fraction``,
never a directory name), archived-fraction ordering of live arms,
baseline-only pairing of contrasts, the flush witness's divide-by-zero
and missing-block handling, and graded sensitivity of the pooled
dose-per-exposure and the paired secondaries contrast.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from telemetry_buffer.observation_model.flush_sweep_readout import (  # noqa: E402
    FLUSH_KEYS,
    _sorted_arms,
    build_report,
    declared_fraction,
    flush_witness,
)
from telemetry_buffer.observation_model.posting_tail_sensitivity import (  # noqa: E402
    MARGIN_KEY,
    MIN_PAIRED_SEEDS,
)

CELL = {
    "platform_id": "classic_cruise_1900",
    "num_agents": 1910,
    "num_epochs": 168,
    "surveillance": "syndromic_comp65",
    "dose_adjustment": 4.0,
    "boarding_mechanism_rung": "reportable",
}

_STATES = (
    "never_symptomatic", "presymptomatic", "convalescent", "incubating",
    "symptomatic", "cleared", "screened_out",
)


def _row(
    seed: int,
    arm: str,
    *,
    fraction: float | None,
    secondary_infections: int = 0,
    imported: int = 1,
    posted: bool = False,
    flush_events: float | None = 0,
    flush_aerosol_emitted: float | None = 0.0,
    flush_recipients: float | None = 0,
    flush_dose_delivered: float | None = 0.0,
    witness_present: bool = True,
    **cell: object,
) -> dict:
    """A minimal but complete voyage row, as ``_flush_row`` produces."""
    row = {
        "run_id": f"run_{arm}_{seed}",
        "arm": arm,
        "seed": seed,
        "tier_id": "fl_cls_7d",
        "initiation_mode": "boarding",
        "imported": imported,
        "imported_passenger": imported,
        "imported_crew": 0,
        "infections_total": imported + secondary_infections,
        "secondary_infections": secondary_infections,
        "passenger_complement": 1600,
        "crew_complement": 310,
        "reported_cases_passenger": secondary_infections,
        "infections_passenger": imported + secondary_infections,
        "infections_crew": 0,
        "reported_case_attack_rate_passenger": 0.05 if posted else 0.0,
        "reported_case_attack_rate_crew": 0.0,
        "infection_attack_rate_passenger": 0.01,
        "ever_ill_attack_rate_passenger": 0.01,
        "posted": posted,
        "posted_passenger": posted,
        "posted_crew": False,
        "peak_prevalence": 5,
        MARGIN_KEY: 0.05 if posted else 0.0,
        "flush_aerosol_fraction": fraction,
        "flush_events": flush_events,
        "flush_aerosol_emitted": flush_aerosol_emitted,
        "flush_recipients": flush_recipients,
        "flush_dose_delivered": flush_dose_delivered,
        "flush_witness_present": witness_present,
        "sanitary_witness_present": True,
        "sanitary_visits": 100,
        "sanitary_person_seconds": 10000.0,
        "sanitary_stool_visits": 2,
        "sanitary_unresolved": 0,
        "sanitary_recipients": 0,
        "sanitary_dose_delivered": 0.0,
        "route_dom_fomite": 0,
        "route_dom_flush_aerosol": 0,
        "route_share_fomite": 0.0,
        "route_share_flush_aerosol": 0.0,
    }
    for state in _STATES:
        row[f"composition_{state}"] = 0
    for role in ("passenger", "crew"):
        for key in (
            "eligible", "declared", "screened_out", "preboarding_reportable",
        ):
            row[f"{role}_{key}"] = 0
    row.update(CELL)
    row.update(cell)
    return row


def _arm_rows(
    arm: str,
    fraction: float | None,
    n: int,
    *,
    seeds: range | None = None,
    **kwargs: object,
) -> list[dict]:
    return [
        _row(seed, arm, fraction=fraction, **kwargs)
        for seed in (seeds or range(n))
    ]


# ── declared_fraction: the item-42 arm-label guard ───────────────────


def test_declared_fraction_returns_the_single_archived_value() -> None:
    rows = _arm_rows("live", 1e-7, 3)
    assert declared_fraction(rows) == pytest.approx(1e-7)


def test_declared_fraction_refuses_a_disagreeing_arm() -> None:
    rows = _arm_rows("live", 1e-7, 3)
    rows.append(_row(99, "live", fraction=1e-9))
    with pytest.raises(ValueError, match="disagree"):
        declared_fraction(rows)


def test_declared_fraction_off_is_zero() -> None:
    assert declared_fraction(_arm_rows("off", 0.0, 3)) == pytest.approx(0.0)


# ── _sorted_arms: baseline first, live arms by archived fraction ──────


def test_sorted_arms_orders_by_fraction_not_name() -> None:
    arms = {
        "off": _arm_rows("off", 0.0, 3),
        "1e-5": _arm_rows("1e-5", 1e-5, 3),
        "1e-9": _arm_rows("1e-9", 1e-9, 3),
        "1e-7": _arm_rows("1e-7", 1e-7, 3),
    }
    assert _sorted_arms(arms) == ["off", "1e-9", "1e-7", "1e-5"]


def test_sorted_arms_reads_the_archive_not_the_label() -> None:
    # A misnamed arm sorts where its archived fraction puts it.
    arms = {
        "off": _arm_rows("off", 0.0, 3),
        "zzz": _arm_rows("zzz", 1e-9, 3),
        "aaa": _arm_rows("aaa", 1e-5, 3),
    }
    assert _sorted_arms(arms) == ["off", "zzz", "aaa"]


# ── build_report: contrasts are against off only ──────────────────────


def test_report_contrasts_live_arms_against_off_only() -> None:
    n = MIN_PAIRED_SEEDS
    rows = (
        _arm_rows("off", 0.0, n)
        + _arm_rows("1e-9", 1e-9, n, secondary_infections=1)
        + _arm_rows("1e-7", 1e-7, n, secondary_infections=3)
    )
    report = build_report(rows, "pre")
    assert report["n_cells"] == 1
    cell = report["cells"][0]
    assert cell["arm_order"] == ["off", "1e-9", "1e-7"]
    assert set(cell["contrasts"]) == {"1e-9", "1e-7"}
    for contrast in cell["contrasts"].values():
        assert contrast["left_arm"] == "off"
        assert contrast["n_shared_seeds"] == n
        assert contrast["identical_import_fraction"] == pytest.approx(1.0)


def test_report_without_off_arm_yields_no_contrasts() -> None:
    rows = _arm_rows("1e-9", 1e-9, MIN_PAIRED_SEEDS, secondary_infections=1)
    report = build_report(rows, "pre")
    cell = report["cells"][0]
    assert cell["arm_order"] == ["1e-9"]
    assert cell["contrasts"] == {}


def test_report_pairs_only_shared_seeds() -> None:
    rows = (
        _arm_rows("off", 0.0, 0, seeds=range(MIN_PAIRED_SEEDS + 10))
        + _arm_rows("1e-9", 1e-9, 0, seeds=range(MIN_PAIRED_SEEDS))
    )
    cell = build_report(rows, "pre")["cells"][0]
    assert cell["contrasts"]["1e-9"]["n_shared_seeds"] == MIN_PAIRED_SEEDS


# ── flush_witness: totals, pooling, missing block ────────────────────


def test_witness_zero_emission_gives_zero_totals_and_no_ratio() -> None:
    block = flush_witness(_arm_rows("live", 1e-7, 5))
    for key in FLUSH_KEYS:
        assert block[f"total_{key}"] == pytest.approx(0.0)
    assert block["dose_per_exposure"] is None


def test_witness_dose_per_exposure_is_pooled() -> None:
    rows = _arm_rows("live", 1e-7, 2)
    rows[0].update(flush_recipients=10, flush_dose_delivered=500.0)
    rows[1].update(flush_recipients=30, flush_dose_delivered=2500.0)
    block = flush_witness(rows)
    assert block["dose_per_exposure"] == pytest.approx(3000.0 / 40.0)
    assert block["total_flush_recipients"] == pytest.approx(40.0)
    assert block["total_flush_dose_delivered"] == pytest.approx(3000.0)


def test_witness_missing_block_reports_not_present() -> None:
    rows = _arm_rows(
        "live", 1e-7, 3, witness_present=False,
        flush_events=None, flush_aerosol_emitted=None,
        flush_recipients=None, flush_dose_delivered=None,
    )
    block = flush_witness(rows)
    assert block["witness_present_fraction"] == pytest.approx(0.0)
    # Missing rows contribute zero to the totals, not a crash.
    assert block["total_flush_events"] == pytest.approx(0.0)


# ── Graded sensitivity across arms ───────────────────────────────────


def test_rising_flush_dose_rises_dose_per_exposure_and_contrast() -> None:
    n = MIN_PAIRED_SEEDS
    arms, prev_dose, prev_diff = [], None, None
    for i, (arm, dose) in enumerate(
        [("a", 100.0), ("b", 1000.0), ("c", 10000.0)],
    ):
        rows = _arm_rows(
            arm, 10.0 ** -(9 - 2 * i), n,
            flush_events=5, flush_recipients=10,
            flush_dose_delivered=dose,
            secondary_infections=i * 2,
        )
        arms.append(rows)
        block = flush_witness(rows)
        if prev_dose is not None:
            assert block["dose_per_exposure"] > prev_dose
        prev_dose = block["dose_per_exposure"]

    rows = _arm_rows("off", 0.0, n) + sum(arms, [])
    cell = build_report(rows, "pre")["cells"][0]
    for arm in ("a", "b", "c"):
        diff = cell["contrasts"][arm]["differences"][
            "secondary_infections"
        ]["mean_difference"]
        if prev_diff is not None:
            assert diff > prev_diff
        prev_diff = diff
