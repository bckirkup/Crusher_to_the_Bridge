"""
Invariants of a 24-epoch legacy run: compartments partition the complement,
the run is reproducible, and costs accrue.

Deliberately holds no expected counts.  The point values this file used to
assert (susceptible/infected/symptomatic/recovered/immune at epoch 23) moved on
every legitimate model change -- the hours clock, onset off the day lattice, the
capacity-weighted leisure draw, activating a third pathogen -- and each move
required editing the expectation, so the assertion detected the edit rather than
the defect.  What survives is what a wrong pipeline cannot satisfy: agents are
conserved across compartments, two runs of the same seed agree field for field,
and the cost ledger is populated.  Per-mechanism expectations belong in the test
for that mechanism (e.g. the legacy epoch-as-day reading in
tests/test_sim_clock.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(REPO_ROOT, "telemetry_buffer", "simulation_history.json")

COMPARTMENTS = ("susceptible", "infected", "recovered", "immune")
LAST_EPOCH = 23
VALID_TRIGGERS = {"BASELINE", "ALERT", "SUSPECTED", "CONFIRMED", "LOCKDOWN"}


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


def _fingerprint(history: list[dict]) -> dict:
    """Every summary field plus trigger and cost, for the repeat comparison."""
    last = history[LAST_EPOCH]
    return {
        "summary": dict(last.get("summary", {})),
        "trigger_status": last.get("trigger_status"),
        "total_financial_usd": last.get("cost_accounting", {}).get(
            "total_financial_usd",
        ),
    }


@pytest.mark.timeout(120)
def test_compartments_partition_the_complement_every_epoch() -> None:
    history = _run_orchestrator(24)
    assert len(history) >= LAST_EPOCH + 1
    for epoch, rec in enumerate(history):
        summary = rec["summary"]
        complement = summary["passenger_complement"] + summary["crew_complement"]
        counts = [summary[key] for key in COMPARTMENTS]
        assert all(count >= 0 for count in counts), f"epoch {epoch}: {summary}"
        assert sum(counts) == complement, f"epoch {epoch}: {summary}"
        assert 0 <= summary["symptomatic"] <= summary["infected"]
        assert summary["cumulative_ever_infected"] >= summary["infected"]
        assert 0.0 <= summary["infection_attack_rate_passenger"] <= 1.0
        assert 0.0 <= summary["infection_attack_rate_crew"] <= 1.0


@pytest.mark.timeout(120)
def test_costs_accrue_and_the_trigger_is_a_known_state() -> None:
    fp = _fingerprint(_run_orchestrator(24))
    assert fp["trigger_status"] in VALID_TRIGGERS
    assert fp["total_financial_usd"] is not None
    assert fp["total_financial_usd"] > 0


@pytest.mark.timeout(120)
def test_reproducible_on_repeat() -> None:
    fp_a = _fingerprint(_run_orchestrator(24))
    fp_b = _fingerprint(_run_orchestrator(24))
    assert fp_a["summary"] == fp_b["summary"]
    assert fp_a["trigger_status"] == fp_b["trigger_status"]
    assert fp_a["total_financial_usd"] == pytest.approx(
        fp_b["total_financial_usd"],
    )
