from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "campaign_fingerprint",
    ROOT / "tools/campaign_fingerprint.py",
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def fixture() -> dict:
    path = ROOT / "docs/examples/publication_campaign_provenance.example.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "schemas/publication_campaign_provenance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )


def test_fingerprint_is_order_independent() -> None:
    left = fixture()
    right = dict(reversed(list(left.items())))
    assert mod.canonical_fingerprint(left) == mod.canonical_fingerprint(right)


def test_scientific_input_mutation_changes_fingerprint() -> None:
    left = fixture()
    right = fixture()
    right["effective_config_sha256"] = "f" * 64
    assert mod.canonical_fingerprint(left) != mod.canonical_fingerprint(right)


def test_outputs_do_not_change_pre_run_fingerprint() -> None:
    left = fixture()
    right = fixture()
    right["outputs"] = [{"path": "result.zip", "sha256": "e" * 64}]
    assert mod.canonical_fingerprint(left) == mod.canonical_fingerprint(right)


def test_example_validates() -> None:
    validator().validate(fixture())


@pytest.mark.parametrize("intent", ["confirmatory", "revision"])
def test_planned_intents_require_plan_and_parent(intent: str) -> None:
    payload = fixture()
    payload["run_intent"] = intent
    assert list(validator().iter_errors(payload))
    payload["analysis_plan_id"] = "plan-v1"
    payload["lineage"]["parent_campaign_uid"] = "92b44427-ad2d-4c3b-93c7-67f856487324"
    validator().validate(payload)


def test_review_response_requires_plan_review_and_parent() -> None:
    payload = fixture()
    payload["run_intent"] = "review_response"
    assert list(validator().iter_errors(payload))
    payload["analysis_plan_id"] = "plan-v1"
    payload["review_response_id"] = "review-2-comment-7"
    payload["lineage"]["parent_campaign_uid"] = "92b44427-ad2d-4c3b-93c7-67f856487324"
    validator().validate(payload)


def test_validate_uses_repository_schema() -> None:
    pytest.importorskip("jsonschema")
    mod.validate(fixture())


def test_validate_requires_jsonschema(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def _block_jsonschema(name: str, *args: object, **kwargs: object):
        if name == "jsonschema":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _block_jsonschema)
    with pytest.raises(SystemExit, match="jsonschema"):
        mod.validate(fixture())


def test_cli_validate_and_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = fixture()
    payload["run_fingerprint"] = mod.canonical_fingerprint(payload)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert mod.main([str(path), "--validate", "--verify"]) == 0
    assert mod.canonical_fingerprint(payload) in capsys.readouterr().out


def test_cli_rejects_mismatched_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = fixture()
    payload["run_fingerprint"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert mod.main([str(path), "--verify"]) == 2


def test_cli_rejects_path_outside_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(fixture()), encoding="utf-8")
    inside = tmp_path / "inside"
    inside.mkdir()
    monkeypatch.chdir(inside)
    with pytest.raises(SystemExit, match="must remain under"):
        mod.main([str(outside)])
