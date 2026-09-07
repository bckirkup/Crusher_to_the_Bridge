"""A run's complement is its hull's, and only one module decides that.

The defect these cover: every bounded screen and feasibility gate ran 450
agents on ``mega_cruise_5000``, a hull declaring 5,000 passengers and 2,000
crew, because the run spec never coupled complement to platform and two
independent complement tables existed -- the campaign's and the observation
model's default of 450.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    _PLATFORM_DEFAULT_AGENTS,
)
from simulation_utils import platform_complement
from simulation_utils.platform_complement import (
    PLATFORMS,
    declared_complement,
    declared_total,
    declaring_platforms,
    require_declared_total,
)
from telemetry_buffer.observation_model import vsp_class_era_scoring
from telemetry_buffer.observation_model.admissible_region import Design


class TestDeclaredComplement:
    def test_every_declaring_hull_splits_into_passengers_and_crew(self) -> None:
        hulls = declaring_platforms()
        assert hulls, "no platform declares a complement"
        for hull in hulls:
            passengers, crew = declared_complement(hull)
            assert passengers > 0
            assert crew > 0
            assert declared_total(hull) == passengers + crew

    def test_the_declaration_is_the_layout_and_not_the_id(self) -> None:
        """The id is not the complement, so it must not be parsed as one."""
        for hull in declaring_platforms():
            layout = json.loads(
                (PLATFORMS / hull / "spatial_layout.json").read_text(
                    encoding="utf-8",
                ),
            )
            declared = layout["nominal_complement"]
            assert declared_complement(hull) == (
                int(declared["passengers"]),
                int(declared["crew"]),
            )

    def test_a_hull_without_a_declaration_is_refused_not_defaulted(self) -> None:
        naval = [
            path.name
            for path in Path(PLATFORMS).iterdir()
            if (path / "spatial_layout.json").is_file()
            and path.name not in declaring_platforms()
        ]
        assert naval, "expected platforms that declare no complement"
        with pytest.raises(RuntimeError, match="nominal_complement"):
            declared_total(naval[0])

    @pytest.mark.parametrize(
        "declared",
        [
            {"passengers": 0, "crew": 150},
            {"passengers": -300, "crew": 150},
            {"passengers": 300.5, "crew": 150},
            {"passengers": True, "crew": 150},
            {"passengers": "300", "crew": 150},
            {"passengers": 300, "crew": 0},
        ],
    )
    def test_a_malformed_berth_count_is_refused(
        self,
        monkeypatch: pytest.MonkeyPatch,
        declared: dict[str, object],
    ) -> None:
        """A complement is people, so nothing that is not a count survives."""
        monkeypatch.setattr(
            platform_complement, "_declared_block", lambda _: declared,
        )
        with pytest.raises(RuntimeError, match="positive whole number"):
            declared_total("expedition_cruise_450")

    def test_a_hull_the_repository_does_not_carry_is_refused(self) -> None:
        with pytest.raises(FileNotFoundError, match="spatial_layout"):
            declared_total("no_such_hull_9999")


class TestOneSourceOfTruth:
    def test_a4_bins_on_the_same_declaration_a_run_sails(self) -> None:
        """One reader, so the binned class and the sailed class agree."""
        for hull in vsp_class_era_scoring.SCORED_HULLS:
            assert (
                vsp_class_era_scoring.HULL_PASSENGER_CAPACITY[hull]
                == declared_complement(hull)[0]
            )

    def test_the_campaign_table_is_the_declarations(self) -> None:
        """A second complement table drifts from the first, and one did."""
        assert _PLATFORM_DEFAULT_AGENTS == {
            hull: declared_total(hull) for hull in declaring_platforms()
        }

    def test_no_module_declares_its_own_cruise_complement(self) -> None:
        """The literal complements must appear in no source but the layouts."""
        totals = {str(declared_total(hull)) for hull in declaring_platforms()}
        repo = PLATFORMS.parents[1]
        offenders = []
        for source in repo.glob("telemetry_buffer/observation_model/*.py"):
            text = source.read_text(encoding="utf-8")
            for line in text.splitlines():
                stated = line.split("#", 1)[0]
                if "num_agents" in stated and any(t in stated for t in totals):
                    offenders.append(f"{source.name}: {line.strip()}")
        assert offenders == []


class TestRefusal:
    def test_a_complement_that_is_not_the_hulls_is_refused(self) -> None:
        hull = "mega_cruise_5000"
        with pytest.raises(ValueError, match="berths"):
            require_declared_total(hull, 450)

    def test_the_hulls_own_complement_passes_through(self) -> None:
        for hull in declaring_platforms():
            total = declared_total(hull)
            assert require_declared_total(hull, total) == total

    def test_a_design_takes_its_complement_from_its_hull(self) -> None:
        for hull in declaring_platforms():
            design = Design(platform=hull)
            assert design.complement == declared_total(hull)
            assert design.run_kwargs()["num_agents"] == declared_total(hull)

    def test_a_design_refuses_a_complement_from_another_class(self) -> None:
        design = Design(platform="mega_cruise_5000", num_agents=450)
        with pytest.raises(ValueError, match="classless"):
            _ = design.complement

    def test_the_default_hull_is_the_observed_records_modal_class(self) -> None:
        """66% of postings carry 600-2,200 passengers; 3.6% carry >3,600."""
        passengers, _ = declared_complement(Design.platform)
        assert 600 <= passengers <= 2200
