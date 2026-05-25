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


class TestLaw1NoHardcodedEpochSchedules:
    """Verify no hardcoded epoch lists drive intervention activation."""

    def _get_orchestrator_source(self) -> str:
        path = os.path.join(REPO_ROOT, "orchestrator.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_no_epoch_intervention_lists(self) -> None:
        src = self._get_orchestrator_source()
        patterns = [
            r"intervention_epochs\s*=\s*\[",
            r"activate_at_epoch\s*=\s*\[",
            r"sop_schedule\s*=\s*\{",
        ]
        for pat in patterns:
            assert not re.search(pat, src), f"Hardcoded epoch schedule pattern found: {pat}"


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

    def _get_orchestrator_source(self) -> str:
        path = os.path.join(REPO_ROOT, "orchestrator.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_no_hardcoded_zone_names_in_logic(self) -> None:
        src = self._get_orchestrator_source()
        # Filter out print/display/docstring lines
        logic_lines = []
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if "print(" in line:
                continue
            logic_lines.append(line)
        logic_src = "\n".join(logic_lines)

        for pat in self.HARDCODED_ZONE_PATTERNS:
            matches = re.findall(pat, logic_src)
            assert not matches, f"Hardcoded zone name found: {pat} ({len(matches)} occurrences)"

    def test_no_hardcoded_pathogen_names_in_logic(self) -> None:
        src = self._get_orchestrator_source()
        logic_lines = []
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if "print(" in line:
                continue
            logic_lines.append(line)
        logic_src = "\n".join(logic_lines)

        for pat in self.HARDCODED_PATHOGEN_PATTERNS:
            matches = re.findall(pat, logic_src)
            assert not matches, f"Hardcoded pathogen name found: {pat}"


class TestLaw3ScalarBounds:
    """Verify scalars that represent physical quantities stay in [0, 1]."""

    BOUNDED_KEYS = [
        "hvac_filter_efficiency_override",
        "surface_decontamination_factor",
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
        src_path = os.path.join(REPO_ROOT, "orchestrator.py")
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        for repo in self.SIBLING_REPOS:
            write_patterns = [
                f"{repo}.*\\.write",
                f"{repo}.*\\.save",
                f"{repo}.*\\.modify",
            ]
            for pat in write_patterns:
                assert not re.search(pat, src), (
                    f"Potential sibling repo modification: {pat}"
                )
