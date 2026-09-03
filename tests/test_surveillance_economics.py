"""Behavioural tests for Paper 3 surveillance economics post-processing."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from crusher_labs.cost_ledger import (
    CATEGORY_SURVEILLANCE,
    CostLedger,
)
from crusher_labs.cost_ledger import (
    CONTRIBUTION_MEDIA as LEDGER_MEDIA,
)
from crusher_labs.cost_ledger import (
    CONTRIBUTION_PAYERS as LEDGER_PAYERS,
)
from picard_framework.analysis.economics import (
    COMMUNITIES,
    CONTRIBUTION_MEDIA,
    CONTRIBUTION_PAYERS,
    CostAllocation,
    cost_shares_for_scenario,
    load_scenario_from_fleet_config,
    load_surveillance_scenario,
    load_surveillance_scenarios,
    sweep_willingness_to_pay,
    willingness_to_pay,
)
from picard_framework.analysis.economics import surveillance as surveillance_module
from picard_framework.analysis.economics.surveillance import BenefitSplit
from picard_framework.analysis.sentinel.port_profiles import capability_for
from picard_framework.analysis.shore import (
    NORWALK_GI_SHORE_SCENARIO,
    PortCallImportation,
    benefit_surface,
    evaluate_counterfactual,
)
from presidio.run_spec import PresidioRunSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_PATH = REPO_ROOT / "presidio" / "data" / "economics" / "surveillance_scenarios.json"
RESOURCE_COSTS_PATH = REPO_ROOT / "data" / "config" / "resource_costs.json"
FLEET_CONFIG = REPO_ROOT / "presidio" / "data" / "config" / "minimal_surveillance_fleet.json"
FLEET_CONFIGS = sorted(
    (REPO_ROOT / "presidio" / "data" / "config").glob("*surveillance_fleet.json")
)


def _conversion_rates() -> tuple[float, float]:
    costs = json.loads(RESOURCE_COSTS_PATH.read_text(encoding="utf-8"))
    media = costs["contribution_media"]
    return (
        media["labour_hours"]["conversion_rate_usd_per_unit"],
        media["consumables"]["conversion_rate_usd_per_unit"],
    )


def _importation(port_id: str = "USMIA", horizon: int = 40) -> PortCallImportation:
    return PortCallImportation(
        port_id=port_id,
        pathogen_id="norwalk_gi",
        epoch_hours=24.0,
        strain_importations={"GII.4": tuple(1.5 for _ in range(horizon))},
        ship_detection_epoch=2,
    )


def _shore_result():
    capability = capability_for("USMIA")
    return evaluate_counterfactual(
        _importation(horizon=24),
        NORWALK_GI_SHORE_SCENARIO.renewal_parameters(capability.population),
        residual_importation_fraction=0.3,
        case_threshold=3,
        capability=capability,
        surveillance_label="norovirus",
    )


def test_all_scenarios_load_and_amortise_by_ships_and_voyages() -> None:
    scenarios = load_surveillance_scenarios(str(SCENARIO_PATH))
    assert set(scenarios) == {"baseline", "minimal", "moderate", "full", "fleet_network"}
    for scenario in scenarios.values():
        expected = scenario.annual_cost_usd / scenario.ships_covered / scenario.voyages_per_year
        assert scenario.per_voyage_programme_cost_usd == pytest.approx(expected)
        assert scenario.voyages_per_year in scenario.voyages_per_year_sweep
        doubled_ships = replace(scenario, ships_covered=scenario.ships_covered * 2)
        doubled_voyages = replace(scenario, voyages_per_year=scenario.voyages_per_year * 2)
        assert doubled_ships.per_voyage_programme_cost_usd == pytest.approx(expected / 2)
        assert doubled_voyages.per_voyage_programme_cost_usd == pytest.approx(expected / 2)

    fleet_scenario = load_scenario_from_fleet_config(str(FLEET_CONFIG))
    assert fleet_scenario.scenario_id == "minimal"
    for fleet_config in FLEET_CONFIGS:
        spec = PresidioRunSpec.from_fleet_json(REPO_ROOT.as_posix(), str(fleet_config))
        assert spec.economics_path.endswith("presidio/data/economics/fleet_economics.json")
    with pytest.raises(ValueError, match="unknown surveillance scenario"):
        load_surveillance_scenario(str(SCENARIO_PATH), "missing")


def test_scenario_validation_rejects_zero_voyages() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    scenario_cls = type(scenario)
    with pytest.raises(ValueError, match="voyages_per_year"):
        scenario_cls(
            scenario_id=scenario.scenario_id,
            label=scenario.label,
            onboard_capability=scenario.onboard_capability,
            ashore_capability=scenario.ashore_capability,
            ships_covered=scenario.ships_covered,
            annual_cost_usd=scenario.annual_cost_usd,
            voyages_per_year=0.0,
            voyages_per_year_sweep=scenario.voyages_per_year_sweep,
            allocations=scenario.allocations,
            provenance=scenario.provenance,
            scope_note=scenario.scope_note,
        )


def test_real_shore_counterfactual_flows_into_signed_benefit_split() -> None:
    result = _shore_result()
    assert math.isfinite(result.total_ship_arm)
    assert result.total_ship_arm >= 0.0
    assert math.isfinite(result.total_port_arm)
    assert result.total_port_arm >= 0.0
    assert result.benefit == pytest.approx(result.total_port_arm - result.total_ship_arm)

    split = BenefitSplit.from_counterfactuals([result], afloat_cases_averted=12.0)
    assert split.shore_cases_averted == pytest.approx(result.benefit)
    assert split.total_cases_averted == pytest.approx(result.benefit + 12.0)
    assert split.shore_benefit_share is not None
    assert split.afloat_benefit_share is not None
    assert split.shore_benefit_share + split.afloat_benefit_share == pytest.approx(1.0)


def test_shore_surface_is_populated_and_sensitive_to_scenario_r_grid() -> None:
    capability = capability_for("USMIA")
    surface = benefit_surface(
        _importation(horizon=24),
        r_shore_grid=NORWALK_GI_SHORE_SCENARIO.r_shore_grid,
        importation_multiplier_grid=(0.5, 1.0, 2.0),
        generation_median_hours=NORWALK_GI_SHORE_SCENARIO.generation_median_hours,
        generation_sigma=NORWALK_GI_SHORE_SCENARIO.generation_sigma,
        generation_max_hours=NORWALK_GI_SHORE_SCENARIO.generation_max_hours,
        population=capability.population,
        residual_importation_fraction=0.3,
        case_threshold=3,
        capability=capability,
        surveillance_label="norovirus",
    )
    assert len(surface["rows"]) == 15
    assert all(math.isfinite(row["benefit"]) for row in surface["rows"])
    summary = surface["summary"]
    assert summary["benefit_fraction_cv_across_r"] < summary["arm_total_cv_across_r"]
    assert summary["cv_ratio_across_r"] < 0.5


def test_benefit_split_handles_zero_and_nonpositive_ratio_denominators() -> None:
    zero = BenefitSplit(shore_cases_averted=0.0, afloat_cases_averted=0.0)
    assert zero.shore_afloat_ratio is None
    assert zero.shore_benefit_share is None
    assert zero.afloat_benefit_share is None

    negative_denominator = BenefitSplit(shore_cases_averted=2.0, afloat_cases_averted=-4.0)
    assert negative_denominator.shore_afloat_ratio is None
    assert negative_denominator.shore_benefit_share is None
    assert negative_denominator.afloat_benefit_share is None
    positive_denominator = BenefitSplit(shore_cases_averted=2.0, afloat_cases_averted=4.0)
    assert positive_denominator.shore_afloat_ratio == pytest.approx(0.5)


def test_willingness_to_pay_rejects_unavailable_shares_and_bad_maps() -> None:
    costs = {
        "ship_operator": {"share_of_total": 0.5},
        "port_authority": {"share_of_total": 0.3},
        "public_health_agency": {"share_of_total": 0.2},
    }
    valid_map = {
        "ship_operator": "afloat",
        "port_authority": "shore",
        "public_health_agency": "shore",
    }
    unavailable_splits = (
        BenefitSplit(shore_cases_averted=0.0, afloat_cases_averted=0.0),
        BenefitSplit(shore_cases_averted=1.0, afloat_cases_averted=-2.0),
    )
    for split in unavailable_splits:
        with pytest.raises(ValueError, match="non-positive"):
            willingness_to_pay(costs, valid_map, split)

    incomplete_map = {"ship_operator": "afloat"}
    unit_split = BenefitSplit(1.0, 1.0)
    with pytest.raises(ValueError, match="exactly every payer"):
        willingness_to_pay(costs, incomplete_map, unit_split)

    unknown_community_map = {**valid_map, "port_authority": "unknown"}
    with pytest.raises(ValueError, match="unknown payer community"):
        willingness_to_pay(costs, unknown_community_map, unit_split)

    with pytest.raises(ValueError, match="unknown port community"):
        willingness_to_pay(
            costs,
            valid_map,
            unit_split,
            port_community="typo",
        )

    costs_missing_share = {
        **costs,
        "port_authority": {"total_usd": 3.0},
    }
    with pytest.raises(ValueError, match="share_of_total"):
        willingness_to_pay(costs_missing_share, valid_map, unit_split)

    costs_with_extra = {**costs, "unexpected": {"share_of_total": 0.1}}
    with pytest.raises(ValueError, match="exactly every payer"):
        willingness_to_pay(costs_with_extra, valid_map, unit_split)

    costs_with_object = {
        **costs,
        "port_authority": object(),
    }
    with pytest.raises(TypeError, match="scalar share or ledger report"):
        willingness_to_pay(costs_with_object, valid_map, unit_split)


def test_labour_sweep_changes_port_cost_but_not_benefit_share() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    split = BenefitSplit(shore_cases_averted=9.0, afloat_cases_averted=11.0)
    payer_communities = {
        "ship_operator": "afloat",
        "port_authority": "shore",
        "public_health_agency": "shore",
    }
    sweep = sweep_willingness_to_pay(
        scenario,
        payer_communities,
        split,
        (10.0, 50.0, 100.0, 200.0),
        consumables_conversion_rate=10.0,
    )
    assert sweep.cost_share_monotone
    assert sweep.crossing_bracketing_rates == (100.0, 200.0)
    assert sweep.results[0].pays_own_way
    assert not sweep.results[-1].pays_own_way
    assert sweep.results[-1].cost_share > sweep.results[0].cost_share
    assert all(result.benefit_share == pytest.approx(split.shore_benefit_share) for result in sweep.results)


def test_cost_shares_have_all_payers_and_cash_only_total_is_rate_invariant() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    low = cost_shares_for_scenario(
        scenario,
        labour_conversion_rate=25.0,
        consumables_conversion_rate=10.0,
    )
    high = cost_shares_for_scenario(
        scenario,
        labour_conversion_rate=100.0,
        consumables_conversion_rate=10.0,
    )
    assert set(low) == {"ship_operator", "port_authority", "public_health_agency"}
    assert sum(report["share_of_total"] for report in low.values()) == pytest.approx(1.0)
    assert high["ship_operator"]["total_usd"] == pytest.approx(low["ship_operator"]["total_usd"])
    assert high["port_authority"]["total_usd"] > low["port_authority"]["total_usd"]

    direct = willingness_to_pay(
        {
            "ship_operator": {"share_of_total": 0.5},
            "port_authority": {"share_of_total": 0.4},
            "public_health_agency": {"share_of_total": 0.1},
        },
        {
            "ship_operator": "afloat",
            "port_authority": "shore",
            "public_health_agency": "shore",
        },
        BenefitSplit(shore_cases_averted=1.0, afloat_cases_averted=1.0),
    )
    assert direct.cost_share == pytest.approx(0.5)
    afloat = willingness_to_pay(
        {
            "ship_operator": 0.25,
            "port_authority": 0.5,
            "public_health_agency": 0.25,
        },
        {
            "ship_operator": "afloat",
            "port_authority": "shore",
            "public_health_agency": "shore",
        },
        BenefitSplit(shore_cases_averted=1.0, afloat_cases_averted=3.0),
        port_community="afloat",
    )
    assert afloat.benefit_share == pytest.approx(0.75)


def test_scenario_and_allocation_validation_guards() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    allocation = scenario.allocations[0]
    with pytest.raises(ValueError, match="unknown contribution payer"):
        CostAllocation("unknown", allocation.medium, 1.0, "source")
    with pytest.raises(ValueError, match="unknown contribution medium"):
        CostAllocation(allocation.payer, "unknown", 1.0, "source")
    with pytest.raises(ValueError, match="allocation quantity"):
        CostAllocation(allocation.payer, allocation.medium, -1.0, "source")
    with pytest.raises(ValueError, match="provenance"):
        CostAllocation(allocation.payer, allocation.medium, 1.0)

    for changes, message in (
        ({"ships_covered": 0}, "ships_covered"),
        ({"annual_cost_usd": -1.0}, "annual cost"),
        ({"voyages_per_year_sweep": (0.0,)}, "voyages_per_year_sweep"),
        ({"allocations": ()}, "allocation"),
        ({"scope_note": ""}, "scope_note"),
        ({"provenance": {}}, "provenance"),
    ):
        with pytest.raises(ValueError, match=message):
            replace(scenario, **changes)


def test_loader_rejects_duplicate_ids_and_requires_scope_note(monkeypatch) -> None:
    payload = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    payload["scenarios"] = [payload["scenarios"][0], payload["scenarios"][0]]
    monkeypatch.setattr(surveillance_module, "_load_json", lambda _: payload)
    with pytest.raises(ValueError, match="duplicate"):
        surveillance_module.load_surveillance_scenarios("unused")

    raw = dict(payload["scenarios"][0])
    raw.pop("scope_note", None)
    with pytest.raises(KeyError, match="scope_note"):
        surveillance_module._scenario_from_dict(raw)


def test_sweep_reports_no_crossing_and_nonmonotone_input() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    split = BenefitSplit(shore_cases_averted=0.9, afloat_cases_averted=0.1)
    communities = {
        "ship_operator": "afloat",
        "port_authority": "shore",
        "public_health_agency": "shore",
    }
    result = sweep_willingness_to_pay(
        scenario,
        communities,
        split,
        (100.0, 10.0),
        consumables_conversion_rate=10.0,
    )
    assert result.crossing_bracketing_rates is None
    assert not result.cost_share_monotone


def test_new_json_inputs_explicitly_exclude_variants_detected() -> None:
    paths = [SCENARIO_PATH, *Path(REPO_ROOT / "presidio" / "data" / "config").glob("*surveillance_fleet.json")]
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(payload).lower()
        def contains_forbidden_key(value: object) -> bool:
            if isinstance(value, dict):
                return "variants_detected" in value or any(
                    contains_forbidden_key(child) for child in value.values()
                )
            if isinstance(value, list):
                return any(contains_forbidden_key(child) for child in value)
            return False

        assert not contains_forbidden_key(payload)
        if path == SCENARIO_PATH:
            assert "variants detected" in text


def test_scenario_allocations_remain_in_medium_units() -> None:
    scenario = load_surveillance_scenario(str(SCENARIO_PATH), "minimal")
    records = [
        allocation.as_contribution(
            epoch=0,
            labour_conversion_rate=50.0,
            consumables_conversion_rate=10.0,
        )
        for allocation in scenario.allocations
    ]
    assert any(record.medium == "labour_hours" and record.quantity == 10.0 for record in records)
    assert all(math.isfinite(record.monetary_equivalent_usd) for record in records)


def test_central_allocations_reconcile_for_every_scenario() -> None:
    labour_rate, consumables_rate = _conversion_rates()
    scenarios = load_surveillance_scenarios(str(SCENARIO_PATH))
    for scenario in scenarios.values():
        ledger = CostLedger()
        for allocation in scenario.allocations:
            ledger.record_contribution(
                allocation.as_contribution(
                    epoch=0,
                    labour_conversion_rate=labour_rate,
                    consumables_conversion_rate=consumables_rate,
                )
            )
        ledger.debit(
            epoch=0,
            source="programme_cost",
            category=CATEGORY_SURVEILLANCE,
            financial_usd=scenario.per_voyage_programme_cost_usd,
        )
        reconciliation = ledger.contribution_reconciliation()
        assert reconciliation["contribution_total_usd"] == pytest.approx(
            scenario.per_voyage_programme_cost_usd
        )
        assert reconciliation["gap_usd"] == pytest.approx(0.0)


def test_shared_cost_vocabularies_are_single_source_of_truth() -> None:
    assert CONTRIBUTION_PAYERS is LEDGER_PAYERS
    assert CONTRIBUTION_MEDIA is LEDGER_MEDIA
    assert set(COMMUNITIES) == {"afloat", "shore"}
