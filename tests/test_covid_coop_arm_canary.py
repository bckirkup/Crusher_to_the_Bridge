"""COVID-COOP-02 — canary driver override tests."""

from __future__ import annotations

import copy

import pytest

from tools.covid_coop_arm_canary import coop_override

PID = "sars_cov2_resp"


def _raw() -> dict:
    return {
        "pathogen_overrides": {
            PID: {
                "dose_response": {
                    "model": "beta_poisson",
                    "alpha": 0.18,
                    "beta": 58.0,
                    "susceptibility_scale": 7.6e13,
                },
            },
        },
        "other_keys": {"nested": True},
    }


class TestCoopOverride:
    def test_sets_only_the_arm_fields(self) -> None:
        patched = coop_override(_raw(), n_star=3, mu_dry=0.05, mu_wet=20.0)
        dose_response = patched["pathogen_overrides"][PID]["dose_response"]
        assert dose_response["model"] == "cooperative_packet"
        assert dose_response["n_star"] == 3
        assert dose_response["carrier_loading"] == {"dry": pytest.approx(0.05), "wet": pytest.approx(20.0)}
        # Theta composite and frailty ride over unchanged.
        assert dose_response["alpha"] == pytest.approx(0.18)
        assert dose_response["beta"] == pytest.approx(58.0)
        assert dose_response["susceptibility_scale"] == pytest.approx(7.6e13)

    def test_does_not_mutate_the_input_spec(self) -> None:
        raw = _raw()
        snapshot = copy.deepcopy(raw)
        coop_override(raw, n_star=2, mu_dry=0.01, mu_wet=5.0)
        assert raw == snapshot

    def test_creates_missing_override_path(self) -> None:
        patched = coop_override({}, n_star=5, mu_dry=0.1, mu_wet=500.0)
        dose_response = patched["pathogen_overrides"][PID]["dose_response"]
        assert dose_response["model"] == "cooperative_packet"
        assert dose_response["n_star"] == 5
