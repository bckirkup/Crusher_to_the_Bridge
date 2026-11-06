"""Cumulative role-checkpoint emitter (Paper-1 sensitivity, Child A).

A read-only sidecar over the ``SimulationState`` person-ID sets the engine
already maintains. At each declared voyage day it snapshots, separately for
passengers and crew, the unique persons ever infected, ever ill, ever a
sick-call *etiologic* reporter, ever a sick-call *clinical-noise* reporter,
and the set algebra between the two reporter sets. Every count is the
cardinality of an actual ``set[int]`` of agent IDs: unions and overlaps are
never recovered from totals or role proportions, and a person who reports
on several epochs is one person.

Zero RNG draws, no writes to existing state: the only state touched is the
dedicated ``SimulationState.role_checkpoints`` scratch dict.

Checkpoint timing
-----------------
Day ``d`` is the hourly epoch boundary ``24 * d`` wall-clock hours after
voyage start. With ``hours_per_epoch`` h per epoch the snapshot is taken at
the end of epoch index ``24 * d / h - 1`` -- the last epoch whose
surveillance and escalation phases complete before that boundary -- and is
cumulative over epoch indices ``0 .. 24 * d / h - 1`` inclusive. Under the
venue02 hourly clock (``h = 1``) days 3/7/10/12 are epoch indices
71/167/239/287. Under the legacy epoch-equals-day clock (``h = 24``) they
are 2/6/9/11. A day whose boundary is not reached by the voyage is emitted
as ``available: false`` with null counts, never as zero.

Clinical eligibility
--------------------
``ever_ill_ids`` is the symptomatic-presentation set (``update_ever_ill_ids``);
it is the clinical-AGE eligibility reference. ``ever_reported_ids`` is
populated by ``update_ever_reported_ids`` from the syndromic modality's
``true_positive_ids`` intersected with the symptomatic roster at report
time, so every etiologic reporter satisfied clinical eligibility when
reporting. ``ever_reported_noise_ids`` holds background sick-call
presenters (``noise_ids``), whose presentation is clinical noise, not
etiologic AGE; they are *not* eligible unless they also appear in
``ever_ill_ids`` through a separate illness episode. Consequently the
reporter union is a sick-call *presentation* set, not a matched clinical-AGE
endpoint: ``union_ever_ill`` is the subset of the union that does satisfy
clinical eligibility and ``union_not_ill`` the subset that never did.
Crew screening roster entries and caregiver reports are in neither reporter
set and are not counted here.
"""
from __future__ import annotations

import math
from typing import Any

from orchestrator_init import role_group_for_agent

SCHEMA = "role_checkpoints/1.0"
DEFAULT_CHECKPOINT_DAYS: tuple[int, ...] = (3, 7, 10, 12)
HOURS_PER_DAY = 24.0
ROLES: tuple[str, ...] = ("passenger", "crew")
CONFIG_KEY = "role_checkpoints"

# Column order of the per-role count block; the contract projects these.
MEASURES: tuple[str, ...] = (
    "complement",
    "infected",
    "ill",
    "unique_etiologic_reporters",
    "unique_clinical_noise_reporters",
    "reporter_overlap",
    "unique_person_union",
    "union_ever_ill",
    "union_not_ill",
    "noise_reporters_ever_ill",
)

DEFINITIONS: dict[str, str] = {
    "complement": "agents of the role on the roster (departed included), "
                  "the denominator the summary block uses",
    "infected": "|ever_infected_ids ∩ role| -- persons ever infected, "
                "imports included",
    "ill": "|ever_ill_ids ∩ role| -- persons ever showing symptomatic "
           "presentation (clinical-AGE eligibility reference set)",
    "unique_etiologic_reporters": "|ever_reported_ids ∩ role| -- unique "
                                  "persons ever a sick-call true positive "
                                  "while symptomatic (eligible at report)",
    "unique_clinical_noise_reporters": "|ever_reported_noise_ids ∩ role| -- "
                                       "unique persons ever a background "
                                       "sick-call presenter (not eligible "
                                       "by that presentation)",
    "reporter_overlap": "|etiologic ∩ noise| -- persons in both reporter sets",
    "unique_person_union": "|etiologic ∪ noise| -- unique persons who ever "
                           "presented at sick call for either reason; a "
                           "presentation set, not a matched clinical-AGE "
                           "endpoint",
    "union_ever_ill": "|(etiologic ∪ noise) ∩ ever_ill_ids| -- the union "
                      "members who satisfy clinical eligibility",
    "union_not_ill": "|(etiologic ∪ noise) − ever_ill_ids| -- union members "
                     "who never satisfied clinical eligibility",
    "noise_reporters_ever_ill": "|noise ∩ ever_ill_ids| -- noise reporters "
                                "who had a genuine symptomatic episode at "
                                "some point",
    "unit": "unique persons (agent IDs); a person reporting on several "
            "epochs counts once",
    "timing": "day d snapshot at end of epoch index 24*d/hours_per_epoch - 1, "
              "cumulative over epoch indices 0..that index inclusive; the "
              "snapshot runs after the epoch's surveillance and escalation "
              "phases, before the epoch record is built",
}


def resolve_config(cfg: dict[str, Any] | None) -> tuple[bool, tuple[int, ...]]:
    """``(enabled, days)`` from ``cfg["role_checkpoints"]``.

    Absent block resolves to enabled at the Edison checkpoint days; an
    explicit ``enabled: false`` emits nothing at all (no record key, no
    summary.json key), which is the paired-replay control arm.
    """
    block = (cfg or {}).get(CONFIG_KEY)
    if not isinstance(block, dict):
        return True, DEFAULT_CHECKPOINT_DAYS
    enabled = bool(block.get("enabled", True))
    raw_days = block.get("days", DEFAULT_CHECKPOINT_DAYS)
    days = tuple(sorted({int(d) for d in raw_days if int(d) > 0}))
    return enabled, days or DEFAULT_CHECKPOINT_DAYS


def checkpoint_epoch_index(day: int, hours_per_epoch: float) -> tuple[int, bool]:
    """``(epoch_index, exact_boundary)`` for voyage day ``day``.

    ``epoch_index`` is the last epoch completed at or before the ``24*day``
    hour boundary; ``exact_boundary`` is False when the boundary falls
    inside an epoch (the snapshot then covers the epoch containing it).
    """
    epochs_to_boundary = (HOURS_PER_DAY * day) / float(hours_per_epoch)
    rounded = round(epochs_to_boundary)
    exact = math.isclose(epochs_to_boundary, rounded, rel_tol=0.0, abs_tol=1e-9)
    n_epochs = rounded if exact else math.ceil(epochs_to_boundary)
    return max(int(n_epochs) - 1, 0), exact


def role_id_sets(agents: list[dict[str, Any]]) -> dict[str, set[int]]:
    """Agent-ID set per role, read from the exported agent dicts."""
    sets: dict[str, set[int]] = {role: set() for role in ROLES}
    for agent in agents:
        sets.setdefault(role_group_for_agent(agent), set()).add(
            int(agent["agent_id"]),
        )
    return sets


def role_counts(
    role_ids: set[int],
    *,
    infected: set[int],
    ill: set[int],
    etiologic: set[int],
    noise: set[int],
) -> dict[str, int]:
    """Set-algebra counts for one role, every value a set cardinality."""
    etio = etiologic & role_ids
    nois = noise & role_ids
    union = etio | nois
    ill_role = ill & role_ids
    return {
        "complement": len(role_ids),
        "infected": len(infected & role_ids),
        "ill": len(ill_role),
        "unique_etiologic_reporters": len(etio),
        "unique_clinical_noise_reporters": len(nois),
        "reporter_overlap": len(etio & nois),
        "unique_person_union": len(union),
        "union_ever_ill": len(union & ill_role),
        "union_not_ill": len(union - ill_role),
        "noise_reporters_ever_ill": len(nois & ill_role),
    }


def snapshot(
    agents: list[dict[str, Any]], state: Any, *, day: int, epoch: int,
    hours_per_epoch: float, exact_boundary: bool,
) -> dict[str, Any]:
    """One available checkpoint, computed from the live state sets."""
    roles = role_id_sets(agents)
    sets = {
        "infected": set(state.ever_infected_ids),
        "ill": set(state.ever_ill_ids),
        "etiologic": set(state.ever_reported_ids),
        "noise": set(state.ever_reported_noise_ids),
    }
    record: dict[str, Any] = {
        "day": int(day),
        "available": True,
        "status": "observed",
        "epoch_index": int(epoch),
        "epochs_completed": int(epoch) + 1,
        "hours_elapsed": float((int(epoch) + 1) * hours_per_epoch),
        "exact_boundary": bool(exact_boundary),
    }
    for role in ROLES:
        record[role] = role_counts(roles.get(role, set()), **sets)
    record["all"] = role_counts(set().union(*roles.values()), **sets)
    return record


def unavailable(
    day: int, epoch_index: int, exact_boundary: bool, num_epochs: int,
) -> dict[str, Any]:
    """A declared day the voyage never reached: explicit nulls, never zero."""
    record: dict[str, Any] = {
        "day": int(day),
        "available": False,
        "status": "not_reached",
        "epoch_index": int(epoch_index),
        "epochs_completed": None,
        "hours_elapsed": None,
        "exact_boundary": bool(exact_boundary),
        "num_epochs": int(num_epochs),
    }
    for role in (*ROLES, "all"):
        record[role] = dict.fromkeys(MEASURES)
    return record


def maybe_record(
    state: Any, agents: list[dict[str, Any]], *, epoch: int, cfg: dict[str, Any],
    hours_per_epoch: float,
) -> None:
    """Snapshot into ``state.role_checkpoints`` when ``epoch`` closes a day."""
    enabled, days = resolve_config(cfg)
    if not enabled:
        return
    for day in days:
        idx, exact = checkpoint_epoch_index(day, hours_per_epoch)
        if idx == epoch:
            state.role_checkpoints[f"day_{day}"] = snapshot(
                agents, state, day=day, epoch=epoch,
                hours_per_epoch=hours_per_epoch, exact_boundary=exact,
            )


def finalize_block(
    state: Any, *, cfg: dict[str, Any], hours_per_epoch: float,
    clock_mode: str, num_epochs: int,
) -> dict[str, Any] | None:
    """The ``role_checkpoints`` summary.json block, or None when disabled."""
    enabled, days = resolve_config(cfg)
    if not enabled:
        return None
    checkpoints: dict[str, Any] = {}
    for day in days:
        key = f"day_{day}"
        idx, exact = checkpoint_epoch_index(day, hours_per_epoch)
        checkpoints[key] = state.role_checkpoints.get(key) or unavailable(
            day, idx, exact, num_epochs,
        )
    return {
        "schema": SCHEMA,
        "enabled": True,
        "days": list(days),
        "clock": {
            "mode": clock_mode,
            "hours_per_epoch": float(hours_per_epoch),
            "num_epochs": int(num_epochs),
            "observed_terminal_epoch": int(num_epochs) - 1,
            "epoch_mapping": {
                f"day_{day}": checkpoint_epoch_index(day, hours_per_epoch)[0]
                for day in days
            },
        },
        "definitions": DEFINITIONS,
        "checkpoints": checkpoints,
    }
