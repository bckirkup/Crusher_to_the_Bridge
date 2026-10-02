"""Tests for the ENV-SOURCE-01 hazard source-model hooks (ship_function_capacity_spec §8).

Covers declaration parsing and referential errors, the schedule window and
closed-form rate math, the ``uniform_outdoor`` penetration adapter resolving
to an ordinary emitter, the layered id-merge, the substance profile fragment
carrying pools through the environmental arm, and the paired-seed proof that
absent and present-but-disabled are bit-identical plus an armed smoke run.
"""

from __future__ import annotations

import math
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.hazard_sources import (
    merge_hazard_source_blocks,
    parse_hazard_sources,
)
from engines.sim_clock import SimClock

ZONES = ("Bridge", "MedBay", "Mess_Hall", "Engine_Room", "Galley", "Berthing")
PATHOGENS = frozenset({"norwalk_gi"})
CLOCK = SimClock(epoch_duration_hours=1.0, mode="hours")  # 1-hour epochs


def _substance(sid: str = "voc", **kw) -> dict:
    body = {
        "substance_id": sid,
        "environmental_contamination": {
            "source_zones": ["Engine_Room"],
            "spore_decay_rate_per_day": 0.5,
        },
        "parameters_provenance": "NULL-SOURCE: test arm",
    }
    body.update(kw)
    return body


def _emitter(eid: str = "e0", **kw) -> dict:
    body = {
        "emitter_id": eid,
        "substance_id": "voc",
        "kind": {"placement": "point", "field": "standing"},
        "zones": ["Engine_Room"],
        "rate": {
            "kind": "constant",
            "mass_per_hour": 10.0,
            "source": "NULL-SOURCE: test",
            "grade": "C",
        },
    }
    body.update(kw)
    return body


def _block(**kw) -> dict:
    body = {
        "enabled": True,
        "substances": [_substance()],
        "emitters": [_emitter()],
    }
    body.update(kw)
    return body


def _model(block: dict):
    return parse_hazard_sources(
        block, zone_names=ZONES, known_profile_ids=PATHOGENS, clock=CLOCK,
    )


# ── schedule window ─────────────────────────────────────────────────────


class TestScheduleWindow:
    def test_onset_gates_early_epochs(self) -> None:
        model = _model(_block(emitters=[_emitter(
            schedule={"start_epoch": 2},
        )]))
        assert model.epoch_deposits(0) == {}
        assert model.epoch_deposits(1) == {}
        assert model.epoch_deposits(2) == {"voc": {"Engine_Room": 10.0}}

    def test_duration_hours_bounds_and_partial_epoch(self) -> None:
        # 1.5-hour window: full deposit at onset, half a deposit next, then out.
        model = _model(_block(emitters=[_emitter(
            schedule={"start_epoch": 1, "duration_hours": 1.5},
        )]))
        assert model.epoch_deposits(0) == {}
        assert model.epoch_deposits(1) == {"voc": {"Engine_Room": 10.0}}
        assert model.epoch_deposits(2)["voc"]["Engine_Room"] == pytest.approx(5.0)
        assert model.epoch_deposits(3) == {}

    def test_introduction_epoch_alias(self) -> None:
        model = _model(_block(emitters=[_emitter(
            schedule={"introduction_epoch": 1},
        )]))
        assert model.epoch_deposits(0) == {}
        assert model.epoch_deposits(1) != {}


# ── rate math ───────────────────────────────────────────────────────────


class TestRateMath:
    def test_constant_integrates_to_hours(self) -> None:
        model = _model(_block(emitters=[_emitter()]))
        assert model.epoch_deposits(0) == {"voc": {"Engine_Room": 10.0}}

    def test_series_replays_per_epoch_and_ends(self) -> None:
        model = _model(_block(emitters=[_emitter(
            kind={"placement": "point", "field": "dynamic"},
            rate={
                "kind": "series",
                "series_per_hour": [5.0, 20.0],
                "source": "NULL-SOURCE: test", "grade": "C",
            },
        )]))
        assert model.epoch_deposits(0) == {"voc": {"Engine_Room": 5.0}}
        assert model.epoch_deposits(1) == {"voc": {"Engine_Room": 20.0}}
        assert model.epoch_deposits(2) == {}

    def test_exponential_decay_matches_closed_form(self) -> None:
        rate_mass, decay = 120.0, math.log(2.0)
        model = _model(_block(emitters=[_emitter(
            kind={"placement": "point", "field": "dynamic"},
            schedule={"duration_hours": 4},
            rate={
                "kind": "functional",
                "functional_form": "exponential_decay",
                "mass_per_hour": rate_mass,
                "decay_rate_per_hour": decay,
                "source": "NULL-SOURCE: test", "grade": "C",
            },
        )]))
        first = model.epoch_deposits(0)["voc"]["Engine_Room"]
        expected = rate_mass / decay * (1.0 - math.exp(-decay))
        assert first == pytest.approx(expected)
        # Half the rate each hour under a log(2) decay.
        second = model.epoch_deposits(1)["voc"]["Engine_Room"]
        assert second == pytest.approx(first / 2.0)

    def test_linear_ramp_piecewise(self) -> None:
        model = _model(_block(emitters=[_emitter(
            kind={"placement": "point", "field": "dynamic"},
            schedule={"duration_hours": 3},
            rate={
                "kind": "functional",
                "functional_form": "linear_ramp",
                "mass_per_hour": 100.0,
                "ramp_up_hours": 2.0,
                "source": "NULL-SOURCE: test", "grade": "C",
            },
        )]))
        # h∈[0,1): ∫ 100·h/2 dh = 25; h∈[1,2): 75; h∈[2,3): plateau 100.
        assert model.epoch_deposits(0)["voc"]["Engine_Room"] == pytest.approx(25.0)
        assert model.epoch_deposits(1)["voc"]["Engine_Room"] == pytest.approx(75.0)
        assert model.epoch_deposits(2)["voc"]["Engine_Room"] == pytest.approx(100.0)


# ── declaration validation ──────────────────────────────────────────────


class TestValidation:
    def _bad(self, **mut) -> dict:
        return _block(emitters=[_emitter(**mut)])

    def test_absent_block_returns_none(self) -> None:
        assert _model(None) is None

    def test_disabled_block_returns_none(self) -> None:
        assert _model(_block(enabled=False)) is None

    def test_malformed_still_raises_when_disabled(self) -> None:
        with pytest.raises(ValueError, match="unknown zones"):
            _model(_block(enabled=False, emitters=[_emitter(zones=["Nowhere"])]))

    @pytest.mark.parametrize("mut, match", [
        ({"emitter_id": ""}, "emitter_id"),
        ({"zones": ["Nowhere"]}, "unknown zones"),
        ({"zones": []}, "zones"),
        (
            {"zones": ["Engine_Room", "Galley"]},
            "'point' but declares 2 zones",
        ),
        ({"substance_id": "ghost"}, "no declared substance"),
        (
            {"rate": {"kind": "bogus", "source": "s", "grade": "C"}},
            "rate.kind",
        ),
        (
            {"rate": {"kind": "constant", "mass_per_hour": 1.0,
                      "grade": "C"}},
            "requires 'source'",
        ),
        (
            {"kind": {"placement": "point", "field": "standing"},
             "rate": {"kind": "series", "series_per_hour": [1.0],
                      "source": "s", "grade": "C"}},
            "'standing'.*constant",
        ),
        (
            {"kind": {"placement": "point", "field": "dynamic"},
             "rate": {"kind": "constant", "mass_per_hour": 1.0,
                      "source": "s", "grade": "C"}},
            "'dynamic'.*series.*functional|'series' or 'functional'",
        ),
        (
            {"kind": {"placement": "point", "field": "dynamic"},
             "rate": {"kind": "series", "source": "s", "grade": "C"}},
            "series_per_hour must be non-empty",
        ),
        (
            {"kind": {"placement": "point", "field": "dynamic"},
             "rate": {"kind": "functional", "functional_form": "spline",
                      "source": "s", "grade": "C"}},
            "functional_form",
        ),
        (
            {"schedule": {"start_epoch": -1}},
            "start_epoch",
        ),
        (
            {"schedule": {"duration_hours": 0}},
            "duration_hours",
        ),
    ])
    def test_emitter_errors(self, mut, match) -> None:
        with pytest.raises(ValueError, match=match):
            _model(self._bad(**mut))

    def test_duplicate_emitter_id(self) -> None:
        with pytest.raises(ValueError, match="duplicate emitter_id"):
            _model(_block(emitters=[_emitter(), _emitter()]))

    def test_substance_id_colliding_with_pathogen(self) -> None:
        with pytest.raises(ValueError, match="duplicate substance_id"):
            _model(_block(substances=[_substance("norwalk_gi")]))

    def test_substance_env_forbidden_and_unknown_keys(self) -> None:
        with pytest.raises(ValueError, match="person_to_person"):
            _model(_block(substances=[_substance(
                environmental_contamination={"person_to_person": True},
            )]))
        with pytest.raises(ValueError, match="unknown keys"):
            _model(_block(substances=[_substance(
                environmental_contamination={"infection_rate": 1.0},
            )]))

    def test_substance_requires_provenance(self) -> None:
        with pytest.raises(ValueError, match="parameters_provenance"):
            _model(_block(substances=[_substance(parameters_provenance="")]))

    def test_per_entry_kill_switch(self) -> None:
        model = _model(_block(
            emitters=[_emitter(), _emitter(eid="e1", enabled=False)],
        ))
        assert [e.emitter_id for e in model.emitters] == ["e0"]


# ── substance profile fragment ──────────────────────────────────────────


class TestSubstanceFragment:
    def test_fragment_is_pathogen_shaped_and_inert(self) -> None:
        model = _model(_block())
        frag = model.profile_fragments()["voc"]
        assert frag["hazard_substance"] is True
        assert frag["initial_infected"] is None
        env = frag["environmental_contamination"]
        assert env["enabled"] is True
        assert env["person_to_person"] is False
        assert env["spore_decay_rate_per_day"] == pytest.approx(0.5)
        # The exponential k=0 arm records dose without converting.
        assert frag["dose_response"] == {"model": "exponential", "k": 0.0}

    def test_emitter_may_target_a_pathogen_profile(self) -> None:
        model = _model(_block(
            substances=[],
            emitters=[_emitter(substance_id="norwalk_gi")],
        ))
        assert model.epoch_deposits(0) == {"norwalk_gi": {"Engine_Room": 10.0}}
        assert model.profile_fragments() == {}

    def test_transport_modes(self) -> None:
        model = _model(_block(
            substances=[
                _substance("voc"),
                _substance("standing_gas", transport="none",
                           environmental_contamination={}),
            ],
        ))
        assert model.transport_armed("voc") is True
        assert model.transport_armed("standing_gas") is False


# ── penetration adapter ─────────────────────────────────────────────────


def _penetration(**kw) -> dict:
    body = {
        "penetration_id": "pen0",
        "substance_id": "voc",
        "adapter": "uniform_outdoor",
        "zones": ["Galley"],
        "penetration_factor": 0.3,
        "outdoor_field": {"kind": "uniform", "concentration_per_hour": 40.0},
        "source": "NULL-SOURCE: test", "grade": "C",
    }
    body.update(kw)
    return body


class TestPenetrationAdapter:
    def test_uniform_resolves_to_standing_constant_emitter(self) -> None:
        model = _model(_block(
            emitters=[],
            penetrations=[_penetration()],
        ))
        (emitter,) = model.emitters
        assert emitter.emitter_id == "pen0"
        assert emitter.origin == "penetration:pen0"
        assert emitter.placement == "multipoint"
        assert emitter.field == "standing"
        # 40/h outdoor x 0.3 factor -> 12/h indoor emission.
        assert model.epoch_deposits(0) == {"voc": {"Galley": 12.0}}

    def test_series_field_resolves_to_dynamic_series(self) -> None:
        model = _model(_block(
            emitters=[],
            penetrations=[_penetration(outdoor_field={
                "kind": "series", "series_per_hour": [10.0, 20.0],
            })],
        ))
        (emitter,) = model.emitters
        assert emitter.field == "dynamic"
        assert emitter.rate.series_per_hour == (3.0, 6.0)

    def test_unknown_adapter_raises(self) -> None:
        with pytest.raises(ValueError, match="not a registered"):
            _model(_block(emitters=[], penetrations=[_penetration(
                adapter="quic_direct",
            )]))

    def test_series_field_requires_series(self) -> None:
        with pytest.raises(ValueError, match="series_per_hour"):
            _model(_block(emitters=[], penetrations=[_penetration(
                outdoor_field={"kind": "series"},
            )]))

    def test_penetration_ids_share_the_emitter_namespace(self) -> None:
        with pytest.raises(ValueError, match="duplicate emitter_id"):
            _model(_block(
                emitters=[_emitter(eid="pen0")],
                penetrations=[_penetration()],
            ))


# ── merge semantics ─────────────────────────────────────────────────────


class TestMerge:
    def test_same_id_entries_merge_key_by_key(self) -> None:
        base = _block(emitters=[
            _emitter(eid="a", rate={
                "kind": "constant", "mass_per_hour": 1.0,
                "source": "s", "grade": "C",
            }),
            _emitter(eid="b"),
        ])
        overlay = {"emitters": [_emitter(eid="a", rate={
            "kind": "constant", "mass_per_hour": 5.0,
            "source": "s", "grade": "C",
        })]}
        merged = merge_hazard_source_blocks(base, overlay)
        rates = {
            e["emitter_id"]: e["rate"]["mass_per_hour"]
            for e in merged["emitters"]
        }
        assert rates == {"a": 5.0, "b": 10.0}

    def test_enabled_resolves_to_last_declaring_layer(self) -> None:
        assert merge_hazard_source_blocks(
            {"enabled": True}, {},
        )["enabled"] is True
        assert merge_hazard_source_blocks(
            {"enabled": True}, {"enabled": False},
        )["enabled"] is False

    def test_later_layer_can_arm_a_disabled_block(self) -> None:
        base = _block(enabled=False)
        merged = merge_hazard_source_blocks(base, {"enabled": True})
        model = _model(merged)
        assert model is not None
        assert model.epoch_deposits(0) == {"voc": {"Engine_Room": 10.0}}


# ── end-to-end on the smoke spec ────────────────────────────────────────


def _smoke_spec(hazard_block):
    from picard_framework import PicardRunSpec

    spec = PicardRunSpec.from_picard_json(
        REPO_ROOT, "picard_framework/runs/smoke_2epoch.json",
    )
    if hazard_block is None:
        spec.legacy_cfg.pop("hazard_sources", None)
    else:
        spec.legacy_cfg["hazard_sources"] = hazard_block
    return spec


def _armed_block() -> dict:
    return {
        "enabled": True,
        "substances": [_substance()],
        "emitters": [_emitter(
            schedule={"start_epoch": 0, "duration_hours": 48},
        )],
    }


@pytest.mark.timeout(300)
def test_disabled_block_is_bit_identical_to_absent() -> None:
    """Paired seeded smoke: declared-and-off must equal never-declared."""
    from picard_framework import ShipSimulation

    run_off = ShipSimulation(
        _smoke_spec(_block(enabled=False)),
        display=False, repo_root=REPO_ROOT,
    ).run()
    run_absent = ShipSimulation(
        _smoke_spec(None), display=False, repo_root=REPO_ROOT,
    ).run()
    assert run_off.history == run_absent.history


@pytest.mark.timeout(300)
def test_armed_sources_deposit_and_transport() -> None:
    """An armed substance writes into env_contamination and moves with the
    armed airflow transport on the destroyer smoke platform."""
    from picard_framework import ShipSimulation

    sim = ShipSimulation(
        _smoke_spec(_armed_block()), display=False, repo_root=REPO_ROOT,
    )
    run = sim.run()
    # The substance registered as an inert profile.
    assert sim.pathogen_profiles["voc"]["hazard_substance"] is True
    assert sim.hazard_model is not None
    # A 10/h constant source deposits 10 per 1-hour epoch at the emitter zone.
    assert sim.hazard_model.epoch_deposits(0) == {
        "voc": {"Engine_Room": 10.0},
    }
    assert sim.tx_core is not None
    pool = sim.tx_core.env_contamination.get("voc", {})
    assert pool, "armed emitter wrote nothing into env_contamination"
    # The armed airflow transport carries the field: every network zone holds
    # mass, and the emitter zone anchors the largest share.
    assert max(pool, key=pool.get) == "Engine_Room"
    assert len(pool) > 1
    assert all(m > 0.0 for m in pool.values())
    assert run.history
