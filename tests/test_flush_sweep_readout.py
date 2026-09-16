"""Flush-sweep stage-1 readout: graded behaviour and invariants.

Per ci-test-design: no golden outputs. Expectations are the arm-label
refusal (an arm's identity is its archived ``flush_aerosol_fraction``,
never a directory name), archived-fraction ordering of live arms,
baseline-only pairing of contrasts, the flush witness's divide-by-zero
and missing-block handling, and graded sensitivity of the pooled
dose-per-exposure and the paired secondaries contrast.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from telemetry_buffer.observation_model.flush_sweep_readout import (  # noqa: E402
    FLUSH_KEYS,
    _sorted_arms,
    build_report,
    collect_rows,
    declared_fraction,
    flush_witness,
    main,
    render_markdown,
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


# ── Archive collection ───────────────────────────────────────────────


def _summary(
    seed: int,
    *,
    fraction: float,
    secondaries: int = 0,
    witness: bool = True,
) -> dict:
    block: dict = {
        "infections_by_dominant_route": {"flush_aerosol": secondaries},
        "infection_dose_share_by_route": {},
    }
    if witness:
        block["sanitary_activity"] = {
            "visits": 10.0,
            "person_seconds": 1000.0,
            "stool_visits": 1.0,
            "unresolved": 0.0,
            "recipients": 0.0,
            "dose_delivered": 0.0,
            "flush_events": 1.0,
            "flush_aerosol_emitted": 1e6,
            "flush_recipients": 2.0,
            "flush_dose_delivered": 10.0,
        }
    return {
        "run_id": f"fl_{fraction}_{seed}",
        "parameters": {
            "tier_id": "fl_cls_7d",
            "platform_id": CELL["platform_id"],
            "surveillance": CELL["surveillance"],
            "dose_adjustment": CELL["dose_adjustment"],
            "num_epochs": CELL["num_epochs"],
            "num_agents": CELL["num_agents"],
            "seed": seed,
            "boarding_mechanism_rung": CELL["boarding_mechanism_rung"],
            "sanitary_visit_mode": "dwell_weighted",
            "flush_aerosol_fraction": fraction,
        },
        "derived": {
            "reported_case_attack_rate_passenger": 0.0,
            "reported_case_attack_rate_crew": 0.0,
            "infection_attack_rate_passenger": (1 + secondaries) / 1600,
            "infection_attack_rate_crew": 0.0,
            "ever_ill_attack_rate_passenger": 0.01,
            "passenger_complement": 1600,
            "crew_complement": 310,
        },
        "summary": block,
    }


def _profile() -> dict:
    return {
        "initiation": {
            "mode": "boarding",
            "boarding": {
                "norwalk_gi": {
                    "drawn_by_role": {"passenger": 1, "crew": 0},
                    "composition": {"never_symptomatic": 1},
                },
            },
        },
    }


def _archive(
    root: Path, name: str, summaries: list[tuple[dict, dict]],
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for summary, profile in summaries:
            prefix = f"{summary['run_id']}/"
            archive.writestr(f"{prefix}summary.json", json.dumps(summary))
            archive.writestr(
                f"{prefix}resolved_pathogen_profiles.json",
                json.dumps(profile),
            )
    return path


def test_collect_rows_flattens_zips_and_deduplicates(tmp_path: Path) -> None:
    pairs = [(_summary(seed, fraction=1e-7), _profile()) for seed in range(3)]
    _archive(tmp_path, "shard_a", pairs)
    first = tmp_path / "shard_a.zip"
    (tmp_path / "shard_b.zip").write_bytes(first.read_bytes())
    rows = collect_rows(tmp_path, "1e-7")
    assert len(rows) == 3
    assert {row["arm"] for row in rows} == {"1e-7"}
    assert declared_fraction(rows) == pytest.approx(1e-7)
    assert all(row["flush_witness_present"] for row in rows)


def test_collect_rows_marks_a_missing_sanitary_block(tmp_path: Path) -> None:
    _archive(
        tmp_path, "arm",
        [(_summary(0, fraction=1e-7, witness=False), _profile())],
    )
    (row,) = collect_rows(tmp_path, "1e-7")
    assert row["flush_witness_present"] is False
    assert row["flush_events"] is None


# ── Empty and unpaired edges ─────────────────────────────────────────


def test_flush_witness_of_no_rows_is_empty() -> None:
    assert flush_witness([]) == {}


def test_contrast_is_none_below_the_paired_floor() -> None:
    rows = _arm_rows("off", 0.0, 20) + _arm_rows("1e-7", 1e-7, 20)
    cell = build_report(rows, "pre")["cells"][0]
    assert cell["contrasts"] == {"1e-7": None}


def test_contrast_is_none_when_seeds_do_not_pair() -> None:
    off = _arm_rows("off", 0.0, 10)
    live = _arm_rows("1e-7", 1e-7, 10)
    live.append(live[0])
    cell = build_report(off + live, "pre")["cells"][0]
    assert cell["contrasts"]["1e-7"] is None


# ── Rendering and the CLI ────────────────────────────────────────────


def test_render_markdown_covers_arms_contrasts_and_unpaired() -> None:
    n = MIN_PAIRED_SEEDS
    rows = (
        _arm_rows("off", 0.0, n)
        + _arm_rows("1e-7", 1e-7, n, secondary_infections=2,
                    flush_events=3, flush_recipients=4)
        + _arm_rows("3e-9", 3e-9, n - 20, seeds=range(200, 200 + n - 20))
    )
    report = build_report(rows, "pre")
    markdown = render_markdown(report, title="Flush sweep stage 1")
    assert "| off |" in markdown
    assert "| 1e-7 |" in markdown
    assert "unpaired" in markdown
    assert "A4" in markdown


def test_build_report_post_era_uses_post_targets() -> None:
    n = MIN_PAIRED_SEEDS
    rows = _arm_rows("off", 0.0, n) + _arm_rows("1e-7", 1e-7, n)
    pre = build_report(rows, "pre")["observed_comparators"]
    post = build_report(rows, "post")["observed_comparators"]
    assert post["A9_posting_probability_per_1000_voyages"] is None
    assert pre["A9_posting_probability_per_1000_voyages"]["fleet"]


def test_main_writes_report_and_markdown(tmp_path: Path) -> None:
    n = MIN_PAIRED_SEEDS
    for arm, fraction in (("off", 0.0), ("1e-7", 1e-7)):
        pairs = [
            (_summary(8000 + seed, fraction=fraction), _profile())
            for seed in range(n)
        ]
        _archive(tmp_path / arm, arm, pairs)
    out_dir = REPO_ROOT / "telemetry_buffer" / "_flush_cli_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "report.json"
    md_path = out_dir / "report.md"
    try:
        assert main([
            "--arm", f"off={tmp_path / 'off'}",
            "--arm", f"1e-7={tmp_path / '1e-7'}",
            "--out", str(out_path),
            "--markdown", str(md_path),
            "--title", "test",
        ]) == 0
        report = json.loads(out_path.read_text())
        assert report["n_cells"] == 1
        assert report["baseline_arm"] == "off"
        assert md_path.read_text().startswith("# test")
    finally:
        out_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
        out_dir.rmdir()


def test_main_refuses_an_empty_arm_root(tmp_path: Path) -> None:
    out_dir = REPO_ROOT / "telemetry_buffer" / "_flush_cli_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with pytest.raises(SystemExit):
            main([
                "--arm", f"missing={tmp_path}",
                "--out", str(out_dir / "report.json"),
            ])
    finally:
        (out_dir / "report.json").unlink(missing_ok=True)
        out_dir.rmdir()
