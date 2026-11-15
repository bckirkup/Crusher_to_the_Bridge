"""FOOD-SUPPLY-01 receipt/lot layer gates.

The receipt layer sits above the PROVISIONED-SOURCE-01 station census:
``station_lots`` remains the bit-identical baseline, while
``single_line_receipt`` / ``declared_receipts`` mint supply receipts with
per-item-line prevalence, preparation-class filtering, and shared-lot
correlation across venues. These tests pin the default-off contract only;
they do not fit any epidemiological anchor.
"""

from __future__ import annotations

from engines.transmission_core import COMMON_SOURCE_LOT_ITEM_LINES
from tests.test_common_source_events import PATHOGEN, ZONE, _core, _diner
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
