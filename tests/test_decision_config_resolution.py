"""Per-key resolution of decision-runtime config across spec and legacy YAML."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_engine.config_resolution import (  # noqa: E402
    SOURCE_DEFAULT,
    SOURCE_LEGACY,
    SOURCE_MERGED,
    SOURCE_SPEC,
    deep_merge,
    resolve_decision_config,
)
from decision_engine.policy import (  # noqa: E402
    RuleBasedPolicy,
    ThresholdBeliefPolicy,
    build_policies_from_config,
)


def _spec(legacy=None, social=None):
    return SimpleNamespace(legacy_cfg=legacy or {}, social_config=social or {})


def test_deep_merge_is_recursive_and_override_wins():
    base = {"a": {"x": 1, "y": 2}, "b": 1}
    over = {"a": {"y": 20, "z": 30}, "c": 3}
    merged = deep_merge(base, over)
    assert merged == {"a": {"x": 1, "y": 20, "z": 30}, "b": 1, "c": 3}
    assert base == {"a": {"x": 1, "y": 2}, "b": 1}


def test_social_only_in_one_source_is_read_unchanged():
    legacy_only = resolve_decision_config(
        _spec(legacy={"social": {"agent_granularity": "per_class"}}),
    )
    assert legacy_only.social == {"agent_granularity": "per_class"}
    assert legacy_only.sources["social.agent_granularity"] == SOURCE_LEGACY

    spec_only = resolve_decision_config(_spec(social={"cruise_id": "7"}))
    assert spec_only.social == {"cruise_id": "7"}
    assert spec_only.sources["social.cruise_id"] == SOURCE_SPEC


def test_social_precedence_is_per_key_not_whole_block():
    resolved = resolve_decision_config(_spec(
        legacy={"social": {
            "agent_granularity": "per_class",
            "telemetry": {"decision_detail": True, "extra": 1},
        }},
        social={"cruise_id": "3", "telemetry": {"decision_detail": False}},
    ))
    assert resolved.social["agent_granularity"] == "per_class"
    assert resolved.social["cruise_id"] == "3"
    assert resolved.social["telemetry"] == {"decision_detail": False, "extra": 1}
    assert resolved.sources["social.agent_granularity"] == SOURCE_LEGACY
    assert resolved.sources["social.cruise_id"] == SOURCE_SPEC
    assert resolved.sources["social.telemetry"] == SOURCE_MERGED


def test_legacy_blocks_are_overridable_from_spec_social():
    legacy = {
        "wearable_monitoring": {"enabled": True, "class_device_map": {"crew": "oura"}},
        "multi_pathogen": {"immunocompromised_fraction": 0.05, "enable_coinfection": True},
        "decision_engine": {
            "population_policy": "threshold_belief",
            "threshold_belief": {"severity_report_threshold": 0.35},
        },
    }
    social = {
        "wearable_monitoring": {"class_device_map": {"crew": "whoop"}},
        "multi_pathogen": {"immunocompromised_fraction": 0.2},
        "decision_engine": {"population_policy": "noop"},
    }
    resolved = resolve_decision_config(_spec(legacy=legacy, social=social))

    assert resolved.wearable_monitoring == {
        "enabled": True, "class_device_map": {"crew": "whoop"},
    }
    assert resolved.multi_pathogen["immunocompromised_fraction"] == 0.2
    assert resolved.multi_pathogen["enable_coinfection"] is True
    assert resolved.decision_engine["population_policy"] == "noop"
    assert resolved.decision_engine["threshold_belief"] == {"severity_report_threshold": 0.35}
    for name in ("wearable_monitoring", "multi_pathogen", "decision_engine"):
        assert resolved.sources[name] == SOURCE_MERGED
        assert name not in resolved.social

    _cmd, _med, pop = build_policies_from_config(resolved.policy_config())
    assert isinstance(pop, RuleBasedPolicy)


def test_legacy_only_blocks_keep_legacy_values():
    legacy = {"decision_engine": {"threshold_belief": {"trust_report_floor": 0.9}}}
    resolved = resolve_decision_config(_spec(legacy=legacy, social={"cruise_id": "1"}))
    assert resolved.sources["decision_engine"] == SOURCE_LEGACY
    assert resolved.sources["wearable_monitoring"] == SOURCE_DEFAULT
    _cmd, _med, pop = build_policies_from_config(resolved.policy_config())
    assert isinstance(pop, ThresholdBeliefPolicy)
    assert pop.trust_report_floor == 0.9


def test_run_spec_without_legacy_or_social_resolves_to_defaults():
    resolved = resolve_decision_config(SimpleNamespace())
    assert resolved.social == {}
    assert resolved.decision_engine == {}
    assert all(src == SOURCE_DEFAULT for src in resolved.sources.values())
