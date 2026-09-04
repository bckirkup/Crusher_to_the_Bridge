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

# Updated 2026-08-16: default platform mega_cruise_5000 (was destroyer_baseline).
# Updated 2026-08-23 (hours clock): an epoch is one physical hour, so this 24-epoch
# run covers one calendar day.  The three seeded norovirus cases pass day-1 onset
# but cannot reach ``recovery_day: 3`` (72 epochs), where the previous
# epoch-as-day reading cleared them inside 3 epochs.  Prior expectation was
# infected 0 / symptomatic 0 / recovered 3; the legacy reading is still asserted
# directly in tests/test_sim_clock.py.
# Updated 2026-08-23 (onset off the day lattice): the illness hazard now opens at
# each host's own drawn incubation period rather than at the next whole day, so a
# case whose draw exceeds 1 day has not presented by epoch 23.  Prior expectation
# under the hours clock was symptomatic 2.
# Updated 2026-09-03 (capacity-weighted leisure draw): the weighted
# ``rng.choice`` consumes the seeded stream differently, moving symptomatic
# from 2 to 1 and the final trigger from CONFIRMED to BASELINE.
EXPECTED_SUMMARY = {
    "susceptible": 13,
    "infected": 3,
    "symptomatic": 1,
    "recovered": 0,
    "immune": 4,
}
# The weighted leisure draw changes the seeded stream, so no true-positive call
# occurs within the first day.
EXPECTED_TRIGGER = "BASELINE"


def _run_orchestrator(epochs: int = 24) -> list[dict]:
    env = {**os.environ, "PYTHONPATH": REPO_ROOT, "PYTHONUTF8": "1"}
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


GOLDEN_LAST_EPOCH = 23


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
    # Own-severity reporting can produce a true-positive sick call inside 24 h.
    assert fp["trigger_status"] == EXPECTED_TRIGGER
    assert fp["total_financial_usd"] is not None
    assert fp["total_financial_usd"] > 0


@pytest.mark.timeout(120)
def test_golden_reproducible_on_repeat() -> None:
    history_a = _run_orchestrator(24)
    history_b = _run_orchestrator(24)
    assert _fingerprint(history_a) == _fingerprint(history_b)
    assert _fingerprint(history_a)["total_financial_usd"] == pytest.approx(
        _fingerprint(history_b)["total_financial_usd"],
    )
