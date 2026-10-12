"""Admissibility gates for NORO-TWO-MODE-TITRE.

``titre_draw_mode: "two_mode"`` — the shipped default — conditions the
mint-time lot-titre draw on the object's denominator (NORO-IMPLICATED-
TITRE-01 §8, applied): a fired ``provisioned_lot`` object only mints
conditional on the voyage carrying a contaminated lot, so it IS the
implicated denominator and draws the implicated band
``lot_titre_implicated_gec_per_g`` (1.5e2, 5e3); any background-stock
titre site (none modelled) would draw ``lot_titre_background_gec_per_g``
(1e1, 1e3). ``"background"`` is the labelled pre-change baseline: every
site resolves to the single-mode ``lot_titre_gec_per_g`` spec
(1e1, 1e4), restoring the prior draw at the same stream position —
each band consumes exactly one uniform per titre.
"""

from __future__ import annotations

import math

import pytest

from tests.test_common_source_events import (
    PATHOGEN,
    ZONE,
    _core,
    _diner,
    _profile,
)
from tests.test_common_source_lot_objects import (
    _object_cfg,
    _step_objects,
)

IMPLICATION = (1.5e2, 5.0e3)
BACKGROUND_BAND = (1.0e1, 1.0e3)
LEGACY_BAND = (1.0e1, 1.0e4)


def _titres(core: object) -> list[float]:
    return [
        obj["lot_titre_gec_per_g"]
        for obj in core._cs_objects[PATHOGEN]
        if obj["source_kind"] == "provisioned_lot"
    ]


def _u(value: float, lo: float, hi: float) -> float:
    """The log-uniform quantile a titre sits at inside a band."""
    return (math.log10(value) - math.log10(lo)) / (
        math.log10(hi) - math.log10(lo)
    )


# ── Mode selection: the mint event picks the band ─────────────────────

def test_two_mode_draws_lot_titres_inside_the_implicated_band() -> None:
    core = _core(cfg_cs=_object_cfg(**{"extra_lot_probability": 1.0}))
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    titres = _titres(core)
    assert len(titres) > 1
    for titre in titres:
        assert IMPLICATION[0] <= titre <= IMPLICATION[1]


def test_the_bands_sit_inside_the_shipped_interval() -> None:
    # The proposal is conditioned INSIDE the legacy draw: both bands'
    # union is a strict subset of (1e1, 1e4) — the impossible ~39% low
    # tail and the surveillance-only top tail are what the split removes
    # from the implicated denominator.
    assert LEGACY_BAND[0] <= BACKGROUND_BAND[0] < BACKGROUND_BAND[1]
    assert IMPLICATION[0] < IMPLICATION[1] <= LEGACY_BAND[1]
    assert BACKGROUND_BAND[1] <= IMPLICATION[1]


def test_the_background_band_spec_is_confined_to_its_interval() -> None:
    core = _core(cfg_cs=_object_cfg(**{"lot_object_probability": 0.0}))
    draws = [
        core._cs_draw("lot_titre_background_gec_per_g", PATHOGEN)
        for _ in range(200)
    ]
    assert draws
    for value in draws:
        assert BACKGROUND_BAND[0] <= value <= BACKGROUND_BAND[1]


def test_resolver_maps_draw_sites_to_their_denominator_band() -> None:
    two_mode = _core(cfg_cs=_object_cfg())
    assert (
        two_mode._cs_titre_spec("provisioned_lot")
        == "lot_titre_implicated_gec_per_g"
    )
    assert (
        two_mode._cs_titre_spec("ill_handler")
        == "lot_titre_background_gec_per_g"
    )
    baseline = _core(cfg_cs=_object_cfg(titre_draw_mode="background"))
    assert (
        baseline._cs_titre_spec("provisioned_lot")
        == "lot_titre_gec_per_g"
    )
    assert (
        baseline._cs_titre_spec("ill_handler")
        == "lot_titre_gec_per_g"
    )


# ── The v1 independent path is an implicated mint too ─────────────────

def test_independent_lot_events_draw_the_implicated_band() -> None:
    # A fired provisioned lot IS the implicated denominator under either
    # arm mode — the v1 per-event titre takes the same band.
    core = _core(cfg_cs={
        "mode": "on",
        "lot_mode": "independent",
        "handler_mode": "independent",
        "diner_mode": "independent",
        "lot_event_probability": 1.0,
        "handler_event_probability": 0.0,
        "diner_event_probability": 0.0,
    })
    events, _, _, _ = _step_objects(core, [_diner(i) for i in range(1, 60)])
    lots = [e for e in events if e["source_kind"] == "provisioned_lot"]
    assert lots
    for event in lots:
        assert (
            IMPLICATION[0]
            <= event["lot_titre_gec_per_g"]
            <= IMPLICATION[1]
        )


# ── Baseline mode restores the pre-change draw ────────────────────────

def test_baseline_restores_the_single_mode_band_and_stream_position() -> None:
    # Same seed, same everything: the baseline must land the same
    # uniform at the same stream position — only the band mapping
    # changes. Titre-derived fields are the only allowed difference.
    def run(mode: str) -> tuple[list[dict], list[dict], dict]:
        core = _core(cfg_cs=_object_cfg(
            **{"extra_lot_probability": 0.5,
               "titre_draw_mode": mode},
        ), seed=23)
        events, _, objects, _ = _step_objects(
            core, [_diner(i) for i in range(1, 60)], epochs=72,
        )
        return events, objects, _titres(core)

    events_2m, objects_2m, titres_2m = run("two_mode")
    events_bg, objects_bg, titres_bg = run("background")
    assert len(titres_2m) == len(titres_bg) > 0
    assert titres_2m != titres_bg
    # Every background titre sits in the legacy band...
    for titre in titres_bg:
        assert LEGACY_BAND[0] <= titre <= LEGACY_BAND[1]
    # ...and maps to the SAME quantile the implicated draw consumed —
    # identical uniform, different interval: the pre-change draw.
    for im, bg in zip(titres_2m, titres_bg, strict=True):
        assert _u(im, *IMPLICATION) == pytest.approx(
            _u(bg, *LEGACY_BAND), abs=1e-9,
        )
    # Nothing else moved: same objects, same pans, same takers.
    def scrub_events(rows: list[dict]) -> list[dict]:
        return [
            {k: v for k, v in r.items()
             if k not in {"lot_titre_gec_per_g", "pan_mass",
                          "per_serving_dose"}}
            for r in rows
        ]
    def scrub_objects(rows: list[dict]) -> list[dict]:
        return [
            {k: v for k, v in r.items()
             if k not in {"lot_titre_gec_per_g", "dose_credited"}}
            for r in rows
        ]
    assert scrub_events(events_2m) == scrub_events(events_bg)
    assert scrub_objects(objects_2m) == scrub_objects(objects_bg)


def test_spec_overrides_route_through_the_resolved_band() -> None:
    # Pinning each spec name proves which spec the site resolves:
    # the implicated pin only moves two_mode; the legacy pin only
    # moves the baseline.
    core_2m = _core(cfg_cs=_object_cfg(
        **{"lot_titre_implicated_gec_per_g": 4.0e3},
    ))
    _step_objects(core_2m, [_diner(i) for i in range(1, 40)])
    assert _titres(core_2m) == [pytest.approx(4.0e3)]

    core_bg = _core(cfg_cs=_object_cfg(
        **{"titre_draw_mode": "background",
           "lot_titre_gec_per_g": 7.77e2},
    ))
    _step_objects(core_bg, [_diner(i) for i in range(1, 40)])
    assert _titres(core_bg) == [pytest.approx(7.77e2)]


def test_profile_block_overrides_the_implicated_band() -> None:
    # Per-pathogen literature replaces the constant, not the mechanism:
    # a profile block pins the band the same way the cfg does.
    core = _core(
        cfg_cs=_object_cfg(),
        profile=_profile(common_source_events={
            "enabled": True,
            "lot_titre_implicated_gec_per_g": [2.0e2, 2.0e2],
        }),
    )
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    assert _titres(core) == [pytest.approx(2.0e2)]


# ── Determinism and the no-op gates ───────────────────────────────────

def test_the_same_seed_reproduces_the_same_titres() -> None:
    def run() -> list[float]:
        core = _core(cfg_cs=_object_cfg(
            **{"extra_lot_probability": 0.5},
        ), seed=41)
        _step_objects(core, [_diner(i) for i in range(1, 60)], epochs=72)
        return _titres(core)

    first = run()
    assert first == run()


def test_unarmed_profiles_draw_nothing_under_either_titre_mode() -> None:
    for mode in ("two_mode", "background"):
        core = _core(
            cfg_cs=_object_cfg(titre_draw_mode=mode),
            profile=_profile(armed=False),
        )
        events, _, objects, _ = _step_objects(
            core, [_diner(i) for i in range(1, 40)],
        )
        assert events == []
        assert objects == []
        assert core._cs_rng is None


def test_handler_and_diner_objects_carry_no_titre() -> None:
    # The doc's mode split has no second titre site: shedder-sourced
    # pans are hand-load deposits, so agent objects mint titre None —
    # nothing about them is conditioned by the draw mode.
    agents = [_diner(1, infected=True)] + [_diner(i) for i in range(2, 60)]
    core = _core(cfg_cs={
        "mode": "on",
        "lot_mode": "independent",
        "lot_event_probability": 0.0,
        "handler_mode": "object",
        "diner_mode": "object",
        "handler_span_contamination_probability": 0.0,
        "diner_course_contamination_probability": 1.0,
    })
    _step_objects(core, agents, epochs=50)
    assert core._cs_objects.get(PATHOGEN)
    for obj in core._cs_objects[PATHOGEN]:
        assert obj["lot_titre_gec_per_g"] is None
        assert obj["source_kind"] != "provisioned_lot"


# Sanity: the fixture zone stays the self-serve venue these gates need.
assert ZONE == "Windjammer"
