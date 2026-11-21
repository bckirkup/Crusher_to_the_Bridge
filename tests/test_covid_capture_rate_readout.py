"""Unit tests for the capture-rate readout's decomposition math.

The readout only restates committed payload echoes, so its correctness
is the bookkeeping on ``funnel_hosts`` + ``campaign_specimen_log`` plus
the serial-escape expectation over the declared sensitivity curve;
these pin it on synthetic cells.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_capture_rate_readout",
        _ROOT / "tools" / "covid_capture_rate_readout.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Stand-in curve: dpi 0-4 at 0.10, dpi 5-14 at 0.80, dpi 15+ at 0.50,
# aligned with the readout's _DPI_BUCKETS edges.
_CURVE = [0.10] * 5 + [0.80] * 10 + [0.50] * 10


def _cell_payload(
    hosts: dict[int, dict],
    log: list[dict],
    observables: dict | None = None,
) -> dict:
    return {
        "observables": observables or {"recorded_onsets": 20},
        "funnel_hosts": {str(k): v for k, v in hosts.items()},
        "campaign_specimen_log": log,
    }


def _log_row(aid: int, day: int, positive: bool = False) -> dict:
    return {"agent_id": aid, "day": day, "positive": positive}


def test_confirmed_campaign_vs_passive_split(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 10, "confirmed_day": 17},
            2: {"infection_day": 10, "confirmed_day": 21},
        },
        log=[
            _log_row(1, 17, positive=True),
            _log_row(1, 18),
            _log_row(2, 17),
        ],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["confirmed_campaign"] == 1
    assert out["confirmed_passive"] == 1
    assert out["capture"] == pytest.approx(1.0)


def test_starved_never_swabbed_vs_tail_infected(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 10},   # before last campaign day 20
            2: {"infection_day": 25},   # tail: infected after day 20
        },
        log=[_log_row(9, 20)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["drains"]["starved_never_swabbed_never_presented"] == 1
    assert out["drains"]["tail_infected_never_presented"] == 1
    assert out["capture"] == 0.0


def test_pre_infection_negative_is_starved_not_tail(mod):
    payload = _cell_payload(
        hosts={1: {"infection_day": 18, "specimen_day": 16}},
        log=[_log_row(1, 16), _log_row(2, 20)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert (
        out["drains"]["starved_pre_infection_negative_never_presented"] == 1
    )


def test_sensitivity_miss_dpi_and_escape_expectation(mod):
    # Infected day 10, campaign misses at day 12 (dpi 2) and day 17
    # (dpi 7): escape = (1 - 0.10) * (1 - 0.80) = 0.18.
    payload = _cell_payload(
        hosts={1: {"infection_day": 10, "specimen_day": 17}},
        log=[_log_row(1, 12), _log_row(1, 17), _log_row(2, 20)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["drains"]["sensitivity_miss_never_presented"] == 1
    assert out["miss_swab_dpi_hist"]["0_4"] == 1
    assert out["miss_swab_dpi_hist"]["5_14"] == 1
    assert out["miss_expected_escape"] == pytest.approx(0.9 * 0.2)
    assert out["miss_swabs_per_host"] == {2: 1}
    # Last while-infected swab day 17 < last campaign day 20: starved.
    assert out["miss_starved_retest"] == 1
    assert out["miss_exhausted"] == 0
    assert out["swabbed_infected_hosts"] == 1
    assert out["swabbed_infected_expected_escape"] == pytest.approx(0.18)


def test_miss_exhausted_when_last_swab_is_last_campaign_day(mod):
    payload = _cell_payload(
        hosts={1: {"infection_day": 30, "specimen_day": 34}},
        log=[_log_row(1, 34)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["miss_exhausted"] == 1
    assert out["miss_starved_retest"] == 0
    assert out["miss_swab_dpi_hist"]["0_4"] == 1


def test_passive_only_specimen_miss_in_passive_hist(mod):
    # Specimen day present but no campaign swab while infected: the
    # single passive-channel specimen is histogrammed by its own dpi.
    payload = _cell_payload(
        hosts={
            1: {
                "infection_day": 10,
                "presented_day": 16,
                "specimen_day": 17,
            }
        },
        log=[_log_row(2, 20)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["drains"]["sensitivity_miss_presented"] == 1
    assert out["miss_passive_dpi_hist"]["5_14"] == 1
    assert out["miss_expected_escape"] == pytest.approx(0.2)


def test_pool_buckets_drain_infection_days_and_takeoff_gate(mod):
    takeoff_cell = mod._decompose_cell(
        _cell_payload(
            hosts={1: {"infection_day": 27, "specimen_day": 28}},
            log=[_log_row(1, 28)],
            observables={"recorded_onsets": 20},
        ),
        _CURVE,
    )
    dead_cell = mod._decompose_cell(
        _cell_payload(
            hosts={1: {"infection_day": 27, "specimen_day": 28}},
            log=[_log_row(1, 28)],
            observables={"recorded_onsets": 3},
        ),
        _CURVE,
    )
    pooled = mod._pool([takeoff_cell, dead_cell])
    assert pooled["cells"] == 2
    assert pooled["takeoff_cells"] == 1
    hist = pooled["drain_infection_days"][
        "sensitivity_miss_never_presented"
    ]
    assert hist == {"25_29": 1}
    assert pooled["infections_total"] == 1


def test_confirmed_escape_includes_confirming_draw(mod):
    # Infected day 10; campaign swab at day 12 (dpi 2) misses,
    # passive confirmation at day 17 (dpi 7): the confirming draw's
    # own escape factor (1 - 0.80) multiplies the product.
    payload = _cell_payload(
        hosts={1: {"infection_day": 10, "confirmed_day": 17}},
        log=[_log_row(1, 12), _log_row(2, 20)],
    )
    out = mod._decompose_cell(payload, _CURVE)
    assert out["swabbed_infected_hosts"] == 1
    expected = (1 - 0.10) * (1 - 0.80)
    assert (
        out["swabbed_infected_expected_escape"]
        == pytest.approx(expected)
    )
    assert out["confirmed_swab_dpi_hist"]["5_14"] == 1
