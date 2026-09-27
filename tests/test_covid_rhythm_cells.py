"""COVID-RHYTHM-01 cell machinery (picard_framework/covid_rhythm_cells.py).

The A/B is a paired design: the same takeoff-conditioned cell under
``rhythm.enabled`` false vs true. These tests lock the declaration layer —
the design file's legs and arms, the cell enumeration order the Batch array
indexes resolve against, the flag's landing point in the run spec, and the
zone/mask helpers the instruments read — without running a simulation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picard_framework.covid_rhythm_cells import (
    RhythmABDesign,
    RhythmLeg,
    crew_zone_names,
    enumerate_rhythm_cells,
    load_rhythm_design,
    prepare_rhythm_cell_spec,
    sync_end_epoch_mask,
    transit_zone_names,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_rhythm_ab_v1_design.json"
)


@pytest.fixture(scope="module")
def design() -> RhythmABDesign:
    return load_rhythm_design(str(DESIGN_PATH))


def _mini_design(**kwargs: object) -> RhythmABDesign:
    base = {
        "design_id": "mini",
        "theta": 2.37e11,
        "infection_age_days": 6.8,
        "imports": 1,
        "sanitary_visit_mode": "dwell_weighted",
        "takeoff_recorded_onsets": 10,
        "arms": (
            {"arm_id": "off", "overrides": {"rhythm": {"enabled": False}}},
            {"arm_id": "on", "overrides": {"rhythm": {"enabled": True}}},
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
    return RhythmABDesign(**base)  # type: ignore[arg-type]


class TestDesignValidation:
    def test_design_loads(self, design: RhythmABDesign) -> None:
        assert design.design_id == "covid_rhythm_ab_v1"
        assert len(design.legs) == 4
        assert {a["arm_id"] for a in design.arms} == {"off", "on"}

    def test_rejects_one_arm(self) -> None:
        with pytest.raises(ValueError, match="two distinct arms"):
            _mini_design(
                arms=(
                    {"arm_id": "off",
                     "overrides": {"rhythm": {"enabled": False}}},
                ),
            )

    def test_rejects_non_rhythm_override(self) -> None:
        with pytest.raises(ValueError, match="rhythm"):
            _mini_design(
                arms=(
                    {"arm_id": "off",
                     "overrides": {"rhythm": {"enabled": False},
                                   "seed_patch": {}}},
                    {"arm_id": "on",
                     "overrides": {"rhythm": {"enabled": True}}},
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
    def test_cell_count(self, design: RhythmABDesign) -> None:
        # 4 legs x 2 arms x 20 seeds.
        assert len(list(enumerate_rhythm_cells(design))) == 160

    def test_leg_major_then_arm_then_seed(
        self, design: RhythmABDesign,
    ) -> None:
        cells = list(enumerate_rhythm_cells(design))
        mega_off = [c for c in cells
                    if c.class_id == "mega_cruise" and c.arm_id == "off"]
        mega_on = [c for c in cells
                   if c.class_id == "mega_cruise" and c.arm_id == "on"]
        assert {c.index for c in mega_off} == set(range(20))
        assert {c.index for c in mega_on} == set(range(20, 40))
        # Pairing: same seed both arms.
        assert [c.seed for c in mega_off] == [c.seed for c in mega_on]
        # Expedition seeds come from the 20200315 base.
        expedition = [c for c in cells if c.class_id == "expedition_cruise"]
        assert min(c.seed for c in expedition) == 20200315
        assert max(c.index for c in expedition) == 159

    def test_keys_unique(self, design: RhythmABDesign) -> None:
        keys = [c.key for c in enumerate_rhythm_cells(design)]
        assert len(keys) == len(set(keys))


class TestSpecPreparation:
    def test_flag_lands(self, design: RhythmABDesign) -> None:
        cells = list(enumerate_rhythm_cells(design))
        off = prepare_rhythm_cell_spec(design, cells[0], repo_root=str(REPO_ROOT))
        on = prepare_rhythm_cell_spec(design, cells[20], repo_root=str(REPO_ROOT))
        assert off["config_overrides"]["rhythm"] == {"enabled": False}
        assert on["config_overrides"]["rhythm"] == {"enabled": True}
        # Same seed, same everything else: a paired draw.
        drop = {k: v for k, v in off["config_overrides"].items()
                if k != "rhythm"}
        assert drop == {
            k: v for k, v in on["config_overrides"].items()
            if k != "rhythm"
        }

    def test_generic_leg_conditioning(self, design: RhythmABDesign) -> None:
        cells = list(enumerate_rhythm_cells(design))
        generic = next(c for c in cells if c.class_id == "contemporary_cruise")
        raw = prepare_rhythm_cell_spec(
            design, generic, repo_root=str(REPO_ROOT),
        )
        co = raw["config_overrides"]
        assert co["num_epochs"] == 32 * 24
        assert co["ship_graph"]["num_agents"] == 2100 + 900
        classes = co["ship_graph"]["agent_classes"]
        assert {c["class_id"] for c in classes} == {
            "passenger_general", "crew_general",
        }
        seed = co["initiation"]["explicit_seeds"][0]
        assert seed["pathogen"] == "sars_cov2_resp"
        assert seed["count"] == 1
        assert seed["infection_age_days"] == pytest.approx(6.8)
        assert seed["onset_day"] == pytest.approx(-1.0)
        assert seed["departure_day"] == pytest.approx(5.0)
        protocols = co["scenario_schedule"]["protocols"]
        assert protocols[0]["protocol_id"] == "SOP-017"
        assert (protocols[0]["start_day"], protocols[0]["end_day"]) == (16, 30)
        # The theta dial lands in the pathogen override, not the overrides.
        assert "rhythm" not in raw.get("pathogen_overrides", {}).get(
            "sars_cov2_resp", {},
        )

    def test_scenario_leg_uses_the_record(
        self, design: RhythmABDesign,
    ) -> None:
        cells = list(enumerate_rhythm_cells(design))
        cell = cells[120]  # first expedition cell
        raw = prepare_rhythm_cell_spec(design, cell, repo_root=str(REPO_ROOT))
        assert raw["config_overrides"]["num_epochs"] == 672
        seeds = raw["config_overrides"]["initiation"]["explicit_seeds"]
        # Greg Mortimer's generic boarding axis (v12 stage-3 convention):
        # no onset/departure days, drawn incubation age, no ascertainment
        # gate.
        assert "onset_day" not in seeds[0]
        assert "departure_day" not in seeds[0]
        assert "molecular_ascertainment_start_day" not in (
            raw["config_overrides"].get("syndromic") or {}
        )


class TestZoneHelpers:
    def test_crew_zones_nonempty_and_disjoint(
        self, design: RhythmABDesign,
    ) -> None:
        for leg in design.legs:
            crew = crew_zone_names(leg.platform_id, repo_root=str(REPO_ROOT))
            transit = transit_zone_names(
                leg.platform_id, repo_root=str(REPO_ROOT),
            )
            assert crew, leg.class_id
            assert transit, leg.class_id
            assert not (crew & transit), leg.class_id

    def test_mask_respects_sop_window(self, design: RhythmABDesign) -> None:
        leg = design.leg("expedition_cruise")
        mask = sync_end_epoch_mask(
            leg.platform_id, 672,
            repo_root=str(REPO_ROOT), sop_window=leg.sop017_window,
        )
        assert len(mask) == 672
        assert any(mask)
        # Every masked epoch lies outside the confinement days.
        assert not any(
            mask[e] for e in range(672) if 8 <= e // 24 <= 27
        )

    def test_mask_empty_without_sop_is_superset(
        self, design: RhythmABDesign,
    ) -> None:
        leg = design.leg("mega_cruise")
        masked = sync_end_epoch_mask(
            leg.platform_id, 768,
            repo_root=str(REPO_ROOT), sop_window=leg.sop017_window,
        )
        full = sync_end_epoch_mask(
            leg.platform_id, 768, repo_root=str(REPO_ROOT),
        )
        assert sum(masked) < sum(full)
