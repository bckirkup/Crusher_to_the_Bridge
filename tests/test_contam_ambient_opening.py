"""CONTAM-AMBIENT-OPENING-SCHEMA-01 contract tests for ``ambient_openings``."""

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

from engines.contamx_runner import find_contamx  # noqa: E402
from engines.contamx_transport import ENVELOPE_LEAK_KIND  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    AMBIENT_OPENING_KIND,
    AMBIENT_OPENING_TYPES,
    AMBIENT_ZONE_ID,
    ContamTransportEngine,
    parse_ambient_exchange_axis,
)
from tools.contam_hobbyist import orifice_params_for_area  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.contamw34_prj import (  # noqa: E402
    AMBIENT_OPENING_MODELS,
    DEFAULT_AMBIENT_OPENING_MODEL,
    path_map_from_prj,
)
from tools.diag import ambient_opening_d8_witness as d8  # noqa: E402

_AIR_FLOW_SCHEMA = REPO_ROOT / "schemas" / "air_flow_paths.schema.json"
_PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"
_CONTAMX = find_contamx({})


def _spatial() -> dict[str, Any]:
    return {
        "platform": "toy",
        "zones": [
            {"id": "A", "volume_m3": 100.0},
            {"id": "B", "volume_m3": 100.0},
        ],
    }


def _opening(**overrides: Any) -> dict[str, Any]:
    record = {
        "zone": "A",
        "type": "open_deck",
        "area_m2": 40.0,
        "exchange_m3h": 100.0,
        "azimuth_deg": None,
        "schedule": "always_open",
    }
    record.update(overrides)
    return record


def _airflow(*records: dict[str, Any], **extra: Any) -> dict[str, Any]:
    airflow: dict[str, Any] = {"hvac_zones": [], "cross_zone_links": [], "adjacency": []}
    if records:
        airflow["ambient_openings"] = list(records)
    airflow.update(extra)
    return airflow


def _native(airflow: dict[str, Any], **kwargs: Any) -> ContamTransportEngine:
    return ContamTransportEngine(
        _spatial(), airflow, filter_efficiency=0.5, natural_decay_rate=0.0, **kwargs,
    )


def _path_rows(engine: ContamTransportEngine) -> list[tuple[Any, ...]]:
    return [
        (p.path_id, p.from_zone, p.to_zone, p.flow_rate_m3h, p.path_type,
         p.is_hvac_ducted, p.filtered, p.sink, p.exchange)
        for p in engine.airflow_paths
    ]


_MAKEUP_RECORDS = {
    "classic_cruise_1900": 1, "diamond_princess": 1, "expedition_cruise_450": 1,
    "greg_mortimer": 1, "mega_cruise_5000": 10, "spirit_cruise_3000": 1,
    "enterprise_constitution_tos": 1, "enterprise_galaxy_tng": 1,
}


class TestSchema:
    @staticmethod
    def _errors(record: Any) -> list[Any]:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        document = {"platform": "toy", "ambient_openings": [record]}
        return list(jsonschema.Draft202012Validator(schema).iter_errors(document))

    @pytest.mark.parametrize("opening_type", AMBIENT_OPENING_TYPES)
    def test_every_catalog_type_validates(self, opening_type: str) -> None:
        assert self._errors(_opening(type=opening_type)) == []

    def test_schema_enum_is_the_code_catalog(self) -> None:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        enum = schema["$defs"]["AmbientOpening"]["properties"]["type"]["enum"]
        assert tuple(enum) == AMBIENT_OPENING_TYPES

    def test_nullable_and_absent_optionals_validate(self) -> None:
        assert self._errors({"zone": "A", "type": "balcony_door", "area_m2": 2.0}) == []
        assert self._errors(_opening(exchange_m3h=None, azimuth_deg=None)) == []

    @pytest.mark.parametrize("field", ["zone", "type", "area_m2"])
    def test_required_fields(self, field: str) -> None:
        record = _opening()
        del record[field]
        assert self._errors(record)

    @pytest.mark.parametrize("overrides", [
        {"zone": AMBIENT_ZONE_ID},
        {"zone": ""},
        {"type": "porthole"},
        {"area_m2": 0.0},
        {"area_m2": -1.0},
        {"area_m2": None},
        {"exchange_m3h": -1.0},
        {"azimuth_deg": 361.0},
        {"azimuth_deg": -1.0},
        {"schedule": None},
        {"flow_rate_m3h": 10.0},
    ])
    def test_invalid_records_are_rejected(self, overrides: dict[str, Any]) -> None:
        assert self._errors(_opening(**overrides))

    def test_only_makeup_louvres_are_declared(self) -> None:
        # CONTAM-AMBIENT-MAKEUP-CRUISE-01 and
        # CONTAM-AMBIENT-MAKEUP-FICTION-01 authored the records: make-up
        # louvres on the six cruise hulls and two fiction hulls, native rate 0
        # (D5). Any other declaration is a later stage and must move this
        # guard deliberately.
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        paths = sorted(_PLATFORM_ROOT.glob("*/air_flow_paths.json"))
        assert paths
        declared: dict[str, int] = {}
        for path in paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            assert not list(validator.iter_errors(document)), path
            records = document.get("ambient_openings", [])
            if records:
                declared[path.parent.name] = len(records)
            for record in records:
                assert record["type"] == "makeup_louvre", path
                assert record["exchange_m3h"] == pytest.approx(0.0), path
        assert declared == _MAKEUP_RECORDS


class TestNativeBuilder:
    def test_path_shape(self) -> None:
        engine = _native(_airflow(_opening()))
        assert _path_rows(engine) == [(
            "ambopen_0_A_open_deck", "A", AMBIENT_ZONE_ID, 100.0,
            "ambient_exchange_open_deck", False, False, True, True,
        )]

    @pytest.mark.parametrize("opening_type", AMBIENT_OPENING_TYPES)
    def test_path_type_names_the_opening_type(self, opening_type: str) -> None:
        (path,) = _native(_airflow(_opening(type=opening_type))).airflow_paths
        assert path.path_type == f"ambient_exchange_{opening_type}"
        assert path.sink is True
        assert path.exchange is True

    def test_exchange_is_the_sink_operator_at_rate_q(self) -> None:
        """§2.3: exchange with clean ambient == the existing sink path at Q."""
        sink_link = {
            "from": "A", "to": AMBIENT_ZONE_ID, "flow_rate_m3h": 100.0,
            "is_hvac_ducted": True, "direction": "oneway",
            "mechanism": "prescribed_flow", "filtered": False,
        }
        exchange = _native(_airflow(_opening()))
        sink = _native(_airflow(cross_zone_links=[sink_link]))
        assert (
            exchange._build_decay_free_operator().tolist()
            == sink._build_decay_free_operator().tolist()
        )
        result = exchange.transport_step({"A": 1000.0, "B": 7.0}, natural_decay_rate=0.0)
        assert result["A"] == pytest.approx(1000.0 * math.exp(-1.0), rel=1e-12)
        assert result["B"] == pytest.approx(7.0)
        assert AMBIENT_ZONE_ID not in result
        # The sink it is compared against is extraction, not exchange.
        assert [p.exchange for p in sink.airflow_paths] == [False]

    def test_null_rate_reads_the_declared_type_axis(self) -> None:
        engine = _native(
            _airflow(_opening(exchange_m3h=None)),
            ambient_exchange_m3h={"open_deck": 250.0},
        )
        assert engine.airflow_paths[0].flow_rate_m3h == pytest.approx(250.0)

    def test_record_rate_overrides_the_axis(self) -> None:
        engine = _native(
            _airflow(_opening(exchange_m3h=40.0)),
            ambient_exchange_m3h={"open_deck": 250.0},
        )
        assert engine.airflow_paths[0].flow_rate_m3h == pytest.approx(40.0)

    def test_no_rate_from_either_source_raises(self) -> None:
        with pytest.raises(ValueError, match="no exchange_m3h"):
            _native(_airflow(_opening(exchange_m3h=None)))

    @pytest.mark.parametrize("overrides", [
        {"zone": "Missing"},
        {"zone": AMBIENT_ZONE_ID},
        {"type": "porthole"},
        {"area_m2": 0.0},
        {"exchange_m3h": -5.0},
        {"exchange_m3h": math.nan},
        {"azimuth_deg": 400.0},
    ])
    def test_invalid_records_fail_loud(self, overrides: dict[str, Any]) -> None:
        with pytest.raises(ValueError, match="ambient_openings"):
            _native(_airflow(_opening(**overrides)))

    @pytest.mark.parametrize("airflow", [
        _airflow(),
        _airflow(ambient_openings=[]),
    ])
    def test_absent_or_empty_adds_nothing(self, airflow: dict[str, Any]) -> None:
        adjacency = [{"from": "A", "to": "B", "type": "doorway"}]
        with_key = _native({**airflow, "adjacency": adjacency})
        baseline = _native({
            "hvac_zones": [], "cross_zone_links": [], "adjacency": adjacency,
        })
        assert _path_rows(with_key) == _path_rows(baseline)
        assert not any(p.exchange for p in with_key.airflow_paths)

    def test_axis_parser(self) -> None:
        assert parse_ambient_exchange_axis({}) == {}
        assert parse_ambient_exchange_axis(
            {"ambient_exchange_m3h": {"open_deck": 10}}
        ) == {"open_deck": 10.0}
        for bad in ({"porthole": 1.0}, {"open_deck": -1.0}, [1.0]):
            with pytest.raises(ValueError, match="ambient_exchange_m3h"):
                parse_ambient_exchange_axis({"ambient_exchange_m3h": bad})


def _prj_section(text: str, marker: str) -> list[str]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if marker in line)
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("-999"))
    return lines[start + 1:end]


def _element_blocks(text: str) -> dict[int, tuple[list[str], str]]:
    """Flow element nr -> (header tokens, parameter line)."""
    body = _prj_section(text, "! flow elements")
    blocks = {}
    for i, line in enumerate(body):
        toks = line.split()
        if len(toks) >= 4 and toks[0].isdigit() and toks[3].startswith("AmbOp_"):
            blocks[int(toks[0])] = (toks, body[i + 2].strip())
    return blocks


class TestExporter:
    @pytest.mark.parametrize("hobbyist", [False, True])
    def test_default_emits_paired_orifices_to_ambient(self, hobbyist: bool) -> None:
        assert DEFAULT_AMBIENT_OPENING_MODEL == "paired_orifices"
        text, path_map = export_prj_with_path_map(
            _spatial(), _airflow(_opening()), hobbyist=hobbyist,
        )
        entries = [e for e in path_map if e["kind"] == AMBIENT_OPENING_KIND]
        assert len(entries) == 2
        for entry in entries:
            assert entry["from_zone"] == "A"
            assert entry["to_zone"] == AMBIENT_ZONE_ID
            assert entry["is_hvac_ducted"] is False
            assert entry["crusher_transfer"] is False
            assert "sink" not in entry

        # Both legs share one half-area orifice sized by orifice_params_for_area.
        blocks = _element_blocks(text)
        assert len(blocks) == 1
        ((toks, params),) = blocks.values()
        assert toks[2] == "plr_orfc"
        assert params == orifice_params_for_area(20.0)

        # Path rows: zone -> ambient (-1) at two different relative heights.
        opening_nrs = {e["path_nr"] for e in entries}
        rows = [
            line.split() for line in _prj_section(text, "! flow paths")
            if line.split() and line.split()[0].isdigit()
            and int(line.split()[0]) in opening_nrs
        ]
        assert len(rows) == 2
        assert {row[3] for row in rows} == {"-1"}
        assert len({row[2] for row in rows}) == 1
        assert len({line_rel_ht(row) for row in rows}) == 2

    @pytest.mark.parametrize("hobbyist", [False, True])
    def test_path_map_from_prj_keeps_the_kind(self, hobbyist: bool) -> None:
        text, path_map = export_prj_with_path_map(
            _spatial(), _airflow(_opening()), hobbyist=hobbyist,
        )
        rebuilt = path_map_from_prj(text, ["A", "B"])
        expected = {
            e["path_nr"] for e in path_map if e["kind"] == AMBIENT_OPENING_KIND
        }
        assert {
            e["path_nr"] for e in rebuilt if e["kind"] == AMBIENT_OPENING_KIND
        } == expected
        # The envelope pressure reference stays its own kind.
        assert {
            e["path_nr"] for e in rebuilt if e["kind"] == ENVELOPE_LEAK_KIND
        } == {e["path_nr"] for e in path_map if e["kind"] == ENVELOPE_LEAK_KIND}

    def test_openings_do_not_disturb_other_paths(self) -> None:
        adjacency = [{"from": "A", "to": "B", "type": "doorway"}]
        base_text, base_map = export_prj_with_path_map(
            _spatial(), _airflow(adjacency=adjacency), hobbyist=True,
        )
        _, with_map = export_prj_with_path_map(
            _spatial(), _airflow(_opening(), adjacency=adjacency), hobbyist=True,
        )
        strip = [
            {k: v for k, v in e.items() if k != "path_nr"}
            for e in with_map if e["kind"] != AMBIENT_OPENING_KIND
        ]
        assert strip == [{k: v for k, v in e.items() if k != "path_nr"} for e in base_map]
        assert "AmbOp_" not in base_text

    def test_authored_azimuth_and_wind_profile(self) -> None:
        text, path_map = export_prj_with_path_map(
            _spatial(), _airflow(_opening(azimuth_deg=135.0)), hobbyist=True,
        )
        nrs = {e["path_nr"] for e in path_map if e["kind"] == AMBIENT_OPENING_KIND}
        rows = [
            line.split() for line in _prj_section(text, "! flow paths")
            if line.split() and line.split()[0].isdigit() and int(line.split()[0]) in nrs
        ]
        for row in rows:
            assert float(row[6]) > 0  # wind pressure profile attached
            assert "135" in row

    def test_schedule_from_type_and_from_record(self) -> None:
        def sched_nrs(record: dict[str, Any]) -> set[str]:
            text, path_map = export_prj_with_path_map(
                _spatial(), _airflow(record), hobbyist=True,
            )
            nrs = {e["path_nr"] for e in path_map if e["kind"] == AMBIENT_OPENING_KIND}
            return {
                line.split()[8] for line in _prj_section(text, "! flow paths")
                if line.split() and line.split()[0].isdigit()
                and int(line.split()[0]) in nrs
            }

        always = sched_nrs(_opening())
        assert always == {"0"}
        typed = _opening(type="weather_door")
        del typed["schedule"]
        door = sched_nrs(typed)
        assert door != always
        assert len(door) == 1
        assert sched_nrs(_opening(schedule="DoorTrafficW")) == door
        assert sched_nrs(_opening(type="weather_door")) == always
        with pytest.raises(ValueError, match="unknown schedule"):
            sched_nrs(_opening(schedule="NoSuchW"))

    def test_unknown_zone_and_model_fail_loud(self) -> None:
        with pytest.raises(ValueError, match="ambient_openings zone"):
            export_prj_with_path_map(_spatial(), _airflow(_opening(zone="Missing")))
        with pytest.raises(ValueError, match="ambient_opening_model"):
            export_prj_with_path_map(
                _spatial(), _airflow(_opening()), hobbyist=True,
                overrides={"ambient_opening_model": "louvre"},
            )

    @pytest.mark.parametrize(("model", "symbol"), [
        ("single_orifice", "plr_orfc"),
        ("two_way_door", "dor_door"),
    ])
    def test_witness_models_emit_one_full_area_path(self, model: str, symbol: str) -> None:
        text, path_map = export_prj_with_path_map(
            _spatial(), _airflow(_opening()), hobbyist=True,
            overrides={"ambient_opening_model": model},
        )
        assert len([e for e in path_map if e["kind"] == AMBIENT_OPENING_KIND]) == 1
        ((toks, params),) = _element_blocks(text).values()
        assert toks[2] == symbol
        if symbol == "plr_orfc":
            assert params == orifice_params_for_area(40.0)

    def test_ambient_source_cross_zone_link_is_still_rejected(self) -> None:
        link = {
            "from": AMBIENT_ZONE_ID, "to": "A", "flow_rate_m3h": 10.0,
            "direction": "oneway", "mechanism": "prescribed_flow", "filtered": False,
        }
        with pytest.raises(ValueError, match="ambient"):
            export_prj_with_path_map(
                _spatial(), _airflow(_opening(), cross_zone_links=[link]),
            )


def line_rel_ht(row: list[str]) -> str:
    """``relHt`` token of a flow-path row (the field after ``pw``)."""
    return row[13]


class TestD8Witness:
    def test_summarize_reads_flow0_only(self) -> None:
        rows = [
            {"path_nr": 1, "flow0_m3h": 30.0, "flow1_m3h": 0.0},
            {"path_nr": 2, "flow0_m3h": -28.0, "flow1_m3h": 0.0},
        ]
        assert d8.summarize(rows) == {
            "n_paths": 2,
            "flow0_outward_m3h": 30.0,
            "flow0_inward_m3h": 28.0,
            "flow0_net_outward_m3h": 2.0,
            "flow1_unread_m3h": 0.0,
        }

    def test_scratch_declaration_is_in_memory_only(self) -> None:
        airflow = {"adjacency": []}
        scratch = d8.scratch_airflow(airflow, "Pool_Deck", 40.0)
        assert "ambient_openings" not in airflow
        assert scratch["ambient_openings"][0]["zone"] == "Pool_Deck"

    @pytest.mark.skipif(_CONTAMX is None, reason="ContamX binary not available")
    def test_only_paired_orifices_show_both_directions_in_flow0(self) -> None:
        """D8: the evidence behind the ``paired_orifices`` default."""
        report = d8.run_witness(
            d8.DEFAULT_HULL, d8.DEFAULT_ZONE, d8.DEFAULT_AREA_M2, (5.0,), _CONTAMX,
        )
        cases = {case["model"]: case for case in report["cases"]}
        assert set(cases) == set(AMBIENT_OPENING_MODELS)

        paired = cases["paired_orifices"]
        assert paired["flow0_outward_m3h"] > 1000.0
        assert paired["flow0_inward_m3h"] == pytest.approx(
            paired["flow0_outward_m3h"], rel=0.01,
        )
        assert paired["flow1_unread_m3h"] == pytest.approx(0.0, abs=1e-6)

        # One orifice solves only the net flow: no exchange at all.
        single = cases["single_orifice"]
        assert single["flow0_outward_m3h"] + single["flow0_inward_m3h"] < 10.0

        # The door element solves the exchange but hides half of it in Flow1.
        door = cases["two_way_door"]
        assert door["flow0_outward_m3h"] > 1000.0
        assert door["flow0_inward_m3h"] == pytest.approx(0.0, abs=1e-6)
        assert door["flow1_unread_m3h"] == pytest.approx(
            door["flow0_outward_m3h"], rel=0.01,
        )
