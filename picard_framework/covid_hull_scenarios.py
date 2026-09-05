"""The two COVID hull scenarios, as run specifications.

``data/scenarios/covid_hull_scenarios.json`` holds the event geometry of the
Diamond Princess and Greg Mortimer outbreaks — how long each lasted, who was
aboard, when passengers were confined, and which simulated day the testing
campaign's first recorded day falls on. This module turns one of those records
into a Picard run-spec mapping, and nothing else: every number it emits comes
from the record, and the biology comes from the shared ``sars_cov2_resp``
profile, so the two hulls differ only in their event.

It also carries the train/test split as data. ``training_scenario_id`` and
``held_out_scenario_ids`` read the split the fit spec fixed in writing before
any of this existed, and :func:`assert_fit_target` refuses a fit against
anything but the training hull, so a later fitting run cannot quietly enlarge
its training set.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from engines.sim_clock import SimClock
from picard_framework.pathogen_overrides import isolate_arm_overrides
from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIO_DATA_REL = os.path.join("data", "scenarios", "covid_hull_scenarios.json")
BUNDLE_ID = "active_profiles"
TRAINING = "training"
HELD_OUT = "held_out"
_SPLIT_ROLES = (TRAINING, HELD_OUT)
_CAMPAIGN_FILE_REL = os.path.join(
    "data", "observation", "covid_testing_campaigns.json",
)


def scenario_data_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(repo_root, SCENARIO_DATA_REL)


@dataclass(frozen=True)
class RoleClass:
    """One agent class of the hull's population, with its head count."""

    class_id: str
    role_group: str
    count: int


@dataclass(frozen=True)
class HullScenario:
    """One replayed hull: its geometry, its calendar and its split role."""

    scenario_id: str
    hull_name: str
    split_role: str
    pathogen_id: str
    platform_id: str
    duration_days: int
    epoch_duration_hours: float
    clock_mode: str
    population_total: int
    role_classes: tuple[RoleClass, ...]
    campaign_id: str
    campaign_start_day: int
    scheduled_protocols: tuple[Mapping[str, Any], ...] = ()
    explicit_seeds: tuple[Mapping[str, Any], ...] = ()
    agent_profile_bundle: str | None = None
    provenance: tuple[Mapping[str, Any], ...] = field(default=(), repr=False)
    refusals: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if self.split_role not in _SPLIT_ROLES:
            raise ValueError(
                f"{self.scenario_id}: split_role {self.split_role!r} is not one "
                f"of {_SPLIT_ROLES}",
            )
        if self.duration_days <= 0:
            raise ValueError(f"{self.scenario_id}: duration_days must be positive")
        if self.epoch_duration_hours <= 0:
            raise ValueError(
                f"{self.scenario_id}: epoch_duration_hours must be positive",
            )
        head_count = sum(rc.count for rc in self.role_classes)
        if head_count != self.population_total:
            raise ValueError(
                f"{self.scenario_id}: role classes total {head_count} but the "
                f"population is {self.population_total}",
            )
        if self.campaign_start_day + 1 > self.duration_days:
            raise ValueError(
                f"{self.scenario_id}: campaign starts on day "
                f"{self.campaign_start_day} of a {self.duration_days}-day event",
            )

    @property
    def is_training(self) -> bool:
        return self.split_role == TRAINING

    @property
    def num_epochs(self) -> int:
        """Epochs the declared duration comes to at the declared epoch length.

        The duration is stated in days and converted here rather than being
        authored in epochs, so the same record means the same four weeks at any
        epoch length.
        """
        clock = SimClock(
            epoch_duration_hours=float(self.epoch_duration_hours),
            mode=self.clock_mode,
        )
        return int(round(clock.epochs_for_days(self.duration_days)))

    def role_fraction(self, role_group: str) -> float:
        matched = sum(
            rc.count for rc in self.role_classes if rc.role_group == role_group
        )
        return matched / float(self.population_total)

    def _agent_classes(self) -> list[dict[str, Any]]:
        return [
            {
                "class_id": rc.class_id,
                "role_group": rc.role_group,
                "count": rc.count,
                "fraction": rc.count / float(self.population_total),
                "home_zone_preference": (
                    "PC_" if rc.role_group == "passenger" else "CC_"
                ),
            }
            for rc in self.role_classes
        ]

    def config_overrides(self) -> dict[str, Any]:
        """The legacy-config blocks this hull's geometry replaces."""
        return {
            "num_epochs": self.num_epochs,
            "epoch_duration_hours": self.epoch_duration_hours,
            "natural_history_clock": self.clock_mode,
            "voyage": {
                "epoch_duration_hours": self.epoch_duration_hours,
                "total_epochs": self.num_epochs,
            },
            "ship_graph": {
                "num_agents": self.population_total,
                "agent_roles": {
                    "passenger_fraction": self.role_fraction("passenger"),
                    "crew_fraction": self.role_fraction("crew"),
                },
                "agent_classes": self._agent_classes(),
            },
            "initiation": {"explicit_seeds": [dict(s) for s in self.explicit_seeds]},
            "scenario_schedule": {
                "protocols": [
                    {
                        "protocol_id": entry["protocol_id"],
                        "start_day": int(entry["start_day"]),
                        "end_day": entry.get("end_day"),
                    }
                    for entry in self.scheduled_protocols
                ],
            },
            "syndromic": {
                "testing_campaigns": {
                    "campaign_file": _CAMPAIGN_FILE_REL,
                    "campaigns": [
                        {
                            "campaign_id": self.campaign_id,
                            "start_day": self.campaign_start_day,
                        },
                    ],
                },
            },
        }

    def pathogen_overrides(self) -> dict[str, Any]:
        """Isolate the hull's one pathogen and hand initiation the index case.

        A replayed outbreak is one pathogen, so every other member of the
        active bundle is removed: leaving norovirus and influenza circulating
        would feed sick calls and tests — the very channels the fit is scored
        on — from an arm the event record has nothing to say about. The
        profile's own ``initial_infected`` is nulled because the scenario's
        explicit seed owns the introduction; the engine refuses to hold both.
        """
        return isolate_arm_overrides(
            BUNDLE_ID,
            self.pathogen_id,
            {self.pathogen_id: {"initial_infected": None}},
        ) or {}

    def to_run_spec_dict(
        self,
        *,
        random_seed: int = 42,
        num_epochs: int | None = None,
        write_ground_truth: bool = False,
    ) -> dict[str, Any]:
        """A Picard run-spec mapping for this hull.

        ``num_epochs`` shortens a run for a smoke test; leaving it unset runs
        the whole declared event. Ground truth is off by default because the
        truth channel is barred from scoring — a scored run has no business
        reading it.
        """
        overrides = self.config_overrides()
        overrides["random_seed"] = random_seed
        if num_epochs is not None:
            overrides["num_epochs"] = int(num_epochs)
            overrides["voyage"]["total_epochs"] = int(num_epochs)
        spec: dict[str, Any] = {
            "schema_version": "1.0.0",
            "catalog": {
                "platform_id": self.platform_id,
                "pathogen_bundle_id": BUNDLE_ID,
            },
            "run": {
                "random_seed": random_seed,
                "num_epochs": overrides["num_epochs"],
                "write_ground_truth": write_ground_truth,
            },
            "config_overrides": overrides,
            "pathogen_overrides": self.pathogen_overrides(),
        }
        if self.agent_profile_bundle:
            spec["social"] = {"agent_profile_bundle": self.agent_profile_bundle}
        return spec


@dataclass(frozen=True)
class HullScenarioSet:
    """Every hull scenario of the COVID arm, plus the fixed split."""

    scenarios: Mapping[str, HullScenario]
    split_source: str

    def __getitem__(self, scenario_id: str) -> HullScenario:
        try:
            return self.scenarios[scenario_id]
        except KeyError:
            known = ", ".join(sorted(self.scenarios))
            raise KeyError(
                f"unknown COVID hull scenario {scenario_id!r}; known: {known}",
            ) from None

    def ids_with_role(self, split_role: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                sid
                for sid, scenario in self.scenarios.items()
                if scenario.split_role == split_role
            ),
        )

    @property
    def training_scenario_id(self) -> str:
        training = self.ids_with_role(TRAINING)
        if len(training) != 1:
            raise ValueError(
                "the COVID arm fits one training hull; the split names "
                f"{len(training)}: {training}",
            )
        return training[0]

    @property
    def held_out_scenario_ids(self) -> tuple[str, ...]:
        return self.ids_with_role(HELD_OUT)

    def assert_fit_target(self, scenario_id: str) -> HullScenario:
        """The scenario, if it is the training hull; otherwise a refusal.

        The split is fixed in writing before the fit, so fitting against a
        held-out hull is not a judgement call to be made at the call site.
        """
        scenario = self[scenario_id]
        if not scenario.is_training:
            raise ValueError(
                f"{scenario_id} is {scenario.split_role} in the fixed split "
                f"({self.split_source}); Θ is fitted on "
                f"{self.training_scenario_id} alone and held-out hulls are "
                "only scored",
            )
        return scenario


def _role_classes(raw: Sequence[Mapping[str, Any]]) -> tuple[RoleClass, ...]:
    return tuple(
        RoleClass(
            class_id=str(entry["class_id"]),
            role_group=str(entry["role_group"]),
            count=int(entry["count"]),
        )
        for entry in raw
    )


def _scenario_from_dict(raw: Mapping[str, Any]) -> HullScenario:
    clock = raw.get("clock") or {}
    campaign = raw.get("testing_campaign") or {}
    population = raw.get("population") or {}
    initiation = raw.get("initiation") or {}
    return HullScenario(
        scenario_id=str(raw["scenario_id"]),
        hull_name=str(raw.get("hull_name", raw["scenario_id"])),
        split_role=str(raw["split_role"]),
        pathogen_id=str(raw["pathogen_id"]),
        platform_id=str(raw["platform_id"]),
        duration_days=int(raw["duration_days"]),
        epoch_duration_hours=float(clock.get("epoch_duration_hours", 1)),
        clock_mode=str(clock.get("natural_history_clock", "hours")),
        population_total=int(population["total"]),
        role_classes=_role_classes(raw.get("role_classes") or ()),
        campaign_id=str(campaign["campaign_id"]),
        campaign_start_day=int(campaign.get("start_day", 0)),
        scheduled_protocols=tuple(
            dict(entry) for entry in raw.get("scheduled_protocols") or ()
        ),
        explicit_seeds=tuple(
            dict(entry) for entry in initiation.get("explicit_seeds") or ()
        ),
        agent_profile_bundle=raw.get("agent_profile_bundle") or None,
        provenance=tuple(dict(entry) for entry in raw.get("provenance") or ()),
        refusals=tuple(str(entry) for entry in raw.get("refusals") or ()),
    )


def load_hull_scenarios(
    path: str | None = None,
    *,
    repo_root: str = REPO_ROOT,
) -> HullScenarioSet:
    """Load the hull scenario records and check them against their own split."""
    resolved = path or scenario_data_path(repo_root)
    with validated_open(
        resolved, allowed_roots=(repo_root,), encoding="utf-8",
    ) as fh:
        raw = json.load(fh)
    scenarios = {
        str(entry["scenario_id"]): _scenario_from_dict(entry)
        for entry in raw.get("scenarios") or ()
    }
    split = raw.get("split") or {}
    scenario_set = HullScenarioSet(
        scenarios=scenarios,
        split_source=str(split.get("fixed_by", "")),
    )
    _check_split_agrees(scenario_set, split)
    return scenario_set


def _check_split_agrees(
    scenario_set: HullScenarioSet,
    split: Mapping[str, Any],
) -> None:
    """Refuse a file whose split block and scenario roles disagree.

    The split is stated twice on purpose — once as a list and once per
    scenario — so that editing one and not the other is a load error rather
    than a silently changed training set.
    """
    for key, role in ((TRAINING, TRAINING), (HELD_OUT, HELD_OUT)):
        declared = tuple(sorted(str(sid) for sid in split.get(key) or ()))
        actual = scenario_set.ids_with_role(role)
        if declared != actual:
            raise ValueError(
                f"split.{key} lists {declared} but the scenarios with "
                f"split_role {role!r} are {actual}",
            )


def build_run_spec_dict(
    scenario_id: str,
    *,
    random_seed: int = 42,
    num_epochs: int | None = None,
    write_ground_truth: bool = False,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Convenience wrapper: load the records and emit one hull's run spec."""
    scenario = load_hull_scenarios(repo_root=repo_root)[scenario_id]
    return scenario.to_run_spec_dict(
        random_seed=random_seed,
        num_epochs=num_epochs,
        write_ground_truth=write_ground_truth,
    )
