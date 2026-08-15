"""Coverage for the VSP degradation post-processor."""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from picard_framework.analysis import vsp_degradation_postprocess as vsp


def _zip_bytes(payload: object, *, member: str = "summary.json") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member, json.dumps(payload))
    return stream.getvalue()


def _summary(
    *,
    run_id: str = "run-1",
    tier_id: str = "threshold_compliance",
    platform_id: str = "mega_cruise_5000",
    parameters: dict | None = None,
    derived: dict | None = None,
) -> dict:
    params = {
        "tier_id": tier_id,
        "platform_id": platform_id,
        "pathogen": "norovirus",
        "seed": 17,
        "dose_adjustment": 10.4,
        "density_exponent": 0.8,
        "vsp_threshold": 0.12,
        "detection_delay_epochs": 3,
        "isolation_compliance": 0.7,
        "sick_call_probability": 0.6,
    }
    params.update(parameters or {})
    values = {
        "attack_rate": 0.24,
        "outbreak_occurred": "true",
        "peak_prevalence": 8,
    }
    values.update(derived or {})
    return {"run_id": run_id, "parameters": params, "derived": values}


def _write_zip(path: Path, payload: dict, *, member: str = "summary.json") -> None:
    path.write_bytes(_zip_bytes(payload, member=member))


def test_summary_from_zip_maps_fields_and_finds_nested_summary() -> None:
    row = vsp._summary_from_zip_bytes(
        _zip_bytes(_summary(), member="run-1/summary.json"),
        "fallback.zip",
    )

    assert row is not None
    assert row["run_id"] == "run-1"
    assert row["tier_id"] == "threshold_compliance"
    assert row["platform_id"] == "mega_cruise_5000"
    assert row["pathogen"] == "norovirus"
    assert row["seed"] == 17
    assert row["dose_adjustment"] == pytest.approx(10.4)
    assert row["density_exponent"] == pytest.approx(0.8)
    assert row["attack_rate"] == pytest.approx(0.24)
    assert row["peak_prevalence"] == 8


@pytest.mark.parametrize(
    ("data", "payload", "member"),
    [
        (b"not a zip", None, "summary.json"),
        (_zip_bytes({"parameters": {}}), {}, "other.json"),
        (_zip_bytes({}, member="summary.json"), b"{", "summary.json"),
        (_zip_bytes([], member="summary.json"), [], "summary.json"),
    ],
)
def test_summary_from_zip_rejects_invalid_summaries(
    data: bytes,
    payload: object,
    member: str,
) -> None:
    if payload == {}:
        data = _zip_bytes(payload, member=member)
    elif payload == b"{":
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(member, payload)
        data = stream.getvalue()

    row = vsp._summary_from_zip_bytes(data, "bad.zip")

    assert row is None


def test_summary_from_zip_uses_nominal_fallbacks_and_filename_run_id() -> None:
    defaults = vsp._summary_from_zip_bytes(
        _zip_bytes(
            {
                "parameters": {},
                "derived": {},
            }
        ),
        "derived-run.zip",
    )
    lockdown = vsp._summary_from_zip_bytes(
        _zip_bytes(
            {
                "parameters": {"lockdown_attack_rate": 0.23},
                "derived": {},
            }
        ),
        "lockdown-run.zip",
    )
    explicit = vsp._summary_from_zip_bytes(
        _zip_bytes(
            {
                "parameters": {
                    "vsp_threshold": 0.31,
                    "lockdown_attack_rate": 0.23,
                },
                "derived": {},
            }
        ),
        "explicit-run.zip",
    )

    assert defaults is not None
    assert lockdown is not None
    assert explicit is not None
    assert defaults["run_id"] == "derived-run"
    assert defaults["vsp_threshold"] == pytest.approx(vsp.NOMINAL["vsp_threshold"])
    assert lockdown["vsp_threshold"] == pytest.approx(0.23)
    assert explicit["vsp_threshold"] == pytest.approx(0.31)
    assert defaults["detection_delay"] == vsp.NOMINAL["detection_delay"]
    assert defaults["isolation_compliance"] == pytest.approx(
        vsp.NOMINAL["isolation_compliance"]
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, 1),
        ("true", 1),
        ("YES", 1),
        (1, 1),
        (False, 0),
        ("false", 0),
        ("no", 0),
        (0, 0),
    ],
)
def test_summary_from_zip_coerces_outbreak_values(value: object, expected: int) -> None:
    row = vsp._summary_from_zip_bytes(
        _zip_bytes(_summary(derived={"outbreak_occurred": value})),
        "outbreak.zip",
    )

    assert row is not None
    assert row["outbreak_occurred"] == expected


def _write_tar(path: Path, members: list[tuple[str, bytes]]) -> None:
    with tarfile.open(path, "w") as archive:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def test_iter_summaries_equivalent_for_directory_tar_and_flat_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    summaries = {
        "a.zip": _zip_bytes(_summary(run_id="a", tier_id="threshold_compliance")),
        "b.zip": _zip_bytes(
            _summary(
                run_id="b",
                tier_id="delay_reporting",
                platform_id="expedition_cruise_450",
                derived={"attack_rate": 0.11},
            )
        ),
    }
    zips = tmp_path / "zips"
    zips.mkdir()
    for name, data in summaries.items():
        (zips / name).write_bytes(data)

    directory_rows = list(vsp.iter_summaries(str(tmp_path)))

    tar_source = tmp_path / "tar_source"
    tar_source.mkdir()
    _write_tar(tar_source / "run_zips.tar", list(summaries.items()))
    tar_rows = list(vsp.iter_summaries(str(tar_source)))

    flat_source = tmp_path / "flat_source"
    flat_source.mkdir()
    for name, data in summaries.items():
        (flat_source / name).write_bytes(data)
    flat_rows = list(vsp.iter_summaries(str(flat_source)))

    def identities(rows: list[dict]) -> set[tuple[str, float]]:
        return {(str(row["run_id"]), float(row["attack_rate"])) for row in rows}

    assert identities(directory_rows) == identities(tar_rows)
    assert identities(directory_rows) == identities(flat_rows)


@pytest.mark.parametrize(
    ("tier_id", "expected"),
    [
        ("threshold_compliance", "threshold_x_compliance"),
        ("delay_reporting", "delay_x_reporting"),
        ("delay_scp", "delay_x_reporting"),
        ("delay_sick", "delay_x_reporting"),
        ("worst_gradient", "worst_case_gradient"),
        ("vsp_threshold", "fat_vsp_threshold"),
        ("vd1_vsp_sweep", "fat_vsp_threshold"),
        ("detection_delay", "fat_detection_delay"),
        ("isolation_compliance", "fat_isolation_compliance"),
        ("sick_call", "fat_sick_call_probability"),
        ("vd1_det_sweep", "fat_detection_delay"),
        ("vd1_iso_sweep", "fat_isolation_compliance"),
        ("vd1_scp_sweep", "fat_sick_call_probability"),
        ("vd2_other", "interaction_other"),
        ("unclassified", "unclassified"),
    ],
)
def test_panel_name_classification(tier_id: str, expected: str) -> None:
    assert vsp._panel_name(tier_id) == expected


def _rows() -> list[dict]:
    return [
        {
            "cell": "a",
            "platform_id": "mega_cruise_5000",
            "attack_rate": 0.2,
            "outbreak_occurred": 0,
        },
        {
            "cell": "a",
            "platform_id": "mega_cruise_5000",
            "attack_rate": 0.4,
            "outbreak_occurred": 1,
        },
        {
            "cell": "b",
            "platform_id": "mega_cruise_5000",
            "attack_rate": 0.8,
            "outbreak_occurred": 1,
        },
    ]


def test_aggregate_cells_preserves_counts_bounds_and_grouping() -> None:
    output = vsp.aggregate_cells(_rows(), ("cell",))

    assert sum(int(row["n_runs"]) for row in output) == len(_rows())
    assert all(0 <= float(row["outbreak_rate"]) <= 1 for row in output)
    group_a = next(row for row in output if row["cell"] == "a")
    assert group_a["mean_attack_rate"] == pytest.approx(0.3)
    assert group_a["n_runs"] == 2


def test_aggregate_cells_outbreak_rate_rises_with_more_outbreak_rows() -> None:
    low = vsp.aggregate_cells(
        [{"cell": "x", "attack_rate": 0.2, "outbreak_occurred": 0}],
        ("cell",),
    )[0]["outbreak_rate"]
    high = vsp.aggregate_cells(
        [
            {"cell": "x", "attack_rate": 0.2, "outbreak_occurred": 1},
            {"cell": "x", "attack_rate": 0.2, "outbreak_occurred": 1},
        ],
        ("cell",),
    )[0]["outbreak_rate"]

    assert high > low


def test_platform_gap_table_sign_boundary_missing_platform_and_counts() -> None:
    cells = [
        {
            "cell": "signed",
            "platform_id": "expedition_cruise_450",
            "mean_attack_rate": 0.23,
            "n_runs": 4,
        },
        {
            "cell": "signed",
            "platform_id": "mega_cruise_5000",
            "mean_attack_rate": 0.10,
            "n_runs": 5,
        },
        {
            "cell": "below",
            "platform_id": "expedition_cruise_450",
            "mean_attack_rate": 0.10 + vsp.SHADOW_BREAK_PP - 0.001,
            "n_runs": 2,
        },
        {
            "cell": "below",
            "platform_id": "mega_cruise_5000",
            "mean_attack_rate": 0.10,
            "n_runs": 3,
        },
        {
            "cell": "above",
            "platform_id": "expedition_cruise_450",
            "mean_attack_rate": 0.10 + vsp.SHADOW_BREAK_PP + 0.001,
            "n_runs": 6,
        },
        {
            "cell": "above",
            "platform_id": "mega_cruise_5000",
            "mean_attack_rate": 0.10,
            "n_runs": 7,
        },
        {
            "cell": "missing",
            "platform_id": "mega_cruise_5000",
            "mean_attack_rate": 0.3,
            "n_runs": 8,
        },
    ]
    output = vsp.platform_gap_table(cells, ("cell",))

    signed = next(row for row in output if row["cell"] == "signed")
    below = next(row for row in output if row["cell"] == "below")
    above = next(row for row in output if row["cell"] == "above")
    missing = next(row for row in output if row["cell"] == "missing")
    assert signed["gap_expedition_minus_mega"] == pytest.approx(0.13)
    assert signed["abs_gap"] == pytest.approx(0.13)
    assert signed["n_expedition_cruise_450"] == 4
    assert signed["n_mega_cruise_5000"] == 5
    assert below["shadow_broken"] == 0
    assert above["shadow_broken"] == 1
    assert missing["gap_expedition_minus_mega"] is None
    assert missing["abs_gap"] is None
    assert missing["shadow_broken"] is None


def test_run_writes_aggregate_outputs_without_matplotlib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "zips"
    source.mkdir()
    _write_zip(source / "run.zip", _summary(run_id="run", tier_id="vsp_threshold"))
    out = tmp_path / "analysis"
    monkeypatch.setattr(vsp, "_matplotlib_or_none", lambda: (None, None))

    result = vsp.run(str(source), str(out))

    assert result == 0
    assert (out / "run_summary.csv").is_file()
    assert (out / "aggregate_fat_vsp_threshold.csv").is_file()
    assert (out / "report.md").is_file()
    assert (out / "manifest.json").is_file()
    assert "run" in (out / "run_summary.csv").read_text(encoding="utf-8")
