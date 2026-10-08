"""Unit coverage for tools/covid_asym_conf_attribution.py pure helpers.

The decomposition keys on presentation status at specimen epoch —
``onset <= specimen_epoch`` means symptomatic-at-specimen, anything else
(asymptomatic course, or presymptomatic swabbed before onset) lands in
the asymptomatic bucket, matching the record's field. These tests pin
the channel split, the ``_symptomatic`` suffix convention the share
math depends on, the three-bucket unconfirmed-infected drain, the
per-day capacity read, and the end-voyage counterfactual bound.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "covid_asym_conf_attribution.py"


@pytest.fixture(scope="module")
def mod() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "covid_asym_conf_attribution", TOOL,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Campaign:
    """Stand-in for TestingCampaign: fixed capacity per day."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity

    def capacity_for_day(self, day: int) -> int:
        return self._capacity


def _pools(**overrides: object) -> dict:
    """A minimal pools dict: epochs double as day indices."""
    pools = {
        "confirmed": {},
        "sampled": {},
        "onset": {},
        "campaign_log": [],
        "campaign": _Campaign(10),
        "sensitivity": [0.0, 0.0, 0.5, 0.8, 0.7, 0.4],
        "role_of": {},
        "infection_epoch": {},
        "day_of": lambda e: int(e),
        "end_epoch": 40,
    }
    pools.update(overrides)
    return pools


def _row(
    aid: int, day: int, *, positive: bool, symptomatic: bool,
    role: str = "passenger", epoch: int | None = None,
) -> dict:
    return {
        "agent_id": aid,
        "epoch": day if epoch is None else epoch,
        "day": day,
        "positive": positive,
        "symptomatic_at_specimen": symptomatic,
        "role": role,
    }


# ---------------------------------------------------------- channels


def test_confirmed_channels_split_by_status_and_route(mod):
    pools = _pools(
        confirmed={1: 100, 2: 101, 3: 102, 4: 103},
        onset={1: 90, 2: 200, 4: 103},
        campaign_log=[
            _row(1, 10, positive=True, symptomatic=True, epoch=100),
            _row(2, 10, positive=True, symptomatic=False, epoch=101),
            _row(9, 10, positive=True, symptomatic=True, epoch=99),
        ],
        role_of={1: "crew", 2: "crew", 3: "passenger", 4: "crew"},
    )
    out = mod._confirmed_channels(pools)
    # host 1: campaign positive at epoch 100, onset 90 <= 100 -> symp
    assert out["campaign_symptomatic"] == {"crew": 1, "passenger": 0}
    # host 2: campaign positive, onset 200 > 101 -> presymptomatic swab
    assert out["campaign_asymptomatic"] == {"crew": 1, "passenger": 0}
    # host 3: not in the campaign positives -> passive, no onset -> asym
    assert out["passive_asymptomatic"] == {"crew": 0, "passenger": 1}
    # host 4: passive, onset at specimen epoch -> symptomatic
    assert out["passive_symptomatic"] == {"crew": 1, "passenger": 0}


def test_share_uses_symptomatic_suffix_not_substring(mod):
    """``campaign_asymptomatic``.endswith("symptomatic") is the trap."""
    pools = _pools(
        confirmed={1: 100, 2: 101, 3: 102, 4: 103},
        onset={1: 90},
        campaign_log=[
            _row(1, 10, positive=True, symptomatic=True, epoch=100),
            _row(2, 10, positive=True, symptomatic=False, epoch=101),
        ],
        role_of={},
    )
    cell = {
        "confirmed_by_channel_status": mod._confirmed_channels(pools),
        "unconfirmed_infected": {},
    }
    pooled = mod._pool_cells([cell])
    # 1 symptomatic (host 1) + 3 asymptomatic (2,3,4) -> share 0.75
    assert pooled["lab_confirmed_total"] == 4
    assert pooled["asymptomatic_share_of_confirmed"] == pytest.approx(0.75)


# -------------------------------------------------------- drain split


def test_unconfirmed_infected_three_buckets(mod):
    pools = _pools(
        confirmed={1: 100},
        infection_epoch={1: 50, 2: 200, 3: 300, 4: 400},
        sampled={3: 250, 4: 410},
        onset={4: 401},
        role_of={2: "crew", 3: "passenger", 4: "crew"},
    )
    out = mod._unconfirmed_infected(pools)
    # host 2: never swabbed, never presented
    assert out["never_swabbed_never_presented"]["crew"] == 1
    # host 3: last specimen (250) pre-infection (300)
    assert out["swabbed_only_pre_infection_never_presented"][
        "passenger"
    ] == 1
    # host 4: last specimen (410) during infection (400), presented (401)
    assert out["swabbed_while_infected_negative_presented"]["crew"] == 1
    # zero rows are still emitted for the full grid
    assert out["never_swabbed_presented"] == {"crew": 0, "passenger": 0}


def test_campaign_days_capacity_and_dpi(mod):
    pools = _pools(
        campaign=_Campaign(7),
        infection_epoch={5: 100, 6: 96},
        campaign_log=[
            _row(5, 4, positive=False, symptomatic=True, role="crew"),
            _row(6, 4, positive=True, symptomatic=False),
            _row(7, 4, positive=False, symptomatic=False),
        ],
    )
    days = mod._campaign_days(pools)
    assert len(days) == 1
    row = days[0]
    assert row["specimens"] == 3
    assert row["capacity"] == 7
    assert row["to_symptomatic"] == 1
    assert row["to_asymptomatic"] == 2
    assert row["positive_symptomatic"] == 0
    assert row["positive_asymptomatic"] == 1
    assert row["crew_specimens"] == 1
    assert row["infected_swabbed"] == 2
    # host 5 negative at dpi -96? no: day 4 vs infection day 100
    assert row["negative_dpi_hist"] == {"-96": 1}


# ----------------------------------------------------- counterfactual


def test_sensitivity_at_clamps(mod):
    pools = _pools(sensitivity=[0.0, 0.2, 0.9])
    assert mod._sensitivity_at(pools, -3) == 0.0
    assert mod._sensitivity_at(pools, 1) == 0.2
    assert mod._sensitivity_at(pools, 99) == 0.9
    assert mod._sensitivity_at(_pools(sensitivity=[]), 2) == 0.0


def test_counterfactual_sums_curve_at_end(mod):
    pools = _pools(
        confirmed={1: 100},
        infection_epoch={1: 50, 2: 39, 3: 38},
        sampled={3: 30},
        onset={3: 200},
        sensitivity=[0.0, 0.5, 0.8, 0.9],
    )
    out = mod._counterfactual(pools)
    # end_day = 40. host 2: never swabbed, dpi 1 -> 0.5
    # host 3: pre-infection swab (30 < 38), dpi 2 -> 0.8, presented
    exp = out["expected_positives"]
    assert exp["never_swabbed_never_presented"] == pytest.approx(0.5)
    assert exp["swabbed_only_pre_infection_presented"] == pytest.approx(0.8)
    assert out["hosts"]["never_swabbed_never_presented"] == 1
    assert "swabbed_while_infected_negative_presented" not in out["hosts"]
