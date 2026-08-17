"""Inviolate guard: agent/CLI path I/O must use simulation_utils.paths helpers.

Sonar ``pythonsecurity:S8707`` / ``S2083`` flag LLM-supplied CLI paths that
reach ``open`` / ``Path.read_text`` without containment checks. These tests
freeze that contract so a later agent cannot reintroduce raw filesystem
access in the hardened modules.
"""

from __future__ import annotations

import ast
import os

import pytest

from simulation_utils.paths import (
    confine_to_base,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Modules that accept CLI / agent path arguments and must not call bare open().
_HARDENED_MODULES = (
    "picard_framework/runs/mega_cruise_campaign/campaign_runner.py",
    "engines/contamx_runner.py",
    "deploy/aws/aggregate_results.py",
    "deploy/aws/analyze_campaign_curves.py",
    "deploy/aws/boundary_analysis_entrypoint.py",
    "deploy/aws/sentinel_recovery_analysis_entrypoint.py",
    "deploy/aws/classify_batch_failures.py",
    "deploy/aws/download_boundary_results.py",
    "deploy/aws/path_safety.py",
    "picard_framework/analysis/_io.py",
    "picard_framework/analysis/campaign_bundle.py",
    "picard_framework/analysis/report.py",
    "picard_framework/analysis/figures.py",
    "picard_framework/analysis/stan/fit_norovirus_trajectory.py",
    "picard_framework/analysis/stan/posterior_summaries.py",
    "picard_framework/analysis/boundary/run_decision_model.py",
    "picard_framework/analysis/boundary/figures.py",
    "picard_framework/analysis/boundary/report.py",
    "picard_framework/analysis/sentinel/export_line_list.py",
    "picard_framework/analysis/sentinel/itinerary.py",
    "picard_framework/analysis/sentinel/observations.py",
    "picard_framework/analysis/sentinel/artifacts.py",
    "picard_framework/analysis/sentinel/figures.py",
    "picard_framework/analysis/sentinel/report.py",
    "picard_framework/analysis/sentinel/run_sentinel.py",
    "picard_framework/analysis/sentinel_recovery_postprocess.py",
)

# Path.write_text / read_text / unlink / open are also sinks for S2083/S8707
# when the Path was built from user data — ban them in hardened modules.
_BAN_PATH_IO_METHODS = frozenset({"read_text", "write_text", "unlink", "open"})


def _module_source(rel: str) -> str:
    path = os.path.join(REPO_ROOT, rel)
    with open(path, encoding="utf-8") as fh:  # noqa: PTH123 - test fixture read
        return fh.read()


def _bare_open_calls(tree: ast.AST) -> list[int]:
    """Return line numbers of Call nodes that invoke the builtin open()."""
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            hits.append(getattr(node, "lineno", -1))
    return hits


def _path_io_method_calls(tree: ast.AST) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _BAN_PATH_IO_METHODS:
            hits.append((getattr(node, "lineno", -1), func.attr))
    return hits


@pytest.mark.parametrize("rel", _HARDENED_MODULES)
def test_hardened_modules_forbid_bare_open(rel: str) -> None:
    src = _module_source(rel)
    tree = ast.parse(src, filename=rel)
    hits = _bare_open_calls(tree)
    assert hits == [], (
        f"{rel} must not call bare open(); use validated_open "
        f"(found at lines {hits}). This keeps agent CLI path access inviolate."
    )


@pytest.mark.parametrize("rel", _HARDENED_MODULES)
def test_hardened_modules_forbid_path_text_io(rel: str) -> None:
    tree = ast.parse(_module_source(rel), filename=rel)
    hits = _path_io_method_calls(tree)
    assert hits == [], (
        f"{rel} must not use Path.read_text/write_text/unlink/open; "
        f"use validated_open after confinement (found {hits})."
    )


def test_campaign_runner_rejects_traversal_run_id() -> None:
    import picard_framework.runs.mega_cruise_campaign.campaign_runner as cr

    with pytest.raises(ValueError, match="Invalid run_id"):
        cr._safe_run_id("../etc")
    with pytest.raises(ValueError, match="Invalid run_id"):
        cr._safe_run_id("foo/bar")
    with pytest.raises(ValueError, match="Invalid run_id"):
        cr._safe_run_id("..")


def test_validated_open_rejects_outside_root(tmp_path) -> None:
    base = tmp_path / "allowed"
    outside = tmp_path / "secret.txt"
    base.mkdir()
    outside.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="outside allowed roots"):
        with validated_open(str(outside), allowed_roots=(str(base),), encoding="utf-8"):
            pass


def test_confine_and_resolve_block_agent_escape(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError):
        resolve_repo_path(str(repo), "../outside")
    with pytest.raises(ValueError):
        confine_to_base(str(repo), str(tmp_path / "outside"))
    assert validate_path_component("t1_norovirus_s42") == "t1_norovirus_s42"
