"""Sentinel line list: onset survives retention, exposure has a denominator.

Graded checks (see docs/ci-test-design): invariants on the ledger's folding
rules, then a handful of labeled golden values as change detectors.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.export_line_list import (
    ledger_from_history,
    port_id_lookup,
)
from picard_framework.analysis.sentinel.line_list import (
    CHANNEL_PRIORITY,
    SentinelLedger,
    active_pathogen,
    agent_is_crew,
)
from picard_framework.analysis.sentinel.observations import bundle_from_dict


def agent(
    aid: int,
    *,
    symptomatic: bool = False,
    crew: bool = False,
    location: str = "Cabin_1",
    pathogen: str | None = None,
) -> dict[str, Any]:
    """Minimal agent record in the shape the orchestrator builds."""
    record: dict[str, Any] = {
        "agent_id": aid,
        "infection_state": "infected" if symptomatic else "susceptible",
        "symptom_presentation": "symptomatic" if symptomatic else "asymptomatic",
        "location": location,
        "agent_class": "crew_enlisted" if crew else "passenger",
        "role": "crew" if crew else "passenger",
    }
    if pathogen:
        record["pathogen_infections"] = {
            pathogen: {"status": "INFECTED", "illness": "SYMPTOMATIC"},
        }
    return record


VOYAGE_CFG: dict[str, Any] = {
    "voyage": {
        "enabled": True,
        "epoch_duration_hours": 1,
        "itinerary": [
            {"day": 1, "type": "embarkation", "port": "Miami"},
            {
                "day": 2,
                "type": "port_day",
                "port": "Cozumel",
                "port_id": "MXCZM",
                "disembark_window_epochs": [2, 3],
                "reembark_window_epochs": [8, 9],
            },
            {"day": 3, "type": "disembarkation", "port": "Miami"},
        ],
    },
}


# ── Onset ────────────────────────────────────────────────────────────

def test_first_symptomatic_epoch_is_the_onset() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(3, [agent(1)])
    ledger.observe_epoch(4, [agent(1, symptomatic=True)])
    ledger.observe_epoch(5, [agent(1, symptomatic=True)])
    (row,) = ledger.records()
    assert row.onset_epoch == 4


def test_onset_is_not_overwritten_by_later_relapse() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(2, [agent(1, symptomatic=True)])
    ledger.observe_epoch(3, [agent(1)])
    ledger.observe_epoch(9, [agent(1, symptomatic=True)])
    (row,) = ledger.records()
    assert row.onset_epoch == 2


def test_epoch_zero_is_clamped_to_voyage_day_one() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(0, [agent(1, symptomatic=True)], detections={"sick_call": [1]})
    (row,) = ledger.records()
    assert (row.onset_epoch, row.report_epoch) == (1, 1)


def test_never_symptomatic_person_has_no_row() -> None:
    ledger = SentinelLedger()
    for epoch in (1, 2, 3):
        ledger.observe_epoch(epoch, [agent(1), agent(2)])
    assert ledger.records() == ()


def test_rows_are_sorted_by_onset_then_person() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(2, [agent(7, symptomatic=True), agent(3, symptomatic=True)])
    ledger.observe_epoch(1, [agent(9, symptomatic=True)])
    ids = [r.person_id for r in ledger.records()]
    assert ids == ["9", "3", "7"]


# ── Crew / passenger and pathogen ────────────────────────────────────

def test_crew_status_is_preserved() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(1, [agent(1, symptomatic=True, crew=True), agent(2, symptomatic=True)])
    flags = {r.person_id: r.crew for r in ledger.records()}
    assert flags == {"1": True, "2": False}


def test_crew_falls_back_to_agent_class_when_role_absent() -> None:
    record = agent(1, crew=True)
    del record["role"]
    assert agent_is_crew(record) is True


def test_pathogen_is_nullable_and_genotype_is_none_until_strains_exist() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(1, [agent(1, symptomatic=True)])
    ledger.observe_epoch(1, [agent(2, symptomatic=True, pathogen="norovirus_gii4")])
    rows = {r.person_id: r for r in ledger.records()}
    assert rows["1"].pathogen is None
    assert rows["2"].pathogen == "norovirus_gii4"
    assert all(r.genotype is None for r in rows.values())


def test_recovered_infection_is_not_reported_as_active_pathogen() -> None:
    record = agent(1, symptomatic=True)
    record["pathogen_infections"] = {"norovirus": {"status": "RECOVERED"}}
    assert active_pathogen(record) is None


# ── Exposure denominators ────────────────────────────────────────────

def test_ashore_hours_accumulate_per_port_and_scale_with_epoch_duration() -> None:
    ledger = SentinelLedger(epoch_duration_hours=4.0)
    for epoch in (3, 4):
        ledger.observe_epoch(
            epoch, [agent(1, symptomatic=True)], port_id="MXCZM", ashore_ids=[1],
        )
    ledger.observe_epoch(
        7, [agent(1, symptomatic=True)], port_id="KYGEC", ashore_ids=[1],
    )
    (row,) = ledger.records()
    assert row.hours_ashore == {"MXCZM": 8.0, "KYGEC": 4.0}


def test_sea_day_epochs_add_no_exposure() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(1, [agent(1, symptomatic=True)], port_id="", ashore_ids=[1])
    assert ledger.exposure_totals() == {}
    assert ledger.records()[0].hours_ashore == {}


def test_exposure_totals_split_crew_from_passengers() -> None:
    ledger = SentinelLedger(epoch_duration_hours=2.0)
    agents = [agent(1), agent(2), agent(3, crew=True)]
    ledger.observe_epoch(4, agents, port_id="MXCZM", ashore_ids=[1, 2, 3])
    assert ledger.exposure_totals() == {
        "MXCZM": {
            "person_hours_passenger": 4.0,
            "person_hours_crew": 2.0,
            "n_passengers_ashore": 2,
            "n_crew_ashore": 1,
        },
    }


def test_ashore_people_without_onset_still_count_toward_the_denominator() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(4, [agent(1), agent(2)], port_id="MXCZM", ashore_ids=[1, 2])
    assert ledger.records() == ()
    assert ledger.exposure_totals()["MXCZM"]["person_hours_passenger"] == 2.0


# ── Reporting channel ────────────────────────────────────────────────

def test_strongest_channel_wins_regardless_of_arrival_order() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(
        2, [agent(1, symptomatic=True)], detections={"wearable": [1]},
    )
    ledger.observe_epoch(
        3, [agent(1, symptomatic=True)], detections={"sick_call": [1]},
    )
    (row,) = ledger.records()
    assert row.reported_via == "sick_call"
    assert row.report_epoch == 3


def test_channel_priority_order_is_the_documented_one() -> None:
    assert CHANNEL_PRIORITY == ("sick_call", "screening", "cascade", "wearable")


def test_case_with_no_detection_is_unreported() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(2, [agent(1, symptomatic=True)])
    (row,) = ledger.records()
    assert row.reported_via == "unreported"
    assert row.report_epoch is None


def test_report_epoch_is_never_before_onset() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(2, [agent(1)], detections={"wearable": [1]})
    ledger.observe_epoch(5, [agent(1, symptomatic=True)])
    (row,) = ledger.records()
    assert row.report_epoch >= row.onset_epoch


def test_unknown_channel_is_rejected() -> None:
    ledger = SentinelLedger()
    with pytest.raises(ValueError, match="Unknown detection channel"):
        ledger.observe_epoch(1, [agent(1)], detections={"telepathy": [1]})


# ── Ground truth (synthetic runs only) ───────────────────────────────

def test_introductions_are_ordered_and_absent_by_default() -> None:
    ledger = SentinelLedger()
    assert ledger.introductions() == ()
    assert "truth_introductions" not in ledger.to_payload(voyage_id="V1", ship_id="s1")

    ledger.note_introduction(person_id="7", epoch=5, port_id="MXCZM", pathogen="norovirus")
    ledger.note_introduction(person_id="3", epoch=5, port_id="MXCZM")
    ledger.note_introduction(person_id="9", epoch=2, port_id="KYGEC")
    assert [(r.person_id, r.epoch) for r in ledger.introductions()] == [
        ("9", 2), ("3", 5), ("7", 5),
    ]
    assert ledger.introductions()[1].pathogen is None
    payload = ledger.to_payload(voyage_id="V1", ship_id="s1")
    assert payload["truth_introductions"][0]["port_id"] == "KYGEC"


def test_introduction_epoch_is_clamped_like_observations() -> None:
    ledger = SentinelLedger()
    ledger.note_introduction(person_id="1", epoch=0, port_id="MXCZM")
    assert ledger.introductions()[0].epoch == 1


# ── Payload / schema round trip ──────────────────────────────────────

def test_payload_round_trips_through_the_observation_loader() -> None:
    ledger = SentinelLedger()
    ledger.observe_epoch(
        4,
        [agent(1, symptomatic=True, pathogen="norovirus"), agent(2, crew=True)],
        port_id="MXCZM",
        ashore_ids=[1, 2],
        detections={"sick_call": [1]},
    )
    payload = ledger.to_payload(
        voyage_id="V1", ship_id="ship_a", n_passengers=10, n_crew=4,
    )
    bundle = bundle_from_dict(payload)
    assert bundle.voyage_id == "V1"
    assert [c.person_id for c in bundle.clinical_cases] == ["1"]
    assert bundle.clinical_cases[0].hours_ashore["MXCZM"] == 1.0
    assert bundle.exposure_totals["MXCZM"]["n_crew_ashore"] == 1.0
    assert bundle.observation_end_epoch == 4


def test_payload_is_json_serialisable_and_schema_valid(tmp_path: Any) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(
        os.path.join(repo_root, "schemas", "sentinel_observations.schema.json"),
        encoding="utf-8",
    ) as handle:
        schema = json.load(handle)
    ledger = SentinelLedger()
    ledger.observe_epoch(
        2,
        [agent(1, symptomatic=True)],
        port_id="MXCZM",
        ashore_ids=[1],
        detections={"screening": [1]},
    )
    payload = json.loads(json.dumps(ledger.to_payload(voyage_id="V1", ship_id="s1")))
    jsonschema.validate(payload, schema)


# ── History replay (retrospective path) ──────────────────────────────

HISTORY: list[dict[str, Any]] = [
    {
        "epoch": 1,
        "voyage_epoch": {"port": "Miami", "day_type": "embarkation"},
        "agents": [agent(1), agent(2, crew=True)],
    },
    {
        "epoch": 2,
        "voyage_epoch": {"port": "Cozumel", "day_type": "port_day"},
        "agents": [agent(1, location="Ashore"), agent(2, crew=True, location="Ashore")],
    },
    {
        "epoch": 3,
        "voyage_epoch": {"port": "Cozumel", "day_type": "port_day"},
        "agents": [agent(1, location="Ashore"), agent(2, crew=True)],
        "wearable_monitoring": {"staff_visible_agents": [1]},
    },
    {
        "epoch": 4,
        "voyage_epoch": {"port": "", "day_type": "sea_day"},
        "agents": [agent(1, symptomatic=True, pathogen="norovirus"), agent(2, crew=True)],
        "diagnostic_cascade": {"new_tier0_agents": [1], "new_tier1_agents": []},
    },
]


def test_history_replay_recovers_onset_exposure_and_channel() -> None:
    ledger = ledger_from_history(HISTORY, port_ids=port_id_lookup(VOYAGE_CFG))
    (row,) = ledger.records()
    assert row.onset_epoch == 4
    assert row.hours_ashore == {"MXCZM": 2.0}
    assert row.reported_via == "cascade"
    assert row.pathogen == "norovirus"


def test_history_replay_uses_port_ids_from_the_voyage_config() -> None:
    lookup = port_id_lookup(VOYAGE_CFG)
    # The home port is a port call too; with no declared code it slugifies.
    assert lookup == {"Cozumel": "MXCZM", "Miami": "miami"}
    unmapped = ledger_from_history(HISTORY)
    assert set(unmapped.exposure_totals()) == {"cozumel"}


def test_home_port_code_keys_the_ledger_when_declared() -> None:
    """Ashore hours at the home port must key on its code, not a name slug.

    This is what lets the exposure model resolve the pier the voyage starts and
    ends on instead of rejecting the bundle as an unknown port.
    """
    cfg = copy.deepcopy(VOYAGE_CFG)
    for day in cfg["voyage"]["itinerary"]:
        if day.get("port") == "Miami":
            day["port_id"] = "USMIA"
    assert port_id_lookup(cfg) == {"Cozumel": "MXCZM", "Miami": "USMIA"}


def test_compact_history_yields_nothing_which_is_why_the_ledger_exists() -> None:
    compact = [{"epoch": e, "summary": {"infected": 1}} for e in (1, 2, 3)]
    ledger = ledger_from_history(compact)
    assert ledger.records() == ()
    assert ledger.exposure_totals() == {}


def test_history_replay_is_deterministic() -> None:
    first = ledger_from_history(HISTORY).to_payload(voyage_id="V", ship_id="s")
    second = ledger_from_history(HISTORY).to_payload(voyage_id="V", ship_id="s")
    assert first == second
