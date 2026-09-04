"""
Apply Picard run-spec pathogen overrides onto catalog bundle profiles.

The run-spec JSON is the experiment contract: ``catalog.pathogen_bundle_id``
selects the baseline bundle, and ``pathogen_overrides`` patches it at
``PicardRunSpec.from_picard_json`` construction time. Resolved profiles are
stored on the run spec and injected into runtime config — they are not
re-read from disk during simulation.
"""

from __future__ import annotations

import json
import os
from typing import Any

from picard_framework.catalog.registry import CatalogRegistry
from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESERVED_OVERRIDE_KEYS = frozenset({"remove", "add"})


def deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *patch* into a copy of *base*."""
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_pathogen_bundle(path: str) -> dict[str, dict[str, Any]]:
    """Load a pathogen bundle JSON file into ``pathogen_id -> profile``."""
    with validated_open(path, allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        data = json.load(fh)
    profiles: dict[str, dict[str, Any]] = {}
    for entry in data.get("pathogens", []):
        pid = entry.get("pathogen_id")
        if not pid:
            raise ValueError("pathogen bundle entry missing pathogen_id")
        profiles[str(pid)] = dict(entry)
    return profiles


def isolate_arm_overrides(
    bundle_id: str,
    pathogen_id: str,
    overrides: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extend an arm's ``remove`` list to every other pathogen in its bundle.

    A campaign arm names the one pathogen it studies, so co-circulation of
    anything else in the bundle is not part of its contract. Deriving the
    removals from the bundle rather than from a hand-written list keeps an
    arm isolated when a pathogen is added to the bundle it draws on.
    """
    registry = CatalogRegistry.from_repo(REPO_ROOT)
    try:
        path = registry.resolve_pathogen_bundle(bundle_id)
    except KeyError:
        return overrides
    others = [
        pid for pid in load_pathogen_bundle(path) if pid != str(pathogen_id)
    ]
    declared = list((overrides or {}).get("remove", []))
    merged = declared + [pid for pid in others if pid not in declared]
    return {**(overrides or {}), "remove": merged}


def apply_pathogen_overrides(
    base_profiles: dict[str, dict[str, Any]],
    overrides: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Return resolved profiles after applying run-spec overrides.

    Override shape::

        {
          "remove": ["sars_cov2_resp"],
          "add": [{...full profile...}],
          "norwalk_gi": {"initial_infected": 3},
          "sars_cov2_resp": {"introduction_epoch": 10}
        }

    ``remove`` drops pathogens from the active set. ``add`` appends or
    replaces full profile dicts (must include ``pathogen_id``). Remaining
    keys are treated as per-pathogen deep patches against the bundle entry.
    """
    if not overrides:
        return {pid: dict(prof) for pid, prof in base_profiles.items()}

    resolved = {pid: dict(prof) for pid, prof in base_profiles.items()}

    for pid in overrides.get("remove", []):
        resolved.pop(str(pid), None)

    for patch in overrides.get("add", []):
        if not isinstance(patch, dict):
            raise ValueError("pathogen_overrides.add entries must be objects")
        pid = patch.get("pathogen_id")
        if not pid:
            raise ValueError("pathogen_overrides.add entry missing pathogen_id")
        resolved[str(pid)] = dict(patch)

    for key, patch in overrides.items():
        if key in RESERVED_OVERRIDE_KEYS:
            continue
        if not isinstance(patch, dict):
            raise ValueError(
                f"pathogen_overrides.{key} must be an object patch, got {type(patch).__name__}",
            )
        pid = str(key)
        if pid not in resolved:
            raise ValueError(
                f"pathogen_overrides patch targets unknown pathogen_id '{pid}'",
            )
        resolved[pid] = deep_merge_dict(resolved[pid], patch)

    return resolved
