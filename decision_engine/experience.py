"""Cross-cruise experience storage for Presidio fleet runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExperienceStore:
    """Persist sufficient statistics and policy params between cruises."""

    store_path: str
    records: list[dict[str, Any]] = field(default_factory=list)
    policy_params: dict[str, Any] = field(default_factory=dict)

    def load(self) -> None:
        if not self.store_path or not os.path.isfile(self.store_path):
            return
        with open(self.store_path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.records = data.get("records", [])
        self.policy_params = data.get("policy_params", {})

    def save(self) -> None:
        if not self.store_path:
            return
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as fh:
            json.dump(
                {"records": self.records, "policy_params": self.policy_params},
                fh,
                indent=2,
            )

    def record_cruise(
        self,
        cruise_id: int,
        rewards: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.records.append({
            "cruise_id": cruise_id,
            "rewards": rewards,
            "metadata": metadata or {},
        })
        for actor, reward in rewards.items():
            key = f"rolling_mean:{actor}"
            prev = float(self.policy_params.get(key, reward))
            n = int(self.policy_params.get(f"count:{actor}", 0))
            self.policy_params[f"count:{actor}"] = n + 1
            self.policy_params[key] = prev + (reward - prev) / (n + 1)

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.policy_params.get(key, default)
