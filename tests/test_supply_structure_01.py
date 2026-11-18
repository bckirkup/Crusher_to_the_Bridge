"""SUPPLY-STRUCTURE-01 Stage A integrity gates.

Contract: ``docs/norovirus/supply_structure_01_design.md``. The arms are
structural scenario labels over the PROVISIONED-SOURCE-01 station census:
``source_cluster`` correlation, ``venue_menu`` service-class incidence, and
``lot_scale`` per-lot yield. These tests pin the no-op flat baseline, the
declared-arm witnesses, and the v1 receipt-layer boundary; they do not fit any
epidemiological anchor.
"""

from __future__ import annotations

import pytest

from engines.transmission_core import COMMON_SOURCE_LOT_ITEM_LINES
from tests.test_common_source_events import (
    MDR_ZONE,
    PATHOGEN,
    ZONE,
    _core,
    _diner,
)
from tests.test_common_source_lot_objects import _step_objects
from tests.test_common_source_provisioned_source import (
    SOURCE_ID,
    _plan,
    _ps_cfg,
)
from tests.test_food_supply_01 import _two_zone_core


def _ps_structure(
    q_source: float = 0.5,
    *,
    lot_layer_mode: str | None = None,
    source_cluster: dict | None = None,
    venue_menu: dict | None = None,
    lot_scale: dict | None = None,
    station_zone_pin: list[str] | None = None,
) -> dict:
    ps: dict = {"source_id": SOURCE_ID, "q_source": q_source}
    if lot_layer_mode is not None:
        ps["lot_layer_mode"] = lot_layer_mode
    structure: dict = {"mode": "declared"}
    if source_cluster is not None:
        structure["source_cluster"] = source_cluster
    if venue_menu is not None:
        structure["venue_menu"] = venue_menu
    if lot_scale is not None:
        structure["lot_scale"] = lot_scale
    if station_zone_pin is not None:
        ps["station_zone_pin"] = list(station_zone_pin)
    ps["supply_structure"] = structure
    return _ps_cfg(0.0, provisioned_source=ps)


def test_explicit_flat_matches_absent_baseline() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    absent = _core(cfg_cs=_ps_cfg(0.7), seed=5)
    explicit = _core(
        cfg_cs=_ps_cfg(
            0.0,
            provisioned_source={
                "source_id": SOURCE_ID,
                "q_source": 0.7,
                "supply_structure": {"mode": "flat"},
            },
        ),
        seed=5,
    )
    events_a, _, objects_a, _ = _step_objects(absent, agents)
    events_b, _, objects_b, _ = _step_objects(explicit, agents)
    assert events_a == events_b
    assert objects_a == objects_b


def test_declared_null_arm_echoes_and_preserves_census() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    flat = _core(cfg_cs=_ps_cfg(0.7), seed=11)
    declared = _core(cfg_cs=_ps_structure(0.7), seed=11)
    _plan(flat, agents)
    _plan(declared, agents)
    assert (
        flat._cs_contaminated_stations[PATHOGEN]
        == declared._cs_contaminated_stations[PATHOGEN]
    )
    witness = declared._cs_provisioned_source[PATHOGEN]
    assert witness["supply_structure"]["mode"] == "declared"
    assert "supply_structure" not in flat._cs_provisioned_source[PATHOGEN]


def test_venue_menu_masks_service_classes() -> None:
    passenger = _core(
        cfg_cs=_ps_structure(
            0.5,
            venue_menu={"service_class_mask": "passenger_raw"},
        ),
    )
    stations = passenger._cs_supply_structure_stations(
        passenger._cs_station_census([ZONE, MDR_ZONE, "Crew_Mess"]),
    )
    assert (ZONE, "shellfish") in stations
    assert (MDR_ZONE, "shellfish") in stations
    assert ("Crew_Mess", "shellfish") not in stations
    assert ("Crew_Mess", "garnish") in stations

    buffet_specialty = _core(
        cfg_cs=_ps_structure(
            0.5,
            venue_menu={"service_class_mask": "buffet_specialty"},
        ),
    )
    stations = buffet_specialty._cs_supply_structure_stations(
        buffet_specialty._cs_station_census([ZONE, MDR_ZONE, "Crew_Mess"]),
    )
    assert (ZONE, "shellfish") in stations
    assert (MDR_ZONE, "shellfish") not in stations
    assert (MDR_ZONE, "salad_leaf") in stations
    assert ("Crew_Mess", "fresh_produce") not in stations


def test_venue_menu_applies_after_station_zone_pin() -> None:
    agents = [
        *[_diner(i, dining_zone=ZONE, location=ZONE) for i in range(1, 20)],
        *[
            _diner(i, dining_zone=MDR_ZONE, location=MDR_ZONE)
            for i in range(20, 40)
        ],
    ]
    core = _two_zone_core(
        _ps_structure(
            1.0,
            venue_menu={"service_class_mask": "buffet_specialty"},
            station_zone_pin=[MDR_ZONE],
        ),
    )
    _plan(core, agents)
    objects = core._cs_objects[PATHOGEN]
    shellfish_mdr = [
        obj for obj in objects
        if obj["item_label"] == "shellfish" and obj["zone"] == MDR_ZONE
    ]
    salad_mdr = [
        obj for obj in objects
        if obj["item_label"] == "salad_leaf" and obj["zone"] == MDR_ZONE
    ]
    assert not shellfish_mdr
    assert salad_mdr


def test_fleet_shared_cluster_is_all_or_nothing() -> None:
    counts = []
    for seed in range(40):
        core = _core(
            cfg_cs=_ps_structure(
                0.5,
                source_cluster={"rung": "fleet_shared"},
            ),
            seed=seed,
        )
        _plan(core, [_diner(i) for i in range(1, 40)])
        witness = core._cs_provisioned_source[PATHOGEN]
        counts.append(witness["n_contaminated"])
        if witness["n_contaminated"]:
            assert all(
                obj["source_cluster_id"] == "fleet"
                for obj in core._cs_objects[PATHOGEN]
            )
    assert set(counts) <= {0, len(COMMON_SOURCE_LOT_ITEM_LINES)}
    assert 0 in counts
    assert len(COMMON_SOURCE_LOT_ITEM_LINES) in counts


def test_line_shared_cluster_spans_venues_for_one_item() -> None:
    agents = [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
    agents += [
        _diner(100 + i, dining_zone=MDR_ZONE) for i in range(1, 20)
    ]
    core = _two_zone_core(
        _ps_structure(1.0, source_cluster={"rung": "line_shared"}),
    )
    _plan(core, agents)
    by_station = {
        obj["zone"]: obj["source_cluster_id"]
        for obj in core._cs_objects[PATHOGEN]
        if obj["item_label"] == "shellfish"
    }
    assert by_station.get(ZONE) == "line|shellfish"
    assert by_station.get(MDR_ZONE) == "line|shellfish"


def test_lot_scale_multiplier_scales_servings_without_extra_draws() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    flat = _core(cfg_cs=_ps_cfg(1.0), seed=7)
    scaled = _core(
        cfg_cs=_ps_structure(
            1.0,
            lot_scale={"servings_multiplier": 2.0},
        ),
        seed=7,
    )
    _, _, flat_objects, _ = _step_objects(flat, agents)
    _, _, scaled_objects, _ = _step_objects(scaled, agents)
    flat_lots = [
        obj for obj in flat_objects if obj["source_kind"] == "provisioned_lot"
    ]
    scaled_lots = [
        obj for obj in scaled_objects if obj["source_kind"] == "provisioned_lot"
    ]
    assert len(flat_lots) == len(scaled_lots)
    for flat_lot, scaled_lot in zip(flat_lots, scaled_lots):
        assert scaled_lot["servings_multiplier"] == pytest.approx(2.0)
        assert scaled_lot["lot_servings"] == pytest.approx(
            flat_lot["lot_servings"] * 2,
            abs=2.0,
        )


def test_flat_mode_rejects_nondefault_subarms() -> None:
    with pytest.raises(ValueError, match="mode 'flat'"):
        _core(
            cfg_cs=_ps_cfg(
                0.0,
                provisioned_source={
                    "source_id": SOURCE_ID,
                    "q_source": 0.5,
                    "supply_structure": {
                        "mode": "flat",
                        "lot_scale": {"servings_multiplier": 2.0},
                    },
                },
            ),
        )


def test_receipt_layer_rejects_supply_structure_arms() -> None:
    cfg = _ps_structure(
        1.0,
        lot_layer_mode="single_line_receipt",
        source_cluster={"rung": "fleet_shared"},
    )
    core = _core(cfg_cs=cfg)
    agents = [_diner(i) for i in range(1, 40)]
    with pytest.raises(ValueError, match="receipt-layer composition"):
        _plan(core, agents)
