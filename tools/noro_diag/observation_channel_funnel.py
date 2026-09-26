#!/usr/bin/env python3
"""Observation-channel funnel for one declared-pathogen voyage, for ledger
NORO-CHANNEL-01.

Purpose
-------
The norwalk_gi profile ships a declared observation channel
(``observation_model`` in ``data/pathogens/norwalk_only.json``, Grade C,
origin ``docs/norovirus/cruise_pathogen_severity_observation_priors_v2.md``,
explicitly not identified). Whether that channel reproduces the reporting
fractions it was elicited toward is a measured question, not an elicitation
one: this tool runs one unmodified voyage and reads off the funnel every
infected host passes through on the way to the ship's record:

    infected -> symptomatic course -> syndrome-eligible severity
      -> reported to the infirmary (pre/post outbreak recognition)
      -> lab-sampled -> lab-confirmed -> onset dated

each rung split passenger vs crew, plus two fidelity reads the COVID channel
audit (``tools/covid_route_attribution.py``) established: onset-dating
fidelity (the epoch the record carries against the epoch the infection
record says symptoms began) and a decomposition of the confirmed-but-undated
tail.

Method
------
Read-only instrumentation only: the run spec is the shipped spec
(``build_spec`` from ``tools.noro_diag.per_host_dose_challenge`` with no
overrides, i.e. the pooled default arm), and observation is a
``ShipSimulation.epoch_observer`` that reads the same per-epoch snapshot the
channel itself was fed (``work.agents``, ``work.syn_result``,
``work.state.trigger_status``) plus the modality's own post-run ledgers
(``_first_sick_call_epoch``, ``_lab_sampled``, ``_lab_confirmed``,
``_onset_observations``). Nothing draws from the engine's RNG; the funnel
changes nothing the run would have done.

Channel mechanics the funnel reads (``crusher_labs/modalities/syndromic.py``):

* A presenting (syndromic-symptomatic, non-isolated) host rolls a per-day
  hazard ``1 - (1 - eligibility[s] * reporting_pre|post[s]) **
  (1/window_days)``, scaled by ``0.5 + 0.5 * trust_medical`` (default 0.75),
  then converted per epoch; ``reporting_post`` replaces ``reporting_pre``
  once trigger status reached SUSPECTED at the end of the prior epoch.
* A sick-call presenter yields at most one specimen per pathogen
  (``lab_sampling_probability_by_severity`` at its severity index;
  ``active_screening`` is off for norwalk_gi); ``assay_sensitivity`` is
  undeclared so sampled-and-still-infected means confirmed.
* A confirmed host gets an ``onset_observation`` at the first epoch its
  infection snapshot reads ``SYMPTOMATIC`` and its severity is
  onset-eligible; the recorded ``onset_epoch`` is ``epoch -
  epochs_since_symptom_onset`` — the stamped arithmetic, exact for onboard
  and pre-boarding onsets alike. Dating loss is therefore structural: a
  confirmed host that never presents a symptomatic snapshot afterwards is
  never dated.

Inputs
------
``--platform`` (default ``spirit_cruise_3000``, the frozen
NORO-COINCIDENCE-CELL-01 cell), ``--bundle norwalk_only``,
``--pathogen-id norwalk_gi``, ``--epochs 168``, ``--seeds``, ``--out`` —
one gzipped JSON per seed plus a pooled ``*_readout.json``.

Outputs
-------
Per seed: the rung counts above with passenger/crew and per-severity splits,
the pre/post-recognition reporting split, the not-reported decomposition
(never visible while symptomatic vs hazard never fired), onset-dating
fidelity, the confirmed-undated decomposition, the declared per-severity
hazard table, the trust modifier actually applied, and the shared
``ascertainment_funnel`` rungs for cross-check. The readout pools per-seed
rung ratios (median + IQR) for the ledger.

Runtime
-------
About 6 min per seed at 3,000 agents x 168 epochs on one core.

Nothing here fits or selects a parameter value; the funnel reads the
channel as declared.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.voyage_itinerary import agent_is_departed  # noqa: E402
from orchestrator_types import STATUS_RANK, STATUS_SUSPECTED  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import (  # noqa: E402
    ShipSimulation,
    _beliefs_from_information,
)
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402
from telemetry_buffer.agent_axes import (  # noqa: E402
    agent_is_isolated,
)
from tools.covid_route_attribution import ascertainment_funnel  # noqa: E402
from tools.noro_diag import per_host_dose_challenge as _pdc  # noqa: E402
from tools.noro_diag.dose_response import load_dose_response  # noqa: E402

ILLNESS_SYMPTOMATIC = "SYMPTOMATIC"
ROLES = ("passenger", "crew", "other")


@dataclass
class HostExposure:
    """Epochs one infected host spent symptomatic, by channel visibility."""

    visible: int = 0
    isolated: int = 0
    departed: int = 0
    first_symptomatic_epoch: int | None = None
    onset_epoch_witness: int | None = None
    trust_medical_seen: set[float] = field(default_factory=set)


class ChannelCapture:
    """Per-epoch capture the observer collects; reads only, draws nothing.

    ``status_by_epoch[e]`` is the trigger status at the end of epoch ``e``,
    which is the flag surveillance consults at epoch ``e + 1`` (surveillance
    runs before escalation within an epoch by design).
    """

    def __init__(self, pathogen_id: str) -> None:
        self.pathogen_id = pathogen_id
        self.status_by_epoch: dict[int, str] = {}
        self.first_report_epoch: dict[int, int] = {}
        self.reported_symptomatic_ids: set[int] = set()
        self.sick_call_count = 0
        self.noise_report_count = 0
        self.exposure: dict[int, HostExposure] = {}
        self.beliefs_nonempty_epochs = 0

    def observe(self, _sim: Any, work: Any) -> None:
        epoch = int(work.epoch)
        self.status_by_epoch[epoch] = str(work.state.trigger_status)
        syn = work.syn_result or {}
        self.sick_call_count += len(syn.get("sick_call_agents") or [])
        self.noise_report_count += len(syn.get("noise_ids") or [])
        for aid in syn.get("true_positive_ids") or []:
            aid = int(aid)
            self.reported_symptomatic_ids.add(aid)
            self.first_report_epoch.setdefault(aid, epoch)
        beliefs = _beliefs_from_information(work.information_state or {})
        if beliefs:
            self.beliefs_nonempty_epochs += 1
        for agent in work.agents or []:
            self._exposure(agent, epoch, beliefs)

    def _exposure(
        self,
        agent: dict[str, Any],
        epoch: int,
        beliefs: dict[int, dict[str, float]],
    ) -> None:
        infection = (agent.get("pathogen_infections") or {}).get(
            self.pathogen_id,
        )
        if infection is None:
            return
        aid = int(agent["agent_id"])
        if str(infection.get("illness")) != ILLNESS_SYMPTOMATIC:
            return
        exp = self.exposure.setdefault(aid, HostExposure())
        if exp.first_symptomatic_epoch is None:
            exp.first_symptomatic_epoch = epoch
            since = infection.get("epochs_since_symptom_onset")
            if since is not None:
                exp.onset_epoch_witness = epoch - int(since)
        belief = beliefs.get(aid)
        if belief is not None:
            exp.trust_medical_seen.add(
                round(float(belief.get("trust_medical", 0.75)), 4),
            )
        if agent_is_departed(agent):
            exp.departed += 1
        elif agent_is_isolated(agent):
            exp.isolated += 1
        else:
            exp.visible += 1

    def recognized_at_report(self, report_epoch: int) -> bool:
        """The reporting vector the host's first call fell under."""
        status = self.status_by_epoch.get(int(report_epoch) - 1)
        return STATUS_RANK.get(str(status), 0) >= STATUS_RANK[STATUS_SUSPECTED]


def _enum_name(value: Any) -> str:
    return str(getattr(value, "name", value) or "")


def _role_group(role: Any) -> str:
    text = str(role or "").lower()
    if "crew" in text:
        return "crew"
    if text == "passenger" or "passenger" in text:
        return "passenger"
    return "other"


def _true_onset_epoch(inf: dict[str, Any]) -> int | None:
    onset_offset = inf.get("onset_time_infected")
    if inf.get("boarding_state") is not None:
        # Boarding import: time_infected counts from a pre-voyage start,
        # so onset sits onset_offset - age_at_boarding into the voyage;
        # age_at_boarding is stamped nowhere else, so the observer's
        # witness (epoch - epochs_since_symptom_onset) is the read.
        return None
    if onset_offset is None:
        return None
    return int(inf.get("infection_epoch") or 0) + int(onset_offset)


def _infection_record(agent: Any, inf: dict[str, Any]) -> dict[str, Any]:
    onset_offset = inf.get("onset_time_infected")
    axes = inf.get("symptom_axes") or {}
    boarding_state = inf.get("boarding_state")
    return {
        "agent_id": int(agent.agent_id),
        "role": _role_group(getattr(agent, "role", None)),
        "infection_epoch": int(inf.get("infection_epoch") or 0),
        "imported": boarding_state is not None,
        "presented": onset_offset is not None,
        "onset_offset": (
            int(onset_offset) if onset_offset is not None else None
        ),
        "true_onset_epoch": _true_onset_epoch(inf),
        "severity_peak": str(
            inf.get("symptom_severity_peak")
            or inf.get("symptom_severity")
            or "none",
        ),
        "severity_end": str(inf.get("symptom_severity") or "none"),
        "vomiting": bool(axes.get("vomiting")),
        "diarrhoea": bool(axes.get("diarrhoea")),
        "axes_drawn": bool(axes),
        "illness_end": _enum_name(inf.get("illness")),
        "status_end": _enum_name(inf.get("status")),
    }


def harvest_infections(
    sim: Any,
    pathogen_id: str,
) -> list[dict[str, Any]]:
    """One plain record per host carrying ``pathogen_id`` at run end."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", set()) or ())
    records = []
    for agent in sim.engine.agents:
        inf = agent.infections.get(pathogen_id)
        if inf is None or agent.agent_id in seeded:
            continue
        records.append(_infection_record(agent, inf))
    return records


def illness_class(record: dict[str, Any]) -> str:
    if not record["axes_drawn"]:
        return "undrawn"
    vomiting = record["vomiting"]
    diarrhoea = record["diarrhoea"]
    if vomiting and diarrhoea:
        return "vomiting_and_diarrhoea"
    if vomiting:
        return "vomiting_only"
    if diarrhoea:
        return "diarrhoea_only"
    return "neither_axis"


def _split(records: list[dict[str, Any]], ids: set[int]) -> dict[str, int]:
    """Count records in ``ids`` total and per role group."""
    out = {"total": 0, **dict.fromkeys(ROLES, 0)}
    for record in records:
        if record["agent_id"] not in ids:
            continue
        out["total"] += 1
        out[record["role"]] += 1
    return out


def _severity_split(
    records: list[dict[str, Any]],
    ids: set[int],
) -> dict[str, int]:
    tally: Counter = Counter()
    for record in records:
        if record["agent_id"] in ids:
            tally[record["severity_peak"]] += 1
    return dict(tally)


def declared_channel_table(profile: dict[str, Any]) -> dict[str, Any]:
    """The channel's declared per-severity mechanics, restated per severity.

    The episode probability ``eligibility * reporting`` is what the vector
    declares; the per-day hazard the engine rolls is
    ``1 - (1 - p) ** (1/window_days)``. The declared vectors are realized
    capture — net of reluctance — so the host-level draw no longer carries
    the Layer-1 ``0.5 + 0.5 * trust_medical`` multiplier unless a profile
    declares ``observation_model.reporting_belief_scaling="trust_medical"``
    (ledger NORO-CHANNEL-02). Neither is a parameter of this tool.
    """
    observation = profile.get("observation_model") or {}
    states = list((profile.get("severity_model") or {}).get("states") or [])
    window = float(observation.get("episode_reporting_window_days") or 1.0)
    rows = _declared_severity_rows(observation, states)
    _annotate_episode_hazards(rows, window)
    return {
        "episode_reporting_window_days": window,
        "per_severity": rows,
        "active_scenario": (
            (observation.get("prior") or {}).get("active_scenario")
        ),
    }


def _declared_severity_rows(
    observation: dict[str, Any],
    states: list[str],
) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    for name, vector in (
        ("eligibility", observation.get(
            "syndrome_case_eligibility_by_severity") or []),
        ("reporting_pre", observation.get(
            "reporting_probability_by_severity_pre_recognition") or []),
        ("reporting_post", observation.get(
            "reporting_probability_by_severity_post_recognition") or []),
        ("lab_sampling", observation.get(
            "lab_sampling_probability_by_severity") or []),
    ):
        for index, value in enumerate(vector):
            if index >= len(states):
                continue
            rows.setdefault(states[index], {})[name] = float(value)
    return rows


def _annotate_episode_hazards(
    rows: dict[str, dict[str, float]],
    window: float,
) -> None:
    for row in rows.values():
        for arm in ("pre", "post"):
            episode = float(row.get("eligibility", 0.0)) * float(
                row.get(f"reporting_{arm}", 0.0),
            )
            row[f"episode_p_{arm}"] = episode
            row[f"per_day_hazard_{arm}"] = (
                1.0 - (1.0 - episode) ** (1.0 / window) if episode else 0.0
            )


def _recognition_summary(capture: ChannelCapture) -> dict[str, Any]:
    first = None
    for epoch in sorted(capture.status_by_epoch):
        status = capture.status_by_epoch[epoch]
        if STATUS_RANK.get(status, 0) >= STATUS_RANK[STATUS_SUSPECTED]:
            first = epoch
            break
    return {
        "first_epoch_at_suspected_or_above": first,
        "final_status": capture.status_by_epoch.get(
            max(capture.status_by_epoch, default=0),
        ),
        "status_hist": dict(Counter(capture.status_by_epoch.values())),
    }


def _non_report_reasons(
    symptomatic: list[dict[str, Any]],
    reported: set[int],
    capture: ChannelCapture,
) -> dict[str, int]:
    """Why an eligible symptomatic host never reached the infirmary record.

    ``course_not_symptomatic_onboard`` covers convalescent imports and other
    hosts whose illness course never read SYMPTOMATIC in a voyage snapshot --
    the channel never had a draw to lose. ``isolated_whole_course`` and the
    two ``*_draw_missed`` buckets are in-voyage ascertainment.
    """
    reasons: Counter = Counter()
    for record in symptomatic:
        aid = record["agent_id"]
        if aid in reported:
            continue
        exp = capture.exposure.get(aid)
        if exp is None or exp.first_symptomatic_epoch is None:
            reasons["course_not_symptomatic_onboard"] += 1
        elif exp.visible == 0:
            reasons["isolated_whole_symptomatic_course"] += 1
        elif exp.isolated > 0:
            reasons["partially_isolated_but_draw_missed"] += 1
        else:
            reasons["visible_whole_course_draw_missed"] += 1
    return dict(reasons)


def _undated_reasons(
    records: list[dict[str, Any]],
    confirmed: set[int],
    dated: set[int],
    capture: ChannelCapture,
    confirmed_epoch_of: dict[int, int],
) -> dict[str, int]:
    """Why a confirmed host never got a dated onset in the record."""
    reasons: Counter = Counter()
    by_id = {r["agent_id"]: r for r in records}
    for aid in confirmed - dated:
        record = by_id.get(aid)
        if record is None:
            reasons["confirmed_but_not_infected_at_end"] += 1
            continue
        if not record["presented"]:
            reasons["asymptomatic_course"] += 1
            continue
        exp = capture.exposure.get(aid)
        confirm_epoch = confirmed_epoch_of.get(aid)
        if exp is not None and exp.first_symptomatic_epoch is not None:
            if confirm_epoch is not None and (
                exp.first_symptomatic_epoch > confirm_epoch
            ):
                reasons["presented_after_confirm_only"] += 1
            else:
                reasons["symptomatic_course_before_confirm"] += 1
        else:
            reasons["no_symptomatic_epoch_observed"] += 1
    return dict(reasons)


def _dating_fidelity(
    records: list[dict[str, Any]],
    dated_records: dict[int, dict[str, Any]],
    capture: ChannelCapture,
) -> dict[str, Any]:
    """Recorded onset epoch vs the infection record's own onset arithmetic."""
    by_id = {r["agent_id"]: r for r in records}
    errors: list[int] = []
    witness_missing = 0
    first_seen_delta: list[int] = []
    for aid, record in dated_records.items():
        host = by_id.get(aid)
        exp = capture.exposure.get(aid)
        if host is None:
            continue
        if exp is not None and exp.onset_epoch_witness is not None:
            errors.append(int(record["onset_epoch"]) - exp.onset_epoch_witness)
        elif host["true_onset_epoch"] is not None:
            errors.append(
                int(record["onset_epoch"]) - int(host["true_onset_epoch"]),
            )
        else:
            witness_missing += 1
        if exp is not None and exp.first_symptomatic_epoch is not None:
            first_seen_delta.append(
                int(record["onset_epoch"]) - exp.first_symptomatic_epoch,
            )
    exact = sum(1 for error in errors if error == 0)
    return {
        "dated_hosts": len(dated_records),
        "compared": len(errors),
        "witness_unavailable": witness_missing,
        "exact_share": exact / len(errors) if errors else None,
        "max_abs_error": max((abs(e) for e in errors), default=None),
        "recorded_minus_first_symptomatic_epoch": {
            "max_abs": max((abs(d) for d in first_seen_delta), default=None),
            "negative_count": sum(1 for d in first_seen_delta if d < 0),
        },
    }


def build_funnel(
    records: list[dict[str, Any]],
    capture: ChannelCapture,
    profile: dict[str, Any],
    *,
    lab_sampled: set[int],
    lab_confirmed: set[int],
    confirmed_epoch_of: dict[int, int],
    dated: dict[int, dict[str, Any]],
    ever_reported_ids: set[int],
) -> dict[str, Any]:
    """The funnel for one finished voyage, from plain host records."""
    observation = profile.get("observation_model") or {}
    states = list((profile.get("severity_model") or {}).get("states") or [])
    eligibility = list(
        observation.get("syndrome_case_eligibility_by_severity") or [],
    )
    infected_ids = {r["agent_id"] for r in records}
    symptomatic = [r for r in records if r["presented"]]
    symptomatic_ids = {r["agent_id"] for r in symptomatic}

    def eligible(record: dict[str, Any]) -> bool:
        severity = record["severity_peak"]
        if not eligibility:
            return True
        if severity not in states:
            return False
        return float(eligibility[states.index(severity)]) > 0.0

    eligible_ids = {r["agent_id"] for r in symptomatic if eligible(r)}
    onboard_ids = {
        aid for aid, exp in capture.exposure.items()
        if exp.first_symptomatic_epoch is not None
    } & infected_ids
    eligible_onboard_ids = eligible_ids & onboard_ids
    reported = capture.reported_symptomatic_ids & symptomatic_ids
    sampled = lab_sampled & infected_ids
    confirmed = lab_confirmed & infected_ids
    dated_ids = set(dated) & infected_ids

    reported_pre = {
        aid for aid in reported
        if not capture.recognized_at_report(capture.first_report_epoch[aid])
    }
    rungs = {
        "infected": _split(records, infected_ids),
        "symptomatic_course": _split(records, symptomatic_ids),
        # In-voyage subset: hosts whose infection read SYMPTOMATIC in at
        # least one epoch snapshot -- the population the infirmary channel
        # could ever see, excluding convalescent imports whose course
        # predates boarding.
        "symptomatic_onboard": _split(records, onboard_ids),
        "syndrome_eligible": _split(records, eligible_ids),
        "eligible_onboard": _split(records, eligible_onboard_ids),
        "reported_infirmary": _split(records, reported),
        "lab_sampled": _split(records, sampled),
        "lab_confirmed": _split(records, confirmed),
        "onset_dated": _split(records, dated_ids),
    }
    rungs["infected"]["imported"] = sum(
        1 for r in records if r["imported"]
    )
    rungs["infected"]["acquired_onboard"] = (
        rungs["infected"]["total"] - rungs["infected"]["imported"]
    )
    rungs["symptomatic_course"]["illness_class"] = dict(
        Counter(illness_class(r) for r in symptomatic),
    )
    rungs["reported_infirmary"]["pre_recognition"] = len(reported_pre)
    rungs["reported_infirmary"]["post_recognition"] = (
        len(reported) - len(reported_pre)
    )
    severity_tables = {
        "symptomatic": _severity_split(records, symptomatic_ids),
        "eligible": _severity_split(records, eligible_ids),
        "reported": _severity_split(records, reported),
        "confirmed": _severity_split(records, confirmed),
        "dated": _severity_split(records, dated_ids),
    }
    trust_seen = sorted({
        value
        for exp in capture.exposure.values()
        for value in exp.trust_medical_seen
    })
    return {
        "rungs": rungs,
        "severity_tables": severity_tables,
        "recognition": _recognition_summary(capture),
        "channel_totals": {
            "sick_call_events": capture.sick_call_count,
            "noise_report_events": capture.noise_report_count,
            "ever_reported_state_ids": len(ever_reported_ids),
            "reported_outside_funnel": sorted(
                ever_reported_ids - reported,
            )[:50],
            "beliefs_nonempty_epochs": capture.beliefs_nonempty_epochs,
            "trust_medical_seen": trust_seen,
        },
        "non_report_decomposition": _non_report_reasons(
            [r for r in symptomatic if r["agent_id"] in eligible_ids],
            reported,
            capture,
        ),
        "dating_fidelity": _dating_fidelity(records, dated, capture),
        "confirmed_never_dated": _undated_reasons(
            records, confirmed, dated_ids, capture, confirmed_epoch_of,
        ),
        "declared": declared_channel_table(profile),
    }


def funnel_ratios(funnel: dict[str, Any]) -> dict[str, float | None]:
    """Rung-to-rung and rung-to-infected shares for the readout table."""
    rungs = funnel["rungs"]

    def num(key: str) -> int:
        return int(rungs[key]["total"])

    infected = num("infected")
    symptomatic = num("symptomatic_course")
    onboard = num("symptomatic_onboard")
    eligible = num("syndrome_eligible")
    eligible_onboard = num("eligible_onboard")
    reported = num("reported_infirmary")
    confirmed = num("lab_confirmed")
    dated = num("onset_dated")

    def share(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "infected": infected,
        "symptomatic_per_infected": share(symptomatic, infected),
        "symptomatic_onboard_per_infected": share(onboard, infected),
        "eligible_per_symptomatic": share(eligible, symptomatic),
        "reported_per_eligible": share(reported, eligible),
        # The infirmary-capture observable literature states (share of ill
        # aboard who ever report): reporters over hosts with an eligible,
        # in-voyage symptomatic course.
        "reported_per_eligible_onboard": share(reported, eligible_onboard),
        "reported_per_symptomatic_onboard": share(reported, onboard),
        "reported_per_symptomatic": share(reported, symptomatic),
        "confirmed_per_reported": share(confirmed, reported),
        "confirmed_per_symptomatic": share(confirmed, symptomatic),
        "dated_per_confirmed": share(dated, confirmed),
        "dated_per_infected": share(dated, infected),
        "reported_passenger_share": (
            share(
                rungs["reported_infirmary"]["passenger"],
                rungs["symptomatic_onboard"]["passenger"],
            )
        ),
        "reported_crew_share": (
            share(
                rungs["reported_infirmary"]["crew"],
                rungs["symptomatic_onboard"]["crew"],
            )
        ),
    }


def run_seed(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    pathogen_id: str,
) -> dict[str, Any]:
    """Run one unmodified voyage and read its observation funnel."""
    started = time.perf_counter()
    num_agents = declared_total(platform)
    _alpha, beta = load_dose_response(pathogen_id, bundle)
    spec_dict = _pdc.build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=num_agents,
        pathogen_id=pathogen_id, alpha=None, beta=beta,
    )
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        sim = ShipSimulation(picard_spec, display=False)
        capture = ChannelCapture(pathogen_id)
        sim.epoch_observer = capture.observe
        sim.run()
    syndromic = sim.modalities["syndromic"]
    sampled = {
        aid for (pid, aid) in syndromic._lab_sampled if pid == pathogen_id
    }
    confirmed_epoch_of = {
        aid: int(epoch)
        for (pid, aid), epoch in syndromic._lab_confirmed.items()
        if pid == pathogen_id
    }
    dated = {
        aid: dict(rec)
        for (pid, aid), rec in syndromic._onset_observations.items()
        if pid == pathogen_id
    }
    ever_reported = set(getattr(sim.state, "ever_reported_ids", set()) or ())
    records = harvest_infections(sim, pathogen_id)
    funnel = build_funnel(
        records, capture, sim.pathogen_profiles[pathogen_id],
        lab_sampled=sampled,
        lab_confirmed=set(confirmed_epoch_of),
        confirmed_epoch_of=confirmed_epoch_of,
        dated=dated,
        ever_reported_ids=ever_reported,
    )
    return {
        "seed": int(seed),
        "platform": platform,
        "bundle": bundle,
        "pathogen_id": pathogen_id,
        "num_epochs": int(epochs),
        "num_agents": num_agents,
        "rungs": funnel["rungs"],
        "severity_tables": funnel["severity_tables"],
        "recognition": funnel["recognition"],
        "channel_totals": funnel["channel_totals"],
        "non_report_decomposition": funnel["non_report_decomposition"],
        "dating_fidelity": funnel["dating_fidelity"],
        "confirmed_never_dated": funnel["confirmed_never_dated"],
        "declared": funnel["declared"],
        "ratios": funnel_ratios(funnel),
        "shared_rungs": ascertainment_funnel(sim, pathogen_id=pathogen_id),
        "wall_clock_seconds_run": time.perf_counter() - started,
    }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(values)
    if not ordered:
        return {"median": None, "q05": None, "q95": None}

    def pick(frac: float) -> float:
        index = min(len(ordered) - 1, int(round(frac * (len(ordered) - 1))))
        return ordered[index]

    return {
        "median": pick(0.5),
        "q05": pick(0.05),
        "q95": pick(0.95),
    }


_POOLED_RATIO_RUNGS: dict[str, tuple[str, str, str]] = {
    # ratio key -> (numerator rung, denominator rung, role)
    "symptomatic_per_infected": ("symptomatic_course", "infected", "total"),
    "symptomatic_onboard_per_infected": (
        "symptomatic_onboard", "infected", "total"),
    "eligible_per_symptomatic": (
        "syndrome_eligible", "symptomatic_course", "total"),
    "reported_per_eligible": (
        "reported_infirmary", "syndrome_eligible", "total"),
    "reported_per_eligible_onboard": (
        "reported_infirmary", "eligible_onboard", "total"),
    "reported_per_symptomatic_onboard": (
        "reported_infirmary", "symptomatic_onboard", "total"),
    "reported_per_symptomatic": (
        "reported_infirmary", "symptomatic_course", "total"),
    "confirmed_per_reported": (
        "lab_confirmed", "reported_infirmary", "total"),
    "confirmed_per_symptomatic": (
        "lab_confirmed", "symptomatic_course", "total"),
    "dated_per_confirmed": ("onset_dated", "lab_confirmed", "total"),
    "dated_per_infected": ("onset_dated", "infected", "total"),
    "reported_passenger_share": (
        "reported_infirmary", "symptomatic_onboard", "passenger"),
    "reported_crew_share": (
        "reported_infirmary", "symptomatic_onboard", "crew"),
}


def _pooled_ratio(per_seed: list[dict[str, Any]], num: str, den: str,
                  role: str) -> float | None:
    numerator = sum(
        row["rungs"].get(num, {}).get(role, 0) for row in per_seed)
    denominator = sum(
        row["rungs"].get(den, {}).get(role, 0) for row in per_seed)
    return numerator / denominator if denominator else None


def build_readout(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-seed funnel ratios into median + spread for the ledger.

    ``rung_ratios`` is the distribution of per-seed ratios (None-bearing
    seeds skipped). ``pooled_ratios`` divides summed numerators by summed
    denominators -- the right view when per-seed populations are thin.
    """
    keys = sorted(per_seed[0]["ratios"]) if per_seed else []
    pooled = {}
    for key in keys:
        values = [
            row["ratios"][key]
            for row in per_seed
            if row["ratios"].get(key) is not None
        ]
        pooled[key] = _quantiles([float(v) for v in values])
    infected_counts = [row["rungs"]["infected"]["total"] for row in per_seed]
    return {
        "seeds": [row["seed"] for row in per_seed],
        "n_seeds": len(per_seed),
        "infected_per_seed": {
            "median": _quantiles([float(v) for v in infected_counts])["median"],
            "min": min(infected_counts, default=None),
            "max": max(infected_counts, default=None),
        },
        "rung_ratios": pooled,
        "pooled_rung_totals": {
            rung: {
                role: sum(
                    row["rungs"].get(rung, {}).get(role, 0)
                    for row in per_seed
                )
                for role in ("total", "passenger", "crew", "other")
            }
            for rung in (
                per_seed[0]["rungs"] if per_seed else {}
            )
        },
        "pooled_ratios": {
            key: _pooled_ratio(per_seed, num, den, role)
            for key, (num, den, role) in _POOLED_RATIO_RUNGS.items()
        },
        "per_seed_ratios": [
            {"seed": row["seed"], **row["ratios"]} for row in per_seed
        ],
        "dating_fidelity": {
            "dated_hosts_total": sum(
                row["dating_fidelity"]["dated_hosts"] for row in per_seed
            ),
            "exact_share_min": min(
                (
                    row["dating_fidelity"]["exact_share"]
                    for row in per_seed
                    if row["dating_fidelity"]["exact_share"] is not None
                ),
                default=None,
            ),
            "max_abs_error": max(
                (
                    row["dating_fidelity"]["max_abs_error"] or 0
                    for row in per_seed
                ),
                default=None,
            ),
        },
        "confirmed_never_dated_total": {
            reason: sum(
                row["confirmed_never_dated"].get(reason, 0)
                for row in per_seed
            )
            for row in per_seed
            for reason in row["confirmed_never_dated"]
        },
        "non_report_total": {
            reason: sum(
                row["non_report_decomposition"].get(reason, 0)
                for row in per_seed
            )
            for row in per_seed
            for reason in row["non_report_decomposition"]
        },
    }


_identifier = _pdc._identifier


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--platform", type=_identifier, default="spirit_cruise_3000")
    parser.add_argument(
        "--bundle", type=_identifier,
        default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument(
        "--pathogen-id", type=_identifier, default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument(
        "--seeds", type=int, nargs="+",
        default=list(range(8000, 8020)),
        help="NORO-COINCIDENCE-CELL-01 canary block is 8000-8019",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--arm-tag", type=_identifier, default="pooled_default")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    per_seed = []
    for seed in args.seeds:
        summary = run_seed(
            seed=seed,
            platform=args.platform,
            bundle=args.bundle,
            epochs=args.epochs,
            pathogen_id=args.pathogen_id,
        )
        per_seed.append(summary)
        filename = (
            f"observation_channel_funnel_{args.arm_tag}_seed{seed}.json.gz"
        )
        path = resolve_child_path(str(out_dir), filename)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=1)
        ratios = summary["ratios"]
        print(
            f"seed {seed}: infected={ratios['infected']} "
            f"symp={_fmt(ratios['symptomatic_per_infected'])} "
            f"rep/elig={_fmt(ratios['reported_per_eligible'])} "
            f"conf/rep={_fmt(ratios['confirmed_per_reported'])} "
            f"dated/conf={_fmt(ratios['dated_per_confirmed'])} "
            f"-> {path}",
            flush=True,
        )
    readout = build_readout(per_seed)
    readout_path = resolve_child_path(
        str(out_dir),
        f"observation_channel_funnel_{args.arm_tag}_readout.json",
    )
    with validated_open(
        readout_path, "w", allowed_roots=(str(out_dir),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(readout, indent=1))
    print(f"readout: {readout_path}")
    return 0


def _fmt(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "n/a"


if __name__ == "__main__":
    raise SystemExit(main())
