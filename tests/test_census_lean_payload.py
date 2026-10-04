"""Seam tests for the ``--payload lean`` census profile in
``tools/noro_diag/growth_chain_census.py`` (MEGA-IMPACT memory lever).

The lean profile counts the twelve per-event row streams instead of
retaining them; every aggregate a consumer reads — ignited,
emitting_hosts, acquisitions_by_gen — must derive identically in either
profile, and every payload key stays present.
"""
import gzip
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

import growth_chain_census as gcc  # noqa: E402


def _emit_record(agent_id: int) -> dict:
    return {"epoch": 0, "agent_id": agent_id, "zone": "Z", "episode_load": 1.0}


def test_lean_drops_event_streams_but_keeps_emit_host_ids() -> None:
    rec = gcc.CensusRecorder(pathogen_id="p", payload_profile="lean")
    rec.record_row("emit", _emit_record(7))
    rec.record_row("emit", _emit_record(9))
    rec.record_row("deposit", {"epoch": 0, "unit": "Z", "mass": 1.0})
    assert rec.emit_rows == []
    assert rec.deposit_rows == []
    assert rec.emit_host_ids == {7, 9}
    assert dict(rec.dropped_counts) == {"emit": 2, "deposit": 1}


def test_full_retains_rows_and_still_tracks_emit_host_ids() -> None:
    rec = gcc.CensusRecorder(pathogen_id="p", payload_profile="full")
    rec.record_row("emit", _emit_record(7))
    assert len(rec.emit_rows) == 1
    assert rec.emit_host_ids == {7}
    assert dict(rec.dropped_counts) == {}


def test_lean_retains_streams_outside_the_dropped_set() -> None:
    rec = gcc.CensusRecorder(pathogen_id="p", payload_profile="lean")
    rec.record_row("acquisition", {"agent_id": 7, "gen": 1})
    rec.census_rows.append({"epoch": 0, "infected": 1})
    assert len(rec.acquisition_rows) == 1
    assert len(rec.census_rows) == 1


def _core_stub() -> SimpleNamespace:
    return SimpleNamespace(
        zone_types={},
        caregiver_telemetry={"caregiver_responses": 3, "caregiver_reports": 2},
        common_source_telemetry={"events_ill_handler": 1, "takers_served": 5},
        _cs_windows={
            ("norwalk_gi", "Windjammer", "Meal:Lunch", 1): {
                "event": {
                    "event_id": "cs-norwalk_gi-1",
                    "zone": "Windjammer",
                    "meal": "Meal:Lunch",
                    "source_kind": "ill_handler",
                    "start_epoch": 25,
                    "end_epoch": 26,
                    "servings_taken": 5,
                    "taker_ids": [1, 2, 3, 4, 5],
                    "per_serving_dose": 1.5,
                },
            },
            ("norwalk_gi", "CafeBakery", "Meal:Dinner", 2): {},
        },
    )


def _spec_stub() -> dict:
    return {
        "run": {"random_seed": 1, "num_epochs": 2},
        "campaign_parameters": {"num_agents": 10},
        "catalog": {"platform_id": "p"},
    }


def test_summarise_lean_preserves_aggregates() -> None:
    rec = gcc.CensusRecorder(pathogen_id="p", payload_profile="lean")
    rec.record_row("emit", _emit_record(7))
    rec.acquired_ids.add(42)
    rec.acquisition_rows.append({"agent_id": 42, "gen": 1})
    payload = gcc._summarise_run(rec, _spec_stub(), 1.0, _core_stub())
    assert payload["ignited"] is True
    assert payload["emitting_hosts"] == [7]
    assert payload["n_acquired"] == 1
    assert payload["acquisitions_by_gen"] == {"1": 1}
    assert payload["emits"] == []
    assert payload["deposits"] == []
    assert payload["meta"]["payload_profile"] == "lean"
    assert payload["meta"]["row_stream_counts"]["emit"] == 1
    # Mechanism blocks are present in both profiles.
    assert payload["common_source"]["telemetry"]["takers_served"] == 5
    assert len(payload["common_source"]["events"]) == 1
    assert payload["common_source"]["events"][0]["zone"] == "Windjammer"
    assert payload["caregiver_telemetry"]["caregiver_reports"] == 2


def test_row_stream_counts_report_retained_plus_dropped() -> None:
    rec = gcc.CensusRecorder(pathogen_id="p", payload_profile="lean")
    rec.record_row("emit", _emit_record(7))
    counts = gcc._row_stream_counts(rec)
    assert counts["emit"] == 1
    assert counts["deposit"] == 0
    full = gcc.CensusRecorder(pathogen_id="p", payload_profile="full")
    full.record_row("emit", _emit_record(7))
    assert gcc._row_stream_counts(full)["emit"] == 1


def test_append_rss_member_adds_third_member(tmp_path: Path) -> None:
    zip_path = gcc._write_run_zip(
        tmp_path, "tier", "run_x",
        {
            "ignited": True, "n_imports": 1, "n_acquired": 2,
            "acquisitions_by_gen": {"1": 2},
            "meta": {
                "epochs": 2,
                "payload_profile": "lean",
                "voyage_rss_mb": 1024.0,
                "fold_rss_mb": 2048.0,
            },
            "common_source": {"events": [], "telemetry": {}},
            "caregiver_telemetry": {},
        },
        {
            "parameters": {}, "summary": {}, "cost_accounting": {},
            "derived": {}, "timeseries": [],
        },
        {"resolved": {}},
    )
    sampler = gcc._RssSampler(interval_s=999.0)  # never starts the thread
    sampler.samples.append([0.0, 128.0])
    gcc._append_rss_member(zip_path, sampler)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "summary.json" in names
        assert "growth_census.json.gz" in names
        assert "rss_samples.json" in names
        rss = json.loads(zf.read("rss_samples.json"))
        assert rss["peak_rss_mb"] > 0
        assert rss["samples"] == [[0.0, 128.0]]
        census = json.loads(
            gzip.decompress(zf.read("growth_census.json.gz")).decode(),
        )
        assert census["ignited"] is True
