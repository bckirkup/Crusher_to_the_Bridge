"""Fleet audit invariants for sanitary makeup direction (D1)."""

from __future__ import annotations

from tools.diag import forced_exhaust_audit


def test_sanitary_makeup_links_are_oneway_with_no_native_reverse() -> None:
    rows, summary = forced_exhaust_audit.build_audit()

    assert summary["reconciliation"]["reconciled"] is True
    sanitary = [row for row in rows if row["path"] == "Sanitary_Makeup"]
    # 587 -> 625: CONTAM-GROUPED-WEATHER-AUXILIARY-01 split group-addressed
    # Sanitary_Makeup links for opened weather zones, preserving per-room-pair flow;
    # CONTAM-GROUPED-WEATHER-AMPHIBIOUS-01 adds two more San Antonio legs.
    assert len(sanitary) == 627
    assert summary["fleet"]["sanitary_makeup_links"] == 627
    assert all(row["direction_declared"] == "oneway" for row in sanitary)
    assert all(row["native_reverse_paths"] == 0 for row in sanitary)
    assert not any(
        forced_exhaust_audit.FLAG_REVERSE in row["flags"].split(";")
        for row in sanitary
    )


GALLEY_PATHS = {
    "Dining_Galley_Exhaust",
    "Galley_Service_Exhaust",
    "Galley_Exhaust_Return",
    "galley_exhaust_to_mess",
}


def test_galley_class_links_report_no_native_reverse_on_stated_oneway() -> None:
    rows, _summary = forced_exhaust_audit.build_audit()

    galley = [row for row in rows if row["path"] in GALLEY_PATHS]
    assert len(galley) == 9
    assert all(row["direction_declared"] == "oneway" for row in galley)
    assert all(row["native_reverse_paths"] == 0 for row in galley)
    assert not any(
        forced_exhaust_audit.FLAG_REVERSE in row["flags"].split(";")
        for row in galley
    )


def test_pressure_directed_class_links_report_no_native_reverse_on_stated_oneway() -> None:
    rows, _summary = forced_exhaust_audit.build_audit()

    pressure_directed = [
        row for row in rows if row["intent_class"] == "pressure_directed"
    ]
    assert len(pressure_directed) == 7
    assert all(row["direction_declared"] == "oneway" for row in pressure_directed)
    assert all(row["native_reverse_paths"] == 0 for row in pressure_directed)
    assert not any(
        forced_exhaust_audit.FLAG_REVERSE in row["flags"].split(";")
        for row in pressure_directed
    )
