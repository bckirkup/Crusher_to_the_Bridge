"""
crusher_labs.modalities.syndromic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Syndromic surveillance – models sick-call reporting with:
- A parameterizable probability that truly symptomatic agents report.
- Optional detection_delay_hours gate after symptom onset.
- Optional proactive crew screening on a fixed interval.
- A molecular ascertainment rung (specimen collection plus assay) kept
  separate from the syndromic rung, so a laboratory-confirmed count is
  not the same observable as a medically attended one.
- Optional replicated testing campaigns (``crusher_labs.testing_campaign``)
  that spend a published daily specimen count down a published eligibility
  ladder, and a symptom-onset channel that records the onset day of
  confirmed cases - the observable the COVID trajectory is scored on, which
  is neither the sick-call roster nor the truth channel.
- FRED-style categorized background noise (seasickness, fatigue,
  minor injury) so healthy agents generate realistic false-signal
  clutter with specific complaint reasons.
- Quarantine compliance tracking: when isolation is ordered, agents
  may stochastically refuse or delay compliance (FRED behavioral
  failure pattern from ``FRED/src/Person.h`` vaccine refusal logic).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from crusher_labs.testing_campaign import TestingCampaign
from engines.sim_clock import SimClock
from simulation_utils.numeric import default_simulation_rng


def _symptomatic_infection(agent: dict[str, Any]) -> dict[str, Any]:
    """Return the first symptomatic pathogen infection on an agent."""
    return next(
        (
            record
            for record in (agent.get("pathogen_infections") or {}).values()
            if record.get("illness") == "SYMPTOMATIC"
        ),
        {},
    )


# Spawn keys for the molecular rung's and the campaign roster's own streams.
# Large so they cannot collide with the sequential keys ``SeedSequence.spawn``
# hands out.
_MOLECULAR_SPAWN_KEY = 7919
_CAMPAIGN_SPAWN_KEY = 7927


def _molecular_stream(
    rng: np.random.Generator,
    spawn_key: int = _MOLECULAR_SPAWN_KEY,
) -> np.random.Generator:
    """Return an independent generator for specimen and assay draws.

    The laboratory modalities share one generator, so a specimen draw taken
    from it would shift every RDT, PCR and sequencing draw that follows.
    Deriving the child from the parent's entropy, without calling ``spawn``,
    leaves the parent's own spawn counter untouched.
    """
    seed_seq = getattr(rng.bit_generator, "seed_seq", None)
    if isinstance(seed_seq, np.random.SeedSequence):
        child = np.random.SeedSequence(
            seed_seq.entropy,
            spawn_key=(*seed_seq.spawn_key, spawn_key),
        )
        return np.random.default_rng(child)
    return np.random.default_rng(spawn_key)


def _agent_is_crew(agent: dict[str, Any]) -> bool:
    role = str(agent.get("role") or "").lower()
    if role == "crew":
        return True
    if role == "passenger":
        return False
    a_class = str(agent.get("agent_class") or "").lower()
    return a_class.startswith("crew")


class SyndromicSurveillance:
    """Symptom-based screening modality with FRED-style behavioral noise."""

    name = "syndromic"

    def __init__(
        self,
        sick_call_probability: float = 0.70,
        background_noise_rate: float = 0.015,
        noise_categories: list[dict[str, Any]] | None = None,
        quarantine_compliance: float = 0.85,
        compliance_delay_epochs: int = 1,
        reluctant_fraction: float = 0.75,
        reluctant_delay_epochs: int = 48,
        compliance_by_class: dict[str, float] | None = None,
        detection_delay_epochs: int = 0,
        crew_screening_interval_epochs: int | None = None,
        reluctant_delay_hours: float | None = None,
        compliance_delay_hours: float | None = None,
        detection_delay_hours: float | None = None,
        crew_screening_interval_hours: float | None = None,
        sick_call_severity_mode: str = "own_severity",
        symptom_severity_profiles: dict[str, dict[str, Any]] | None = None,
        clock: SimClock | None = None,
        rng: np.random.Generator | None = None,
        testing_campaigns: Iterable[TestingCampaign] | None = None,
    ) -> None:
        self.sick_call_probability = sick_call_probability
        self.sick_call_severity_mode = sick_call_severity_mode
        self.symptom_severity_profiles = dict(symptom_severity_profiles or {})
        self.clock = clock or SimClock()
        self.background_noise_rate = background_noise_rate
        self.quarantine_compliance = quarantine_compliance
        # Deprecated: forced post-delay compliance removed. Kept for config compat.
        self.compliance_delay_epochs = (
            self.clock.epochs_for_hours(compliance_delay_hours)
            if compliance_delay_hours is not None
            else compliance_delay_epochs
        )
        self.reluctant_fraction = float(reluctant_fraction)
        self.reluctant_delay_epochs = (
            self.clock.epochs_for_hours(reluctant_delay_hours)
            if reluctant_delay_hours is not None
            else int(reluctant_delay_epochs)
        )
        self.compliance_by_class = dict(compliance_by_class or {})
        self.detection_delay_epochs = (
            self.clock.epochs_for_hours(detection_delay_hours)
            if detection_delay_hours is not None
            else max(0, int(detection_delay_epochs))
        )
        if crew_screening_interval_hours is not None:
            crew_screening_interval_epochs = self.clock.epochs_for_hours(
                crew_screening_interval_hours,
            )
        if crew_screening_interval_epochs is None:
            self.crew_screening_interval_epochs: int | None = None
        else:
            interval = int(crew_screening_interval_epochs)
            self.crew_screening_interval_epochs = interval if interval > 0 else None
        self.rng = rng if rng is not None else default_simulation_rng()
        self._molecular_rng = _molecular_stream(self.rng)
        # Sticky per-agent compliance class for the cruise (compliant/reluctant/defiant)
        self._compliance_class: dict[int, str] = {}
        # First epoch agent observed symptomatic (for detection_delay_hours)
        self._symptom_onset_epoch: dict[int, int] = {}
        self._first_sick_call_epoch: dict[int, int] = {}
        # One specimen per agent per pathogen, keyed (pathogen_id, agent_id):
        # a case swabbed on day two is not a second case when it is still
        # sick on day three.
        self._lab_sampled: dict[tuple[str, int], int] = {}
        self._lab_confirmed: dict[tuple[str, int], int] = {}
        # Replicated campaigns, one per pathogen; each spends its day's
        # capacity exactly once, on the first epoch of that day.
        self._campaign_rng = _molecular_stream(self.rng, _CAMPAIGN_SPAWN_KEY)
        self._campaigns = self._index_campaigns(testing_campaigns)
        self._campaign_days_run: set[tuple[str, int]] = set()
        # Symptom-onset channel: the first epoch each host presented symptoms,
        # whether or not it was free to report them (an isolated host still
        # has an onset day), and the subset whose onset entered the record.
        self._presentation_onset_epoch: dict[int, int] = {}
        self._onset_observations: dict[tuple[str, int], dict[str, Any]] = {}

        # None → built-in defaults; explicit [] disables background noise categories.
        if noise_categories is None:
            self.noise_categories = [
                {"reason": "seasickness",  "probability_per_day": 0.0042},
                {"reason": "fatigue",      "probability_per_day": 0.0030},
                {"reason": "minor_injury", "probability_per_day": 0.0020},
            ]
        else:
            self.noise_categories = list(noise_categories)

    @staticmethod
    def effective_sick_call_probability(
        base_probability: float,
        severity_belief: float = 0.5,
        trust_medical: float = 0.75,
    ) -> float:
        """Scale base sick-call rate by agent beliefs (Layer 1)."""
        sev = max(0.1, min(1.0, float(severity_belief)))
        trust = max(0.0, min(1.0, float(trust_medical)))
        return base_probability * sev * (0.5 + 0.5 * trust)

    def _process_symptomatic_agent(
        self,
        aid: int,
        epoch: int,
        overrides: dict[int, str],
        beliefs: dict[int, dict[str, float]],
        chronic_mods: dict[int, dict[str, float]],
        severity_hazards: dict[int, float],
        sick_call_ids: list[int],
        true_positive_ids: list[int],
    ) -> None:
        if aid not in self._symptom_onset_epoch:
            self._symptom_onset_epoch[aid] = int(epoch)
        override = overrides.get(aid, "")
        if override == "hide_symptoms":
            return
        if override == "report_sick_call":
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)
            return
        onset = self._symptom_onset_epoch[aid]
        if (int(epoch) - onset) < self.detection_delay_epochs:
            return
        if self.sick_call_probability <= 0.0:
            return
        inf = beliefs.get(aid, {})
        if self.sick_call_severity_mode == "information_belief":
            prob = self.effective_sick_call_probability(
                self.sick_call_probability,
                severity_belief=inf.get("severity_belief", 0.5),
                trust_medical=inf.get("trust_medical", 0.75),
            )
        else:
            prob = severity_hazards.get(aid, self.sick_call_probability)
            trust = max(0.0, min(1.0, float(inf.get("trust_medical", 0.75))))
            prob *= 0.5 + 0.5 * trust
        agent_chronic = chronic_mods.get(aid, {})
        prob = min(1.0, prob + agent_chronic.get(
            "sick_call_probability_boost", 0.0,
        ))
        prob = self.clock.probability_per_epoch(prob)
        if self.rng.random() < prob:
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)

    def _apply_crew_screening(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
        sick_call_ids: list[int],
        crew_screening_ids: list[int],
    ) -> None:
        interval = self.crew_screening_interval_epochs
        if interval is None or interval <= 0:
            return
        if int(epoch) % interval != 0:
            return
        from telemetry_buffer.agent_axes import agent_is_isolated

        already = set(sick_call_ids)
        for agent in agents:
            aid = int(agent["agent_id"])
            if aid in already:
                continue
            if agent_is_isolated(agent):
                continue
            if not _agent_is_crew(agent):
                continue
            sick_call_ids.append(aid)
            crew_screening_ids.append(aid)
            already.add(aid)

    def query_ground_truth(
        self,
        json_data: dict[str, Any],
        behavioral_overrides: dict[int, str] | None = None,
        information_beliefs: dict[int, dict[str, float]] | None = None,
        chronic_behavioral_mods: dict[int, dict[str, float]] | None = None,
        include_episode_telemetry: bool = False,
        *,
        outbreak_recognized: bool = False,
    ) -> dict[str, Any]:
        """Parse ground-truth agent states and return sick-call roster.

        Returns:
        - ``sick_call_agents``: IDs that reported to sick-call this epoch.
        - ``true_positive_ids``: subset that are genuinely symptomatic.
        - ``noise_ids``: subset that are healthy but reported (background).
        - ``noise_reasons``: complaint reasons for noise reporters.
        - ``crew_screening_ids``: crew added via proactive screening.
        - ``total_agents``: total agent count.
        """
        agents = json_data.get("agents", [])
        epoch = json_data.get("epoch", 0)

        sick_call_ids: list[int] = []
        true_positive_ids: list[int] = []
        noise_ids: list[int] = []
        noise_reasons: list[dict[str, Any]] = []
        crew_screening_ids: list[int] = []

        from telemetry_buffer.agent_axes import (
            COMPLIANCE_NON_COMPLIANT,
            agent_has_symptomatic_presentation,
            agent_is_isolated,
            resolve_agent_axes,
        )

        overrides = behavioral_overrides or {}
        beliefs = information_beliefs or {}
        chronic_mods = chronic_behavioral_mods or {}
        severity_hazards: dict[int, float] = {}

        for agent in agents:
            aid = agent["agent_id"]
            is_isolated = agent_is_isolated(agent)
            _, _, compliance = resolve_agent_axes(agent)
            presenting = agent_has_symptomatic_presentation(agent)
            if presenting and aid not in self._presentation_onset_epoch:
                self._presentation_onset_epoch[aid] = int(epoch)
            is_symptomatic = presenting or compliance == COMPLIANCE_NON_COMPLIANT

            if is_isolated:
                continue

            if is_symptomatic:
                severity_hazards[aid] = self._severity_hazard(
                    agent, outbreak_recognized=outbreak_recognized,
                )
                self._process_symptomatic_agent(
                    aid, epoch, overrides, beliefs, chronic_mods,
                    severity_hazards,
                    sick_call_ids, true_positive_ids,
                )
            else:
                reported, reason = self._check_background_noise(aid)
                if reported:
                    sick_call_ids.append(aid)
                    noise_ids.append(aid)
                    noise_reasons.append({"agent_id": aid, "reason": reason})

        self._apply_crew_screening(
            agents, epoch, sick_call_ids, crew_screening_ids,
        )
        detection_events = []
        agents_by_id = {int(agent["agent_id"]): agent for agent in agents}
        for aid in dict.fromkeys(sick_call_ids):
            if aid in self._first_sick_call_epoch:
                continue
            self._first_sick_call_epoch[aid] = int(epoch)
            agent = agents_by_id.get(int(aid), {})
            infection = _symptomatic_infection(agent)
            detection_events.append({
                "agent_id": int(aid),
                "symptom_onset_epoch": self._symptom_onset_epoch.get(aid),
                "first_sick_call_epoch": int(epoch),
                "symptom_severity": infection.get("symptom_severity", ""),
            })
        episode_telemetry = []
        if include_episode_telemetry:
            for agent in agents:
                aid = int(agent["agent_id"])
                if aid not in self._symptom_onset_epoch:
                    continue
                infection = _symptomatic_infection(agent)
                episode_telemetry.append({
                    "agent_id": aid,
                    "symptom_onset_epoch": self._symptom_onset_epoch[aid],
                    "first_sick_call_epoch": self._first_sick_call_epoch.get(aid),
                    "symptom_severity": infection.get("symptom_severity", ""),
                })

        molecular = self.collect_specimens(
            agents, epoch, sick_call_ids,
        )
        onset_observations = self._record_onset_observations(agents, epoch)

        return {
            "modality": self.name,
            "epoch": epoch,
            "sick_call_agents": sick_call_ids,
            "true_positive_ids": true_positive_ids,
            "noise_ids": noise_ids,
            "noise_reasons": noise_reasons,
            "crew_screening_ids": crew_screening_ids,
            "sick_call_count": len(sick_call_ids),
            "total_agents": len(agents),
            "first_detection_events": detection_events,
            "episode_detection_telemetry": episode_telemetry,
            **molecular,
            "onset_observations": onset_observations,
            "onset_observation_count": len(onset_observations),
        }

    # ── molecular ascertainment rung ──────────────────────────────────────
    #
    # Kept apart from the sick-call roster above because the two are
    # different observables: Ward 2010 counted 176/1,970 NAT-confirmed
    # passengers on the same voyage that sent 13/1,970 to the infirmary.
    # Collapsing them would make one anchor unreachable whenever the other
    # is matched.

    def collect_specimens(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
        sick_call_ids: list[int],
    ) -> dict[str, Any]:
        """Draw specimens and assay results for this epoch.

        Presentation to sick call makes an agent eligible for a specimen;
        ``active_screening`` additionally reaches symptomatic agents who
        never presented, which is how case-finding campaigns differ from
        passive infirmary records.
        """
        presenting = {int(aid) for aid in sick_call_ids}
        sampled: dict[str, list[int]] = {}
        confirmed: dict[str, list[int]] = {}
        campaign_rosters: dict[str, list[int]] = {}
        campaign_confirmed: dict[str, list[int]] = {}
        for pathogen_id, model in self._molecular_models().items():
            roster = self._campaign_roster(agents, epoch, pathogen_id)
            drawn, positive = self._sample_pathogen(
                agents, epoch, presenting, pathogen_id, model,
                forced=set(roster),
            )
            if drawn:
                sampled[pathogen_id] = drawn
            if positive:
                confirmed[pathogen_id] = positive
            if roster:
                on_roster = set(roster)
                campaign_rosters[pathogen_id] = roster
                campaign_confirmed[pathogen_id] = [
                    aid for aid in positive if aid in on_roster
                ]
        sampled_union = sorted({aid for ids in sampled.values() for aid in ids})
        confirmed_union = sorted(
            {aid for ids in confirmed.values() for aid in ids},
        )
        return {
            "lab_sampled_agents": sampled_union,
            "lab_confirmed_agents": confirmed_union,
            "lab_sampled_by_pathogen": sampled,
            "lab_confirmed_by_pathogen": confirmed,
            "lab_sampled_count": len(sampled_union),
            "lab_confirmed_count": len(confirmed_union),
            "campaign_specimens_by_pathogen": campaign_rosters,
            "campaign_confirmed_by_pathogen": campaign_confirmed,
        }

    def _sample_pathogen(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
        presenting: set[int],
        pathogen_id: str,
        model: dict[str, Any],
        *,
        forced: set[int] | None = None,
    ) -> tuple[list[int], list[int]]:
        drawn: list[int] = []
        positive: list[int] = []
        scheduled = forced or set()
        for agent in agents:
            aid = int(agent["agent_id"])
            if (pathogen_id, aid) in self._lab_sampled:
                continue
            infection = (agent.get("pathogen_infections") or {}).get(
                pathogen_id, {},
            ) or {}
            probability = self._specimen_probability(
                model, infection, presented=aid in presenting,
                scheduled=aid in scheduled,
            )
            if probability <= 0.0 or self._molecular_rng.random() >= probability:
                continue
            self._lab_sampled[(pathogen_id, aid)] = int(epoch)
            drawn.append(aid)
            if self._assay_positive(model, infection):
                self._lab_confirmed[(pathogen_id, aid)] = int(epoch)
                positive.append(aid)
        return drawn, positive

    def _specimen_probability(
        self,
        model: dict[str, Any],
        infection: dict[str, Any],
        *,
        presented: bool,
        scheduled: bool = False,
    ) -> float:
        """Per-epoch probability that this agent yields a specimen.

        A host on a campaign roster is swabbed with certainty: the record
        says the specimen was taken, and whether it comes back positive is
        the assay's draw, not this one.
        """
        if scheduled:
            return 1.0
        severity = str(infection.get("symptom_severity") or "")
        symptomatic = infection.get("illness") == "SYMPTOMATIC"
        index = self._severity_index(model, severity) if symptomatic else None
        if presented:
            # A complaint that is not this pathogen still reaches the
            # clinician, and swabbing it is what makes test positivity an
            # emergent quantity rather than one by construction.
            reference = index if index is not None else model["mild_index"]
            return float(model["sampling"][reference])
        if not symptomatic or index is None:
            return 0.0
        return self.clock.probability_per_epoch(
            float(model["screening_probability_per_day"]),
        )

    def _assay_positive(
        self,
        model: dict[str, Any],
        infection: dict[str, Any],
    ) -> bool:
        if infection.get("status") != "INFECTED":
            return False
        sensitivity = self._assay_sensitivity(model, infection)
        return bool(self._molecular_rng.random() < sensitivity)

    def _assay_sensitivity(
        self,
        model: dict[str, Any],
        infection: dict[str, Any],
    ) -> float:
        """Detectability of this host's specimen on the day it is taken.

        A profile declaring ``assay_sensitivity_by_time_since_infection``
        reads the day of infection the host is on, with the curve's last entry
        held, so an early swab and a late one are different observations of
        the same infection. Detectability is its own clock: a host past the
        culture-positive window still tests positive at the curve's tail.
        """
        curve = model["sensitivity_by_day"]
        if not curve:
            return float(model["sensitivity"])
        # ``time_infected`` counts epochs, so the clock is where the two
        # units meet, as ``days_post_infection`` reads it elsewhere.
        day = self.clock.day_index(int(infection.get("time_infected") or 0))
        return float(curve[min(max(day, 0), len(curve) - 1)])

    @staticmethod
    def _severity_index(
        model: dict[str, Any],
        severity: str,
    ) -> int | None:
        states = model["states"]
        return states.index(severity) if severity in states else None

    def _molecular_models(self) -> dict[str, dict[str, Any]]:
        """Molecular parameters for every profile that declares them."""
        models: dict[str, dict[str, Any]] = {}
        for pathogen_id, profile in self.symptom_severity_profiles.items():
            model = self._molecular_model(profile)
            if model is not None:
                models[str(pathogen_id)] = model
        return models

    @staticmethod
    def _molecular_model(profile: dict[str, Any]) -> dict[str, Any] | None:
        """Extract specimen and assay terms, or None when undeclared."""
        severity = profile.get("severity_model")
        observation = profile.get("observation_model")
        if not isinstance(severity, dict) or not isinstance(observation, dict):
            return None
        sampling = list(
            observation.get("lab_sampling_probability_by_severity") or [],
        )
        states = list(severity.get("states") or [])
        if len(sampling) != len(states) or not sampling:
            return None
        screening = observation.get("active_screening") or {}
        enabled = bool(screening.get("enabled"))
        return {
            "states": states,
            "sampling": [float(value) for value in sampling],
            "mild_index": states.index("mild") if "mild" in states else 0,
            "screening_probability_per_day": (
                float(screening.get("selection_probability_per_day") or 0.0)
                if enabled
                else 0.0
            ),
            "sensitivity": float(observation.get("assay_sensitivity") or 1.0),
            "sensitivity_by_day": [
                float(value) for value in (
                    observation.get("assay_sensitivity_by_time_since_infection")
                    or []
                )
            ],
        }

    # ── replicated testing campaigns ──────────────────────────────────────

    def _index_campaigns(
        self,
        campaigns: Iterable[TestingCampaign] | None,
    ) -> dict[str, TestingCampaign]:
        """Key campaigns by pathogen, refusing two for one pathogen.

        A campaign needs a molecular model to hand its specimens to, so a
        campaign for a pathogen whose profile declares no specimen sampling
        is a configuration error rather than a silent no-op.
        """
        indexed: dict[str, TestingCampaign] = {}
        models = self._molecular_models()
        for campaign in campaigns or ():
            pathogen_id = campaign.pathogen_id
            if pathogen_id in indexed:
                raise ValueError(
                    f"two testing campaigns declared for {pathogen_id}: "
                    f"{indexed[pathogen_id].campaign_id} and "
                    f"{campaign.campaign_id}",
                )
            if pathogen_id not in models:
                raise ValueError(
                    f"testing campaign {campaign.campaign_id} targets "
                    f"{pathogen_id}, whose profile declares no "
                    "observation_model.lab_sampling_probability_by_severity",
                )
            indexed[pathogen_id] = campaign
        return indexed

    def _campaign_roster(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
        pathogen_id: str,
    ) -> list[int]:
        """Hosts the pathogen's campaign swabs this epoch.

        A campaign day is spent on the first epoch of that simulated day and
        never again: the record gives a count per day, and a test event is a
        concentrated one, not a rate spread over the hours.
        """
        campaign = self._campaigns.get(pathogen_id)
        if campaign is None:
            return []
        day_index = self.clock.day_index(int(epoch))
        key = (pathogen_id, day_index)
        if key in self._campaign_days_run:
            return []
        self._campaign_days_run.add(key)
        confirmed = {
            aid for (pid, aid) in self._lab_confirmed if pid == pathogen_id
        }
        sampled = {
            aid for (pid, aid) in self._lab_sampled if pid == pathogen_id
        }
        return campaign.specimen_roster(
            agents, day_index,
            confirmed_ids=confirmed,
            already_sampled=sampled,
            rng=self._campaign_rng,
        )

    def campaign_for(self, pathogen_id: str) -> TestingCampaign | None:
        return self._campaigns.get(str(pathogen_id))

    # ── symptom-onset channel ─────────────────────────────────────────────
    #
    # The Diamond Princess onset curve (NIID field briefing, 19 Feb 2020) is
    # onset dates among confirmed cases with a recorded onset: 197 of 619
    # cases by 20 Feb. It is a different observable from the sick-call
    # roster - a host swabbed on a campaign day and confirmed positive has
    # an onset date whether or not it ever reported to the infirmary - and
    # from the truth channel, which knows every onset including the ones no
    # record ever held. A host enters this channel only once it is
    # laboratory-confirmed and presenting a syndrome-eligible severity;
    # the day recorded is the day it first presented.

    def _record_onset_observations(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
    ) -> list[dict[str, Any]]:
        recorded: list[dict[str, Any]] = []
        for agent in agents:
            aid = int(agent["agent_id"])
            onset_epoch = self._presentation_onset_epoch.get(aid)
            if onset_epoch is None:
                continue
            for pathogen_id, infection in (
                agent.get("pathogen_infections") or {}
            ).items():
                record = self._onset_observation(
                    agent, aid, str(pathogen_id), infection or {},
                    onset_epoch, int(epoch),
                )
                if record is not None:
                    recorded.append(record)
        return recorded

    def _onset_observation(
        self,
        agent: dict[str, Any],
        aid: int,
        pathogen_id: str,
        infection: dict[str, Any],
        onset_epoch: int,
        epoch: int,
    ) -> dict[str, Any] | None:
        key = (pathogen_id, aid)
        if key in self._onset_observations or key not in self._lab_confirmed:
            return None
        if infection.get("illness") != "SYMPTOMATIC":
            return None
        severity = str(infection.get("symptom_severity") or "")
        if not self._onset_eligible(pathogen_id, severity):
            return None
        record = {
            "agent_id": aid,
            "pathogen_id": pathogen_id,
            "onset_epoch": int(onset_epoch),
            "onset_day": self.clock.day_index(int(onset_epoch)),
            "recorded_epoch": int(epoch),
            "confirmed_epoch": int(self._lab_confirmed[key]),
            "symptom_severity": severity,
            "role": "crew" if _agent_is_crew(agent) else "passenger",
        }
        self._onset_observations[key] = record
        return record

    def _onset_eligible(self, pathogen_id: str, severity: str) -> bool:
        """Whether this severity presents a syndrome the record can date.

        Read from the profile's ``syndrome_case_eligibility_by_severity``;
        a profile without one treats every symptomatic host as datable.
        """
        model = self._severity_model(pathogen_id)
        if model is None or not model["eligibility"]:
            return True
        if severity not in model["states"]:
            return False
        return float(model["eligibility"][model["states"].index(severity)]) > 0.0

    def onset_observation_curve(
        self,
        pathogen_id: str,
    ) -> dict[int, dict[str, int]]:
        """Recorded onsets by onset day, split passenger/crew."""
        curve: dict[int, dict[str, int]] = {}
        for (pid, _aid), record in self._onset_observations.items():
            if pid != str(pathogen_id):
                continue
            day = curve.setdefault(
                int(record["onset_day"]), {"passenger": 0, "crew": 0},
            )
            day[record["role"]] += 1
        return dict(sorted(curve.items()))

    def _severity_hazard(
        self,
        agent: dict[str, Any],
        *,
        outbreak_recognized: bool = False,
    ) -> float:
        """Resolve per-day hazard; missing profiles use the unattenuated base."""
        infection = _symptomatic_infection(agent)
        if not infection:
            return self.sick_call_probability
        severity = str(infection.get("symptom_severity") or "")
        if severity == "asymptomatic":
            return 0.0
        pathogen_id = self._infection_pathogen_id(agent, infection)
        profile = self.symptom_severity_profiles.get(pathogen_id, {})
        if "severity_model" not in profile:
            return self.sick_call_probability
        return self._five_state_hazard(
            pathogen_id,
            severity,
            outbreak_recognized,
        )

    @staticmethod
    def _infection_pathogen_id(
        agent: dict[str, Any],
        infection: dict[str, Any],
    ) -> str:
        pathogen_id = str(infection.get("pathogen_id") or "")
        if pathogen_id:
            return pathogen_id
        for candidate_id, candidate in (
            agent.get("pathogen_infections") or {}
        ).items():
            if candidate is infection:
                return str(candidate_id)
        return ""

    def _five_state_hazard(
        self,
        pathogen_id: str,
        severity: str,
        outbreak_recognized: bool,
    ) -> float:
        model = self._severity_model(pathogen_id)
        if model is None:
            raise ValueError(
                f"{pathogen_id} severity_model requires observation_model",
            )
        if severity not in model["states"]:
            raise ValueError(
                f"{pathogen_id} has unrecognised symptom severity "
                f"state {severity!r}",
            )
        index = model["states"].index(severity)
        eligibility = model["eligibility"][index]
        reporting = model["reporting_post" if outbreak_recognized else "reporting_pre"]
        episode_probability = eligibility * reporting[index]
        window = model["window_days"]
        hazard = 1.0 - (1.0 - episode_probability) ** (1.0 / window)
        return hazard

    def _severity_model(self, pathogen_id: str) -> dict[str, Any] | None:
        """Return normalized five-state observation vectors for a pathogen."""
        profile = self.symptom_severity_profiles.get(pathogen_id, {})
        severity = profile.get("severity_model")
        observation = profile.get("observation_model")
        if not isinstance(severity, dict) or not isinstance(observation, dict):
            return None
        return {
            "states": list(severity.get("states", [])),
            "eligibility": list(
                observation.get("syndrome_case_eligibility_by_severity", []),
            ),
            "reporting_pre": list(
                observation.get("reporting_probability_by_severity_pre_recognition", []),
            ),
            "reporting_post": list(
                observation.get("reporting_probability_by_severity_post_recognition", []),
            ),
            "window_days": float(
                observation.get("episode_reporting_window_days", 1.0),
            ),
        }

    def _check_background_noise(self, _aid: int) -> tuple[bool, str | None]:
        """FRED-style categorized background noise check.

        ``background_noise_rate <= 0`` disables all background sick-call noise.
        Otherwise each noise category has its own independent probability
        (ref: FRED ``Household.vaccination_probability`` pattern).
        """
        if self.background_noise_rate <= 0.0:
            return False, None
        for cat in self.noise_categories:
            probability = self.clock.probability_per_epoch(float(
                cat.get("probability_per_day", cat.get("probability", 0.0)),
            ))
            if self.rng.random() < probability:
                return True, cat["reason"]
        return False, None

    def _resolve_base_compliance(
        self,
        agent_class: str | None,
        chronic_compliance_boost: float,
    ) -> float:
        """Population (or class-specific) compliance fraction, chronic-boosted."""
        base = self.quarantine_compliance
        if agent_class and self.compliance_by_class:
            a_class = str(agent_class)
            if a_class in self.compliance_by_class:
                base = float(self.compliance_by_class[a_class])
            else:
                # role_group keys: "crew" / "passenger" match class_id prefixes
                for key, val in self.compliance_by_class.items():
                    if a_class.startswith(f"{key}_") or a_class == key:
                        base = float(val)
                        break
                else:
                    # passenger_young → non-elderly passenger classes
                    if "passenger_young" in self.compliance_by_class and (
                        a_class.startswith("passenger_")
                        and a_class != "passenger_elderly"
                    ):
                        base = float(self.compliance_by_class["passenger_young"])
        return min(1.0, max(0.0, base + chronic_compliance_boost))

    def assign_compliance_class(
        self,
        agent_id: int,
        *,
        agent_class: str | None = None,
        chronic_compliance_boost: float = 0.0,
        behavioral_override: str | None = None,
    ) -> str:
        """Assign sticky compliance class at first quarantine order (idempotent)."""
        if agent_id in self._compliance_class:
            return self._compliance_class[agent_id]

        if behavioral_override == "refuse_quarantine":
            cls = "defiant"
        else:
            effective = self._resolve_base_compliance(
                agent_class, chronic_compliance_boost,
            )
            draw = float(self.rng.random())
            if draw < effective:
                cls = "compliant"
            elif draw < effective + (1.0 - effective) * self.reluctant_fraction:
                cls = "reluctant"
            else:
                cls = "defiant"
        self._compliance_class[agent_id] = cls
        return cls

    def check_quarantine_compliance(
        self,
        agent_id: int,
        epochs_since_order: int,
        behavioral_override: str | None = None,
        chronic_compliance_boost: float = 0.0,
        agent_class: str | None = None,
        is_symptomatic: bool = False,
    ) -> bool:
        """Bimodal quarantine compliance (compliant / reluctant / defiant).

        Compliance class is drawn once per agent at first order and sticky.
        - compliant: follows immediately
        - reluctant: complies after ``reluctant_delay_hours`` or if symptomatic
        - defiant: never complies (unless override cleared)

        The legacy ``compliance_delay_hours`` forced-compliance path is removed.
        """
        if behavioral_override == "refuse_quarantine":
            self._compliance_class[agent_id] = "defiant"
            return False

        cls = self.assign_compliance_class(
            agent_id,
            agent_class=agent_class,
            chronic_compliance_boost=chronic_compliance_boost,
            behavioral_override=behavioral_override,
        )
        if cls == "compliant":
            return True
        if cls == "defiant":
            return False
        # reluctant
        if is_symptomatic:
            return True
        return epochs_since_order >= self.reluctant_delay_epochs
