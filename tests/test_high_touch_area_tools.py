"""High-touch-area tools: readout verdicts on synthetic cells, envelope invariants."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path

import pytest

from simulation_utils.paths import REPO_ROOT
from tools.noro_diag import high_touch_area_envelope as htae
from tools.noro_diag import high_touch_area_readout as htar

_LF_SIGMA = 0.1


def _pool_row(
    calls: float = 100.0,
    area: float = 1.5,
    lf: float = -4.0,
    clean: float = 100.0,
    capped: float = 0.0,
    confined: float = 0.0,
    zero_mass: float = 0.0,
) -> dict:
    return {
        "calls": calls,
        "calls_clean": clean,
        "calls_capped": capped,
        "calls_confined": confined,
        "calls_zero_mass": zero_mass,
        "sum_surface_area_m2": calls * area,
        "sum_log10_f_touch": clean * lf,
        "sum_sq_log10_f_touch": clean * (lf * lf + _LF_SIGMA**2),
    }


def _cell(
    seed: int,
    *,
    area: float,
    lf: float,
    calls: float = 100.0,
    clean: float = 100.0,
    capped: float = 0.0,
    confined: float = 0.0,
    zero_mass: float = 0.0,
    dose: float = 1.0,
    req: float = 1.0,
    off: float = 1.0,
    secondaries: int = 0,
    extra_classes: dict | None = None,
) -> dict:
    rows = {
        "cabin": _pool_row(calls, area, lf, clean, capped, confined, zero_mass),
    }
    for zone_class, kwargs in (extra_classes or {}).items():
        rows[zone_class] = _pool_row(**kwargs)
    return {
        "seed": seed,
        "transfer_product_witness": {
            "surface_to_hand": {"pool": rows, "patch": {}},
        },
        "fomite_witness": {"hand_to_mouth_dose_gec": dose},
        "delivery_scale_witness": {
            "sum_requested_gec": req,
            "sum_offered_gec": off,
        },
        "transmission": {"secondaries": secondaries},
    }


def _write(directory: Path, tag: str | None, cell: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    stem = "per_host_dose_challenge_" + (f"{tag}_" if tag else "")
    path = directory / f"{stem}seed{cell['seed']}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(cell, handle)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    scale: float | None = None,
    scale_by_zone_class: dict | None = None,
    predicted_direction: str = "up",
    base_cells: list[dict],
    arm_cells: list[dict],
    tag: str = "htaT",
) -> dict:
    base_dir = tmp_path / "base"
    arm_dir = tmp_path / "arm"
    for cell in base_cells:
        _write(base_dir, None, cell)
    for cell in arm_cells:
        _write(arm_dir, tag, cell)
    monkeypatch.setattr(htar, "BASELINE_DIR", base_dir)
    return htar.readout(
        arm_dir, tag,
        scale=scale,
        scale_by_zone_class=scale_by_zone_class,
        predicted_direction=predicted_direction,
    )


_BASE_LF = -4.0
_SCALE = 0.25
_SHIFT = -math.log10(_SCALE)


def _paired(*, area_mult: float | None = None, **overrides):
    seeds = [9001, 9002]
    arm_area = 1.5 * _SCALE if area_mult is None else 1.5 * area_mult
    return (
        [_cell(s, area=1.5, lf=_BASE_LF) for s in seeds],
        [
            _cell(s, area=arm_area, lf=_BASE_LF + _SHIFT, **overrides)
            for s in seeds
        ],
    )


def test_per_touch_conforms_at_exact_area_and_shift(monkeypatch, tmp_path):
    base, arm = _paired()
    row = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]["cabin"]
    assert row["verdict"] == "conforms"
    assert row["area_ratio"] == pytest.approx(0.25, rel=0.0, abs=0.0)


def test_per_touch_departs_when_area_ratio_wrong(monkeypatch, tmp_path):
    base, arm = _paired(area_mult=0.5)
    row = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]["cabin"]
    assert row["verdict"] == "departs"


def _two_class_paired(cabin_mult: float, dining_mult: float):
    """Two zone classes each scaling at its own multiplier."""
    seeds = [9001, 9002]
    base = [
        _cell(
            s, area=1.5, lf=_BASE_LF,
            extra_classes={"dining": {"area": 2.0, "lf": _BASE_LF}},
        )
        for s in seeds
    ]
    arm = [
        _cell(
            s, area=1.5 * cabin_mult, lf=_BASE_LF - math.log10(cabin_mult),
            extra_classes={
                "dining": {
                    "area": 2.0 * dining_mult,
                    "lf": _BASE_LF - math.log10(dining_mult),
                },
            },
        )
        for s in seeds
    ]
    return base, arm


def test_per_class_scaling_conforms_at_each_multiplier(monkeypatch, tmp_path):
    base, arm = _two_class_paired(0.5, 2.0)
    rows = _run(
        monkeypatch, tmp_path,
        scale_by_zone_class={"cabin": 0.5, "dining": 2.0},
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]
    assert rows["cabin"]["verdict"] == "conforms"
    assert rows["dining"]["verdict"] == "conforms"
    assert rows["cabin"]["area_ratio_expected"] == pytest.approx(0.5)
    assert rows["dining"]["area_ratio_expected"] == pytest.approx(2.0)


def test_per_class_scaling_departs_on_wrong_multiplier(monkeypatch, tmp_path):
    base, arm = _two_class_paired(0.5, 2.0)
    rows = _run(
        monkeypatch, tmp_path,
        scale_by_zone_class={"cabin": 0.5, "dining": 3.0},
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]
    assert rows["cabin"]["verdict"] == "conforms"
    assert rows["dining"]["verdict"] == "departs"


def test_unlisted_zone_class_rides_at_unit_multiplier(monkeypatch, tmp_path):
    seeds = [9001, 9002]
    base = [_cell(s, area=1.5, lf=_BASE_LF) for s in seeds]
    arm = [_cell(s, area=1.5, lf=_BASE_LF) for s in seeds]
    row = _run(
        monkeypatch, tmp_path, scale_by_zone_class={"dining": 4.0},
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]["cabin"]
    assert row["verdict"] == "conforms"
    assert row["scale_c"] == pytest.approx(1.0)


def test_censored_class_still_reports_raw_matches(monkeypatch, tmp_path):
    base, arm = _paired(capped=2.0)  # 2 % of 100 calls > 1 % ceiling
    row = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["per_touch_scaling"]["cabin"]
    assert row["verdict"] == "censored"
    assert row["area_ratio_matches"] is True
    assert row["log10_shift_within_3se"] is True


@pytest.mark.parametrize(
    ("capped", "verdict"),
    [(5.0, "out of linear regime"), (0.5, "linear regime")],
)
def test_saturation_verdicts_and_per_class_rows(
    monkeypatch, tmp_path, capped, verdict,
):
    base, arm = _paired(capped=capped)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["saturation_arm"]
    assert result["verdict"] == verdict
    assert result["per_zone_class_pool"]["cabin"]["capped_share"] == (
        pytest.approx(capped / 100.0, rel=1e-12)
    )


def test_saturation_reports_censored_shares_and_regime(monkeypatch, tmp_path):
    base, arm = _paired(capped=25.0, confined=10.0, zero_mass=3.0)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["saturation_arm"]
    cabin = result["per_zone_class_pool"]["cabin"]
    assert cabin["regime"] == "measures the cap"
    assert cabin["confined_share"] == pytest.approx(0.10, rel=1e-12)
    assert cabin["zero_mass_share"] == pytest.approx(0.03, rel=1e-12)
    assert result["classes_measuring_the_cap"] == ["cabin"]


@pytest.mark.parametrize(
    ("capped", "regime"),
    [(0.5, "linear"), (10.0, "capped regime"), (25.0, "measures the cap")],
)
def test_saturation_regime_grades_with_capped_share(
    monkeypatch, tmp_path, capped, regime,
):
    base, arm = _paired(capped=capped)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["saturation_arm"]["per_zone_class_pool"]["cabin"]
    assert result["regime"] == regime


def test_classes_measuring_the_cap_empty_in_linear_regime(
    monkeypatch, tmp_path,
):
    base, arm = _paired(capped=0.5)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["saturation_arm"]
    assert result["classes_measuring_the_cap"] == []


@pytest.mark.parametrize(
    ("secondaries", "fragment"),
    [(3, "not resolvable at"), (25, "changed")],
)
def test_secondaries_resolvability_floor(
    monkeypatch, tmp_path, secondaries, fragment,
):
    base, arm = _paired(secondaries=secondaries)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["secondaries_arm"]
    assert fragment in result["verdict"]


def _dose_pairs(
    n: int,
    up_count: int,
    *,
    dose_up: float = 10.0,
    dose_down: float = 0.1,
    zero_seed: int | None = None,
):
    """n paired seeds: first up_count arm doses above base, rest below."""
    seeds = list(range(9001, 9001 + n))
    base = [_cell(s, area=1.5, lf=_BASE_LF, dose=1.0) for s in seeds]
    arm = []
    for i, s in enumerate(seeds):
        if s == zero_seed:
            dose = 0.0
        else:
            dose = dose_up if i < up_count else dose_down
        arm.append(
            _cell(s, area=1.5 * _SCALE, lf=_BASE_LF + _SHIFT, dose=dose)
        )
    return base, arm


@pytest.mark.parametrize(
    ("up_count", "predicted", "verdict"),
    [
        (18, "up", "shifted"),
        (10, "up", "not resolvable at n=20"),
        (2, "up", "shifted against prediction"),
        (18, "down", "shifted against prediction"),
        (2, "down", "shifted"),
    ],
)
def test_paired_dose_distribution_sign_verdicts(
    monkeypatch, tmp_path, up_count, predicted, verdict,
):
    base, arm = _dose_pairs(20, up_count)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE, predicted_direction=predicted,
        base_cells=base, arm_cells=arm,
    )["paired_dose_distribution"]
    assert result["verdict"] == verdict
    assert result["n"] == 20
    assert result["k_matching_predicted_sign"] == (
        up_count if predicted == "up" else 20 - up_count
    )


def test_paired_dose_distribution_magnitude_is_unscaled(monkeypatch, tmp_path):
    base, arm = _dose_pairs(20, 18)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["paired_dose_distribution"]
    assert result["median_r"] == pytest.approx(
        math.log10(10.0), rel=1e-12,
    )
    assert result["min_r"] == pytest.approx(math.log10(0.1), rel=1e-12)
    assert result["max_r"] == pytest.approx(math.log10(10.0), rel=1e-12)


def test_zero_dose_pair_is_undefined_not_counted(monkeypatch, tmp_path):
    base, arm = _dose_pairs(20, 18, zero_seed=9005)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["paired_dose_distribution"]
    assert result["pairs_undefined"] == 1
    assert result["n"] == 19
    zero_row = next(p for p in result["paired"] if p["seed"] == 9005)
    assert zero_row["r_s"] is None


def test_k_threshold_alpha05_at_n20_is_15():
    assert htar._k_threshold_alpha05(20) == 15


def test_one_sided_tail_straddles_alpha_at_threshold():
    assert htar._binomial_one_sided_tail(20, 15) <= 0.025
    assert htar._binomial_one_sided_tail(20, 14) > 0.025


def test_paired_dose_all_undefined_is_not_resolvable(monkeypatch, tmp_path):
    seeds = [9001, 9002]
    base = [_cell(s, area=1.5, lf=_BASE_LF, dose=0.0) for s in seeds]
    arm = [
        _cell(s, area=1.5 * _SCALE, lf=_BASE_LF + _SHIFT, dose=2.0)
        for s in seeds
    ]
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["paired_dose_distribution"]
    assert result["verdict"] == "undefined: no defined pairs"
    assert result["n"] == 0


def test_missing_baseline_seed_exits(monkeypatch, tmp_path):
    base, arm = _paired()
    base = base[:1]
    with pytest.raises(SystemExit, match="no baseline cell"):
        _run(
            monkeypatch, tmp_path, scale=_SCALE,
            base_cells=base, arm_cells=arm,
        )


def test_main_writes_named_readout_json(monkeypatch, tmp_path):
    base, arm = _paired()
    _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )
    out_dir = Path(tempfile.mkdtemp(dir=REPO_ROOT))
    try:
        rc = htar.main(
            [
                "--arm-dir", str(tmp_path / "arm"),
                "--arm-tag", "htaT",
                "--scale", "0.25",
                "--predicted-direction", "up",
                "--out", str(out_dir),
            ],
        )
        assert rc == 0
        written = out_dir / "high_touch_area_readout_htaT.json"
        assert written.is_file()
        assert json.loads(written.read_text())["arm_tag"] == "htaT"
    finally:
        import shutil

        shutil.rmtree(out_dir)


def test_main_per_class_path_writes_class_map(monkeypatch, tmp_path):
    base, arm = _two_class_paired(0.5, 2.0)
    _run(
        monkeypatch, tmp_path,
        scale_by_zone_class={"cabin": 0.5, "dining": 2.0},
        base_cells=base, arm_cells=arm,
    )
    out_dir = Path(tempfile.mkdtemp(dir=REPO_ROOT))
    try:
        rc = htar.main(
            [
                "--arm-dir", str(tmp_path / "arm"),
                "--arm-tag", "htaT",
                "--scale-by-zone-class", '{"cabin": 0.5, "dining": 2.0}',
                "--predicted-direction", "down",
                "--out", str(out_dir),
            ],
        )
        assert rc == 0
        written = json.loads(
            (out_dir / "high_touch_area_readout_htaT.json").read_text()
        )
        assert "scale" not in written
        assert written["scale_by_zone_class"] == {"cabin": 0.5, "dining": 2.0}
        assert written["predicted_direction"] == "down"
    finally:
        import shutil

        shutil.rmtree(out_dir)


def test_envelope_rows_are_ordered_positive_and_finite():
    for zone_class, row in htae.build_envelope()["classes"].items():
        for key in (
            "hardware_m2",
            "broad_m2",
            "shared_m2",
            "ceiling_total_surface_m2",
        ):
            assert math.isfinite(row[key]), (zone_class, key, row[key])
            assert row[key] > 0.0, (zone_class, key, row[key])
        assert row["hardware_m2"] <= row["broad_m2"], zone_class
        assert row["broad_m2"] <= row["ceiling_total_surface_m2"], zone_class
        assert row["shared_m2"] <= row["ceiling_total_surface_m2"], zone_class
        assert row["scale_to_hardware"] == pytest.approx(
            row["hardware_m2"] / row["shipped_m2"], rel=1e-9,
        )
        assert row["scale_to_shared"] == pytest.approx(
            row["shared_m2"] / row["shipped_m2"], rel=1e-9,
        )


@pytest.mark.parametrize("zone_class", ["dining", "crew_mess", "public"])
def test_envelope_shared_reading_is_occupancy_coupled(zone_class):
    row = htae.build_envelope()["classes"][zone_class]
    assert row["shared_m2_per_occupant"] is not None
    assert math.isfinite(row["shared_m2_per_occupant"])
    assert row["shared_m2_per_occupant"] > 0.0
    assert row["shared_m2_per_occupant"] == pytest.approx(
        row["shared_m2"] / row["representative_occupancy"], rel=1e-9,
    )


def test_envelope_item_area_sources_are_the_three_labels():
    labels = {
        item["src"] for item in htae.build_envelope()["item_areas_m2"].values()
    }
    assert labels <= {"measured", "qmra", "declared"}


def test_envelope_build_is_deterministic():
    first = htae.build_envelope()
    second = htae.build_envelope()
    assert first == second


def _check(cfg: dict) -> list:
    from tools.sanity_checker import Report, _check_high_touch_area_scale

    report = Report()
    _check_high_touch_area_scale(cfg, report)
    return report.errors


def test_sanity_check_map_absent_and_valid_are_quiet():
    assert not _check({"transmission": {}})
    assert not _check(
        {
            "transmission": {
                "high_touch_area_scale": 2.0,
                "high_touch_area_scale_by_zone_class": {"cabin": 0.11},
            },
        },
    )


@pytest.mark.parametrize(
    "by_class",
    [
        4,
        {"not_a_class": 1.0},
        {"cabin": 0.0},
        {"cabin": 0.001},
        {"cabin": 1000.0},
        {"cabin": "half"},
    ],
)
def test_sanity_check_map_reports_bad_shapes_and_arms(by_class):
    errors = _check(
        {"transmission": {"high_touch_area_scale_by_zone_class": by_class}},
    )
    assert errors
    assert all(
        "high_touch_area_scale_by_zone_class" in e.message for e in errors
    )
