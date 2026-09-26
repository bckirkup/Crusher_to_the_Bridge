"""
test_ab_diff.py – A/B run diff pure helpers (Issue #99)
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _history(infected: list[int], symptomatic: list[int] | None = None,
             trigger: str = "BASELINE", cost: dict | None = None) -> list[dict]:
    symptomatic = symptomatic or [0] * len(infected)
    hist = []
    for i, (inf, sym) in enumerate(zip(infected, symptomatic)):
        rec = {
            "epoch": i,
            "trigger_status": trigger,
            "summary": {
                "susceptible": 100 - inf - sym,
                "infected": inf,
                "symptomatic": sym,
                "isolated": 0,
                "recovered": 0,
                "sick_call_count": i,
                "quarantine_refusers": 0,
            },
            "spaces": {},
            "agents": [],
        }
        if cost and i == len(infected) - 1:
            rec["cost_accounting"] = cost
        hist.append(rec)
    return hist


class TestSummarizeHistory:
    def test_empty_history(self) -> None:
        from dashboard.ab_diff import summarize_history
        assert summarize_history([]) == {}

    def test_run_summary_fields(self) -> None:
        from dashboard.ab_diff import summarize_history
        hist = _history([0, 4, 9, 3], symptomatic=[0, 1, 2, 1],
                        cost={"operational_impact_cumulative": 7.5,
                              "total_financial_usd": 1200.0,
                              "total_labor_hours": 3.0})
        s = summarize_history(hist)
        assert s["epochs"] == 4
        assert s["peak_active_cases"] == 11
        assert s["peak_active_epoch"] == 2
        assert s["peak_infected"] == 9
        assert s["final_infected"] == 3
        assert s["ois_cumulative"] == pytest.approx(7.5)
        assert s["credits_spent_usd"] == pytest.approx(1200.0)
        assert s["labor_hours"] == pytest.approx(3.0)
        assert s["first_non_baseline_epoch"] is None

    def test_first_non_baseline_epoch(self) -> None:
        from dashboard.ab_diff import summarize_history
        hist = _history([0, 1, 2])
        hist[2]["trigger_status"] = "SUSPECTED"
        assert summarize_history(hist)["first_non_baseline_epoch"] == 2


class TestDeltaSummaryFrame:
    def test_delta_is_b_minus_a(self) -> None:
        from dashboard.ab_diff import delta_summary_frame
        a = _history([0, 5, 2])
        b = _history([0, 8, 6])
        df = delta_summary_frame(a, b)
        row = df[df["Metric"] == "peak_infected"].iloc[0]
        assert row["Run A"] == "5"
        assert row["Run B"] == "8"
        assert row["Delta (B-A)"] == 3

    def test_status_column_no_numeric_delta(self) -> None:
        from dashboard.ab_diff import delta_summary_frame
        df = delta_summary_frame(_history([0]), _history([0]))
        row = df[df["Metric"] == "final_trigger_status"].iloc[0]
        assert pd.isna(row["Delta (B-A)"])


class TestPerEpochDeltaFrame:
    def test_shared_prefix_alignment(self) -> None:
        from dashboard.ab_diff import per_epoch_delta_frame
        a = _history([1, 2, 3, 4])
        b = _history([2, 4])
        df = per_epoch_delta_frame(a, b)
        assert df["epoch"].nunique() == 2
        inf = df[(df["metric"] == "infected")].set_index("epoch")
        assert inf.loc[0, "delta"] == 1
        assert inf.loc[1, "delta"] == 2

    def test_all_summary_metrics_present(self) -> None:
        from dashboard.ab_diff import SUMMARY_METRICS, per_epoch_delta_frame
        df = per_epoch_delta_frame(_history([1]), _history([1]))
        assert set(df["metric"].unique()) == set(SUMMARY_METRICS)

    def test_empty_histories(self) -> None:
        from dashboard.ab_diff import per_epoch_delta_frame
        assert per_epoch_delta_frame([], _history([1])).empty


class TestActiveCasesSeries:
    def test_infected_plus_symptomatic(self) -> None:
        from dashboard.ab_diff import active_cases_series
        hist = _history([1, 3], symptomatic=[2, 4])
        assert active_cases_series(hist) == [3, 7]
