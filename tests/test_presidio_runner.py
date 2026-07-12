"""Presidio fleet runner smoke test (short cruises)."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.timeout(180)
def test_presidio_runner_two_cruises_two_epochs() -> None:
    env = {**os.environ, "PYTHONPATH": REPO_ROOT, "PYTHONUTF8": "1"}
    fleet_config = os.path.join(
        REPO_ROOT, "presidio", "data", "config", "smoke_fleet.json",
    )
    result = subprocess.run(
        [
            sys.executable,
            "presidio_runner.py",
            "--fleet-config",
            fleet_config,
            "--cruises",
            "1",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary_path = os.path.join(
        REPO_ROOT,
        "presidio",
        "data",
        "experiences",
        "smoke_runs",
        "fleet_summary.json",
    )
    assert os.path.isfile(summary_path)
    with open(summary_path, encoding="utf-8") as fh:
        summary = json.load(fh)
    assert summary.get("num_cruises") == 1
