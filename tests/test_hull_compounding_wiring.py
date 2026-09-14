"""The hull-compounding campaign axes: phi, occupancy, and the run ids.

``contact_class_exponents`` and tier-declared ``num_agents`` are
absent-by-default axes: a tier that does not declare them yields
byte-identical run ids and identical config overrides to before the axis
existed. Graded behaviour checks that phi and the density exponent move
the engine's contact outcome follow the ``test_contact_class_scaling`` /
``test_density_contact`` idiom. No goldens.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.transmission_core import TransmissionCore
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    generate_tier_runs,
)
from tests.test_contact_class_scaling import (
    _core as _phi_core,
)
from tests.test_contact_class_scaling import (
    _crew_fraction,
    _room,
    _rows,
)
from tests.test_density_contact import _agent as _density_agent


def _manifest(tiers: dict) -> dict:
    return {
        "platform": "classic_cruise_1900",
        "default_epochs": 24,
        "default_num_agents": 1910,
        "pathogen_configs": {
            "norovirus": {
                "bundle": "active_profiles",
                "pathogen_id": "norwalk_gi",
                "overrides": {"remove": ["sars_cov2_resp"]},
            },
        },
        "surveillance_configs": {"syndromic": {}},
        "tiers": tiers,
    }


def _tier(**extra) -> dict:
    tier = {
        "platform": "classic_cruise_1900",
        "pathogen": "norovirus",
        "dose_adjustments": [4.0],
        "surveillance_strategies": ["syndromic"],
        "epoch_durations": [24],
        "boarding_mechanism_rungs": ["reportable"],
        "seeds": [7, 8],
    }
    tier.update(extra)
    return tier


def _runs(tier: dict) -> dict[str, dict]:
    manifest = _manifest({"rl_probe": tier})
    return {
        rid: spec
        for rid, spec in generate_tier_runs(manifest, "rl_probe")
    }


class TestPhiAxis:
    BASE_RID = (
        "rl_norovirus_classic_cruise_1900_dose4_rung-reportable"
        "_ep24_syndromic_s7"
    )

    def test_absent_phi_leaves_run_id_and_config_untouched(self) -> None:
        runs = _runs(_tier())
        assert self.BASE_RID in runs
        spec = runs[self.BASE_RID]
        transmission = (spec.get("config_overrides") or {}).get("transmission")
        assert transmission is None
        assert "contact_class_exponent" not in spec["campaign_parameters"]

    def test_declared_phi_sets_override_factor_and_tag(self) -> None:
        runs = _runs(_tier(contact_class_exponents=[0.0, 0.5, 1.0]))
        assert len(runs) == 6
        rid = (
            "rl_norovirus_classic_cruise_1900_dose4_rung-reportable"
            "_phi050_ep24_syndromic_s7"
        )
        spec = runs[rid]
        assert spec["config_overrides"]["transmission"] == {
            "contact_class_exponent": 0.5,
        }
        assert spec["campaign_parameters"][
            "contact_class_exponent"
        ] == pytest.approx(0.5)
        assert any("phi000" in r for r in runs)
        assert any("phi100" in r for r in runs)

    def test_phi_does_not_force_a_contact_mode(self) -> None:
        runs = _runs(_tier(contact_class_exponents=[0.5]))
        transmission = next(
            iter(runs.values()),
        )["config_overrides"]["transmission"]
        assert "contact_mode" not in transmission

    def test_a_negative_phi_tag_is_distinguishable(self) -> None:
        runs = _runs(_tier(contact_class_exponents=[-0.2, 0.2]))
        tags = {r for r in runs if r.endswith("_s7")}
        assert any("phi-020" in r for r in tags)
        assert any("phi020" in r for r in tags)


class TestOccupancyAxis:
    def test_declared_num_agents_enters_the_run_id(self) -> None:
        runs = _runs(_tier(num_agents=478))
        rid = next(iter(runs))
        assert "_n478_" in rid
        spec = runs[rid]
        assert spec["campaign_parameters"]["num_agents"] == 478
        assert spec["config_overrides"]["ship_graph"]["num_agents"] == 478

    def test_two_occupancy_points_do_not_collide(self) -> None:
        manifest = _manifest({
            "rl_quarter": _tier(num_agents=478),
            "rl_half": _tier(num_agents=955),
        })
        rids = [
            rid
            for tier_id in manifest["tiers"]
            for rid, _ in generate_tier_runs(manifest, tier_id)
        ]
        assert len(rids) == len(set(rids))
        assert any("_n478_" in r for r in rids)
        assert any("_n955_" in r for r in rids)

    def test_absent_num_agents_keeps_the_run_id(self) -> None:
        rid = next(iter(_runs(_tier())))
        assert rid == TestPhiAxis.BASE_RID


class TestKernelGraded:
    """The swept coordinates must move the engine outcome they name."""

    def test_phi_grades_partner_class_share(self) -> None:
        fractions = [
            _crew_fraction(_rows(_phi_core(phi), _room(40, 10), epochs=120), 0)
            for phi in (-1.0, 0.0, 1.0)
        ]
        assert fractions == sorted(fractions, reverse=True)
        assert fractions[0] > fractions[-1]

    @staticmethod
    def _density_core(alpha: float) -> TransmissionCore:
        return TransmissionCore(
            rng=np.random.default_rng(3),
            zone_volumes={"Lounge": 200.0},
            zone_types={"Lounge": "Free"},
            cfg={
                "transmission": {
                    "contact_mode": "density_dependent",
                    "density_dependent": {
                        "reference_occupancy": 50,
                        "base_contacts_per_day": 1.33,
                        "max_contacts_per_day": 100,
                        "exponent": alpha,
                        "crew_contact_multiplier": 1.0,
                    },
                },
            },
        )

    def test_alpha_grades_occupancy_scaling(self) -> None:
        """Contacts at 3x occupancy over baseline grade with the exponent."""
        agent = _density_agent(1, "Lounge")
        ratios = []
        for alpha in (0.0, 0.5, 1.0):
            core = self._density_core(alpha)
            core.initialize_zones(["Lounge"])
            n = 4000
            hi = sum(
                core._effective_contacts(150, agent, 0) for _ in range(n)
            ) / n
            lo = sum(
                core._effective_contacts(50, agent, 0) for _ in range(n)
            ) / n
            ratios.append(hi / lo)
        assert ratios == sorted(ratios)
        assert ratios[0] == pytest.approx(1.0, abs=0.05)
        assert ratios[-1] > 2.5
