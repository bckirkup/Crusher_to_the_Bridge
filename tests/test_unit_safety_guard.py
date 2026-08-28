"""Regression guards for configuration and per-epoch unit declarations."""

from __future__ import annotations

import ast
import fnmatch
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = "telemetry_buffer/clock_audit/unit_safety_spec.md"
UNIT_KEY = re.compile(r"(?:_per_epoch|_epochs)$")
PER_EPOCH_CONSTANT = re.compile(r"_(?:RATE|FRACTION|PROBABILITY|DECAY)$")

# Each entry is a deliberate, path-scoped exception to the package-wide rule.
ALLOWED_EPOCH_KEYS = (
    # Schema declarations retain retired aliases for old-document validation.
    ("schemas/pathogen_profiles.schema.json", "colonization_rate_per_epoch"),  # retired alias
    ("schemas/pathogen_profiles.schema.json", "decay_rate_per_epoch"),  # retired alias
    ("schemas/pathogen_profiles.schema.json", "exposure_probability_per_epoch"),  # retired alias
    ("schemas/pathogen_profiles.schema.json", "growth_rate_per_epoch"),  # retired alias
    ("schemas/pathogen_profiles.schema.json", "spore_decay_rate_per_epoch"),  # retired alias
    ("schemas/resource_costs.schema.json", "baseline_surveillance_costs_per_epoch"),  # retired alias
    ("schemas/protocols.schema.json", "costs_per_epoch"),  # active protocol maintenance unit
    ("schemas/lab_notebook.schema.json", "total_epochs"),  # output bookkeeping
    ("schemas/picard_run_spec.schema.json", "num_epochs"),  # run-length bookkeeping
    ("schemas/sentinel_recovery_design.schema.json", "default_epochs"),  # run-length bookkeeping
    ("schemas/sentinel_recovery_design.schema.json", "disembark_window_epochs"),  # Sentinel itinerary alias
    ("schemas/sentinel_recovery_design.schema.json", "embarkation_window_epochs"),  # Sentinel itinerary alias
    ("schemas/sentinel_recovery_design.schema.json", "reembark_window_epochs"),  # Sentinel itinerary alias
    ("schemas/sentinel_recovery_design.schema.json", "sampling_interval_epochs"),  # Sentinel wastewater cadence
    ("schemas/voyage_config.schema.json", "total_epochs"),  # run-length bookkeeping
    ("_epoch_timing/*.json", "mean_seconds_per_epoch"),  # benchmark output rate
    ("campaign_summary.json", "total_quarantine_person_epochs"),  # output bookkeeping
    ("campaign_summary.json", "num_epochs"),  # output bookkeeping
    ("campaign_summary.json", "n_epochs"),  # output bookkeeping
    ("campaign_summary.json", "parameters.num_epochs"),  # output bookkeeping
    ("campaign_summary.json", "derived.total_quarantine_person_epochs"),  # output bookkeeping
    ("campaign_summary.json", "timeseries.n_epochs"),  # output bookkeeping
    ("crusher_labs/config.yaml", "num_epochs"),  # run-length bookkeeping
    ("crusher_labs/config.yaml", "sampling_interval_epochs"),  # Sentinel wastewater consumer; defer to separate unit pass required by AGENTS.md
    ("data/config/instrument_turnaround.json", "delay_epochs"),  # grid-native same-epoch queue sentinel
    ("data/config/protocols.json", "costs_per_epoch"),  # active protocol maintenance debit per simulation epoch
    ("data/platforms/*/voyage_config.json", "total_epochs"),  # run-length bookkeeping
    ("picard_framework/runs/*.json", "num_epochs"),  # run-length bookkeeping
    ("picard_framework/runs/mega_cruise_campaign/*.json", "default_epochs"),  # run-length bookkeeping
    ("picard_framework/runs/mega_cruise_campaign/*.json", "sampling_interval_epochs"),  # Sentinel wastewater consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/runs/mega_cruise_campaign/*.json", "disembark_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/runs/mega_cruise_campaign/*.json", "embarkation_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/runs/mega_cruise_campaign/*.json", "reembark_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/analysis/sentinel/data/*.json", "total_epochs"),  # Sentinel run-length bookkeeping; defer to separate unit pass required by AGENTS.md
    ("picard_framework/analysis/sentinel/data/*.json", "disembark_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/analysis/sentinel/data/*.json", "embarkation_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
    ("picard_framework/analysis/sentinel/data/*.json", "reembark_window_epochs"),  # Sentinel itinerary consumer; defer to separate unit pass required by AGENTS.md
)

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
            if not any(
                fnmatch.fnmatch(path.relative_to(REPO_ROOT).as_posix(), path_glob)
                and key == allowed_key
                for path_glob, allowed_key in ALLOWED_EPOCH_KEYS
            )
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


def _module_constant_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for statement in tree.body:
        targets = (
            statement.targets
            if isinstance(statement, ast.Assign)
            else [statement.target]
            if isinstance(statement, ast.AnnAssign)
            else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and PER_EPOCH_CONSTANT.search(target.id):
                names.add(target.id)
    return names


def _names_in(node: ast.AST, names: set[str]) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and child.id in names
    }


def _target_occurs_in_value(target: ast.AST, value: ast.AST) -> bool:
    target_dump = ast.dump(target)
    return any(ast.dump(child) == target_dump for child in ast.walk(value))


def find_per_epoch_constant_offenders(source: str) -> list[tuple[str, str]]:
    """Find per-epoch methods using mutable-rate module constants."""
    tree = ast.parse(source)
    module_constants = _module_constant_names(tree)
    offenders: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _per_epoch_method(node):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign):
                names = _names_in(child.value, module_constants)
                offenders.extend((node.name, name) for name in sorted(names))
            elif isinstance(child, ast.Assign):
                names = _names_in(child.value, module_constants)
                if names and any(
                    _target_occurs_in_value(target, child.value)
                    for target in child.targets
                ):
                    offenders.extend((node.name, name) for name in sorted(names))
    return offenders


def test_per_epoch_constant_detector_catches_rhs_mutation() -> None:
    source = """
SURFACE_DECAY_RATE = 0.05
class E:
    def transport_step(self, epoch):
        self.pool *= (1 - SURFACE_DECAY_RATE)
"""
    assert find_per_epoch_constant_offenders(source) == [
        ("transport_step", "SURFACE_DECAY_RATE"),
    ]


def test_per_epoch_constant_detector_allows_clock_conversion() -> None:
    source = """
SURFACE_DECAY_PER_DAY = 0.05
class E:
    def transport_step(self, epoch):
        self.pool *= (1 - self.clock.decay_per_epoch(SURFACE_DECAY_PER_DAY))
"""
    assert find_per_epoch_constant_offenders(source) == []


def test_per_epoch_constants_do_not_accumulate_without_units() -> None:
    offenders: list[tuple[Path, str, str]] = []
    for path in REPO_ROOT.rglob("*.py"):
        if "tests" in path.parts or "telemetry_buffer" in path.parts:
            continue
        try:
            source = path.read_text()
        except OSError:
            continue
        try:
            offenders_in_file = find_per_epoch_constant_offenders(source)
        except SyntaxError:
            continue
        for method, name in offenders_in_file:
            if name not in ALLOWED_PER_EPOCH_CONSTANTS:
                offenders.append((path.relative_to(REPO_ROOT), name, method))
    assert not offenders, (
        f"Per-epoch module constant mutation {offenders}; declare physical units "
        f"or add a narrow justified exception per {SPEC}."
    )
