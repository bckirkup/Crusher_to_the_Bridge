"""
crusher_labs.testing_campaign
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A published testing campaign, replayed as an observation process.

The difference between this and ``observation_model.active_screening`` is the
one the model-parameter-provenance skill warns about: a per-agent per-day
selection probability is a well-mixed pool, and a testing campaign is not one.
The Diamond Princess quarantine took 31 specimens on 5 February and 681 on 18
February, in a published order of eligibility, and a probability that produces
the same total on average produces neither the daily volume nor the order. A
campaign here is therefore a **finite daily capacity spent down a ranked
roster**, taken from the event record in
``data/observation/covid_testing_campaigns.json``.

What this module does not decide: whether a specimen comes back positive. That
is the assay's business - ``observation_model.assay_sensitivity_by_time_since_infection``
on the pathogen profile, read against the host's own day since infection - so
the campaign schedules observation and the assay resolves it. Nothing here
reads infection truth except through the eligibility rules the record itself
states (a host presenting symptoms was eligible because the ship could see the
symptoms), and no count here is fitted.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation

RULE_SYMPTOMATIC_OR_CONTACT = "symptomatic_or_cabin_contact"
RULE_PASSENGERS_IN_AGE_BANDS = "passengers_in_age_bands"
RULE_REMAINING_PASSENGERS = "remaining_passengers"
RULE_CREW = "crew"
RULE_EVERYONE = "everyone"

RULES = (
    RULE_SYMPTOMATIC_OR_CONTACT,
    RULE_PASSENGERS_IN_AGE_BANDS,
    RULE_REMAINING_PASSENGERS,
    RULE_CREW,
    RULE_EVERYONE,
)

#: Repository default location of the replicated campaigns.
CAMPAIGN_DATA_PATH = "data/observation/covid_testing_campaigns.json"


@dataclass(frozen=True)
class EligibilityTier:
    """One step of a published eligibility ladder."""

    tier_id: str
    rule: str
    age_bands: tuple[str, ...] = ()
    include_comorbid: bool = False

    def __post_init__(self) -> None:
        if self.rule not in RULES:
            raise ValueError(
                f"tier {self.tier_id}: unknown eligibility rule {self.rule!r}",
            )
        if self.rule == RULE_PASSENGERS_IN_AGE_BANDS and not (
            self.age_bands or self.include_comorbid
        ):
            raise ValueError(
                f"tier {self.tier_id}: {RULE_PASSENGERS_IN_AGE_BANDS} needs "
                "age_bands or include_comorbid",
            )


@dataclass(frozen=True)
class CampaignDay:
    """A day of the event record: how many specimens, in which order."""

    day_offset: int
    tests: int | None
    tiers: tuple[str, ...]
    date: str = ""

    @property
    def unreported(self) -> bool:
        """True where the record carries no volume for this date.

        Distinguished from a reported zero on purpose: an unreported day is a
        gap in the source, and imputing a count for it would be a fitted
        number wearing a measurement's clothes.
        """
        return self.tests is None

    @property
    def capacity(self) -> int:
        return 0 if self.tests is None else int(self.tests)


def _is_crew(agent: Mapping[str, Any]) -> bool:
    role = str(agent.get("role") or "").lower()
    if role == "crew":
        return True
    if role == "passenger":
        return False
    return str(agent.get("agent_class") or "").lower().startswith("crew")


def _is_symptomatic(agent: Mapping[str, Any]) -> bool:
    """Whether the ship can see this host is unwell.

    Reads the presentation axis the syndromic modality also reads; a
    snapshot without one falls back to the infection record's illness flag.
    """
    if "symptom_presentation" in agent:
        return agent_has_symptomatic_presentation(dict(agent))
    infections = (agent.get("pathogen_infections") or {}).values()
    return any(
        record.get("illness") == "SYMPTOMATIC" for record in infections
    )


def _is_cabin_contact(
    agent: Mapping[str, Any],
    confirmed_ids: set[int],
) -> bool:
    mates = agent.get("cabin_mate_ids") or ()
    return any(int(mate) in confirmed_ids for mate in mates)


class TestingCampaign:
    """A finite, ranked, day-indexed specimen schedule.

    ``start_day`` aligns the record's first day with a simulated day index;
    which simulated day a published date falls on is a scenario's statement,
    not this object's.
    """

    def __init__(
        self,
        campaign_id: str,
        pathogen_id: str,
        source: str,
        evidence_grade: str,
        tiers: Mapping[str, EligibilityTier],
        days: Sequence[CampaignDay],
        *,
        start_day: int = 0,
        notes: str = "",
    ) -> None:
        if not campaign_id or not pathogen_id:
            raise ValueError("campaign_id and pathogen_id are required")
        if not source or not evidence_grade:
            raise ValueError(
                f"campaign {campaign_id}: source and evidence_grade are "
                "required at the definition",
            )
        if not days:
            raise ValueError(f"campaign {campaign_id}: no days declared")
        self.campaign_id = str(campaign_id)
        self.pathogen_id = str(pathogen_id)
        self.source = str(source)
        self.evidence_grade = str(evidence_grade)
        self.notes = str(notes)
        self.start_day = int(start_day)
        self.tiers = dict(tiers)
        self._days: dict[int, CampaignDay] = {}
        for day in days:
            self._validate_day(day)
            self._days[int(day.day_offset)] = day

    def _validate_day(self, day: CampaignDay) -> None:
        if int(day.day_offset) in self._days:
            raise ValueError(
                f"campaign {self.campaign_id}: duplicate day_offset "
                f"{day.day_offset}",
            )
        if day.tests is not None and int(day.tests) < 0:
            raise ValueError(
                f"campaign {self.campaign_id}: negative tests on day "
                f"{day.day_offset}",
            )
        unknown = [tier for tier in day.tiers if tier not in self.tiers]
        if unknown:
            raise ValueError(
                f"campaign {self.campaign_id}: day {day.day_offset} names "
                f"undeclared tiers {unknown}",
            )

    # ── construction ──────────────────────────────────────────────────────

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        start_day: int = 0,
    ) -> "TestingCampaign":
        """Build one campaign from its entry in the campaign data file."""
        tiers = {
            str(tier_id): EligibilityTier(
                tier_id=str(tier_id),
                rule=str(spec.get("rule") or ""),
                age_bands=tuple(str(band) for band in (spec.get("age_bands") or ())),
                include_comorbid=bool(spec.get("include_comorbid")),
            )
            for tier_id, spec in (payload.get("eligibility_tiers") or {}).items()
        }
        days = [
            CampaignDay(
                day_offset=int(entry["day_offset"]),
                tests=None if entry.get("tests") is None else int(entry["tests"]),
                tiers=tuple(str(tier) for tier in (entry.get("tiers") or ())),
                date=str(entry.get("date") or ""),
            )
            for entry in (payload.get("days") or [])
        ]
        return cls(
            campaign_id=str(payload.get("campaign_id") or ""),
            pathogen_id=str(payload.get("pathogen_id") or ""),
            source=str(payload.get("source") or ""),
            evidence_grade=str(payload.get("evidence_grade") or ""),
            tiers=tiers,
            days=days,
            start_day=start_day,
            notes=str(payload.get("notes") or ""),
        )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        campaign_id: str,
        *,
        start_day: int = 0,
    ) -> "TestingCampaign":
        """Load one named campaign from a campaign data file."""
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        for entry in payload.get("campaigns") or []:
            if str(entry.get("campaign_id")) == str(campaign_id):
                return cls.from_dict(entry, start_day=start_day)
        raise KeyError(f"campaign {campaign_id!r} not found in {path}")

    # ── schedule ──────────────────────────────────────────────────────────

    @property
    def days(self) -> tuple[CampaignDay, ...]:
        return tuple(self._days[key] for key in sorted(self._days))

    @property
    def total_scheduled_tests(self) -> int:
        """Specimens the record reports across the whole campaign."""
        return sum(day.capacity for day in self._days.values())

    def day_for(self, day_index: int) -> CampaignDay | None:
        """The campaign day active on simulated day *day_index*, if any."""
        return self._days.get(int(day_index) - self.start_day)

    def capacity_for_day(self, day_index: int) -> int:
        day = self.day_for(day_index)
        return 0 if day is None else day.capacity

    # ── eligibility ───────────────────────────────────────────────────────

    def _tier_members(
        self,
        tier: EligibilityTier,
        agents: Sequence[Mapping[str, Any]],
        confirmed_ids: set[int],
    ) -> list[int]:
        members: list[int] = []
        for agent in agents:
            if self._matches(tier, agent, confirmed_ids):
                members.append(int(agent["agent_id"]))
        return members

    @staticmethod
    def _matches(
        tier: EligibilityTier,
        agent: Mapping[str, Any],
        confirmed_ids: set[int],
    ) -> bool:
        if tier.rule == RULE_EVERYONE:
            return True
        if tier.rule == RULE_CREW:
            return _is_crew(agent)
        if tier.rule == RULE_SYMPTOMATIC_OR_CONTACT:
            return _is_symptomatic(agent) or _is_cabin_contact(
                agent, confirmed_ids,
            )
        if _is_crew(agent):
            return False
        if tier.rule == RULE_REMAINING_PASSENGERS:
            return True
        if tier.include_comorbid and (agent.get("chronic_disease_ids") or ()):
            return True
        return str(agent.get("age_band") or "") in tier.age_bands

    def specimen_roster(
        self,
        agents: Sequence[Mapping[str, Any]],
        day_index: int,
        *,
        confirmed_ids: Iterable[int] = (),
        already_sampled: Iterable[int] = (),
        rng: np.random.Generator,
    ) -> list[int]:
        """Hosts this campaign takes a specimen from on *day_index*.

        The day's capacity is spent down the ladder: every member of the
        first tier before any member of the second, and nothing at all once
        the published count is exhausted - which is the whole point, because
        a campaign that runs out of tests on 8 February (6 of them) observes
        a different outbreak from one that has 681.

        Order *within* a tier is a draw, not a rank: the record states which
        groups were reached in which order and says nothing about who inside
        a group went first, so imposing an order there would be an invented
        number. Hosts already swabbed for this pathogen are skipped, so the
        roster is without replacement across days.
        """
        day = self.day_for(day_index)
        if day is None or day.capacity <= 0:
            return []
        confirmed = {int(aid) for aid in confirmed_ids}
        taken = {int(aid) for aid in already_sampled}
        roster: list[int] = []
        remaining = day.capacity
        for tier_id in day.tiers:
            if remaining <= 0:
                break
            members = [
                aid
                for aid in self._tier_members(
                    self.tiers[tier_id], agents, confirmed,
                )
                if aid not in taken
            ]
            if not members:
                continue
            order = rng.permutation(len(members))
            for position in order[:remaining]:
                aid = members[int(position)]
                roster.append(aid)
                taken.add(aid)
            remaining = day.capacity - len(roster)
        return roster


def load_campaigns(
    path: str | Path = CAMPAIGN_DATA_PATH,
    *,
    start_days: Mapping[str, int] | None = None,
    campaign_ids: Iterable[str] | None = None,
) -> dict[str, TestingCampaign]:
    """Load campaigns from *path*, keyed by ``campaign_id``.

    ``start_days`` aligns each campaign's first recorded day with a simulated
    day index. A campaign with no entry starts on simulated day 0.
    """
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    wanted = None if campaign_ids is None else {str(cid) for cid in campaign_ids}
    offsets = dict(start_days or {})
    campaigns: dict[str, TestingCampaign] = {}
    for entry in payload.get("campaigns") or []:
        campaign_id = str(entry.get("campaign_id") or "")
        if wanted is not None and campaign_id not in wanted:
            continue
        campaigns[campaign_id] = TestingCampaign.from_dict(
            entry, start_day=int(offsets.get(campaign_id, 0)),
        )
    if wanted is not None:
        missing = sorted(wanted - set(campaigns))
        if missing:
            raise KeyError(f"campaigns {missing} not found in {path}")
    return campaigns
