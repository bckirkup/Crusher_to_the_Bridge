"""CREW-REACH-01 campaign contract tests.

Pins the campaign grammar for campaigns/covid/crew_reach_01/: the four
blocks cover the design grid exactly once, the design's declared
``base_overrides`` equals the parent's ``sect_mess_boxed`` arm verbatim,
arm 0 carries empty overrides, and the ``observation_overrides`` arm key
writes the specimen-channel flags onto ``config_overrides.syndromic``.

The engine side of the leg is pinned at the campaign-object level:
``retest_tiers`` on a campaign day lets that day's tiers renominate
negative holders when the modality passes ``retest_on_sweep``, a
``wave``-tagged day exists only while the scenario arms its name, an
armed-but-undeclared wave raises, and ``retest_tiers`` naming a tier not
in the day's list is refused. The shipped Diamond Princess file is
checked as a contract: the crew wave is declared on 23 Feb at the
published 831 tests and the mass-screen days carry the serial-testing
declaration.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_crew_reach_01_design.json"
)
PARENT_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_crew_mess_01_design.json"
)
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "covid" / "crew_reach_01"
CAMPAIGN_DATA = (
    REPO_ROOT / "data" / "observation" / "covid_testing_campaigns.json"
)

SEEDS = list(range(20200205, 20200225))
ARM_IDS = ("boxed_declared", "boxed_s1", "boxed_s2", "boxed_s1s2")


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def design_raw() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parent_raw() -> dict:
    return json.loads(PARENT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def campaign() -> dict:
    return json.loads(
        (CAMPAIGN_DIR / "campaign.json").read_text(encoding="utf-8"),
    )


@pytest.fixture(scope="module")
def entry_mod() -> types.ModuleType:
    return _load("crew_reach_01_entry", CAMPAIGN_DIR / "entry.py")


# ---------------------------------------------------------------- design


class TestDesign:
    def test_arms_cover_the_declared_grid(self, design_raw: dict) -> None:
        arms = [a["arm_id"] for a in design_raw["arms"]]
        assert arms == list(ARM_IDS)

    def test_baseline_arm_carries_empty_overrides(
        self, design_raw: dict,
    ) -> None:
        assert design_raw["arms"][0]["overrides"] == {}

    def test_base_overrides_equals_parent_boxed_arm(
        self, design_raw: dict, parent_raw: dict,
    ) -> None:
        parent = next(
            a for a in parent_raw["arms"] if a["arm_id"] == "sect_mess_boxed"
        )
        assert design_raw["base_overrides"] == parent["overrides"]

    def test_funnel_echo_flag_on(self, design_raw: dict) -> None:
        assert design_raw["funnel_echo"] is True

    def test_design_loads_and_enumerates_80_cells(
        self, design_raw: dict,
    ) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(DESIGN_PATH))
        cells = enumerate_cells(design)
        assert len(cells) == 80
        assert {c.arm_id for c in cells} == set(ARM_IDS)
        assert {c.seed for c in cells} == set(SEEDS)


class TestCampaignJson:
    def test_blocks_cover_the_grid_once(self, campaign: dict) -> None:
        cells = {
            (name, seed)
            for name, block in campaign["blocks"].items()
            for seed in block["seeds"]
        }
        assert len(cells) == 80
        assert {b[0] for b in cells} == set(ARM_IDS)

    def test_fargate_queue_and_prefix(self, campaign: dict) -> None:
        assert campaign["queue"] == "picard-analysis-fargate-queue"
        assert campaign["s3_prefix"] == "campaign/covid_crew_reach_01/"
        assert campaign["image_tag"] == "covid-crew-reach-01"

    def test_build_argv(self, entry_mod: types.ModuleType) -> None:
        import argparse

        args = argparse.Namespace(platform="fargate")
        block = {
            "artifact": "cell_{seed}.json",
            "args": {"theta": 7900000, "arm_id": "boxed_s1s2"},
        }
        command, artifact = entry_mod.build_argv(
            args, block, 20200211, Path("/tmp/out"),
        )
        assert "--arm" in command
        assert command[command.index("--arm") + 1] == "boxed_s1s2"
        assert command[command.index("--seed") + 1] == "20200211"
        assert artifact.name == "cell_20200211.json"


# ------------------------------------------------------------- arm grammar


class TestObservationOverrides:
    def _raw(self) -> dict:
        return {"config_overrides": {"syndromic": {}}}

    def test_sweep_flag_lands_on_syndromic(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        raw = self._raw()
        apply_arm_overrides(
            raw,
            {"observation_overrides": {"retest_negative_sweeps": True}},
            profile={},
        )
        assert (
            raw["config_overrides"]["syndromic"]["retest_negatives_on_sweep"]
            is True
        )

    def test_campaign_waves_lands_on_testing_campaigns(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        raw = self._raw()
        apply_arm_overrides(
            raw,
            {"observation_overrides": {"campaign_waves": ["crew_wave"]}},
            profile={},
        )
        assert raw["config_overrides"]["syndromic"]["testing_campaigns"][
            "waves"
        ] == ["crew_wave"]

    def test_unknown_subkey_refused(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        with pytest.raises(ValueError, match="observation_overrides"):
            apply_arm_overrides(
                self._raw(),
                {"observation_overrides": {"bogus": True}},
                profile={},
            )

    def test_non_list_waves_refused(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        with pytest.raises(ValueError, match="campaign_waves"):
            apply_arm_overrides(
                self._raw(),
                {"observation_overrides": {"campaign_waves": "crew_wave"}},
                profile={},
            )


# ---------------------------------------------------------- engine mechanics


def _tiers() -> dict:
    from crusher_labs.testing_campaign import EligibilityTier

    return {
        "sweep": EligibilityTier("sweep", "everyone"),
        "crew": EligibilityTier("crew", "crew"),
    }


def _day(
    offset: int, tests: int, tiers: tuple[str, ...], **kw: object,
):
    from crusher_labs.testing_campaign import CampaignDay

    return CampaignDay(
        day_offset=offset, tests=tests, tiers=tiers, **kw,
    )


def _campaign(days: list, **kw: object):
    from crusher_labs.testing_campaign import TestingCampaign

    return TestingCampaign(
        campaign_id="unit",
        pathogen_id="p",
        source="unit",
        evidence_grade="n/a",
        tiers=_tiers(),
        days=days,
        **kw,
    )


def _agents(n: int = 40, crew: int = 10) -> list[dict]:
    return [
        {
            "agent_id": aid,
            "role": "crew" if aid >= n else "passenger",
            "age_band": "adult",
            "symptom_presentation": "asymptomatic",
            "pathogen_infections": {},
        }
        for aid in range(n + crew)
    ]


class TestRetestTiers:
    def test_sweep_tier_renominates_negative_holders(self) -> None:
        rng = np.random.default_rng(7)
        campaign = _campaign([
            _day(0, 20, ("sweep",)),
            _day(1, 20, ("sweep",), retest_tiers=("sweep",)),
        ])
        agents = _agents()
        first = set(
            campaign.specimen_roster(agents, 0, rng=rng),
        )
        second = campaign.specimen_roster(
            agents, 1,
            already_sampled=first,
            retest_on_sweep=first,
            rng=rng,
        )
        # Day 2's retest tier reaches back into the negatives.
        assert set(second) & first

    def test_undeclared_day_never_renominates(self) -> None:
        rng = np.random.default_rng(7)
        campaign = _campaign([
            _day(0, 20, ("sweep",)),
            _day(1, 20, ("sweep",)),
        ])
        agents = _agents()
        first = set(campaign.specimen_roster(agents, 0, rng=rng))
        second = campaign.specimen_roster(
            agents, 1,
            already_sampled=first,
            retest_on_sweep=first,
            rng=rng,
        )
        # Day 2 declares no retest_tiers: negatives stay barred.
        assert not (set(second) & first)

    def test_retest_tier_outside_day_tiers_refused(self) -> None:
        with pytest.raises(ValueError, match="retest_tiers"):
            _campaign([
                _day(0, 5, ("sweep",), retest_tiers=("crew",)),
            ])


class TestWaves:
    def test_wave_day_inert_until_armed(self) -> None:
        campaign = _campaign(
            [
                _day(0, 5, ("sweep",)),
                _day(1, 30, ("crew",), wave="crew_wave"),
            ],
            start_day=0,
        )
        assert campaign.day_for(1) is None
        armed = _campaign(
            [
                _day(0, 5, ("sweep",)),
                _day(1, 30, ("crew",), wave="crew_wave"),
            ],
            start_day=0, waves=("crew_wave",),
        )
        assert armed.day_for(1) is not None
        assert armed.day_for(1).wave == "crew_wave"
        assert armed.declared_waves == frozenset({"crew_wave"})

    def test_armed_wave_unknown_to_file_raises(self) -> None:
        from crusher_labs.testing_campaign import load_campaigns

        with pytest.raises(ValueError, match="waves"):
            load_campaigns(
                waves=["no_such_wave"],
                campaign_ids=["diamond_princess_2020"],
            )


class TestShippedDeclaration:
    def test_schema_validates(self) -> None:
        from simulation_utils.paths import load_validated_json

        payload = load_validated_json(
            CAMPAIGN_DATA,
            "testing_campaigns.schema.json",
            allowed_roots=(REPO_ROOT,),
        )
        assert payload["campaigns"]

    def test_dp_declares_retest_days_and_crew_wave(self) -> None:
        from crusher_labs.testing_campaign import load_campaigns

        loaded = load_campaigns(
            CAMPAIGN_DATA,
            campaign_ids=["diamond_princess_2020"],
            waves=["crew_wave"],
        )
        campaign = loaded["diamond_princess_2020"]
        by_offset = {d.day_offset: d for d in campaign.days}
        for offset in range(10, 16):
            assert by_offset[offset].retest_tiers, offset
        crew_day = by_offset[18]
        assert crew_day.tests == 831
        assert crew_day.tiers == ("crew",)
        assert crew_day.wave == "crew_wave"
        # The unarmed replica never reaches the crew wave.
        unarmed = load_campaigns(
            CAMPAIGN_DATA, campaign_ids=["diamond_princess_2020"],
        )["diamond_princess_2020"]
        assert unarmed.day_for(0) is not None
        assert all(d.wave == "" for d in [
            unarmed.day_for(off) for off in range(0, 19)
            if unarmed.day_for(off) is not None
        ]) or unarmed.day_for(18) is None

    def test_greg_mortimer_untouched(self) -> None:
        payload = json.loads(CAMPAIGN_DATA.read_text(encoding="utf-8"))
        gm = next(
            c for c in payload["campaigns"]
            if c["campaign_id"] == "greg_mortimer_2020"
        )
        assert len(gm["days"]) == 1
        assert "wave" not in gm["days"][0]
