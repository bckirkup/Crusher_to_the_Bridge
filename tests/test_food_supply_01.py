"""FOOD-SUPPLY-01 receipt/lot layer gates.

The receipt layer sits above the PROVISIONED-SOURCE-01 station census:
``station_lots`` remains the bit-identical baseline, while
``single_line_receipt`` / ``declared_receipts`` mint supply receipts with
per-item-line prevalence, preparation-class filtering, and shared-lot
correlation across venues. These tests pin the default-off contract only;
they do not fit any epidemiological anchor.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    COMMON_SOURCE_LOT_ITEM_LINES,
    TransmissionCore,
)
from tests.test_common_source_events import (
    MDR_ZONE,
    PATHOGEN,
    ZONE,
    _core,
    _diner,
    _profile,
)
from tests.test_common_source_lot_objects import _step_objects
from tests.test_common_source_provisioned_source import (
    SOURCE_ID,
    _plan,
    _ps_cfg,
)


def _ps_override(**fields: object) -> dict:
    ps: dict[str, object] = {"source_id": SOURCE_ID, "q_source": 0.0}
    ps.update(fields)
    return ps


def _two_zone_core(cfg_cs: dict) -> TransmissionCore:
    """Two Dining venues so a single receipt can cover multiple zones."""
    core = TransmissionCore(
        rng=np.random.default_rng(7),
        zone_volumes={ZONE: 50.0, MDR_ZONE: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={ZONE: "Dining", MDR_ZONE: "Dining"},
        cfg={"transmission": {"common_source": cfg_cs}},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([ZONE, MDR_ZONE])
    core._quarantined_ids = set()
    return core


def test_station_lots_ignores_receipt_fields() -> None:
    """Explicit station_lots with receipt metadata stays seed-paired with
    the unmarked provisioned_source baseline."""
    agents = [_diner(i) for i in range(1, 40)]
    core_a = _core(cfg_cs=_ps_cfg(1.0))
    core_b = _core(cfg_cs=_ps_cfg(
        0.0,
        provisioned_source=_ps_override(
            q_source=1.0,
            lot_layer_mode="station_lots",
            q_source_by_item_line={
                "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
            },
        ),
    ))
    events_a, _, objects_a, _ = _step_objects(core_a, agents)
    events_b, _, objects_b, _ = _step_objects(core_b, agents)
    assert core_b._cs_ps_lot_layer_mode == "station_lots"
    assert events_a == events_b
    assert objects_a == objects_b
    assert core_b._cs_receipt_log == []


def test_single_line_receipt_filters_preparation_class() -> None:
    """One receipt per item line: raw/RTE shellfish mints a lot, prepared
    deli is witnessed RNA-positive but mints no infectious object."""
    ps = _ps_override(
        lot_layer_mode="single_line_receipt",
        q_source_by_item_line={
            "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
            "deli": {"prevalence": 1.0, "implicated_share": 1.0},
        },
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    _plan(core, [_diner(i) for i in range(1, 40)])
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["lot_layer_mode"] == "single_line_receipt"
    assert witness["n_receipts"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_lots"] == 1
    assert witness["n_contaminated"] == 2
    assert witness["contaminated_by_item_line"] == {
        "shellfish": 1,
        "deli": 1,
    }
    receipts = {r["item_line"]: r for r in core._cs_receipt_log}
    shellfish = receipts["shellfish"]
    deli = receipts["deli"]
    assert shellfish["contamination"] == "infectious"
    assert shellfish["lot_id"] is not None
    assert shellfish["supply_stratum"] == "shellfish"
    assert shellfish["scale_class"] == "bulk_raw"
    assert deli["contamination"] == "rna_positive_noninfectious"
    assert deli["lot_id"] is None
    assert deli["preparation_class"] == "prepared_or_pasteurized"
    obj = core._cs_objects[PATHOGEN][0]
    assert obj["receipt_id"] == shellfish["receipt_id"]
    assert obj["lot_id"] == shellfish["lot_id"]
    assert obj["venues_served"] == [ZONE]
    assert obj["service_eligible"] is True
    assert obj["quantity_servings"] is not None


def test_declared_receipts_partition_venues() -> None:
    """declared_receipts draws N receipts per item line and assigns venue
    subsets round-robin; only receipts with venues mint objects."""
    ps = _ps_override(
        lot_layer_mode="declared_receipts",
        receipts_per_item_line=2,
        q_source_by_item_line={
            "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
        },
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    _plan(core, [_diner(i) for i in range(1, 40)])
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["receipts_per_item_line"] == 2
    assert witness["n_receipts"] == 2 * len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_lots"] == 1
    shellfish_rows = [
        r for r in core._cs_receipt_log if r["item_line"] == "shellfish"
    ]
    assert len(shellfish_rows) == 2
    assert [r["venues_served"] for r in shellfish_rows] == [[ZONE], []]
    assert [r["lot_id"] is not None for r in shellfish_rows] == [True, False]


def test_empty_item_line_map_disables_receipt_contamination() -> None:
    """An explicit empty per-line map is a real map: unnamed lines carry
    zero prevalence instead of falling back to scalar ``q_source``."""
    ps = _ps_override(
        q_source=1.0,
        lot_layer_mode="single_line_receipt",
        q_source_by_item_line={},
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    _plan(core, [_diner(i) for i in range(1, 40)])
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["n_receipts"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_lots"] == 0
    assert witness["n_contaminated"] == 0
    assert all(
        row["contamination"] == "none" for row in core._cs_receipt_log
    )


def test_prevalence_scale_nests_receipt_contamination() -> None:
    """Receipt Bernoullis are all drawn before lot realization, so a
    higher prevalence scale cannot re-roll later receipts."""
    def run(scale: float) -> dict[tuple[str, int], str]:
        ps = _ps_override(
            lot_layer_mode="declared_receipts",
            receipts_per_item_line=4,
            prevalence_scale=scale,
            q_source_by_item_line={
                "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
                "salad_leaf": {"prevalence": 1.0, "implicated_share": 1.0},
            },
        )
        core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
        _plan(core, [_diner(i) for i in range(1, 40)])
        return {
            (row["item_line"], row["receipt_index"]): row["contamination"]
            for row in core._cs_receipt_log
        }

    low = run(0.2)
    high = run(0.8)
    assert set(low) == set(high)
    low_hits = sum(state != "none" for state in low.values())
    high_hits = sum(state != "none" for state in high.values())
    assert low_hits <= high_hits
    for key, state in low.items():
        if state != "none":
            assert high[key] != "none"


def test_receipt_serving_mass_is_minted_once() -> None:
    """Receipt lots mint one serving mass; pans reuse it, so emitted dose
    stays inside ``quantity_g x lot_titre``."""
    ps = _ps_override(
        lot_layer_mode="single_line_receipt",
        q_source_by_item_line={
            "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
        },
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    agents = [_diner(i) for i in range(1, 40)]
    events, _, _, _ = _step_objects(core, agents, epochs=96)
    obj = next(
        o for o in core._cs_objects[PATHOGEN] if o.get("receipt_id")
    )
    assert obj["serving_mass_g"] is not None
    assert obj["quantity_g"] == pytest.approx(
        obj["lot_servings"] * obj["serving_mass_g"],
    )
    receipt_events = [
        event for event in events if event["object_id"] == obj["object_id"]
    ]
    assert receipt_events
    expected = obj["lot_titre_gec_per_g"] * obj["serving_mass_g"]
    assert all(
        event["per_serving_dose"] == pytest.approx(expected)
        for event in receipt_events
    )


def test_shared_receipt_witness_covers_all_venues() -> None:
    """A receipt serving two Dining venues reports both venues in the
    voyage witness and contaminated-station set, not just the minted
    start zone."""
    ps = _ps_override(
        lot_layer_mode="single_line_receipt",
        q_source_by_item_line={
            "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
        },
    )
    core = _two_zone_core(_ps_cfg(0.0, provisioned_source=ps))
    agents = [
        *[_diner(i, dining_zone=ZONE, location=ZONE) for i in range(1, 20)],
        *[
            _diner(i, dining_zone=MDR_ZONE, location=MDR_ZONE)
            for i in range(20, 40)
        ],
    ]
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["n_lots"] == 1
    assert set(witness["actual_venues_used"]) == {ZONE, MDR_ZONE}
    assert core._cs_contaminated_stations[PATHOGEN] == {
        (ZONE, "shellfish"),
        (MDR_ZONE, "shellfish"),
    }
    assert core._cs_objects[PATHOGEN][0]["venues_served"] == [
        ZONE, MDR_ZONE,
    ]


def test_receipt_scalar_q_source_fallback_covers_all_lines() -> None:
    """Without a per-line map, receipt mode falls back to scalar
    ``q_source`` for every item line and preparation filtering still
    applies."""
    ps = _ps_override(
        source_id="unregistered_receipt_source",
        q_source=1.0,
        lot_layer_mode="single_line_receipt",
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    _plan(core, [_diner(i) for i in range(1, 40)])
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["n_receipts"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_contaminated"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_lots"] == 4
    assert witness["contaminated_by_preparation_class"] == {
        "raw_or_rte_no_kill": 4,
        "prepared_or_pasteurized": 3,
    }


def test_invalid_receipt_modes_fall_back_to_defaults() -> None:
    """Unknown receipt-layer modes resolve to the shipped defaults."""
    ps = _ps_override(
        lot_layer_mode="not_a_mode",
        preparation_survival_mode="cooked",
        q_source_by_item_line={
            "shellfish": {"prevalence": 1.0, "implicated_share": 1.0},
        },
    )
    core = _core(cfg_cs=_ps_cfg(0.0, provisioned_source=ps))
    _plan(core, [_diner(i) for i in range(1, 40)])
    assert core._cs_ps_lot_layer_mode == "station_lots"
    assert core._cs_ps_preparation_survival_mode == "raw_rte_only"


def test_receipt_spec_helpers_cover_intervals_and_bad_values() -> None:
    """Receipt spec helpers accept interval draws and fall back on bad
    scalar specs without contaminating the stream."""
    core = _core(cfg_cs=_ps_cfg(0.0))
    assert 0.2 <= core._cs_receipt_draw_spec([0.2, 0.4]) <= 0.4
    assert core._cs_receipt_draw_spec("bad") == pytest.approx(0.0)
    assert core._cs_receipt_count_draw([2, 3]) in {2, 3}
    assert core._cs_receipt_count_draw("bad") == 1
    assert core._cs_receipt_venue_sets([], 3) == [[], [], []]
    core._cs_ps_q_by_item_line = {
        "shellfish": {"prevalence": 1.0, "implicated_share": "bad"},
    }
    core._cs_ps_prevalence_scale = 1.0
    specs, scale = core._cs_receipt_line_specs(PATHOGEN, {"q_source": 0.0})
    assert specs["shellfish"] == pytest.approx(0.0)
    assert scale == pytest.approx(1.0)
