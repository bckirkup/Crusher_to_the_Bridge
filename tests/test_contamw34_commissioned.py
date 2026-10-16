"""
test_contamw34_commissioned.py – commissioned AHS terminal emission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline checks for ``ahs_terminal_mode="commissioned"``: per-room
``ach·V·duty`` Fahs on a constant schedule, exhaust-only head branches
(supply 0 / return ``ach·V``), ``declared_flow_m3h`` in the path_map, and
the mode-select plumbing. No ContamX binary required — the measured
hull→solver proof lives in ``tools/contam_commissioned_check.py``.

Design-mode invariance is a labelled change-detector: the committed
``contam/platform.prj`` + ``path_map.json`` are the emitters' baseline.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.contamx_ahs_bridge import (  # noqa: E402
    ahs_plenum_id,
    synthesize_ahs_recirculation_paths,
)
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.contamw34_prj import _flow_m3h_to_fahs_kg_s  # noqa: E402

_PLATFORM = "destroyer_baseline"
_AIR_DENSITY = 1.2041

# Path-row token slots (ContamW 3.4 flow-paths section)
_TOK_FLAG = 1
_TOK_SCHED = 8
_TOK_FAHS = 18
_FLAG_TERMINAL = 8


def _load_platform(name: str = _PLATFORM) -> tuple[dict, dict]:
    base = REPO_ROOT / "data" / "platforms" / name
    with open(base / "spatial_layout.json", encoding="utf-8") as fh:
        spatial = json.load(fh)
    with open(base / "air_flow_paths.json", encoding="utf-8") as fh:
        airflow = json.load(fh)
    return spatial, airflow


def _terminal_rows(text: str) -> dict[int, dict[str, float]]:
    """flow-paths rows with flag=8 → {path nr: {sched, fahs}}."""
    rows: dict[int, dict[str, float]] = {}
    for ln in text.splitlines():
        toks = ln.split()
        if (
            len(toks) > _TOK_FAHS
            and toks[0].isdigit()
            and int(toks[_TOK_FLAG]) == _FLAG_TERMINAL
        ):
            rows[int(toks[0])] = {
                "sched": float(toks[_TOK_SCHED]),
                "fahs": float(toks[_TOK_FAHS]),
            }
    return rows


def _export(platform: str = _PLATFORM, **kwargs):
    spatial, airflow = _load_platform(platform)
    return export_prj_with_path_map(
        spatial, airflow, hobbyist=True, **kwargs,
    )


def _declared(platform: str = _PLATFORM) -> dict[str, dict[str, float]]:
    """Independently recomputed declared field (same contract as the
    commissioning harness: ach·V·duty balanced; supply 0 / return ach·V
    when hvac_duty <= 0)."""
    spatial, airflow = _load_platform(platform)
    volumes = {z["id"]: float(z["volume_m3"]) for z in spatial["zones"]}
    default_duty = float(airflow.get("hvac_duty", 1.0) or 0.0)
    out: dict[str, dict[str, float]] = {}
    for hz in airflow["hvac_zones"]:
        ach = float(hz["ach"])
        duty = default_duty if hz.get("hvac_duty") is None else float(
            hz["hvac_duty"]
        )
        for room in hz["rooms"]:
            vol = volumes[room]
            if duty <= 0.0:
                out[room] = {"supply": 0.0, "return": ach * vol}
            else:
                out[room] = {"supply": ach * vol * duty,
                             "return": ach * vol * duty}
    return out


def test_commissioned_terminal_fahs_is_per_room_declared() -> None:
    text, path_map = _export(ahs_terminal_mode="commissioned")
    rows = _terminal_rows(text)
    declared = _declared()
    terminal_entries = [
        e for e in path_map if e["kind"] in ("ahs_supply", "ahs_return")
    ]
    assert terminal_entries, "no terminal paths emitted"
    for entry in terminal_entries:
        room = (
            entry["to_zone"] if entry["kind"] == "ahs_supply"
            else entry["from_zone"]
        )
        leg = "supply" if entry["kind"] == "ahs_supply" else "return"
        want_fahs = _flow_m3h_to_fahs_kg_s(declared[room][leg])
        assert rows[entry["path_nr"]]["fahs"] == pytest.approx(want_fahs), (
            f"{entry['kind']} {room}: Fahs "
            f"{rows[entry['path_nr']]['fahs']} != {want_fahs}"
        )


def test_commissioned_terminals_ignore_duty_schedule() -> None:
    """Commissioned flow is folded into Fahs; sched must be constant (0)."""
    text, _ = _export(ahs_terminal_mode="commissioned")
    for nr, row in _terminal_rows(text).items():
        assert row["sched"] == 0, f"terminal {nr} sched={row['sched']}"


def test_commissioned_exhaust_only_branches() -> None:
    """Head-deck AHUs (hvac_duty=0): supply 0, return at ach·V."""
    _text, path_map = _export(ahs_terminal_mode="commissioned")
    declared = _declared()
    hd_rooms = [
        r for r, d in declared.items()
        if d["supply"] == 0.0 and d["return"] > 0.0
    ]
    assert hd_rooms, "fixture should contain exhaust-only head rooms"
    for entry in path_map:
        if entry["kind"] == "ahs_supply" and entry["to_zone"] in hd_rooms:
            assert entry["declared_flow_m3h"] == pytest.approx(0.0)
        if entry["kind"] == "ahs_return" and entry["from_zone"] in hd_rooms:
            room = entry["from_zone"]
            assert entry["declared_flow_m3h"] == pytest.approx(
                declared[room]["return"]
            )


def test_path_map_records_declared_flow() -> None:
    _text, path_map = _export(ahs_terminal_mode="commissioned")
    declared = _declared()
    seen = 0
    for entry in path_map:
        if entry["kind"] not in ("ahs_supply", "ahs_return"):
            continue
        room = (
            entry["to_zone"] if entry["kind"] == "ahs_supply"
            else entry["from_zone"]
        )
        leg = "supply" if entry["kind"] == "ahs_supply" else "return"
        assert entry["declared_flow_m3h"] == pytest.approx(
            declared[room][leg]
        )
        seen += 1
    assert seen == 2 * len(declared)


def test_commissioned_differs_from_design_split() -> None:
    """Graded sensitivity: rooms of different volume get different Fahs."""
    _text, path_map = _export(ahs_terminal_mode="commissioned")
    ahs2_supplies = {
        e["to_zone"]: e["declared_flow_m3h"]
        for e in path_map
        if e["kind"] == "ahs_supply" and e.get("ahs_nr") == 2
    }
    # MedBay 180 / Mess_Hall 480 / Galley 240 — uniform split would be 300 each
    assert len(set(ahs2_supplies.values())) == len(ahs2_supplies) > 1


def test_design_mode_is_byte_stable() -> None:
    """Change-detector: default emission still reproduces committed files."""
    from tools.contam_hobbyist import load_hobbyist_overrides

    for name in ("destroyer_baseline", "expedition_cruise_450"):
        platform_dir = str(REPO_ROOT / "data" / "platforms" / name)
        spatial, airflow = _load_platform(name)
        text, path_map = export_prj_with_path_map(
            spatial, airflow, hobbyist=True,
            overrides=load_hobbyist_overrides(platform_dir),
        )
        contam = REPO_ROOT / "data" / "platforms" / name / "contam"
        assert text == (contam / "platform.prj").read_text(
            encoding="utf-8"
        ), f"{name}: design-mode .prj drifted"
        committed = json.loads(
            (contam / "path_map.json").read_text(encoding="utf-8")
        )
        assert path_map == committed, f"{name}: design-mode path_map drifted"


def test_overrides_select_terminal_mode() -> None:
    _t, path_map = _export(overrides={"ahs_terminal_mode": "commissioned"})
    terminal = next(
        e for e in path_map if e["kind"] == "ahs_supply"
    )
    assert "declared_flow_m3h" in terminal


def test_invalid_terminal_mode_rejected() -> None:
    with pytest.raises(ValueError, match="ahs_terminal_mode"):
        _export(ahs_terminal_mode="balanced")


def test_exhaust_only_group_still_emits_plenum_returns() -> None:
    """Star synthesis: a return-only group drains room → plenum."""
    entries = [
        {
            "path_nr": 11, "kind": "ahs_supply",
            "from_zone": "ahs4(Sup)", "to_zone": "HD_MAIN_M", "ahs_nr": 4,
        },
        {
            "path_nr": 12, "kind": "ahs_return",
            "from_zone": "HD_MAIN_M", "to_zone": "ahs4(Ret)", "ahs_nr": 4,
        },
    ]
    flows = {11: 0.0, 12: 358.0}
    paths = synthesize_ahs_recirculation_paths(
        entries, flows, {"HD_MAIN_M"}, oa_fraction=1.0,
    )
    assert len(paths) == 1
    assert paths[0].from_zone == "HD_MAIN_M"
    assert paths[0].to_zone == ahs_plenum_id(4)
    assert paths[0].flow_rate_m3h == pytest.approx(358.0)


def test_balanced_group_unaffected_by_returns_relaxation() -> None:
    """A normal supply+return group keeps its supply legs (no regression)."""
    entries = [
        {
            "path_nr": 1, "kind": "ahs_supply",
            "from_zone": "ahs1(Sup)", "to_zone": "Room_A", "ahs_nr": 1,
        },
        {
            "path_nr": 2, "kind": "ahs_return",
            "from_zone": "Room_A", "to_zone": "ahs1(Ret)", "ahs_nr": 1,
        },
        {
            "path_nr": 3, "kind": "ahs_recirc",
            "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "ahs_nr": 1,
        },
    ]
    flows = {1: 200.0, 2: 200.0, 3: 0.0}
    paths = synthesize_ahs_recirculation_paths(
        entries, flows, {"Room_A"}, oa_fraction=0.2,
    )
    assert re.match(r".*_(ret|sup)_", paths[0].path_id)
    kinds = {p.to_zone for p in paths} | {p.from_zone for p in paths}
    assert ahs_plenum_id(1) in kinds
    assert "Room_A" in kinds
    supply_leg = next(p for p in paths if p.to_zone == "Room_A")
    assert supply_leg.flow_rate_m3h == pytest.approx(0.8 * 200.0)
