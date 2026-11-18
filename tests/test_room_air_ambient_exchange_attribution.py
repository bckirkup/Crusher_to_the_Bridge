"""Tests for tools/room_air_ambient_exchange_attribution.py."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tools import room_air_ambient_exchange_attribution as attr_mod


def test_residence_factor_boundaries() -> None:
    assert attr_mod._residence_factor(0.0) == pytest.approx(1.0)
    assert attr_mod._residence_factor(-3.0) == pytest.approx(1.0)
    assert attr_mod._residence_factor(6.0) == pytest.approx(
        -math.expm1(-6.0) / 6.0,
    )


def test_hvac_only_map_uses_duty_and_duty0_extract() -> None:
    airflow = {
        "hvac_duty": 0.5,
        "oa_fraction": 0.3,
        "hvac_zones": [
            {"ach": 4.0, "rooms": ["A"]},
            {"ach": 8.0, "hvac_duty": 0.0, "oa_fraction": 1.0, "rooms": ["B"]},
        ],
    }
    assert attr_mod._hvac_only_zone_air_exchange_map(airflow) == {
        "A": 2.0,
        "B": 8.0,
    }


def test_map_builder_modes_split_ambient_exchange() -> None:
    airflow = {
        "hvac_zones": [{"ach": 2.0, "rooms": ["Cabin"]}],
        "ambient_openings": [
            {
                "zone": "Pool",
                "type": "open_deck",
                "area_m2": 10.0,
                "exchange_m3h": 100.0,
                "azimuth_deg": 180.0,
                "wind_speed_m_s": 5.0,
            },
        ],
    }
    volumes = {"Cabin": 50.0, "Pool": 100.0}
    off = attr_mod._map_builder("ambient_off")(
        airflow,
        zone_volumes=volumes,
        ambient_exchange_m3h={},
    )
    on = attr_mod._map_builder("ambient_on")(
        airflow,
        zone_volumes=volumes,
        ambient_exchange_m3h={},
    )
    assert off == {"Cabin": 2.0}
    assert on == {"Cabin": 2.0, "Pool": pytest.approx(1.0)}


def test_map_census_finds_expedition_open_deck_row() -> None:
    census = attr_mod.map_census(["expedition_cruise_450"])
    assert census["changed_zone_rows"] >= 1
    assert census["platforms_with_ambient_openings"] == 1
    assert census["factor_ratio_min"] <= census["factor_ratio_median"]
    assert census["factor_ratio_median"] <= census["factor_ratio_max"]
    assert census["rows"][0]["platform"] == "expedition_cruise_450"


def test_norovirus_route_gate_reports_emesis_conditioned() -> None:
    gate = attr_mod.norovirus_route_gate()
    assert gate["pathogen_id"] == "norwalk_gi"
    assert gate["airborne_emission_mode"] == "emesis_conditioned"
    assert gate["has_airborne_emission_fraction"] is False


def test_safe_output_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository root"):
        attr_mod._safe_output_path(tmp_path / "evil.json")
    with pytest.raises(ValueError, match="repository root"):
        attr_mod._safe_output_path(Path("../evil.json"))
    accepted = attr_mod._safe_output_path(Path("docs/audits/x.json"))
    assert accepted.is_relative_to(attr_mod.REPO_ROOT)


def test_simulate_hull_with_map_mode_patches_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    import picard_framework.covid_theta_fit as ctf
    import picard_framework.simulation.ship_simulation as ship_simulation

    seen: dict[str, object] = {}

    def fake_simulate_hull(scenario_id, theta, seed, num_epochs=None):
        seen["map"] = ship_simulation.build_zone_air_exchange_map(
            {
                "hvac_zones": [],
                "ambient_openings": [
                    {
                        "zone": "Pool",
                        "type": "open_deck",
                        "area_m2": 10.0,
                        "exchange_m3h": 100.0,
                        "azimuth_deg": 180.0,
                        "wind_speed_m_s": 5.0,
                    },
                ],
            },
            zone_volumes={"Pool": 100.0},
            ambient_exchange_m3h={},
        )
        return "sentinel"

    monkeypatch.setattr(ctf, "simulate_hull", fake_simulate_hull)
    result = attr_mod._simulate_hull_with_map_mode(
        "scenario", 1.0, 7, "ambient_on", num_epochs=3,
    )
    assert result == "sentinel"
    assert seen["map"] == {"Pool": pytest.approx(1.0)}


def test_paired_hull_runs_reports_seed_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, str, int | None]] = []

    class _Obs:
        def __init__(self, onsets: int, seed: int) -> None:
            self.onsets = onsets
            self.seed = seed

        def as_dict(self) -> dict[str, int]:
            return {
                "seed": self.seed,
                "recorded_onsets": self.onsets,
                "onsets_before_split_day": self.onsets,
                "onsets_on_or_after_split_day": 0,
                "campaign_specimens": 0,
                "campaign_positives": self.onsets,
                "campaign_asymptomatic_positives": 0,
            }

    def fake_simulate(scenario_id, theta, seed, mode, num_epochs=None):
        calls.append((scenario_id, seed, mode, num_epochs))
        return _Obs(10 if mode == "ambient_off" else 12, seed)

    monkeypatch.setattr(attr_mod, "_simulate_hull_with_map_mode", fake_simulate)
    result = attr_mod.paired_hull_runs("scenario", 1.0, [7], num_epochs=3)
    assert calls == [
        ("scenario", 7, "ambient_off", 3),
        ("scenario", 7, "ambient_on", 3),
    ]
    assert result["by_seed"]["7"]["paired_delta_on_minus_off"]["recorded_onsets"] == 2
    assert result["rows"][0]["arm"] == "ambient_off"
    assert result["rows"][1]["arm"] == "ambient_on"


def test_main_writes_payload_under_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(attr_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        attr_mod,
        "map_census",
        lambda platform_ids=None: {
            "platforms_with_ambient_openings": 1,
            "changed_zone_rows": 2,
            "factor_ratio_min": 10.0,
            "factor_ratio_median": 20.0,
            "factor_ratio_max": 30.0,
            "rows": [],
        },
    )
    monkeypatch.setattr(attr_mod, "norovirus_route_gate", lambda: {"pathogen_id": "norwalk_gi"})
    out = tmp_path / "evidence.json"
    assert attr_mod.main(["--skip-hull", "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["criterion"]["arms"] == ["ambient_off", "ambient_on"]
    assert payload["map_census"]["changed_zone_rows"] == 2
    assert payload["norovirus_route_gate"]["pathogen_id"] == "norwalk_gi"
