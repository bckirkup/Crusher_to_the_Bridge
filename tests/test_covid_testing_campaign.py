"""The replicated testing campaign and the symptom-onset channel (#33).

A campaign is a finite, ranked, day-indexed specimen schedule: the record
says how many swabs were taken each day and which groups were reached in
which order. The tests below check that the schedule is spent the way the
record states (capacity graded across days, ladder honoured, nothing drawn
twice), that positivity among campaign specimens comes from the assay and
not from truth, and that the onset channel is neither the sick-call roster
nor the truth channel. The shipped Diamond Princess and Greg Mortimer files
are checked only as contracts against their published totals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from crusher_labs import testing_campaigns_from_config as campaigns_from_config
from crusher_labs.modalities.syndromic import SyndromicSurveillance
from crusher_labs.testing_campaign import (
    CAMPAIGN_DATA_PATH,
    CampaignDay,
    EligibilityTier,
    TestingCampaign,
    load_campaigns,
)
from engines.infection_dynamics_bridge import KorkinAgent
from engines.sim_clock import SimClock

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "sars_cov2_resp"
_STATES = [
    "asymptomatic", "subclinical", "mild", "moderate", "severe_critical",
]

# Diamond Princess, NIID/JMIR daily test counts, 5-20 Feb 2020; the two
# ``None`` entries are the dates the record does not report.
_PUBLISHED_DP_TESTS = [
    31, 71, 171, 6, 57, 103, None, 53, 221, None,
    217, 289, 504, 681, 607, 52,
]


# ── fixtures ──────────────────────────────────────────────────────────────


def _agent(
    aid: int,
    *,
    role: str = "passenger",
    age_band: str = "adult",
    infected: bool = False,
    symptomatic: bool = False,
    time_infected: int = 0,
    cabin_mates: tuple[int, ...] = (),
    chronic: tuple[str, ...] = (),
) -> dict[str, Any]:
    infection: dict[str, Any] = {
        "status": "INFECTED" if infected else "SUSCEPTIBLE",
        "illness": "SYMPTOMATIC" if symptomatic else "ASYMPTOMATIC",
        "symptom_severity": "mild" if symptomatic else "",
        "time_infected": time_infected,
    }
    agent: dict[str, Any] = {
        "agent_id": aid,
        "role": role,
        "age_band": age_band,
        "infection_state": "infected" if infected else "susceptible",
        "symptom_presentation": "mild" if symptomatic else "asymptomatic",
        "compliance_status": "compliant",
        "pathogen_infections": {PATHOGEN: infection},
    }
    if cabin_mates:
        agent["cabin_mate_ids"] = list(cabin_mates)
    if chronic:
        agent["chronic_disease_ids"] = list(chronic)
    return agent


def _ladder() -> dict[str, EligibilityTier]:
    return {
        "symptomatic": EligibilityTier(
            "symptomatic", "symptomatic_or_cabin_contact",
        ),
        "oldest": EligibilityTier(
            "oldest", "passengers_in_age_bands", age_bands=("75+",),
            include_comorbid=True,
        ),
        "older": EligibilityTier(
            "older", "passengers_in_age_bands", age_bands=("65-74",),
        ),
        "rest": EligibilityTier("rest", "remaining_passengers"),
        "crew": EligibilityTier("crew", "crew"),
    }


_FULL_LADDER = ("symptomatic", "oldest", "older", "rest", "crew")


def _campaign(
    tests_by_day: list[int | None],
    *,
    start_day: int = 0,
    tiers: tuple[str, ...] = _FULL_LADDER,
) -> TestingCampaign:
    return TestingCampaign(
        campaign_id="unit",
        pathogen_id=PATHOGEN,
        source="unit fixture",
        evidence_grade="n/a",
        tiers=_ladder(),
        days=[
            CampaignDay(day_offset=offset, tests=tests, tiers=tiers)
            for offset, tests in enumerate(tests_by_day)
        ],
        start_day=start_day,
    )


def _profile(curve: list[float] | None = None) -> dict[str, dict[str, Any]]:
    observation: dict[str, Any] = {
        "syndrome_case_eligibility_by_severity": [0.0, 0.0, 1.0, 1.0, 1.0],
        "reporting_probability_by_severity_pre_recognition": [
            0.0, 0.0, 0.0, 0.0, 0.0,
        ],
        "reporting_probability_by_severity_post_recognition": [
            0.0, 0.0, 0.0, 0.0, 0.0,
        ],
        "episode_reporting_window_days": 7.0,
        "lab_sampling_probability_by_severity": [0.0, 0.0, 0.0, 0.0, 0.0],
        "assay_sensitivity_by_time_since_infection": curve or [1.0],
    }
    return {
        PATHOGEN: {
            "severity_model": {"states": _STATES},
            "observation_model": observation,
        },
    }


def _ship(
    passengers: int = 60,
    crew: int = 30,
    *,
    infected: int = 0,
    symptomatic: int = 0,
) -> list[dict[str, Any]]:
    bands = ["75+", "65-74", "adult", "adult"]
    agents = [
        _agent(
            aid, age_band=bands[aid % len(bands)],
            infected=aid < infected, symptomatic=aid < symptomatic,
            time_infected=0,
        )
        for aid in range(passengers)
    ]
    agents += [
        _agent(passengers + k, role="crew", age_band="adult")
        for k in range(crew)
    ]
    return agents


# ── the schedule ──────────────────────────────────────────────────────────


class TestFiniteDailyBudget:
    @pytest.mark.parametrize("capacity", [6, 57, 221])
    def test_the_roster_is_exactly_the_published_count(
        self, capacity: int,
    ) -> None:
        campaign = _campaign([capacity])
        roster = campaign.specimen_roster(
            _ship(400, 100), 0, rng=np.random.default_rng(1),
        )

        assert len(roster) == capacity
        assert len(set(roster)) == capacity

    def test_capacity_grades_the_roster_across_days(self) -> None:
        """Three published volumes, three roster sizes, same order."""
        campaign = _campaign([31, 171, 681])
        ship = _ship(600, 300)
        sizes = [
            len(campaign.specimen_roster(
                ship, day, rng=np.random.default_rng(day),
            ))
            for day in range(3)
        ]

        assert sizes == [31, 171, 681]

    def test_the_roster_is_capped_by_the_eligible_population(self) -> None:
        campaign = _campaign([500])
        roster = campaign.specimen_roster(
            _ship(20, 10), 0, rng=np.random.default_rng(1),
        )

        assert len(roster) == 30
        assert sorted(roster) == list(range(30))

    def test_an_unreported_day_schedules_nothing_and_stays_distinct(
        self,
    ) -> None:
        """``None`` is not zero: the record is silent, not empty."""
        campaign = _campaign([31, None, 0])

        assert campaign.day_for(1) is not None
        assert campaign.day_for(1).unreported
        assert not campaign.day_for(2).unreported
        assert campaign.capacity_for_day(1) == 0
        assert campaign.capacity_for_day(2) == 0
        assert campaign.specimen_roster(
            _ship(), 1, rng=np.random.default_rng(1),
        ) == []
        assert campaign.total_scheduled_tests == 31

    @pytest.mark.parametrize("start_day", [0, 4, 16])
    def test_start_day_shifts_the_whole_schedule(self, start_day: int) -> None:
        campaign = _campaign([10, 20], start_day=start_day)

        assert campaign.capacity_for_day(start_day - 1) == 0
        assert campaign.capacity_for_day(start_day) == 10
        assert campaign.capacity_for_day(start_day + 1) == 20
        assert campaign.capacity_for_day(start_day + 2) == 0

    def test_a_pinned_stream_reproduces_the_roster(self) -> None:
        campaign = _campaign([40])
        ship = _ship()
        first = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(3))
        second = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(3))
        other = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(4))

        assert first == second
        assert first != other


class TestEligibilityLadder:
    def test_symptomatic_and_cabin_contacts_go_first(self) -> None:
        ship = _ship(40, 10)
        ship[7]["symptom_presentation"] = "symptomatic"
        ship[7]["pathogen_infections"][PATHOGEN]["illness"] = "SYMPTOMATIC"
        ship[12]["cabin_mate_ids"] = [99]
        campaign = _campaign([2])
        roster = campaign.specimen_roster(
            ship, 0, confirmed_ids={99}, rng=np.random.default_rng(1),
        )

        assert sorted(roster) == [7, 12]

    def test_each_rung_is_exhausted_before_the_next_begins(self) -> None:
        ship = _ship(40, 20)
        oldest = {a["agent_id"] for a in ship if a["age_band"] == "75+"}
        older = {a["agent_id"] for a in ship if a["age_band"] == "65-74"}
        campaign = _campaign([len(oldest) + 3])
        roster = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(2))

        assert oldest <= set(roster)
        assert len(set(roster) - oldest) == 3
        assert set(roster) - oldest <= older

    def test_comorbidity_lifts_a_young_passenger_into_the_oldest_rung(
        self,
    ) -> None:
        ship = _ship(40, 0)
        ship[2]["chronic_disease_ids"] = ["diabetes"]
        assert ship[2]["age_band"] == "adult"
        oldest = {a["agent_id"] for a in ship if a["age_band"] == "75+"}
        campaign = _campaign([len(oldest) + 1])
        roster = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(2))

        assert set(roster) == oldest | {2}

    def test_crew_are_reached_only_after_every_passenger(self) -> None:
        ship = _ship(30, 30)
        passengers = {a["agent_id"] for a in ship if a["role"] == "passenger"}
        campaign = _campaign([30 + 5])
        roster = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(5))

        assert set(roster[:30]) == passengers
        assert all(ship[aid]["role"] == "crew" for aid in roster[30:])
        assert len(roster) == 35

    def test_a_day_without_the_crew_rung_never_reaches_crew(self) -> None:
        ship = _ship(10, 50)
        campaign = _campaign([40], tiers=_FULL_LADDER[:-1])
        roster = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(5))

        assert len(roster) == 10
        assert all(ship[aid]["role"] == "passenger" for aid in roster)

    def test_the_everyone_rung_has_no_order(self) -> None:
        """Greg Mortimer: one day, one rung, passengers and crew alike."""
        tier = {"everyone": EligibilityTier("everyone", "everyone")}
        campaign = TestingCampaign(
            "gm", PATHOGEN, "unit", "n/a", tier,
            [CampaignDay(0, 217, ("everyone",))],
        )
        ship = _ship(128, 95)
        roster = campaign.specimen_roster(ship, 0, rng=np.random.default_rng(8))
        roles = {ship[aid]["role"] for aid in roster[:20]}

        assert len(roster) == 217
        assert roles == {"passenger", "crew"}

    def test_hosts_already_swabbed_are_never_drawn_again(self) -> None:
        campaign = _campaign([25, 25, 25])
        ship = _ship(40, 40)
        taken: set[int] = set()
        for day in range(3):
            roster = campaign.specimen_roster(
                ship, day, already_sampled=taken, rng=np.random.default_rng(day),
            )
            assert not taken & set(roster)
            taken |= set(roster)
        assert len(taken) == 75


class TestCampaignRefusals:
    def test_an_unknown_rule_is_refused(self) -> None:
        with pytest.raises(ValueError, match="rule"):
            EligibilityTier("x", "by_deck")

    def test_an_age_rung_needs_bands_or_comorbidity(self) -> None:
        with pytest.raises(ValueError):
            EligibilityTier("x", "passengers_in_age_bands")

    def test_a_day_naming_an_undeclared_rung_is_refused(self) -> None:
        with pytest.raises(ValueError, match="undeclared"):
            _campaign([1], tiers=("symptomatic", "nurses"))

    def test_source_and_grade_are_required_at_the_definition(self) -> None:
        with pytest.raises(ValueError, match="source"):
            TestingCampaign(
                "x", PATHOGEN, "", "", _ladder(),
                [CampaignDay(0, 1, ("crew",))],
            )

    def test_negative_and_duplicate_days_are_refused(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            TestingCampaign(
                "x", PATHOGEN, "s", "B", _ladder(),
                [CampaignDay(0, -1, ("crew",))],
            )
        with pytest.raises(ValueError, match="duplicate"):
            TestingCampaign(
                "x", PATHOGEN, "s", "B", _ladder(),
                [CampaignDay(0, 1, ("crew",)), CampaignDay(0, 2, ("crew",))],
            )


# ── the modality ──────────────────────────────────────────────────────────


def _surveillance(
    campaign: TestingCampaign | None,
    *,
    curve: list[float] | None = None,
    seed: int = 7,
    sick_call: float = 0.0,
) -> SyndromicSurveillance:
    return SyndromicSurveillance(
        sick_call_probability=sick_call,
        background_noise_rate=0.0,
        symptom_severity_profiles=_profile(curve),
        clock=SimClock(epoch_duration_hours=6.0, mode="hours"),
        rng=np.random.default_rng(seed),
        testing_campaigns=[campaign] if campaign else None,
    )


class TestCampaignInsideTheModality:
    def test_a_campaign_day_is_spent_once_on_its_first_epoch(self) -> None:
        surveillance = _surveillance(_campaign([10, 20]))
        ship = _ship()
        per_epoch = [
            len(surveillance.query_ground_truth({"agents": ship, "epoch": epoch})[
                "campaign_specimens_by_pathogen"
            ].get(PATHOGEN, []))
            for epoch in range(8)
        ]

        assert per_epoch == [10, 0, 0, 0, 20, 0, 0, 0]
        assert surveillance.query_ground_truth({"agents": ship, "epoch": 8})[
            "campaign_specimens_by_pathogen"
        ] == {}

    def test_campaign_specimens_enter_the_shared_lab_ledger(self) -> None:
        surveillance = _surveillance(_campaign([12]))
        result = surveillance.query_ground_truth({"agents": _ship(), "epoch": 0})

        assert result["lab_sampled_count"] == 12
        assert set(result["campaign_specimens_by_pathogen"][PATHOGEN]) == set(
            result["lab_sampled_by_pathogen"][PATHOGEN],
        )

    @pytest.mark.parametrize(
        ("sensitivity", "low", "high"),
        [(0.0, 0.0, 0.0), (0.5, 0.35, 0.65), (1.0, 1.0, 1.0)],
    )
    def test_positivity_is_the_assay_draw_not_the_truth_state(
        self, sensitivity: float, low: float, high: float,
    ) -> None:
        """Every host is infected; the assay decides who is confirmed."""
        surveillance = _surveillance(_campaign([200]), curve=[sensitivity])
        ship = _ship(200, 0, infected=200)
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 0})
        confirmed = result["campaign_confirmed_by_pathogen"][PATHOGEN]
        share = len(confirmed) / 200

        assert low <= share <= high
        assert set(confirmed) <= set(
            result["campaign_specimens_by_pathogen"][PATHOGEN],
        )

    def test_positivity_reads_the_day_of_infection_the_swab_falls_on(
        self,
    ) -> None:
        """Same roster size, three infection ages, graded positivity.

        ``time_infected`` counts epochs since infection; at six-hour epochs
        four of them are one day on the sensitivity curve.
        """
        curve = [0.0, 0.3, 0.9]
        shares = []
        for age_days in (0, 1, 2):
            surveillance = _surveillance(_campaign([150]), curve=curve)
            ship = [
                _agent(aid, infected=True, time_infected=4 * age_days)
                for aid in range(150)
            ]
            result = surveillance.query_ground_truth(
                {"agents": ship, "epoch": 0},
            )
            shares.append(
                len(result["campaign_confirmed_by_pathogen"][PATHOGEN]) / 150,
            )

        assert shares == sorted(shares)
        assert shares[0] == pytest.approx(0.0)
        assert shares[1] == pytest.approx(0.3, abs=0.1)
        assert shares[2] == pytest.approx(0.9, abs=0.08)

    def test_an_uninfected_roster_yields_no_confirmations(self) -> None:
        surveillance = _surveillance(_campaign([50]), curve=[1.0])
        result = surveillance.query_ground_truth({"agents": _ship(), "epoch": 0})

        assert len(result["campaign_specimens_by_pathogen"][PATHOGEN]) == 50
        assert result["campaign_confirmed_by_pathogen"][PATHOGEN] == []
        assert result["lab_confirmed_count"] == 0

    def test_the_specimen_log_holds_one_entry_per_swab_in_order(self) -> None:
        surveillance = _surveillance(_campaign([5, 3]), curve=[1.0])
        ship = _ship(200, 0, infected=200)
        for epoch in range(5):
            surveillance.query_ground_truth({"agents": ship, "epoch": epoch})
        log = surveillance.campaign_specimen_log(PATHOGEN)

        assert len(log) == 8
        assert [entry["day"] for entry in log] == [0] * 5 + [1] * 3
        assert [entry["epoch"] for entry in log] == [0] * 5 + [4] * 3
        assert len({entry["agent_id"] for entry in log}) == 8
        assert all(entry["positive"] for entry in log)
        assert surveillance.campaign_specimen_log("norwalk_gi") == []

    def test_specimen_positivity_in_the_log_is_the_assay_draw(self) -> None:
        surveillance = _surveillance(_campaign([40]), curve=[0.0])
        surveillance.query_ground_truth(
            {"agents": _ship(200, 0, infected=200), "epoch": 0},
        )
        log = surveillance.campaign_specimen_log(PATHOGEN)

        assert len(log) == 40
        assert not any(entry["positive"] for entry in log)

    def test_symptomatic_at_specimen_is_the_state_when_swabbed(self) -> None:
        """A host that presents after its swab is asymptomatic in the log."""
        surveillance = _surveillance(_campaign([2, 2]), curve=[1.0])
        ship = [
            _agent(0, infected=True, symptomatic=True),
            _agent(1, infected=True),
            _agent(2, infected=True),
            _agent(3, infected=True),
        ]
        surveillance.query_ground_truth({"agents": ship, "epoch": 0})
        ship[1]["pathogen_infections"][PATHOGEN]["illness"] = "SYMPTOMATIC"
        ship[1]["pathogen_infections"][PATHOGEN]["symptom_severity"] = "mild"
        ship[1]["symptom_presentation"] = "mild"
        for epoch in range(1, 5):
            surveillance.query_ground_truth({"agents": ship, "epoch": epoch})
        log = surveillance.campaign_specimen_log(PATHOGEN)
        first_day = {e["agent_id"]: e["symptomatic_at_specimen"] for e in log[:2]}

        assert first_day[0] is True
        assert first_day[1] is False

    def test_no_campaign_means_no_campaign_keys_are_populated(self) -> None:
        surveillance = _surveillance(None)
        result = surveillance.query_ground_truth({"agents": _ship(), "epoch": 0})

        assert result["campaign_specimens_by_pathogen"] == {}
        assert result["lab_sampled_count"] == 0

    def test_two_campaigns_for_one_pathogen_are_refused(self) -> None:
        with pytest.raises(ValueError, match="two testing campaigns"):
            SyndromicSurveillance(
                symptom_severity_profiles=_profile(),
                testing_campaigns=[_campaign([1]), _campaign([2])],
            )

    def test_a_campaign_for_an_unmodelled_pathogen_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no observation_model"):
            SyndromicSurveillance(
                symptom_severity_profiles={},
                testing_campaigns=[_campaign([1])],
            )


class TestAssayReadsTheEnginePayload:
    """The seam the unit fixtures bypass: the engine's own agent export.

    The assay reads ``time_infected`` off ``pathogen_infections``; a payload
    that omits it silently reads day zero of the sensitivity curve, where a
    day-indexed PCR curve is 0.0, and every campaign swab comes back
    negative regardless of how many infected hosts are on the roster.
    """

    @staticmethod
    def _engine_agent(aid: int, epochs_infected: int) -> dict[str, Any]:
        clock = SimClock(epoch_duration_hours=6.0, mode="hours")
        agent = KorkinAgent(
            agent_id=aid, role="passenger", immune=False,
            home_zone="Cabin_A", dining_zone="MainDining_L",
            work_zone="Main_Pool_Deck", free_zone="Main_Pool_Deck",
            schedule=["home"] * 4,
        )
        agent.clock = clock
        agent.infect_with_pathogen(PATHOGEN, 100.0, 0, rng=np.random.default_rng(aid))
        agent.infections[PATHOGEN]["time_infected"] = epochs_infected
        return agent.to_schema_dict()

    def test_payload_carries_the_epoch_counter_the_assay_reads(self) -> None:
        payload = self._engine_agent(1, 8)["pathogen_infections"][PATHOGEN]

        assert payload["status"] == "INFECTED"
        assert payload["time_infected"] == 8
        assert payload["days_post_infection"] == 2

    def test_late_swab_of_engine_agents_is_positive_at_the_curve_tail(
        self,
    ) -> None:
        curve = [0.0, 0.0, 0.9]
        shares = []
        for epochs_infected in (0, 8):
            surveillance = _surveillance(_campaign([150]), curve=curve)
            ship = [self._engine_agent(aid, epochs_infected) for aid in range(150)]
            result = surveillance.query_ground_truth(
                {"agents": ship, "epoch": 0},
            )
            shares.append(
                len(result["campaign_confirmed_by_pathogen"][PATHOGEN]) / 150,
            )

        assert shares[0] == pytest.approx(0.0)
        assert shares[1] == pytest.approx(0.9, abs=0.08)


class TestSymptomOnsetChannel:
    def test_onset_is_recorded_for_confirmed_symptomatic_hosts_only(
        self,
    ) -> None:
        surveillance = _surveillance(_campaign([90]), curve=[1.0])
        ship = _ship(60, 30, infected=40, symptomatic=20)
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 0})
        recorded = {r["agent_id"] for r in result["onset_observations"]}

        assert recorded == set(range(20))
        assert result["onset_observation_count"] == 20
        for record in result["onset_observations"]:
            assert record["onset_day"] == 0
            assert record["symptom_severity"] == "mild"
            assert record["role"] == "passenger"

    def test_onset_is_not_the_sick_call_roster(self) -> None:
        """Nobody reports, everybody symptomatic is confirmed: 0 vs 20."""
        surveillance = _surveillance(_campaign([90]), curve=[1.0], sick_call=0.0)
        ship = _ship(60, 30, infected=40, symptomatic=20)
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 0})

        assert result["sick_call_count"] == 0
        assert result["onset_observation_count"] == 20

    def test_onset_is_not_the_truth_channel(self) -> None:
        """A symptomatic host the assay misses has no recorded onset."""
        surveillance = _surveillance(_campaign([90]), curve=[0.0])
        ship = _ship(60, 30, infected=40, symptomatic=20)
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 0})

        assert result["onset_observation_count"] == 0
        assert len(result["episode_detection_telemetry"]) == 0

    def test_the_onset_day_is_the_first_presenting_day_not_the_swab_day(
        self,
    ) -> None:
        surveillance = _surveillance(_campaign([0, 0, 5]), curve=[1.0])
        ship = _ship(5, 0, infected=5, symptomatic=5)
        surveillance.query_ground_truth({"agents": ship, "epoch": 0})
        surveillance.query_ground_truth({"agents": ship, "epoch": 4})
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 8})

        assert result["onset_observation_count"] == 5
        for record in result["onset_observations"]:
            assert record["onset_day"] == 0
            assert record["confirmed_epoch"] == 8
            assert record["recorded_epoch"] == 8

    def test_each_host_enters_the_channel_once(self) -> None:
        surveillance = _surveillance(_campaign([5]), curve=[1.0])
        ship = _ship(5, 0, infected=5, symptomatic=5)
        first = surveillance.query_ground_truth({"agents": ship, "epoch": 0})
        later = surveillance.query_ground_truth({"agents": ship, "epoch": 1})

        assert first["onset_observation_count"] == 5
        assert later["onset_observation_count"] == 0

    def test_the_curve_splits_passengers_from_crew(self) -> None:
        surveillance = _surveillance(_campaign([90]), curve=[1.0])
        ship = _ship(60, 30)
        for aid in (0, 1, 2, 60, 61):
            ship[aid]["pathogen_infections"][PATHOGEN].update(
                status="INFECTED", illness="SYMPTOMATIC", symptom_severity="mild",
            )
            ship[aid]["symptom_presentation"] = "mild"
        surveillance.query_ground_truth({"agents": ship, "epoch": 0})

        assert surveillance.onset_observation_curve(PATHOGEN) == {
            0: {"passenger": 3, "crew": 2},
        }

    def test_a_severity_outside_the_syndrome_is_not_datable(self) -> None:
        surveillance = _surveillance(_campaign([5]), curve=[1.0])
        ship = _ship(5, 0, infected=5, symptomatic=5)
        for agent in ship:
            agent["pathogen_infections"][PATHOGEN]["symptom_severity"] = (
                "subclinical"
            )
        result = surveillance.query_ground_truth({"agents": ship, "epoch": 0})

        assert result["lab_confirmed_count"] == 5
        assert result["onset_observation_count"] == 0


# ── the shipped records ───────────────────────────────────────────────────


class TestShippedCampaignRecords:
    def test_diamond_princess_reproduces_the_published_table(self) -> None:
        campaign = load_campaigns(REPO_ROOT / CAMPAIGN_DATA_PATH)[
            "diamond_princess_2020"
        ]

        assert [day.tests for day in campaign.days] == _PUBLISHED_DP_TESTS
        assert campaign.total_scheduled_tests == 3063
        assert campaign.pathogen_id == PATHOGEN
        for day in campaign.days:
            assert day.tiers[0] == "symptomatic_or_contact"
            assert (day.tiers[-1] == "crew") == (day.date >= "2020-02-11")

    def test_the_ladder_opens_to_the_whole_ship_on_11_february(self) -> None:
        campaign = load_campaigns(REPO_ROOT / CAMPAIGN_DATA_PATH)[
            "diamond_princess_2020"
        ]
        by_date = {day.date: day for day in campaign.days}

        assert "other_passengers" not in by_date["2020-02-10"].tiers
        assert "other_passengers" in by_date["2020-02-11"].tiers
        assert by_date["2020-02-11"].unreported
        assert by_date["2020-02-14"].unreported

    def test_greg_mortimer_is_one_day_one_rung(self) -> None:
        campaign = load_campaigns(REPO_ROOT / CAMPAIGN_DATA_PATH)[
            "greg_mortimer_2020"
        ]

        assert len(campaign.days) == 1
        assert campaign.total_scheduled_tests == 217
        assert campaign.days[0].tiers == ("everyone",)

    def test_every_record_carries_source_and_grade(self) -> None:
        with (REPO_ROOT / CAMPAIGN_DATA_PATH).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        for entry in payload["campaigns"]:
            assert entry["source"]
            assert entry["evidence_grade"]
            assert entry["notes"]

    def test_the_config_seam_aligns_by_start_day(self) -> None:
        campaigns = campaigns_from_config({
            "testing_campaigns": {
                "campaign_file": str(REPO_ROOT / CAMPAIGN_DATA_PATH),
                "campaigns": [
                    {"campaign_id": "diamond_princess_2020", "start_day": 16},
                ],
            },
        })

        assert [c.campaign_id for c in campaigns] == ["diamond_princess_2020"]
        assert campaigns[0].capacity_for_day(15) == 0
        assert campaigns[0].capacity_for_day(16) == 31
        assert campaigns[0].capacity_for_day(16 + 13) == 681
        assert campaigns_from_config({}) == []
