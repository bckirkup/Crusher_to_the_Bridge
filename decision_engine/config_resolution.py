"""Single resolution path for the decision runtime's configuration.

A run can describe the social layer in two places: the Picard run spec's
``social`` block (``run_spec.social_config``) and the legacy
``crusher_labs/config.yaml`` (``run_spec.legacy_cfg``). Every consumer reads
the resolved structure produced here instead of either raw source, so a
setting is read from exactly one place.

Precedence is per key, not per block:

* ``social`` — legacy ``social`` is the base; the spec's ``social`` block
  overrides it key by key (nested mappings merge recursively).
* ``wearable_monitoring``, ``multi_pathogen``, ``decision_engine`` — the
  legacy top-level block is the base; a same-named block nested under the
  spec's ``social`` overrides it key by key. These are reachable from the
  spec so that a spec-only run is fully configurable.

``ResolvedDecisionConfig.sources`` records which source supplied each block
(and each key of ``social``) so a run can report where a value came from.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Legacy top-level blocks the decision runtime consumes, overridable from the
# spec's social block under the same name.
OVERRIDABLE_BLOCKS: tuple[str, ...] = (
    "wearable_monitoring",
    "multi_pathogen",
    "decision_engine",
)

SOURCE_SPEC = "spec"
SOURCE_LEGACY = "legacy"
SOURCE_MERGED = "spec+legacy"
SOURCE_DEFAULT = "default"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` onto ``base``; ``override`` wins per key."""
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _source_of(base: dict[str, Any], override: dict[str, Any]) -> str:
    if base and override:
        return SOURCE_MERGED
    if override:
        return SOURCE_SPEC
    if base:
        return SOURCE_LEGACY
    return SOURCE_DEFAULT


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass(frozen=True)
class ResolvedDecisionConfig:
    """One resolved source of truth for the decision runtime's inputs."""

    social: dict[str, Any] = field(default_factory=dict)
    wearable_monitoring: dict[str, Any] = field(default_factory=dict)
    multi_pathogen: dict[str, Any] = field(default_factory=dict)
    decision_engine: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    def policy_config(self) -> dict[str, Any]:
        """Config mapping for :func:`decision_engine.policy.build_policies_from_config`."""
        return {"decision_engine": dict(self.decision_engine)}

    def describe_sources(self) -> str:
        return ", ".join(f"{key}={src}" for key, src in sorted(self.sources.items()))


def resolve_decision_config(run_spec: Any) -> ResolvedDecisionConfig:
    """Resolve social, wearable, multi-pathogen and policy config for a run."""
    legacy = _as_dict(getattr(run_spec, "legacy_cfg", None))
    spec_social = _as_dict(getattr(run_spec, "social_config", None))

    legacy_social = _as_dict(legacy.get("social"))
    spec_social_keys = {
        key: value for key, value in spec_social.items()
        if key not in OVERRIDABLE_BLOCKS
    }
    social = deep_merge(legacy_social, spec_social_keys)

    sources: dict[str, str] = {}
    for key in sorted(set(legacy_social) | set(spec_social_keys)):
        sources[f"social.{key}"] = _source_of(
            {key: legacy_social[key]} if key in legacy_social else {},
            {key: spec_social_keys[key]} if key in spec_social_keys else {},
        )

    blocks: dict[str, dict[str, Any]] = {}
    for name in OVERRIDABLE_BLOCKS:
        base = _as_dict(legacy.get(name))
        override = _as_dict(spec_social.get(name))
        blocks[name] = deep_merge(base, override)
        sources[name] = _source_of(base, override)

    resolved = ResolvedDecisionConfig(
        social=social,
        wearable_monitoring=blocks["wearable_monitoring"],
        multi_pathogen=blocks["multi_pathogen"],
        decision_engine=blocks["decision_engine"],
        sources=sources,
    )
    logger.debug("resolved decision config: %s", resolved.describe_sources())
    return resolved
