"""Project simulator incubation profiles onto sentinel delay specs.

The simulator and the sentinel estimator both need to know how long after
exposure a case appears, and until this module they said it separately: the
pathogen profile (``data/pathogens/*.json``, days, dose- and host-conditioned,
drawn per infection) and the sentinel delay catalog
(``data/incubation_distributions.json``, hours, pathogen-level). Nothing failed
when they disagreed, and they did.

The profile is the source of truth for *incubation*. This module projects it
into the catalog's units and family so the catalog entry can be checked against
it (``incubation_drift``), and so an analysis that wants the simulator's own
kernel can build one directly (``incubation_delay_for_profile``).

Two things are deliberately **not** projected. Generation and shedding kernels
have no counterpart on the profile — a generation interval is not an incubation
period, and inventing one from the other would be worse than keeping the
sentinel's own literature values. And the profile's dose conditioning cannot be
represented by a single pathogen-level kernel at all: the projection is the
kernel of a host at the profile's reference dose, so a run whose realized doses
sit far from that reference has a narrower or wider true kernel than the one the
estimator uses (see ``docs/history/incubation_reconciliation_plan.md``, R2).
"""

from __future__ import annotations

import math
import os
from typing import Any, Mapping

from engines.incubation import (
    DEFAULT_DISPERSION,
    DEFAULT_MAX_DAYS,
    DEFAULT_MIN_DAYS,
    DISTRIBUTION_LOGNORMAL,
)
from picard_framework.analysis.sentinel.incubation import (
    LOGNORMAL,
    DelayDistribution,
    lognormal_delay,
)
from picard_framework.pathogen_overrides import load_pathogen_bundle

HOURS_PER_DAY = 24.0

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

#: The bundle the shipped simulator runs on, and so the source of truth the
#: catalog is checked against.
ACTIVE_PROFILES_PATH = os.path.join(
    _REPO_ROOT,
    "data",
    "pathogens",
    "active_profiles.json",
)

#: Relative tolerance for the drift check. Catalog values are rounded for
#: readability, so exact equality would fail on the sixth decimal of sigma.
DRIFT_RTOL = 1e-4

_PATHOGEN_ID_KEY = "pathogen_id"


def project_incubation(
    incubation: Mapping[str, Any],
    *,
    pathogen_id: str,
) -> dict[str, Any]:
    """Profile ``incubation`` block -> sentinel delay spec, in hours.

    ``median_days``/``dispersion`` are the lognormal median and geometric
    standard deviation, so the catalog's ``sigma`` is ``log(dispersion)`` and
    the catalog's ``median_hours`` is the median in days times 24. The profile's
    ``min_days``/``max_days`` are the truncation bounds the simulator clamps
    each draw to, and they project onto the catalog's support the same way.
    """
    distribution = str(incubation.get("distribution") or DISTRIBUTION_LOGNORMAL)
    if distribution != DISTRIBUTION_LOGNORMAL:
        raise ValueError(
            f"{pathogen_id}: cannot project a {distribution!r} incubation onto "
            f"the sentinel catalog, which is lognormal-only; a gamma profile "
            f"needs an explicit moment-matched entry and a recorded rationale",
        )
    median_days = incubation.get("median_days")
    if median_days is None:
        raise ValueError(f"{pathogen_id}: incubation has no median_days")
    dispersion = float(incubation.get("dispersion") or DEFAULT_DISPERSION)
    if dispersion <= 1.0:
        raise ValueError(
            f"{pathogen_id}: lognormal dispersion must exceed 1 "
            f"(it is a geometric standard deviation): {dispersion}",
        )
    max_days = float(incubation.get("max_days") or DEFAULT_MAX_DAYS)
    min_days = incubation.get("min_days")
    return {
        "family": LOGNORMAL,
        "median_hours": float(median_days) * HOURS_PER_DAY,
        "sigma": math.log(dispersion),
        "min_hours": float(
            DEFAULT_MIN_DAYS if min_days is None else min_days,
        )
        * HOURS_PER_DAY,
        "max_hours": max_days * HOURS_PER_DAY,
    }


def incubation_delay_for_profile(
    profile: Mapping[str, Any],
    *,
    epoch_hours: float = 1.0,
) -> DelayDistribution:
    """The simulator's own incubation kernel, on the analysis epoch grid.

    For an analysis that would rather use the profile than the catalog. At the
    profile's reference dose: see the module docstring on what dose
    conditioning a pathogen-level kernel cannot carry.
    """
    pathogen_id = str(profile.get("pathogen_id") or "?")
    incubation = profile.get("incubation")
    if not isinstance(incubation, Mapping):
        raise ValueError(f"{pathogen_id}: profile carries no incubation block")
    spec = project_incubation(incubation, pathogen_id=pathogen_id)
    return lognormal_delay(
        name=f"{pathogen_id}.incubation",
        median_hours=spec["median_hours"],
        sigma=spec["sigma"],
        epoch_hours=epoch_hours,
        min_hours=spec["min_hours"],
        max_hours=spec["max_hours"],
    )


def active_profiles(path: str | None = None) -> dict[str, dict[str, Any]]:
    """``pathogen_id -> profile`` from the active bundle (or a given one)."""
    return load_pathogen_bundle(path or ACTIVE_PROFILES_PATH)


def _field_drift(
    label: str,
    entry: Mapping[str, Any],
    projected: Mapping[str, Any],
) -> list[str]:
    """Per-field comparison of one catalog incubation block to its projection."""
    drift: list[str] = []
    for field, want in projected.items():
        got = entry.get(field)
        if isinstance(want, str):
            if str(got) != want:
                drift.append(f"{label}.{field}: catalog {got!r} != profile {want!r}")
            continue
        if got is None:
            drift.append(f"{label}.{field}: missing from catalog (profile {want})")
            continue
        if not math.isclose(float(got), float(want), rel_tol=DRIFT_RTOL):
            drift.append(
                f"{label}.{field}: catalog {float(got)} != profile {float(want)}",
            )
    return drift


def incubation_drift(
    catalog: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    """Every way the catalog's incubation entries disagree with the profiles.

    Only entries that declare ``pathogen_id`` are checked: the catalog also
    carries pathogens the simulator does not model (the port-resolution
    counter-example), and those are not drift. An entry naming a pathogen that
    the bundle does not have, or a bundle pathogen whose profile has no
    incubation block, *is* drift — both are ways for the link to rot silently.
    """
    drift: list[str] = []
    for name, entry in sorted((catalog.get("distributions") or {}).items()):
        pathogen_id = entry.get(_PATHOGEN_ID_KEY)
        if not pathogen_id:
            continue
        profile = profiles.get(str(pathogen_id))
        if profile is None:
            drift.append(
                f"{name}: declares pathogen_id {pathogen_id!r}, which the "
                f"bundle does not define",
            )
            continue
        incubation = profile.get("incubation")
        if not isinstance(incubation, Mapping):
            drift.append(
                f"{name}: profile {pathogen_id!r} has no incubation block, so "
                f"the catalog entry is unanchored",
            )
            continue
        drift.extend(
            _field_drift(
                name,
                entry.get("incubation") or {},
                project_incubation(incubation, pathogen_id=str(pathogen_id)),
            ),
        )
    return tuple(drift)
