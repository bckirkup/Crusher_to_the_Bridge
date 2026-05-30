"""Instrument turnaround queue tests."""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.instrument_turnaround import (
    INSTRUMENT_MICROBIO,
    INSTRUMENT_WW,
    InstrumentTurnaroundQueue,
    InstrumentTurnaroundRegistry,
    TurnaroundSpec,
)


def test_turnaround_spec_sub_epoch_fraction() -> None:
    spec = TurnaroundSpec.from_config_block({"epoch_fraction": 0.04})
    assert spec.delay_epochs == 0


def test_turnaround_spec_full_run_hours() -> None:
    spec = TurnaroundSpec.from_config_block({"full_run_hours": 48})
    assert spec.delay_epochs == 2


def test_wastewater_delay_one_epoch() -> None:
    reg = InstrumentTurnaroundRegistry({
        "hours_per_epoch": 24,
        "instruments": {INSTRUMENT_WW: {"delay_epochs": 1}},
    })
    queue = InstrumentTurnaroundQueue(reg)
    queue.submit(INSTRUMENT_WW, "Engine_Room", {"zone": "Engine_Room", "x": 1}, 0)
    pending = queue.release(0).get(INSTRUMENT_WW, {})
    assert pending["Engine_Room"]["status"] == "pending"
    released = queue.release(1).get(INSTRUMENT_WW, {})
    assert "Engine_Room" in released
    assert released["Engine_Room"]["status"] == "complete"


def test_microbiology_pending_three_epochs() -> None:
    reg = InstrumentTurnaroundRegistry({
        "instruments": {INSTRUMENT_MICROBIO: {"delay_epochs": 3}},
    })
    queue = InstrumentTurnaroundQueue(reg)
    queue.submit(INSTRUMENT_MICROBIO, "1", {"agent_id": 1}, 0)
    pending = queue.release(0).get(INSTRUMENT_MICROBIO, {})
    assert pending["1"]["status"] == "pending"
    assert pending["1"]["available_epoch"] == 3
    assert queue.release(2).get(INSTRUMENT_MICROBIO, {})["1"]["status"] == "pending"
    done = queue.release(3).get(INSTRUMENT_MICROBIO, {})
    assert done["1"]["status"] == "complete"


def test_long_read_profile_turnaround_from_json() -> None:
    path = os.path.join(REPO_ROOT, "data/config/long_read_sequencing_params.json")
    reg = InstrumentTurnaroundRegistry.load(path, repo_root=REPO_ROOT)
    flongle = reg._instruments.get("long_read_verification", {"use_profile": True})
    reg_f = InstrumentTurnaroundRegistry(
        {"hours_per_epoch": 24, "instruments": {"long_read_verification": flongle}},
        long_read_profile_turnaround={
            "epoch_fraction": 0.04,
            "full_run_hours": 16,
        },
    )
    assert reg_f.delay_epochs_for("long_read_verification") == 0
