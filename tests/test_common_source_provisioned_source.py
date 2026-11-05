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

from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    _COMMON_SOURCE_STREAM_KEY,
    COMMON_SOURCE_LOT_ITEM_LINES,
    ContactTracingMatrix,
    TransmissionCore,
    _provisioning_source_registry,
)
from tests.test_common_source_events import (
    MDR_ZONE,
    PATHOGEN,
    ZONE,
    _core,
    _diner,
    _handler,
    _profile,
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
    lo, hi = _provisioning_source_registry()["sources"][SOURCE_ID]["q_source"]
    assert lo < hi
    assert lo <= q <= hi


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


# ── Per-source genotype mix (issue #1011) ───────────────────────────

def _lot_genotypes(core: TransmissionCore) -> list[str]:
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    lots = [o for o in objects if o["source_kind"] == "provisioned_lot"]
    assert lots, "q_source 1.0 should contaminate every served station"
    return [
        core.strain_registry.get(row["strain_id"]).genotype
        for row in lots
    ]


def _mix_core(ps_block: dict) -> TransmissionCore:
    """provisioned_source object-mode core with variant_surveillance
    armed and the boarding prior pinned to GII.4."""
    return _strain_core(
        cs_overrides={
            "lot_mint_model": "provisioned_source",
            "provisioned_source": ps_block,
        },
        strain_evolution={
            "genotypes": ["GII.4", "GII.2"],
            "prior_genotype_distribution": {"GII.4": 0.7, "GII.2": 0.3},
        },
    )


def test_source_genotype_distribution_overrides_the_boarding_prior(
) -> None:
    """A source that declares its own mix supplies the lot's strain —
    independent of who boards (issue #1011). The boarding prior says
    GII.4/GII.2; the source says GII.6; every minted lot is GII.6."""
    core = _mix_core({
        "source_id": SOURCE_ID,
        "q_source": 1.0,
        "genotype_distribution": {PATHOGEN: {"GII.6": 1.0}},
    })
    assert set(_lot_genotypes(core)) == {"GII.6"}


def test_registry_declared_mix_supplies_the_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registry entry's own mix is the default — the
    ``provisioned_source`` block only outranks it when it declares one."""
    from engines import transmission_core as tc

    monkeypatch.setattr(
        tc,
        "_provisioning_source_registry",
        lambda: {
            "default_source": SOURCE_ID,
            "sources": {
                SOURCE_ID: {
                    "q_source": 1.0,
                    "genotype_distribution": {PATHOGEN: {"GII.9": 1.0}},
                },
            },
        },
    )
    core = _mix_core({"source_id": SOURCE_ID, "q_source": 1.0})
    assert set(_lot_genotypes(core)) == {"GII.9"}


def test_mix_unscoped_to_the_pathogen_falls_back_to_the_prior() -> None:
    """A mix that doesn't name the pathogen is the reason-to-be-the-same
    fallback — the lot draws the boarding prior as before."""
    core = _mix_core({
        "source_id": SOURCE_ID,
        "q_source": 1.0,
        "genotype_distribution": {"influenza_a": {"H1N1": 1.0}},
    })
    assert set(_lot_genotypes(core)) == {"GII.4", "GII.2"}


def test_fiat_ignores_the_source_mix() -> None:
    """The fiat grammar never resolves a source, so a declared mix is
    inert — lot strains draw the prior exactly as on main."""
    core = _strain_core(
        cs_overrides={
            "lot_mint_model": "fiat",
            "provisioned_source": {
                "source_id": SOURCE_ID,
                "genotype_distribution": {PATHOGEN: {"GII.6": 1.0}},
            },
        },
        strain_evolution={
            "genotypes": ["GII.4"],
            "prior_genotype_distribution": {"GII.4": 1.0},
        },
    )
    assert set(_lot_genotypes(core)) == {"GII.4"}


# ── Phase-2 venue-pin counterfactual ───────────────────────────────

def _two_zone_core(cfg_cs: dict, seed: int = 7) -> TransmissionCore:
    """ZONE (buffet) and MDR_ZONE (plated) both served Dining zones."""
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0, MDR_ZONE: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={ZONE: "Dining", MDR_ZONE: "Dining"},
        cfg={"transmission": {"common_source": cfg_cs}},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([ZONE, MDR_ZONE])
    core._quarantined_ids = set()
    return core


def _pin_cfg(
    pin: list,
    arm: str = "passenger_venue",
    q: float = 1.0,
) -> dict:
    return _ps_cfg(q, **{
        "provisioned_source": {
            "source_id": SOURCE_ID,
            "q_source": q,
            "station_zone_pin": pin,
            "source_venue_arm": arm,
        },
    })


def test_pin_remaps_every_minted_station_onto_the_pin_set() -> None:
    """q=1, pin=[MDR]: every census station mints a lot bound to the
    pinned venue — n_lots_placed == n_contaminated and
    actual_venues_used is exactly the pin."""
    core = _two_zone_core(_pin_cfg([MDR_ZONE]))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    n_stations = 2 * len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_stations"] == n_stations
    assert witness["n_contaminated"] == n_stations
    assert witness["n_lots_placed"] == n_stations
    assert witness["station_zone_pin"] == [MDR_ZONE]
    assert witness["source_venue_arm"] == "passenger_venue"
    assert witness["actual_venues_used"] == [MDR_ZONE]
    for row in core._cs_objects[PATHOGEN]:
        assert row["zone"] == MDR_ZONE
    items = {row["item_label"] for row in core._cs_objects[PATHOGEN]}
    assert items == set(COMMON_SOURCE_LOT_ITEM_LINES)


def test_pin_keeps_the_contamination_draw_stream_seed_paired() -> None:
    """Placement-only: the Bernoulli census draws are identical pinned
    vs unpinned on the same seed — the pin re-maps zones after the
    draws, never consuming uniforms."""
    base = _two_zone_core(_ps_cfg(0.5))
    pin = _two_zone_core(_pin_cfg([MDR_ZONE], arm="crew_venue", q=0.5))
    agents = [_diner(i, dining_zone=MDR_ZONE, location=MDR_ZONE)
              for i in range(1, 40)]
    _plan(base, agents)
    _plan(pin, agents)
    assert (
        base._cs_contaminated_stations[PATHOGEN]
        == pin._cs_contaminated_stations[PATHOGEN]
    )


def test_pin_round_robins_a_multi_zone_pin() -> None:
    """A two-venue pin spreads minted stations alternately in census
    order — deterministic, still count-preserving."""
    core = _two_zone_core(_pin_cfg([ZONE, MDR_ZONE]))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["actual_venues_used"] == [MDR_ZONE, ZONE]
    assert witness["n_lots_placed"] == witness["n_contaminated"]
    zones = [o["zone"] for o in core._cs_objects[PATHOGEN]]
    assert zones[0::2] == [ZONE] * (len(zones) // 2)
    assert zones[1::2] == [MDR_ZONE] * (len(zones) // 2)


def test_pin_to_an_unserved_venue_witnesses_the_drop() -> None:
    """The guard the spec names: pin to a venue whose cohort never
    serves inside the embarkation span → every minted lot drops,
    n_lots_placed falls below n_contaminated, and the witness says so."""
    core = _two_zone_core(_pin_cfg([MDR_ZONE]))
    _plan(core, [_diner(i) for i in range(1, 40)])  # all dine at ZONE
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["n_contaminated"] > 0
    assert witness["n_lots_placed"] == 0
    assert witness["actual_venues_used"] == []


def test_unpinned_witness_fields_are_null() -> None:
    """Baseline arm: the pin fields witness as null and placement
    stays on the census venues."""
    core = _two_zone_core(_ps_cfg(1.0))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["station_zone_pin"] is None
    assert witness["source_venue_arm"] is None
    assert witness["n_lots_placed"] == witness["n_contaminated"]
    assert set(witness["actual_venues_used"]) == {ZONE, MDR_ZONE}


def _weighted_pin_cfg(
    pin: list,
    weights: list,
    arm: str = "mixed_venue",
    q: float = 1.0,
) -> dict:
    return _ps_cfg(q, **{
        "provisioned_source": {
            "source_id": SOURCE_ID,
            "q_source": q,
            "station_zone_pin": pin,
            "station_zone_pin_weights": weights,
            "source_venue_arm": arm,
        },
    })


def test_weighted_pin_places_each_minted_station() -> None:
    """``station_zone_pin_weights``: every minted station still places
    (n_lots_placed == n_contaminated), onto pin venues only, and the
    witness carries the declared weights."""
    core = _two_zone_core(_weighted_pin_cfg([ZONE, MDR_ZONE], [3.0, 1.0]))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    n_stations = 2 * len(COMMON_SOURCE_LOT_ITEM_LINES)
    assert witness["n_lots_placed"] == n_stations
    assert witness["station_zone_pin"] == [ZONE, MDR_ZONE]
    assert witness["station_zone_pin_weights"] == [3.0, 1.0]
    assert witness["source_venue_arm"] == "mixed_venue"
    assert set(witness["actual_venues_used"]) <= {ZONE, MDR_ZONE}
    for row in core._cs_objects[PATHOGEN]:
        assert row["zone"] in (ZONE, MDR_ZONE)


def test_weighted_pin_converges_to_the_declared_shares() -> None:
    """Placement is a per-voyage weighted draw on a dedicated stream —
    across seeds the realized venue share approaches the declared
    weights, not the round-robin 50/50 alternation."""
    counts = {ZONE: 0, MDR_ZONE: 0}
    for seed in range(40):
        core = _two_zone_core(
            _weighted_pin_cfg([ZONE, MDR_ZONE], [3.0, 1.0]), seed=seed,
        )
        agents = (
            [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
            + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
               for i in range(1, 20)]
        )
        _plan(core, agents)
        for row in core._cs_objects[PATHOGEN]:
            counts[row["zone"]] += 1
    total = sum(counts.values())
    assert total == 40 * 2 * len(COMMON_SOURCE_LOT_ITEM_LINES)
    share = counts[ZONE] / total
    assert 0.6 < share < 0.9


def test_weighted_pin_keeps_streams_seed_paired() -> None:
    """Placement draws run on a parallel SeedSequence — the census
    draws and the minted lot count are identical to the unpinned
    baseline on the same seed."""
    base = _two_zone_core(_ps_cfg(1.0))
    pin = _two_zone_core(_weighted_pin_cfg([ZONE, MDR_ZONE], [3.0, 1.0]))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(base, agents)
    _plan(pin, agents)
    assert (
        base._cs_contaminated_stations[PATHOGEN]
        == pin._cs_contaminated_stations[PATHOGEN]
    )
    assert (
        pin._cs_provisioned_source[PATHOGEN]["n_lots_placed"]
        == base._cs_provisioned_source[PATHOGEN]["n_lots_placed"]
    )


def test_weighted_placement_consumes_no_shared_stream_draws() -> None:
    """The placement stream is a parallel SeedSequence — weighted
    remapping leaves ``_cs_rng`` state untouched, so the census draw
    stream stays seed-paired with the unpinned baseline."""
    core = _two_zone_core(_weighted_pin_cfg([ZONE, MDR_ZONE], [3.0, 1.0]))
    contaminated = [
        (ZONE, item) for item in COMMON_SOURCE_LOT_ITEM_LINES
    ]
    before = core._cs_rng.bit_generator.state
    placed = core._cs_place_pinned_stations(contaminated)
    assert core._cs_rng.bit_generator.state == before
    assert all(zone in (ZONE, MDR_ZONE) for zone, _item in placed)


def test_invalid_weights_fall_back_to_round_robin() -> None:
    """A malformed weights list (wrong length / non-positive) is inert
    at runtime — the pin keeps its deterministic round-robin, and the
    sanity checker is the gate that errors."""
    core = _two_zone_core(_weighted_pin_cfg([ZONE, MDR_ZONE], [3.0]))
    agents = (
        [_diner(i, dining_zone=ZONE) for i in range(1, 20)]
        + [_diner(i + 40, dining_zone=MDR_ZONE, location=MDR_ZONE)
           for i in range(1, 20)]
    )
    _plan(core, agents)
    witness = core._cs_provisioned_source[PATHOGEN]
    assert witness["station_zone_pin_weights"] is None
    assert witness["n_lots_placed"] == witness["n_contaminated"]
    zones = [o["zone"] for o in core._cs_objects[PATHOGEN]]
    assert zones[0::2] == [ZONE] * (len(zones) // 2)
    assert zones[1::2] == [MDR_ZONE] * (len(zones) // 2)


def test_sanity_checker_flags_bad_pin_weights() -> None:
    """Weights must be a list of finite positive numbers parallel to
    the pin — length mismatch and non-positive entries error."""
    from tools.sanity_checker import Report, _check_common_source

    def _cfg(weights: object) -> dict:
        return {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {
                "source_id": SOURCE_ID,
                "station_zone_pin": ["MainDining", "LidoBuffet"],
                "station_zone_pin_weights": weights,
            },
        }}}

    for bad in ([1.0], [1.0, 0.0], [1.0, "x"], "not-a-list"):
        report = Report()
        _check_common_source(_cfg(bad), report)
        assert report.errors, bad
    report_ok = Report()
    _check_common_source(_cfg([3.0, 1.0]), report_ok)
    assert not report_ok.errors


def test_sanity_checker_flags_a_bad_station_zone_pin() -> None:
    """Pin shape is validated: non-list errors, a pin naming an
    unknown zone errors when a layout is available, and a clean pin
    passes."""
    from tools.sanity_checker import Report, _check_common_source

    report = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {
                "source_id": SOURCE_ID,
                "station_zone_pin": "MainDining",
            },
        }}},
        report,
    )
    assert report.errors
    report2 = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {
                "source_id": SOURCE_ID,
                "station_zone_pin": ["MainDining"],
                "source_venue_arm": "passenger_venue",
            },
        }}},
        report2,
    )
    assert not report2.errors


def test_sanity_checker_flags_a_bad_genotype_distribution() -> None:
    """The hook: a config-block or registry mix that isn't a
    {pathogen: {genotype: weight}} probability map errors."""
    from tools.sanity_checker import (
        Report,
        _check_common_source,
        _check_source_genotype_distribution,
    )

    report = Report()
    _check_common_source(
        {"transmission": {"common_source": {
            "lot_mint_model": "provisioned_source",
            "provisioned_source": {
                "source_id": SOURCE_ID,
                "genotype_distribution": {PATHOGEN: {"GII.4": 0.5}},
            },
        }}},
        report,
    )
    assert any("sum" in f.message for f in report.errors)

    report2 = Report()
    _check_source_genotype_distribution(
        {"flat": "not-a-map"}, "genotype_distribution",
        "provisioning_sources.json", report2,
    )
    assert report2.errors

    report3 = Report()
    _check_source_genotype_distribution(
        {PATHOGEN: {"GII.4": 0.6, "GII.2": 0.4}},
        "genotype_distribution", "provisioning_sources.json", report3,
    )
    assert not report3.errors
