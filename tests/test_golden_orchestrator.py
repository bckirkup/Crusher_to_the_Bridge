"""
Golden regression: 24-epoch legacy run produces stable summary and cost totals.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(REPO_ROOT, "telemetry_buffer", "simulation_history.json")

EXPECTED_SUMMARY = {
    "susceptible": 6,
    "infected": 0,
    "symptomatic": 0,
    "recovered": 10,
    "immune": 4,
}
EXPECTED_TRIGGER = "BASELINE"
EXPECTED_COST_USD = 3085.0
GOLDEN_LAST_EPOCH = 23


def _run_orchestrator(epochs: int = 24) -> list[dict]:
    env = {**os.environ, "PYTHONPATH": REPO_ROOT}
    result = subprocess.run(
        [sys.executable, "orchestrator.py", "--epochs", str(epochs)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"orchestrator failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    with open(HISTORY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _fingerprint(history: list[dict]) -> dict:
    last = history[GOLDEN_LAST_EPOCH]
    summary = last.get("summary", {})
    cost = last.get("cost_accounting", {})
    return {
        "summary": {k: summary.get(k) for k in EXPECTED_SUMMARY},
        "trigger_status": last.get("trigger_status"),
        "total_financial_usd": cost.get("total_financial_usd"),
    }


@pytest.mark.timeout(120)
def test_golden_24_epoch_summary_and_costs() -> None:
    history = _run_orchestrator(24)
    assert len(history) >= GOLDEN_LAST_EPOCH + 1
    fp = _fingerprint(history)
    assert fp["summary"] == EXPECTED_SUMMARY
    assert fp["trigger_status"] == EXPECTED_TRIGGER
    assert fp["total_financial_usd"] == pytest.approx(EXPECTED_COST_USD, rel=0.01)


@pytest.mark.timeout(120)
def test_golden_reproducible_on_repeat() -> None:
    history_a = _run_orchestrator(24)
    history_b = _run_orchestrator(24)
    assert _fingerprint(history_a) == _fingerprint(history_b)
