"""Exception classification in the Paper-1 frozen-block checker.

No simulation is built: initialization is replaced, so these run in
milliseconds and assert only how a flip's outcome is classified.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "paper1_freeze_block_check.py"
_SPEC = importlib.util.spec_from_file_location("paper1_freeze_block_check", _SCRIPT)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)

_REJECTED = "transmission.contact_mode"
_PLAIN = "transmission.cabin_air_mode"


def _leaf(path: str) -> object:
    return checker.Leaf(path, path, "pinned", "alt", checker.TX, "tx.x", ())


def _classify(monkeypatch: pytest.MonkeyPatch, path: str, error: Exception | None) -> str:
    def fake_init(_spec: object) -> object:
        if error is not None:
            raise error
        return object()

    monkeypatch.setattr(checker, "build_raw", lambda *_a, **_k: {})
    monkeypatch.setattr(checker, "parse_spec", lambda raw: raw)
    monkeypatch.setattr(checker, "init_sim", fake_init)
    monkeypatch.setattr(checker, "probe", lambda *_a, **_k: "moved")
    block = {"transmission": {path.split(".")[-1]: "pinned"}}
    return checker.flip_moves_state(block, _leaf(path), "alt", "pinned", {})


@pytest.mark.parametrize("error", [
    FileNotFoundError("no such file"),
    KeyError("spatial_layout"),
    ValueError("some other validation"),
])
def test_unexpected_initialization_error_is_not_a_live_pin(monkeypatch, error):
    for path in (_PLAIN, _REJECTED):
        verdict = _classify(monkeypatch, path, error)
        assert verdict.startswith("UNEXPECTED")
        assert "live" not in verdict


def test_declared_rejection_is_recorded_with_its_reason(monkeypatch):
    name, fragment = checker.EXPECTED_REJECTIONS[_REJECTED]
    verdict = _classify(monkeypatch, _REJECTED, ValueError(f"x {fragment} y"))
    assert verdict.startswith("expected rejection")
    assert name in verdict and fragment in verdict


def test_declared_rejection_that_does_not_occur_fails(monkeypatch):
    assert _classify(monkeypatch, _REJECTED, None).startswith("UNEXPECTED")


def test_flip_that_moves_or_leaves_state(monkeypatch):
    assert _classify(monkeypatch, _PLAIN, None) == "live"
    monkeypatch.setattr(checker, "probe", lambda *_a, **_k: "pinned")
    block = {"transmission": {"cabin_air_mode": "pinned"}}
    assert checker.flip_moves_state(
        block, _leaf(_PLAIN), "alt", "pinned", {},
    ) == "DEAD"
