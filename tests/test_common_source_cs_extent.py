"""Admissibility gates for NORO-CS-EXTENT (NORO-ENTRAIN-01 design §4.3).

``transmission.common_source.lot_extent_mode`` and
``lot_state_redraw`` are the two lot-arm knobs the design declares for
the iso-dose and draw-cadence isolations config cannot express:
``"declared"`` mints a served-window extent and meters the lot's
servings uniformly per window (per-window cap, leftover to the last);
``"per_window"`` re-mints the lot's titre and take-share at each
served window off the object's own stream partition. The shipped
``"emergent"`` / ``"per_object"`` pair is the labelled baseline — the
contract waives default-ON — and must stay bit-identical at shared
seeds.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.test_common_source_events import (
    PATHOGEN,
    _core,
    _diner,
    _profile,
)
from tests.test_common_source_lot_objects import (
    _object_cfg,
    _step_objects,
)
from tests.test_common_source_titre_modes import (
    IMPLICATION,
    LEGACY_BAND,
    _u,
)


def _extent_cfg(**overrides: object) -> dict:
    """``_object_cfg`` plus the cs_extent knobs pinned at baseline."""
    cs = _object_cfg(**{
        "lot_extent_mode": "emergent",
        "lot_state_redraw": "per_object",
    })
    cs.update(overrides)
    return cs


def _lot_windows(events: list[dict]) -> list[int]:
    """Per-window servings_taken of the provisioned-lot pans, in
    service order (pan_servings pinned > any window's servings)."""
    return [
        e["servings_taken"] for e in events
        if e["source_kind"] == "provisioned_lot"
    ]


def _lot_titres(events: list[dict]) -> list[float]:
    return [
        e["lot_titre_gec_per_g"] for e in events
        if e["source_kind"] == "provisioned_lot"
    ]


# ── Declared extent: uniform spread + leftover to the last window ────

def test_declared_extent_meters_servings_uniformly() -> None:
    # 100 servings over 3 declared windows → 33 + 33 + 34. The cap
    # binds against a 59-strong cohort's full demand — emergent would
    # serve min(59, 100) = 59 in the first window.
    core = _core(cfg_cs=_extent_cfg(**{
        "lot_extent_mode": "declared",
        "lot_extent_windows": 3,
        "lot_servings": 100.0,
        "item_take_share": 1.0,
        "pan_servings": 80,
        "embarkation_lot_window_days": 1,
        "lot_shelf_life_days": 4,
    }))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)], epochs=96,
    )
    obj = objects[0]
    assert obj["extent_mode"] == "declared"
    assert obj["extent_windows"] == 3
    assert obj["windows_covered"] == 3
    assert _lot_windows(events) == [33, 33, 34]
    assert obj["servings_served"] == 100
    assert obj["end_reason"] == "exhausted"


def test_declared_extent_closes_extent_met_with_leftover() -> None:
    # A 10-strong cohort's whole demand (10/window) fits under the
    # 33-cap: every window under-serves and the declared span is spent
    # with 70 servings left — the arm's close signature.
    core = _core(cfg_cs=_extent_cfg(**{
        "lot_extent_mode": "declared",
        "lot_extent_windows": 3,
        "lot_servings": 100.0,
        "item_take_share": 1.0,
        "pan_servings": 80,
        "embarkation_lot_window_days": 1,
        "lot_shelf_life_days": 4,
    }))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 11)], epochs=96,
    )
    obj = objects[0]
    assert _lot_windows(events) == [10, 10, 10]
    assert obj["windows_covered"] == 3
    assert obj["servings_served"] == 30
    assert obj["end_reason"] == "extent_met"
    assert obj["exhausted_epoch"] is not None


def test_emergent_extent_keeps_the_uncapped_bookkeeping() -> None:
    # Same voyage minus the arm: the first window serves the full
    # cohort demand — no cap exists under the shipped default.
    core = _core(cfg_cs=_extent_cfg(**{
        "lot_servings": 100.0,
        "item_take_share": 1.0,
        "pan_servings": 80,
        "embarkation_lot_window_days": 1,
        "lot_shelf_life_days": 4,
    }))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 60)], epochs=96,
    )
    obj = objects[0]
    assert obj["extent_mode"] == "emergent"
    assert obj["extent_windows"] is None
    assert _lot_windows(events) == [59, 41]
    assert obj["end_reason"] == "exhausted"


def test_the_arm_intervals_are_expressible() -> None:
    # fx_wide / fx_narrow are config spellings of the same knob.
    for lo, hi in ((12, 24), (2, 4)):
        core = _core(cfg_cs=_extent_cfg(**{
            "lot_extent_mode": "declared",
            "lot_extent_windows": [lo, hi],
            "item_take_share": 0.0,
            "lot_shelf_life_days": 10,
            "embarkation_lot_window_days": 1,
        }))
        _, _, objects, _ = _step_objects(
            core, [_diner(i) for i in range(1, 40)], epochs=30,
        )
        obj = objects[0]
        assert lo <= obj["extent_windows"] <= hi


def test_lot_extent_windows_resolves_per_pathogen_block() -> None:
    # The usual chain: profile block > cfg > frozen.
    core = _core(
        cfg_cs=_extent_cfg(**{"lot_extent_mode": "declared"}),
        profile=_profile(**{
            "common_source_events": {
                "enabled": True, "lot_extent_windows": 2,
            },
        }),
    )
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    assert objects[0]["extent_windows"] == 2


# ── Per-window redraw: state re-mints on the object's partition ──────

def test_per_window_redraw_remints_state_each_served_window() -> None:
    # Titre re-mints at every served window: several distinct values
    # across the object's life, and the witness row keeps the last.
    core = _core(cfg_cs=_extent_cfg(**{
        "lot_state_redraw": "per_window",
        "lot_servings": 600.0,
        "item_take_share": [0.3, 0.7],
        "pan_servings": 80,
        "embarkation_lot_window_days": 1,
        "lot_shelf_life_days": 4,
    }))
    events, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)], epochs=120,
    )
    obj = objects[0]
    assert obj["redraw"] == "per_window"
    titres = _lot_titres(events)
    assert len(titres) >= 2
    assert len(set(titres)) > 1
    assert obj["lot_titre_gec_per_g"] == pytest.approx(titres[-1])


def test_per_window_remints_draw_off_the_object_partition() -> None:
    # A draw through an object partition never reaches the shared
    # stream: two identically-seeded cores, one drawing through a
    # spawned partition, still produce the same next shared value.
    core_a = _core(cfg_cs=_extent_cfg())
    core_b = _core(cfg_cs=_extent_cfg())
    partition = np.random.default_rng(
        core_a._cs_seed_seq.spawn(1)[0],
    )
    for name in ("lot_titre_gec_per_g", "item_take_share"):
        core_a._cs_draw(name, PATHOGEN, rng=partition)
    assert core_a._cs_rng.random() == pytest.approx(
        core_b._cs_rng.random(),
    )


def test_per_window_reproduces_at_shared_seed() -> None:
    def run() -> tuple:
        core = _core(cfg_cs=_extent_cfg(**{
            "lot_extent_mode": "declared",
            "lot_extent_windows": 4,
            "lot_state_redraw": "per_window",
            "lot_servings": 200.0,
            "item_take_share": [0.3, 0.7],
            "embarkation_lot_window_days": 1,
            "lot_shelf_life_days": 5,
        }), seed=23)
        return _step_objects(
            core, [_diner(i) for i in range(1, 40)], epochs=120,
        )[:3]

    first = run()
    second = run()
    assert first == second


# ── Per-window redraw × titre_draw_mode: re-mints resolve the band ───

def test_per_window_remints_draw_the_resolved_spec() -> None:
    # Pinning a spec name proves WHICH spec the re-mint resolves: under
    # the shipped ``two_mode`` a ``provisioned_lot`` re-mint draws
    # ``lot_titre_implicated_gec_per_g`` — the same denominator the
    # mint resolves — so every re-minted window titre lands the pin;
    # under ``"background"`` it draws the single-mode spec. A re-mint
    # that bypassed the resolver would leave these unpinned.
    for mode, spec in (
        ("two_mode", "lot_titre_implicated_gec_per_g"),
        ("background", "lot_titre_gec_per_g"),
    ):
        core = _core(cfg_cs=_extent_cfg(**{
            "titre_draw_mode": mode,
            "lot_state_redraw": "per_window",
            spec: 4.0e3,
            "lot_servings": 600.0,
            "item_take_share": [0.3, 0.7],
            "pan_servings": 80,
            "embarkation_lot_window_days": 1,
            "lot_shelf_life_days": 4,
        }))
        events, _, _, _ = _step_objects(
            core, [_diner(i) for i in range(1, 40)], epochs=120,
        )
        titres = _lot_titres(events)
        assert len(titres) > 1
        for titre in titres:
            assert titre == pytest.approx(4.0e3)


def test_per_window_remints_follow_the_resolved_band() -> None:
    # Every served window's re-minted titre sits in the band the mode
    # resolves — implicated under shipped ``two_mode``, single-mode
    # under the labelled baseline. The object partition consumes the
    # same uniforms either way, so same-seed re-mints pair at equal
    # log-uniform quantiles across the bands.
    def run(mode: str) -> list[float]:
        core = _core(cfg_cs=_extent_cfg(**{
            "titre_draw_mode": mode,
            "lot_state_redraw": "per_window",
            "lot_servings": 600.0,
            "item_take_share": [0.3, 0.7],
            "pan_servings": 80,
            "embarkation_lot_window_days": 1,
            "lot_shelf_life_days": 4,
        }), seed=23)
        events, _, _, _ = _step_objects(
            core, [_diner(i) for i in range(1, 40)], epochs=120,
        )
        return _lot_titres(events)

    implicated = run("two_mode")
    legacy = run("background")
    assert len(implicated) == len(legacy) > 1
    for im, bg in zip(implicated, legacy, strict=True):
        assert IMPLICATION[0] <= im <= IMPLICATION[1]
        assert LEGACY_BAND[0] <= bg <= LEGACY_BAND[1]
        assert _u(im, *IMPLICATION) == pytest.approx(
            _u(bg, *LEGACY_BAND), abs=1e-6,
        )


# ── The baseline pair stays bit-identical ────────────────────────────

def test_shipped_defaults_equal_the_explicit_baseline() -> None:
    # No new draws under the shipped pair: default cfg and the
    # explicit "emergent"/"per_object" spelling produce identical
    # witness rows at a shared seed.
    def run(modes: dict) -> tuple:
        core = _core(
            cfg_cs=_object_cfg(**modes), seed=23,
        )
        return _step_objects(
            core, [_diner(i) for i in range(1, 60)], epochs=72,
        )[:3]

    default = run({})
    explicit = run({
        "lot_extent_mode": "emergent",
        "lot_state_redraw": "per_object",
    })
    assert default == explicit


def test_baseline_objects_carry_the_baseline_witnesses() -> None:
    core = _core(cfg_cs=_extent_cfg())
    _, _, objects, _ = _step_objects(
        core, [_diner(i) for i in range(1, 40)],
    )
    obj = objects[0]
    assert obj["extent_mode"] == "emergent"
    assert obj["redraw"] == "per_object"
    assert obj["extent_windows"] is None


def test_a_forced_per_object_lot_mints_no_partition() -> None:
    # Construction witness for the draw-order constraint: the object
    # holds no redraw stream under the shipped default, so nothing
    # new consumes entropy anywhere.
    core = _core(cfg_cs=_extent_cfg())
    _step_objects(core, [_diner(i) for i in range(1, 40)])
    obj = core._cs_objects[PATHOGEN][0]
    assert obj["redraw_rng"] is None
    assert obj["extent_windows"] is None
    assert obj["window_serving_cap"] is None
