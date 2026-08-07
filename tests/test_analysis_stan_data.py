"""Stan data-prep tests (no CmdStan required)."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from picard_framework.analysis.campaign_bundle import build_bundle
from picard_framework.analysis.metrics import encode_trigger_status
from picard_framework.analysis.stan.fit_norovirus_trajectory import (
    build_stan_data,
    filter_norovirus_runs,
    fit_model,
)
from picard_framework.analysis.stan.posterior_summaries import summarize_fit
from tests.test_analysis_campaign_bundle import _curve, _make_run_zip


def _bundle_with_noro(tmp_path: Path) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    curve = _curve()
    for eng, surv, seed, plat, dose in (
        ("native", "none_true", 1, "mega_cruise_5000", 10.6),
        ("native", "syndromic", 1, "mega_cruise_5000", 10.6),
        ("native", "syndromic", 2, "expedition_cruise_450", 10.4),
        ("native", "syndromic", 3, "mega_cruise_5000", 10.6),  # influenza control below
    ):
        pathogen = "influenza" if seed == 3 else "norovirus"
        rid = f"run_{plat}_{pathogen}_{surv}_s{seed}"
        _make_run_zip(
            results,
            run_id=rid,
            platform_id=plat,
            pathogen=pathogen,
            dose=dose,
            seed=seed,
            surveillance=surv,
            transport_engine=eng,
            timeseries=curve,
        )

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        build_bundle("results", "analysis")
    finally:
        os.chdir(prev)
    return tmp_path / "analysis"


def test_filter_norovirus_and_stan_data_shape(tmp_path: Path) -> None:
    analysis = _bundle_with_noro(tmp_path)
    with (analysis / "run_summary.csv").open(encoding="utf-8", newline="") as fh:
        run_rows = list(csv.DictReader(fh))
    noro = filter_norovirus_runs(run_rows)
    assert len(noro) == 3
    assert all("influenza" not in str(r.get("pathogen")) for r in noro)

    # Load epoch rows from csv.gz
    import gzip

    gz = analysis / "epoch_timeseries.csv.gz"
    parquet = analysis / "epoch_timeseries.parquet"
    if gz.is_file():
        with gzip.open(gz, "rt", encoding="utf-8", newline="") as fh:
            epoch_rows = list(csv.DictReader(fh))
    else:
        import pyarrow.parquet as pq

        epoch_rows = pq.read_table(parquet).to_pylist()

    data, meta = build_stan_data(run_rows, epoch_rows)
    assert data["N_runs"] == 3
    assert data["T"] == 6
    assert data["P"] == 2
    assert data["S"] == 2
    assert len(data["new_infections"]) == 3
    assert len(data["new_infections"][0]) == 6
    assert set(meta["platforms"]) == {"expedition_cruise_450", "mega_cruise_5000"}
    # trigger encoding
    assert encode_trigger_status("SUSPECTED") == 1
    # At least one run should have suspected/confirmed states
    flat_triggers = [v for row in data["trigger_state"] for v in row]
    assert 1 in flat_triggers
    assert 2 in flat_triggers


def test_fit_model_skips_without_cmdstan(tmp_path: Path) -> None:
    _bundle_with_noro(tmp_path)
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        status = fit_model("analysis", "stan_fit", chains=1, iter_sampling=10, iter_warmup=10)
    finally:
        os.chdir(prev)

    assert status["status"] in {"ok", "skipped"}
    assert (tmp_path / "stan_fit" / "stan_data_meta.json").is_file()
    if status["status"] == "skipped":
        fit_status = json.loads(
            (tmp_path / "stan_fit" / "fit_status.json").read_text(encoding="utf-8")
        )
        assert fit_status["status"] == "skipped"


def test_posterior_summaries_from_fake_fit(tmp_path: Path) -> None:
    class FakeFit:
        def stan_variables(self):
            import numpy as np

            return {
                "beta_d": np.array([0.8, 1.0, 1.2]),
                "alpha_platform": np.array([[0.1, -0.2], [0.0, -0.1], [0.2, -0.3]]),
                "platform_risk": np.exp(
                    np.array([[0.1, -0.2], [0.0, -0.1], [0.2, -0.3]])
                ),
                "delta_surveillance": np.array([[0.1, 0.5], [0.2, 0.4], [0.15, 0.6]]),
                "eta_vsp": np.array([0.2, 0.3, 0.25]),
                "vsp_compression": np.exp(np.array([0.2, 0.3, 0.25])),
                "pred_attack_rate": np.array([[0.1, 0.2], [0.12, 0.18], [0.11, 0.22]]),
            }

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        arts = summarize_fit(
            fit=FakeFit(),
            meta={
                "platforms": ["expedition_cruise_450", "mega_cruise_5000"],
                "surveillances": ["none_true", "syndromic"],
                "d0": 10.6,
                "vsp_ref": 0.05,
            },
            out_dir="stan_fit",
            run_summary_rows=[
                {"run_id": "a", "attack_rate": 0.13},
                {"run_id": "b", "attack_rate": 0.2},
            ],
        )
    finally:
        os.chdir(prev)

    assert "dose_adj_calibration" in arts
    assert (tmp_path / "stan_fit" / "posterior" / "platform_effects.csv").is_file()
    assert (tmp_path / "stan_fit" / "posterior" / "vsp_threshold_effect.csv").is_file()
    with (tmp_path / "stan_fit" / "posterior" / "platform_effects.csv").open(
        encoding="utf-8", newline=""
    ) as fh:
        rows = list(csv.DictReader(fh))
    assert any(r["platform"] == "expedition_over_mega_ratio" for r in rows)


def test_cmdstan_smoke_opt_in(tmp_path: Path) -> None:
    """Real CmdStan sample is opt-in (heavy); default CI skips."""
    if os.environ.get("RUN_CMDSTAN_SMOKE") != "1":
        pytest.skip("RUN_CMDSTAN_SMOKE not set")
    try:
        from cmdstanpy import cmdstan_path

        cmdstan_path()
    except Exception:
        pytest.skip("CmdStan not installed")

    _bundle_with_noro(tmp_path)
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        status = fit_model(
            "analysis",
            "stan_fit_smoke",
            chains=1,
            iter_sampling=20,
            iter_warmup=20,
        )
    finally:
        os.chdir(prev)
    assert status["status"] == "ok"
    assert (tmp_path / "stan_fit_smoke" / "posterior" / "dose_adj_calibration.csv").is_file()
