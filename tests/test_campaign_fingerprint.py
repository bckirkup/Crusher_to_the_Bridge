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


def _write_manifest(directory: Path, payload: dict | None = None) -> Path:
    """Write a provenance envelope under *directory* for CLI tests."""
    path = directory / "manifest.json"
    path.write_text(json.dumps(payload or fixture()), encoding="utf-8")
    return path


def test_validate_accepts_the_example_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``validate`` loads the schema through the confined reader."""
    pytest.importorskip("jsonschema")
    monkeypatch.chdir(ROOT)
    schema = Path("schemas/publication_campaign_provenance.schema.json")
    mod.validate(fixture(), schema)


def test_validate_requires_jsonschema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing jsonschema fails closed with a clear SystemExit."""
    monkeypatch.chdir(ROOT)
    real_import = __import__

    def _block_jsonschema(name: str, *args: object, **kwargs: object):
        if name == "jsonschema":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _block_jsonschema)
    with pytest.raises(SystemExit, match="jsonschema"):
        mod.validate(fixture(), Path("schemas/publication_campaign_provenance.schema.json"))


def test_main_prints_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI happy path prints the canonical fingerprint and exits 0."""
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["campaign_fingerprint", str(manifest.name)],
    )
    assert mod.main() == 0
    assert capsys.readouterr().out.strip() == mod.canonical_fingerprint(fixture())


def test_main_verify_rejects_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--verify`` fails closed when the stored fingerprint disagrees."""
    monkeypatch.chdir(tmp_path)
    payload = fixture()
    payload["run_fingerprint"] = "0" * 64
    manifest = _write_manifest(tmp_path, payload)
    monkeypatch.setattr(
        "sys.argv",
        ["campaign_fingerprint", str(manifest.name), "--verify"],
    )
    assert mod.main() == 2
    assert "fingerprint mismatch" in capsys.readouterr().out


def test_main_validate_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--validate`` runs schema validation before fingerprinting."""
    pytest.importorskip("jsonschema")
    # Schema lives in the repo; confine reads under cwd, so run from ROOT and
    # place the manifest beside a copy-free relative path.
    monkeypatch.chdir(ROOT)
    manifest = Path("docs/examples/publication_campaign_provenance.example.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "campaign_fingerprint",
            str(manifest),
            "--validate",
            "--schema",
            "schemas/publication_campaign_provenance.schema.json",
        ],
    )
    assert mod.main() == 0
    assert capsys.readouterr().out.strip() == mod.canonical_fingerprint(fixture())
