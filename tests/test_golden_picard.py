"""
test_golden_picard.py – ShipSimulation golden parity vs orchestrator.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the same seed / config, assert key telemetry fields match between
orchestrator.py subprocess output and ShipSimulation.step() loop.

Closes #87.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

HISTORY_PATH = os.path.join(REPO_ROOT, "telemetry_buffer", "simulation_history.json")
GOLDEN_EPOCHS = 24
GOLDEN_SEED = 42
GOLDEN_LAST = GOLDEN_EPOCHS - 1


def _run_orchestrator() -> list[dict[str, Any]]:
    env = {**os.environ, "PYTHONPATH": REPO_ROOT, "PYTHONUTF8": "1"}
    result = subprocess.run(
        [sys.executable, "orchestrator.py", "--epochs", str(GOLDEN_EPOCHS)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, f"orchestrator failed: {result.stderr}"
    with open(HISTORY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _run_picard() -> list[dict[str, Any]]:
    from picard_framework import PicardRunSpec, ShipSimulation

    spec = PicardRunSpec.from_legacy_yaml(
        repo_root=REPO_ROOT,
        num_epochs=GOLDEN_EPOCHS,
    )
    sim = ShipSimulation(spec, display=False)
    result = sim.run()
    return result.history


def _fingerprint(history: list[dict[str, Any]], epoch: int) -> dict[str, Any]:
    rec = history[epoch]
    summary = rec.get("summary", {})
    cost = rec.get("cost_accounting", {})
    return {
        "susceptible": summary.get("susceptible"),
        "infected": summary.get("infected"),
        "symptomatic": summary.get("symptomatic"),
        "recovered": summary.get("recovered"),
        "immune": summary.get("immune"),
        "trigger_status": rec.get("trigger_status"),
        "total_financial_usd": cost.get("total_financial_usd"),
    }


@pytest.mark.timeout(240)
def test_picard_golden_summary_and_trigger() -> None:
    """ShipSimulation.run() must reproduce golden SIR summary and trigger."""
    picard_history = _run_picard()
    assert len(picard_history) >= GOLDEN_LAST + 1
    fp = _fingerprint(picard_history, GOLDEN_LAST)
    # Updated 2026-08-02: density_dependent contact_mode default (α=0.5).
    assert fp["susceptible"] == 0
    assert fp["infected"] == 0
    assert fp["symptomatic"] == 0
    assert fp["recovered"] == 16
    assert fp["immune"] == 4
    assert fp["trigger_status"] == "CONFIRMED"


@pytest.mark.timeout(240)
def test_picard_cost_accounting_nonzero() -> None:
    """ShipSimulation cost accounting should be non-trivially positive."""
    picard_history = _run_picard()
    fp = _fingerprint(picard_history, GOLDEN_LAST)
    assert fp["total_financial_usd"] is not None
    assert fp["total_financial_usd"] > 0


@pytest.mark.timeout(240)
def test_picard_vs_orchestrator_sir_parity() -> None:
    """Picard and orchestrator must agree on SIR summary and trigger status."""
    orch_history = _run_orchestrator()
    picard_history = _run_picard()

    assert len(orch_history) >= GOLDEN_LAST + 1
    assert len(picard_history) >= GOLDEN_LAST + 1

    fp_orch = _fingerprint(orch_history, GOLDEN_LAST)
    fp_picard = _fingerprint(picard_history, GOLDEN_LAST)

    assert fp_picard["susceptible"] == fp_orch["susceptible"]
    assert fp_picard["infected"] == fp_orch["infected"]
    assert fp_picard["symptomatic"] == fp_orch["symptomatic"]
    assert fp_picard["recovered"] == fp_orch["recovered"]
    assert fp_picard["immune"] == fp_orch["immune"]
    assert fp_picard["trigger_status"] == fp_orch["trigger_status"]
