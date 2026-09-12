"""Path containment for the adj-stratified expedition readout (S8707)."""

from __future__ import annotations

from pathlib import Path

import pytest

from telemetry_buffer.observation_model import adj_stratified_readout as asr


def test_load_rejects_stage_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "arrays"
    root.mkdir()
    monkeypatch.setattr(asr, "REPO_ROOT", tmp_path)
    with pytest.raises(ValueError, match="Invalid stage"):
        asr.load("../escape", root=str(root))


def test_load_rejects_root_outside_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(asr, "REPO_ROOT", repo)
    with pytest.raises(ValueError, match="escapes repository root"):
        asr.load("threearm_expedition_base", root=str(outside))


def test_load_reads_contained_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    stage = repo / "arrays" / "threearm_expedition_base" / "0001"
    stage.mkdir(parents=True)
    record = {
        "point_index": 1,
        "factors": {asr.ADJ: 5.0, asr.BOARDING_PAX: 0.01},
        "runs": [
            {
                "seed": 7,
                "infection_attack_rate_passenger": 0.1,
                "infection_attack_rate_crew": 0.05,
                "reported_case_attack_rate_passenger": 0.04,
                "reported_case_attack_rate_crew": 0.0,
                "took_off": True,
            },
        ],
    }
    (stage / "cell.jsonl").write_text(
        __import__("json").dumps(record) + "\n", encoding="utf-8",
    )
    monkeypatch.setattr(asr, "REPO_ROOT", repo)
    rows, factors = asr.load("threearm_expedition_base", root=str(repo / "arrays"))
    assert factors[1][asr.ADJ] == pytest.approx(5.0)
    assert "p0001_s7" in rows
