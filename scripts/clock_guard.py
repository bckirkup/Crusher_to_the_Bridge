#!/usr/bin/env python3
"""Guards the one place days and epochs are allowed to meet.

Pathogen natural history is parameterised in days; the simulation advances in
epochs; ``engines.sim_clock.SimClock`` converts between them. Nothing else may.
This checker enforces that mechanically, because the units are not in the type
system and the failure mode is silent — a day-valued threshold compared against
an epoch counter runs natural history 24x fast without raising anything.

Rules
    CLOCK001  A day-named value compared against an epoch-named counter.
    CLOCK002  A literal 24 used as a conversion factor outside ``sim_clock``.
    CLOCK003  Configs declaring two different epoch durations or clock modes.

``# clock-exempt: <reason>`` on the offending line suppresses CLOCK002 for
genuine hour-of-day arithmetic (a circadian term is not a unit conversion).

Usage
    python3 scripts/clock_guard.py engines/ crusher_labs/
    python3 scripts/clock_guard.py --configs
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

CLOCK_MODULE = Path("engines/sim_clock.py")
EXEMPT_MARKER = "clock-exempt"

#: Names whose value is a count of days of natural history.
_DAY_SUFFIXES = ("_day", "_days")
#: Names whose value is a count of simulation epochs.
_EPOCH_SUFFIXES = ("_epoch", "_epochs")
#: Epoch counters that predate the naming convention and cannot be renamed
#: without breaking the recorded telemetry contract.
_EPOCH_NAMES = frozenset({"epoch", "time_infected", "epochs"})
#: Day-valued names that predate the convention.
_DAY_NAMES = frozenset({"dpi", "days_post_infection", "days_infected"})

_CONFIG_GLOBS = (
    "crusher_labs/config.yaml",
    "data/platforms/*/voyage_config.json",
    "data/config/*.json",
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:1: {self.rule} {self.message}"


def _label(node: ast.AST) -> str:
    """The readable name a comparison operand carries, if it has one."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        value = node.slice.value
        return value if isinstance(value, str) else ""
    if isinstance(node, ast.Call):
        return _label(node.func)
    return ""


def _is_day_valued(node: ast.AST) -> bool:
    name = _label(node)
    return bool(name) and (
        name in _DAY_NAMES or name.endswith(_DAY_SUFFIXES)
    )


def _is_epoch_valued(node: ast.AST) -> bool:
    name = _label(node)
    return bool(name) and (
        name in _EPOCH_NAMES or name.endswith(_EPOCH_SUFFIXES)
    )


def _mixed_units(left: ast.AST, right: ast.AST) -> bool:
    return (_is_day_valued(left) and _is_epoch_valued(right)) or (
        _is_epoch_valued(left) and _is_day_valued(right)
    )


def _comparison_findings(path: Path, tree: ast.AST) -> Iterator[Finding]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for left, right in zip(operands, operands[1:]):
            if _mixed_units(left, right):
                yield Finding(
                    path,
                    node.lineno,
                    "CLOCK001",
                    f"{_label(left)!r} and {_label(right)!r} are different units; "
                    "convert through the run's SimClock first",
                )


def _is_conversion_factor(node: ast.BinOp) -> bool:
    if not isinstance(node.op, (ast.Mult, ast.Div, ast.FloorDiv)):
        return False
    return any(
        isinstance(side, ast.Constant) and side.value in (24, 24.0)
        for side in (node.left, node.right)
    )


def _factor_findings(path: Path, tree: ast.AST, lines: list[str]) -> Iterator[Finding]:
    if path == CLOCK_MODULE:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not _is_conversion_factor(node):
            continue
        source = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
        if EXEMPT_MARKER in source:
            continue
        yield Finding(
            path,
            node.lineno,
            "CLOCK002",
            "literal 24 as a conversion factor; use SimClock, or mark the line "
            f"'# {EXEMPT_MARKER}: <reason>' if this is hour-of-day arithmetic",
        )


def check_python_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return [Finding(path, error.lineno or 1, "CLOCK000", f"unparseable: {error.msg}")]
    lines = text.splitlines()
    return [
        *_comparison_findings(path, tree),
        *_factor_findings(path, tree, lines),
    ]


def _load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    return loaded if isinstance(loaded, dict) else {}


def _declared(cfg: dict[str, Any], key: str) -> list[Any]:
    voyage = cfg.get("voyage") if isinstance(cfg.get("voyage"), dict) else {}
    return [value for value in (cfg.get(key), voyage.get(key)) if value is not None]


def check_config_file(path: Path) -> list[Finding]:
    cfg = _load_config(path)
    findings: list[Finding] = []
    for key in ("epoch_duration_hours", "natural_history_clock"):
        declared = _declared(cfg, key)
        if len(declared) > 1 and len({str(value) for value in declared}) > 1:
            findings.append(
                Finding(
                    path,
                    1,
                    "CLOCK003",
                    f"{key} declared twice with different values {declared}; "
                    "a run has one clock",
                ),
            )
    return findings


def _python_files(paths: Iterable[Path]) -> Iterator[Path]:
    for path in paths:
        if path.is_dir():
            yield from sorted(
                candidate
                for candidate in path.rglob("*.py")
                if "__pycache__" not in candidate.parts
            )
        elif path.suffix == ".py":
            yield path


def _config_files(root: Path) -> Iterator[Path]:
    for pattern in _CONFIG_GLOBS:
        yield from sorted(root.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configs",
        action="store_true",
        help="check shipped configs for disagreeing clock declarations",
    )
    parser.add_argument("paths", nargs="*", type=Path, help="files or directories")
    args = parser.parse_args()

    if args.configs:
        targets = args.paths or list(_config_files(Path()))
        findings = [f for path in targets for f in check_config_file(path)]
    else:
        findings = [f for path in _python_files(args.paths) for f in check_python_file(path)]

    for finding in findings:
        print(finding.render())
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
