"""Golden-value + sensitivity tests for pre-boarding boundary decision model."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import numpy as np
import pytest

from picard_framework.analysis.boundary.campaign import (
    expand_scenarios,
    load_platform_defaults,
    load_scenario_matrix,
    run_campaign,
)
from picard_framework.analysis.boundary.costs import (
    CostParams,
    break_even_prevalence,
    compute_voyage_costs,
)
from picard_framework.analysis.boundary.decision_model import run_monte_carlo
from picard_framework.analysis.boundary.posterior_lookup import (
    load_fixture_surface,
    load_outbreak_surface,
    load_stan_surface,
)
from picard_framework.analysis.boundary.prevalence import draw_introductions
from picard_framework.analysis.boundary.run_decision_model import main as cli_main
from picard_framework.analysis.boundary.screening import (
    apply_policy,
    run_screening,
)


def _base_scenario(**overrides):
    sc = {
        "scenario_id": "test_mega_P2",
        "policy": "P2",
        "N_pax": 500,
        "N_crew": 100,
        "platform_class": "mega",
        "pathogen": "norovirus",
        "baseline_response": "vsp",
        "pi_inf": 0.002,
        "prevalence_mode": "bernoulli",
        "rho_cluster": 1.0,
        "adoption_pax": 0.43,
        "adoption_crew": 1.0,
        "Se_w": 0.65,
        "Sp_w": 0.85,
        "Se_confirm": 0.9,
        "Sp_confirm": 0.98,
        "costs": CostParams().to_dict(),
    }
    sc.update(overrides)
    return sc


def test_prevalence_bernoulli_mean_near_pi():
    rng = np.random.default_rng(0)
    draws = [
        draw_introductions(
            n_pax=2000, n_crew=0, pi_inf=0.01, rng=rng, mode="bernoulli"
        ).k_intro
        for _ in range(200)
    ]
    assert abs(np.mean(draws) - 20.0) < 3.0


def test_prevalence_beta_binomial_overdispersed():
    rng = np.random.default_rng(1)
    bb = [
        draw_introductions(
            n_pax=500,
            n_crew=0,
            pi_inf=0.01,
            rng=rng,
            mode="beta_binomial",
            rho_cluster=5.0,
        ).k_intro
        for _ in range(300)
    ]
    bern = [
        draw_introductions(
            n_pax=500, n_crew=0, pi_inf=0.01, rng=rng, mode="bernoulli"
        ).k_intro
        for _ in range(300)
    ]
    assert np.var(bb) > np.var(bern)


def test_policy_p3_denies_on_flag_without_confirm():
    z = np.array([1, 0, 0], dtype=np.int8)
    flagged = np.array([1, 1, 0], dtype=np.int8)
    confirmed = np.array([0, 0, 0], dtype=np.int8)
    denied = apply_policy(
        policy="P3", z=z, flagged=flagged, confirmed_pos=confirmed
    )
    assert denied.tolist() == [1, 1, 0]


def test_policy_p2_requires_confirmation():
    z = np.array([1, 0], dtype=np.int8)
    flagged = np.array([1, 1], dtype=np.int8)
    confirmed = np.array([1, 0], dtype=np.int8)
    denied = apply_policy(
        policy="P2", z=z, flagged=flagged, confirmed_pos=confirmed
    )
    assert denied.tolist() == [1, 0]


def test_p0_no_denials_and_k_board_equals_intro():
    rng = np.random.default_rng(2)
    z = np.array([1, 1, 0, 0, 0], dtype=np.int8)
    is_crew = np.zeros(5, dtype=bool)
    result = run_screening(
        z=z,
        is_crew=is_crew,
        policy="P0",
        adoption_pax=0.43,
        adoption_crew=1.0,
        se_w=0.9,
        sp_w=0.9,
        se_confirm=0.9,
        sp_confirm=0.9,
        rng=rng,
    )
    assert result.k_board == 2
    assert result.intercepted == 0
    assert int(result.denied.sum()) == 0


def test_cost_formula_vsp_bundle():
    params = CostParams(
        C_outbreak=100.0, C_vsp=200.0, C_reputation=300.0, C_case=10.0
    )
    costs = compute_voyage_costs(
        params=params,
        n_total=100,
        n_adopted=10,
        n_secondary=2,
        n_fp=1,
        n_tp=1,
        k_missed=0,
        p_trigger=0.5,
        e_ar=0.1,
        n_pax_boarded=100,
    )
    expected_onboard = 0.5 * (100 + 200 + 300) + 0.1 * 100 * 10
    assert costs.onboard == pytest.approx(expected_onboard)
    assert costs.total == pytest.approx(
        10 * params.C_screen
        + 2 * params.C_secondary
        + 1 * params.C_false_positive
        + 1 * params.C_true_positive
        + expected_onboard
    )


def test_lookup_interpolation_and_clamp():
    surface = load_fixture_surface()
    mid = surface.lookup(
        platform_class="mega",
        pathogen="norovirus",
        baseline_response="vsp",
        k=1.5,
    )
    lo = surface.lookup(
        platform_class="mega",
        pathogen="norovirus",
        baseline_response="vsp",
        k=1,
    )
    hi = surface.lookup(
        platform_class="mega",
        pathogen="norovirus",
        baseline_response="vsp",
        k=2,
    )
    assert lo.p_trigger < mid.p_trigger < hi.p_trigger
    clamped = surface.lookup(
        platform_class="mega",
        pathogen="norovirus",
        baseline_response="vsp",
        k=10_000,
    )
    top = surface.lookup(
        platform_class="mega",
        pathogen="norovirus",
        baseline_response="vsp",
        k=40,
    )
    assert clamped.p_trigger == pytest.approx(top.p_trigger)


def test_stan_surface_csv_loader(tmp_path):
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        stan = Path("stan_fit/posterior")
        stan.mkdir(parents=True)
        csv_path = stan / "outbreak_surface.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(
                fh,
                fieldnames=[
                    "platform_class",
                    "pathogen",
                    "baseline_response",
                    "k",
                    "P_trigger",
                    "E_AR",
                    "P_accel",
                    "E_cost_onboard",
                ],
            )
            w.writeheader()
            w.writerow(
                {
                    "platform_class": "mega",
                    "pathogen": "norovirus",
                    "baseline_response": "vsp",
                    "k": 0,
                    "P_trigger": 0.0,
                    "E_AR": 0.0,
                    "P_accel": 0.0,
                    "E_cost_onboard": 0.0,
                }
            )
            w.writerow(
                {
                    "platform_class": "mega",
                    "pathogen": "norovirus",
                    "baseline_response": "vsp",
                    "k": 2,
                    "P_trigger": 0.5,
                    "E_AR": 0.1,
                    "P_accel": 0.2,
                    "E_cost_onboard": 1000.0,
                }
            )
        surface = load_stan_surface("stan_fit")
        pt = surface.lookup(
            platform_class="mega",
            pathogen="norovirus",
            baseline_response="vsp",
            k=1,
        )
        assert pt.p_trigger == pytest.approx(0.25)
        auto = load_outbreak_surface(lookup="auto", stan_fit_dir="stan_fit")
        assert auto.source.startswith("stan:")
    finally:
        os.chdir(prev)


def test_golden_p0_vs_p2_seeded():
    surface = load_fixture_surface()
    p0 = run_monte_carlo(
        _base_scenario(policy="P0", scenario_id="golden_p0"),
        surface,
        n_mc=200,
        seed=1701,
    )
    p2 = run_monte_carlo(
        _base_scenario(policy="P2", scenario_id="golden_p2"),
        surface,
        n_mc=200,
        seed=1701,
        baseline_summary=p0,
    )
    # Seed-pinned golden anchors (update deliberately if model changes).
    assert p0["expected_K_board"] == pytest.approx(1.075, abs=1e-9)
    assert p0["expected_P_trigger"] == pytest.approx(0.278175, abs=1e-9)
    assert p2["expected_K_board"] == pytest.approx(0.88, abs=1e-9)
    assert p2["expected_intercepted"] == pytest.approx(0.385, abs=1e-9)
    assert p2["expected_K_board"] < p0["expected_K_board"]


def test_sensitivity_se_w_reduces_k_board_for_p3_not_p0():
    surface = load_fixture_surface()
    p0_lo = run_monte_carlo(
        _base_scenario(policy="P0", Se_w=0.4, scenario_id="p0_lo"),
        surface,
        n_mc=150,
        seed=42,
    )
    p0_hi = run_monte_carlo(
        _base_scenario(policy="P0", Se_w=0.9, scenario_id="p0_hi"),
        surface,
        n_mc=150,
        seed=42,
    )
    assert p0_lo["expected_K_board"] == pytest.approx(p0_hi["expected_K_board"])

    p3_lo = run_monte_carlo(
        _base_scenario(policy="P3", Se_w=0.4, Sp_w=0.95, scenario_id="p3_lo"),
        surface,
        n_mc=150,
        seed=42,
    )
    p3_hi = run_monte_carlo(
        _base_scenario(policy="P3", Se_w=0.9, Sp_w=0.95, scenario_id="p3_hi"),
        surface,
        n_mc=150,
        seed=42,
    )
    assert p3_hi["expected_K_board"] < p3_lo["expected_K_board"]
    assert p3_hi["expected_intercepted"] > p3_lo["expected_intercepted"]


def test_sensitivity_adoption_increases_intercepts_p2():
    surface = load_fixture_surface()
    low = run_monte_carlo(
        _base_scenario(policy="P2", adoption_pax=0.2, scenario_id="a_lo"),
        surface,
        n_mc=150,
        seed=7,
    )
    high = run_monte_carlo(
        _base_scenario(policy="P2", adoption_pax=0.9, scenario_id="a_hi"),
        surface,
        n_mc=150,
        seed=7,
    )
    assert high["expected_intercepted"] >= low["expected_intercepted"]


def test_expand_smoke_matrix_policies():
    matrix = load_scenario_matrix(None, smoke=True)
    scenarios = expand_scenarios(matrix, load_platform_defaults())
    assert len(scenarios) == 4  # 1 platform × 2 pi × 2 policies × 1 cost
    assert {s["policy"] for s in scenarios} == {"P0", "P2"}


def test_campaign_smoke_and_resume(tmp_path):
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        surface = load_fixture_surface()
        scenarios = expand_scenarios(
            load_scenario_matrix(None, smoke=True), load_platform_defaults()
        )
        rows = run_campaign(
            scenarios, surface, out_dir="boundary_out", n_mc=20, seed=1701
        )
        assert len(rows) == 4
        assert Path("boundary_out/policy_comparison.csv").is_file()
        completed = Path("boundary_out/completed_runs.txt").read_text(
            encoding="utf-8"
        ).strip().splitlines()
        assert len(completed) == 4

        # Resume should not duplicate work; still 4 rows
        rows2 = run_campaign(
            scenarios,
            surface,
            out_dir="boundary_out",
            n_mc=20,
            seed=1701,
            resume=True,
        )
        assert len(rows2) == 4
    finally:
        os.chdir(prev)


def test_cli_smoke(tmp_path):
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = cli_main(
            ["--smoke", "--out", "boundary_analysis", "--no-figures"]
        )
        # heatmap still runs on smoke; figures disabled
        assert rc == 0
        assert Path("boundary_analysis/policy_comparison.csv").is_file()
        assert Path("boundary_analysis/report.md").is_file()
        meta = json.loads(
            Path("boundary_analysis/campaign_meta.json").read_text(encoding="utf-8")
        )
        assert meta["n_completed"] == 4
        assert meta["surface_source"].startswith("fixture:")
    finally:
        os.chdir(prev)


def test_cli_smoke_with_figures(tmp_path):
    pytest.importorskip("matplotlib")
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = cli_main(["--smoke", "--out", "figs_out"])
        assert rc == 0
        fig_dir = Path("figs_out/figures")
        assert fig_dir.is_dir()
        pngs = list(fig_dir.glob("*.png"))
        assert len(pngs) >= 4
        names = {p.name for p in pngs}
        assert "01_cost_vs_prevalence.png" in names
        assert "02_vsp_vs_prevalence.png" in names
        assert "06_se_sp_heatmap.png" in names
        assert "08_policy_frontier.png" in names
    finally:
        os.chdir(prev)


def test_break_even_helper():
    be = break_even_prevalence(
        pi_grid=[0.001, 0.002, 0.005],
        cost_baseline_by_pi=[100.0, 200.0, 400.0],
        cost_policy_by_pi=[150.0, 180.0, 300.0],
    )
    # Crosses between 0.001 (Δ=+50) and 0.002 (Δ=-20) → interpolate.
    assert be == pytest.approx(0.001 + 50 / 70 * 0.001)

    already = break_even_prevalence(
        pi_grid=[0.001, 0.002],
        cost_baseline_by_pi=[100.0, 200.0],
        cost_policy_by_pi=[90.0, 150.0],
    )
    assert already == pytest.approx(0.001)

    never = break_even_prevalence(
        pi_grid=[0.001, 0.002],
        cost_baseline_by_pi=[100.0, 200.0],
        cost_policy_by_pi=[150.0, 250.0],
    )
    assert never is None


def test_default_scenario_matrix_log_prevalence_grid():
    matrix = load_scenario_matrix(None, smoke=False)
    pis = [float(x) for x in matrix["axes"]["pi_inf"]]
    assert len(pis) >= 20
    assert pis[0] == pytest.approx(1e-4)
    assert pis[-1] == pytest.approx(0.02)
    # Approximately log-spaced: successive ratios near-constant.
    ratios = [pis[i + 1] / pis[i] for i in range(len(pis) - 1)]
    assert max(ratios) / min(ratios) < 1.05


def test_p1_matches_p0_economics():
    surface = load_fixture_surface()
    p0 = run_monte_carlo(
        _base_scenario(policy="P0", scenario_id="econ_p0"),
        surface,
        n_mc=100,
        seed=99,
    )
    p1 = run_monte_carlo(
        _base_scenario(policy="P1", scenario_id="econ_p1"),
        surface,
        n_mc=100,
        seed=99,
    )
    assert p1["expected_K_board"] == pytest.approx(p0["expected_K_board"])
    assert p1["expected_total_cost"] == pytest.approx(p0["expected_total_cost"])


def test_resolve_initial_infected_sources():
    from picard_framework.analysis.parse_run_id import resolve_initial_infected

    assert (
        resolve_initial_infected(parameters={"initial_infected": 5}, run_id="x") == 5
    )
    assert (
        resolve_initial_infected(
            run_spec={"pathogen_overrides": {"norwalk_gi": {"initial_infected": 3}}},
            run_id="x",
        )
        == 3
    )
    assert resolve_initial_infected(run_id="tier_init10_s1") == 10
    assert (
        resolve_initial_infected(
            run_id="no_init",
            timeseries=[{"infected": 2, "new_infections": 2}],
        )
        == 2
    )


def test_aggregate_outbreak_surface_and_export(tmp_path):
    from picard_framework.analysis.boundary.export_outbreak_surface import (
        aggregate_outbreak_surface,
        export_outbreak_surface,
        normalize_pathogen,
    )
    from picard_framework.analysis.boundary.posterior_lookup import load_stan_surface

    assert normalize_pathogen("sarscov2") == "SARS-CoV-2"
    rows = [
        {
            "platform_class": "mega",
            "pathogen": "norovirus",
            "baseline_response": "vsp",
            "k": 2,
            "triggered": True,
            "attack_rate": 0.1,
            "took_off": True,
            "peak_epoch": 20.0,
            "cumulative_cost_usd": 1000.0,
            "num_agents": 5000,
        },
        {
            "platform_class": "mega",
            "pathogen": "norovirus",
            "baseline_response": "vsp",
            "k": 2,
            "triggered": False,
            "attack_rate": 0.0,
            "took_off": False,
            "peak_epoch": 10.0,
            "cumulative_cost_usd": 0.0,
            "num_agents": 5000,
        },
        {
            "platform_class": "mega",
            "pathogen": "norovirus",
            "baseline_response": "vsp",
            "k": 5,
            "triggered": True,
            "attack_rate": 0.2,
            "took_off": True,
            "peak_epoch": 15.0,
            "cumulative_cost_usd": 2000.0,
            "num_agents": 5000,
        },
    ]
    surface_rows = aggregate_outbreak_surface(rows)
    by_k = {int(r["k"]): r for r in surface_rows}
    assert 0 in by_k
    assert by_k[2]["P_trigger"] == pytest.approx(0.5)
    assert by_k[2]["E_AR"] == pytest.approx(0.05)
    assert by_k[2]["P_accel"] == pytest.approx(0.5)
    assert by_k[5]["P_trigger"] == pytest.approx(1.0)

    # End-to-end zip export under CWD confinement
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        results = Path("results_tiny")
        results.mkdir()
        # minimal zip via helper patterns from campaign bundle tests
        import zipfile

        ts = [
            {
                "epoch": 0,
                "susceptible": 98,
                "infected": 2,
                "symptomatic": 1,
                "recovered": 0,
                "immune": 0,
                "quarantined": 0,
                "isolated": 0,
                "new_infections": 2,
                "total_pathogen_mass": 0,
                "n_zones_contaminated": 0,
                "max_concentration": 0,
                "max_conc_zone": "",
                "cumulative_cost_usd": 0,
                "cumulative_ois": 0,
                "trigger_status": "none",
            },
            {
                "epoch": 1,
                "susceptible": 90,
                "infected": 8,
                "symptomatic": 5,
                "recovered": 2,
                "immune": 0,
                "quarantined": 1,
                "isolated": 0,
                "new_infections": 8,
                "total_pathogen_mass": 1,
                "n_zones_contaminated": 1,
                "max_concentration": 1,
                "max_conc_zone": "A",
                "cumulative_cost_usd": 100,
                "cumulative_ois": 0.1,
                "trigger_status": "SUSPECTED",
            },
        ]
        summary = {
            "run_id": "t_mega_norovirus_s1",
            "parameters": {
                "platform_id": "mega_cruise_5000",
                "pathogen": "norovirus",
                "num_agents": 100,
                "seed": 1,
                "lockdown_attack_rate": 0.05,
                "suspect_attack_rate": 0.02,
            },
            "num_epochs": 2,
            "trigger_status": "SUSPECTED",
            "summary": {"infected": 8, "recovered": 2, "susceptible": 90},
            "cost_accounting": {"total_financial_usd": 100},
            "derived": {},
        }
        run_spec = {
            "catalog": {"platform_id": "mega_cruise_5000"},
            "run": {"random_seed": 1, "num_epochs": 2},
            "config_overrides": {"ship_graph": {"num_agents": 100}},
        }
        with zipfile.ZipFile(results / "run1.zip", "w") as zf:
            zf.writestr("summary.json", json.dumps(summary))
            zf.writestr("timeseries.json", json.dumps(ts))
            zf.writestr("run_spec.json", json.dumps(run_spec))

        out = Path("stan_fit") / "outbreak_surface.csv"
        out.parent.mkdir()
        manifest = export_outbreak_surface(
            ["results_tiny"],
            str(out),
            pathogens=["norovirus"],
        )
        assert manifest["n_runs_used"] == 1
        assert out.is_file()
        assert out.with_suffix(".json").is_file()
        surface = load_stan_surface("stan_fit")
        pt = surface.lookup(
            platform_class="mega",
            pathogen="norovirus",
            baseline_response="vsp",
            k=2,
        )
        assert pt.p_trigger == pytest.approx(1.0)
    finally:
        os.chdir(prev)
