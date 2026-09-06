from __future__ import annotations
import importlib.util, json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("campaign_fingerprint",ROOT/"tools/campaign_fingerprint.py")
mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
def fixture(): return json.loads((ROOT/"docs/examples/publication_campaign_provenance.example.json").read_text())
def validator():
    jsonschema=pytest.importorskip("jsonschema")
    schema=json.loads((ROOT/"schemas/publication_campaign_provenance.schema.json").read_text())
    return jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
def test_fingerprint_is_order_independent():
    x=fixture(); y=dict(reversed(list(x.items())))
    assert mod.canonical_fingerprint(x)==mod.canonical_fingerprint(y)
def test_scientific_input_mutation_changes_fingerprint():
    x=fixture(); y=fixture(); y["effective_config_sha256"]="f"*64
    assert mod.canonical_fingerprint(x)!=mod.canonical_fingerprint(y)
def test_outputs_do_not_change_pre_run_fingerprint():
    x=fixture(); y=fixture(); y["outputs"]=[{"path":"result.zip","sha256":"e"*64}]
    assert mod.canonical_fingerprint(x)==mod.canonical_fingerprint(y)
def test_example_validates(): validator().validate(fixture())
@pytest.mark.parametrize("intent",["confirmatory","revision"])
def test_planned_intents_require_plan_and_parent(intent):
    x=fixture(); x["run_intent"]=intent
    errors=list(validator().iter_errors(x))
    assert errors
    x["analysis_plan_id"]="plan-v1"; x["lineage"]["parent_campaign_uid"]="92b44427-ad2d-4c3b-93c7-67f856487324"
    validator().validate(x)
def test_review_response_requires_plan_review_and_parent():
    x=fixture(); x["run_intent"]="review_response"
    assert list(validator().iter_errors(x))
    x["analysis_plan_id"]="plan-v1"; x["review_response_id"]="review-2-comment-7"; x["lineage"]["parent_campaign_uid"]="92b44427-ad2d-4c3b-93c7-67f856487324"
    validator().validate(x)
def test_validate_uses_repository_schema(): mod.validate(fixture())
def test_cli_validate_and_verify(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path); x=fixture(); x["run_fingerprint"]=mod.canonical_fingerprint(x)
    p=tmp_path/"manifest.json"; p.write_text(json.dumps(x))
    assert mod.main([str(p),"--validate","--verify"])==0
    assert mod.canonical_fingerprint(x) in capsys.readouterr().out
def test_cli_rejects_mismatched_fingerprint(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path); x=fixture(); x["run_fingerprint"]="0"*64
    p=tmp_path/"manifest.json"; p.write_text(json.dumps(x))
    assert mod.main([str(p),"--verify"])==2
def test_cli_rejects_path_outside_working_directory(tmp_path,monkeypatch):
    outside=tmp_path/"outside.json"; outside.write_text(json.dumps(fixture()))
    inside=tmp_path/"inside"; inside.mkdir(); monkeypatch.chdir(inside)
    with pytest.raises(SystemExit,match="must remain under"): mod.main([str(outside)])
