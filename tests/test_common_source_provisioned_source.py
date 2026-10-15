"""PROVISIONED-SOURCE-01 — the provisioned_source lot mint model.

Contract: docs/provisioned_source_01_design.md. Under
``lot_mint_model: "provisioned_source"`` the fiat voyage gate is
replaced by a derived census: every served Dining venue x
``COMMON_SOURCE_LOT_ITEM_LINES`` station draws one Bernoulli
``u_s < q_source`` on the shared ``_cs_rng`` stream, in canonical
order, and each contaminated station mints exactly one lot object.

The §4 integrity gates pinned here:

* fiat bit-identity — explicit ``"fiat"`` resolves the fiat grammar,
  whose voyage-rate draws replay verbatim on a twin stream; absent
  ``lot_mint_model`` resolves ``"provisioned_source"``, the shipped
  default;
* nested contaminated-station sets across scalar q rungs;
* objects per voyage ~ Binomial(N_lots, q_source);
* the station witness — object (zone, item) pairs are the census and
  every row carries ``provisioned_source_id``;
* worker/diner arms untouched — agent objects keep
  ``provisioned_source_id: None``.
"""

import numpy as np
import pytest

from engines.transmission_core import (
    _COMMON_SOURCE_STREAM_KEY,
    COMMON_SOURCE_LOT_ITEM_LINES,
    ContactTracingMatrix,
    TransmissionCore,
)
from tests.test_common_source_events import (
    PATHOGEN,
    ZONE,
    _core,
    _diner,
    _handler,
)
from tests.test_common_source_lot_objects import (
    _object_cfg,
    _step_objects,
    _strain_core,
)

SOURCE_ID = "generic_cruise_port"


def _ps_cfg(q_source: object = 0.5, **overrides: object) -> dict:
    """Armed object-mode cfg on the provisioned_source grammar."""
    cs: dict[str, object] = {
        "mode": "on",
        "lot_mode": "object",
        "lot_mint_model": "provisioned_source",
        "provisioned_source": {
            "source_id": SOURCE_ID,
            "q_source": q_source,
        },
        # Keep the worker arms inert so the census is the only mint.
        "handler_mode": "independent",
        "diner_mode": "independent",
        "handler_event_probability": 0.0,
        "diner_event_probability": 0.0,
    }
    cs.update(overrides)
    return cs


def _fiat_cfg_interval_rates() -> dict:
    """The fiat grammar with its rate keys left at module intervals so
    the voyage draws actually consume stream uniforms."""
    cs = _object_cfg()
    cs.pop("lot_object_probability", None)
    cs.pop("extra_lot_probability", None)
    return cs


def _twin(seed: int = 7) -> np.random.Generator:
    """Replay the ``_cs_rng`` stream the engine builds for ``seed``."""
    entropy = np.random.default_rng(seed).bit_generator.seed_seq.entropy
    return np.random.default_rng(
        np.random.SeedSequence(entropy, spawn_key=(_COMMON_SOURCE_STREAM_KEY,))
    )


def _plan(core: TransmissionCore, agents: list) -> None:
    """Drive one epoch so the lot plan schedules (first armed epoch)."""
    core._agents_by_id = {a.agent_id: a for a in agents}
    matrix = ContactTracingMatrix(epoch=0)
    core._pathway_common_source(
        0, {ZONE: agents}, {}, matrix, {},
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )


# ── Gate: absent resolves fiat; fiat grammar draws verbatim ─────────

def test_absent_lot_mint_model_resolves_provisioned_source() -> None:
    """An unmarked config takes the shipped default — absent resolves
    ``"provisioned_source"``; only a spelled ``"fiat"`` keeps the v1
    grammar."""
    cfg = _object_cfg()
    cfg.pop("lot_mint_model", None)
    core = _core(cfg_cs=cfg)
    assert core._cs_lot_mint_model == "provisioned_source"


def test_absent_cfg_runs_the_provisioned_grammar() -> None:
    """Absent and explicit "provisioned_source" produce identical
    objects — the unmarked config runs the census grammar with the
    registry default source and interval."""
    cfg_absent = _object_cfg()
    cfg_absent.pop("lot_mint_model", None)
    cfg_absent.pop("lot_object_probability", None)
    cfg_absent.pop("extra_lot_probability", None)
    core_absent = _core(cfg_cs=cfg_absent)
    core_ps = _core(cfg_cs=_ps_cfg(None))
    assert core_absent._cs_ps_source_id == SOURCE_ID
    assert core_absent._cs_rates[PATHOGEN]["q_source"] == (
        core_ps._cs_rates[PATHOGEN]["q_source"])
    _, _, obj_absent, _ = _step_objects(
        core_absent, [_diner(i) for i in range(1, 40)])
    _, _, obj_ps, _ = _step_objects(
        core_ps, [_diner(i) for i in range(1, 40)])
    assert obj_absent == obj_ps
    for row in obj_ps:
        assert row["provisioned_source_id"] == SOURCE_ID


def test_fiat_voyage_rates_replay_the_shipped_sequence() -> None:
    """Gate 1 support: under fiat the voyage-rate draws are the v1
    pair — lot_object_probability then extra_lot_probability — at the
    first two stream positions, replayed verbatim on a twin stream."""
    twin = _twin()
    expected_gate = twin.uniform(0.001, 0.02)
    expected_extra = twin.uniform(0.02, 0.25)
    core = _core(cfg_cs=_fiat_cfg_interval_rates())
    rates = core._cs_rates[PATHOGEN]
    assert rates["lot_object_probability"] == pytest.approx(expected_gate)
    assert rates["extra_lot_probability"] == pytest.approx(expected_extra)
    assert "q_source" not in rates


# ── Gate: the provisioned_source voyage draw ────────────────────────

def test_q_source_draws_at_the_first_lot_rate_slot() -> None:
    """Interval q_source is the voyage's first lot-rate draw — the
    declared position the fiat gate pair occupied."""
    twin = _twin()
    expected_q = twin.uniform(0.2, 0.4)
    core = _core(cfg_cs=_ps_cfg([0.2, 0.4]))
    rates = core._cs_rates[PATHOGEN]
    assert rates["q_source"] == pytest.approx(expected_q)
    assert "lot_object_probability" not in rates
    assert "extra_lot_probability" not in rates


def test_q_source_scalar_is_a_rung_not_a_draw() -> None:
    """A scalar rung consumes no uniform — the same _cs_draw early
    return every other common-source scalar uses."""
    core = _core(cfg_cs=_ps_cfg(0.3))
    assert core._cs_rates[PATHOGEN]["q_source"] == pytest.approx(0.3)


def test_registry_resolves_source_id_and_q_interval() -> None:
    """A null q_source in the block resolves through the named registry
    entry's declared interval; an absent source_id resolves the
    registry default."""
    core = _core(cfg_cs=_ps_cfg(None))
    assert core._cs_ps_source_id == SOURCE_ID
    q = core._cs_rates[PATHOGEN]["q_source"]
    assert q >= 0.0002
    assert q <= 0.0005


def test_station_census_is_served_zones_times_item_lines() -> None:
    core = _core(cfg_cs=_ps_cfg(0.5))
    assert core._cs_station_census([ZONE]) == [
        (ZONE, item) for item in COMMON_SOURCE_LOT_ITEM_LINES
    ]


# ── Gate: Binomial(N, q) counts and the voyage witness ──────────────

def test_q_one_mints_every_station_and_witnesses_the_voyage() -> None:
    """q_source = 1 → every station mints exactly once: the objects
    ARE the census, one row per (zone, item) station."""
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_ps_cfg(1.0))
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["source_id"] == SOURCE_ID
    assert witness["q_source_drawn"] == pytest.approx(1.0)
    assert witness["n_stations"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_contaminated"] == len(COMMON_SOURCE_LOT_ITEM_LINES)
    stations = {
        (o["zone"], o["item_label"]) for o in core._cs_objects[PATHOGEN]
    }
    assert stations == set(core._cs_station_census([ZONE]))


def test_q_zero_mints_nothing() -> None:
    core = _core(cfg_cs=_ps_cfg(0.0))
    _plan(core, [_diner(i) for i in range(1, 40)])
    assert core._cs_provisioned_source[PATHOGEN]["n_contaminated"] == 0
    assert not core._cs_objects.get(PATHOGEN)


def test_contaminated_counts_track_binomial() -> None:
    """E[objects] = N * q: over 120 seeds the mean contaminated count
    sits within a few standard errors of the Binomial mean — a graded
    sensitivity pin, not a golden."""
    seeds, q, n = 120, 0.5, len(COMMON_SOURCE_LOT_ITEM_LINES)
    counts = []
    for seed in range(seeds):
        core = _core(cfg_cs=_ps_cfg(q), seed=seed)
        _plan(core, [_diner(1)])
        count = core._cs_provisioned_source[PATHOGEN]["n_contaminated"]
        assert count >= 0
        assert count <= n
        counts.append(count)
    mean = float(np.mean(counts))
    se = (n * q * (1 - q) / seeds) ** 0.5
    assert abs(mean - n * q) <= 2.5 * se


# ── Gate: nested contaminated-station sets across scalar rungs ──────

def test_contaminated_sets_nest_across_scalar_rungs() -> None:
    """Scalar rungs draw no uniform, so every rung reads the identical
    station-uniform sequence: a lower rung's contaminated set is a
    subset of every higher rung's — the contract's monotone-nesting
    gate, pinned twice (set inclusion and the exact station-uniform
    sequence the stream hands each rung)."""
    rungs = (0.2, 0.5, 0.9)
    sets = []
    for q in rungs:
        core = _core(cfg_cs=_ps_cfg(q))
        _plan(core, [_diner(1)])
        sets.append(core._cs_contaminated_stations[PATHOGEN])
    assert sets[0] <= sets[1] <= sets[2]
    stations = [(ZONE, i) for i in COMMON_SOURCE_LOT_ITEM_LINES]
    twin = _twin()
    uniforms = [twin.random() for _ in stations]
    expected = [
        {s for s, uu in zip(stations, uniforms) if uu < q}
        for q in rungs
    ]
    assert sets == expected


def test_objects_are_station_bound_not_zone_item_drawn() -> None:
    """Each minted object's (zone, item) is its census station — a
    provisioned object can never duplicate a station the way the fiat
    zone/item picks can."""
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_ps_cfg(0.7))
    _plan(core, agents)
    contaminated = core._cs_contaminated_stations[PATHOGEN]
    realized = [
        (o["zone"], o["item_label"]) for o in core._cs_objects[PATHOGEN]
    ]
    assert len(realized) == len(set(realized))
    assert set(realized) == contaminated


# ── Gate: object-row and voyage witnesses ───────────────────────────

def test_lot_rows_carry_provisioned_source_id() -> None:
    """Issue #1004: every provisioned-source lot row names the upstream
    source it minted from."""
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_ps_cfg(1.0))
    _, _, objects, _ = _step_objects(core, agents)
    lot_rows = [r for r in objects if r["source_kind"] == "provisioned_lot"]
    assert lot_rows
    for row in lot_rows:
        assert row["provisioned_source_id"] == SOURCE_ID


def test_fiat_rows_carry_null_provisioned_source_id() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_object_cfg())
    _, _, objects, _ = _step_objects(core, agents)
    for row in objects:
        assert row["provisioned_source_id"] is None


def test_agent_objects_keep_null_provisioned_source_id() -> None:
    """Worker/diner arms untouched: handler objects minted beside a
    provisioned lot still carry no provisioned_source_id."""
    agents = [_handler(1)] + [_diner(i) for i in range(2, 60)]
    core = _core(cfg_cs=_ps_cfg(
        1.0,
        handler_mode="object",
        handler_span_contamination_probability=1.0,
    ))
    _, _, objects, _ = _step_objects(core, agents, epochs=72)
    lots = [r for r in objects if r["source_kind"] == "provisioned_lot"]
    handlers = [r for r in objects if r["source_kind"] == "ill_handler"]
    assert lots
    assert handlers
    for row in lots:
        assert row["provisioned_source_id"] == SOURCE_ID
    for row in handlers:
        assert row["provisioned_source_id"] is None


def test_lot_strains_record_the_provisioning_source() -> None:
    """Issue #1004: the minted imported:lot strain's source_location is
    the resolved provisioning-source id, not the ship."""
    core = _strain_core(cs_overrides={
        "lot_mint_model": "provisioned_source",
        "provisioned_source": {"source_id": SOURCE_ID, "q_source": 1.0},
    })
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    lots = [r for r in objects if r["source_kind"] == "provisioned_lot"]
    assert lots
    for row in lots:
        strain = core.strain_registry.get(row["strain_id"])
        assert strain.origin == "imported:lot"
        assert strain.source_location == SOURCE_ID


def test_mode_off_mints_nothing_and_witnesses_nothing() -> None:
    core = _core(cfg_cs=_ps_cfg(1.0, **{"mode": "off"}))
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    assert objects == []
    assert core._cs_provisioned_source == {}


def test_independent_mode_ignores_the_mint_model() -> None:
    """``lot_mode: "independent"`` keeps v1 semantics even with the
    provisioned_source block spelled — the mint model is only
    meaningful under object-mode lot mints."""
    cs = _ps_cfg(1.0, **{"lot_mode": "independent",
                         "lot_event_probability": 0.0})
    core = _core(cfg_cs=cs)
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    assert objects == []
    assert not any(e["source_kind"] == "provisioned_lot" for e in events)


# ── Sanity-checker coverage (issue #1006) ───────────────────────────

def test_sanity_checker_flags_bad_source_and_bad_grammar() -> None:
    """The registry hook: an unresolvable source_id errors, a malformed
    q_source errors, and the shipped spelling stays clean."""
    from tools.sanity_checker import Report, _check_common_source

    report = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {"source_id": "nowhere_port"},
        }}},
        report,
    )
    assert report.errors
    report2 = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {"q_source": [0.9, 0.1]},
        }}},
        report2,
    )
    assert report2.errors
    report3 = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {"source_id": SOURCE_ID},
        }}},
        report3,
    )
    assert not report3.errors
