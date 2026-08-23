"""Contract tests for the fictional `federation` port library and the two
Enterprise itineraries.

The values under test are invented for the fictional setting, so nothing here
asserts a literature quantity. What it does assert is that the fifth region is
indistinguishable from the four real ones to every consumer: same schema, same
loader, no special case; that both itineraries reference only ports that a
region library actually profiles; and that the derived surveillance quantities
still move with the capability fields, so an invented port programme cannot be
silently mute and inflate the shipboard benefit.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace

import pytest

from engines.incubation import IncubationModel
from engines.voyage_itinerary import (
    load_voyage_config,
    voyage_config_path_for_platform,
)
from picard_framework.analysis.sentinel.itinerary import PortCall, port_calls_from_config
from picard_framework.analysis.sentinel.port_health import REPORTING_PATHWAYS
from picard_framework.analysis.sentinel.port_profiles import (
    PROFILE_REGIONS,
    REGION_FEDERATION,
    load_all_profiles,
    load_region_profiles,
)
from picard_framework.analysis.sentinel.profile_delays import (
    incubation_delay_for_profile,
)
from picard_framework.analysis.shore.detection import port_detection_epoch
from picard_framework.pathogen_overrides import load_pathogen_bundle

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_PATH = os.path.join(
    REPO_ROOT,
    "picard_framework",
    "analysis",
    "sentinel",
    "data",
    f"port_surveillance_{REGION_FEDERATION}.json",
)
SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas", "port_surveillance.schema.json")
VOYAGE_SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas", "voyage_config.schema.json")

# The fiction pathogen bundles the Enterprise platforms run on. They are not
# the active bundle, so the shore model only sees them when handed them.
TOS_BUNDLE = os.path.join(
    REPO_ROOT, "data", "pathogens", "enterprise_tos_profiles.json",
)
TNG_BUNDLE = os.path.join(
    REPO_ROOT, "data", "pathogens", "enterprise_tng_profiles.json",
)

TOS_PLATFORM = "enterprise_constitution_tos"
TNG_PLATFORM = "enterprise_galaxy_tng"

# The routes of docs/variant_surveillance_spec.md §3, home port included at
# both ends because the voyage begins and ends on that pier.
TOS_ROUTE = ("SBONE", "SBELV", "KSEVN", "MEMAL", "SBONE")
TNG_ROUTE = ("SBONE", "FARPT", "DSNIN", "RISAA", "SBSVF", "SBONE")

# Fixed inputs for every sensitivity sweep: a flat incidence series and one
# shipped active profile, so only the swept capability field varies.
FLAT_INCIDENCE = [6.0] * 90
SWEEP_PATHOGEN = "norwalk_gi"
EPOCH_HOURS = 24.0
CASE_THRESHOLD = 12.0


def _bundle(path: str) -> dict:
    return load_pathogen_bundle(path)


def _itinerary_config(platform_id: str) -> dict:
    return load_voyage_config(voyage_config_path_for_platform(REPO_ROOT, platform_id))


def _port_sequence(platform_id: str) -> tuple[str, ...]:
    calls = port_calls_from_config(_itinerary_config(platform_id))
    return tuple(call.port_id for call in calls)


def _exposure_denominator(call: PortCall) -> float:
    """Passenger person-hours ashore for one call, per passenger aboard."""
    return call.mean_hours_ashore * call.pax_ashore_fraction


def _voyage_denominator(platform_id: str) -> float:
    return sum(
        _exposure_denominator(call)
        for call in port_calls_from_config(_itinerary_config(platform_id))
    )


def _detection_epoch(capability, **overrides) -> int | None:
    return port_detection_epoch(
        FLAT_INCIDENCE,
        port_id=capability.port_id,
        pathogen_id=SWEEP_PATHOGEN,
        epoch_hours=EPOCH_HOURS,
        case_threshold=CASE_THRESHOLD,
        capability=replace(capability, **overrides) if overrides else capability,
    )


# --- the region loads like the other four ---------------------------------


def test_federation_is_a_registered_region():
    assert REGION_FEDERATION in PROFILE_REGIONS


def test_federation_loads_through_the_shared_loader():
    profiles = load_region_profiles(REGION_FEDERATION)
    assert set(profiles) == set(TOS_ROUTE) | set(TNG_ROUTE)
    for port_id, capability in profiles.items():
        assert capability.port_id == port_id
        assert capability.port_name
        assert capability.population >= 1
        assert capability.reports_to in REPORTING_PATHWAYS


def test_federation_ports_reach_the_merged_catalog():
    catalog = load_all_profiles()
    federation = load_region_profiles(REGION_FEDERATION)
    assert set(federation) <= set(catalog)
    # The merge is additive: the four real libraries are still whole.
    for region in PROFILE_REGIONS:
        assert set(load_region_profiles(region)) <= set(catalog)


def test_federation_validates_against_the_shipped_schema():
    jsonschema = pytest.importorskip("jsonschema")
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        document = json.load(fh)
    jsonschema.validate(document, schema)


def test_federation_labels_itself_as_fictional():
    """The setting values must not be readable as measured capabilities."""
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        document = json.load(fh)
    assert "fiction" in document["description"].casefold()
    for port_id, entry in document["port_surveillance_profiles"].items():
        assert "fictional" in str(entry.get("note", "")).casefold(), port_id


# --- referential integrity ------------------------------------------------


@pytest.mark.parametrize("platform_id", [TOS_PLATFORM, TNG_PLATFORM])
def test_itinerary_platform_directory_exists(platform_id):
    path = voyage_config_path_for_platform(REPO_ROOT, platform_id)
    assert os.path.isdir(os.path.join(REPO_ROOT, "data", "platforms", platform_id))
    assert os.path.isfile(path)


@pytest.mark.parametrize("platform_id", [TOS_PLATFORM, TNG_PLATFORM])
def test_every_itinerary_port_is_profiled(platform_id):
    catalog = load_all_profiles()
    for day in _itinerary_config(platform_id)["voyage"]["itinerary"]:
        port_id = day.get("port_id")
        if port_id is None:
            assert day["type"] == "sea_day", day
            continue
        assert port_id in catalog, port_id


@pytest.mark.parametrize(
    ("platform_id", "route"),
    [(TOS_PLATFORM, TOS_ROUTE), (TNG_PLATFORM, TNG_ROUTE)],
)
def test_itinerary_follows_the_specified_route(platform_id, route):
    assert _port_sequence(platform_id) == route


@pytest.mark.parametrize("platform_id", [TOS_PLATFORM, TNG_PLATFORM])
def test_itinerary_is_simulation_inert(platform_id):
    """Both configs are analysis metadata: existing runs stay identical."""
    voyage = _itinerary_config(platform_id)["voyage"]
    assert voyage["effects_enabled"] is False
    assert voyage["shore_exposure"]["enabled"] is False


# --- the two itineraries are genuinely different --------------------------


def test_itineraries_give_different_sequences_and_denominators():
    tos_seq, tng_seq = _port_sequence(TOS_PLATFORM), _port_sequence(TNG_PLATFORM)
    assert tos_seq != tng_seq
    assert len(set(tos_seq) ^ set(tng_seq)) >= 4

    tos_denom, tng_denom = (
        _voyage_denominator(TOS_PLATFORM),
        _voyage_denominator(TNG_PLATFORM),
    )
    assert tos_denom > 0.0
    # The TNG survey is longer and higher-liberty, by a wide margin rather
    # than a rounding difference.
    assert tng_denom > tos_denom * 1.5


def test_excursion_calls_each_carry_their_own_exposure_window():
    for platform_id in (TOS_PLATFORM, TNG_PLATFORM):
        excursions = port_calls_from_config(
            _itinerary_config(platform_id),
            include_home_port=False,
        )
        assert excursions
        denominators = [_exposure_denominator(call) for call in excursions]
        assert all(value > 0.0 for value in denominators)
        assert all(call.carries_ashore_exposure for call in excursions)
        # Distinct calls, not one window copied down the itinerary.
        assert len(set(denominators)) == len(denominators)


# --- graded sensitivity of the derived surveillance quantities ------------


def test_reporting_delay_moves_with_the_syndromic_delay_field():
    capability = load_region_profiles(REGION_FEDERATION)["SBONE"]
    epochs = [
        _detection_epoch(capability, syndromic_delay_days=days)
        for days in (1.0, 2.0, 4.0, 8.0)
    ]
    assert all(value is not None for value in epochs)
    assert epochs == sorted(epochs)
    assert all(later - earlier >= 1 for earlier, later in zip(epochs, epochs[1:]))
    assert epochs[-1] - epochs[0] >= 7


def test_lab_turnaround_adds_to_the_reporting_delay():
    capability = load_region_profiles(REGION_FEDERATION)["SBONE"]
    baseline = _detection_epoch(capability, lab_confirmation=False)
    epochs = [
        _detection_epoch(capability, lab_turnaround_days=days)
        for days in (1.0, 3.0, 6.0)
    ]
    assert baseline is not None
    assert all(value is not None for value in epochs)
    assert epochs == sorted(epochs)
    assert epochs[0] > baseline
    assert len(set(epochs)) == len(epochs)


def test_ascertainment_moves_with_syndromic_coverage():
    capability = load_region_profiles(REGION_FEDERATION)["RISAA"]
    epochs = [
        _detection_epoch(capability, syndromic_coverage=coverage)
        for coverage in (0.1, 0.25, 0.5, 0.9)
    ]
    assert all(value is not None for value in epochs)
    # Better ascertainment can only bring the crossing forward.
    assert epochs == sorted(epochs, reverse=True)
    assert epochs[0] - epochs[-1] >= 2


def test_uninstrumented_port_reports_nothing_while_its_homeport_does():
    """Negative control, stated rather than emerging from a mute label."""
    profiles = load_region_profiles(REGION_FEDERATION)
    assert _detection_epoch(profiles["MEMAL"]) is None
    assert _detection_epoch(profiles["SBONE"]) is not None


def test_capability_gradient_orders_the_federation_ports():
    profiles = load_region_profiles(REGION_FEDERATION)
    dense = _detection_epoch(profiles["SBSVF"])
    middling = _detection_epoch(profiles["DSNIN"])
    sparse = _detection_epoch(profiles["RISAA"])
    assert dense is not None
    assert middling is not None
    assert sparse is not None
    assert dense < middling
    assert middling < sparse


# --- the Enterprise pathogen bundles run through the shore model ----------


@pytest.mark.parametrize("bundle", [TOS_BUNDLE, TNG_BUNDLE])
def test_enterprise_profiles_carry_a_projectable_incubation(bundle):
    """Every fiction pathogen has a kernel the sentinel projection accepts."""
    for pathogen_id, profile in _bundle(bundle).items():
        model = IncubationModel.from_mapping(profile["incubation"])
        assert 0.0 < model.median_days < float(profile["recovery_day"]), pathogen_id
        delay = incubation_delay_for_profile(profile, epoch_hours=EPOCH_HOURS)
        assert len(delay.pmf) > 0
        assert sum(delay.pmf) == pytest.approx(1.0)
        assert "fiction" in str(profile["incubation"]["notes"]).casefold(), pathogen_id


def test_enterprise_kernels_span_a_fast_and_a_slow_pathogen():
    """The bundles are only a useful test bed if their kernels differ."""
    profiles = {**_bundle(TOS_BUNDLE), **_bundle(TNG_BUNDLE)}
    medians = {
        pathogen_id: IncubationModel.from_mapping(profile["incubation"]).median_days
        for pathogen_id, profile in profiles.items()
    }
    assert medians["psi_2000_polywater"] < 2.0
    assert medians["barclay_protomorphosis"] > 4.0
    assert len(set(medians.values())) == len(medians)


@pytest.mark.parametrize("bundle", [TOS_BUNDLE, TNG_BUNDLE])
def test_every_federation_port_resolves_every_enterprise_pathogen(bundle):
    """No fiction pathogen is silently mute at a port that has a programme.

    detection.py raises on a label it cannot resolve precisely so that an
    unwatched pathogen cannot pass for an undetected one; this asserts the
    region's vocabulary is complete enough that the raise never fires.
    """
    profiles = _bundle(bundle)
    capabilities = load_region_profiles(REGION_FEDERATION)
    for pathogen_id in profiles:
        for port_id, capability in capabilities.items():
            epoch = port_detection_epoch(
                FLAT_INCIDENCE,
                port_id=port_id,
                pathogen_id=pathogen_id,
                epoch_hours=EPOCH_HOURS,
                case_threshold=CASE_THRESHOLD,
                capability=capability,
                profiles=profiles,
            )
            if port_id == "MEMAL":
                assert epoch is None
                continue
            assert epoch is not None, (pathogen_id, port_id)
            assert epoch > 0


def test_slow_kernel_detects_later_than_the_fast_one_at_one_port():
    """The kernel, not only the port programme, moves the detection epoch."""
    capability = load_region_profiles(REGION_FEDERATION)["SBONE"]
    profiles = {**_bundle(TOS_BUNDLE), **_bundle(TNG_BUNDLE)}
    epochs = {
        pathogen_id: port_detection_epoch(
            FLAT_INCIDENCE,
            port_id=capability.port_id,
            pathogen_id=pathogen_id,
            epoch_hours=EPOCH_HOURS,
            case_threshold=CASE_THRESHOLD,
            capability=capability,
            profiles=profiles,
        )
        for pathogen_id in ("psi_2000_polywater", "barclay_protomorphosis")
    }
    assert epochs["psi_2000_polywater"] < epochs["barclay_protomorphosis"]


# --- platform_class ------------------------------------------------------


@pytest.mark.parametrize(
    ("platform_id", "platform_class"),
    [(TOS_PLATFORM, "constitution"), (TNG_PLATFORM, "galaxy")],
)
def test_itinerary_declares_a_schema_valid_platform_class(platform_id, platform_class):
    jsonschema = pytest.importorskip("jsonschema")
    with open(VOYAGE_SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    with open(voyage_config_path_for_platform(REPO_ROOT, platform_id)) as fh:
        document = json.load(fh)
    assert document["platform_class"] == platform_class
    jsonschema.validate(document, schema)
    # Widening the enum did not drop the cruise classes it already carried.
    assert {"expedition", "classic", "spirit", "mega"} <= set(
        schema["properties"]["platform_class"]["enum"],
    )


# --- the existing libraries are untouched --------------------------------


def test_existing_region_behaviour_unchanged():
    caribbean = load_region_profiles("caribbean")
    nordic = load_region_profiles("nordic")
    assert caribbean["USMIA"].syndromic_delay_days == 3
    assert caribbean["MXCZM"].wbe_enabled is False
    assert nordic["DKCPH"].syndromic_delay_days == 1
    # Adding a region changed neither the real ports' derived quantities...
    assert _detection_epoch(caribbean["USMIA"]) is not None
    # ...nor the ordering the paper's claim rests on.
    assert _detection_epoch(caribbean["MXCZM"]) > _detection_epoch(nordic["DKCPH"])
