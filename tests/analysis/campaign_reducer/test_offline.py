"""tests/analysis/campaign_reducer/test_offline.py — offline + namespace gates.

D0 acceptance: ``plan``/``validate`` invoke zero network calls, jobs or
simulation functions under subprocess/network spies; the other nine
registered operations exit nonzero with NOT_YET_IMPLEMENTED; the launcher
wires ``analysis`` without touching the campaign simulation path.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from picard_framework.analysis.campaign_reducer import cli, contracts

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = contracts.CONTRACTS_DIR
BLOCKED_REQUEST = CONTRACTS / "BLOCKED_REQUEST.template.json"

_UNIMPLEMENTED_OPS = (
    "preflight", "inventory", "quote", "submit", "status",
    "resume", "query", "collect", "acknowledge",
)

_EXTRA_ARGV = {
    "quote": ["--evidence", "evidence.json"],
    "submit": ["--phase", "pilot"],
    "status": ["--attempt-id", "attempt-1"],
    "resume": ["--checkpoint", "s3://bucket/checkpoint.json"],
    "query": ["--query", "query.json"],
    "collect": ["--receipt", "s3://bucket/receipt.json"],
    "acknowledge": ["--ack", "ack.json"],
}


def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rig every network/AWS entrypoint to raise."""
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("network/subprocess/AWS call attempted")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    # Any boto3 import becomes an ImportError.
    monkeypatch.setitem(sys.modules, "boto3", None)
    monkeypatch.setitem(sys.modules, "botocore", None)


def _load_launcher() -> object:
    """Import the extensionless scripts/campaign file as a module."""
    loader = importlib.machinery.SourceFileLoader(
        "campaign_launcher", str(REPO_ROOT / "scripts" / "campaign"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_plan_and_validate_run_with_no_network_or_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_external(monkeypatch)
    assert cli.main([
        "plan", "--request", str(BLOCKED_REQUEST), "--out", str(tmp_path / "plan"),
    ]) == 0
    assert cli.main([
        "validate", "--request", str(BLOCKED_REQUEST),
        "--request-kind", "execution", "--out", str(tmp_path / "validate"),
    ]) == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED


def test_launcher_analysis_path_never_invokes_simulation_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_external(monkeypatch)
    launcher = _load_launcher()
    exit_code = launcher.main([
        "analysis", "plan", "--request", str(BLOCKED_REQUEST),
        "--out", str(tmp_path / "plan"),
    ])
    assert exit_code == 0
    assert (tmp_path / "plan" / "scope.json").is_file()


@pytest.mark.parametrize("operation", _UNIMPLEMENTED_OPS)
def test_unimplemented_operations_exit_nonzero(
    tmp_path: Path, operation: str,
) -> None:
    out = tmp_path / operation
    exit_code = cli.main([
        operation, "--request", str(BLOCKED_REQUEST),
        "--out", str(out), *_EXTRA_ARGV.get(operation, []),
    ])
    assert exit_code != 0
    status = json.loads((out / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "NOT_YET_IMPLEMENTED"
    assert status["operation"] == operation


def test_all_eleven_operations_registered() -> None:
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    operations = canonical["public_cli"]["operations"]
    assert set(operations) == {
        "plan", "validate", "preflight", "inventory", "quote", "submit",
        "status", "resume", "query", "collect", "acknowledge",
    }
