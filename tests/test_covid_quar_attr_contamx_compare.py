"""
test_covid_quar_attr_contamx_compare.py — QUAR-CONTAMX-01 compare tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline-safe tests for ``tools/covid_quar_attr_contamx_compare.py`` and
the ``--transport-engine`` additions to
``tools/covid_attribution_arm_smoke.py``. All fixtures are synthetic —
no simulation runs.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    ScreenCell,
    enumerate_cells,
    load_design,
)
from tools import covid_attribution_arm_smoke as smoke  # noqa: E402
from tools import covid_quar_attr_contamx_compare as cmp  # noqa: E402

THETA = 1e9
ARM = "A0_declared"


def _cell(seed: int) -> ScreenCell:
    return ScreenCell(
        index=0,
        scenario_id="diamond_princess_2020",
        theta=THETA,
        infection_age_days=8.0,
        imports=1,
        seed=seed,
        arm_id=ARM,
    )


CELLS = [_cell(20200205), _cell(20200206), _cell(20200217)]


def _payload(
    seed: int,
    *,
    infections: int = 100,
    onsets: int = 12,
    during: int = 40,
    engine_class: str = "ContamXTransportEngine",
) -> dict:
    return {
        "infections_total": infections,
        "attack_rate": 0.1,
        "observables": {
            "recorded_onsets": onsets,
            "onsets_before_split_day": 3,
        },
        "infections_before_quarantine": 10,
        "infections_during_quarantine": during,
        "infections_after_quarantine": 50,
        "confined_passenger_infections_during_quarantine": 7,
        "quarantine_witness": {"confined_at_activation": 2},
        "during_quarantine_by_role": {"passenger": 30, "crew": 10},
        "during_quarantine_by_zone_class": {"cabin": 30, "corridor": 10},
        "during_quarantine_by_route": {"hvac_airborne": 20, "droplet": 20},
        "transport_engine": {
            "requested": "contamx",
            "engine_class": engine_class,
            "n_airflow_paths": 2182,
            "total_flow_m3h": 3070000.0,
        },
    }


def _write_payload(directory: Path, cell: ScreenCell, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / cell.key).write_text(
        json.dumps(payload), encoding="utf-8",
    )


def _row(seed: int, *, onsets: int = 12, during: int = 40) -> dict:
    return {
        "seed": seed,
        "theta": str(THETA),
        "arm_id": ARM,
        "recorded_onsets": str(onsets),
        "infections_during_quarantine": str(during),
        "infections_total": str(during * 3),
    }


def _write_settled_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["theta", "arm_id", "seed"] + list(cmp.SURFACE_COLUMNS[3:])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_resolve_cli_path_absolute_and_relative(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cmp, "REPO_ROOT", str(tmp_path))
    inside = cmp._resolve_cli_path("sub/dir")
    assert inside.startswith(str(tmp_path))
    absolute = cmp._resolve_cli_path(str(tmp_path / "abs"))
    assert absolute == str(tmp_path / "abs")
    with pytest.raises(ValueError):
        cmp._resolve_cli_path("../escape")


def test_load_settled_rows_filters_theta_and_arm(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cmp, "REPO_ROOT", str(tmp_path))
    settled = tmp_path / "settled.csv"
    _write_settled_csv(settled, [
        _row(1), _row(2, during=60),
        {**_row(3), "arm_id": "A2_pooled"},
        {**_row(4), "theta": "100000.0"},
    ])
    rows = cmp._load_settled_rows(str(settled), THETA, ARM)
    assert sorted(rows) == [1, 2]
    assert rows[2]["infections_during_quarantine"] == "60"


def test_payload_row_mirrors_readout_columns() -> None:
    row = cmp._payload_row(_payload(20200205), CELLS[0])
    assert row["infections_during_quarantine"] == 40
    assert row["recorded_onsets"] == 12
    assert row["ledger_events_during"] == 40
    assert row["confined_at_activation"] == 2
    assert row["during_role_passenger"] == 30
    assert row["during_role_crew"] == 10
    assert row["during_zone_cabin"] == 30
    assert row["during_route_hvac_airborne"] == 20
    assert row["engine_class"] == "ContamXTransportEngine"
    assert row["n_airflow_paths"] == 2182
    assert row["transport_engine_requested"] == "contamx"


def test_payload_row_empty_payload() -> None:
    row = cmp._payload_row({}, CELLS[0])
    assert row["infections_total"] is None
    assert row["ledger_events_during"] == 0
    assert row["during_role_passenger"] == 0
    assert row["engine_class"] is None


def test_median_empty() -> None:
    assert cmp._median([]) is None
    assert cmp._median([1.0, 5.0, 3.0]) == pytest.approx(3.0)


def test_lane_rows_reads_payloads_and_skips_missing(tmp_path) -> None:
    _write_payload(tmp_path, CELLS[0], _payload(20200205))
    _write_payload(tmp_path, CELLS[1], _payload(20200206, during=60))
    rows = cmp._lane_rows(str(tmp_path), CELLS)
    assert sorted(rows) == [20200205, 20200206]
    assert rows[20200206]["infections_during_quarantine"] == 60


def test_lane_stats_takeoff_boundary() -> None:
    by_seed = {
        1: _row(1, onsets=10, during=10),   # takeoff boundary: counts
        2: _row(2, onsets=9, during=20),    # below boundary: does not
        3: _row(3, onsets=15, during=30),
        4: {"infections_during_quarantine": None},  # missing both fields
    }
    stats = cmp._lane_stats(by_seed)
    assert stats["n"] == 4
    assert stats["takeoff_n"] == 2
    assert stats["takeoff_seeds"] == [1, 3]
    assert stats["takeoff_probability"] == pytest.approx(0.5)
    assert stats["all_seed_median"] == pytest.approx(20.0)


def _lane(seed_during: dict[int, int], *, onset: int = 12) -> dict[int, dict]:
    return {
        s: {
            "seed": s,
            "recorded_onsets": onset,
            "infections_during_quarantine": d,
            "infections_total": d * 3,
        }
        for s, d in seed_during.items()
    }


def test_verdict_shift_no_overlap() -> None:
    settled = _lane({1: 10}, onset=9)
    probe = _lane({1: 10}, onset=9)
    out = cmp._verdict_shift(settled, probe)
    assert out["band"] == "not eligible (no takeoff overlap)"
    assert out["n_both"] == 0


def test_verdict_shift_non_load_bearing() -> None:
    settled = _lane({1: 100, 2: 100})
    probe = _lane({1: 95, 2: 105})
    out = cmp._verdict_shift(settled, probe)
    assert out["band"] == "non_load_bearing_shift"
    assert out["shift"] == pytest.approx(0.0)
    assert out["n_both"] == 2


def test_verdict_shift_load_bearing() -> None:
    settled = _lane({1: 100, 2: 200})
    probe = _lane({1: 20, 2: 40})
    out = cmp._verdict_shift(settled, probe)
    assert out["band"] == "load_bearing_decrease"
    assert out["shift"] == pytest.approx(-0.8)


def test_verdict_shift_indeterminate() -> None:
    settled = _lane({1: 100, 2: 100})
    probe = _lane({1: 160, 2: 160})
    out = cmp._verdict_shift(settled, probe)
    assert out["band"] == "indeterminate"
    assert out["takeoff"]["probe_only"] == []
    assert out["takeoff"]["settled_only"] == []


def test_verdict_shift_records_takeoff_sets() -> None:
    settled = _lane({1: 100, 2: 100}, onset=12)
    settled[3] = _row(3, onsets=5, during=5)
    probe = _lane({1: 50, 3: 50}, onset=12)
    probe[2] = _row(2, onsets=5, during=5)
    out = cmp._verdict_shift(settled, probe)
    assert out["takeoff"]["probe_only"] == [3]
    assert out["takeoff"]["settled_only"] == [2]


def test_paired_deltas_and_takeoff_sets() -> None:
    probe = _lane({1: 40, 2: 60, 3: 30})
    head = _lane({1: 50, 2: 70})
    out = cmp._paired_deltas(probe, head)
    assert out["shared_seeds"] == [1, 2]
    assert out["n_shared"] == 2
    assert out["median_delta"]["infections_during_quarantine"] == pytest.approx(-10.0)
    assert out["median_delta"]["infections_total"] == pytest.approx(-30.0)
    assert out["per_seed"]["1"]["infections_during_quarantine"][
        "delta"
    ] == pytest.approx(-10.0)
    assert out["takeoff"]["probe"] == [1, 2]
    assert out["takeoff"]["head_native"] == [1, 2]
    assert out["verdict_shift_vs_head"]["band"] == "non_load_bearing_shift"


def test_paired_deltas_missing_fields() -> None:
    probe = {1: {"infections_during_quarantine": None}}
    head = _lane({1: 50})
    out = cmp._paired_deltas(probe, head)
    assert out["shared_seeds"] == [1]
    assert out["per_seed"]["1"] == {}
    assert out["median_delta"]["infections_total"] is None


def test_native_parity_clean_and_mismatch(tmp_path) -> None:
    cells = [_cell(20200205), _cell(20200206)]
    _write_payload(tmp_path, cells[0], _payload(20200205))
    _write_payload(tmp_path, cells[1], _payload(20200206))
    settled_rows = {
        20200205: {
            "theta": str(THETA), "arm_id": ARM, "seed": "20200205",
            "infections_total": "100",
            "infections_during_quarantine": "999",
        },
    }
    out = cmp._native_parity(str(tmp_path), cells, settled_rows)
    assert out["seeds_checked"] == [20200205, 20200206]
    assert out["byte_identical_to_settled"] is False
    diff = out["mismatches"][0]["diffs"]
    assert diff["infections_during_quarantine"]["settled"] == "999"
    assert diff["infections_during_quarantine"]["head"] == 40


def test_native_parity_byte_identical_and_missing(tmp_path) -> None:
    cells = [_cell(20200205), _cell(20200206)]
    _write_payload(tmp_path, cells[0], _payload(20200205))
    payload = _payload(20200205)
    settled_rows = {
        20200205: {
            col: str(cmp._payload_row(payload, cells[0]).get(col))
            for col in cmp.SURFACE_COLUMNS
            if col not in ("theta", "arm_id")
        },
    }
    settled_rows[20200205].update({"theta": str(THETA), "arm_id": ARM})
    out = cmp._native_parity(str(tmp_path), cells, settled_rows)
    assert out["seeds_checked"] == [20200205]
    assert out["byte_identical_to_settled"] is True


def _main_args(tmp_path, extra: list[str]) -> list[str]:
    design_cells = [
        c for c in enumerate_cells(load_design(
            cmp.ATTRIBUTION_DESIGN_REL, repo_root=str(REPO_ROOT),
        ))
        if c.theta == THETA and c.arm_id == ARM
    ]
    probe = tmp_path / "probe"
    for cell in design_cells[:3]:
        _write_payload(probe, cell, _payload(cell.seed))
    real = REPO_ROOT / cmp.SETTLED_SURFACE_REL
    with open(real, newline="", encoding="utf-8") as fh:
        rows = [
            r for r in csv.DictReader(fh)
            if float(r["theta"]) == THETA and r["arm_id"] == ARM
        ]
    settled = tmp_path / "settled.csv"
    with open(settled, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return [
        "--probe-dir", str(probe),
        "--theta", str(THETA),
        "--arm", ARM,
        "--settled-csv", str(settled),
        "--repo-root", str(REPO_ROOT),
    ] + extra


def test_main_end_to_end(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cmp, "REPO_ROOT", str(tmp_path))
    out_csv = tmp_path / "surface.csv"
    out_json = tmp_path / "summary.json"
    argv = _main_args(tmp_path, [
        "--native-dir", str(tmp_path / "probe"),
        "--out-csv", str(out_csv),
        "--out-json", str(out_json),
    ])
    monkeypatch.setattr(sys, "argv", ["cmp"] + argv)
    assert cmp.main() == 0
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["probe_all_contamx"] is True
    assert summary["probe_engine_classes"] == ["ContamXTransportEngine"]
    assert summary["cell"]["arm_id"] == ARM
    assert summary["settled_stats"]["takeoff_n"] > 0
    assert summary["verdict_shift"]["band"]
    assert summary["native_head_parity"]["byte_identical_to_settled"] is False
    assert summary["probe_vs_head"]["n_shared"] == 3
    lines = out_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4  # header + 3 probe cells
    assert "engine_class" in lines[0]
    assert "missing probe payloads" in capsys.readouterr().err


def test_main_no_cells_errors(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cmp, "REPO_ROOT", str(tmp_path))
    argv = [
        "--probe-dir", str(tmp_path),
        "--theta", str(THETA),
        "--arm", "no_such_arm",
        "--repo-root", str(REPO_ROOT),
    ]
    monkeypatch.setattr(sys, "argv", ["cmp"] + argv)
    with pytest.raises(SystemExit):
        cmp.main()


def test_main_missing_settled_seeds_errors(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cmp, "REPO_ROOT", str(tmp_path))
    settled = tmp_path / "thin.csv"
    _write_settled_csv(settled, [_row(20200205)])
    argv = _main_args(tmp_path, [])
    argv[argv.index("--settled-csv") + 1] = str(settled)
    monkeypatch.setattr(sys, "argv", ["cmp"] + argv)
    with pytest.raises(SystemExit):
        cmp.main()


def test_smoke_transport_engine_identity() -> None:
    paths = [SimpleNamespace(flow_rate_m3h=1.5), SimpleNamespace(flow_rate_m3h=2.5)]
    sim = SimpleNamespace(
        contam_engine=SimpleNamespace(airflow_paths=paths),
    )
    raw = {"config_overrides": {"hvac": {"transport_engine": "contamx"}}}
    ident = smoke._transport_engine_identity(sim, raw, "contamx")
    assert ident["requested"] == "contamx"
    assert ident["config_transport_engine"] == "contamx"
    assert ident["engine_class"] == "SimpleNamespace"
    assert ident["n_airflow_paths"] == 2
    assert ident["total_flow_m3h"] == pytest.approx(4.0)
    assert ident["max_path_flow_m3h"] == pytest.approx(2.5)


def test_smoke_transport_engine_identity_empty_engine() -> None:
    sim = SimpleNamespace(contam_engine=None)
    ident = smoke._transport_engine_identity(sim, {}, None)
    assert ident["requested"] == "native"
    assert ident["engine_class"] is None
    assert ident["n_airflow_paths"] == 0
    assert ident["max_path_flow_m3h"] == pytest.approx(0.0)


def test_smoke_read_back_transport_engine() -> None:
    raw = {"config_overrides": {"hvac": {"transport_engine": "contamx"}}}
    assert smoke._read_back(raw)["hvac.transport_engine"] == "contamx"
    assert smoke._read_back({"config_overrides": {}})[
        "hvac.transport_engine"
    ] is None
