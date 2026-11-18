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
    "greg_mortimer": 2, "mega_cruise_5000": 10, "spirit_cruise_3000": 1,
    "enterprise_constitution_tos": 1, "enterprise_galaxy_tng": 1,
    "olympia_c6": 1,
}
# CONTAM-AMBIENT-WEATHER-CRUISE-01, CONTAM-EXPOSURE-TAGGING-01,
# CONTAM-AMBIENT-WEATHER-DESTROYER-01, CONTAM-AMBIENT-WEATHER-CARRIER-01,
# CONTAM-AMBIENT-WEATHER-BATTLESHIP-01, CONTAM-AMBIENT-WEATHER-CRUISER-01,
# CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01, CONTAM-AMBIENT-WEATHER-AUXILIARY-01
# and CONTAM-AMBIENT-WEATHER-MISC-01: one ``open_deck`` record per declared
# weather zone on the cruise, destroyer, carrier, battleship, cruiser,
# amphibious, auxiliary and misc roster hulls.
_WEATHER_ZONES = {
    "classic_cruise_1900": {"PoolDeck"},
    "diamond_princess": {
        "OceanFront", "TerracePool", "NeptunePool", "CalypsoPool",
        "HorizonTerrace", "OpenAirCinema", "SportsCourt", "CenterCourt",
    },
    "expedition_cruise_450": {"PoolDeck"},
    "greg_mortimer": {
        "ZodiacPlatforms", "ActivityPlat", "ViewPlatforms", "SunDeck", "TopDeck",
    },
    "mega_cruise_5000": {
        "Main_Pool_Deck", "Sports_Court", "Waterpark", "CentralPark", "Aqua_Theater",
    },
    "spirit_cruise_3000": {"MainPool", "AftPool", "SportsDeck"},
    "cannon_de701": {"Gun_Deck_Open", "Island_Open_Aft", "Fantail", "Focsle_Deck"},
    "cushing_dd376": {"Focsle_Open", "Fantail"},
    "davison_dd618": {
        "Super_Open", "After_Deckhouse_Top", "Midship_Deckhouse",
        "Focsle_Open", "Fantail_MS",
    },
    "fletcher_dde_dd445": {"Fantail", "Focsle_Main"},
    "hunter_killer_dd692": {
        "Signal_Bridge", "Boat_Deck_01", "Launcher_Deck_01", "Fantail",
        "Torpedo_Deck", "Fwd_Mount_Deck", "Focsle_Fwd",
    },
    "keppler_dd765": {
        "Signal_Shelter", "Helo_Platform", "Weather_Deck_01",
        "Forecastle_Top_01", "Fantail", "Gun_Deck_Aft", "Focsle_Fwd",
    },
    "nields_dd616": {
        "Super_Open", "After_Deckhouse_Top", "Midship_Deckhouse",
        "Focsle_Open", "Fantail",
    },
    "palmer_dms5": {"Boat_Deck_Uptakes"},
    "sigsbee_dd502": {"Midship_Deckhouse", "Mt2_Deck", "Fantail", "Focsle_Deck"},
    # CONTAM-AMBIENT-WEATHER-CARRIER-01: carrier flight decks with no HVAC
    # group.
    # CONTAM-GROUPED-WEATHER-CARRIER-01: grouped carrier weather zones whose
    # open_deck opening replaces the HVAC group OA leg; remaining group
    # members stay grouped and carry no opening.
    "lexington_cv2": {"Flight_Deck"},
    "saratoga_cv3": {"Flight_Deck"},
    "antietam_cvs36": {
        "Gallery_Deck", "Flight_Deck", "Forecastle_Deck",
    },
    "battler_acv6": {"Walkways_Focsle", "Flight_Deck"},
    "independence_cvl26": {
        "Gallery_Deck", "Flight_Deck", "Poop_Deck", "Forecastle_Deck",
    },
    "puncher_cve53": {"Flight_Deck"},
    "ranger_cv4": {"Flight_Deck", "Poop_Deck"},
    "saratoga_cv60": {"Flight_Deck"},
    "thetis_bay_cve90": {"Flight_Deck"},
    "wasp_cv7": {"Flight_Deck"},
    "wright_cc2": {
        "Flight_Deck_Aft", "Flight_Deck_Mid", "Flight_Deck_Fwd",
    },
    "yorktown_cv5": {"Flight_Deck"},
    # CONTAM-AMBIENT-WEATHER-BATTLESHIP-01: ungrouped battleship weather zones;
    # HVAC-grouped VENT_Weather hulls stay untouched as the known grouped-zone
    # open item.
    "new_york_bb34": {
        "Fantail_Weather", "Weather_Deck_Aft", "Catapult_Mid", "Focsle_Deck",
        "Super_Deck_Open", "AA_Control_Top",
    },
    "south_dakota_bb49": {"Landing_Platform", "Boat_Deck", "Forecastle", "Fantail"},
    "texas_bb35": {
        "Super_Deck_Open", "Fantail_Weather", "Weather_Deck_Aft", "Catapult_Mid",
        "Focsle_Deck",
    },
    "west_virginia_bb48": {
        "Signal_Bridge_Open", "Landing_Platform", "Boat_Deck", "Forecastle",
        "Fantail",
    },
    # CONTAM-AMBIENT-WEATHER-CRUISER-01: the four zero-outdoor-exchange
    # AHU_Weather rooms on the only cruiser roster hull in that state.
    "alexander_henry_cgs119": {
        "Wheelhouse_Top", "Bridge_Wings", "Boat_Stowage_Open",
        "Forecastle_Working",
    },
    # CONTAM-GROUPED-WEATHER-CRUISER-01: grouped VENT_Weather weather zones on
    # the three OA>0 cruiser roster hulls; each opening replaces the group OA
    # leg for its zone.
    "astoria_ca34": {
        "Fantail", "Catapult_Deck", "Boat_Deck", "Focsle_Deck", "Upper_Deck_Aft",
    },
    "chicago_cg11": {
        "Fantail_Weather", "Helo_Deck", "Helo_Deck_02_Aft", "Forecastle_Deck",
        "Bow_Weather", "Terrier_Deck_02", "Launcher_Deck_01", "Open_03",
    },
    "miami_cl89": {"Catapult_Deck", "Bow_Weather"},
    # CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01: ungrouped amphibious weather zones;
    # HVAC-grouped amphibious weather zones stay untouched as the known
    # grouped-zone open item.
    "lsm_354": {
        "Forecastle_Weather", "Bridge_Wings", "Weather_Aft_Super",
        "Weather_Fwd_Super",
    },
    "middlesex_lst983": {
        "Gun_Platform_Aft_Bridge", "Boat_Deck", "Gun_Platforms_Fwd_Bridge",
        "Fantail_Main", "Gun_Platform_Aft_Main", "Weather_Deck_Amids",
        "Forecastle_Bow",
    },
    "ruchamkin_apd89": {
        "Boat_Deck_Open", "Island_Open_Aft", "Fantail", "Focsle_Deck",
    },
    # CONTAM-AMBIENT-WEATHER-AUXILIARY-01: ungrouped auxiliary weather zones;
    # HVAC-grouped OA>0 auxiliary weather zones stay untouched as the known
    # grouped-zone open item. alexander_henry_cgs119 is owned by CRUISER-01.
    "aeolus_arc3": {"Bow_Sheave_Area", "Cable_Working_Deck", "Top_Of_House"},
    "apl_24": {"Fantail_Main", "Fantail_Upper", "Forecastle", "Gun_Platforms"},
    "bolster_ars38": {
        "Focsle_Deck_Open", "Focsle_Open_Aft", "Gun_Tub_Fwd", "Salvage_Deck",
    },
    "cobalt_k124": {"Foc_Deck_Open", "Quarterdeck", "Stern_Open"},
    "gordon_gunter_r338": {
        "Aft_Working_Deck", "Boat_Deck", "Mission_Deck", "Shelter_Deck",
    },
    "liberty_cargo_ec2": {
        "Aft_Deck_Open", "Boat_Deck_Open", "Bridge_Wings", "Forecastle_Deck",
        "Gun_Platform", "Top_Of_House",
    },
    "lyon_ap71": {
        "Boat_Deck_Walkway", "Boat_Stowage_Port", "Boat_Stowage_Stbd",
        "Bow_Shelter_Weather", "Bridge_Wings_Walkway", "Forecastle_Weather",
        "Hatch_3_Weather", "Hatch_4_Weather", "House_Top_Platform",
        "Quarter_Weather", "Stern_Weather_Shelter",
    },
    "passumpsic_ao106": {
        "Aft_Open_Deck", "Focsle_Deck", "Island_Deck", "Working_Deck",
    },
    "savannah_ns": {
        "Boat_Deck_Aft", "Boat_Deck_Fwd", "Bridge_Wings", "Docking_Bridge_Aft",
        "Fantail_Aft", "Forecastle_A", "Fwd_Deck_Promenade",
        "Promenade_Aft_Open", "Promenade_Walkway_Port", "Promenade_Walkway_Stbd",
        "Swimming_Pool", "Top_Of_House", "Weather_Deck_Port_A",
        "Weather_Deck_Stbd_A",
    },
    # CONTAM-AMBIENT-WEATHER-MISC-01 and CONTAM-GROUPED-WEATHER-MISC-01: the
    # ungrouped/zero-exchange weather zones plus the grouped weather zones whose
    # openings now replace the group OA leg.
    "castle_class_corvette": {"Foc_Deck_Open", "Quarterdeck", "Upper_Deck_Aft"},
    "erie_pg50": {
        "Sup_Deck_Open", "Fantail_Aft", "Gun_Deck_Aft", "Focsle_Main",
        "Focsle_Stores",
    },
    "esteem_mso438": {
        "Sweep_Deck", "Reel_Deck", "Boat_Deck_Aft", "Focsle_01",
        "Deck_House_Main",
    },
    "eagle_pe60": {
        "Open_Bridge", "Nav_Bridge", "Gun_Platform_Fwd", "After_Gun_Platform",
        "AA_Gun_Platforms", "Fantail", "Gun_Deck_Fwd",
    },
    "fort_william_j311": {"Signal_Deck", "Quarterdeck", "Foc_Deck_Open"},
    "montana_acr13": {"MD_Aft_Open", "MD_Forecastle_Open"},
    "pce_874": {"Fantail", "Focsle_Deck"},
    "pt_564": {"Torpedo_Deck", "Foredeck"},
    "raven_am55": {"Foc_Deck_Fwd", "Foc_Deck_Open", "Sweep_Deck"},
    "river_class_frigate": {"Quarterdeck", "Foc_Deck_Open", "Signal_Deck"},
    "rolla_pc483": {"Fantail", "Focsle_Deck"},
    "winnipeg_j337": {"Signal_Deck", "Quarterdeck", "Foc_Deck_Open"},
    # CONTAM-AMBIENT-WEATHER-OLYMPIA-01: final stage-4 holdout; ungrouped
    # zero-outdoor-exchange weather and boat-stowage open zones.
    "olympia_c6": {
        "SD_Stern_Open", "SD_Boats_Aft_Port", "SD_Boats_Aft_Stb",
        "SD_Boats_Mid_Port", "SD_Boats_Mid_Stb", "SD_Boats_Fwd_Port",
        "SD_Boats_Fwd_Stb", "SD_Forecastle_Open", "MD_Stern_Fantail",
        "MD_Forecastle_Open",
    },
    # CONTAM-GROUPED-WEATHER-MIDWAY-01: first grouped weather zone (G1). The
    # opening replaces the VENT_Weather OA leg for Flight_Deck, which left the
    # group; Island_Upper stays grouped and carries no opening.
    "midway_cv41": {"Flight_Deck"},
}
# CONTAM-EXPOSURE-TAGGING-01, CONTAM-AMBIENT-WEATHER-DESTROYER-01,
# CONTAM-AMBIENT-WEATHER-CARRIER-01, CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01,
# CONTAM-AMBIENT-WEATHER-AUXILIARY-01 and CONTAM-AMBIENT-WEATHER-MISC-01:
# declared enclosed zones. They carry no opening.
_ENCLOSED_ZONES = {
    "classic_cruise_1900": {"Promenade"},
    "diamond_princess": {"PromGalleria"},
    "greg_mortimer": {"BarsDeck5", "ObsDeck7", "BarsDeck8", "ObsDeck8"},
    "mega_cruise_5000": {"Royal_Promenade"},
    "spirit_cruise_3000": {"Promenade"},
    "cannon_de701": {"Signal_Deck"},
    "davison_dd618": {"Bow_Focsle"},
    "nields_dd616": {"Bow_Focsle"},
    # CONTAM-AMBIENT-WEATHER-CARRIER-01: lexical Focsle id, enclosed stores.
    "independence_cvl26": {"Focsle_Stores"},
    # CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01: enclosed amphibious deck/shelter
    # corrections; neither carries an opening.
    "ruchamkin_apd89": {"Signal_Deck"},
    "san_antonio_class_lpd": {"Vehicle_Deck"},
    # CONTAM-AMBIENT-WEATHER-AUXILIARY-01: lexical misses that are enclosed
    # stores/mechanical spaces, not weather openings.
    "gosper_apa170": {"Focsle_Stores", "Focsle_Stores_2D"},
    "jupiter_ac3": {"Passage_Deckhouse"},
    "passumpsic_ao106": {"Signal_Deck"},
    "pope_ap110": {"Sup_Deck_Mech"},
    # CONTAM-AMBIENT-WEATHER-MISC-01: lexical Focsle id, enclosed storerooms.
    "esteem_mso438": {"Focsle_Store"},
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
        {"wind_speed_m_s": -1.0},
        {"wind_speed_m_s": "fast"},
    ])
    def test_invalid_records_are_rejected(self, overrides: dict[str, Any]) -> None:
        assert self._errors(_opening(**overrides))

    @staticmethod
    def _declared(opening_type: str) -> dict[str, list[dict[str, Any]]]:
        schema = json.loads(_AIR_FLOW_SCHEMA.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        paths = sorted(_PLATFORM_ROOT.glob("*/air_flow_paths.json"))
        assert paths
        declared: dict[str, list[dict[str, Any]]] = {}
        for path in paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            assert not list(validator.iter_errors(document)), path
            for record in document.get("ambient_openings", []):
                assert record["type"] in ("makeup_louvre", "open_deck"), path
                if record["type"] == opening_type:
                    declared.setdefault(path.parent.name, []).append(record)
        return declared

    def test_declared_makeup_louvres(self) -> None:
        # CONTAM-AMBIENT-MAKEUP-CRUISE-01 and
        # CONTAM-AMBIENT-MAKEUP-FICTION-01 authored the records: make-up
        # louvres on the six cruise hulls and two fiction hulls, native rate 0
        # (D5), no imposed wind. CONTAM-GREG-SERVICE-MAKEUP-01 adds the
        # greg_mortimer Engine_Room service intake (second record).
        # CONTAM-OLYMPIA-MAKEUP-01 adds the olympia_c6 forecastle make-up
        # intake.
        declared = self._declared("makeup_louvre")
        assert {hull: len(rows) for hull, rows in declared.items()} == _MAKEUP_RECORDS
        for rows in declared.values():
            for record in rows:
                assert record["exchange_m3h"] == pytest.approx(0.0)
                assert "wind_speed_m_s" not in record

    def test_declared_weather_openings(self) -> None:
        # CONTAM-AMBIENT-WEATHER-CRUISE-01, CONTAM-AMBIENT-WEATHER-DESTROYER-01,
        # CONTAM-AMBIENT-WEATHER-CARRIER-01 and
        # CONTAM-AMBIENT-WEATHER-BATTLESHIP-01 authored the weather openings;
        # committed bundles carry two legs per record.
        declared = self._declared("open_deck")
        assert {
            hull: {record["zone"] for record in rows} for hull, rows in declared.items()
        } == _WEATHER_ZONES
        for hull, rows in declared.items():
            assert len(rows) == len(_WEATHER_ZONES[hull])
            for record in rows:
                assert record["wind_speed_m_s"] == pytest.approx(1.0)
                assert record["exchange_m3h"] > 0.0

    def test_weather_zones_carry_the_authored_exposure(self) -> None:
        # D7(b): the zone an ``open_deck`` record sits on declares
        # ``exposure: weather``; owner-ruled enclosed zones declare
        # ``exposure: enclosed``; no other committed zone declares exposure.
        weather: dict[str, set[str]] = {}
        enclosed: dict[str, set[str]] = {}
        for path in sorted(_PLATFORM_ROOT.glob("*/spatial_layout.json")):
            for zone in json.loads(path.read_text(encoding="utf-8"))["zones"]:
                exposure = zone.get("exposure")
                if exposure is None:
                    continue
                assert exposure in ("weather", "enclosed"), (path, zone["id"])
                target = weather if exposure == "weather" else enclosed
                target.setdefault(path.parent.name, set()).add(zone["id"])
        assert weather == _WEATHER_ZONES
        assert enclosed == _ENCLOSED_ZONES


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

    def _opening_rows(self, record: dict[str, Any], **kwargs: Any) -> list[list[str]]:
        kwargs.setdefault("hobbyist", True)
        text, path_map = export_prj_with_path_map(_spatial(), _airflow(record), **kwargs)
        nrs = {e["path_nr"] for e in path_map if e["kind"] == AMBIENT_OPENING_KIND}
        return [
            line.split() for line in _prj_section(text, "! flow paths")
            if line.split() and line.split()[0].isdigit() and int(line.split()[0]) in nrs
        ]

    _CALM = {"relative_wind_speed_m_s": 0.0}

    @pytest.mark.parametrize("speed", [None, 0.0])
    def test_no_declared_wind_follows_the_hull_wind(self, speed: float | None) -> None:
        # CONTAM-DEFAULT-WEATHER-01: an opening with no declared speed is an
        # ordinary profile path: flagged under the hull wind, both legs on the
        # zone's wall azimuth, no constant pressure.
        rows = self._opening_rows(_opening(wind_speed_m_s=speed))
        assert {row[1] for row in rows} == {"1"}
        assert {row[6] for row in rows} == {"1"}
        assert len({row[17] for row in rows}) == 1
        for row in rows:
            assert float(row[15]) == pytest.approx(0.0)  # wPset
            assert float(row[16]) == pytest.approx(0.8)  # wPmod
        calm = self._opening_rows(_opening(wind_speed_m_s=speed), overrides=self._CALM)
        assert {row[1] for row in calm} == {"0"}  # labelled calm baseline

    def test_declared_wind_faces_one_leg_windward_and_one_leeward(self) -> None:
        windward, leeward = self._opening_rows(_opening(wind_speed_m_s=1.0))
        assert windward[1] == leeward[1] == "1"  # ContamX wind flag
        assert windward[6] == leeward[6] == "1"  # the hull's Cp profile
        assert (float(windward[17]), float(leeward[17])) == (0.0, 180.0)
        for row in (windward, leeward):
            assert float(row[15]) == pytest.approx(0.0)  # no constant pressure
            assert float(row[16]) == pytest.approx(0.8)  # record speed = hull speed

    def test_cross_ventilated_legs_follow_the_wind_direction(self) -> None:
        windward, leeward = self._opening_rows(
            _opening(wind_speed_m_s=1.0),
            overrides={"relative_wind_direction_deg": 270.0},
        )
        assert (float(windward[17]), float(leeward[17])) == (270.0, 90.0)

    @pytest.mark.parametrize("hull,record", [(1.0, 2.0), (1.0, 5.0), (4.0, 2.0)])
    def test_record_speed_is_not_a_second_contamx_wind(
        self, hull: float, record: float,
    ) -> None:
        rows = self._opening_rows(
            _opening(wind_speed_m_s=record),
            overrides={"relative_wind_speed_m_s": hull},
        )
        assert [float(row[16]) for row in rows] == pytest.approx([0.8, 0.8])

    def test_calm_baseline_imposes_windward_and_leeward_pressure(self) -> None:
        # CONTAM-AMBIENT-WEATHER-CRUISE-01: wPmod 0.8 x Cp x rho U^2 / 2 with
        # the ShipHull Cp of 0.7 windward and -0.25 leeward.
        dynamic = 0.5 * 101325.0 / (287.055 * 293.15)
        windward, leeward = self._opening_rows(
            _opening(wind_speed_m_s=1.0), overrides=self._CALM,
        )
        assert windward[1] == leeward[1] == "1"  # ContamX wind flag
        assert windward[6] == leeward[6] == "0"  # no profile: wPset is constant
        assert float(windward[15]) == pytest.approx(0.8 * 0.7 * dynamic, rel=1e-5)
        assert float(leeward[15]) == pytest.approx(0.8 * -0.25 * dynamic, rel=1e-5)

    def test_imposed_pressure_scales_with_the_square_of_the_speed(self) -> None:
        pressures = {
            speed: [float(row[15]) for row in self._opening_rows(
                _opening(wind_speed_m_s=speed), overrides=self._CALM,
            )]
            for speed in (1.0, 2.0, 5.0)
        }
        for speed in (2.0, 5.0):
            for slow, fast in zip(pressures[1.0], pressures[speed]):
                assert fast == pytest.approx(slow * speed * speed, rel=1e-4)

    def test_skeleton_export_imposes_the_calm_baseline_pressure(self) -> None:
        record = _opening(wind_speed_m_s=1.0)
        calm = [row[15] for row in self._opening_rows(record, overrides=self._CALM)]
        skeleton = [row[15] for row in self._opening_rows(record, hobbyist=False)]
        assert skeleton == calm
        assert all(abs(float(value)) > 1e-6 for value in skeleton)

    def test_declared_wind_needs_the_paired_model(self) -> None:
        record = _opening(wind_speed_m_s=1.0)
        with pytest.raises(ValueError, match="wind_speed_m_s"):
            self._opening_rows(record, overrides={"ambient_opening_model": "single_orifice"})

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
