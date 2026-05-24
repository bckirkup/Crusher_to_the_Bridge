"""
test_sanity_checker.py – Verify the sanity checker passes on current configs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Imports and runs the sanity checker programmatically to ensure all
configuration files are internally consistent.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.sanity_checker import run_checks


def test_default_configs_pass_sanity_checks() -> None:
    """The shipped configuration files must pass all sanity checks."""
    config_dir = os.path.join(REPO_ROOT, "data", "config")
    platform_dir = os.path.join(REPO_ROOT, "data", "platforms", "destroyer_baseline")
    pathogen_dir = os.path.join(REPO_ROOT, "data", "pathogens")

    report = run_checks(config_dir, platform_dir, pathogen_dir)

    error_msgs = [
        f"[{f.rule}] {f.file}: {f.message}" for f in report.errors
    ]
    assert report.passed, (
        f"Sanity checker found {len(report.errors)} error(s):\n"
        + "\n".join(error_msgs)
    )
