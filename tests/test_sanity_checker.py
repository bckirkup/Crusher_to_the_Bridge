"""test_sanity_checker.py – sanity checker vs orchestrator config paths."""
from __future__ import annotations
import os, sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from tools.sanity_checker import Report, paths_from_run_config, run_checks

def _assert_passed(report: Report) -> None:
    msgs = [f"[{f.rule}] {f.file}: {f.message}" for f in report.errors]
    assert report.passed, f"{len(report.errors)} error(s):\n" + "\n".join(msgs)

def test_default_destroyer_and_active_profiles() -> None:
    report = run_checks(
        os.path.join(REPO_ROOT, "data", "config"),
        os.path.join(REPO_ROOT, "data", "platforms", "destroyer_baseline"),
        pathogen_file=os.path.join(REPO_ROOT, "data", "pathogens", "active_profiles.json"),
    )
    _assert_passed(report)

def test_from_config_yaml_matches_orchestrator() -> None:
    paths = paths_from_run_config(REPO_ROOT)
    report = run_checks(
        paths["config_dir"], paths["platform_dir"], pathogen_file=paths["pathogen_file"],
    )
    _assert_passed(report)
