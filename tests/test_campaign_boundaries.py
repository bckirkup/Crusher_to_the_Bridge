"""Boundaries of campaign parameter mapping, shard gating, and metrics helpers."""

from __future__ import annotations

import copy
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    _campaign_gate,
    _campaign_parameters,
    _copy_present,
    _detection_epochs,
    generate_tier_runs,
    load_manifest,
)


def _gate_args(**overrides: object) -> SimpleNamespace:
    base = {
        "limit": None,
        "resume": False,
        "retry_failed": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestCopyPresent:
    def test_filter_efficiency_grades_into_campaign_parameters(self) -> None:
        efficiencies = [0.5, 0.8, 0.95]
        seen = []
        for eff in efficiencies:
            params = _campaign_parameters(
                tier_id="t2",
                run_id="r",
                platform="destroyer_baseline",
                bundle="norovirus",
                seed=1,
                epochs=24,
                num_agents=20,
                config_overrides={"hvac": {"filter_efficiency": eff}},
            )
            seen.append(params["filter_efficiency"])
        assert seen == efficiencies

    def test_oa_fraction_maps_to_outdoor_air_fraction(self) -> None:
        params = _campaign_parameters(
            tier_id="t2",
            run_id="r",
            platform="destroyer_baseline",
            bundle="norovirus",
            seed=1,
            epochs=24,
            num_agents=20,
            config_overrides={"hvac": {"oa_fraction": 0.4}},
        )
        assert params["outdoor_air_fraction"] == pytest.approx(0.4)
        assert "oa_fraction" not in params

    def test_explicit_factor_wins_over_config_for_transport_engine(self) -> None:
        params = _campaign_parameters(
            tier_id="t2",
            run_id="r",
            platform="destroyer_baseline",
            bundle="norovirus",
            seed=1,
            epochs=24,
            num_agents=20,
            transport_engine="native",
            config_overrides={"hvac": {"transport_engine": "contamx"}},
        )
        assert params["transport_engine"] == "native"

    def test_decay_rate_does_not_move_filter_efficiency(self) -> None:
        base = _campaign_parameters(
            tier_id="t2",
            run_id="r",
            platform="destroyer_baseline",
            bundle="norovirus",
            seed=1,
            epochs=24,
            num_agents=20,
            config_overrides={"hvac": {"filter_efficiency": 0.8}},
        )
        other = _campaign_parameters(
            tier_id="t2",
            run_id="r",
            platform="destroyer_baseline",
            bundle="norovirus",
            seed=1,
            epochs=24,
            num_agents=20,
            config_overrides={
                "hvac": {"filter_efficiency": 0.8, "natural_decay_rate": 9.9},
            },
        )
        assert other["filter_efficiency"] == base["filter_efficiency"]
        assert other["decay_rate"] == pytest.approx(9.9)

    def test_copy_present_skips_missing_source_keys(self) -> None:
        params: dict[str, object] = {"keep": 1}
        _copy_present(params, {}, (("filter_efficiency", "filter_efficiency"),))
        assert params == {"keep": 1}


class TestCampaignGate:
    def test_shard_assignment_is_partition(self) -> None:
        args = _gate_args()
        shard_count = 3
        assigned = {0: [], 1: [], 2: []}
        for index in range(9):
            for shard in range(shard_count):
                gate = _campaign_gate(
                    global_index=index,
                    run_id=f"r{index}",
                    args=args,
                    shard_count=shard_count,
                    shard_index=shard,
                    executed=0,
                    done=set(),
                    retry_only=None,
                    uploader=None,
                )
                if gate == "run":
                    assigned[shard].append(index)
        assert assigned[0] == [0, 3, 6]
        assert assigned[1] == [1, 4, 7]
        assert assigned[2] == [2, 5, 8]

    def test_done_run_is_skipped_not_ignored(self) -> None:
        gate = _campaign_gate(
            global_index=0,
            run_id="done_run",
            args=_gate_args(),
            shard_count=None,
            shard_index=0,
            executed=0,
            done={"done_run"},
            retry_only=None,
            uploader=None,
        )
        assert gate == "skip"

    def test_limit_stops_after_executed_budget(self) -> None:
        gate = _campaign_gate(
            global_index=4,
            run_id="next",
            args=_gate_args(limit=2),
            shard_count=None,
            shard_index=0,
            executed=2,
            done=set(),
            retry_only=None,
            uploader=None,
        )
        assert gate == "stop"


class TestDetectionEpochs:
    def test_detection_and_confirmation_grade_with_later_status(self) -> None:
        early = _detection_epochs(
            [
                {"epoch": 0, "trigger_status": "none"},
                {"epoch": 2, "trigger_status": "SUSPECTED"},
                {"epoch": 4, "trigger_status": "CONFIRMED"},
            ],
        )
        late = _detection_epochs(
            [
                {"epoch": 0, "trigger_status": "none"},
                {"epoch": 8, "trigger_status": "SUSPECTED"},
                {"epoch": 12, "trigger_status": "CONFIRMED"},
            ],
        )
        assert early == (2, 4)
        assert late == (8, 12)
        assert late[0] > early[0]
        assert late[1] > early[1]

    def test_quiet_series_has_no_detection(self) -> None:
        det, conf = _detection_epochs(
            [{"epoch": 0, "trigger_status": "none"} for _ in range(5)],
        )
        assert det is None
        assert conf is None


def test_unknown_tier_family_is_refused() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["tiers"]["zz_mystery"] = {"epochs": 2}
    with pytest.raises(ValueError, match="No generator"):
        list(generate_tier_runs(manifest, "zz_mystery"))
