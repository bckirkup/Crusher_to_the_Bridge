"""Boundaries of the extracted mega-cruise tier iterators."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework.runs.mega_cruise_campaign.tier_iterators import (  # noqa: E402
    _CALIBRATION_SHORTS,
    _STANDARD_ITERS,
    _latency_from_level,
    _lockdown_tag,
    _path_overrides,
    dispatch_standard_or_calibration,
)


def test_standard_iterator_table_covers_t1_through_t16() -> None:
    expected = {f"t{i}" for i in range(1, 17)}
    assert set(_STANDARD_ITERS) == expected


def test_dispatch_returns_none_for_other_families() -> None:
    for short in ("sr", "vd", "zz", "t17"):
        streamed = dispatch_standard_or_calibration(SimpleNamespace(short=short))
        assert streamed is None, short


def test_dispatch_hands_back_an_iterator_for_standard_and_calibration() -> None:
    ctx = SimpleNamespace(short="t9")
    streamed = dispatch_standard_or_calibration(ctx)
    assert streamed is not None
    assert hasattr(streamed, "__iter__")
    cal = dispatch_standard_or_calibration(SimpleNamespace(short="c1"))
    assert cal is not None
    assert hasattr(cal, "__iter__")
    assert "c1" in _CALIBRATION_SHORTS


def test_t9_cartesian_count_grades_with_seeds() -> None:
    def yield_run(rid: str, **kwargs: object) -> tuple[str, dict[str, object]]:
        return rid, kwargs

    def get_pathogen_config(_manifest: object, pathogen: str) -> tuple[str, str, dict]:
        return f"{pathogen}_bundle", pathogen, {}

    seed_counts = [1, 2, 4]
    run_counts = []
    for n_seeds in seed_counts:
        ctx = SimpleNamespace(
            short="t9",
            tier={
                "pathogens": ["norovirus"],
                "surveillance_strategies": ["none", "syndromic"],
                "seeds": list(range(n_seeds)),
            },
            manifest={},
            surv_cfgs={"none": {}, "syndromic": {}},
            get_pathogen_config=get_pathogen_config,
            yield_run=yield_run,
        )
        streamed = dispatch_standard_or_calibration(ctx)
        assert streamed is not None
        run_counts.append(len(list(streamed)))
    assert run_counts == [2 * n for n in seed_counts]
    assert run_counts[-1] - run_counts[0] >= 4


def test_unrelated_pathogen_list_does_not_change_strategy_span() -> None:
    def yield_run(rid: str, **kwargs: object) -> tuple[str, dict[str, object]]:
        return rid, kwargs

    def get_pathogen_config(_manifest: object, pathogen: str) -> tuple[str, str, dict]:
        return f"{pathogen}_bundle", pathogen, {}

    def count_for(pathogens: list[str]) -> int:
        ctx = SimpleNamespace(
            short="t9",
            tier={
                "pathogens": pathogens,
                "surveillance_strategies": ["none"],
                "seeds": [1],
            },
            manifest={},
            surv_cfgs={"none": {}},
            get_pathogen_config=get_pathogen_config,
            yield_run=yield_run,
        )
        streamed = dispatch_standard_or_calibration(ctx)
        assert streamed is not None
        return len(list(streamed))

    assert count_for(["norovirus"]) == 1
    assert count_for(["norovirus", "influenza"]) == 2


def test_latency_from_level_grades_confirmed_delay() -> None:
    delays = [0, 6, 24]
    tags = []
    confirmed = []
    for delay in delays:
        lat, tag = _latency_from_level(delay)
        tags.append(tag)
        confirmed.append(lat["confirmed_delay_epochs"])
    assert tags == delays
    assert confirmed == delays
    assert all(lat_tag >= 0 for lat_tag in tags)


def test_latency_dict_uses_confirmed_as_the_run_tag() -> None:
    lat, tag = _latency_from_level(
        {"alert": 1, "suspected": 2, "confirmed": 8, "lockdown": 24},
    )
    assert tag == 8
    assert lat["alert_delay_epochs"] == 1
    assert lat["lockdown_delay_epochs"] == 24


def test_lockdown_tag_never_versus_numeric_rates() -> None:
    rates = [0.01, 0.05, 0.10]
    tags = []
    values = []
    for rate in rates:
        val, tag = _lockdown_tag(rate)
        values.append(val)
        tags.append(tag)
    assert values == rates
    assert tags == ["1", "5", "10"]
    never_val, never_tag = _lockdown_tag("never")
    assert never_val is None
    assert never_tag == "never"


def test_path_overrides_dose_grades_and_init_is_independent() -> None:
    doses = [1.0, 5.0, 10.6]
    seen = []
    for dose in doses:
        over = _path_overrides({}, "norwalk_gi", dose, 3)
        seen.append(over["norwalk_gi"]["dose_adjustment"])
        assert over["norwalk_gi"]["initial_infected"] == 3
    assert seen == doses
    no_patch = _path_overrides({"keep": 1}, "norwalk_gi", None, None)
    assert no_patch == {"keep": 1}
