"""Unit tests for the NORO-VENUE-01 placement census pure functions.

These cover the landing-site classifier and the emit x confinement join
classification — the parts of ``tools/noro_diag/venue_placement_census.py``
that carry the deliverable's semantics — without running a voyage.
"""

from __future__ import annotations

import argparse

import pytest

from tools.noro_diag.venue_placement_census import (
    ADMIT_ACTIONS,
    ORDER_ACTIONS,
    VenueRecorder,
    _emit_confinement_class,
    _emitter_class,
    _host_timeline,
    _join_emits,
    _seed_list,
    classify_site,
)
from tools.diag.readout_common import wilson_interval


def _zone(ztype: str, deck: str = "4_Pax", service: str = "") -> dict:
    rec: dict[str, object] = {"name": "Z", "type": ztype, "deck": deck}
    if service:
        rec["dining_service_type"] = service
    return rec


class TestClassifySite:
    def test_compartment_key_is_own_stateroom(self) -> None:
        out = classify_site("PC_D4-11_A::cabin0123", None)
        assert out["site_class"] == "own_stateroom"
        assert out["site_group"] == "stateroom_pax"
        out = classify_site("CC_D1-3_A::cabin0042", None)
        assert out["site_class"] == "own_stateroom"
        assert out["site_group"] == "stateroom_crew"

    def test_dining_split_by_service_type(self) -> None:
        pax = classify_site("MainDiningRoom", _zone("Dining", service="mdr"))
        assert (pax["site_class"], pax["site_group"]) == (
            "shared_venue", "dining_pax",
        )
        crew = classify_site(
            "CrewMessMain", _zone("Dining", "1_Crew", "crew_mess"),
        )
        assert (crew["site_class"], crew["site_group"]) == (
            "crew_only", "dining_crew",
        )
        galley = classify_site(
            "MainGalley", _zone("Dining", "4_Pax", "galley"),
        )
        assert galley["site_class"] == "crew_only"

    def test_sanitary_split_by_deck(self) -> None:
        pax = classify_site("HD_D7_FWD", _zone("Sanitary", "7_Pax"))
        assert (pax["site_class"], pax["site_group"]) == (
            "shared_venue", "toilet_pax",
        )
        crew = classify_site("HD_D2_FWD", _zone("Sanitary", "2_Crew"))
        assert (crew["site_class"], crew["site_group"]) == (
            "crew_only", "toilet_crew",
        )

    def test_medical_and_offgrid(self) -> None:
        med = classify_site("MedCenter", _zone("Medical", "4_Pax"))
        assert med["site_class"] == "medical"
        for loc in ("Ashore", "Departed", "Isolated_In_Quarters"):
            assert classify_site(loc, None)["site_class"] == "off_grid"

    def test_nonleisure_tokens_and_crew_decks(self) -> None:
        eng = classify_site("Engine_Room", _zone("Service", "0_Engine"))
        assert eng["site_class"] == "crew_only"
        laundry = classify_site("Laundry_A", _zone("Service", "4_Pax"))
        assert laundry["site_class"] == "crew_only"

    def test_free_zone_is_shared_venue(self) -> None:
        out = classify_site("Theatre_Main", _zone("Free", "6_Pax"))
        assert out["site_class"] == "shared_venue"
        assert out["site_group"] == "venue_free"


def _row(epoch: int, confined: bool) -> dict:
    return {"epoch": epoch, "confined_at_emit": confined}


def _timeline(
    order: int | None, refusals: list[int] | None = None,
) -> dict:
    return {
        "first_order_epoch": order,
        "first_admit_event_epoch": None,
        "refusal_epochs": refusals or [],
        "release_epochs": [],
        "actions": [],
    }


class TestEmitConfinementClass:
    def test_confined_at_emit(self) -> None:
        cls, sub = _emit_confinement_class(
            _row(10, True), _timeline(9), [10, 11],
        )
        assert (cls, sub) == ("post_confinement", "confined")

    def test_ordered_mobile_window(self) -> None:
        cls, sub = _emit_confinement_class(
            _row(10, False), _timeline(10), [11, 12],
        )
        assert (cls, sub) == ("pre_confinement", "ordered_mobile")

    def test_pre_order(self) -> None:
        cls, sub = _emit_confinement_class(
            _row(5, False), _timeline(9), [9, 10],
        )
        assert (cls, sub) == ("pre_confinement", "pre_order")

    def test_never_confined_variants(self) -> None:
        cls, sub = _emit_confinement_class(_row(7, False), _timeline(None), None)
        assert (cls, sub) == ("never_confined", "never_ordered")
        cls, sub = _emit_confinement_class(
            _row(7, False), _timeline(5, refusals=[5]), None,
        )
        assert (cls, sub) == ("never_confined", "ordered_refused")
        cls, sub = _emit_confinement_class(
            _row(7, False), _timeline(5), None,
        )
        assert (cls, sub) == ("never_confined", "ordered_never_admitted")

    def test_emit_after_first_confined_but_unconfined(self) -> None:
        # Released mid-voyage: has confined epochs strictly before emit.
        cls, sub = _emit_confinement_class(
            _row(20, False), _timeline(9), [9, 10],
        )
        assert cls == "never_confined_at_emit"
        assert sub == "ordered_not_admitted"


class TestEmitterClass:
    def _rec(self, symptomatic: bool, will_present: object) -> object:
        from tools.noro_diag.venue_placement_census import VenueRecorder
        rec = VenueRecorder(pathogen_id="norwalk_gi")
        if symptomatic:
            rec.ever_symptomatic.add(7)
        rec.host_meta[7] = {"will_present": will_present}
        return rec

    def test_three_way_split(self) -> None:
        assert _emitter_class(
            self._rec(True, True), 7,
        ) == "symptomatic_onboard"
        assert _emitter_class(
            self._rec(False, False), 7,
        ) == "never_symptomatic_course"
        assert _emitter_class(
            self._rec(False, True), 7,
        ) == "never_symptomatic_onboard"


class TestEscortActions:
    def test_escort_actions_classified(self) -> None:
        assert "escort_order" in ORDER_ACTIONS
        assert "escorted_admission" in ADMIT_ACTIONS
        assert "escort_order" not in ADMIT_ACTIONS
        assert "escorted_admission" not in ORDER_ACTIONS

    def test_host_timeline_carries_escort_due(self) -> None:
        rec = VenueRecorder(pathogen_id="norwalk_gi")
        rec.confinement_events.extend([
            {
                "epoch": 10, "agent_id": 7, "action": "escort_order",
                "compliance_class": "compliant", "escort_due_epoch": 12,
            },
            {
                "epoch": 12, "agent_id": 7, "action": "escorted_admission",
                "compliance_class": "compliant",
            },
        ])
        timeline = _host_timeline(rec, 7)
        assert timeline["first_order_epoch"] == 10
        assert timeline["first_admit_event_epoch"] == 12
        assert timeline["escort_due_epochs"] == [12]


class TestFirstEmitJoin:
    def _rec(self) -> VenueRecorder:
        rec = VenueRecorder(pathogen_id="norwalk_gi")
        rec.emesis_rows.extend([
            {"epoch": 11, "agent_id": 7, "zone": "Theatre",
             "confined_at_emit": False},
            {"epoch": 12, "agent_id": 7, "zone": "PC_D4::cabin0001",
             "confined_at_emit": True},
            {"epoch": 12, "agent_id": 8, "zone": "Theatre",
             "confined_at_emit": False},
        ])
        rec.confinement_events.extend([
            {"epoch": 10, "agent_id": 7, "action": "escort_order",
             "compliance_class": "compliant", "escort_due_epoch": 12},
            {"epoch": 12, "agent_id": 7, "action": "escorted_admission",
             "compliance_class": "compliant"},
        ])
        rec.confined_membership.extend([
            {"epoch": 11, "ids": []},
            {"epoch": 12, "ids": [7]},
        ])
        rec.host_meta[7] = {"will_present": True}
        rec.host_meta[8] = {"will_present": True}
        rec.ever_symptomatic.update({7, 8})
        return rec

    def test_first_emit_flag_and_mobile_class(self) -> None:
        rows, unattributed = _join_emits(self._rec(), {})
        assert unattributed == 0
        by_agent = {}
        for row in rows:
            by_agent.setdefault(row["agent_id"], []).append(row)
        firsts = [r for r in by_agent[7] if r["first_emit"]]
        assert len(firsts) == 1
        assert firsts[0]["epoch"] == 11
        assert firsts[0]["confinement_class"] == "pre_confinement"
        assert firsts[0]["order_subclass"] == "ordered_mobile"
        assert firsts[0]["site_class"] == "shared_venue"
        assert [r["first_emit"] for r in by_agent[8]] == [True]


class TestHelpers:
    def test_seed_list(self) -> None:
        assert _seed_list("8105, 8114,,8159") == [8105, 8114, 8159]
        with pytest.raises(argparse.ArgumentTypeError):
            _seed_list("not-a-seed")

    def test_wilson_bounds(self) -> None:
        lo, hi = wilson_interval(0, 0)
        assert (lo, hi) == (0.0, 0.0)
        lo, hi = wilson_interval(4, 10)
        assert 0.0 < lo < 0.4 < hi < 1.0
        lo, hi = wilson_interval(10, 10)
        assert hi <= 1.0
        assert lo > 0.5
