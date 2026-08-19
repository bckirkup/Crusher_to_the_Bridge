"""Port public-health surveillance: universal generation, analysis-time ablation.

The contract under test is the one the fleet analysis depends on:

1. every port generates every channel, whatever its capability profile;
2. the signals are graded in the latent prevalence, not just non-constant;
3. capability and analyst ablation suppress channels *afterwards*, and an
   ablated port reads ``unknown`` rather than ``normal``;
4. the truth columns survive every ablation, because they are the comparison
   target and were never observable.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from picard_framework.analysis.sentinel.port_health import (
    ALERT_ELEVATED,
    ALERT_NORMAL,
    ALERT_OUTBREAK,
    ALERT_UNKNOWN,
    CHANNEL_GENOTYPING,
    CHANNEL_LAB,
    CHANNEL_SYNDROMIC,
    CHANNEL_WBE,
    CHANNELS,
    REPORTING_PATHWAYS,
    AlertThresholds,
    PortSurveillanceCapability,
    PrevalenceLink,
    ablate_series,
    ablate_state,
    alert_level_for,
    generate_port_series,
    generate_port_signals,
    resolve_channels,
    state_from_dict,
)
from picard_framework.analysis.sentinel.port_ledger import (
    ablate_ledger,
    build_port_ledger,
    hazards_from_itinerary,
    ledger_from_itinerary,
    port_signal_table,
    states_by_port,
)
from picard_framework.analysis.sentinel.port_ledger import (
    main as ledger_main,
)
from picard_framework.analysis.sentinel.port_profiles import (
    PROFILE_REGIONS,
    capability_for,
    capability_or_default,
    load_all_profiles,
    load_region_profiles,
)

try:  # pragma: no cover - exercised by the schema test module
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_SCHEMA = REPO_ROOT / "schemas" / "port_surveillance_ledger.schema.json"
PATHOGEN = "norovirus"
# The scan's hazard ladder: background, one-hot, and the outbreak stress cell.
HAZARD_LADDER = (0.0, 1e-4, 1e-3, 1.5e-2)
SCAN_PORTS = ("USMIA", "MXCZM", "MXCTM", "KYGEC")


def _capability(**overrides: Any) -> PortSurveillanceCapability:
    base: dict[str, Any] = {
        "port_id": "XXTST",
        "port_name": "Test Port",
        "region": "AMR",
        "population": 200_000,
        "syndromic_enabled": True,
        "syndromic_coverage": 0.6,
        "wbe_enabled": True,
        "wbe_assay": "qpcr",
        "wbe_frequency_days": 2.0,
        "lab_confirmation": True,
        "genotyping_available": True,
        "reports_to": "CDC_VSP",
    }
    base.update(overrides)
    return PortSurveillanceCapability(**base)


def _signals_for(prevalence: float, capability: PortSurveillanceCapability, seed: int = 7):
    return generate_port_signals(
        capability,
        pathogen=PATHOGEN,
        true_prevalence=prevalence,
        day_index=0,
        rng=np.random.default_rng(seed),
    )


# --- prevalence link -----------------------------------------------------


def test_hazard_prevalence_round_trips():
    link = PrevalenceLink()
    assert link.prevalence_from_hazard(link.hazard_from_prevalence(0.02)) == (
        pytest.approx(0.02)
    )


def test_prevalence_from_hazard_is_capped_at_one():
    assert PrevalenceLink().prevalence_from_hazard(10.0) == pytest.approx(1.0)


def test_scan_hazard_ladder_maps_into_plausible_prevalence():
    link = PrevalenceLink()
    prevalences = [link.prevalence_from_hazard(h) for h in HAZARD_LADDER]
    assert prevalences == sorted(prevalences)
    assert prevalences[1] < 0.01, prevalences
    assert prevalences[-1] < 0.5, prevalences


def test_municipal_dilution_is_weaker_than_a_holding_tank():
    """A port sees a far lower concentration than a ship at equal prevalence."""
    from picard_framework.analysis.sentinel.wastewater_assays import ShedLoadModel

    port = PrevalenceLink().gc_per_l(0.01)
    ship = ShedLoadModel().gc_per_l(0.01)
    assert port < ship
    assert ship / port > 3.0


# --- graded signal generation -------------------------------------------


def test_syndromic_rate_grades_with_prevalence():
    capability = _capability()
    rates = [
        _signals_for(p, capability).syndromic_rate_per_100k
        for p in (0.0, 0.001, 0.01, 0.05)
    ]
    assert rates == sorted(rates), rates
    assert rates[0] == pytest.approx(0.0)
    assert rates[-1] > 10.0 * rates[1], rates


def test_wbe_concentration_grades_with_prevalence():
    capability = _capability()
    observed = [
        _signals_for(p, capability).wbe_gc_per_l_observed
        for p in (1e-5, 1e-4, 1e-3, 1e-2)
    ]
    assert observed == sorted(observed), observed
    assert observed[-1] / observed[0] > 100.0, observed


def test_low_prevalence_falls_below_a_high_limit_of_detection():
    """The LOD is a live knob: a strict port misses what a sensitive one sees."""
    strict = _capability(wbe_lod_gc_per_l=1.0e7)
    sensitive = _capability(wbe_lod_gc_per_l=1.0e2)
    prevalence = 1e-5
    assert _signals_for(prevalence, strict).wbe_detected is False
    assert _signals_for(prevalence, sensitive).wbe_detected is True


def test_coverage_reduces_reported_cases_without_touching_truth():
    high = _capability(syndromic_coverage=0.9)
    low = _capability(syndromic_coverage=0.1)
    hi_state = _signals_for(0.01, high)
    lo_state = _signals_for(0.01, low)
    assert lo_state.syndromic_cases_reported < hi_state.syndromic_cases_reported
    assert lo_state.true_incidence_per_100k_day == pytest.approx(
        hi_state.true_incidence_per_100k_day,
    )


def test_population_does_not_move_the_true_rates():
    """Negative control: catchment size scales counts, not per-capita truth."""
    small = _signals_for(0.01, _capability(population=10_000))
    large = _signals_for(0.01, _capability(population=1_000_000))
    assert small.true_incidence_per_100k_day == pytest.approx(
        large.true_incidence_per_100k_day,
    )
    assert small.true_ww_gc_per_l == pytest.approx(large.true_ww_gc_per_l)


def test_signals_are_seeded_and_deterministic():
    capability = _capability()
    first = _signals_for(0.01, capability, seed=99)
    second = _signals_for(0.01, capability, seed=99)
    assert first == second


def test_signal_bounds_hold_across_the_ladder():
    capability = _capability()
    link = PrevalenceLink()
    for hazard in HAZARD_LADDER:
        state = _signals_for(link.prevalence_from_hazard(hazard), capability)
        assert 0.0 <= state.true_community_prevalence <= 1.0
        assert state.true_incidence_per_100k_day >= 0.0
        assert state.syndromic_cases_reported >= 0
        assert state.syndromic_cases_reported <= capability.population
        assert state.lab_confirmed_cases <= state.syndromic_cases_reported
        assert np.isfinite(state.wbe_gc_per_l_observed)
        assert state.alert_level in (ALERT_NORMAL, ALERT_ELEVATED, ALERT_OUTBREAK)


# --- universal generation (the user's requirement) -----------------------


def test_uninstrumented_port_still_generates_every_channel():
    """Cozumel runs no WBE and confirms nothing, yet the data exists."""
    capability = capability_for("MXCZM")
    assert capability.wbe_enabled is False
    assert capability.lab_confirmation is False
    state = _signals_for(0.01, capability)
    assert state.wbe_gc_per_l_observed is not None
    assert state.wbe_detected is not None
    assert state.lab_confirmed_cases is not None
    assert state.wbe_capable is False
    assert state.lab_capable is False


def test_unreportable_pathogen_still_generates_syndromic_cases():
    capability = _capability(syndromic_pathogens=("influenza",))
    state = _signals_for(0.01, capability)
    assert state.syndromic_capable is False
    assert state.syndromic_cases_reported > 0


def test_wbe_cadence_marks_sampling_days_without_gating_generation():
    capability = _capability(wbe_frequency_days=3.0)
    states = generate_port_series(
        capability,
        pathogen=PATHOGEN,
        prevalence_by_day=[0.01] * 9,
        rng=np.random.default_rng(3),
    )
    sampled = [s.day_index for s in states if s.wbe_sampled]
    assert sampled == [0, 3, 6]
    assert all(s.wbe_gc_per_l_observed is not None for s in states)


def test_reporting_delays_land_on_the_expected_dates():
    capability = _capability(syndromic_delay_days=3, lab_turnaround_days=2.0)
    state = generate_port_signals(
        capability,
        pathogen=PATHOGEN,
        true_prevalence=0.01,
        day_index=1,
        rng=np.random.default_rng(1),
        start_date=date(2026, 1, 10),
    )
    assert state.observation_date == "2026-01-11"
    assert state.syndromic_report_date == "2026-01-14"
    assert state.lab_result_date == "2026-01-13"


# --- alert levels --------------------------------------------------------


def test_alert_level_grades_with_reported_rate():
    capability = _capability()
    levels = [
        alert_level_for(capability, syndromic_rate_per_100k=rate, wbe_gc_per_l=0.0)
        for rate in (0.0, 60.0, 500.0)
    ]
    assert levels == [ALERT_NORMAL, ALERT_ELEVATED, ALERT_OUTBREAK]


def test_wastewater_alone_can_escalate_but_not_declare_an_outbreak():
    capability = _capability()
    level = alert_level_for(
        capability,
        syndromic_rate_per_100k=None,
        wbe_gc_per_l=1.0e8,
    )
    assert level == ALERT_ELEVATED


def test_wastewater_detection_alone_does_not_escalate():
    """Municipal qPCR detects background daily; only a rise is informative."""
    capability = _capability()
    state = _signals_for(1e-4, capability)
    assert state.wbe_detected is True
    assert state.alert_level == ALERT_NORMAL


def test_off_cadence_days_cannot_raise_a_wastewater_alert():
    """A high concentration only escalates on days the port ran the assay."""
    capability = _capability(
        wbe_frequency_days=7.0,
        syndromic_coverage=0.0,
    )
    states = generate_port_series(
        capability,
        pathogen=PATHOGEN,
        prevalence_by_day=[0.15] * 8,
        rng=np.random.default_rng(11),
    )
    sampled = [s for s in states if s.wbe_sampled]
    unsampled = [s for s in states if not s.wbe_sampled]
    assert sampled
    assert unsampled
    assert all(s.alert_level == ALERT_ELEVATED for s in sampled)
    assert all(s.alert_level == ALERT_NORMAL for s in unsampled)
    # The counterfactual concentration is still generated for every day.
    assert all(s.wbe_gc_per_l_observed is not None for s in unsampled)


def test_no_channel_reads_unknown_not_normal():
    capability = _capability()
    level = alert_level_for(
        capability,
        syndromic_rate_per_100k=None,
        wbe_gc_per_l=None,
    )
    assert level == ALERT_UNKNOWN


def test_alert_thresholds_reject_inverted_bands():
    with pytest.raises(ValueError, match="must exceed elevated"):
        AlertThresholds(elevated_rate_per_100k=100.0, outbreak_rate_per_100k=10.0)


# --- analysis-time ablation ---------------------------------------------


def test_capability_ablation_masks_only_unsupported_channels():
    capability = capability_for("MXCZM")  # syndromic yes, WBE/lab/typing no
    state = ablate_state(_signals_for(0.01, capability), capability)
    assert state.syndromic_cases_reported is not None
    assert state.wbe_gc_per_l_observed is None
    assert state.wbe_detected is None
    assert state.lab_confirmed_cases is None


def test_channel_selection_ablates_a_capable_port():
    capability = _capability()
    state = ablate_state(
        _signals_for(0.01, capability),
        capability,
        channels=[CHANNEL_WBE],
    )
    assert state.wbe_gc_per_l_observed is not None
    assert state.syndromic_cases_reported is None
    assert state.lab_confirmed_cases is None
    assert state.alert_level == ALERT_NORMAL


def test_full_ablation_reads_unknown():
    capability = _capability()
    state = ablate_state(_signals_for(0.05, capability), capability, channels=[])
    assert state.alert_level == ALERT_UNKNOWN


def test_ignoring_capability_recovers_the_counterfactual_channel():
    capability = capability_for("MXCZM")
    generated = _signals_for(0.01, capability)
    realistic = ablate_state(generated, capability)
    counterfactual = ablate_state(generated, capability, respect_capability=False)
    assert realistic.wbe_gc_per_l_observed is None
    assert counterfactual.wbe_gc_per_l_observed == pytest.approx(
        generated.wbe_gc_per_l_observed,
    )


def test_ablation_never_touches_the_truth_columns():
    capability = _capability()
    generated = _signals_for(0.02, capability)
    ablated = ablate_state(generated, capability, channels=[])
    assert ablated.true_community_prevalence == generated.true_community_prevalence
    assert ablated.true_incidence_per_100k_day == (
        generated.true_incidence_per_100k_day
    )
    assert ablated.true_ww_gc_per_l == generated.true_ww_gc_per_l


def test_ablate_series_applies_to_every_day():
    capability = _capability()
    states = generate_port_series(
        capability,
        pathogen=PATHOGEN,
        prevalence_by_day=[0.01] * 5,
        rng=np.random.default_rng(11),
    )
    ablated = ablate_series(states, capability, channels=[CHANNEL_SYNDROMIC])
    assert len(ablated) == len(states)
    assert all(s.wbe_gc_per_l_observed is None for s in ablated)


def test_unknown_channel_is_rejected():
    with pytest.raises(ValueError, match="unknown port channels"):
        resolve_channels(["syndromic", "telepathy"])


def test_resolve_channels_defaults_to_everything():
    assert resolve_channels(None) == CHANNELS


def test_capability_supports_each_known_channel():
    capability = _capability()
    for channel in (CHANNEL_SYNDROMIC, CHANNEL_WBE, CHANNEL_LAB, CHANNEL_GENOTYPING):
        assert capability.supports(channel, PATHOGEN) is True


# --- profile libraries ---------------------------------------------------


def test_every_region_library_loads():
    for region in PROFILE_REGIONS:
        profiles = load_region_profiles(region)
        assert profiles, region


def test_scan_ports_all_have_profiles():
    catalog = load_all_profiles()
    missing = [p for p in SCAN_PORTS if p not in catalog]
    assert missing == []


def test_profile_reporting_pathways_are_known():
    for capability in load_all_profiles().values():
        assert capability.reports_to in REPORTING_PATHWAYS


def test_caribbean_is_the_surveillance_desert():
    """The paper's claim, as a data assertion rather than prose."""
    caribbean = load_region_profiles("caribbean")
    nordic = load_region_profiles("nordic")
    carib_wbe = sum(1 for c in caribbean.values() if c.wbe_enabled) / len(caribbean)
    nordic_wbe = sum(1 for c in nordic.values() if c.wbe_enabled) / len(nordic)
    assert carib_wbe < 0.5
    assert nordic_wbe > 0.5


def test_unknown_region_is_rejected():
    with pytest.raises(ValueError, match="unknown port profile region"):
        load_region_profiles("antarctic")


def test_unlisted_port_gets_a_local_only_authority():
    capability = capability_or_default("ZZZZZ", population=5_000)
    assert capability.reports_to == "local_only"
    assert capability.wbe_enabled is False
    assert capability.population == 5_000


def test_capability_metadata_is_flat_and_complete():
    row = capability_for("USMIA").to_metadata()
    assert row["reports_to"] == "CDC_VSP"
    assert row["wbe_enabled"] is True
    assert isinstance(row["population"], int)


# --- ledgers -------------------------------------------------------------


def _scan_ledger(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "port_hazards": {"USMIA": 1e-4, "MXCZM": 1e-3, "KYGEC": 0.0},
        "pathogen": PATHOGEN,
        "n_days": 7,
        "seed": 501,
    }
    kwargs.update(overrides)
    return build_port_ledger(**kwargs)


def test_ledger_covers_every_port_every_day():
    ledger = _scan_ledger()
    assert len(ledger["observations"]) == 21
    assert set(states_by_port(ledger)) == {"USMIA", "MXCZM", "KYGEC"}


def test_ledger_is_seeded_and_deterministic():
    first = _scan_ledger()
    second = _scan_ledger()
    assert first == second


def test_ledger_seed_changes_the_signals_not_the_truth():
    baseline = _scan_ledger()
    other = _scan_ledger(seed=502)
    assert other["observations"] != baseline["observations"]
    truth = [r["true_community_prevalence"] for r in baseline["observations"]]
    assert [r["true_community_prevalence"] for r in other["observations"]] == truth


def test_ledger_ports_are_independent_streams():
    """Adding a port must not renumber another port's draws."""
    baseline = _scan_ledger()
    extended = _scan_ledger(
        port_hazards={"USMIA": 1e-4, "MXCZM": 1e-3, "KYGEC": 0.0, "BSNAS": 1e-3},
    )
    before = [r for r in baseline["observations"] if r["port_id"] == "USMIA"]
    after = [r for r in extended["observations"] if r["port_id"] == "USMIA"]
    assert before == after


def test_hotter_port_reports_more_than_a_quiet_one():
    table = {row["port_id"]: row for row in port_signal_table(_scan_ledger())}
    assert table["MXCZM"]["mean_syndromic_rate_per_100k"] > (
        table["USMIA"]["mean_syndromic_rate_per_100k"]
    )
    assert table["KYGEC"]["mean_syndromic_rate_per_100k"] == pytest.approx(0.0)


def test_signal_table_excludes_ablated_channels_rather_than_zeroing_them():
    view = ablate_ledger(_scan_ledger(), channels=[CHANNEL_SYNDROMIC])
    rows = {row["port_id"]: row for row in port_signal_table(view)}
    assert rows["USMIA"]["wbe_detection_fraction"] is None
    assert rows["USMIA"]["mean_observed_log10_gc_per_l"] is None
    assert rows["USMIA"]["mean_syndromic_rate_per_100k"] is not None


def test_signal_table_reports_wbe_only_where_the_port_samples():
    rows = {row["port_id"]: row for row in port_signal_table(ablate_ledger(_scan_ledger()))}
    assert rows["USMIA"]["n_wbe_samples"] > 0
    assert rows["MXCZM"]["n_wbe_samples"] == 0


def test_ablated_ledger_records_its_own_provenance():
    view = ablate_ledger(_scan_ledger(), channels=[CHANNEL_WBE, CHANNEL_LAB])
    assert view["ablation"]["channels"] == [CHANNEL_WBE, CHANNEL_LAB]
    assert view["ablation"]["respect_capability"] is True


def test_ablation_leaves_the_generated_ledger_untouched():
    ledger = _scan_ledger()
    rows = json.dumps(ledger["observations"], sort_keys=True)
    ablate_ledger(ledger, channels=[])
    assert json.dumps(ledger["observations"], sort_keys=True) == rows


def test_itinerary_hazards_collapse_repeated_home_port_calls():
    days = [
        {"port_id": "USMIA", "shore_infection_probability": 1e-4},
        {"port_id": "", "shore_infection_probability": 0.0},
        {"port_id": "MXCZM", "shore_infection_probability": 1e-3},
        {"port_id": "USMIA", "shore_infection_probability": 1e-4},
    ]
    assert hazards_from_itinerary(days) == {"USMIA": 1e-4, "MXCZM": 1e-3}


def test_ledger_from_itinerary_uses_the_voyage_length():
    days = [
        {"port_id": "USMIA", "shore_infection_probability": 1e-4},
        {"port_id": "MXCZM", "shore_infection_probability": 1e-3},
    ]
    ledger = ledger_from_itinerary(days, pathogen=PATHOGEN, seed=5)
    assert ledger["n_days"] == 2
    assert len(ledger["observations"]) == 4


def test_state_row_round_trips():
    state = _signals_for(0.01, _capability())
    assert state_from_dict(state.as_row()) == state


def test_state_row_rejects_an_unknown_alert_level():
    row = _signals_for(0.01, _capability()).as_row()
    row["alert_level"] = "condition_red"
    with pytest.raises(ValueError, match="unknown alert_level"):
        state_from_dict(row)


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_ledger_and_ablated_view_validate_against_the_schema():
    schema = json.loads(LEDGER_SCHEMA.read_text(encoding="utf-8"))
    ledger = _scan_ledger()
    jsonschema.validate(ledger, schema)
    jsonschema.validate(ablate_ledger(ledger, channels=[CHANNEL_WBE]), schema)


def test_cli_writes_ledger_analysis_view_and_table(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = ledger_main([
        "--hazard", "USMIA=0.0001",
        "--hazard", "MXCZM=0.001",
        "--pathogen", PATHOGEN,
        "--days", "4",
        "--channels", "syndromic,wbe",
        "--out", "out",
    ])
    assert code == 0
    written = {p.name for p in (tmp_path / "out").iterdir()}
    assert written == {
        "port_surveillance_ledger.json",
        "port_surveillance_analysis.json",
        "port_signal_table.json",
    }
    view = json.loads(
        (tmp_path / "out" / "port_surveillance_analysis.json").read_text(
            encoding="utf-8",
        ),
    )
    assert view["ablation"]["channels"] == ["syndromic", "wbe"]
    assert all(row["lab_confirmed_cases"] is None for row in view["observations"])


def test_cli_rejects_a_malformed_hazard():
    with pytest.raises(SystemExit):
        ledger_main(["--hazard", "USMIA", "--pathogen", PATHOGEN])


def test_cli_requires_an_explicit_pathogen():
    with pytest.raises(SystemExit):
        ledger_main(["--hazard", "USMIA=0.0001"])
