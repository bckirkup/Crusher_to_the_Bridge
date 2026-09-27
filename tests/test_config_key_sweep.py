"""Tests for tools/config_key_sweep.py.

Drives the sweep against a synthetic repo fixture (tmp_path) covering every
read kind and classification status, then checks the report contents and the
``main()`` write/stdout paths.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

from tools import config_key_sweep as cks


CONFIG_YAML = """\
engine:
  read_get: 1.0
  read_sub: 2
  read_contains: 3
  dead_leaf: 0
deep_sec:
  deep:
    dead_grandchild: 0
bulk_sec:
  a: 1
  b: 2
splat_sec:
  sp_a: 1
  sp_b: 2
model_sec:
  m_a: 1
  m_b: 2
  unmodeled: 0
downstream_sec:
  leaf: 1
  dead_leaf: 0
weak_sec:
  name_match_key: 9
  lit_only: x
orphan_sec:
  orphan: 0
"""

# direct scope: root-level orchestrator_*.py
ORCHESTRATOR_SRC = '''\
from crusher_labs import load_config

cfg = load_config()


def use_splat(sp_a=None):
    return sp_a


def run():
    v = cfg.get("engine").get("read_get")
    w = cfg["engine"]["read_sub"]
    if "read_contains" in cfg.get("engine"):
        pass
    eng = cfg.get("engine")
    again = eng.get("read_get")
    popped = cfg.get("deep_sec", {})
    for k, v2 in cfg["bulk_sec"].items():
        pass
    for k3 in cfg.get("bulk_sec"):
        pass
    sec = cfg.get("splat_sec")
    use_splat(**sec)
    kw_sink(named=v)
    return v + w + again + popped
'''

# direct scope: crusher_labs/
CRUSHER_SRC = '''\
from crusher_labs import load_config


def check(turnaround_cfg):
    # name matches a config leaf but the base object is not resolvable —
    # this is exactly what the indirect-name-match tier exists for.
    return turnaround_cfg.get("name_match_key")


def check2(run_spec):
    lc = run_spec.legacy_cfg
    table = {"leaf": "lit_only"}
    return lc.get("dead_sec", {}), table
'''

# direct scope: tools/sanity_checker.py (model_validate covers fields + bulk)
SANITY_SRC = '''\
from crusher_labs import load_config

cfg = load_config()


class ModelSpec:
    m_a: float
    m_b: float


spec = ModelSpec.model_validate(cfg.get("model_sec"))
ctor = ModelSpec(cfg["model_sec"])
'''

# downstream scope: engines/
ENGINES_SRC = '''\
def consume(cfg):
    return cfg.get("downstream_sec")["leaf"]
'''

BROKEN_SRC = "def broken(:\n"


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "crusher_labs").mkdir()
    (tmp_path / "engines").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "crusher_labs" / "config.yaml").write_text(CONFIG_YAML)
    (tmp_path / "orchestrator_fake.py").write_text(ORCHESTRATOR_SRC)
    (tmp_path / "crusher_labs" / "mod.py").write_text(CRUSHER_SRC)
    (tmp_path / "tools" / "sanity_checker.py").write_text(SANITY_SRC)
    (tmp_path / "engines" / "down.py").write_text(ENGINES_SRC)
    (tmp_path / "broken.py").write_text(BROKEN_SRC)
    # skipped dirs must not be walked
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.py").write_text('cfg.get("zzz")')
    monkeypatch.setattr(cks, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cks, "CONFIG_PATH",
                        tmp_path / "crusher_labs" / "config.yaml")
    monkeypatch.setattr(cks, "REPORTS_DIR", tmp_path / "reports")
    return tmp_path


def _run_sweep() -> list[dict]:
    leaves = cks._config_leaf_paths()
    scans = [s for p in cks._iter_python_files()
             if (s := cks._scan_file(p)) is not None]
    rows = cks.classify(leaves, scans, cks._build_name_index(scans),
                        cks._build_literal_index(scans))
    return rows


def _status(rows: list[dict], key: str) -> str:
    return next(r["status"] for r in rows if r["key"] == key)


def test_classification(fake_repo: Path) -> None:
    rows = _run_sweep()
    # exact direct reads
    assert _status(rows, "engine.read_get") == "consumed-direct"
    assert _status(rows, "engine.read_sub") == "consumed-direct"
    assert _status(rows, "engine.read_contains") == "consumed-direct"
    # model fields resolved through model_validate
    assert _status(rows, "model_sec.m_a") == "consumed-direct"
    assert _status(rows, "model_sec.unmodeled") == "consumed-bulk"
    # .items() and bare iteration cover every leaf
    assert _status(rows, "bulk_sec.a") == "consumed-bulk"
    assert _status(rows, "bulk_sec.b") == "consumed-bulk"
    # splat resolves callee params; leftover leaf falls to bulk
    assert _status(rows, "splat_sec.sp_a") == "consumed-direct"
    assert _status(rows, "splat_sec.sp_b") == "consumed-bulk"
    # downstream-only read
    assert _status(rows, "downstream_sec.leaf") == "consumed-downstream"
    # weak tiers
    assert _status(rows, "weak_sec.name_match_key") == "indirect-name-match"
    assert _status(rows, "weak_sec.lit_only") == "indirect-literal"
    # dead keys: section-read vs never-touched
    assert _status(rows, "engine.dead_leaf") == "UNREFERENCED"
    assert _status(rows, "deep_sec.deep.dead_grandchild") == "UNREFERENCED"
    assert _status(rows, "downstream_sec.dead_leaf") == "UNREFERENCED"
    assert _status(rows, "orphan_sec.orphan") == "UNREFERENCED"
    assert _status(rows, "deep_sec.deep.dead_grandchild")


def test_report_contains_all_sections(fake_repo: Path) -> None:
    rows = _run_sweep()
    md = cks.render_markdown(rows, reads_in_scope=42)
    assert "config leaves examined: **17**" in md
    assert "## Unreferenced keys" in md
    assert "## Weak-evidence keys" in md
    assert "## Literal-only keys" in md
    assert "## Keys read only outside" in md
    assert "engine.dead_leaf" in md


def test_main_writes_reports(fake_repo: Path,
                             monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["config_key_sweep.py"])
    assert cks.main() == 0
    md = (fake_repo / "reports" / "config_key_sweep.md").read_text()
    data = json.loads(
        (fake_repo / "reports" / "config_key_sweep.json").read_text())
    assert "UNREFERENCED" in md
    assert data["config"].endswith("config.yaml")
    assert len(data["keys"]) == 17


def test_main_stdout(fake_repo: Path, monkeypatch: pytest.MonkeyPatch,
                     capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(sys, "argv", ["config_key_sweep.py", "--stdout"])
    assert cks.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("# config.yaml key sweep")
    assert not (fake_repo / "reports").exists()


def test_self_referential_alias_converges(fake_repo: Path) -> None:
    """x = x.get("k") must not grow its own path each fixpoint pass.

    The target's binding is popped while its own RHS resolves, so the
    re-assignment cannot extend x's path; the read itself is still
    recorded on the alias-preloaded pass.
    """
    f = fake_repo / "orchestrator_selfref.py"
    f.write_text(
        "cfg = load_config()\n"
        "x = cfg.get('engine')\n"
        "x = x.get('read_get')\n"
        "y = x\n"
    )
    scan = cks._scan_file(f)
    assert scan is not None
    assert scan.aliases["x"] == "engine"
    assert scan.aliases["y"] == "engine"
    assert any(r.path == "engine.read_get" for r in scan.reads)


def test_scope_of() -> None:
    assert cks._scope_of("orchestrator_epoch.py") == "direct"
    assert cks._scope_of("crusher_labs/x.py") == "direct"
    assert cks._scope_of("tools/sanity_checker.py") == "direct"
    assert cks._scope_of("engines/x.py") == "downstream"
    assert cks._scope_of("pkg/orchestrator_thing.py") == "downstream"


def test_const_str() -> None:
    node = ast.parse("x['k']").body[0].value  # type: ignore[attr-defined]
    assert cks._const_str(node.slice) == "k"
    assert cks._const_str(ast.parse("x[0]").body[0].value.slice) is None  # type: ignore[attr-defined]
    assert cks._const_str(None) is None
