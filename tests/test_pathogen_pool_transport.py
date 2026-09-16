"""Per-pathogen airborne pool transport configuration and wiring tests."""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from engines.py_contam_bridge import _parse_pathogen_pool_transport
from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.covid_first_look import enumerate_cells, load_design, run_cell
from picard_framework.covid_theta_fit import HullObservables, build_fit_run_spec

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATHOGEN = "sars_cov2_resp"


def _stub_runner(
    scenario_id: str,
    theta: float,
    seed: int,
    *,
    cabin_air_mode: str | None = None,
    pathogen_pool_transport: str | None = None,
) -> HullObservables:
    del cabin_air_mode, pathogen_pool_transport
    return HullObservables(
        scenario_id=scenario_id,
        theta=theta,
        seed=seed,
        recorded_onsets=0,
        onsets_before_split_day=0,
        onsets_on_or_after_split_day=0,
        passenger_onsets_before=0,
        passenger_onsets_after=0,
        crew_onsets_before=0,
        crew_onsets_after=0,
        campaign_specimens=0,
        campaign_positives=0,
        campaign_asymptomatic_positives=0,
    )


def test_pathogen_pool_transport_mode_parsing() -> None:
    assert _parse_pathogen_pool_transport({}) == "airflow"
    assert _parse_pathogen_pool_transport(
        {"pathogen_pool_transport": "airflow"},
    ) == "airflow"
    with pytest.raises(ValueError, match="pathogen_pool_transport"):
        _parse_pathogen_pool_transport({"pathogen_pool_transport": "foo"})


def _initialized_sim(mode: str) -> ShipSimulation:
    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=1)
    spec.legacy_cfg.setdefault("hvac", {})["pathogen_pool_transport"] = mode
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    sim.initialize()
    return sim


def _seed_one_outgoing_zone(sim: ShipSimulation) -> tuple[str, str]:
    assert sim.contam_engine is not None
    path = next(
        path for path in sim.contam_engine.airflow_paths
        if path.from_zone != path.to_zone
        and path.from_zone in sim.contam_engine.zone_nodes
        and path.to_zone in sim.contam_engine.zone_nodes
        and not path.from_zone.startswith("_plenum_")
        and not path.to_zone.startswith("_plenum_")
        and path.flow_rate_m3h > 0.0
    )
    masses = {
        zone: (1.0 if zone == path.from_zone else 0.0)
        for zone in sim.engine.get_pathogen_zone_mass(PATHOGEN)
    }
    sim.engine.set_pathogen_zone_mass(PATHOGEN, masses)
    return path.from_zone, path.to_zone


@pytest.mark.parametrize("mode", ["none", "airflow"])
def test_ship_simulation_moves_per_pathogen_pool_only_in_airflow_mode(mode: str) -> None:
    sim = _initialized_sim(mode)
    _, downstream = _seed_one_outgoing_zone(sim)
    sim._transport_airborne_pools()  # noqa: SLF001
    pool = sim.engine.get_pathogen_zone_mass(PATHOGEN)
    if mode == "airflow":
        assert pool[downstream] > 0.0
    else:
        assert pool[downstream] == pytest.approx(0.0)
    if mode == "airflow":
        aggregate = sim.engine.zone_pathogen_mass
        expected = {
            zone: sum(
                masses.get(zone, 0.0)
                for masses in sim.engine.multi_pathogen_mass.values()
            )
            for zone in aggregate
        }
        for zone, mass in expected.items():
            assert aggregate[zone] == pytest.approx(mass)


def test_fit_run_spec_declares_pool_transport_without_default_hvac_override() -> None:
    base = build_fit_run_spec("diamond_princess_2020", 1e8, 7, num_epochs=1)
    assert "hvac" not in base["config_overrides"]
    airflow = build_fit_run_spec(
        "diamond_princess_2020", 1e8, 7, num_epochs=1,
        pathogen_pool_transport="airflow",
    )
    assert airflow["config_overrides"]["hvac"] == {
        "pathogen_pool_transport": "airflow",
    }


def test_design_round_trip_keeps_pool_transport_field() -> None:
    design = load_design()
    assert design.pathogen_pool_transport == "airflow"
    assert load_design().as_dict()["pathogen_pool_transport"] == "airflow"
    cells = enumerate_cells(design)
    payload = run_cell(design, cells[0], runner=_stub_runner)
    assert payload["pathogen_pool_transport"] == "airflow"


def test_design_rejects_unknown_pool_transport_mode() -> None:
    with pytest.raises(ValueError, match="pathogen_pool_transport"):
        replace(load_design(), pathogen_pool_transport="foo")
