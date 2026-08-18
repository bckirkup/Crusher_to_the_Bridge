"""Helpers for sentinel synthetic-recovery post-process."""
from __future__ import annotations

import math

import pytest

from picard_framework.analysis.sentinel_recovery_priors import (
    fleet_config_from_cell_id,
    recovery_fleet_priors,
    recovery_r_log_prior_fields,
)
from picard_framework.analysis.sentinel_recovery_postprocess import (
    cell_id,
    cell_key,
    interval_covers,
    port_day_ids,
    prepare_observations,
    remap_hours,
    remap_port_id,
    r_onboard_tag,
)


def test_r_onboard_tag_and_cell_id() -> None:
    assert r_onboard_tag(0.5) == "R0p5"
    assert cell_id("one_hot", "fleet_crossed", 1.0) == "one_hot__fleet_crossed__R1p0"


def test_posix_join_normalizes_windows_separators() -> None:
    from picard_framework.analysis.sentinel_recovery_postprocess import _posix_join

    assert _posix_join("..", "voyages\\run\\itinerary.json") == (
        "../voyages/run/itinerary.json"
    )


def test_cell_key_reads_campaign_parameters() -> None:
    hazard, fleet, r_val = cell_key(
        {
            "hazard_profile": "last_port_hot",
            "fleet_config": "single",
            "R_onboard": 1.5,
        },
    )
    assert hazard == "last_port_hot"
    assert fleet == "single"
    assert r_val == pytest.approx(1.5)


def test_interval_covers_closed_90_percent() -> None:
    assert interval_covers(0.001, 0.0005, 0.002)
    assert interval_covers(0.001, 0.001, 0.002)
    assert not interval_covers(0.01, 0.0005, 0.002)


def test_miami_slug_maps_to_usmia() -> None:
    assert remap_port_id("miami") == "USMIA"
    assert remap_port_id("MXCZM") == "MXCZM"
    hours = remap_hours({"miami": 10.0, "USMIA": 3.0, "MXCZM": 8.0})
    assert hours["USMIA"] == pytest.approx(13.0)
    assert hours["MXCZM"] == pytest.approx(8.0)


def test_port_day_ids_skip_home_port() -> None:
    ids = port_day_ids(
        {
            "itinerary": [
                {"type": "embarkation", "port_id": "USMIA"},
                {"type": "port_day", "port_id": "MXCZM"},
                {"type": "port_day", "port_id": "KYGEC"},
                {"type": "disembarkation", "port_id": "USMIA"},
            ],
        },
    )
    assert ids == {"MXCZM", "KYGEC"}


def test_prepare_observations_uniques_ship_and_drops_home_port() -> None:
    payload = prepare_observations(
        {
            "voyage_id": "old",
            "ship_id": "mega_cruise_5000",
            "clinical_cases": [
                {
                    "person_id": "1",
                    "onset_epoch": 40,
                    "crew": False,
                    "hours_ashore": {"miami": 5.0, "MXCZM": 8.0},
                },
            ],
            "exposure_totals": {
                "miami": {"person_hours_passenger": 10.0, "person_hours_crew": 0.0},
                "MXCZM": {"person_hours_passenger": 20.0, "person_hours_crew": 1.0},
            },
            "truth_introductions": [
                {"person_id": "1", "epoch": 20, "port_id": "miami"},
                {"person_id": "2", "epoch": 40, "port_id": "MXCZM"},
            ],
        },
        "sr_run_s300",
        {"MXCZM", "MXCTM", "KYGEC"},
    )
    assert payload["voyage_id"] == "sr_run_s300"
    assert payload["ship_id"] == "sr_run_s300"
    assert "USMIA" not in payload["clinical_cases"][0]["hours_ashore"]
    assert payload["clinical_cases"][0]["hours_ashore"]["MXCZM"] == pytest.approx(8.0)
    assert "miami" not in payload["exposure_totals"]
    assert "USMIA" not in payload["exposure_totals"]
    assert payload["exposure_totals"]["MXCZM"]["person_hours_passenger"] == pytest.approx(20.0)
    ports = [row["port_id"] for row in payload["truth_introductions"]]
    assert ports == ["MXCZM"]


def test_fleet_config_from_cell_id() -> None:
    assert fleet_config_from_cell_id("one_hot__fleet_same__R1p0") == "fleet_same"
    assert fleet_config_from_cell_id("null__single__R0p0") == "single"


def test_recovery_fleet_priors_tighten_r_and_baseline() -> None:
    priors = recovery_fleet_priors(fleet_config="single")
    fields = recovery_r_log_prior_fields(fleet_config="single")
    assert priors.r_prior_median == pytest.approx(0.06)
    assert priors.r_prior_log_sd == pytest.approx(0.35)
    assert priors.baseline_prior_log_sd == pytest.approx(1.0)
    assert fields["r_log_prior_mean"] == pytest.approx(math.log(0.06))
    assert fields["baseline_log_prior_sd"] == pytest.approx(1.0)
