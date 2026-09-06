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
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "schemas/publication_campaign_provenance.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(fixture())


def test_safe_read_rejects_path_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI path arguments must stay under the process working directory."""
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    inside = tmp_path / "workspace"
    inside.mkdir()
    monkeypatch.chdir(inside)
    with pytest.raises(ValueError, match="escapes"):
        mod._safe_read_text(outside)


def test_safe_read_allows_paths_under_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relative paths under the working directory remain readable."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "manifest.json"
    target.write_text('{"ok": true}', encoding="utf-8")
    assert json.loads(mod._safe_read_text(Path("manifest.json"))) == {"ok": True}
