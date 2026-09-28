"""COVID-VULN-01 cell machinery (picard_framework/covid_vuln_cells.py).

The A/B is a paired endpoint design: the same takeoff-conditioned cells
under ``dose_response.alpha`` at the two declared interval endpoints, with
``susceptibility_scale`` recomputed so E[s] = Theta on every arm. These
tests lock the declaration layer — the design file's legs and arms, the
cell enumeration order the Batch array indexes resolve against, the
alpha/scale landing point in the run spec, and the override math —
without running a simulation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picard_framework.covid_rhythm_cells import RhythmLeg
from picard_framework.covid_vuln_cells import (
    BETA_FIXED,
    VulnABDesign,
    enumerate_vuln_cells,
    load_vuln_design,
    prepare_vuln_cell_spec,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_vuln_ab_v1_design.json"
)
THETA = 2.37e11


@pytest.fixture(scope="module")
def design() -> VulnABDesign:
    return load_vuln_design(str(DESIGN_PATH))


def _mini_design(**kwargs: object) -> VulnABDesign:
    base = {
        "design_id": "mini",
        "theta": THETA,
        "beta": 58.0,
        "infection_age_days": 6.8,
        "imports": 1,
        "sanitary_visit_mode": "dwell_weighted",
        "takeoff_recorded_onsets": 10,
        "arms": (
            {"arm_id": "alpha_lo", "alpha": 0.05},
            {"arm_id": "alpha_hi", "alpha": 2.0},
        ),
        "legs": (
            RhythmLeg(
                class_id="mega_cruise",
                platform_id="mega_cruise_5000",
                kind="scenario",
                scenario_id="diamond_princess_2020",
                seed_base=20200205,
                seeds=2,
            ),
        ),
    }
    base.update(kwargs)
    return VulnABDesign(**base)  # type: ignore[arg-type]


class TestDesignValidation:
    def test_design_loads(self, design: VulnABDesign) -> None:
        assert design.design_id == "covid_vuln_ab_v1"
        assert len(design.legs) == 4
        assert {a["arm_id"] for a in design.arms} == {
            "alpha_lo", "alpha_hi",
        }
        assert design.beta == pytest.approx(58.0)

    def test_rejects_one_arm(self) -> None:
        with pytest.raises(ValueError, match="two distinct arms"):
            _mini_design(arms=({"arm_id": "alpha_lo", "alpha": 0.05},))

    def test_rejects_equal_alphas(self) -> None:
        with pytest.raises(ValueError, match="distinct alpha"):
            _mini_design(
                arms=(
                    {"arm_id": "alpha_lo", "alpha": 1.0},
                    {"arm_id": "alpha_hi", "alpha": 1.0},
                ),
            )

    def test_rejects_bad_alpha(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            _mini_design(
                arms=(
                    {"arm_id": "alpha_lo", "alpha": -0.05},
                    {"arm_id": "alpha_hi", "alpha": 2.0},
                ),
            )

    def test_rejects_duplicate_class(self) -> None:
        leg = RhythmLeg(
            class_id="mega_cruise", platform_id="mega_cruise_5000",
            kind="scenario", scenario_id="diamond_princess_2020",
            seed_base=1, seeds=1,
        )
        with pytest.raises(ValueError, match="distinct"):
            _mini_design(legs=(leg, leg))


class TestEnumeration:
    def test_cell_count(self, design: VulnABDesign) -> None:
        # 4 legs x 2 arms x 20 seeds.
        assert len(list(enumerate_vuln_cells(design))) == 160

    def test_leg_major_then_arm_then_seed(
        self, design: VulnABDesign,
    ) -> None:
        cells = list(enumerate_vuln_cells(design))
        mega_lo = [c for c in cells
                   if c.class_id == "mega_cruise"
                   and c.arm_id == "alpha_lo"]
        mega_hi = [c for c in cells
                   if c.class_id == "mega_cruise"
                   and c.arm_id == "alpha_hi"]
        assert {c.index for c in mega_lo} == set(range(20))
        assert {c.index for c in mega_hi} == set(range(20, 40))
        # Pairing: same seed both arms.
        assert [c.seed for c in mega_lo] == [c.seed for c in mega_hi]
        assert {c.alpha for c in mega_lo} == {0.05}
        assert {c.alpha for c in mega_hi} == {2.0}
        expedition = [c for c in cells if c.class_id == "expedition_cruise"]
        assert min(c.seed for c in expedition) == 20200315
        assert max(c.index for c in expedition) == 159

    def test_keys_unique(self, design: VulnABDesign) -> None:
        keys = [c.key for c in enumerate_vuln_cells(design)]
        assert len(keys) == len(set(keys))


class TestSpecPreparation:
    def test_alpha_and_scale_land(self, design: VulnABDesign) -> None:
        cells = list(enumerate_vuln_cells(design))
        lo = prepare_vuln_cell_spec(design, cells[0], repo_root=str(REPO_ROOT))
        hi = prepare_vuln_cell_spec(design, cells[20], repo_root=str(REPO_ROOT))
        dr_lo = lo["pathogen_overrides"]["sars_cov2_resp"]["dose_response"]
        dr_hi = hi["pathogen_overrides"]["sars_cov2_resp"]["dose_response"]
        assert dr_lo["alpha"] == pytest.approx(0.05)
        assert dr_hi["alpha"] == pytest.approx(2.0)
        assert dr_lo["beta"] == pytest.approx(BETA_FIXED)
        # scale = Theta * (alpha + beta) / alpha keeps E[s] = Theta.
        assert dr_lo["susceptibility_scale"] == pytest.approx(
            THETA * (0.05 + BETA_FIXED) / 0.05,
        )
        assert dr_hi["susceptibility_scale"] == pytest.approx(
            THETA * (2.0 + BETA_FIXED) / 2.0,
        )
        assert dr_lo["model"] == "beta_poisson"

    def test_rhythm_and_cap_pinned(self, design: VulnABDesign) -> None:
        cells = list(enumerate_vuln_cells(design))
        raw = prepare_vuln_cell_spec(design, cells[0], repo_root=str(REPO_ROOT))
        co = raw["config_overrides"]
        assert co["rhythm"] == {"enabled": True}
        assert co["transmission"]["exposure_cap"] == {"enabled": True}

    def test_same_seed_paired_except_alpha(
        self, design: VulnABDesign,
    ) -> None:
        cells = list(enumerate_vuln_cells(design))
        lo = prepare_vuln_cell_spec(design, cells[0], repo_root=str(REPO_ROOT))
        hi = prepare_vuln_cell_spec(design, cells[20], repo_root=str(REPO_ROOT))
        assert lo["config_overrides"] == hi["config_overrides"]
        po_lo = lo["pathogen_overrides"]["sars_cov2_resp"]
        po_hi = hi["pathogen_overrides"]["sars_cov2_resp"]
        assert {
            k: v for k, v in po_lo.items() if k != "dose_response"
        } == {
            k: v for k, v in po_hi.items() if k != "dose_response"
        }
        # The incubation reference is Theta-only: unchanged across arms.
        assert po_lo.get("incubation") == po_hi.get("incubation")

    def test_generic_leg_conditioning(self, design: VulnABDesign) -> None:
        cells = list(enumerate_vuln_cells(design))
        generic = next(c for c in cells if c.class_id == "contemporary_cruise")
        raw = prepare_vuln_cell_spec(
            design, generic, repo_root=str(REPO_ROOT),
        )
        co = raw["config_overrides"]
        assert co["num_epochs"] == 32 * 24
        assert co["ship_graph"]["num_agents"] == 2100 + 900
        seed = co["initiation"]["explicit_seeds"][0]
        assert seed["pathogen"] == "sars_cov2_resp"
        assert seed["count"] == 1
        assert seed["infection_age_days"] == pytest.approx(6.8)

    def test_scenario_leg_uses_the_record(
        self, design: VulnABDesign,
    ) -> None:
        cells = list(enumerate_vuln_cells(design))
        cell = cells[120]  # first expedition cell
        raw = prepare_vuln_cell_spec(design, cell, repo_root=str(REPO_ROOT))
        assert raw["config_overrides"]["num_epochs"] == 672
        seeds = raw["config_overrides"]["initiation"]["explicit_seeds"]
        assert "onset_day" not in seeds[0]
        assert "departure_day" not in seeds[0]
