"""
test_law_compliance.py – Ensure the Laws from .cursorrules are not violated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Law 1: No hardcoded epoch schedules for interventions
Law 2: No hardcoded zone or pathogen names
Law 3: Scalar bounds are physical laws (values in [0, 1])
Law 4: No external bioinformatics tool dependencies
Law 5: Maintain referential integrity across JSON configs
Law 6: Never modify sibling repos
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# All orchestrator modules that contain logic (not just data/display)
ORCHESTRATOR_MODULES = [
    "orchestrator.py",
    "orchestrator_types.py",
    "orchestrator_init.py",
    "orchestrator_epoch.py",
    "orchestrator_record.py",
]

# Extended module directories for Law 1–4 scanning (closes #82)
EXTENDED_DIRS = [
    "picard_framework",
    "crusher_labs",
    "decision_engine",
]


def _read_orchestrator_sources() -> dict[str, str]:
    """Read all orchestrator module source files into a dict."""
    sources: dict[str, str] = {}
    for mod in ORCHESTRATOR_MODULES:
        path = os.path.join(REPO_ROOT, mod)
        with open(path, encoding="utf-8") as f:
            sources[mod] = f.read()
    return sources


def _find_mutable_module_assignments(src: str, mod: str) -> str | None:
    tree = ast.parse(src, filename=mod)
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if not name.startswith("_") and name != name.upper():
                    return (
                        f"{mod}:{node.lineno} has mutable module-level "
                        f"variable '{name}' (not UPPER_CASE constant)"
                    )
    return None


def _read_extended_sources() -> dict[str, str]:
    """Read all Python sources under picard_framework/, crusher_labs/, decision_engine/."""
    sources: dict[str, str] = {}
    for dir_name in EXTENDED_DIRS:
        dir_path = os.path.join(REPO_ROOT, dir_name)
        for root, _dirs, files in os.walk(dir_path):
            for fname in files:
                if not fname.endswith(".py") or fname == "__init__.py":
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, REPO_ROOT)
                with open(full, encoding="utf-8") as f:
                    sources[rel] = f.read()
    return sources


def _strip_non_logic(src: str) -> str:
    """Strip comments, docstrings, and print lines from source."""
    logic_lines = []
    for line in src.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("\"\"\"", "'''")):
            continue
        if "print(" in line:
            continue
        logic_lines.append(line)
    return "\n".join(logic_lines)


class TestLaw1NoHardcodedEpochSchedules:
    """Verify no hardcoded epoch lists drive intervention activation."""

    def test_no_epoch_intervention_lists(self) -> None:
        patterns = [
            r"intervention_epochs\s*=\s*\[",
            r"activate_at_epoch\s*=\s*\[",
            r"sop_schedule\s*=\s*\{",
        ]
        for mod, src in _read_orchestrator_sources().items():
            for pat in patterns:
                assert not re.search(pat, src), (
                    f"Hardcoded epoch schedule in {mod}: {pat}"
                )


class TestLaw2NoHardcodedNames:
    """Verify no hardcoded zone or pathogen names in orchestrator logic."""

    HARDCODED_ZONE_PATTERNS = [
        r'"Bridge"',
        r'"MedBay"',
        r'"Galley"',
        r'"Engine_Room"',
        r'"Berthing"',
        r'"Mess_Hall"',
    ]

    HARDCODED_PATHOGEN_PATTERNS = [
        r'"norovirus"',
        r'"sars_cov_2"',
        r'"vibrio_cholerae"',
    ]

    def test_no_hardcoded_zone_names_in_logic(self) -> None:
        for mod, src in _read_orchestrator_sources().items():
            logic_src = _strip_non_logic(src)
            for pat in self.HARDCODED_ZONE_PATTERNS:
                matches = re.findall(pat, logic_src)
                assert not matches, (
                    f"Hardcoded zone name in {mod}: {pat} ({len(matches)} occurrences)"
                )

    def test_no_hardcoded_pathogen_names_in_logic(self) -> None:
        for mod, src in _read_orchestrator_sources().items():
            logic_src = _strip_non_logic(src)
            for pat in self.HARDCODED_PATHOGEN_PATTERNS:
                matches = re.findall(pat, logic_src)
                assert not matches, (
                    f"Hardcoded pathogen name in {mod}: {pat}"
                )


class TestLaw3ScalarBounds:
    """Verify scalars that represent physical quantities stay in [0, 1]."""

    BOUNDED_KEYS = [
        "hvac_filter_efficiency_override",
        "direct_contact_scalar",
        "droplet_scalar",
        "hvac_airborne_scalar",
        "fomite_scalar",
    ]

    def test_protocol_modifier_scalars_bounded(self) -> None:
        path = os.path.join(REPO_ROOT, "data", "config", "protocols.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for proto in data.get("protocols", []):
            mods = proto.get("modifiers", {})
            for key in self.BOUNDED_KEYS:
                if key in mods:
                    val = mods[key]
                    assert 0.0 <= val <= 1.0, (
                        f"{proto['protocol_id']}.modifiers.{key}={val} out of [0,1]"
                    )

    def test_hvac_filter_efficiency_in_config(self) -> None:
        from crusher_labs import load_config
        cfg = load_config()
        hvac_cfg = cfg.get("hvac", {})
        eff = hvac_cfg.get("filter_efficiency", 0.50)
        assert 0.0 <= eff <= 1.0


class TestLaw5ReferentialIntegrity:
    """Cross-validate JSON configs reference each other correctly."""

    def _load_json(self, relpath: str) -> dict:
        path = os.path.join(REPO_ROOT, relpath)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_protocol_instruments_reference_valid_classes(self) -> None:
        valid_classes = {
            "continuous_air_sampler",
            "targeted_surface_swab",
            "wastewater_sequencing_grid",
            "clinical_rdt",
            "clinical_qpcr",
            "clinical_microbiology",
            "wearable_physiological_monitor",
            "wearable_fleet_monitor",
            "detection_escalation",
            "scenario_calendar",
        }
        protocols = self._load_json("data/config/protocols.json")
        for proto in protocols.get("protocols", []):
            trigger_class = proto.get("trigger", {}).get("instrument_class", "")
            assert trigger_class in valid_classes, (
                f"{proto['protocol_id']}: invalid instrument_class '{trigger_class}'"
            )

    def test_protocol_stoplight_levels_valid(self) -> None:
        valid_levels = {"GREEN", "AMBER", "RED"}
        protocols = self._load_json("data/config/protocols.json")
        for proto in protocols.get("protocols", []):
            level = proto.get("trigger", {}).get("stoplight_level", "RED")
            assert level in valid_levels, f"{proto['protocol_id']}: invalid level '{level}'"

    def test_detection_escalation_protocols_require_min_modes(self) -> None:
        protocols = self._load_json("data/config/protocols.json")
        for proto in protocols.get("protocols", []):
            trigger = proto.get("trigger", {})
            if trigger.get("instrument_class") == "detection_escalation":
                assert trigger.get("min_modes_affected", 0) >= 1, (
                    f"{proto['protocol_id']}: detection_escalation requires min_modes_affected"
                )


class TestLaw6NoSiblingRepoModification:
    """Verify no code imports or calls that would modify sibling repos."""

    SIBLING_REPOS = [
        "infection-dynamics",
        "py-contam",
        "GRUMB",
        "EMOD-Generic",
        "FRED",
    ]

    def test_no_write_imports_to_siblings(self) -> None:
        for mod, src in _read_orchestrator_sources().items():
            for repo in self.SIBLING_REPOS:
                write_patterns = [
                    f"{repo}.*\\.write",
                    f"{repo}.*\\.save",
                    f"{repo}.*\\.modify",
                ]
                for pat in write_patterns:
                    assert not re.search(pat, src), (
                        f"Potential sibling repo modification in {mod}: {pat}"
                    )


# ── Extended law compliance for picard_framework/, crusher_labs/, decision_engine/ ──
# Closes #82.

class TestExtendedLaw1NoHardcodedEpochSchedules:
    """Law 1 across extended modules."""

    def test_no_epoch_intervention_lists_extended(self) -> None:
        patterns = [
            r"intervention_epochs\s*=\s*\[",
            r"activate_at_epoch\s*=\s*\[",
            r"sop_schedule\s*=\s*\{",
        ]
        for mod, src in _read_extended_sources().items():
            for pat in patterns:
                assert not re.search(pat, src), (
                    f"Hardcoded epoch schedule in {mod}: {pat}"
                )


class TestExtendedLaw2NoHardcodedNames:
    """Law 2 across extended modules."""

    HARDCODED_PATHOGEN_PATTERNS = [
        r'"norovirus"',
        r'"sars_cov_2"',
        r'"vibrio_cholerae"',
    ]

    def test_no_hardcoded_pathogen_names_in_extended(self) -> None:
        for mod, src in _read_extended_sources().items():
            logic_src = _strip_non_logic(src)
            for pat in self.HARDCODED_PATHOGEN_PATTERNS:
                matches = re.findall(pat, logic_src)
                assert not matches, (
                    f"Hardcoded pathogen name in {mod}: {pat}"
                )


class TestExtendedLaw4NoExternalBioinformaticsDeps:
    """Law 4: no external bioinformatics tool imports."""

    FORBIDDEN_IMPORTS = [
        r"^import\s+(?:Bio|biopython|pysam|samtools|bcftools|blast)",
        r"^from\s+(?:Bio|biopython|pysam)\s+import",
    ]

    def test_no_bioinformatics_imports_in_extended(self) -> None:
        for mod, src in _read_extended_sources().items():
            for pat in self.FORBIDDEN_IMPORTS:
                assert not re.search(pat, src, re.MULTILINE), (
                    f"External bioinformatics import in {mod}: {pat}"
                )


class TestExtendedNoGlobalKeyword:
    """No 'global' keyword in extended module functions."""

    def test_no_global_keyword_in_extended(self) -> None:
        for mod, src in _read_extended_sources().items():
            tree = ast.parse(src, filename=mod)
            for node in ast.walk(tree):
                if isinstance(node, ast.Global):
                    pytest.fail(
                        f"{mod} uses 'global' keyword at line {node.lineno}"
                    )


# ── Pure state isolation tests ───────────────────────────────────────────

class TestPureStateIsolation:
    """Verify segregated functions don't mutate global state or use globals."""

    def test_no_global_keyword_in_orchestrator_modules(self) -> None:
        """No function should use the 'global' keyword."""
        for mod, src in _read_orchestrator_sources().items():
            if mod == "orchestrator.py":
                continue  # thin coordinator may have module-level state
            tree = ast.parse(src, filename=mod)
            for node in ast.walk(tree):
                if isinstance(node, ast.Global):
                    pytest.fail(
                        f"{mod} uses 'global' keyword at line {node.lineno}"
                    )

    def test_no_module_level_mutable_state(self) -> None:
        """Module-level assignments should be constants (UPPER_CASE) or imports."""
        skip_modules = {"orchestrator.py"}
        for mod, src in _read_orchestrator_sources().items():
            if mod in skip_modules:
                continue
            violations = _find_mutable_module_assignments(src, mod)
            if violations:
                pytest.fail(violations)

    def test_step_functions_accept_state_as_parameter(self) -> None:
        """Step functions must receive SimulationState as a parameter, not access it globally."""
        epoch_src = _read_orchestrator_sources()["orchestrator_epoch.py"]
        tree = ast.parse(epoch_src, filename="orchestrator_epoch.py")

        step_functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("step_")
        ]

        for func in step_functions:
            param_names = [a.arg for a in func.args.args]
            has_state = "state" in param_names
            has_syndromic_or_engine = any(
                p in param_names
                for p in ("engine", "syndromic", "proto_ctx", "obs")
            )
            assert has_state or has_syndromic_or_engine, (
                f"step function '{func.name}' at line {func.lineno} does not "
                f"accept state-carrying parameters (found: {param_names})"
            )

    def test_no_os_environ_mutation(self) -> None:
        """Orchestrator modules must not mutate os.environ."""
        for mod, src in _read_orchestrator_sources().items():
            assert "os.environ[" not in src, (
                f"{mod} mutates os.environ"
            )
            assert "os.putenv(" not in src, (
                f"{mod} uses os.putenv"
            )

    def test_no_sys_path_manipulation_in_submodules(self) -> None:
        """Submodules should not manipulate sys.path — only orchestrator.py may."""
        skip = {"orchestrator.py", "presidio_runner.py"}
        for mod, src in _read_orchestrator_sources().items():
            if mod in skip:
                continue
            assert "sys.path" not in src, (
                f"{mod} manipulates sys.path"
            )

    def test_confine_agents_only_mutates_state_parameter(self) -> None:
        """confine_agents must only mutate its 'state' parameter."""
        from orchestrator_types import SimulationState
        from orchestrator_epoch import confine_agents
        from unittest.mock import MagicMock

        state = SimulationState()
        agents = [
            {
                "agent_id": 0,
                "infection_state": "infected",
                "symptom_presentation": "symptomatic",
                "compliance_status": "compliant",
                "shedding_rate": 50.0,
            },
        ]
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True

        confine_agents(1, agents, state, syndromic, include_shedding=False)

        # state was mutated (expected)
        assert 0 in state.quarantined_ids
        # agents list itself was NOT mutated (no items added/removed)
        assert len(agents) == 1
        # agent dict was NOT mutated
        assert agents[0]["symptom_presentation"] == "symptomatic"

    def test_sync_vsp_isolation_only_mutates_state_when_compliant(self) -> None:
        """sync_vsp_isolation must not mutate engine when agents comply."""
        from unittest.mock import MagicMock

        from orchestrator_types import SimulationState
        from orchestrator_epoch import sync_vsp_isolation
        from orchestrator_init import build_engine
        from crusher_labs import load_config

        cfg = load_config()
        engine = build_engine(cfg, seed=42)
        state = SimulationState()
        engine.quarantined_ids = {5, 10}
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True

        original_engine_ids = set(engine.quarantined_ids)
        sync_vsp_isolation(1, engine, state, syndromic)

        # state was mutated (expected)
        assert state.quarantined_ids == {5, 10}
        # engine.quarantined_ids was NOT mutated when agents comply
        assert engine.quarantined_ids == original_engine_ids
