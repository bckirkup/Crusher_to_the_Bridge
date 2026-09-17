"""
test_telemetry_fields.py – Telemetry field-name contract vs. simulation_history schema
"""

from __future__ import annotations

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from telemetry_buffer import fields  # noqa: E402
from telemetry_buffer.agent_axes import (  # noqa: E402
    COMPLIANCE_ISOLATED,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
    resolve_agent_axes,
)

SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas", "simulation_history.schema.json")


def _defs() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)["$defs"]


def _typed_keys(td: type) -> set[str]:
    return set(td.__annotations__)


class TestSchemaAgreement:
    def test_record_required_matches_schema(self) -> None:
        assert set(fields.RECORD_REQUIRED) == set(_defs()["EpochRecord"]["required"])

    def test_epoch_record_keys_cover_schema_properties(self) -> None:
        schema_props = set(_defs()["EpochRecord"]["properties"])
        assert schema_props <= _typed_keys(fields.EpochRecord)

    def test_agent_state_keys_cover_schema_properties(self) -> None:
        schema_props = set(_defs()["AgentState"]["properties"]) - {"status"}
        assert schema_props <= _typed_keys(fields.AgentState)

    def test_zone_state_keys_cover_schema_properties(self) -> None:
        schema_props = set(_defs()["ZoneState"]["properties"])
        assert schema_props <= _typed_keys(fields.ZoneState)

    def test_constants_are_typed_dict_keys(self) -> None:
        agent_keys = _typed_keys(fields.AgentState)
        for name, value in vars(fields).items():
            if name.startswith("AGENT_") and isinstance(value, str):
                assert value in agent_keys, name
        record_keys = _typed_keys(fields.EpochRecord)
        for name, value in vars(fields).items():
            if name.startswith("RECORD_") and isinstance(value, str):
                assert value in record_keys, name


class TestPublicView:
    def _record(self) -> dict:
        return {
            fields.RECORD_EPOCH: 7,
            fields.RECORD_TRIGGER_STATUS: "YELLOW",
            fields.RECORD_SUMMARY: {fields.SUMMARY_INFECTED: 3},
            fields.RECORD_SPACES: {"mess": {fields.ZONE_PATHOGEN_MASS: 1.5}},
            fields.RECORD_AGENTS: [
                {
                    fields.AGENT_ID: 1,
                    fields.AGENT_INFECTION_STATE: INFECTION_INFECTED,
                    fields.AGENT_SYMPTOM_PRESENTATION: PRESENTATION_SYMPTOMATIC,
                    fields.AGENT_COMPLIANCE_STATUS: COMPLIANCE_ISOLATED,
                },
            ],
            fields.RECORD_REACTIVE_PROTOCOLS: {
                fields.PROTOCOLS_STOPLIGHTS: {"sanitation": "amber"},
            },
            fields.RECORD_COST_ACCOUNTING: {fields.COST_TOTAL_FINANCIAL_USD: 12.0},
        }

    def test_public_view_maps_record_fields(self) -> None:
        view = fields.public_view(self._record())
        assert view[fields.PUBLIC_EPOCH] == 7
        assert view[fields.PUBLIC_TRIGGER_STATUS] == "YELLOW"
        assert view[fields.PUBLIC_SUMMARY][fields.SUMMARY_INFECTED] == 3
        assert view[fields.PUBLIC_STOPLIGHTS] == {"sanitation": "amber"}
        assert view[fields.PUBLIC_COST_ACCOUNTING][fields.COST_TOTAL_FINANCIAL_USD] == pytest.approx(12.0)
        assert view[fields.PUBLIC_OBSERVATION_ENGINE] == {}
        assert len(view[fields.PUBLIC_AGENTS]) == 1

    def test_public_view_epoch_override(self) -> None:
        assert fields.public_view(self._record(), 8)[fields.PUBLIC_EPOCH] == 8

    def test_trigger_status_falls_back_to_reactive_protocols(self) -> None:
        rec = self._record()
        del rec[fields.RECORD_TRIGGER_STATUS]
        rec[fields.RECORD_REACTIVE_PROTOCOLS][fields.PROTOCOLS_TRIGGER_STATUS] = "RED"
        assert fields.record_trigger_status(rec) == "RED"

    def test_zone_pathogen_mass_accepts_scalar_or_map(self) -> None:
        assert fields.zone_pathogen_mass({fields.ZONE_PATHOGEN_MASS: 2.0}) == pytest.approx(2.0)
        assert fields.zone_pathogen_mass(
            {fields.ZONE_PATHOGEN_MASS: {"noro": 1.0, "flu": 0.5}},
        ) == pytest.approx(1.5)
        assert fields.zone_pathogen_mass({}) == pytest.approx(0.0)

    def test_public_agent_resolves_through_axes(self) -> None:
        agent = fields.public_view(self._record())[fields.PUBLIC_AGENTS][0]
        assert resolve_agent_axes(agent) == (
            INFECTION_INFECTED,
            PRESENTATION_SYMPTOMATIC,
            COMPLIANCE_ISOLATED,
        )
