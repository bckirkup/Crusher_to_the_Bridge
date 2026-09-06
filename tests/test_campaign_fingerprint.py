from __future__ import annotations
import importlib.util, json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("campaign_fingerprint",ROOT/"tools/campaign_fingerprint.py")
mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
def fixture(): return json.loads((ROOT/"docs/examples/publication_campaign_provenance.example.json").read_text())
def test_fingerprint_is_order_independent():
    x=fixture(); y=dict(reversed(list(x.items())))
    assert mod.canonical_fingerprint(x)==mod.canonical_fingerprint(y)
def test_scientific_input_mutation_changes_fingerprint():
    x=fixture(); y=fixture(); y["effective_config_sha256"]="f"*64
    assert mod.canonical_fingerprint(x)!=mod.canonical_fingerprint(y)
def test_outputs_do_not_change_pre_run_fingerprint():
    x=fixture(); y=fixture(); y["outputs"]=[{"path":"result.zip","sha256":"e"*64}]
    assert mod.canonical_fingerprint(x)==mod.canonical_fingerprint(y)
def test_example_validates():
    jsonschema=pytest.importorskip("jsonschema")
    schema=json.loads((ROOT/"schemas/publication_campaign_provenance.schema.json").read_text())
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(fixture())
