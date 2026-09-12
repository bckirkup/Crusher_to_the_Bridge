"""The staged campaign's stopping rule: graded, bounded, and refuses a repeat."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telemetry_buffer.observation_model import staged_posting_readout as spr

REPO_ROOT = Path(__file__).resolve().parents[1]


def _row(seed: int, pax_rate: float, crew_rate: float = 0.0, hull: str = "classic_cruise_1900"):
    return {
        "seed": seed,
        "hull": hull,
        "passenger_complement": 1350,
        "crew_complement": 560,
        "voyage_days": 7.0,
        "reported_case_attack_rate_passenger": pax_rate,
        "reported_case_attack_rate_crew": crew_rate,
    }


def _stream(path: Path, point: int, rows: list[dict], block: int = 0) -> Path:
    path.write_text(
        json.dumps({"point_index": point, "block_index": block, "rows": rows}) + "\n",
    )
    return path


def test_posterior_mass_above_the_band_rises_with_postings() -> None:
    above = [spr.band_mass(k, 48)["above"] for k in range(0, 6)]
    assert above == sorted(above)
    assert above[0] < 0.5 < above[-1]
    for k in range(6):
        mass = spr.band_mass(k, 48)
        assert abs(mass["below"] + mass["inside"] + mass["above"] - 1.0) < 1e-9


def test_a_small_quiet_cell_continues_and_a_loud_one_stops() -> None:
    assert spr.decision(spr.band_mass(0, 24)) == spr.CONTINUE
    assert spr.decision(spr.band_mass(6, 24)) == spr.STOP_ABOVE
    assert spr.decision(spr.band_mass(0, 1500)) == spr.STOP_BELOW


def test_a_stop_needs_both_channels_settled() -> None:
    # Crew posts on every voyage, passengers never: the or-rule is decided
    # high, the passenger channel is still open, so the cell continues.
    rows = [_row(seed, 0.0, crew_rate=0.05) for seed in range(24)]
    cell = spr.score_cell(rows)
    assert cell["channels"]["or_rule"]["decision"] == spr.STOP_ABOVE
    assert cell["channels"]["passenger"]["decision"] == spr.CONTINUE
    assert cell["decision"] == spr.CONTINUE


def test_stages_pool_by_seed_and_the_next_stage_resumes_past_them(tmp_path: Path) -> None:
    out = REPO_ROOT / "telemetry_buffer" / "observation_model"
    first = _stream(out / "test_stage1.jsonl", 46, [_row(s, 0.0) for s in range(500, 524)])
    second = _stream(out / "test_stage2.jsonl", 46, [_row(s, 0.0) for s in range(524, 548)])
    try:
        report = spr.readout([first, second])
        cell = report["cells"]["classic_cruise_1900"][46]
        assert cell["eligible_runs"] == 48
        assert cell["seeds"] == list(range(500, 548))
        plan = report["next_stage"]["classic_cruise_1900"]
        assert plan == {"only_points": [46], "seed_base": 548, "seeds": 48}
        with pytest.raises(SystemExit, match="appears twice"):
            spr.readout([first, first])
    finally:
        first.unlink()
        second.unlink()


def test_hulls_are_separate_cells_and_a_decided_hull_has_no_next_points(tmp_path: Path) -> None:
    out = REPO_ROOT / "telemetry_buffer" / "observation_model"
    path = out / "test_stage_mixed.jsonl"
    quiet = [_row(s, 0.0, hull="expedition_cruise_450") for s in range(500, 524)]
    loud = [_row(s, 0.05, hull="mega_cruise_5000") for s in range(500, 524)]
    path.write_text(
        json.dumps({"point_index": 12, "block_index": 0, "rows": quiet}) + "\n"
        + json.dumps({"point_index": 12, "block_index": 0, "rows": loud}) + "\n",
    )
    try:
        report = spr.readout([path])
        assert report["cells"]["mega_cruise_5000"][12]["decision"] == spr.STOP_ABOVE
        assert report["cells"]["expedition_cruise_450"][12]["decision"] == spr.CONTINUE
        assert report["next_stage"]["mega_cruise_5000"]["only_points"] == []
        assert report["next_stage"]["expedition_cruise_450"]["only_points"] == [12]
    finally:
        path.unlink()


def test_each_hull_is_scored_against_its_own_record() -> None:
    bands = {hull: spr.hull_posting_band(hull) for hull in spr.HULL_TO_GRT_BANDS}
    for low, high in bands.values():
        assert 0.0 < low < high < 1.0
    # A hull that can occupy several tonnage bands carries its denominator
    # uncertainty as width; one confined to a single band is narrower.
    widths = {hull: high - low for hull, (low, high) in bands.items()}
    multi = [h for h, b in spr.HULL_TO_GRT_BANDS.items() if len(b) > 1]
    single = [h for h, b in spr.HULL_TO_GRT_BANDS.items() if len(b) == 1]
    assert multi
    assert single
    assert max(widths[h] for h in multi) > min(widths[h] for h in single)
    # Asking for more mass widens the band; an unmapped hull falls back.
    narrow = spr.hull_posting_band(single[0], band_mass=0.5)
    assert narrow[0] > bands[single[0]][0]
    assert narrow[1] < bands[single[0]][1]
    assert spr.hull_posting_band("no_such_hull") == spr.A9_BAND


def test_the_band_decides_the_verdict(tmp_path: Path) -> None:
    rows = [_row(seed, 0.04 if seed < 2 else 0.0) for seed in range(40)]
    loud = spr.score_cell(rows, band=(0.001, 0.005))
    quiet = spr.score_cell(rows, band=(0.02, 0.30))
    assert loud["channels"]["passenger"]["above"] > quiet["channels"]["passenger"]["above"]
    assert loud["band"] == [0.001, 0.005]
