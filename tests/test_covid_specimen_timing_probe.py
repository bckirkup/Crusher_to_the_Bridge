"""Unit tests for the specimen-timing probe's pure helpers.

The probe reruns whole cells; these pin the small label/aggregate
functions so the readout math stays honest without a voyage.
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
        "covid_specimen_timing_probe",
        _ROOT / "tools" / "covid_specimen_timing_probe.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cell(**kw):
    base = {
        "seed": 1,
        "lab_confirmed_total": 0,
        "catch_classes": {},
        "window_coverage": {},
    }
    base.update(kw)
    return base


def test_catch_class_campaign_vs_passive_and_pre_onset(mod):
    assert (
        mod._catch_class(
            campaign_days={10}, spec_day=10, onset_day=12,
        )
        == "campaign_pre_onset"
    )
    assert (
        mod._catch_class(
            campaign_days={10}, spec_day=9, onset_day=12,
        )
        == "passive_pre_onset"
    )
    assert (
        mod._catch_class(
            campaign_days={10}, spec_day=10, onset_day=8,
        )
        == "campaign_post_onset"
    )
    # Same-day specimen and onset is post-onset (gate is strict <).
    assert (
        mod._catch_class(
            campaign_days={10}, spec_day=10, onset_day=10,
        )
        == "campaign_post_onset"
    )


def test_catch_class_never_presented_counts_as_pre_onset(mod):
    # A host with no onset ever is an asymmetric catch by the record's
    # bookkeeping: the undated set is never-symptomatic + pre-symptomatic.
    assert (
        mod._catch_class(
            campaign_days=set(), spec_day=5, onset_day=None,
        )
        == "passive_pre_onset"
    )


def test_pool_cells_aggregates_roles_and_share(mod):
    cells = [
        _cell(
            lab_confirmed_total=4,
            catch_classes={
                "campaign_pre_onset": {"crew": 1, "passenger": 1},
                "passive_post_onset": {"crew": 2, "passenger": 0},
            },
            window_coverage={
                "swabbed_in_window": {"crew": 3, "passenger": 0},
            },
        ),
        _cell(
            lab_confirmed_total=4,
            catch_classes={
                "campaign_pre_onset": {"crew": 0, "passenger": 1},
                "passive_post_onset": {"crew": 1, "passenger": 2},
            },
            window_coverage={
                "swabbed_in_window": {"crew": 1, "passenger": 2},
            },
        ),
    ]
    pooled = mod._pool_cells(cells)
    assert pooled["lab_confirmed_total"] == 8
    assert pooled["pre_onset_share_of_confirmed"] == pytest.approx(3 / 8)
    assert pooled["catch_classes"]["campaign_pre_onset"] == {
        "crew": 1,
        "passenger": 2,
    }
    assert pooled["window_coverage"]["swabbed_in_window"] == {
        "crew": 4,
        "passenger": 2,
    }


def test_pool_cells_zero_confirmed_share_is_none(mod):
    pooled = mod._pool_cells([_cell()])
    assert pooled["lab_confirmed_total"] == 0
    assert pooled["pre_onset_share_of_confirmed"] is None
