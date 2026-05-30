"""Structured result from a single simulation epoch step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    epoch: int
    trigger_status: str
    stoplights: dict[str, dict[str, str]]
    epoch_record: dict[str, Any]
    ground_truth: dict[str, Any] | None = None
    active_protocols: list[dict[str, Any]] = field(default_factory=list)
    merged_modifiers: dict[str, Any] = field(default_factory=dict)
    decisions: dict[str, Any] = field(default_factory=dict)
