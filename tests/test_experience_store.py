"""Save/load and rolling-mean invariants for ExperienceStore."""

from __future__ import annotations

import json
import os

import pytest

from decision_engine.experience import ExperienceStore


class TestSaveLoad:
    def test_save_load_round_trip_with_allowed_roots(self, tmp_path) -> None:
        root = str(tmp_path.resolve())
        path = os.path.join(root, "exp.json")
        store = ExperienceStore(path, allowed_roots=(root,))
        store.records = [{"cruise_id": 0, "rewards": {"fleet": 1.0}, "metadata": {}}]
        store.policy_params = {"alpha": 0.3}
        store.save()

        loaded = ExperienceStore(path, allowed_roots=(root,))
        loaded.load()
        assert loaded.records == store.records
        assert loaded.policy_params["alpha"] == pytest.approx(0.3)

        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        assert "records" in raw
        assert "policy_params" in raw

    def test_value_error_without_roots(self, tmp_path) -> None:
        path = str(tmp_path / "exp.json")
        store = ExperienceStore(path, allowed_roots=())
        store.records = []
        with pytest.raises(ValueError, match="allowed_roots"):
            store.save()

    def test_empty_path_is_noop(self, tmp_path) -> None:
        store = ExperienceStore("", allowed_roots=(str(tmp_path),))
        store.records = [{"cruise_id": 1, "rewards": {}, "metadata": {}}]
        store.save()  # no-op: must not write
        store.load()  # no-op: must not clear
        assert len(store.records) == 1


class TestRollingMean:
    def test_rolling_mean_invariant_for_rewards(self) -> None:
        store = ExperienceStore("unused.json", allowed_roots=("/tmp",))
        rewards_seq = [10.0, 20.0, 30.0]
        for i, r in enumerate(rewards_seq):
            store.record_cruise(i, {"fleet": r})

        # Online mean of [10, 20, 30] is exactly 20.
        assert store.policy_params["count:fleet"] == 3
        assert store.policy_params["rolling_mean:fleet"] == pytest.approx(20.0)
        # Invariant: rolling mean stays within min/max of observations.
        assert min(rewards_seq) <= store.policy_params["rolling_mean:fleet"] <= max(
            rewards_seq
        )
        assert store.get_param("rolling_mean:fleet") == pytest.approx(20.0)
        assert store.get_param("missing_key", default=42) == 42
