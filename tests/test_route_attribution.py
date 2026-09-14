"""Route-attribution telemetry is exhaustive and numerically inert."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator_init import update_route_attribution
from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.simulation import ship_simulation as ship_simulation_module
from telemetry_buffer.observation_model import realism_ladder_readout

REPO_ROOT = str(Path(__file__).resolve().parents[1])


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


def _summary_fixture(
    seed: int,
    counts: dict[str, int],
    shares: dict[str, float],
) -> dict:
    derived = {key: 0.01 for key in realism_ladder_readout.LEVEL_KEYS}
    derived.update({
        "passenger_complement": 1600,
        "crew_complement": 300,
        "reported_case_attack_rate_passenger": 0.001,
        "infection_attack_rate_passenger": 0.01,
        "infection_attack_rate_crew": 0.0,
    })
    return {
        "run_id": f"fixture_{seed}",
        "parameters": {
            "tier_id": "fixture",
            "platform_id": "classic_cruise_1900",
            "surveillance": "syndromic_comp65",
            "dose_adjustment": 4.0,
            "num_epochs": 168,
            "seed": seed,
            "boarding_mechanism_rung": "shipped",
        },
        "derived": derived,
        "summary": {
            "infections_by_dominant_route": counts,
            "infection_dose_share_by_route": shares,
        },
    }


class TestReadoutRouteAttribution:
    def test_rows_and_cell_carry_per_route_means_and_fractions(self) -> None:
        rows = []
        for record in (
            _summary_fixture(
                1,
                {"fomite": 3, "direct_contact": 1},
                {"fomite": 2.4, "direct_contact": 0.4, "droplet": 0.2},
            ),
            _summary_fixture(
                2,
                {"fomite": 5},
                {"fomite": 4.8, "hvac_airborne": 0.2},
            ),
        ):
            row = realism_ladder_readout._row(record, None)
            row["arm"] = "fixture"
            rows.append(row)

        cell = realism_ladder_readout.summarise_cell(rows)
        block = cell["secondary_route_attribution"]
        assert block["fomite"]["mean_dominant_count"] == pytest.approx(4.0)
        assert block["fomite"]["mean_dose_share"] == pytest.approx(3.6)
        assert block["fomite"]["fraction_dominant"] == pytest.approx(8.0 / 9.0)
        assert block["direct_contact"]["fraction_dominant"] == pytest.approx(
            1.0 / 9.0,
        )
        assert block["droplet"]["mean_dose_share"] == pytest.approx(0.1)
        assert block["droplet"]["fraction_dominant"] == pytest.approx(0.0)
        assert block["unknown"]["mean_dominant_count"] == pytest.approx(0.0)

    def test_markdown_omits_all_zero_route_columns(self) -> None:
        rows = []
        for record in (
            _summary_fixture(1, {"fomite": 3, "unknown": 1}, {"fomite": 3.0}),
            _summary_fixture(2, {}, {}),
        ):
            row = realism_ladder_readout._row(record, None)
            row["arm"] = "fixture"
            rows.append(row)
        report = realism_ladder_readout.build_report(rows, era="pre")
        markdown = realism_ladder_readout.render_markdown(report)

        header = next(
            line for line in markdown.splitlines() if line.startswith("| rung")
        )
        assert "fomite dominant %" in header
        assert "unknown dominant %" in header
        assert "droplet dominant %" not in header

        zero_report = realism_ladder_readout.build_report(
            [dict(rows[1])], era="pre",
        )
        zero_markdown = realism_ladder_readout.render_markdown(zero_report)
        assert "dominant %" not in zero_markdown
