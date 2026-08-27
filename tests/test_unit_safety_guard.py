"""Regression guards for configuration and per-epoch unit declarations."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = "telemetry_buffer/clock_audit/unit_safety_spec.md"
UNIT_KEY = re.compile(r"(?:_per_epoch|_epochs)$")
PER_EPOCH_CONSTANT = re.compile(r"_(?:RATE|FRACTION|PROBABILITY|DECAY)$")

# Each entry is a deliberate exception to the package-wide unit-key rule.
ALLOWED_EPOCH_KEYS = {
    "activation_delay_epochs",  # retired compatibility aliases warn at read time
    "baseline_surveillance_costs_per_epoch",  # cost ledger bookkeeping
    "colonization_rate_per_epoch",  # pathogen environmental rate is per epoch
    "costs_per_epoch",  # protocol cost accrual is per epoch
    "decay_rate_per_epoch",  # pathogen environmental rate is per epoch
    "default_epochs",  # campaign and Sentinel run-length bookkeeping
    "delay_epochs",  # instrument turnaround internal epoch representation
    "derived.total_quarantine_person_epochs",  # output bookkeeping field
    "disembark_window_epochs",  # Sentinel follow-up retains this alias
    "embarkation_window_epochs",  # Sentinel follow-up retains this alias
    "exposure_probability_per_epoch",  # pathogen environmental per-epoch probability
    "growth_rate_per_epoch",  # pathogen food-pool per-epoch rate
    "mean_seconds_per_epoch",  # benchmark output rate
    "num_epochs",  # simulation run-length bookkeeping
    "parameters.num_epochs",  # campaign output bookkeeping field
    "reembark_window_epochs",  # Sentinel follow-up retains this alias
    "sampling_interval_epochs",  # Sentinel follow-up retains this cadence
    "spore_decay_rate_per_epoch",  # pathogen environmental per-epoch rate
    "timeseries.n_epochs",  # telemetry output bookkeeping field
    "total_epochs",  # simulation run-length bookkeeping
}

# No current module constant should be incremented or multiplied inside an
# epoch-step method; retained entries belong here only with a justification.
ALLOWED_PER_EPOCH_CONSTANTS: dict[str, str] = {}


def _iter_config_files() -> list[Path]:
    return [
        path
        for suffix in ("*.json", "*.yaml", "*.yml")
        for path in REPO_ROOT.rglob(suffix)
        if "telemetry_buffer" not in path.parts and ".git" not in path.parts
    ]


def _load(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text())
    return yaml.safe_load(path.read_text())


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and UNIT_KEY.search(key):
                keys.append(key)
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def test_config_unit_keys_are_explicitly_declared() -> None:
    offenders: list[tuple[Path, str]] = []
    for path in _iter_config_files():
        try:
            keys = _walk_keys(_load(path))
        except (OSError, ValueError, yaml.YAMLError):
            continue
        offenders.extend(
            (path.relative_to(REPO_ROOT), key)
            for key in keys
            if key not in ALLOWED_EPOCH_KEYS
        )
    assert not offenders, (
        f"Undeclared epoch-unit key(s) {offenders}; rename to a physical unit "
        f"or add a narrow justified exception per {SPEC}."
    )


def _per_epoch_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return (
        "epoch" in node.name
        or "step" in node.name
        or any(arg.arg == "epoch" for arg in node.args.args)
    )


def test_per_epoch_constants_do_not_accumulate_without_units() -> None:
    offenders: list[tuple[Path, str, str]] = []
    for path in REPO_ROOT.rglob("*.py"):
        if "tests" in path.parts or "telemetry_buffer" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text())
        except (OSError, SyntaxError):
            continue
        module_constants: set[str] = set()
        for statement in tree.body:
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
                if isinstance(statement, ast.AnnAssign)
                else []
            )
            for target in targets:
                if isinstance(target, ast.Name) and PER_EPOCH_CONSTANT.search(
                    target.id,
                ):
                    module_constants.add(target.id)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _per_epoch_method(node):
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.AugAssign):
                    continue
                if not isinstance(child.target, ast.Name):
                    continue
                if child.target.id in module_constants and child.target.id not in (
                    ALLOWED_PER_EPOCH_CONSTANTS
                ):
                    offenders.append((path.relative_to(REPO_ROOT), child.target.id, node.name))
    assert not offenders, (
        f"Per-epoch module constant mutation {offenders}; declare physical units "
        f"or add a narrow justified exception per {SPEC}."
    )
