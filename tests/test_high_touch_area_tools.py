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


def _cell(
    seed: int,
    *,
    area: float,
    lf: float,
    calls: float = 100.0,
    clean: float = 100.0,
    capped: float = 0.0,
    dose: float = 1.0,
    req: float = 1.0,
    off: float = 1.0,
    secondaries: int = 0,
) -> dict:
    row = {
        "calls": calls,
        "calls_clean": clean,
        "calls_capped": capped,
        "sum_surface_area_m2": calls * area,
        "sum_log10_f_touch": clean * lf,
        "sum_sq_log10_f_touch": clean * (lf * lf + _LF_SIGMA**2),
    }
    return {
        "seed": seed,
        "transfer_product_witness": {
            "surface_to_hand": {"pool": {"cabin": row}, "patch": {}},
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
    scale: float,
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
    return htar.readout(arm_dir, tag, scale)


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


@pytest.mark.parametrize(
    ("arm_dose", "verdict"),
    [(4.2, "conforms"), (8.0, "departs")],
)
def test_whole_voyage_median_within_and_outside_tolerance(
    monkeypatch, tmp_path, arm_dose, verdict,
):
    base, arm = _paired(dose=arm_dose)
    result = _run(
        monkeypatch, tmp_path, scale=_SCALE,
        base_cells=base, arm_cells=arm,
    )["whole_voyage_scaling"]
    assert result["verdict"] == verdict
    assert result["median_arm_times_scale_over_base"] == pytest.approx(
        arm_dose * _SCALE, rel=1e-12,
    )


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
