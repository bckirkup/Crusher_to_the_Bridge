"""Route-attribution telemetry is exhaustive and numerically inert."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from orchestrator_init import update_route_attribution
from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.simulation import ship_simulation as ship_simulation_module

REPO_ROOT = "/home/ubuntu/repos/Crusher-to-the-Bridge"


def _event(ledger: dict[str, float], pathway: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        acquired_particles_by_route=ledger,
        pathway=pathway,
    )


class TestRouteAttribution:
    def test_attribution_is_exhaustive_and_normalised(self) -> None:
        events = [
            _event({"fomite": 1.0, "direct_contact": 3.0}, "fomite"),
            _event({"hvac_airborne": 2.0, "food_contamination": 1.0}),
            _event({}, "emesis_aerosol"),
            _event({}, None),
        ]
        dominant: dict[str, int] = {}
        shares: dict[str, float] = {}
        update_route_attribution(events, dominant, shares)

        assert sum(dominant.values()) == len(events)
        assert sum(shares.values()) == pytest.approx(len(events))

    def test_ledger_share_grades_and_dominant_flips_once(self) -> None:
        fractions = (0.1, 0.5, 0.9)
        dominant: list[str] = []
        fomite_shares: list[float] = []
        for fraction in fractions:
            counts: dict[str, int] = {}
            shares: dict[str, float] = {}
            update_route_attribution(
                [_event({"fomite": fraction, "direct_contact": 1.0 - fraction})],
                counts,
                shares,
            )
            dominant.append(next(iter(counts)))
            fomite_shares.append(shares["fomite"])

        assert fomite_shares == sorted(fomite_shares)
        assert dominant == ["direct_contact", "fomite", "fomite"]

    def test_empty_ledger_falls_back_to_pathway_then_unknown(self) -> None:
        dominant: dict[str, int] = {}
        shares: dict[str, float] = {}
        update_route_attribution(
            [_event({}, "food_contamination"), _event({}, None)],
            dominant,
            shares,
        )
        assert dominant == {"food_contamination": 1, "unknown": 1}
        assert shares == {"food_contamination": 1.0, "unknown": 1.0}

    def test_short_run_summary_contains_attribution_without_moving_metrics(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spec_path = (
            f"{REPO_ROOT}/picard_framework/runs/"
            "smoke_pathogen_overrides_2epoch.json"
        )
        spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
        spec.num_epochs = 48
        first = ShipSimulation(spec, display=False, repo_root=REPO_ROOT).run(48)
        monkeypatch.setattr(
            ship_simulation_module,
            "update_route_attribution",
            lambda events, dominant, shares: None,
        )
        second = ShipSimulation(spec, display=False, repo_root=REPO_ROOT).run(48)
        first_summary = first.history[-1]["summary"]
        second_summary = second.history[-1]["summary"]

        assert "infections_by_dominant_route" in first_summary
        assert "infection_dose_share_by_route" in first_summary
        assert first_summary["infections_by_dominant_route"], (
            "fixture should establish at least one transmission event"
        )

        fiat_imports = 2 + 1  # two norwalk seeds plus the legacy seed
        assert sum(first_summary["infections_by_dominant_route"].values()) == (
            first_summary["cumulative_ever_infected"] - fiat_imports
        ), "route events exclude all three fiat index-case imports"
        assert second_summary["infections_by_dominant_route"] == {}
        assert second_summary["infection_dose_share_by_route"] == {}
        for key in (
            "cumulative_ever_infected",
            "infection_attack_rate_passenger",
            "infection_attack_rate_crew",
            "cumulative_reported_cases",
        ):
            assert first_summary[key] == second_summary[key]
