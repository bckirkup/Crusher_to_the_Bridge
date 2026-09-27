#!/usr/bin/env python3
"""Static sweep of ``crusher_labs/config.yaml`` keys against their consumers.

Report-only tool: enumerates every key the shipped config.yaml declares,
extracts every key-path read by the Python consumers, and flags keys that
no consumer parses. Nothing is removed or edited — review the report before
deleting keys.

Consumers scanned for *direct* evidence:

* ``orchestrator*.py`` (repo root)
* ``crusher_labs/**/*.py``
* ``tools/sanity_checker.py``

All other Python files are scanned too, but reads there are classed as
``downstream`` evidence (engines/, picard_framework/, telemetry_buffer/,
scripts/, tests/, tools/ other than sanity_checker, etc.) since config
sections are forwarded into them via ``run_spec.legacy_cfg`` and explicit
arguments.

Extraction model (AST, no regex guessing):

* ``cfg`` / ``config`` / ``legacy_cfg`` names, ``*.legacy_cfg`` attribute
  roots, and anything assigned ``load_config(...)`` are root aliases.
* ``x = <alias>.get("k")`` / ``x = <alias>["k"]`` / ``x = dict(<alias>.get("k")
  or {})`` bind ``x`` to ``<alias>.k``; propagation iterates to a fixpoint.
* ``<alias>.get("k")``, ``<alias>["k"]``, ``<alias>.pop/setdefault("k")``,
  ``"k" in <alias>``, ``for ... in <alias>``, ``<alias>.items()/keys()``,
  and ``**<alias>`` record reads; ``.items()``/iteration marks every child
  of the path as consumed.
* ``Model.model_validate(<alias>)`` / ``Model(**<alias>)`` mark the model's
  declared field names as consumed under that path (pydantic/dataclass).

A key with no direct read but whose final segment appears as a dict access
or model field somewhere in the repo is reported ``indirect`` (weak — a
human must confirm). A key with no evidence anywhere is ``unreferenced``.

Usage::

    python3 tools/config_key_sweep.py            # writes reports/
    python3 tools/config_key_sweep.py --stdout   # print markdown only
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "crusher_labs" / "config.yaml"
REPORTS_DIR = REPO_ROOT / "reports"

# Root variables/attributes treated as "the config dict" when they appear on
# the receiving end of .get()/[...] access.
ROOT_NAMES = {"cfg", "config", "legacy_cfg", "raw_cfg", "yaml_cfg"}
ROOT_ATTRS = {"legacy_cfg"}  # e.g. run_spec.legacy_cfg, self.run_spec.legacy_cfg
LOADER_NAMES = {"load_config"}

DIRECT_SCOPES = (
    "orchestrator",      # root-level orchestrator*.py
    "crusher_labs/",
    "tools/sanity_checker.py",
)

_AccessKind = str  # "get" | "subscript" | "pop" | "setdefault" | "contains" | "iterate" | "splat" | "model"


@dataclass
class Read:
    path: str           # dotted config path that was read ("" = whole config)
    file: str           # repo-relative
    line: int
    kind: _AccessKind
    scope: str          # "direct" | "downstream"


def _scope_of(rel: str) -> str:
    base = os.path.basename(rel)
    if base.startswith("orchestrator") and base.endswith(".py") and "/" not in rel:
        return "direct"
    if rel.startswith("crusher_labs/") or rel == "tools/sanity_checker.py":
        return "direct"
    return "downstream"


def _iter_python_files() -> Iterable[Path]:
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__",
                 ".mypy_cache", ".pytest_cache", "third_party"}
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if fn.endswith(".py"):
                yield Path(dirpath) / fn


def _config_leaf_paths() -> dict[str, Any]:
    """Return {dotted_leaf_path: yaml_value} for every leaf in config.yaml."""
    import yaml

    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    leaves: dict[str, Any] = {}

    def walk(node: Any, pfx: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{pfx}.{k}" if pfx else str(k))
        else:
            leaves[pfx] = node

    walk(cfg, "")
    return leaves


class _ModelInfo:
    """Field names of a pydantic model or dataclass defined in a file."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.fields: set[str] = set()


class _FileScan(ast.NodeVisitor):
    """One pass over a module: aliases, reads, model fields, local callables."""

    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.scope = _scope_of(rel)
        self.aliases: dict[str, str] = {}          # var -> config path (""=root)
        self.reads: list[Read] = []
        self.models: dict[str, _ModelInfo] = {}
        # name -> param names for locally defined functions/classes/ctors
        self.callable_params: dict[str, set[str]] = {}
        self._pending_assigns: list[tuple[str, ast.expr]] = []
        # every string literal in the file (dynamic-key lookup tables like
        # {"alert": "alert_delay_hours"} feed .get() via a variable)
        self.literals: set[str] = set()
        # string keys used in .get()/[]/.pop()/setdefault()/kwarg/`in` on ANY
        # object — including bases we cannot resolve (a config section passed
        # through a function parameter reads as a bare name here)
        self.key_uses: set[str] = set()

    # ── expression → config-path resolution ──────────────────────────
    def _resolve(self, node: ast.expr | None) -> str | None:
        """Map an expression to a dotted config path, or None."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return self._resolve_name(node)
        if isinstance(node, ast.Attribute):
            return self._resolve_attribute(node)
        if isinstance(node, ast.Subscript):
            return self._resolve_subscript(node)
        if isinstance(node, ast.Call):
            return self._resolve_call(node)
        if isinstance(node, ast.BoolOp):
            return self._resolve_boolop(node)
        if isinstance(node, ast.IfExp):
            return self._resolve(node.body) or self._resolve(node.orelse)
        return None

    def _resolve_name(self, node: ast.Name) -> str | None:
        if node.id in self.aliases:
            return self.aliases[node.id]
        if node.id in ROOT_NAMES:
            return ""
        return None

    def _resolve_attribute(self, node: ast.Attribute) -> str | None:
        if node.attr in ROOT_ATTRS:
            return ""
        inner = self._resolve(node.value)
        return f"{inner}.{node.attr}" if inner is not None else None

    def _resolve_subscript(self, node: ast.Subscript) -> str | None:
        key = _const_str(node.slice)
        inner = self._resolve(node.value)
        if inner is not None and key is not None:
            return f"{inner}.{key}" if inner else key
        return inner

    def _resolve_call(self, node: ast.Call) -> str | None:
        func = node.func
        if isinstance(func, ast.Name):
            return self._resolve_named_call(func, node)
        if isinstance(func, ast.Attribute):
            return self._resolve_method_call(func, node)
        return None

    def _resolve_named_call(self, func: ast.Name, node: ast.Call) -> str | None:
        if func.id in LOADER_NAMES:
            return ""
        if func.id in {"dict", "Dict"} and node.args:
            return self._resolve(node.args[0])
        return None

    def _resolve_method_call(self, func: ast.Attribute,
                             node: ast.Call) -> str | None:
        inner = self._resolve(func.value)
        if inner is None:
            return None
        if func.attr in {"get", "pop", "setdefault"} and node.args:
            key = _const_str(node.args[0])
            if key is not None:
                return f"{inner}.{key}" if inner else key
        if func.attr == "copy" or func.attr in {"items", "keys", "values"}:
            return inner
        return inner if func.attr == "get" else None

    def _resolve_boolop(self, node: ast.BoolOp) -> str | None:
        if not isinstance(node.op, ast.Or):
            return None
        for v in node.values:
            r = self._resolve(v)
            if r is not None:
                return r
        return None

    # ── visitors ─────────────────────────────────────────────────────
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        info, params = self._class_surface(node)
        if info.fields or params:
            self.models[node.name] = info
            self.callable_params[node.name] = info.fields | params
        self.generic_visit(node)

    @staticmethod
    def _class_surface(node: ast.ClassDef) -> tuple["_ModelInfo", set[str]]:
        """Annotated/assigned field names + init-method params of a class."""
        info = _ModelInfo(node.name)
        params: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                info.fields.add(stmt.target.id)
            elif isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        info.fields.add(t.id)
            elif isinstance(stmt, ast.FunctionDef) and stmt.args:
                params |= _param_names(stmt.args)
        return info, params

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        params = _param_names(node.args)
        if params:
            self.callable_params.setdefault(node.name, set()).update(params)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            if isinstance(t, ast.Name):
                self._pending_assigns.append((t.id, node.value))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            self._pending_assigns.append((node.target.id, node.value))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        src = self._resolve(node.iter)
        if src is not None:
            self._record(src, node.lineno, "iterate")
        elif isinstance(node.iter, ast.Call) and isinstance(
            node.iter.func, ast.Attribute,
        ) and node.iter.func.attr in {"items", "keys", "values"}:
            src = self._resolve(node.iter.func.value)
            if src is not None:
                self._record(src, node.lineno, "iterate")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and node.value.isidentifier():
            self.literals.add(node.value)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # "key" in <alias>  /  "key" not in <alias>
        if node.ops and isinstance(node.ops[0], (ast.In, ast.NotIn)):
            left, right = node.left, node.comparators[0]
            for cand, key_node in ((right, left), (left, right)):
                src = self._resolve(cand)
                key = _const_str(key_node)
                if key is not None:
                    self.key_uses.add(key)
                if src is not None and key is not None:
                    self._record(f"{src}.{key}" if src else key,
                                 node.lineno, "contains")
                    break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._record_kwarg_names(node)
        self._record_splat_reads(node)
        self._record_model_reads(node)
        self._record_method_reads(node)
        self.generic_visit(node)

    def _record_kwarg_names(self, node: ast.Call) -> None:
        # name= keyword arguments count as key use (ctor/param names often
        # mirror config keys)
        for kw in node.keywords:
            if kw.arg is not None:
                self.key_uses.add(kw.arg)

    def _record_splat_reads(self, node: ast.Call) -> None:
        # splat: f(**<alias>)
        for kw in node.keywords:
            if kw.arg is not None:
                continue
            src = self._resolve(kw.value)
            if src is None:
                continue
            callee = ""
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr
            self._record(src, node.lineno, "splat")
            for p in self.callable_params.get(callee, ()):
                self._record(f"{src}.{p}" if src else p,
                             node.lineno, "splat")

    def _record_model_reads(self, node: ast.Call) -> None:
        # model_validate / Model(**x) / Model(x)
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {
            "model_validate", "parse_obj",
        }:
            model = func.value.id if isinstance(func.value, ast.Name) else ""
            if node.args:
                src = self._resolve(node.args[0])
                if src is not None:
                    self._apply_model(model, src, node.lineno)
        elif isinstance(func, ast.Name) and func.id in self.models:
            src = self._resolve(node.args[0]) if node.args else None
            if src is not None:
                self._apply_model(func.id, src, node.lineno)

    def _record_method_reads(self, node: ast.Call) -> None:
        # <alias>.get/pop/setdefault("k") / <alias>.items()/.keys()/.values()
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        if func.attr in {"get", "pop", "setdefault"}:
            self._record_keyed_read(node, func)
        elif func.attr in {"items", "keys", "values"}:
            src = self._resolve(node)
            if src is not None:
                self._record(src, node.lineno, "iterate")

    def _record_keyed_read(self, node: ast.Call, func: ast.Attribute) -> None:
        key = _const_str(node.args[0]) if node.args else None
        if key is not None:
            self.key_uses.add(key)
        base = self._resolve(func.value)
        if base is not None and key is not None:
            self._record(f"{base}.{key}" if base else key,
                         node.lineno, func.attr)
            return
        src = self._resolve(node)
        if src is not None:
            self._record(src, node.lineno, func.attr)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        src = self._resolve(node.value)
        key = _const_str(node.slice)
        if key is not None:
            self.key_uses.add(key)
        if src is not None and key is not None:
            self._record(f"{src}.{key}" if src else key, node.lineno, "subscript")
        self.generic_visit(node)

    def _apply_model(self, model: str, src: str, lineno: int) -> None:
        info = self.models.get(model)
        self._record(src, lineno, "model")
        for f_ in (info.fields if info else ()):
            self._record(f"{src}.{f_}" if src else f_, lineno, "model")

    def _record(self, path: str, line: int, kind: _AccessKind) -> None:
        self.reads.append(Read(path=path, file=self.rel, line=line,
                               kind=kind, scope=self.scope))

    def resolve_aliases(self) -> None:
        """Iterate pending assignments until the alias map stabilises.

        Each target is resolved with its own current binding removed, so a
        self-referential ``x = x.get("k")`` cannot extend its own path every
        round (which would never converge). Real alias chains are shallow;
        10 passes is generous headroom.
        """
        for _ in range(10):
            changed = False
            for name, expr in self._pending_assigns:
                prior = self.aliases.pop(name, None)
                r = self._resolve(expr)
                if prior is not None:
                    self.aliases[name] = prior
                if r is not None and r != prior:
                    self.aliases[name] = r
                    changed = True
            if not changed:
                break


def _param_names(args: ast.arguments) -> set[str]:
    """Callable param names minus the bound-method slots."""
    return {
        a.arg for a in args.args + args.kwonlyargs
        if a.arg not in {"self", "cls"}
    }


def _const_str(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Index):  # py<3.9 compat shape
        return _const_str(node.value)  # pragma: no cover
    return None


def _scan_file(path: Path) -> _FileScan | None:
    rel = str(path.relative_to(REPO_ROOT))
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None
    scan = _FileScan(rel)
    scan.visit(tree)
    # pre-pass discovered class/function params; a second visit applies them
    scan.resolve_aliases()
    scan2 = _FileScan(rel)
    scan2.models = scan.models
    scan2.callable_params = scan.callable_params
    scan2.visit(tree)
    scan2.aliases.update(scan.aliases)
    scan2.resolve_aliases()
    # third pass so reads see aliases resolved by the fixpoint
    scan3 = _FileScan(rel)
    scan3.models = scan.models
    scan3.callable_params = scan.callable_params
    scan3.aliases.update(scan2.aliases)
    scan3.resolve_aliases()
    scan3.visit(tree)
    return scan3


def _build_name_index(scans: list[_FileScan]) -> dict[str, set[str]]:
    """Names seen as dict-key access (.get/[]/pop/setdefault/kwarg/`in`) or
    model field on any object — resolvable or not."""
    idx: dict[str, set[str]] = {}
    for s in scans:
        for name in s.key_uses:
            idx.setdefault(name, set()).add(s.rel)
        for m in s.models.values():
            for f_ in m.fields:
                idx.setdefault(f_, set()).add(s.rel)
    return idx


def _build_literal_index(scans: list[_FileScan]) -> dict[str, set[str]]:
    """Bare string literals per name (weakest evidence: dynamic-key tables)."""
    idx: dict[str, set[str]] = {}
    for s in scans:
        for lit in s.literals:
            idx.setdefault(lit, set()).add(s.rel)
    return idx


def _ancestors(path: str) -> Iterable[str]:
    anc = path
    while "." in anc:
        anc = anc.rsplit(".", 1)[0]
        yield anc


def _index_reads(scans: list[_FileScan]) -> tuple[
        dict[str, list[Read]], dict[str, list[Read]], set[str]]:
    direct: dict[str, list[Read]] = {}
    downstream: dict[str, list[Read]] = {}
    iterated: set[str] = set()   # parents consumed wholesale
    for s in scans:
        for r in s.reads:
            (direct if r.scope == "direct" else downstream).setdefault(
                r.path, []).append(r)
            if r.kind in {"iterate", "splat", "model"}:
                iterated.add(r.path)
    return direct, downstream, iterated


def _any_read(path: str, direct: dict[str, list[Read]],
              downstream: dict[str, list[Read]]) -> Read | None:
    rs = direct.get(path) or downstream.get(path)
    return rs[0] if rs else None


def _bulk_status(path: str, iterated: set[str],
                 direct: dict[str, list[Read]],
                 downstream: dict[str, list[Read]]) -> tuple[str, str] | None:
    # An ancestor consumed wholesale (items()/splat/model) covers leaves.
    for anc in _ancestors(path):
        if anc in iterated:
            ev = _any_read(anc, direct, downstream)
            return "consumed-bulk", _fmt(ev) if ev else ""
    return None


def _weak_status(path: str, name_index: dict[str, set[str]],
                 literal_index: dict[str, set[str]]) -> tuple[str, str] | None:
    leaf = path.rsplit(".", 1)[-1]
    if leaf in name_index:
        return "indirect-name-match", ", ".join(sorted(name_index[leaf])[:3])
    if leaf in literal_index:
        return "indirect-literal", ", ".join(sorted(literal_index[leaf])[:3])
    return None


def _dead_status(path: str, direct: dict[str, list[Read]],
                 downstream: dict[str, list[Read]]) -> tuple[str, str]:
    # Parent section was fetched but this leaf never: strong dead signal.
    for anc in _ancestors(path):
        ev = _any_read(anc, direct, downstream)
        if ev is not None:
            return "UNREFERENCED", f"section read {_fmt(ev)}; key never"
    return "UNREFERENCED", "no consumer reads this key"


def _row_status(path: str, direct: dict[str, list[Read]],
                downstream: dict[str, list[Read]], iterated: set[str],
                name_index: dict[str, set[str]],
                literal_index: dict[str, set[str]]) -> tuple[str, str]:
    if path in direct:
        return "consumed-direct", _fmt(direct[path][0])
    if path in downstream:
        return "consumed-downstream", _fmt(downstream[path][0])
    bulk = _bulk_status(path, iterated, direct, downstream)
    if bulk is not None:
        return bulk
    weak = _weak_status(path, name_index, literal_index)
    if weak is not None:
        return weak
    return _dead_status(path, direct, downstream)


def classify(leaves: dict[str, Any], scans: list[_FileScan],
             name_index: dict[str, set[str]],
             literal_index: dict[str, set[str]]) -> list[dict[str, Any]]:
    direct, downstream, iterated = _index_reads(scans)
    rows = []
    for path in sorted(leaves):
        st, ev = _row_status(path, direct, downstream, iterated,
                             name_index, literal_index)
        rows.append({"key": path, "value": leaves[path],
                     "status": st, "evidence": ev})
    return rows


def _fmt(r: Read) -> str:
    return f"{r.file}:{r.line} ({r.kind})"


def render_markdown(rows: list[dict[str, Any]],
                    reads_in_scope: int) -> str:
    unref = [r for r in rows if r["status"] == "UNREFERENCED"]
    indirect = [r for r in rows if r["status"] == "indirect-name-match"]
    literal = [r for r in rows if r["status"] == "indirect-literal"]
    down = [r for r in rows if r["status"] == "consumed-downstream"]
    bulk = [r for r in rows if r["status"] == "consumed-bulk"]
    direct = [r for r in rows if r["status"] == "consumed-direct"]

    def table(rs: list[dict[str, Any]], show_val: bool = True) -> str:
        lines = ["| key | value | evidence |", "|---|---|---|"]
        for r in rs:
            val = json.dumps(r["value"])[:60] if show_val else ""
            lines.append(f"| `{r['key']}` | `{val}` | {r['evidence']} |")
        return "\n".join(lines)

    parts = [
        "# config.yaml key sweep",
        "",
        f"- config leaves examined: **{len(rows)}**",
        f"- resolved key reads recorded: **{reads_in_scope}**",
        f"- consumed by orchestrator_*/crusher_labs/sanity_checker (direct): {len(direct)}",
        f"- consumed via bulk access (`.items()`, splat, model_validate): {len(bulk)}",
        f"- consumed only downstream (engines/picard/scripts/tests): {len(down)}",
        f"- weak evidence (name matches a dict access or model field somewhere): {len(indirect)}",
        f"- weakest evidence (name appears only as a bare string literal): {len(literal)}",
        f"- **UNREFERENCED — candidates for removal: {len(unref)}**",
        "",
        "> Report-only. Review `UNREFERENCED` and `indirect-name-match` rows",
        "> before deleting anything; static analysis cannot see keys built",
        "> dynamically (f-strings, getattr) or read by external tooling.",
        "",
    ]
    if unref:
        parts += ["## Unreferenced keys", "", table(unref), ""]
    if indirect:
        parts += [
            "## Weak-evidence keys (name matches somewhere; path unresolved)",
            "", table(indirect), "",
        ]
    if literal:
        parts += [
            "## Literal-only keys (name appears in a string literal; likely a "
            "dynamic-key table — verify before removing)",
            "", table(literal), "",
        ]
    if down:
        parts += [
            "## Keys read only outside orchestrator_*/crusher_labs/sanity_checker",
            "", table(down, show_val=False), "",
        ]
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stdout", action="store_true",
                    help="print the markdown report instead of writing reports/")
    args = ap.parse_args()

    leaves = _config_leaf_paths()
    scans: list[_FileScan] = []
    for py in _iter_python_files():
        s = _scan_file(py)
        if s:
            scans.append(s)

    reads = [r for s in scans for r in s.reads]
    name_index = _build_name_index(scans)
    literal_index = _build_literal_index(scans)
    rows = classify(leaves, scans, name_index, literal_index)
    md = render_markdown(rows, len(reads))

    if args.stdout:
        print(md)
        return

    REPORTS_DIR.mkdir(exist_ok=True)
    md_path = REPORTS_DIR / "config_key_sweep.md"
    json_path = REPORTS_DIR / "config_key_sweep.json"
    md_path.write_text(md + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps({"config": str(CONFIG_PATH.relative_to(REPO_ROOT)),
                    "keys": rows}, indent=2),
        encoding="utf-8",
    )
    n_unref = sum(1 for r in rows if r["status"] == "UNREFERENCED")
    print(f"Wrote {md_path} and {json_path}")
    print(f"{len(rows)} keys scanned; {n_unref} unreferenced candidates")


if __name__ == "__main__":
    main()
