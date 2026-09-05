"""The scored observables of the COVID arm, and the side of the split each is on.

``data/observation/covid_fit_targets.json`` holds one row per anchor of
``docs/proposals/covid_trajectory_fit_spec.md`` section 3: what an observer of
the real event held, where it was published, and whether the anchor is training
or held out. This module loads those rows and enforces the split.

Enforcement is the point. :meth:`FitTargets.objective_anchors` hands back only
the rows the fit spec nominated as objective terms, and
:meth:`FitTargets.assert_fittable` raises on anything else, so a held-out anchor
cannot be reached from inside a fit even by name. The held-out rows are readable
only through :meth:`FitTargets.held_out`, which is called after a value of Theta
has been fixed and never before.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS_REL = os.path.join("data", "observation", "covid_fit_targets.json")
TRAINING = "training"
HELD_OUT = "held_out"


def targets_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(repo_root, TARGETS_REL)


@dataclass(frozen=True)
class FitTarget:
    """One published observable, with the split side it belongs to."""

    anchor_id: str
    split_role: str
    scenario_id: str | None
    observable: str
    channel: str
    values: dict[str, Any]
    source: str
    evidence_grade: str
    scorable: bool
    notes: str

    @property
    def is_training(self) -> bool:
        return self.split_role == TRAINING


@dataclass(frozen=True)
class FitTargets:
    """The anchor set, with the split it was fixed under."""

    anchors: tuple[FitTarget, ...]
    split: dict[str, Any]

    def by_id(self, anchor_id: str) -> FitTarget:
        for anchor in self.anchors:
            if anchor.anchor_id == str(anchor_id):
                return anchor
        raise KeyError(f"no fit target {anchor_id!r}")

    def training(self) -> tuple[FitTarget, ...]:
        return tuple(a for a in self.anchors if a.split_role == TRAINING)

    def held_out(self) -> tuple[FitTarget, ...]:
        """Held-out rows. Only ever read after Theta has been fixed."""
        return tuple(a for a in self.anchors if a.split_role == HELD_OUT)

    @property
    def objective_anchor_ids(self) -> tuple[str, ...]:
        return tuple(str(a) for a in self.split.get("fitted_against", ()))

    def objective_anchors(self) -> tuple[FitTarget, ...]:
        """The rows the objective is allowed to sum over, and no others."""
        return tuple(
            self.assert_fittable(anchor_id)
            for anchor_id in self.objective_anchor_ids
        )

    def assert_fittable(self, anchor_id: str) -> FitTarget:
        """Return the anchor, refusing anything the split did not nominate.

        The refusal is the split doing its work: the training/held-out
        assignment was fixed in writing before this code existed
        (covid_trajectory_fit_spec.md section 7), so a fit that wants one
        more anchor has to change the declaration in data and say so, not
        pick the row up at runtime.
        """
        anchor = self.by_id(anchor_id)
        if anchor.split_role != TRAINING:
            raise ValueError(
                f"{anchor.anchor_id} is {anchor.split_role}, not a fit "
                "target: the COVID split was fixed before implementation "
                "and Theta is fitted on Diamond Princess alone",
            )
        if anchor.anchor_id not in self.objective_anchor_ids:
            raise ValueError(
                f"{anchor.anchor_id} is a training-side diagnostic, not an "
                "objective term: it is reported, and reporting it is what "
                "makes it a test of the mechanism rather than a fitted-to "
                "quantity",
            )
        return anchor


def _target_from_row(row: dict[str, Any]) -> FitTarget:
    return FitTarget(
        anchor_id=str(row["anchor_id"]),
        split_role=str(row["split_role"]),
        scenario_id=(
            None if row.get("scenario_id") is None
            else str(row["scenario_id"])
        ),
        observable=str(row["observable"]),
        channel=str(row["channel"]),
        values=dict(row.get("values") or {}),
        source=str(row["source"]),
        evidence_grade=str(row["evidence_grade"]),
        scorable=bool(row.get("scorable", True)),
        notes=str(row.get("notes", "")),
    )


def load_fit_targets(repo_root: str = REPO_ROOT) -> FitTargets:
    """Load the anchor set from data, refusing an undeclared split."""
    with validated_open(
        targets_path(repo_root), allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        payload = json.load(handle)
    split = dict(payload.get("split") or {})
    if not split.get("fixed_before_implementation"):
        raise ValueError(
            "covid_fit_targets.json does not declare its split as fixed "
            "before implementation; the defensibility claim of this arm "
            "rests on that declaration",
        )
    anchors = tuple(_target_from_row(row) for row in payload["anchors"])
    _assert_split_consistent(anchors, split)
    return FitTargets(anchors=anchors, split=split)


def _assert_split_consistent(
    anchors: tuple[FitTarget, ...],
    split: dict[str, Any],
) -> None:
    """The rows and the split declaration have to agree, exactly."""
    declared_training = tuple(str(a) for a in split.get("training_anchors", ()))
    declared_held_out = tuple(str(a) for a in split.get("held_out_anchors", ()))
    actual_training = tuple(a.anchor_id for a in anchors if a.is_training)
    actual_held_out = tuple(
        a.anchor_id for a in anchors if a.split_role == HELD_OUT
    )
    if actual_training != declared_training:
        raise ValueError(
            f"training rows {actual_training} disagree with the declared "
            f"split {declared_training}",
        )
    if actual_held_out != declared_held_out:
        raise ValueError(
            f"held-out rows {actual_held_out} disagree with the declared "
            f"split {declared_held_out}",
        )
    unknown = set(split.get("fitted_against", ())) - set(declared_training)
    if unknown:
        raise ValueError(
            f"objective terms {sorted(unknown)} are not training anchors",
        )
