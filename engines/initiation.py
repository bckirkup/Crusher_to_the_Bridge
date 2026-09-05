"""Initiation: how a voyage starts with infection already aboard.

Two mechanisms, deliberately not one. **Boarding** is a prevalence: each
eligible host is drawn with the measured per-person probability of arriving
already shedding, and because it is a prevalence the host arrives somewhere
inside its own course, so its infection age has to be drawn rather than set to
zero. **Explicit seeds** are the scenario override: a stated number of index
cases at a stated epoch, additive with boarding by construction.

Boarding has two draw modes, because independent per-person draws are the
wrong shape for a pathogen nobody carries in the embarkation population. A
rare import — Andes virus, Ebola — arrives as one travelling party that was
exposed together at a common source: either no such party is aboard, or a
whole cabin group of them is. ``mode: party`` draws that all-or-nothing
cluster; ``mode: prevalence`` draws the independent Binomial that an endemic
community prevalence licenses. Rescaling the independent draw cannot produce a
clustered import, which is the archetype recorded in
``.agents/skills/model-parameter-provenance/SKILL.md``: a well-mixed pool
standing in for a small number of concentrated events.

With no ``initiation`` block in the config the plan is ``legacy`` and every
caller runs the paths it ran before, consuming exactly the draws it consumed
before. See ``docs/proposals/initiation_engine_spec.md`` for the design and
for what each configured coordinate means.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import IllnessStatus, InfectionStatus
from engines.natural_history import (
    DEFAULT_RECOVERY_DAY,
    draw_symptom_severity,
    host_age_band,
    incubation_days,
)

# Attempts allowed for the state draw before a host is left uninfected, used
# when the drawn state's window is empty for this host's own duration.
_STATE_MAX_DRAWS = 8

ROLE_PASSENGER = "passenger"
ROLE_CREW = "crew"
_ROLES = (ROLE_PASSENGER, ROLE_CREW)

STATE_NEVER_SYMPTOMATIC = "never_symptomatic"
STATE_PRESYMPTOMATIC = "presymptomatic"
STATE_CONVALESCENT = "convalescent"
# Party mode only: infected at the common exposure, not yet shedding. A
# prevalent sample never contains it (a prevalence is of hosts shedding), and a
# party that has already had a case in it does not board, so it replaces the
# convalescent state there.
STATE_INCUBATING = "incubating"
_STATES = (
    STATE_NEVER_SYMPTOMATIC, STATE_PRESYMPTOMATIC, STATE_CONVALESCENT,
    STATE_INCUBATING,
)

# The two boarding draw modes. Which one a pathogen uses is a claim about the
# embarkation population, not a tuning choice: a prevalence needs a measured
# per-person carriage rate to exist, and a rare import has none.
BOARDING_MODE_PREVALENCE = "prevalence"
BOARDING_MODE_PARTY = "party"
_BOARDING_MODES = (BOARDING_MODE_PREVALENCE, BOARDING_MODE_PARTY)

MODE_LEGACY = "legacy"
MODE_NONE = "none"
MODE_BOARDING = "boarding"
MODE_SEEDS = "seeds"
MODE_BOARDING_AND_SEEDS = "boarding+seeds"

# The artifact key always exists, so downstream analysis can tell a
# prevalence-based run from a legacy one without re-deriving it.
LEGACY_MANIFEST: dict[str, Any] = {"mode": MODE_LEGACY}

_ASYMPTOMATIC_SEVERITY = "asymptomatic"


@dataclass(frozen=True)
class BoardingParty:
    """One clustered import: a travelling party exposed at a common source.

    ``probability`` is per voyage, not per person — the chance that any such
    party embarks at all — and ``size`` is how many of it are infected when one
    does. The two are separate because they answer different questions and the
    literature supports them differently: whether an imported case sails is a
    route and season property, how large its travelling group is is not.
    """

    probability: float
    size: int
    role: str


@dataclass(frozen=True)
class BoardingSpec:
    """One pathogen's boarding channel, as configured."""

    pathogen_id: str
    passenger_prevalence: float
    crew_prevalence: float
    never_symptomatic_fraction: float
    presymptomatic_share_of_presenting: float
    party: BoardingParty | None = None
    epoch: int = 0

    @property
    def mode(self) -> str:
        """Which draw this pathogen boards by."""
        if self.party is None:
            return BOARDING_MODE_PREVALENCE
        return BOARDING_MODE_PARTY


@dataclass(frozen=True)
class ExplicitSeed:
    """One scenario-stated introduction."""

    pathogen_id: str
    count: int
    role: str | None
    epoch: int
    infection_age_days: float
    dose: float | None
    strain_id: str | None


@dataclass(frozen=True)
class InitiationPlan:
    """The resolved initiation configuration for one run."""

    boarding: tuple[BoardingSpec, ...]
    seeds: tuple[ExplicitSeed, ...]
    legacy: bool


@dataclass(frozen=True)
class BoardingReport:
    """What one pathogen's boarding draw actually produced."""

    pathogen_id: str
    drawn_by_role: dict[str, int]
    composition: dict[str, int]


# ── Configuration resolution ─────────────────────────────────────────────

def initiation_configured(cfg: dict[str, Any] | None) -> bool:
    """Whether this run declares an ``initiation`` block at all.

    Callers that must decide before the pathogen profiles are loaded — the
    engine's own pathogen-unaware index case — read this rather than resolving
    the plan.
    """
    return isinstance(cfg, dict) and cfg.get("initiation") is not None


def _fraction(value: Any, location: str, requirement: str) -> float:
    """Read one [0, 1] coordinate, naming the config key and the requirement."""
    if value is None:
        raise ValueError(f"{location} is unset: {requirement}")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(
            f"{location} = {number!r} is outside [0, 1]: {requirement}",
        )
    return number


def _known_pathogen(
    pathogen_id: str,
    location: str,
    pathogen_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if pathogen_id not in pathogen_profiles:
        raise ValueError(
            f"{location} names pathogen {pathogen_id!r}, which is absent from "
            f"the loaded profiles {sorted(pathogen_profiles)}",
        )
    return pathogen_profiles[pathogen_id]


def _refuse_legacy_index_case(
    pathogen_id: str,
    location: str,
    profile: dict[str, Any],
    mechanism: str,
) -> None:
    """Refuse an initiation mechanism layered over ``profile.initial_infected``.

    Ownership is per pathogen, and an owned pathogen is dropped from legacy
    seeding: leaving the profile field set would make the run's index-case
    count silently the initiation block's rather than the profile's, so a
    sweep over ``initial_infected`` would move a label and nothing else.
    """
    if profile.get("initial_infected") is None:
        return
    raise ValueError(
        f"{location} {mechanism} while the {pathogen_id} profile carries "
        f"initial_infected={profile['initial_infected']!r}: initiation owns "
        f"{pathogen_id}, so that profile field would be ignored rather than "
        "honoured, and the resulting incidence would be attributable to "
        "neither. Null the profile field, or leave initiation without this "
        "pathogen",
    )


def _resolve_mode(block: dict[str, Any], location: str) -> str:
    """Which draw mode this block asks for, defaulting to the prevalence."""
    mode = str(block.get("mode") or BOARDING_MODE_PREVALENCE)
    if mode not in _BOARDING_MODES:
        raise ValueError(
            f"{location}.mode = {mode!r} is not one of "
            f"{list(_BOARDING_MODES)}: a boarding draw is either an "
            "independent per-person prevalence or one clustered party",
        )
    return mode


def _resolve_party(block: dict[str, Any], location: str) -> BoardingParty:
    """The ``party`` coordinates, refusing a prevalence alongside them.

    A block carrying both would be two mechanisms for one import, and the
    resulting count would be attributable to neither.
    """
    if block.get("prevalence"):
        raise ValueError(
            f"{location} is in party mode and also carries a prevalence: a "
            "clustered import and an independent per-person draw are "
            "alternative mechanisms, so keep one of them",
        )
    party = block.get("party") or {}
    size = int(party.get("size", 0) or 0)
    if size < 1:
        raise ValueError(
            f"{location}.party.size = {size} is below one: a party that "
            "boards has at least one infected member, and no party aboard "
            "is what party.probability expresses",
        )
    role = str(party.get("role") or ROLE_PASSENGER)
    if role not in _ROLES:
        raise ValueError(
            f"{location}.party.role = {role!r} is neither "
            f"{ROLE_PASSENGER!r} nor {ROLE_CREW!r}, and agent roles carry no "
            "other value",
        )
    return BoardingParty(
        probability=_fraction(
            party.get("probability"),
            f"{location}.party.probability",
            "it is the per-voyage chance that such a party embarks at all, "
            "so it is not defaulted from a per-person prevalence",
        ),
        size=size,
        role=role,
    )


def _resolve_prevalence(
    block: dict[str, Any], location: str,
) -> tuple[float, float]:
    """The two per-role boarding prevalences."""
    prevalence = block.get("prevalence") or {}
    requirement = "a boarding prevalence is a per-person probability"
    return (
        _fraction(
            prevalence.get(ROLE_PASSENGER),
            f"{location}.prevalence.passenger",
            requirement,
        ),
        _fraction(
            prevalence.get(ROLE_CREW),
            f"{location}.prevalence.crew",
            requirement,
        ),
    )


def _resolve_epoch(
    block: dict[str, Any], profile: dict[str, Any], location: str,
) -> int:
    """Which port call this cohort embarks at, the sailing port by default.

    A staged bundle introduces its pathogens at successive port calls, and
    that schedule is the profile's ``introduction_epoch``: it survives the
    migration off the fiat index case, because *when* a pathogen arrives and
    *how many* arrive are different claims. A block may state its own epoch to
    override the profile's.
    """
    stated = block.get("epoch")
    epoch = int(
        profile.get("introduction_epoch", 0) or 0 if stated is None
        else stated,
    )
    if epoch < 0:
        raise ValueError(
            f"{location}.epoch = {epoch} is negative, and the voyage has no "
            "port call before it sails",
        )
    return epoch


def _resolve_boarding_spec(
    pathogen_id: str,
    block: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> BoardingSpec:
    """One ``initiation.boarding.<pathogen>`` block, fully validated."""
    location = f"initiation.boarding.{pathogen_id}"
    profile = _known_pathogen(pathogen_id, location, pathogen_profiles)
    _refuse_legacy_index_case(pathogen_id, location, profile, "is enabled")
    split = block.get("state_split") or {}
    party = (
        _resolve_party(block, location)
        if _resolve_mode(block, location) == BOARDING_MODE_PARTY
        else None
    )
    passenger, crew = (
        (0.0, 0.0) if party is not None
        else _resolve_prevalence(block, location)
    )
    return BoardingSpec(
        pathogen_id=pathogen_id,
        passenger_prevalence=passenger,
        crew_prevalence=crew,
        never_symptomatic_fraction=_fraction(
            split.get("never_symptomatic_fraction"),
            f"{location}.state_split.never_symptomatic_fraction",
            "no value for it is licensed in "
            "docs/parameter_provenance_register.md, so enabling boarding "
            "requires setting it explicitly rather than defaulting it",
        ),
        presymptomatic_share_of_presenting=_fraction(
            split.get("presymptomatic_share_of_presenting"),
            f"{location}.state_split.presymptomatic_share_of_presenting",
            "it is a share of the imported hosts that do present",
        ),
        party=party,
        epoch=_resolve_epoch(block, profile, location),
    )


def _boarding_enabled(block: Any, whole: dict[str, Any]) -> bool:
    """Whether one pathogen's block is on, under the channel's own switch.

    A per-pathogen ``enabled: false`` is the fiat opt-out: the profile bundle
    ships every pathogen's boarding coordinates, and an arm that wants a fiat
    index case for one of them withdraws that one rather than the channel.
    """
    if not whole.get("enabled", False):
        return False
    return bool((block or {}).get("enabled", True))


def _merge_block(base: Any, override: Any) -> Any:
    """Config over profile, one nested mapping level at a time; null erases."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    merged = dict(base)
    for key, value in override.items():
        merged[key] = _merge_block(base.get(key), value)
    return merged


def profile_boarding_block(profile: dict[str, Any]) -> dict[str, Any] | None:
    """The boarding coordinates a pathogen profile ships, if it ships any.

    The profile is where a pathogen's own defaults live, so that each bundle
    carries the coordinates for exactly the pathogens it loads: a ship-wide
    config cannot name pathogens from a bundle it does not load, and an arm
    that narrows its profiles must not inherit blocks for the ones it dropped.
    """
    block = profile.get("boarding")
    return dict(block) if isinstance(block, dict) else None


def boarding_blocks(
    raw: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Effective per-pathogen blocks: profile defaults under config overrides.

    Every loaded profile that ships a ``boarding`` block is a candidate, and so
    is every pathogen the config names — a config block over an unloaded
    pathogen stays an error, since nothing would honour it.
    """
    blocks: dict[str, dict[str, Any]] = {}
    for pathogen_id, profile in pathogen_profiles.items():
        shipped = profile_boarding_block(profile)
        if shipped is not None:
            blocks[str(pathogen_id)] = shipped
    for pathogen_id, block in raw.items():
        if pathogen_id == "enabled":
            continue
        merged = _merge_block(blocks.get(str(pathogen_id), {}), block or {})
        blocks[str(pathogen_id)] = merged
    return blocks


def _resolve_boarding(
    raw: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> tuple[BoardingSpec, ...]:
    """Every enabled pathogen block, profile defaults under config overrides.

    The per-pathogen ``enabled: false`` survives the merge, so an arm can
    withdraw one pathogen's boarding (its fiat opt-out) while the bundle's
    other pathogens keep theirs.
    """
    if not raw.get("enabled", False):
        return ()
    return tuple(
        _resolve_boarding_spec(pathogen_id, block, pathogen_profiles)
        for pathogen_id, block in sorted(boarding_blocks(raw, pathogen_profiles).items())
        if _boarding_enabled(block, raw)
    )


def _resolve_seed(
    index: int,
    raw: dict[str, Any],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> ExplicitSeed:
    location = f"initiation.explicit_seeds[{index}]"
    pathogen_id = str(raw.get("pathogen") or "")
    profile = _known_pathogen(
        pathogen_id, f"{location}.pathogen", pathogen_profiles,
    )
    _refuse_legacy_index_case(
        pathogen_id, location, profile, "seeds that pathogen",
    )
    count = int(raw.get("count", 1))
    if count < 0:
        raise ValueError(
            f"{location}.count = {count} is negative: a seed introduces a "
            "non-negative number of hosts",
        )
    role = raw.get("role")
    if role is not None and str(role) not in _ROLES:
        raise ValueError(
            f"{location}.role = {role!r} is neither {ROLE_PASSENGER!r}, "
            f"{ROLE_CREW!r} nor null, and agent roles carry no other value",
        )
    age_days = float(raw.get("infection_age_days", 0.0) or 0.0)
    if age_days < 0.0:
        raise ValueError(
            f"{location}.infection_age_days = {age_days} is negative: an "
            "infection age is measured forward from acquisition",
        )
    dose = raw.get("dose")
    strain = raw.get("strain")
    return ExplicitSeed(
        pathogen_id=pathogen_id,
        count=count,
        role=None if role is None else str(role),
        epoch=int(raw.get("epoch", 0)),
        infection_age_days=age_days,
        dose=None if dose is None else float(dose),
        strain_id=None if strain is None else str(strain),
    )


def resolve_initiation_plan(
    cfg: dict[str, Any] | None,
    pathogen_profiles: dict[str, dict[str, Any]],
) -> InitiationPlan:
    """Resolve ``cfg['initiation']`` into a validated plan.

    With no ``initiation`` key the plan is ``legacy`` and every caller keeps
    its present behaviour, down to the draws it consumes. Every other outcome
    is validated eagerly: a misconfigured boarding channel is a load error, not
    a silently defaulted run.
    """
    raw = (cfg or {}).get("initiation")
    if raw is None:
        return InitiationPlan((), (), legacy=True)
    if not isinstance(raw, dict):
        raise ValueError(
            f"initiation must be a mapping, got {type(raw).__name__}",
        )
    boarding = _resolve_boarding(raw.get("boarding") or {}, pathogen_profiles)
    seeds = tuple(
        _resolve_seed(index, seed or {}, pathogen_profiles)
        for index, seed in enumerate(raw.get("explicit_seeds") or ())
    )
    return InitiationPlan(boarding, seeds, legacy=False)


# ── The boarding draw ────────────────────────────────────────────────────

def _eligible(agent: Any, pathogen_id: str, role: str | None = None) -> bool:
    """Whether this host can be given a boarding or seeded infection."""
    if role is not None and str(getattr(agent, "role", "")) != role:
        return False
    return not (
        agent.immune
        or agent.is_infected_with(pathogen_id)
        or agent.infection_status == InfectionStatus.RECOVERED
    )


def _host_duration(
    agent: Any, pathogen_id: str, profile: dict[str, Any],
) -> float:
    """This host's own shedding duration, read as ``clearance_days`` reads it.

    A host property, not a draw. The chronic-shedder branch has already run at
    initialization, over the immunocompromised hosts it is defined on, so a
    chronic host carries its stamped duration here and every other host
    carries the profile's. Nothing in initiation re-draws it: running the
    ``chronic_shedder_fraction`` Bernoulli over boarding hosts would promote a
    share of *immunocompromised hosts* into a share of *all infections*.
    """
    assigned = agent.get_chronic_shedding_duration(pathogen_id)
    if assigned is not None:
        return float(assigned)
    recovery_day = float(profile.get("recovery_day", DEFAULT_RECOVERY_DAY))
    return float(profile.get("shedding_duration_days", recovery_day))


def _select_prevalent(
    pool: list[Any],
    count: int,
    pathogen_id: str,
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> Any:
    """Choose which of the eligible hosts board, weighted by episode length.

    A prevalent sample over-represents long episodes in proportion to their
    length: a host shedding for 218 days sits in the boarding population for
    about fifteen times as much calendar time as one shedding for 15 days, so
    it is that much likelier to be caught mid-episode. The Binomial fixes how
    many board; this fixes who, with probability proportional to each host's
    own already-assigned duration. That is the prevalent-sample construction
    itself rather than an approximation to it, and it introduces no
    distribution and reinterprets no fraction: the weights are host properties
    the run already had.
    """
    size = min(count, len(pool))
    weights = np.asarray(
        [_host_duration(agent, pathogen_id, profile) for agent in pool],
        dtype=float,
    )
    positive = int((weights > 0.0).sum())
    total = float(weights[weights > 0.0].sum())
    if total <= 0.0 or positive == 0:
        return rng.choice(pool, size=size, replace=False)
    return rng.choice(
        pool, size=min(size, positive), replace=False, p=weights / total,
    )


def _draw_state(spec: BoardingSpec, rng: np.random.Generator) -> str:
    """Draw the boarding state from the two configured split coordinates.

    The presenting-but-not-presymptomatic remainder is convalescent in a
    prevalent sample and still incubating in a travelling party.
    """
    never = spec.never_symptomatic_fraction
    presenting = 1.0 - never
    share = spec.presymptomatic_share_of_presenting
    remainder = (
        STATE_INCUBATING if spec.party is not None else STATE_CONVALESCENT
    )
    states = (STATE_NEVER_SYMPTOMATIC, STATE_PRESYMPTOMATIC, remainder)
    weights = np.asarray(
        [never, presenting * share, presenting * (1.0 - share)], dtype=float,
    )
    total = float(weights.sum())
    if total <= 0.0:
        return STATE_NEVER_SYMPTOMATIC
    return str(rng.choice(states, p=weights / total))


def _state_window(
    state: str,
    incubation_days: float,
    presymptomatic_days: float,
    recovery_day: float,
    duration_days: float,
) -> tuple[float, float] | None:
    """The days-since-infection window this state occupies for this host.

    ``None`` when the window is empty — a convalescent host needs a shedding
    duration that outlasts its illness — and the caller then redraws the state.
    """
    shedding_onset = max(0.0, incubation_days - presymptomatic_days)
    low = shedding_onset
    if state == STATE_INCUBATING:
        low, high = 0.0, shedding_onset
    elif state == STATE_PRESYMPTOMATIC:
        high = incubation_days
    elif state == STATE_NEVER_SYMPTOMATIC:
        high = incubation_days + duration_days
    else:
        low = incubation_days + recovery_day
        high = incubation_days + duration_days
    if high <= low:
        return None
    return low, high


def _draw_incubation_days(
    agent: Any,
    pathogen_id: str,
    profile: dict[str, Any],
    rng: np.random.Generator,
) -> float:
    """This host's incubation period, through the natural-history owner.

    Drawn against a scratch record and stamped onto the real one by the caller,
    so ``onset_day`` later reads the value the boarding windows were built
    from.
    """
    scratch: dict[str, Any] = {"acquired_particles": 0.0}
    return float(incubation_days(agent, pathogen_id, scratch, profile, rng))


def _write_presentation_history(
    inf: dict[str, Any],
    state: str,
    incubation_days: float,
    clock: Any,
    profile: dict[str, Any],
    rng: np.random.Generator,
    age_band: str = "",
) -> None:
    """Set the presentation history the boarding state implies.

    A boarding host carries no acquisition dose, so ``will_present`` states
    what ``illness_probability`` would otherwise have decided, and the epoch
    loop reads it in place of the dose draw.
    """
    if state in (STATE_PRESYMPTOMATIC, STATE_INCUBATING):
        inf["illness"] = IllnessStatus.NOT_ILL
        inf["will_present"] = True
        return
    if state == STATE_NEVER_SYMPTOMATIC:
        inf["illness"] = IllnessStatus.NOT_ILL
        inf["will_present"] = False
        inf["presented"] = False
        inf["symptom_severity"] = _ASYMPTOMATIC_SEVERITY
        return
    inf["illness"] = IllnessStatus.RECOVERED
    inf["presented"] = True
    inf["will_present"] = True
    inf["onset_time_infected"] = int(
        round(clock.epochs_for_days(incubation_days)),
    )
    # A convalescent boarding host is past its course, so the peak it carries
    # is the state it ends on: the trajectory is not replayed backwards.
    inf["symptom_severity"] = draw_symptom_severity(profile, rng, age_band)
    inf["symptom_severity_peak"] = inf["symptom_severity"]


def _board_one_host(
    spec: BoardingSpec,
    agent: Any,
    profile: dict[str, Any],
    clock: Any,
    rng: np.random.Generator,
) -> str | None:
    """Give one host a boarding infection; returns its state, or ``None``.

    Duration read, then state, then the age conditional on both: drawing the
    age first and reading the state off the clocks would make the composition
    a silent function of natural-history constants never sourced against a
    prevalent sample.
    """
    pathogen_id = spec.pathogen_id
    duration_days = _host_duration(agent, pathogen_id, profile)
    incubation_days = _draw_incubation_days(agent, pathogen_id, profile, rng)
    recovery_day = float(agent.get_chronic_recovery_day(
        pathogen_id, int(profile.get("recovery_day", DEFAULT_RECOVERY_DAY)),
    ))
    presymptomatic_days = float(
        profile.get("presymptomatic_shedding_days", 0.0) or 0.0,
    )
    window: tuple[float, float] | None = None
    state = STATE_NEVER_SYMPTOMATIC
    for _ in range(_STATE_MAX_DRAWS):
        state = _draw_state(spec, rng)
        window = _state_window(
            state, incubation_days, presymptomatic_days,
            recovery_day, duration_days,
        )
        if window is not None:
            break
    if window is None:
        return None
    age_days = float(rng.uniform(window[0], window[1]))
    agent.infect_with_pathogen(
        pathogen_id, 0.0, 0,
        time_infected=int(round(clock.epochs_for_days(age_days))),
        rng=rng, profile=profile,
    )
    inf = agent.infections[pathogen_id]
    inf["incubation_days"] = incubation_days
    inf["boarding_state"] = state
    inf["shedding_duration_days"] = duration_days
    _write_presentation_history(
        inf, state, incubation_days, clock, profile, rng,
        host_age_band(agent),
    )
    return state


def _party_rank(seed: Any, agent: Any) -> int:
    """How close a host is to the party's first member: cabin, then zone."""
    if agent.agent_id in seed.cabin_mate_ids:
        return 0
    if seed.home_zone is not None and agent.home_zone == seed.home_zone:
        return 1
    return 2


def _select_party(
    pool: list[Any], size: int, rng: np.random.Generator,
) -> list[Any]:
    """One travelling party: a first member, then its cabin mates, then its zone.

    The cluster is in *who* boards, not in their natural history: each member
    still draws its own state and infection age below, because a shared
    exposure fixes when the party was infected far less tightly than it fixes
    that they were infected together.
    """
    if not pool or size <= 0:
        return []
    order = list(rng.permutation(len(pool)))
    first = pool[order[0]]
    rest = [pool[index] for index in order[1:]]
    rest.sort(key=lambda agent: _party_rank(first, agent))
    return [first, *rest[: size - 1]]


def _draw_party_cohort(
    spec: BoardingSpec,
    agents: list[Any],
    profile: dict[str, Any],
    clock: Any,
    rng: np.random.Generator,
) -> BoardingReport:
    """The clustered import: with ``party.probability``, one whole party."""
    party = spec.party
    drawn_by_role = dict.fromkeys(_ROLES, 0)
    composition = dict.fromkeys(_STATES, 0)
    if party is None or rng.random() >= party.probability:
        return BoardingReport(spec.pathogen_id, drawn_by_role, composition)
    pool = [
        agent for agent in agents
        if _eligible(agent, spec.pathogen_id, party.role)
    ]
    for agent in _select_party(pool, party.size, rng):
        state = _board_one_host(spec, agent, profile, clock, rng)
        if state is None:
            continue
        drawn_by_role[party.role] += 1
        composition[state] += 1
    return BoardingReport(spec.pathogen_id, drawn_by_role, composition)


def draw_boarding_cohort(
    spec: BoardingSpec,
    agents: list[Any],
    profile: dict[str, Any],
    clock: Any,
    rng: np.random.Generator,
) -> BoardingReport:
    """Draw one pathogen's boarding cohort over the eligible population.

    In prevalence mode, per role a Binomial over that role's eligible pool,
    then a duration-weighted, without-replacement choice of who: the
    measurement is a per-person probability, and the two roles carry rates
    that differ by about a factor of four, so they are drawn against their own
    populations. In party mode the draw is the all-or-nothing cluster of
    ``_draw_party_cohort``.
    """
    if spec.party is not None:
        return _draw_party_cohort(spec, agents, profile, clock, rng)
    drawn_by_role = dict.fromkeys(_ROLES, 0)
    composition = dict.fromkeys(_STATES, 0)
    prevalence_by_role = {
        ROLE_PASSENGER: spec.passenger_prevalence,
        ROLE_CREW: spec.crew_prevalence,
    }
    for role in _ROLES:
        pool = [
            agent for agent in agents
            if _eligible(agent, spec.pathogen_id, role)
        ]
        if not pool:
            continue
        count = int(rng.binomial(len(pool), prevalence_by_role[role]))
        if count <= 0:
            continue
        chosen = _select_prevalent(
            pool, count, spec.pathogen_id, profile, rng,
        )
        for agent in chosen:
            state = _board_one_host(spec, agent, profile, clock, rng)
            if state is None:
                continue
            drawn_by_role[role] += 1
            composition[state] += 1
    return BoardingReport(spec.pathogen_id, drawn_by_role, composition)


# ── Explicit seeds ───────────────────────────────────────────────────────

def _seed_pool(seed: ExplicitSeed, engine: Any) -> list[Any]:
    from orchestrator_types import LOCATION_ISOLATED

    return [
        agent for agent in engine.agents
        if _eligible(agent, seed.pathogen_id, seed.role)
        and getattr(agent, "current_location", "") != LOCATION_ISOLATED
    ]


def _apply_one_seed(
    seed: ExplicitSeed,
    engine: Any,
    epoch: int,
    rng: np.random.Generator,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Introduce one seed's hosts and return what it actually did."""
    pool = _seed_pool(seed, engine)
    count = min(seed.count, len(pool))
    dose = 0.0 if seed.dose is None else float(seed.dose)
    time_infected = int(
        round(engine.clock.epochs_for_days(seed.infection_age_days)),
    )
    chosen = (
        rng.choice(pool, size=count, replace=False) if count > 0 else []
    )
    for agent in chosen:
        agent.infect_with_pathogen(
            seed.pathogen_id, dose, epoch,
            time_infected=time_infected, rng=rng, profile=profile,
            strain_id=seed.strain_id,
        )
        if seed.dose is None:
            # A stated index case presents by construction rather than by
            # ``illness_probability`` at a fabricated acquisition dose.
            agent.infections[seed.pathogen_id]["will_present"] = True
    return {
        "pathogen": seed.pathogen_id,
        "epoch": epoch,
        "role": seed.role,
        "requested": seed.count,
        "seeded": int(count),
        "dose": dose,
        "infection_age_days": seed.infection_age_days,
        "strain": seed.strain_id,
    }


def apply_explicit_seeds(
    plan: InitiationPlan,
    engine: Any,
    epoch: int,
    rng: np.random.Generator,
    profiles: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Apply every seed scheduled for ``epoch``; records go in the manifest.

    Additive with the boarding draw by construction: a scenario that wants a
    stated index case on top of a drawn cohort writes the seed and gets both,
    and the artifact says so.
    """
    resolved = (
        profiles if profiles is not None
        else getattr(engine, "initiation_profiles", {}) or {}
    )
    records = [
        _apply_one_seed(
            seed, engine, epoch, rng, resolved.get(seed.pathogen_id, {}),
        )
        for seed in plan.seeds
        if seed.epoch == epoch
    ]
    manifest = getattr(engine, "initiation_manifest", None)
    if records and isinstance(manifest, dict):
        manifest.setdefault("seeds", []).extend(records)
    return records


# ── Run artifact ─────────────────────────────────────────────────────────

def _initiation_mode(plan: InitiationPlan) -> str:
    """Which mechanisms ran, for the run artifact."""
    if plan.legacy:
        return MODE_LEGACY
    if plan.boarding and plan.seeds:
        return MODE_BOARDING_AND_SEEDS
    if plan.boarding:
        return MODE_BOARDING
    if plan.seeds:
        return MODE_SEEDS
    return MODE_NONE


def draw_port_call(
    plan: InitiationPlan,
    engine: Any,
    epoch: int,
    profiles: dict[str, dict[str, Any]],
) -> list[BoardingReport]:
    """Board every pathogen whose port call is this epoch.

    Embarkation is not one event: a staged bundle boards its pathogens at
    successive port calls, so each draw belongs to the epoch its own spec
    names rather than to initialization alone. They share the one boarding
    stream held on the engine, so a later call does not rebase the first.
    """
    return [
        draw_boarding_cohort(
            spec, engine.agents, profiles[spec.pathogen_id],
            engine.clock, engine.boarding_rng,
        )
        for spec in plan.boarding
        if spec.epoch == epoch
    ]


def record_boarding_reports(engine: Any, reports: list[BoardingReport]) -> None:
    """Fold a port call's draws into the manifest already written."""
    manifest = getattr(engine, "initiation_manifest", None)
    if not reports or not isinstance(manifest, dict):
        return
    boarding = manifest.setdefault("boarding", {})
    for report in reports:
        boarding[report.pathogen_id] = {
            "drawn_by_role": dict(report.drawn_by_role),
            "composition": dict(report.composition),
        }


def initiation_owned_pathogens(plan: InitiationPlan) -> frozenset[str]:
    """The pathogens initiation owns, and only those.

    Ownership is per pathogen, not per run: dropping one pathogen's legacy
    introduction because a *different* pathogen has a boarding block would be
    exactly the silent default the spec's §3 forbids. A norovirus boarding
    block therefore leaves the COVID arm's ``introduction_epoch`` firing as
    before, while the pathogens named here are not introduced twice.
    """
    if plan.legacy:
        return frozenset()
    return frozenset(
        [spec.pathogen_id for spec in plan.boarding]
        + [seed.pathogen_id for seed in plan.seeds],
    )


def build_initiation_manifest(
    plan: InitiationPlan,
    reports: list[BoardingReport],
    seed_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """The run artifact's ``initiation`` block.

    Records the mode, the drawn counts by role and pathogen, both configured
    split coordinates, and the realised three-way composition, so downstream
    analysis can tell a prevalence-based run from an explicitly seeded one
    without re-deriving it.
    """
    if plan.legacy:
        return dict(LEGACY_MANIFEST)
    return {
        "mode": _initiation_mode(plan),
        "boarding": {
            report.pathogen_id: {
                "drawn_by_role": dict(report.drawn_by_role),
                "composition": dict(report.composition),
            }
            for report in reports
        },
        "boarding_mode": {spec.pathogen_id: spec.mode for spec in plan.boarding},
        "boarding_epoch": {
            spec.pathogen_id: spec.epoch for spec in plan.boarding
        },
        "party": {
            spec.pathogen_id: {
                "probability": spec.party.probability,
                "size": spec.party.size,
                "role": spec.party.role,
            }
            for spec in plan.boarding
            if spec.party is not None
        },
        "prevalence": {
            spec.pathogen_id: {
                ROLE_PASSENGER: spec.passenger_prevalence,
                ROLE_CREW: spec.crew_prevalence,
            }
            for spec in plan.boarding
        },
        "state_split": {
            spec.pathogen_id: {
                "never_symptomatic_fraction": spec.never_symptomatic_fraction,
                "presymptomatic_share_of_presenting":
                    spec.presymptomatic_share_of_presenting,
            }
            for spec in plan.boarding
        },
        "seeds": list(seed_records),
    }
