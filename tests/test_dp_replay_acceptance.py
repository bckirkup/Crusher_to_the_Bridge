"""Coverage for the DP replay acceptance harness (tools/dp_replay_acceptance.py)."""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.dp_replay_acceptance import MovementLedger  # noqa: E402


def _ledger() -> MovementLedger:
    zone_meta = {
        "PC_D8_P_M": "Cabin_Corridor",
        "MainGalley": "Dining",
        "NeptunePool": "Venue",
        "PromGalleria": "Venue",
    }
    return MovementLedger(zone_meta, {1: "PC_D8_P_M"})


def test_classify_buckets() -> None:
    ledger = _ledger()
    pax = SimpleNamespace(agent_id=1, role="passenger")
    assert ledger.classify("PC_D8_P_M", pax) == "cabin"
    assert ledger.classify("MainGalley", pax) == "dining"
    assert ledger.classify("NeptunePool", pax) == "outdoor"
    assert ledger.classify("PromGalleria", pax) == "corridor"
    assert ledger.classify("Ashore", pax) == "ashore"


def test_observe_records_bounded_buckets() -> None:
    ledger = _ledger()
    agent = SimpleNamespace(
        agent_id=1, role="passenger", current_location="PC_D8_P_M",
    )
    engine = SimpleNamespace(
        agents=[agent], epoch=0, active_sop_names=[],
    )
    sim = SimpleNamespace(engine=engine, epoch=390)
    ledger.observe(sim, None)
    engine.active_sop_names = [
        "Diamond Princess Cabin Quarantine (2020-02-05)",
    ]
    sim.epoch = engine.epoch = 391
    ledger.observe(sim, None)
    engine.active_sop_names = []
    sim.epoch = engine.epoch = 745
    ledger.observe(sim, None)
    assert "passenger|pre_quarantine" in ledger.hours
    assert "passenger|quarantine" in ledger.hours
    assert "passenger|post_release" in ledger.hours
    # Epoch 391 is inside confinement; 390 and 745 are not.
    assert ledger.home_fraction[391] == (1, 1)
    assert ledger.home_fraction[390] == (1, 1)  # at home pre-quarantine too
    assert 745 not in ledger.home_fraction or ledger.home_fraction[745] == (1, 1)


def test_main_rejects_unexpected_platform_id(tmp_path, monkeypatch) -> None:
    import tools.dp_replay_acceptance as acc

    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--num-epochs", "4",
         "--out", str(tmp_path / "r.json")],
    )
    # A platform_id that is not a bare directory name must be refused
    # before any layout path is opened.
    monkeypatch.setattr(
        acc, "prepare_cell_run_spec",
        lambda *a, **k: {"platform_id": "../../etc"},
    )
    try:
        acc.main()
    except SystemExit as exc:
        assert "unexpected platform id" in str(exc)
    else:
        raise AssertionError("main() accepted a traversal platform id")


def test_main_smoke_writes_readout(tmp_path, monkeypatch, capsys) -> None:
    import tools.dp_replay_acceptance as acc

    out = tmp_path / "readout.json"
    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--num-epochs", "48", "--out", str(out)],
    )
    assert acc.main() == 0
    readout = json.loads(out.read_text())
    assert readout["epochs"] == 48
    assert readout["arm"] == "replay_niid"
    assert readout["person_hours"]
    assert readout["confinement_witness"] == {}
