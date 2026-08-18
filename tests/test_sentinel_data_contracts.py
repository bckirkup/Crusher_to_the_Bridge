"""Sentinel data contracts: itinerary view + observation bundle.

The itinerary is a read-only view over ``voyage_config``; these tests freeze
that (no second itinerary model, no dependence on ``effects_enabled``) and the
referential integrity the JSON schema cannot express.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from picard_framework.analysis.sentinel.itinerary import (
    HOURS_FROM_WINDOWS,
    HOURS_UNSPECIFIED,
    censoring_epochs_after,
    load_voyage,
    port_calls_from_config,
    slugify_port,
    voyage_from_config,
)
from picard_framework.analysis.sentinel.observations import (
    bundle_from_dict,
    load_observation_bundle,
    validate_against_voyage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_DATA = REPO_ROOT / "picard_framework" / "analysis" / "sentinel" / "data"
ITINERARY_FIXTURE = SENTINEL_DATA / "example_itinerary.json"
OBSERVATIONS_FIXTURE = SENTINEL_DATA / "example_observations.json"

VOYAGE_ID = "VOY-2026-01-10-ENDEAVOR"
SHIP_ID = "ENDEAVOR"


def _read(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:  # noqa: PTH123 - test fixture read
        return json.load(fh)


def _call_for(config: dict[str, Any], port_id: str):
    """The first call at ``port_id`` (the home port is called twice)."""
    calls = [c for c in port_calls_from_config(config) if c.port_id == port_id]
    assert calls, f"no port call for {port_id}"
    return calls[0]


@pytest.fixture
def itinerary_config() -> dict[str, Any]:
    return _read(ITINERARY_FIXTURE)


@pytest.fixture
def observations_payload() -> dict[str, Any]:
    return _read(OBSERVATIONS_FIXTURE)


@pytest.fixture
def voyage(itinerary_config: dict[str, Any]):
    return voyage_from_config(
        itinerary_config,
        voyage_id=VOYAGE_ID,
        ship_id=SHIP_ID,
        n_passengers=4000,
        n_crew=1500,
    )


# ---------------------------------------------------------------- itinerary


def test_home_port_and_excursion_days_become_port_calls(voyage) -> None:
    assert voyage.port_ids == ("USMIA", "MXCZM", "MXCTM", "KYGEC")
    excursions = [c for c in voyage.port_calls if not c.is_home_port]
    assert [c.voyage_day for c in excursions] == [3, 4, 6]
    home = [c for c in voyage.port_calls if c.is_home_port]
    assert [c.voyage_day for c in home] == [1, 7]
    assert {c.port_id for c in home} == {"USMIA"}


def test_home_port_excluded_on_request(itinerary_config: dict[str, Any]) -> None:
    excursions = port_calls_from_config(itinerary_config, include_home_port=False)
    assert [c.port_id for c in excursions] == ["MXCZM", "MXCTM", "KYGEC"]
    assert not any(c.is_home_port for c in excursions)


def test_home_port_visits_are_summed_into_one_port(voyage) -> None:
    visits = voyage.port_calls_for("USMIA")
    assert len(visits) == 2
    assert [v.voyage_day for v in visits] == [1, 7]
    assert voyage.port_calls_for("MXCZM") == (voyage.port_call("MXCZM"),)
    assert voyage.port_calls_for("NOWHERE") == ()


def test_embarkation_day_carries_no_ashore_hours_by_default(voyage) -> None:
    embark = voyage.port_calls_for("USMIA")[0]
    # The default embarkation day keeps every passenger aboard once boarded, so
    # the pier contributes no exposure denominator.
    assert embark.pax_ashore_fraction == pytest.approx(0.0)
    assert embark.mean_hours_ashore == 0.0
    assert embark.hours_ashore_source == HOURS_UNSPECIFIED


def test_disembarkation_day_carries_home_port_ashore_hours(voyage) -> None:
    walk_off = voyage.port_calls_for("USMIA")[1]
    assert walk_off.pax_ashore_fraction == pytest.approx(1.0)
    # Window midpoint 9 to the last epoch of the day (23) at 1 h per epoch.
    assert walk_off.mean_hours_ashore == pytest.approx(14.0)
    assert walk_off.hours_ashore_source == HOURS_FROM_WINDOWS


def test_home_port_ashore_hours_grade_with_the_disembark_window(
    itinerary_config: dict[str, Any],
) -> None:
    observed: list[float] = []
    for start in (2, 6, 14):
        cfg = copy.deepcopy(itinerary_config)
        for day in cfg["voyage"]["itinerary"]:
            if day.get("type") == "disembarkation":
                day["disembark_window_epochs"] = [start, start + 6]
        observed.append(port_calls_from_config(cfg)[-1].mean_hours_ashore)
    assert observed == sorted(observed, reverse=True)
    assert observed[0] - observed[-1] > 6.0


def test_home_port_windows_stay_inside_the_voyage(voyage) -> None:
    for call in voyage.port_calls:
        assert 1 <= call.arrival_epoch <= call.departure_epoch <= voyage.total_epochs


def test_port_calls_ordered_and_within_voyage(voyage) -> None:
    days = [call.voyage_day for call in voyage.port_calls]
    assert days == sorted(days)
    for call in voyage.port_calls:
        assert 1 <= call.arrival_epoch < call.departure_epoch <= voyage.total_epochs


def test_observation_end_ignores_the_home_port_departure(
    itinerary_config: dict[str, Any],
) -> None:
    # The disembarkation day runs to the last epoch of the voyage; a ledger
    # that stops one epoch earlier is not censoring a shore excursion.
    built = voyage_from_config(
        itinerary_config,
        voyage_id=VOYAGE_ID,
        ship_id=SHIP_ID,
        observation_end_epoch=167,
    )
    assert built.observation_end_epoch == 167
    assert max(c.departure_epoch for c in built.port_calls) == 168


def test_epoch_windows_match_voyage_day_arithmetic(voyage) -> None:
    # Day 3 with 1 h epochs starts at epoch 49; disembark window opens at +2.
    cozumel = voyage.port_call("MXCZM")
    assert cozumel is not None
    assert (cozumel.arrival_epoch, cozumel.departure_epoch) == (51, 64)
    assert voyage.epochs_per_day == 24


def test_calendar_dates_derive_from_embarkation_date(voyage) -> None:
    assert voyage.embarkation_date == date(2026, 1, 10)
    cozumel = voyage.port_call("MXCZM")
    assert cozumel is not None
    assert cozumel.calendar_date == date(2026, 1, 12)
    assert cozumel.visit_key == "MXCZM@2026-01-12"


def test_explicit_calendar_date_overrides_derived(
    itinerary_config: dict[str, Any],
) -> None:
    cfg = copy.deepcopy(itinerary_config)
    for day in cfg["voyage"]["itinerary"]:
        if day.get("port_id") == "MXCZM":
            day["calendar_date"] = "2026-02-01"
    call = _call_for(cfg, "MXCZM")
    assert call.calendar_date == date(2026, 2, 1)


def test_mean_hours_ashore_from_window_midpoints(voyage) -> None:
    cozumel = voyage.port_call("MXCZM")
    assert cozumel is not None
    # midpoints 3.5 → 13.5 at 1 h per epoch
    assert cozumel.mean_hours_ashore == pytest.approx(10.0)
    assert cozumel.hours_ashore_source == HOURS_FROM_WINDOWS


def test_mean_hours_ashore_increases_with_later_reembarkation(
    itinerary_config: dict[str, Any],
) -> None:
    observed: list[float] = []
    for shift in (0, 2, 4):
        cfg = copy.deepcopy(itinerary_config)
        for day in cfg["voyage"]["itinerary"]:
            if day.get("port_id") == "MXCZM":
                day["reembark_window_epochs"] = [12 + shift, 15 + shift]
        observed.append(_call_for(cfg, "MXCZM").mean_hours_ashore)
    assert observed == sorted(observed)
    assert observed[-1] > observed[0]


def test_missing_windows_flag_hours_as_unspecified(
    itinerary_config: dict[str, Any],
) -> None:
    cfg = copy.deepcopy(itinerary_config)
    for day in cfg["voyage"]["itinerary"]:
        if day.get("port_id") == "MXCZM":
            day.pop("disembark_window_epochs")
            day.pop("reembark_window_epochs")
    call = _call_for(cfg, "MXCZM")
    assert call.hours_ashore_source == HOURS_UNSPECIFIED
    assert call.mean_hours_ashore == 0.0
    assert call.departure_epoch == 49 + 23


def test_crew_shore_leave_defaults_to_zero(itinerary_config: dict[str, Any]) -> None:
    cfg = copy.deepcopy(itinerary_config)
    for day in cfg["voyage"]["itinerary"]:
        day.pop("crew_shore_leave_fraction", None)
    calls = port_calls_from_config(cfg, include_home_port=False)
    assert [c.crew_ashore_fraction for c in calls] == [0.0, 0.0, 0.0]


def test_crew_shore_leave_read_from_config(voyage) -> None:
    fractions = {c.port_id: c.crew_ashore_fraction for c in voyage.port_calls}
    assert fractions["MXCZM"] == pytest.approx(0.15)
    assert 0.0 <= min(fractions.values()) <= max(fractions.values()) <= 1.0


def test_pax_ashore_fraction_falls_back_to_day_defaults(
    itinerary_config: dict[str, Any],
) -> None:
    cfg = copy.deepcopy(itinerary_config)
    for day in cfg["voyage"]["itinerary"]:
        day.pop("disembark_fraction", None)
    # port_day default onboard fraction is 0.30 → 0.70 ashore
    assert _call_for(cfg, "MXCZM").pax_ashore_fraction == pytest.approx(0.70)


def test_view_is_independent_of_effects_enabled(
    itinerary_config: dict[str, Any],
) -> None:
    cfg = copy.deepcopy(itinerary_config)
    cfg["voyage"]["effects_enabled"] = False
    assert port_calls_from_config(cfg) == port_calls_from_config(itinerary_config)


def test_unknown_day_type_still_rejected(itinerary_config: dict[str, Any]) -> None:
    cfg = copy.deepcopy(itinerary_config)
    cfg["voyage"]["itinerary"][1]["type"] = "shore_excursion"
    with pytest.raises(ValueError, match="Unknown itinerary day type"):
        port_calls_from_config(cfg)


def test_empty_itinerary_yields_no_port_calls() -> None:
    assert port_calls_from_config({}) == ()
    assert port_calls_from_config(None) == ()


def test_slugify_port_ids_when_codes_absent(
    itinerary_config: dict[str, Any],
) -> None:
    cfg = copy.deepcopy(itinerary_config)
    for day in cfg["voyage"]["itinerary"]:
        day.pop("port_id", None)
    assert [c.port_id for c in port_calls_from_config(cfg)] == [
        "miami",
        "cozumel",
        "costa_maya",
        "george_town",
        "miami",
    ]
    assert slugify_port("  ") == "unknown_port"


def test_censoring_decreases_for_later_ports(voyage) -> None:
    remaining = [censoring_epochs_after(voyage, c) for c in voyage.port_calls]
    assert remaining == sorted(remaining, reverse=True)
    assert min(remaining) >= 0


def test_observation_end_before_last_departure_rejected(
    itinerary_config: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="observation_end_epoch"):
        voyage_from_config(
            itinerary_config,
            voyage_id=VOYAGE_ID,
            ship_id=SHIP_ID,
            observation_end_epoch=100,
        )


def test_load_voyage_reads_config_from_disk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    itinerary_config: dict[str, Any],
) -> None:
    target = tmp_path / "voyage_config.json"
    target.write_text(json.dumps(itinerary_config), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    loaded = load_voyage(
        "voyage_config.json",
        voyage_id=VOYAGE_ID,
        ship_id=SHIP_ID,
    )
    assert loaded.port_ids == ("USMIA", "MXCZM", "MXCTM", "KYGEC")
    assert loaded.platform_class == "mega"


# ------------------------------------------------------------- observations


def test_bundle_parses_and_sorts_cases(observations_payload: dict[str, Any]) -> None:
    bundle = bundle_from_dict(observations_payload)
    onsets = [c.onset_epoch for c in bundle.clinical_cases]
    assert onsets == sorted(onsets)
    assert len(bundle.clinical_cases) == 5
    assert sum(1 for c in bundle.clinical_cases if c.crew) == 1
    assert [c.went_ashore for c in bundle.clinical_cases].count(False) == 1


def test_wastewater_relative_abundance_bounded(
    observations_payload: dict[str, Any],
) -> None:
    bundle = bundle_from_dict(observations_payload)
    for sample in bundle.wastewater_samples:
        assert 0.0 <= sample.relative_abundance <= 1.0
    epochs = [s.sample_epoch for s in bundle.wastewater_samples]
    assert epochs == sorted(epochs)


def test_genotypes_absent_until_strain_state_exists(
    observations_payload: dict[str, Any],
) -> None:
    bundle = bundle_from_dict(observations_payload)
    assert all(c.genotype is None for c in bundle.clinical_cases)


def test_reads_exceeding_library_depth_rejected(
    observations_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["wastewater_samples"][0]["pathogen_reads"] = 999999
    with pytest.raises(ValueError, match="exceeds total_reads"):
        bundle_from_dict(payload)


def test_duplicate_person_id_rejected(observations_payload: dict[str, Any]) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"].append(copy.deepcopy(payload["clinical_cases"][0]))
    with pytest.raises(ValueError, match="Duplicate person_id"):
        bundle_from_dict(payload)


def test_unknown_reporting_channel_rejected(
    observations_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["reported_via"] = "rumor"
    with pytest.raises(ValueError, match="Unknown reported_via"):
        bundle_from_dict(payload)


def test_hours_ashore_is_read_only(observations_payload: dict[str, Any]) -> None:
    bundle = bundle_from_dict(observations_payload)
    case = bundle.clinical_cases[0]
    with pytest.raises(TypeError):
        case.hours_ashore["MXCZM"] = 1.0  # type: ignore[index]


def test_fixture_bundle_is_referentially_clean(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    bundle = bundle_from_dict(observations_payload)
    assert validate_against_voyage(bundle, voyage) == []


def test_unknown_port_reported(voyage, observations_payload: dict[str, Any]) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["hours_ashore"] = {"XXNOP": 4.0}
    problems = validate_against_voyage(bundle_from_dict(payload), voyage)
    assert any("unknown port" in p for p in problems)


def test_home_port_ashore_hours_validate(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    """The pier the voyage starts and ends on is not an unknown port.

    Simulated ledgers record ashore hours at the home port on the
    disembarkation day; rejecting them would make every campaign bundle unfit.
    """
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["hours_ashore"] = {"USMIA": 10.0}
    assert validate_against_voyage(bundle_from_dict(payload), voyage) == []


def test_home_port_hours_beyond_both_calls_reported(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    """Two home-port calls raise the dwell ceiling, they do not remove it."""
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["hours_ashore"] = {"USMIA": 500.0}
    problems = validate_against_voyage(bundle_from_dict(payload), voyage)
    assert any("exceeds the" in p for p in problems)


def test_onset_past_observation_end_reported(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["onset_epoch"] = 5000
    problems = validate_against_voyage(bundle_from_dict(payload), voyage)
    assert any("observation_end_epoch" in p for p in problems)


def test_hours_ashore_beyond_dwell_reported(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["clinical_cases"][0]["hours_ashore"] = {"MXCZM": 40.0}
    problems = validate_against_voyage(bundle_from_dict(payload), voyage)
    assert any("exceeds the" in p for p in problems)


def test_identity_mismatch_reported(
    voyage,
    observations_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(observations_payload)
    payload["ship_id"] = "OTHER_SHIP"
    problems = validate_against_voyage(bundle_from_dict(payload), voyage)
    assert any("ship_id mismatch" in p for p in problems)


def test_load_observation_bundle_from_disk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observations_payload: dict[str, Any],
) -> None:
    target = tmp_path / "observations.json"
    target.write_text(json.dumps(observations_payload), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    bundle = load_observation_bundle("observations.json")
    assert bundle.voyage_id == VOYAGE_ID
    assert bundle.n_crew == 1500
