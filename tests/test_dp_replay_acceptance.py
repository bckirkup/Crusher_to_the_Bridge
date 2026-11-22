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
        agents=[agent], epoch=0, quarantined_ids=set(),
    )
    sim = SimpleNamespace(engine=engine, epoch=390)
    ledger.observe(sim, None)
    engine.quarantined_ids = {1}
    sim.epoch = engine.epoch = 391
    ledger.observe(sim, None)
    engine.quarantined_ids = set()
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


def test_main_rejects_outside_out_before_sim(monkeypatch) -> None:
    import tools.dp_replay_acceptance as acc

    called = {"design": False}
    monkeypatch.setattr(
        acc, "load_design",
        lambda *a, **k: called.update(design=True) or {},
    )
    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--out", "/etc/evil.json"],
    )
    try:
        acc.main()
    except SystemExit as exc:
        assert "--out must be under the repo" in str(exc)
    else:
        raise AssertionError("main() accepted an out-of-tree --out")
    assert called["design"] is False


def test_main_rejects_outside_design_before_sim(monkeypatch) -> None:
    import tools.dp_replay_acceptance as acc

    called = {"design": False}
    monkeypatch.setattr(
        acc, "load_design",
        lambda *a, **k: called.update(design=True) or {},
    )
    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--design", "/etc/passwd"],
    )
    try:
        acc.main()
    except SystemExit as exc:
        assert "--design must be under the repo" in str(exc)
    else:
        raise AssertionError("main() accepted an out-of-tree --design")
    assert called["design"] is False


def test_out_symlink_to_outside_rejected(tmp_path, monkeypatch) -> None:
    import tools.dp_replay_acceptance as acc

    link = tmp_path / "link.json"
    link.symlink_to("/etc/evil.json")
    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--num-epochs", "4", "--out", str(link)],
    )
    try:
        acc.main()
    except SystemExit as exc:
        assert "--out must be under the repo" in str(exc)
    else:
        raise AssertionError("--out followed a symlink outside the roots")


def test_out_symlink_planted_at_write_refused(tmp_path, monkeypatch) -> None:
    """A link that appears after validation must still be refused."""
    import tools.dp_replay_acceptance as acc
    import picard_framework.run_spec as run_spec
    from picard_framework.simulation import ship_simulation as ss

    link = tmp_path / "link.json"

    class FakeSim:
        def __init__(self, spec, display=False):
            self.engine = SimpleNamespace(agents=[], _rhythm=None)
            self.num_epochs = 1
            self.epoch_observer = None

        def initialize(self):
            pass

        def step(self):
            link.symlink_to("/etc/evil.json")

    monkeypatch.setattr(
        run_spec, "PicardRunSpec",
        SimpleNamespace(
            from_picard_dict=staticmethod(lambda *a, **k: object()),
        ),
    )
    monkeypatch.setattr(ss, "ShipSimulation", FakeSim)
    monkeypatch.setattr(
        sys, "argv",
        ["dp_replay_acceptance", "--num-epochs", "1", "--out", str(link)],
    )
    try:
        acc.main()
    except OSError:
        pass  # O_NOFOLLOW refused the post-check symlink
    else:
        raise AssertionError("write followed a post-check symlink")


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
