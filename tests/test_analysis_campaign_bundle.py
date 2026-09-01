"""Unit tests for the campaign analysis bundle (parser, metrics, pairwise)."""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from picard_framework.analysis.campaign_bundle import build_bundle
from picard_framework.analysis.metrics import (
    EPOCH_COLUMNS,
    RUN_SUMMARY_COLUMNS,
    build_aggregate_metrics,
    coerce_bool,
    compute_derived_metrics,
    encode_trigger_status,
    epoch_table_columns,
)
from picard_framework.analysis.pairwise import build_pairwise_deltas
from picard_framework.analysis.parse_run_id import (
    extract_factors,
    is_norovirus,
    parse_run_tags,
    platform_class,
)


def _ts_point(
    epoch: int,
    *,
    s: int,
    i: int,
    r: int,
    new: int,
    trigger: str = "none",
    mass: float = 1.0,
) -> dict:
    return {
        "epoch": epoch,
        "susceptible": s,
        "infected": i,
        "symptomatic": max(0, i - 1),
        "recovered": r,
        "immune": 0,
        "quarantined": 1 if trigger != "none" else 0,
        "isolated": 0,
        "passenger_complement": 80,
        "crew_complement": 20,
        "new_infections": new,
        "total_pathogen_mass": mass,
        "n_zones_contaminated": 1 if mass > 0 else 0,
        "max_concentration": mass,
        "max_conc_zone": "Cabin_A",
        "cumulative_cost_usd": epoch * 10,
        "cumulative_ois": epoch * 0.1,
        "trigger_status": trigger,
    }


def _make_run_zip(
    directory: Path,
    *,
    run_id: str,
    platform_id: str,
    pathogen: str,
    dose: float,
    seed: int,
    surveillance: str,
    transport_engine: str,
    timeseries: list[dict],
    num_agents: int = 100,
    lockdown: float | str = 0.05,
) -> Path:
    derived = compute_derived_metrics(timeseries, num_agents)
    summary = {
        "run_id": run_id,
        "num_epochs": len(timeseries),
        "trigger_status": timeseries[-1]["trigger_status"],
        "parameters": {
            "tier_id": "c12c_finecal",
            "run_id": run_id,
            "platform_id": platform_id,
            "pathogen": pathogen,
            "pathogen_bundle_id": f"{pathogen}_only",
            "dose_adjustment": dose,
            "density_exponent": 1.0,
            "seed": seed,
            "num_agents": num_agents,
            "num_epochs": len(timeseries),
            "surveillance": surveillance,
            "transport_engine": transport_engine,
            "lockdown_attack_rate": lockdown,
            "suspect_attack_rate": 0.02,
            "immune_fraction": 0.0,
        },
        "summary": {
            "susceptible": timeseries[-1]["susceptible"],
            "infected": timeseries[-1]["infected"],
            "recovered": timeseries[-1]["recovered"],
        },
        "cost_accounting": {
            "total_financial_usd": timeseries[-1]["cumulative_cost_usd"],
            "operational_impact_cumulative": timeseries[-1]["cumulative_ois"],
        },
        "derived": derived,
    }
    run_spec = {
        "description": run_id,
        "catalog": {
            "platform_id": platform_id,
            "pathogen_bundle_id": f"{pathogen}_only",
        },
        "run": {"random_seed": seed, "num_epochs": len(timeseries)},
        "config_overrides": {
            "hvac": {"transport_engine": transport_engine},
            "ship_graph": {"num_agents": num_agents, "immune_fraction": 0.0},
            "escalation": {"lockdown_attack_rate": lockdown},
        },
    }
    path = directory / f"{run_id}.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("summary.json", json.dumps(summary))
        zf.writestr("timeseries.json", json.dumps(timeseries))
        zf.writestr("run_spec.json", json.dumps(run_spec))
    return path


def _curve(peak_epoch: int = 2, trigger_at: int | None = 3) -> list[dict]:
    pts = [
        _ts_point(0, s=98, i=2, r=0, new=0),
        _ts_point(1, s=95, i=5, r=0, new=3),
        _ts_point(2, s=90, i=8, r=2, new=5),
        _ts_point(3, s=88, i=6, r=6, new=2, trigger="SUSPECTED" if trigger_at == 3 else "none"),
        _ts_point(4, s=87, i=3, r=10, new=1, trigger="CONFIRMED" if trigger_at else "none"),
        _ts_point(5, s=87, i=1, r=12, new=0, trigger="CONFIRMED" if trigger_at else "none"),
    ]
    return pts


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    """Four synthetic zips: native/contamx × none_true/syndromic."""
    base = tmp_path / "results"
    base.mkdir()
    curve = _curve()
    configs = [
        ("mega_cruise_5000", "norovirus", 10.6, 1, "none_true", "native"),
        ("mega_cruise_5000", "norovirus", 10.6, 1, "none_true", "contamx"),
        ("mega_cruise_5000", "norovirus", 10.6, 1, "syndromic", "native"),
        ("expedition_cruise_450", "norovirus", 10.4, 2, "syndromic", "native"),
    ]
    for plat, patho, dose, seed, surv, eng in configs:
        rid = f"c12c_{plat}_{patho}_d{dose}_{surv}_{eng}_s{seed}"
        _make_run_zip(
            base,
            run_id=rid,
            platform_id=plat,
            pathogen=patho,
            dose=dose,
            seed=seed,
            surveillance=surv,
            transport_engine=eng,
            timeseries=curve,
        )
    return base


def test_parse_run_tags_and_platform_class() -> None:
    tags = parse_run_tags("t7_noro_oa30_imm25_comp80_s12")
    assert tags["oa"] == "oa30"
    assert tags["imm"] == "imm25"
    assert tags["comp"] == "comp80"
    assert tags["seed_tag"] == "12"
    assert platform_class("mega_cruise_5000") == "mega"
    assert platform_class("expedition_cruise_450") == "expedition"
    assert is_norovirus("norovirus", "norovirus_only")
    assert is_norovirus(None, "noro_bundle")
    assert not is_norovirus("influenza", "flu_only")


def test_extract_factors_prefers_parameters() -> None:
    factors = extract_factors(
        run_id="x_d11_s9_syndromic_contamx",
        parameters={
            "platform_id": "mega_cruise_5000",
            "pathogen": "norovirus",
            "dose_adjustment": 10.6,
            "seed": 99,
            "surveillance": "cascade",
            "transport_engine": "native",
            "num_agents": 7000,
        },
    )
    assert factors["dose_adjustment"] == 10.6
    assert factors["seed"] == 99
    assert factors["surveillance_strategy"] == "cascade"
    assert factors["transport_engine"] == "native"
    assert factors["platform_class"] == "mega"


def test_encode_trigger_status() -> None:
    assert encode_trigger_status("none") == 0
    assert encode_trigger_status("SUSPECTED") == 1
    assert encode_trigger_status("CONFIRMED") == 2
    assert encode_trigger_status("LOCKDOWN") == 2


def test_coerce_bool_csv_roundtrip() -> None:
    assert coerce_bool(True) is True
    assert coerce_bool(False) is False
    assert coerce_bool("True") is True
    assert coerce_bool("False") is False
    assert coerce_bool("false") is False
    assert coerce_bool("0") is False
    assert coerce_bool("1") is True
    assert coerce_bool("") is False
    assert coerce_bool(None) is False


def test_build_aggregate_metrics_outbreak_rate_from_csv_strings() -> None:
    """CSV DictReader yields string booleans; both are truthy under plain bool()."""
    rows = [
        {"outbreak_occurred": "True", "attack_rate": "0.2", "platform_id": "a", "pathogen": "norovirus", "surveillance_strategy": "none"},
        {"outbreak_occurred": "False", "attack_rate": "0.0", "platform_id": "a", "pathogen": "norovirus", "surveillance_strategy": "none"},
        {"outbreak_occurred": "False", "attack_rate": "", "platform_id": "b", "pathogen": "norovirus", "surveillance_strategy": "syndromic"},
        {"outbreak_occurred": False, "attack_rate": "0.1", "platform_id": "b", "pathogen": "influenza", "surveillance_strategy": "syndromic"},
    ]
    agg = build_aggregate_metrics(rows)
    assert agg["n_runs"] == 4
    assert agg["outbreak_rate"] == 0.25
    assert agg["mean_attack_rate"] == pytest.approx(0.1)


def test_compute_derived_metrics_matches_expected() -> None:
    ts = _curve()
    m = compute_derived_metrics(ts, 100)
    # final infected=1 recovered=12 → ever=13 → AR=0.13
    # VSP at epoch 3 with incidence 0,3,5,2 → Δ²=2-10+3 < 0 → fizzle
    assert m["attack_rate"] == 0.13
    assert m["peak_prevalence"] == 8
    assert m["peak_epoch"] == 2
    assert m["detection_epoch"] == 3
    assert m["confirmation_epoch"] == 4
    assert m["outbreak_occurred"] is False
    assert m["seed_established"] is True
    assert m["total_quarantine_person_epochs"] == 3  # epochs 3,4,5
    assert m["passenger_complement"] == 80
    assert m["crew_complement"] == 20


def test_legacy_timeseries_rebundle_omits_role_complements() -> None:
    timeseries = [
        {
            key: value
            for key, value in _ts_point(0, s=99, i=1, r=0, new=1).items()
            if key not in {"passenger_complement", "crew_complement"}
        },
    ]
    derived = compute_derived_metrics(timeseries, 100)
    assert "passenger_complement" not in derived
    assert "crew_complement" not in derived


def test_boundary_row_builder_survives_legacy_timeseries() -> None:
    from picard_framework.analysis.boundary.export_outbreak_surface import (
        run_row_from_payload,
    )

    timeseries = [
        {
            key: value
            for key, value in _ts_point(0, s=99, i=1, r=0, new=1).items()
            if key not in {"passenger_complement", "crew_complement"}
        },
    ]
    payload = {
        "run_id": "legacy_norovirus_init1_s1",
        "summary": {
            "parameters": {
                "platform_id": "mega_cruise_5000",
                "pathogen": "norovirus",
                "num_agents": 100,
                "initial_infected": 1,
            },
        },
        "timeseries": timeseries,
    }
    row = run_row_from_payload(payload)
    assert row is not None
    assert row["num_agents"] == 100
    assert "passenger_complement" not in row
    assert "crew_complement" not in row
    explicit_payload = payload | {
        "timeseries": [_ts_point(0, s=99, i=1, r=0, new=1)],
    }
    from picard_framework.analysis.metrics import build_run_summary_row

    explicit_summary_row = build_run_summary_row(explicit_payload)
    assert explicit_summary_row["passenger_complement"] == 80
    assert explicit_summary_row["crew_complement"] == 20
    explicit_row = run_row_from_payload(explicit_payload)
    assert explicit_row is not None


def _takeoff_curve() -> list[dict]:
    """Accelerating incidence into VSP at epoch 3 → takeoff."""
    return [
        _ts_point(0, s=99, i=1, r=0, new=1),
        _ts_point(1, s=97, i=3, r=0, new=2),
        _ts_point(2, s=93, i=7, r=0, new=4),
        _ts_point(3, s=85, i=15, r=0, new=8, trigger="SUSPECTED"),
        _ts_point(4, s=79, i=12, r=9, new=6, trigger="CONFIRMED"),
        _ts_point(5, s=76, i=6, r=18, new=3, trigger="CONFIRMED"),
    ]


def test_epidemic_takeoff_vs_fizzle() -> None:
    from simulation_utils.epidemic_labels import (
        epidemic_took_off,
        incidence_second_difference,
        seed_established,
    )

    # Default _curve: VSP after incidence already decelerating → fizzle
    assert epidemic_took_off(_curve()) is False
    # No VSP → fizzle
    assert epidemic_took_off(_curve(trigger_at=None)) is False
    # Accelerating into VSP: Δ² at t=3 is 8 - 2*4 + 2 = 2 ≥ 0 → takeoff
    takeoff_ts = _takeoff_curve()
    assert incidence_second_difference([1, 2, 4, 8, 6, 3], 3) == 2
    assert epidemic_took_off(takeoff_ts) is True
    assert compute_derived_metrics(takeoff_ts, 100)["outbreak_occurred"] is True
    assert seed_established(5) is True
    assert seed_established(2) is False


def test_build_bundle_writes_required_artifacts(results_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "analysis"
    # build_bundle confines to CWD — chdir into tmp (fixture already wrote results/)
    import os

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert Path("results").is_dir()
        manifest = build_bundle("results", "analysis")
    finally:
        os.chdir(prev)

    assert manifest["n_runs"] == 4
    assert (out / "run_summary.csv").is_file()
    assert (out / "factor_dictionary.json").is_file()
    assert (out / "aggregate_metrics.json").is_file()
    # parquet or csv.gz
    assert (out / "epoch_timeseries.csv.gz").is_file() or (
        out / "epoch_timeseries.parquet"
    ).is_file()

    with (out / "run_summary.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    for col in RUN_SUMMARY_COLUMNS[:20]:
        assert col in rows[0]
    assert all(r["pathogen"] == "norovirus" for r in rows)
    assert {r["transport_engine"] for r in rows} >= {"native", "contamx"}

    # Pairwise should include native vs contamx for matched seed/surv
    assert (out / "pairwise_deltas.csv").is_file()
    with (out / "pairwise_deltas.csv").open(encoding="utf-8", newline="") as fh:
        pairs = list(csv.DictReader(fh))
    assert any(p["comparison_id"] == "native_vs_contamx" for p in pairs)
    assert any(p["comparison_id"] == "none_true_vs_syndromic" for p in pairs)


def test_metric_column_lists_match_row_keys(results_dir: Path) -> None:
    from picard_framework.analysis._io import load_run_zip
    from picard_framework.analysis.metrics import build_epoch_rows, build_run_summary_row

    payload = load_run_zip(str(next(results_dir.glob("*.zip"))))
    assert payload is not None
    summary_row = build_run_summary_row(payload)
    epoch_rows = build_epoch_rows(payload, summary_row)

    assert all(column in summary_row for column in RUN_SUMMARY_COLUMNS)
    assert epoch_rows
    assert all(column in epoch_rows[0] for column in EPOCH_COLUMNS)


def test_pairwise_trajectory_match_rates(results_dir: Path) -> None:
    from picard_framework.analysis._io import load_run_zip
    from picard_framework.analysis.metrics import build_epoch_rows, build_run_summary_row

    run_rows = []
    epoch_rows = []
    for z in sorted(results_dir.glob("*.zip")):
        payload = load_run_zip(str(z))
        assert payload is not None
        summary = build_run_summary_row(payload)
        run_rows.append(summary)
        epoch_rows.extend(build_epoch_rows(payload, summary))

    pairs = build_pairwise_deltas(run_rows, epoch_rows)
    native_contam = [p for p in pairs if p["comparison_id"] == "native_vs_contamx"]
    assert native_contam
    # Identical synthetic curves → perfect match
    assert native_contam[0]["epoch_match_rate_infected"] == 1.0
    assert native_contam[0]["delta_attack_rate"] == 0.0


def test_epoch_table_columns_include_factors() -> None:
    cols = epoch_table_columns()
    assert "run_id" in cols
    assert "new_infections" in cols
    assert "trigger_state" in cols
    assert "dose_adjustment" in cols
