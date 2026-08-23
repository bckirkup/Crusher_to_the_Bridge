"""Cited named scenarios for the deterministic shore model."""

from __future__ import annotations

from dataclasses import replace
from math import exp, isfinite

import numpy as np
import pytest

from picard_framework.analysis.shore import (
    NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO,
    NORWALK_GI_SHORE_SCENARIO,
    ParameterProvenance,
    PortCallImportation,
    ShoreTransmissionScenario,
    benefit_surface,
    evaluate_counterfactual,
)

NUMERIC_FIELDS = (
    "r_shore",
    "r_shore_grid",
    "generation_median_hours",
    "generation_sigma",
    "generation_max_hours",
    "residual_importation_fraction",
    "residual_importation_fraction_grid",
    "case_threshold",
    "case_threshold_grid",
)


def _scenario(**updates: object) -> ShoreTransmissionScenario:
    return replace(NORWALK_GI_SHORE_SCENARIO, **updates)


def _importation() -> PortCallImportation:
    return PortCallImportation(
        port_id="USMIA",
        pathogen_id="norwalk_gi",
        epoch_hours=24.0,
        strain_importations={
            "GII.4": tuple(2.0 for _ in range(120)),
            "GII.17": tuple(1.0 for _ in range(120)),
        },
        ship_detection_epoch=0,
    )


class TestNorovirusScenario:
    """The named scenario keeps values and provenance auditable."""

    def test_values_and_provenance_are_citable(self) -> None:
        scenario = NORWALK_GI_SHORE_SCENARIO
        assert scenario.pathogen_id == "norwalk_gi"
        assert scenario.r_shore == pytest.approx(1.6)
        assert scenario.r_shore_grid == (1.1, 1.3, 1.6, 2.0, 2.75)
        assert scenario.generation_median_hours == pytest.approx(44.6)
        assert scenario.generation_sigma == pytest.approx(0.47)
        assert scenario.generation_max_hours == pytest.approx(192.0)
        assert scenario.residual_importation_fraction == pytest.approx(0.3)
        assert scenario.residual_importation_fraction_grid == (0.1, 0.3, 0.5, 0.8)
        assert scenario.case_threshold == pytest.approx(3.0)
        assert scenario.case_threshold_grid == (1.0, 3.0, 5.0, 10.0)
        assert exp(scenario.generation_sigma) == pytest.approx(1.60, rel=1e-4)

        assert all(
            isinstance(scenario.provenance[field], ParameterProvenance)
            and scenario.provenance[field].source_text.strip()
            for field in NUMERIC_FIELDS
        )
        assert {
            field
            for field, record in scenario.provenance.items()
            if record.anchored
        } == {
            "generation_median_hours",
            "generation_sigma",
        }
        assert {
            field
            for field, record in scenario.provenance.items()
            if record.anchoring == "unanchored"
        } == {
            "residual_importation_fraction",
            "residual_importation_fraction_grid",
            "case_threshold",
            "case_threshold_grid",
        }
        assert {
            field
            for field, record in scenario.provenance.items()
            if record.anchoring == "cited_range_author_selected"
        } == {"r_shore", "r_shore_grid"}
        assert {
            field
            for field, record in scenario.provenance.items()
            if record.anchoring == "modelling_choice"
        } == {"generation_max_hours"}
        assert "Harris et al. 2014" in scenario.provenance["generation_sigma"].source_text
        assert "not attributed" in scenario.provenance[
            "generation_max_hours"
        ].source_text
        assert "Steele et al. 2020" in scenario.provenance["r_shore"].source_text
        assert "Gaythorpe et al. 2018" in scenario.provenance["r_shore"].source_text
        assert scenario.provenance["residual_importation_fraction"].semantics["0.3"]
        assert scenario.provenance["case_threshold_grid"].semantics["10"]
        for alternative in (NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO,):
            assert set(alternative.provenance) == set(NUMERIC_FIELDS)
            assert all(
                record.source_text.strip()
                for record in alternative.provenance.values()
            )
            assert {
                field
                for field, record in alternative.provenance.items()
                if record.anchoring == "modelling_choice"
            } == {
                "generation_median_hours",
                "generation_sigma",
                "generation_max_hours",
            }

    def test_grids_are_sorted_unique_and_include_centres(self) -> None:
        scenario = NORWALK_GI_SHORE_SCENARIO
        for field, central in (
            ("r_shore_grid", scenario.r_shore),
            (
                "residual_importation_fraction_grid",
                scenario.residual_importation_fraction,
            ),
            ("case_threshold_grid", scenario.case_threshold),
        ):
            values = getattr(scenario, field)
            assert values == tuple(sorted(set(values)))
            assert central in values

    def test_central_parameters_are_built_for_caller_population(self) -> None:
        parameters = NORWALK_GI_SHORE_SCENARIO.renewal_parameters(321_000)
        assert parameters.population == 321_000
        assert parameters.r_shore == pytest.approx(1.6)
        assert parameters.generation_median_hours == pytest.approx(44.6)
        assert parameters.generation_sigma == pytest.approx(0.47)
        assert parameters.generation_max_hours == pytest.approx(192.0)

    def test_scenario_drives_surface_and_counterfactual(self) -> None:
        scenario = NORWALK_GI_SHORE_SCENARIO
        surface = benefit_surface(
            _importation(),
            r_shore_grid=scenario.r_shore_grid,
            importation_multiplier_grid=(0.5, 1.0),
            generation_median_hours=scenario.generation_median_hours,
            generation_sigma=scenario.generation_sigma,
            generation_max_hours=scenario.generation_max_hours,
            population=200_000,
            residual_importation_fraction=scenario.residual_importation_fraction,
            case_threshold=scenario.case_threshold,
        )
        rows = surface["rows"]
        assert len(rows) == len(scenario.r_shore_grid) * 2
        assert all(isfinite(row["benefit"]) for row in rows)
        assert all(row["total_ship_arm"] >= 0.0 for row in rows)
        assert all(row["total_port_arm"] >= 0.0 for row in rows)
        assert len({row["total_port_arm"] for row in rows}) > 2

        result = evaluate_counterfactual(
            _importation(),
            scenario.renewal_parameters(200_000),
            residual_importation_fraction=scenario.residual_importation_fraction,
            case_threshold=scenario.case_threshold,
        )
        assert np.all(np.isfinite(result.ship_arm.trajectory))
        assert np.all(np.isfinite(result.port_arm.trajectory))
        assert result.total_ship_arm >= 0.0
        assert result.total_port_arm >= 0.0
        assert result.port_arm.unbounded_growth
        assert result.port_arm.depletion_regime
        assert result.benefit == pytest.approx(
            result.total_port_arm - result.total_ship_arm
        )

    def test_environmental_generation_scenario_changes_benefit_direction(self) -> None:
        central = NORWALK_GI_SHORE_SCENARIO
        environmental = NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO
        importation = _importation()
        central_result = evaluate_counterfactual(
            importation,
            central.renewal_parameters(200_000),
            residual_importation_fraction=central.residual_importation_fraction,
            case_threshold=central.case_threshold,
        )
        environmental_result = evaluate_counterfactual(
            importation,
            environmental.renewal_parameters(200_000),
            residual_importation_fraction=environmental.residual_importation_fraction,
            case_threshold=environmental.case_threshold,
        )
        assert environmental.generation_median_hours > central.generation_median_hours
        assert environmental_result.benefit < central_result.benefit
        assert abs(environmental_result.benefit - central_result.benefit) > 1.0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("r_shore", -1.0, "r_shore"),
        ("generation_median_hours", 0.0, "generation_median_hours"),
        ("generation_sigma", 0.0, "generation_sigma"),
        ("generation_max_hours", 0.0, "generation_max_hours"),
        ("residual_importation_fraction", 1.1, "residual_importation_fraction"),
        ("case_threshold", -1.0, "case_threshold"),
    ],
)
def test_scenario_rejects_invalid_central_values(
    field: str,
    value: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _scenario(**{field: value})


def test_scenario_rejects_nonfinite_values_and_empty_names() -> None:
    with pytest.raises(ValueError, match="finite"):
        _scenario(r_shore=float("inf"))
    with pytest.raises(ValueError, match="pathogen_id"):
        _scenario(pathogen_id="")
    with pytest.raises(ValueError, match="pathogen_id"):
        _scenario(name="")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("r_shore_grid", (), "non-empty"),
        ("r_shore_grid", (1.3, 1.1, 1.6), "sorted"),
        ("r_shore_grid", (1.1, 1.3, 1.3, 1.6), "sorted"),
        ("r_shore_grid", (1.1, 1.3), "central"),
        (
            "residual_importation_fraction_grid",
            (0.1, float("inf")),
            "finite",
        ),
        ("case_threshold_grid", (1.0, 5.0, 3.0), "sorted"),
    ],
)
def test_scenario_rejects_invalid_grids(
    field: str,
    value: tuple[float, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _scenario(**{field: value})


def test_scenario_requires_complete_nonempty_provenance() -> None:
    with pytest.raises(ValueError, match="exactly"):
        _scenario(provenance={})
    records = dict(NORWALK_GI_SHORE_SCENARIO.provenance)
    records["r_shore"] = ParameterProvenance("", "unanchored")
    with pytest.raises(ValueError, match="source_text"):
        _scenario(provenance=records)
    records["r_shore"] = ParameterProvenance(
        "author",
        "unanchored",
        semantics={"": "missing key"},
    )
    with pytest.raises(ValueError, match="semantics"):
        _scenario(provenance=records)
