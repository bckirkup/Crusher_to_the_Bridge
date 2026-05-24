"""
test_schema_module.py – Unit tests for telemetry_buffer.schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validates the ground-truth payload construction and IO helpers.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from telemetry_buffer.schema import (
    SCHEMA_VERSION,
    make_agent,
    make_ground_truth,
    make_space,
    read_ground_truth,
    write_ground_truth,
)


class TestMakeAgent:
    def test_default_agent(self) -> None:
        agent = make_agent(agent_id=0)
        assert agent["agent_id"] == 0
        assert agent["symptom_status"] == "asymptomatic"
        assert agent["shedding_rate"] == 0.0

    def test_agent_with_location(self) -> None:
        agent = make_agent(agent_id=5, location="Bridge")
        assert agent["location"] == "Bridge"

    def test_agent_without_location(self) -> None:
        agent = make_agent(agent_id=1)
        assert "location" not in agent


class TestMakeSpace:
    def test_default_space(self) -> None:
        space = make_space()
        assert space["pathogen_mass"] == 0.0
        assert space["microbiome_id"] == "baseline"

    def test_custom_space(self) -> None:
        space = make_space(pathogen_mass=42.5, microbiome_id="disrupted")
        assert space["pathogen_mass"] == 42.5
        assert space["microbiome_id"] == "disrupted"


class TestMakeGroundTruth:
    def test_structure(self) -> None:
        agents = [make_agent(0), make_agent(1)]
        spaces = {"Bridge": make_space(), "MedBay": make_space(pathogen_mass=10.0)}
        gt = make_ground_truth(epoch=5, agents=agents, spaces=spaces)
        assert gt["schema_version"] == SCHEMA_VERSION
        assert gt["epoch"] == 5
        assert len(gt["agents"]) == 2
        assert "Bridge" in gt["spaces"]


class TestIOHelpers:
    def test_write_and_read_roundtrip(self, tmp_path: str) -> None:
        path = os.path.join(str(tmp_path), "test_gt.json")
        payload = make_ground_truth(
            epoch=0,
            agents=[make_agent(0, symptom_status="symptomatic", shedding_rate=50.0)],
            spaces={"Galley": make_space(pathogen_mass=100.0)},
        )
        write_ground_truth(payload, path)
        loaded = read_ground_truth(path)
        assert loaded == payload
