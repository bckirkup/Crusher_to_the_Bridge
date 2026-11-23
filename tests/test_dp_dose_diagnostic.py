"""Coverage for the Checkpoint B dose diagnostic (tools/dp_dose_diagnostic.py)."""
from __future__ import annotations

import errno
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.dp_dose_diagnostic import (  # noqa: E402
    DoseLedger,
    _quantiles,
    _suspend_secondary_transmission,
    PATHOGEN_ID,
)


def _ledger() -> DoseLedger:
    zone_meta = {
        "PC_D8_P_M": "Cabin_Corridor",
        "MainGalley": "Dining",
        "NeptunePool": "Venue",
    }
    return DoseLedger(zone_meta, {1: "PC_D8_P_M"}, {9})


def test_suspend_scale_pins_near_zero() -> None:
    raw = {
        "pathogen_overrides": {
            PATHOGEN_ID: {
                "dose_response": {"susceptibility_scale": 100.0},
            },
        },
    }
    _suspend_secondary_transmission(raw)
    scale = raw["pathogen_overrides"][PATHOGEN_ID][
        "dose_response"]["susceptibility_scale"]
    assert 0 < scale < 1e-20


def test_suspend_scale_requires_resolved_block() -> None:
    try:
        _suspend_secondary_transmission({})
    except SystemExit as exc:
        assert "susceptibility_scale" in str(exc)
    else:
        raise AssertionError("missing dose_response block was tolerated")


def test_observe_attributes_dose_deltas() -> None:
    ledger = _ledger()
    source = SimpleNamespace(
        agent_id=9, role="passenger", current_location="GrandPlaza",
        infection_status="INFECTED", illness_status="NOT_ILL",
        current_shedding=1.5, ashore=False,
    )
    pax = SimpleNamespace(
        agent_id=1, role="passenger", current_location="PC_D8_P_M",
        cumulative_exposure={PATHOGEN_ID: 0.0},
    )
    crew = SimpleNamespace(
        agent_id=2, role="crew", current_location="MainGalley",
        cumulative_exposure={PATHOGEN_ID: 0.25},
    )
    engine = SimpleNamespace(agents=[source, pax, crew], epoch=3)
    ledger.observe(SimpleNamespace(engine=engine), None)
    crew.cumulative_exposure[PATHOGEN_ID] = 0.5
    crew.current_location = "NeptunePool"
    engine.epoch = 4
    ledger.observe(SimpleNamespace(engine=engine), None)

    # 0.25 dosed in a Dining zone, 0.25 more while outdoor.
    assert ledger.dose_by_setting == {"dining": 0.25, "outdoor": 0.25}
    assert ledger.dose_by_role == {"crew": 0.5}
    # The source is echoed each epoch but never dose-attributed.
    assert len(ledger.source_trace) == 2
    assert ledger.source_trace[1]["current_shedding"] == 1.5
    assert all(t["agent_id"] == 9 for t in ledger.source_trace)


def test_quantiles() -> None:
    assert _quantiles([]) == {}
    q = _quantiles([1.0, 2.0, 3.0, 4.0])
    assert q["p50"] == 2.5
    assert set(q) == {"p50", "p90", "p99"}


def test_out_symlink_planted_at_write_refused(tmp_path, monkeypatch) -> None:
    """A link that appears after validation must still be refused."""
    import tools.dp_dose_diagnostic as diag
    import picard_framework.run_spec as run_spec
    from picard_framework.simulation import ship_simulation as ss

    link = tmp_path / "link.json"

    class FakeSim:
        def __init__(self, spec, display=False):
            self.engine = SimpleNamespace(
                agents=[
                    SimpleNamespace(
                        agent_id=9, role="passenger",
                        home_zone="PC_D8_P_M", current_location="GrandPlaza",
                        infection_status="INFECTED", illness_status="NOT_ILL",
                        current_shedding=1.0, ashore=False,
                        cumulative_exposure={}, dose_response_susceptibility={},
                        cumulative_exposure_by_route={},
                    ),
                ],
                explicit_seed_agent_ids=[9],
            )
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
        ["dp_dose_diagnostic", "--seeds", "20200205", "--num-epochs", "1",
         "--out", str(link)],
    )
    try:
        diag.main()
    except OSError as exc:
        assert link.is_symlink()
        assert exc.errno == errno.ELOOP
    else:
        raise AssertionError("write followed a post-check symlink")
