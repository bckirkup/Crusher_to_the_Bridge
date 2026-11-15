"""EXHAUST-SINK contract tests for the ambient sink endpoint."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    AMBIENT_ZONE_ID,
    ContamTransportEngine,
)
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.contamw34_prj import path_map_from_prj  # noqa: E402
from tools.sanity_checker import (  # noqa: E402
    AirFlowPaths,
    CrossZoneLink,
    Report,
    _check_ambient_sink_links,
    _check_cross_zone_link_endpoints,
)

_AIR_FLOW_SCHEMA = REPO_ROOT / "schemas" / "air_flow_paths.schema.json"
_PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"


def _spatial() -> dict[str, Any]:
    return {
        "platform": "toy",
        "zones": [
            {"id": "A", "volume_m3": 100.0},
            {"id": "B", "volume_m3": 100.0},
        ],
    }


def _sink_link(**overrides: Any) -> dict[str, Any]:
    link = {
        "from": "A",
        "to": AMBIENT_ZONE_ID,
        "flow_rate_m3h": 100.0,
        "is_hvac_ducted": True,
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "path": "medical_exhaust",
    }
    link.update(overrides)
    return link


def _airflow(link: dict[str, Any]) -> dict[str, Any]:
    return {
        "hvac_zones": [],
        "cross_zone_links": [link],
        "adjacency": [],
    }


def _native_engine(link: dict[str, Any]) -> ContamTransportEngine:
    return ContamTransportEngine(
        _spatial(),
        _airflow(link),
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
    )


def _sink_paths(engine: ContamTransportEngine) -> list[Any]:
    return [
        path for path in engine.airflow_paths
        if path.sink and path.to_zone == AMBIENT_ZONE_ID
    ]


class TestAmbientSinkSchema:
    @staticmethod
    def _document(link: dict[str, Any]) -> dict[str, Any]:
        return {"platform": "toy", "cross_zone_links": [link]}

    def test_valid_sink_link_validates(self) -> None:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(self._document(_sink_link()), schema)

    @pytest.mark.parametrize("field", ["direction", "mechanism", "filtered"])
    def test_sink_requires_explicit_semantics(self, field: str) -> None:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        link = _sink_link()
        link.pop(field)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(self._document(link), schema)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("direction", "bidirectional"),
            ("mechanism", "pressure_opening"),
            ("filtered", True),
        ],
    )
    def test_sink_rejects_wrong_semantics(
        self, field: str, value: Any,
    ) -> None:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                self._document(_sink_link(**{field: value})), schema,
            )

    def test_ambient_is_not_a_valid_source(self) -> None:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        link = _sink_link(**{"from": AMBIENT_ZONE_ID, "to": "B"})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(self._document(link), schema)


class TestAmbientSinkSanity:
    @staticmethod
    def _airflow_model(link: CrossZoneLink) -> AirFlowPaths:
        return AirFlowPaths(platform="toy", cross_zone_links=[link])

    @staticmethod
    def _model_link(**overrides: Any) -> CrossZoneLink:
        values = _sink_link()
        values.update(overrides)
        return CrossZoneLink(**values)

    def test_valid_sink_passes_sink_and_endpoint_checks(self) -> None:
        airflow = self._airflow_model(self._model_link())
        report = Report()
        _check_ambient_sink_links(airflow, report)
        _check_cross_zone_link_endpoints(airflow, {"A", "B"}, report)
        assert report.passed

    @pytest.mark.parametrize(
        "overrides",
        [
            {"direction": "bidirectional"},
            {"mechanism": "pressure_opening"},
            {"filtered": True},
        ],
    )
    def test_invalid_sink_semantics_fail_loud(self, overrides: dict[str, Any]) -> None:
        airflow = self._airflow_model(self._model_link(**overrides))
        report = Report()
        _check_ambient_sink_links(airflow, report)
        assert not report.passed
        assert any(f.rule == "AIRFLOW_SINK" for f in report.errors)

    def test_alias_filtered_true_is_not_a_sink(self) -> None:
        airflow = self._airflow_model(CrossZoneLink(
            **{
                "from": "A",
                "to": "ambient",
                "flow_rate_m3h": 100.0,
                "is_hvac_ducted": True,
                "direction": "oneway",
                "mechanism": "prescribed_flow",
            },
        ))
        report = Report()
        _check_ambient_sink_links(airflow, report)
        assert not report.passed
        assert any("filtered" in f.message for f in report.errors)

    def test_sink_requires_explicit_fields_not_ducted_alias(self) -> None:
        values = _sink_link()
        values.pop("direction")
        values.pop("mechanism")
        airflow = self._airflow_model(CrossZoneLink(**values))
        report = Report()
        _check_ambient_sink_links(airflow, report)
        assert not report.passed
        assert any(f.rule == "AIRFLOW_SINK" for f in report.errors)

    def test_ambient_from_is_rejected_by_endpoint_check(self) -> None:
        airflow = self._airflow_model(self._model_link(**{
            "from": "ambient", "to": "B",
        }))
        report = Report()
        _check_cross_zone_link_endpoints(airflow, {"B"}, report)
        assert not report.passed
        assert any(f.rule == "GRAPH_REF" for f in report.errors)


class TestNativeSinkTransport:
    def test_sink_paths_expand_per_source_room(self) -> None:
        spatial = _spatial()
        airflow = {
            "hvac_zones": [{"id": "G", "rooms": ["A", "B"]}],
            "cross_zone_links": [_sink_link(**{"from": "G", "flow_rate_m3h": 200.0})],
            "adjacency": [],
        }
        engine = ContamTransportEngine(
            spatial, airflow, filter_efficiency=0.5, natural_decay_rate=0.0,
        )
        paths = _sink_paths(engine)
        assert len(paths) == 2
        assert {path.from_zone for path in paths} == {"A", "B"}
        assert all(path.flow_rate_m3h == pytest.approx(100.0) for path in paths)
        assert all(path.sink for path in paths)
        assert all(path.filtered is False for path in paths)

    def test_sink_removes_mass_without_arrival(self) -> None:
        engine = _native_engine(_sink_link())
        result = engine.transport_step(
            {"A": 1000.0, "B": 0.0}, natural_decay_rate=0.0,
        )
        assert result["A"] == pytest.approx(1000.0 * math.exp(-1.0), rel=1e-12)
        assert result["B"] == pytest.approx(0.0)
        assert AMBIENT_ZONE_ID not in result
        assert sum(result.values()) == pytest.approx(
            result["A"] + result["B"], rel=1e-12,
        )

    @pytest.mark.parametrize("flow", [0.0, 50.0, 100.0, 200.0])
    def test_sink_response_is_graded(self, flow: float) -> None:
        engine = _native_engine(_sink_link(flow_rate_m3h=flow))
        result = engine.transport_step(
            {"A": 1000.0, "B": 0.0}, natural_decay_rate=0.0,
        )
        assert result["A"] == pytest.approx(
            1000.0 * math.exp(-flow / 100.0), rel=1e-12,
        )
        assert result["B"] == pytest.approx(0.0)

    def test_sink_lowers_source_column_only(self) -> None:
        engine = _native_engine(_sink_link())
        operator = engine._build_decay_free_operator()
        col_a = engine._real_zone_ids.index("A")
        col_b = engine._real_zone_ids.index("B")
        row_b = engine._real_zone_ids.index("B")
        assert float(operator[:, col_a].sum()) == pytest.approx(-1.0, abs=1e-12)
        assert float(operator[:, col_b].sum()) == pytest.approx(0.0, abs=1e-12)
        assert float(operator[row_b, col_a]) == pytest.approx(0.0, abs=1e-12)

    def test_native_fail_loud_unknown_endpoint(self) -> None:
        airflow = _airflow(_sink_link(**{
            "to": "Missing_Zone",
            "direction": "oneway",
            "mechanism": "prescribed_flow",
            "filtered": False,
        }))
        with pytest.raises(ValueError, match="cross_zone_links endpoint 'Missing_Zone'"):
            ContamTransportEngine(
                _spatial(), airflow,
                filter_efficiency=0.5, natural_decay_rate=0.0,
            )


class TestExporterAndLaneSink:
    @pytest.mark.parametrize("hobbyist", [False, True])
    def test_export_writes_fan_to_ambient_and_path_map_sink(
        self, hobbyist: bool,
    ) -> None:
        text, path_map = export_prj_with_path_map(
            _spatial(), _airflow(_sink_link()), hobbyist=hobbyist,
        )
        entries = [
            entry for entry in path_map if entry.get("kind") == "medical_exhaust"
        ]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["from_zone"] == "A"
        assert entry["to_zone"] == AMBIENT_ZONE_ID
        assert entry["sink"] is True
        assert entry["filtered"] is False
        assert entry["is_hvac_ducted"] is True
        assert entry["crusher_transfer"] is False

        round_tripped = path_map_from_prj(text, ["A", "B"])
        sinks = [item for item in round_tripped if item.get("sink") is True]
        assert len(sinks) == 1
        assert sinks[0]["kind"] == "exhaust_sink"
        assert sinks[0]["from_zone"] == "A"
        assert sinks[0]["to_zone"] == AMBIENT_ZONE_ID
        assert sinks[0]["is_hvac_ducted"] is True
        assert sinks[0]["crusher_transfer"] is False

    def test_lane_sink_path_is_outflow_only_and_matches_native(self) -> None:
        spatial = _spatial()
        native = _native_engine(_sink_link())
        entries = [{
            "path_nr": 1,
            "from_zone": "A",
            "to_zone": AMBIENT_ZONE_ID,
            "is_hvac_ducted": True,
            "kind": "exhaust_sink",
            "crusher_transfer": False,
            "ahs_nr": 0,
            "filtered": False,
            "sink": True,
        }]
        lane = ContamXTransportEngine.from_flow_field(
            spatial, entries, {1: 100.0},
            filter_efficiency=0.5, natural_decay_rate=0.0,
        )
        lane_paths = [path for path in lane.airflow_paths if path.sink]
        native_paths = _sink_paths(native)
        assert len(lane_paths) == 1
        assert len(native_paths) == 1
        assert {
            (path.from_zone, path.to_zone, path.flow_rate_m3h, path.sink)
            for path in lane_paths
        } == {
            (path.from_zone, path.to_zone, path.flow_rate_m3h, path.sink)
            for path in native_paths
        }

        initial = {"A": 1000.0, "B": 0.0}
        native_result = native.transport_step(initial, natural_decay_rate=0.0)
        lane_result = lane.transport_step(initial, natural_decay_rate=0.0)
        assert lane_result["A"] == pytest.approx(native_result["A"], rel=1e-12)
        assert lane_result["B"] == pytest.approx(native_result["B"], rel=1e-12)
        assert AMBIENT_ZONE_ID not in lane_result

    @pytest.mark.parametrize("flow", [-5.0, 0.0])
    def test_lane_ignores_nonpositive_sink_flow(self, flow: float) -> None:
        entries = [{
            "path_nr": 1,
            "from_zone": "A",
            "to_zone": AMBIENT_ZONE_ID,
            "is_hvac_ducted": True,
            "kind": "exhaust_sink",
            "crusher_transfer": False,
            "ahs_nr": 0,
            "sink": True,
        }]
        lane = ContamXTransportEngine.from_flow_field(
            _spatial(), entries, {1: flow},
            filter_efficiency=0.5, natural_decay_rate=0.0,
        )
        assert not [path for path in lane.airflow_paths if path.sink]

    @pytest.mark.parametrize(
        "link",
        [
            _sink_link(**{"direction": "bidirectional"}),
            _sink_link(mechanism="pressure_opening"),
            _sink_link(**{"from": "ambient", "to": "B"}),
        ],
    )
    def test_exporter_rejects_invalid_sink_links(self, link: dict[str, Any]) -> None:
        with pytest.raises(ValueError, match="ambient"):
            export_prj_with_path_map(_spatial(), _airflow(link))

    def test_exporter_rejects_implicit_sink_semantics(self) -> None:
        link = _sink_link()
        link.pop("direction")
        link.pop("mechanism")
        with pytest.raises(ValueError, match="ambient"):
            export_prj_with_path_map(_spatial(), _airflow(link))


class TestCommittedPlatformAmbientSinks:
    _EXPECTED_SINKS = {
        ("legend_class_nsc", "medical_exhaust", "HVAC_Medical", 100.0),
        ("san_antonio_class_lpd", "medical_exhaust", "HVAC_Medical", 200.0),
        (
            "san_antonio_class_lpd",
            "galley_exhaust_to_mess",
            "HVAC_Galley",
            400.0,
        ),
        ("classic_cruise_1900", "Galley_Hood_Exhaust", "MainGalley", 12000.0),
        ("diamond_princess", "Galley_Hood_Exhaust", "MainGalley", 18000.0),
        ("expedition_cruise_450", "Galley_Hood_Exhaust", "MainGalley", 8000.0),
        ("greg_mortimer", "Galley_Hood_Exhaust", "MainGalley", 5000.0),
        ("spirit_cruise_3000", "Galley_Hood_Exhaust", "MainGalley", 15000.0),
        (
            "enterprise_constitution_tos",
            "Galley_Hood_Exhaust",
            "Galley",
            5000.0,
        ),
        ("enterprise_galaxy_tng", "Galley_Hood_Exhaust", "Galley", 8000.0),
        (
            "mega_cruise_5000",
            "Dining_to_Galley_Transfer",
            "AHU_Network_Aft_Dining_Rec",
            15000.0,
        ),
        (
            "messy_cruise_500",
            "Dining_to_Galley_Transfer",
            "AHU_Network_Aft_Dining_Rec",
            15000.0,
        ),
    }

    def test_committed_platforms_declare_only_expected_ambient_sinks(self) -> None:
        observed: set[tuple[str, str, str, float]] = set()
        for path in sorted(_PLATFORM_ROOT.glob("*/air_flow_paths.json")):
            platform = path.parent.name
            airflow = json.loads(path.read_text(encoding="utf-8"))
            for link in airflow.get("cross_zone_links", []):
                assert link.get("from") != AMBIENT_ZONE_ID, (
                    f"{platform} uses ambient as a source"
                )
                if link.get("to") != AMBIENT_ZONE_ID:
                    continue
                observed.add((
                    platform,
                    str(link.get("path")),
                    str(link.get("from")),
                    float(link.get("flow_rate_m3h", 0.0)),
                ))
                assert link.get("direction") == "oneway"
                assert link.get("mechanism") == "prescribed_flow"
                assert link.get("filtered") is False
        assert observed == self._EXPECTED_SINKS
