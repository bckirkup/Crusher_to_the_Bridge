"""CONTAM-AMBIENT-OPENING-BOUNDARY-01: outward ambient openings are sinks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_transport import (  # noqa: E402
    ENVELOPE_LEAK_PRESSURE_ONLY,
    ContamXTransportEngine,
    is_outward_ambient_opening,
)
from engines.py_contam_bridge import AMBIENT_OPENING_KIND  # noqa: E402
from tools.contam_flow_compare import (  # noqa: E402
    FATE_BOUNDARY_SINK,
    classify_contamx_path_fate,
    contamx_flow_report,
)

_LAYOUT = {
    "zones": [
        {"id": "A", "volume_m3": 100.0},
        {"id": "B", "volume_m3": 100.0},
    ]
}
_KNOWN = {"A", "B"}
_PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"


def _entry(
    nr: int, kind: str, src: str, dst: str = "ambient", **extra: Any,
) -> dict[str, Any]:
    return {
        "path_nr": nr,
        "kind": kind,
        "from_zone": src,
        "to_zone": dst,
        "crusher_transfer": False,
        "is_hvac_ducted": False,
        **extra,
    }


def _ambient_entries() -> list[dict[str, Any]]:
    return [
        _entry(1, AMBIENT_OPENING_KIND, "A"),
        _entry(2, AMBIENT_OPENING_KIND, "B"),
        _entry(3, "adjacency", "A", "B", crusher_transfer=True),
    ]


def _mixed_entries() -> list[dict[str, Any]]:
    return [
        _entry(1, "envelope_leak", "A"),
        _entry(2, AMBIENT_OPENING_KIND, "B"),
        _entry(3, "adjacency", "A", "B", crusher_transfer=True),
    ]


def _compare_entries() -> list[dict[str, Any]]:
    return [
        _entry(1, "envelope_leak", "A"),
        _entry(2, AMBIENT_OPENING_KIND, "A"),
        _entry(3, AMBIENT_OPENING_KIND, "B"),
        _entry(4, "adjacency", "A", "B", crusher_transfer=True),
    ]


def _engine(
    entries: list[dict[str, Any]],
    flows: dict[int, float],
    mode: str | None = None,
) -> ContamXTransportEngine:
    return ContamXTransportEngine(
        _LAYOUT,
        entries,
        flows,
        natural_decay_rate=0.0,
        path_map_entries=entries,
        envelope_leak_mode=mode,
    )


def _ambient_engine(
    flows: dict[int, float], mode: str | None = None,
) -> ContamXTransportEngine:
    return _engine(_ambient_entries(), flows, mode)


def _sink_paths(engine: ContamXTransportEngine) -> list[Any]:
    return [p for p in engine.airflow_paths if p.sink]


def test_outward_ambient_opening_becomes_sink_with_unchanged_magnitude() -> None:
    sinks = _sink_paths(_ambient_engine({1: 36.0, 2: -12.0, 3: 5.0}))
    assert [(p.from_zone, p.flow_rate_m3h) for p in sinks] == [("A", 36.0)]
    assert sinks[0].filtered is False


def test_inward_ambient_opening_adds_no_path() -> None:
    engine = _ambient_engine({1: -36.0, 2: -12.0, 3: 5.0})
    assert _sink_paths(engine) == []
    assert [(p.from_zone, p.to_zone) for p in engine.airflow_paths] == [("A", "B")]


def test_zero_flow_ambient_opening_adds_no_path() -> None:
    engine = _ambient_engine({1: 0.0, 2: 0.0, 3: 5.0})
    assert _sink_paths(engine) == []
    assert len(engine.airflow_paths) == 1


def test_sink_removes_mass_monotonically_in_outward_flow() -> None:
    start = {"A": 1000.0, "B": 0.0}
    retained = []
    for outward in (0.0, 18.0, 36.0, 72.0):
        result = _ambient_engine({1: outward, 2: -12.0}).transport_step(dict(start))
        retained.append(result["A"] + result["B"])
    assert retained[0] == pytest.approx(1000.0)
    assert retained[0] > retained[1] > retained[2] > retained[3] > 0.0


def test_inward_exchange_conserves_mass() -> None:
    engine = _ambient_engine({1: -72.0, 2: -36.0})
    result = engine.transport_step({"A": 1000.0, "B": 500.0})
    assert engine.airflow_paths == []
    assert result["A"] + result["B"] == pytest.approx(1500.0)


def test_pressure_only_mode_still_gates_only_envelope_leaks() -> None:
    entries = _mixed_entries()
    engine = _engine(entries, {1: 36.0, 2: 12.0, 3: 5.0}, ENVELOPE_LEAK_PRESSURE_ONLY)
    assert [(p.from_zone, p.to_zone, p.flow_rate_m3h) for p in _sink_paths(engine)] == [
        ("B", "ambient", 12.0)
    ]
    assert len(engine.airflow_paths) == 2


def test_helper_requires_real_source_and_ambient_destination() -> None:
    opening = _ambient_entries()[0]
    assert is_outward_ambient_opening(opening, 1.0, _KNOWN)
    assert not is_outward_ambient_opening(opening, -1.0, _KNOWN)
    assert not is_outward_ambient_opening(opening, 0.0, _KNOWN)
    assert not is_outward_ambient_opening(opening, 1.0, {"B"})
    assert not is_outward_ambient_opening(_ambient_entries()[2], 1.0, _KNOWN)


def test_compare_fate_matches_engine_filter() -> None:
    entries = _compare_entries()
    flows = {1: 36.0, 2: -12.0, 3: 10.0, 4: 5.0}
    fates = {
        e["path_nr"]: classify_contamx_path_fate(e, flows, _KNOWN)["fate"]
        for e in entries
    }
    assert fates == {1: FATE_BOUNDARY_SINK, 2: "skipped", 3: FATE_BOUNDARY_SINK, 4: "kept"}
    report = contamx_flow_report(entries, flows, _KNOWN)
    assert report["n_boundary_sink_paths"] == 2
    assert report["boundary_sink_out_m3h"] == pytest.approx(46.0)
    assert report["n_ambient_opening_paths"] == 2
    assert report["ambient_opening_sink_out_m3h"] == pytest.approx(10.0)
    assert report["ambient_opening_inward_m3h"] == pytest.approx(12.0)
    assert report["n_crusher_paths"] == len(_engine(entries, flows).airflow_paths)


def test_compare_pressure_only_baseline_still_reports_ambient_sink() -> None:
    entries = _compare_entries()
    flows = {1: 36.0, 2: -12.0, 3: 10.0, 4: 5.0}
    report = contamx_flow_report(
        entries, flows, _KNOWN, envelope_leak_mode=ENVELOPE_LEAK_PRESSURE_ONLY,
    )
    assert report["n_boundary_sink_paths"] == 1
    assert report["n_ambient_opening_paths"] == 2
    assert report["ambient_opening_sink_out_m3h"] == pytest.approx(10.0)
    assert report["fate_counts"] == {"boundary_sink": 1, "skipped": 2, "kept": 1}


def test_compare_without_sim_flows_reports_ambient_rows_as_skipped() -> None:
    entries = _ambient_entries()
    report = contamx_flow_report(entries, None, _KNOWN)
    assert report["n_ambient_opening_paths"] == 2
    assert report["ambient_opening_sink_out_m3h"] == pytest.approx(0.0)
    assert report["ambient_opening_inward_m3h"] == pytest.approx(0.0)
    assert {
        row["path_nr"]: row["fate"] for row in report["classified_paths"]
    } == {1: "skipped", 2: "skipped", 3: "unknown"}


def test_committed_ambient_opening_legs_are_the_declared_records() -> None:
    # CONTAM-AMBIENT-MAKEUP-CRUISE-01 and CONTAM-AMBIENT-MAKEUP-FICTION-01:
    # two legs per authored make-up louvre on the eight hulls;
    # CONTAM-GREG-SERVICE-MAKEUP-01 adds the two legs of the greg_mortimer
    # Engine_Room service intake.
    # CONTAM-AMBIENT-WEATHER-CRUISE-01 adds two legs per authored cruise
    # weather-deck opening; CONTAM-AMBIENT-WEATHER-DESTROYER-01 adds two legs
    # per destroyer roster weather opening; CONTAM-AMBIENT-WEATHER-CARRIER-01
    # adds two legs on each ungrouped carrier flight deck (lexington_cv2,
    # saratoga_cv3); CONTAM-GROUPED-WEATHER-CARRIER-01 adds two legs per
    # grouped carrier weather opening; CONTAM-AMBIENT-WEATHER-BATTLESHIP-01
    # adds two legs per
    # ungrouped battleship weather opening;
    # CONTAM-AMBIENT-WEATHER-CRUISER-01 adds two legs on each
    # zero-outdoor-exchange AHU_Weather room of alexander_henry_cgs119;
    # CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01 adds two legs per ungrouped
    # amphibious weather opening; CONTAM-AMBIENT-WEATHER-AUXILIARY-01 adds two
    # legs per ungrouped auxiliary weather opening;
    # CONTAM-AMBIENT-WEATHER-MISC-01 adds two legs per ungrouped/zero-exchange
    # misc weather opening; CONTAM-AMBIENT-WEATHER-OLYMPIA-01 adds two legs
    # per olympia_c6 weather/boat-stowage opening; CONTAM-OLYMPIA-MAKEUP-01
    # adds the two legs of the olympia_c6 forecastle make-up intake;
    # CONTAM-GROUPED-WEATHER-MIDWAY-01 adds the two legs of the midway_cv41
    # Flight_Deck opening (first grouped weather zone);
    # CONTAM-GROUPED-WEATHER-CRUISER-01 adds two legs per opening on
    # astoria_ca34, chicago_cg11 and miami_cl89;
    # CONTAM-GROUPED-WEATHER-AMPHIBIOUS-01 adds six legs on fort_mandan_lsd21
    # and four legs on middlesex_lst983 (san_antonio_class_lpd has no committed
    # bundle). No other committed bundle carries an opening.
    paths = sorted(_PLATFORM_ROOT.glob("*/contam/path_map.json"))
    assert paths
    legs: dict[str, int] = {}
    for path in paths:
        entries = json.loads(path.read_text(encoding="utf-8"))
        count = sum(1 for e in entries if e.get("kind") == AMBIENT_OPENING_KIND)
        if count:
            legs[path.parent.parent.name] = count
    assert legs == {
        "classic_cruise_1900": 2 + 2, "diamond_princess": 2 + 16,
        "expedition_cruise_450": 2 + 2, "greg_mortimer": 2 + 2 + 10,
        "mega_cruise_5000": 20 + 10, "spirit_cruise_3000": 2 + 6,
        "enterprise_constitution_tos": 2, "enterprise_galaxy_tng": 2,
        "cannon_de701": 8, "cushing_dd376": 4, "davison_dd618": 10,
        "fletcher_dde_dd445": 4, "hunter_killer_dd692": 14,
        "keppler_dd765": 14, "nields_dd616": 10, "palmer_dms5": 2,
        "sigsbee_dd502": 8,
        "lexington_cv2": 2, "saratoga_cv3": 2,
        "antietam_cvs36": 6, "battler_acv6": 4,
        "independence_cvl26": 8, "puncher_cve53": 2,
        "ranger_cv4": 4, "saratoga_cv60": 2, "thetis_bay_cve90": 2,
        "wasp_cv7": 2, "wright_cc2": 6, "yorktown_cv5": 2,
        "new_york_bb34": 12, "south_dakota_bb49": 8, "texas_bb35": 10,
        "west_virginia_bb48": 10, "alexander_henry_cgs119": 8,
        "astoria_ca34": 10, "chicago_cg11": 16, "miami_cl89": 4,
        "lsm_354": 8, "middlesex_lst983": 18, "fort_mandan_lsd21": 6,
        "ruchamkin_apd89": 8,
        "aeolus_arc3": 6, "apl_24": 8,
        "bolster_ars38": 8, "cobalt_k124": 6, "gordon_gunter_r338": 8,
        "liberty_cargo_ec2": 12, "lyon_ap71": 22, "passumpsic_ao106": 8,
        "savannah_ns": 28,
        "castle_class_corvette": 4, "eagle_pe60": 14,
        "pce_874": 4, "raven_am55": 6, "river_class_frigate": 4,
        "rolla_pc483": 4, "olympia_c6": 22,
        "midway_cv41": 2,
    }
