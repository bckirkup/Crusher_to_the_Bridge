"""Coverage for the synthetic recovery post-processor."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from picard_framework.analysis import synthetic_recovery_postprocess as recovery


def _summary_zip(
    path: Path,
    *,
    run_id: str,
    vector: str = "ridge_3",
    platform: str = "mega_cruise_5000",
    attack_rate: float = 0.2,
    outbreak: object = True,
) -> None:
    payload = {
        "run_id": run_id,
        "parameters": {
            "parameter_vector": vector,
            "platform_id": platform,
            "pathogen": "norovirus",
            "dose_adjustment": 10.6,
            "density_exponent": 0.75,
            "surveillance": "syndromic",
            "seed": 7,
            "initial_infected": 3,
            "num_agents": 100,
        },
        "derived": {
            "attack_rate": attack_rate,
            "outbreak_occurred": outbreak,
        },
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("summary.json", json.dumps(payload))
    path.write_bytes(stream.getvalue())


def test_logit_and_bernoulli_likelihood_are_stable_and_bounded() -> None:
    values = recovery._logit(np.array([0.2, 0.5, 0.8]))
    expected = np.log(np.array([0.2, 0.5, 0.8])) - np.log(
        1 - np.array([0.2, 0.5, 0.8])
    )
    assert np.allclose(values, expected)

    moderate = recovery._bernoulli_logit_lpmf(
        np.array([1.0, 0.0]),
        np.array([0.7, 0.7]),
    )
    naive = np.log(1 / (1 + np.exp(-0.7))) + np.log(1 - 1 / (1 + np.exp(-0.7)))
    assert moderate == pytest.approx(float(naive), rel=1e-10)
    assert moderate <= 0
    assert recovery._bernoulli_logit_lpmf(1, 700) == pytest.approx(0, abs=1e-12)
    assert recovery._bernoulli_logit_lpmf(0, 700) < -600
    assert np.isfinite(recovery._bernoulli_logit_lpmf(1, -700))
    assert np.isfinite(recovery._bernoulli_logit_lpmf(0, -700))


def test_normal_log_density_is_symmetric_peaked_and_sigma_sensitive() -> None:
    left = recovery._normal_lpdf(-1.0, 0.0, 1.0)
    right = recovery._normal_lpdf(1.0, 0.0, 1.0)
    center = recovery._normal_lpdf(0.0, 0.0, 1.0)
    wide_center = recovery._normal_lpdf(0.0, 0.0, 2.0)

    assert left == pytest.approx(right)
    assert center > left
    assert wide_center < center


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.2, 0.2), (0.5, 0.5), (0.0, 1e-4), (1.0, 1 - 1e-4)],
)
def test_clip_ar_preserves_interior_and_open_bounds(value: float, expected: float) -> None:
    assert recovery._clip_ar(value) == pytest.approx(expected)


def test_parameter_vector_prefers_explicit_value_and_distinguishes_inputs() -> None:
    explicit = recovery._parameter_vector("run_ridge_1", {"vector_id": "custom"})
    inferred = recovery._parameter_vector("run_ridge_2_x", {})
    missing = recovery._parameter_vector("run_without_vector", {})

    assert explicit == "custom"
    assert inferred == "ridge_2"
    assert missing == "unknown"
    assert recovery._parameter_vector("run_ridge_1", {}) != inferred


def _rows() -> list[dict]:
    return [
        {
            "parameter_vector": "ridge_1",
            "platform_id": "mega_cruise_5000",
            "attack_rate": 0.2,
            "outbreak_occurred": 0,
        },
        {
            "parameter_vector": "ridge_1",
            "platform_id": "mega_cruise_5000",
            "attack_rate": 0.4,
            "outbreak_occurred": 1,
        },
        {
            "parameter_vector": "ridge_2",
            "platform_id": "expedition_cruise_450",
            "attack_rate": 0.7,
            "outbreak_occurred": 1,
        },
    ]


def test_aggregate_by_vector_platform_has_grouping_invariants() -> None:
    output = recovery.aggregate_by_vector_platform(_rows())

    assert sum(int(row["n_runs"]) for row in output) == len(_rows())
    assert all(0 <= float(row["outbreak_rate"]) <= 1 for row in output)
    first = next(row for row in output if row["parameter_vector"] == "ridge_1")
    assert first["n_runs"] == 2
    assert first["mean_attack_rate"] == pytest.approx(0.3)


def test_rw_mh_is_seeded_and_reacts_to_a_posterior() -> None:
    def log_post(theta: np.ndarray) -> float:
        return float(-np.sum(theta**2))

    first, first_acceptance = recovery._rw_mh(
        log_post,
        np.array([0.0, 0.0]),
        n_warmup=10,
        n_sample=20,
        step=0.2,
        seed=11,
    )
    repeat, repeat_acceptance = recovery._rw_mh(
        log_post,
        np.array([0.0, 0.0]),
        n_warmup=10,
        n_sample=20,
        step=0.2,
        seed=11,
    )
    other, other_acceptance = recovery._rw_mh(
        log_post,
        np.array([0.0, 0.0]),
        n_warmup=10,
        n_sample=20,
        step=0.2,
        seed=12,
    )

    assert np.array_equal(first, repeat)
    assert first_acceptance == pytest.approx(repeat_acceptance)
    assert not np.array_equal(first, other)
    assert first_acceptance >= 0
    assert first_acceptance <= 1
    assert other_acceptance >= 0
    assert other_acceptance <= 1


def _ar_data(attack_rate: float) -> dict:
    return {
        "N_runs": 8,
        "P": 1,
        "ar": [attack_rate] * 8,
        "platform": [1] * 8,
        "dose_adj": [10.6] * 8,
        "alpha_c": [0.75] * 8,
        "d0": 10.6,
        "a0": 0.75,
    }


def test_fit_pooled_ar_posterior_mean_rises_with_attack_rate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    low = recovery._fit_pooled_ar_numpy(
        _ar_data(0.15),
        "low",
        chains=1,
        iter_warmup=30,
        iter_sampling=40,
        seed=31,
    )
    high = recovery._fit_pooled_ar_numpy(
        _ar_data(0.75),
        "high",
        chains=1,
        iter_warmup=30,
        iter_sampling=40,
        seed=31,
    )

    low_mean = float(low["draws"]["alpha_platform[1]"].mean())
    high_mean = float(high["draws"]["alpha_platform[1]"].mean())
    assert high_mean > low_mean
    assert (tmp_path / "low" / "fit_status.json").is_file()
    assert (tmp_path / "high" / "fit_status.json").is_file()


def test_build_run_summary_reads_synthetic_zips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    zips = tmp_path / "zips"
    zips.mkdir()
    _summary_zip(zips / "first.zip", run_id="first", attack_rate=0.2)
    _summary_zip(
        zips / "second.zip",
        run_id="second",
        vector="off_ridge",
        platform="expedition_cruise_450",
        attack_rate=0.4,
        outbreak=False,
    )

    rows = recovery.build_run_summary(str(zips))

    assert len(rows) == 2
    assert {row["run_id"] for row in rows} == {"first", "second"}
    assert {row["parameter_vector"] for row in rows} == {"ridge_3", "off_ridge"}
    assert all(0 <= float(row["attack_rate"]) <= 1 for row in rows)
