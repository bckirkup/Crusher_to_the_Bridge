"""Shared preflight machinery for the covid declared-replay assay smokes.

The ``covid_*_smoke.py`` tools all prove the same three things before a
Batch cell runs — the design's cell enumeration matches the declared
count, each arm's ``transmission_overrides`` reaches the run spec, and
the arm's axis actually binds at runtime — so the enumeration,
spec-lands, ring-recorder, engine read-back, and truncated-run drivers
live here once and the per-assay tools carry only their axis checks.

Both sibling tools import this module; their tests exercise the helpers
through the tool's own names.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from engines.transmission_core import TransmissionCore
from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec
from simulation_utils.paths import confine_to_base, validated_open

REQUIRED_PAYLOAD_KEYS = (
    "observables",
    "onset_curve",
    "index_onset_day",
    "index_shedding_at_day0",
    "arm_id",
    "during_quarantine_by_route",
    "quarantine_witness",
)


def check_enumeration(  # pragma: no cover - CLI-driven check
    design, declared_cells: int,
) -> dict[str, list[int]]:
    """The dry-run count: enumeration must match the declared cells."""
    cells = enumerate_cells(design)
    assert len(cells) == declared_cells, (
        f"enumerate_cells = {len(cells)} but the design declares {declared_cells}"
    )
    by_arm: dict[str, list[int]] = defaultdict(list)
    for idx, cell in enumerate(cells):
        by_arm[cell.arm_id].append(idx)
    assert len(by_arm) == len(design.arms), "an arm produced no cells"
    return {arm: [min(idxs), max(idxs)] for arm, idxs in by_arm.items()}


def check_spec_lands(  # pragma: no cover - CLI-driven check
    design,
    cell,
    repo_root: str,
    blocks: tuple[str, ...] = ("activity_contacts", "droplet_field_split"),
) -> None:
    """The arm's named override blocks must appear in the run spec."""
    raw = prepare_cell_run_spec(design, cell, num_epochs=24, repo_root=repo_root)
    tx = raw.get("config_overrides", {}).get("transmission", {})
    overrides = design.arm_overrides(cell.arm_id).get(
        "transmission_overrides", {},
    )
    for block in blocks:
        declared = overrides.get(block)
        if declared is None:
            assert block not in tx, (
                f"{cell.arm_id}: unexpected {block} override landed"
            )
        else:
            assert tx.get(block) == declared, (
                f"{cell.arm_id}: spec {block} {tx.get(block)} "
                f"!= declared {declared}"
            )


def install_ring_recorder() -> dict[str, Any]:  # pragma: no cover
    """Tag partner draws made on the ring path (``_proximity_shedder_ids``).

    ``_proximity_shedder_ids`` calls ``_activity_contact_draw`` synchronously,
    so a depth counter on the instance tags ring-path draws without touching
    the engine's logic — the draw still happens once, on the same RNG call.
    """
    records: dict[str, Any] = {
        "ring_draws": [],  # (activity, role, value) drawn inside the ring path
        "ring_calls": 0,
    }
    original_draw = TransmissionCore._activity_contact_draw
    original_ring = TransmissionCore._proximity_shedder_ids

    def drawing(core, target, unit_name, zone_name, hallway, epoch):
        value = original_draw(core, target, unit_name, zone_name, hallway, epoch)
        if getattr(core, "_ring_depth", 0) > 0:
            activity = core._contact_activity(
                target, unit_name, zone_name, hallway, epoch,
            )
            records["ring_draws"].append((activity, target.role, value))
        return value

    def ringing(core, target, shedders, n_occupants, unit_name, zone_name, epoch):
        core._ring_depth = getattr(core, "_ring_depth", 0) + 1
        try:
            records["ring_calls"] += 1
            return original_ring(
                core, target, shedders, n_occupants, unit_name, zone_name, epoch,
            )
        finally:
            core._ring_depth -= 1

    TransmissionCore._activity_contact_draw = drawing
    TransmissionCore._proximity_shedder_ids = ringing
    return records


def engine_rates(  # pragma: no cover - CLI-driven check
    tx_core,
) -> dict[str, dict[str, float]]:
    """The parsed per-role table the engine actually used."""
    return {
        activity: dict(rates)
        for activity, rates in (tx_core.activity_contacts or {}).items()
    }


def engine_near_field(  # pragma: no cover - CLI-driven check
    tx_core,
) -> dict[str, float]:
    """The parsed plume-flush constants the engine actually used."""
    near = tx_core.near_field_air
    return {
        "beta": near.interzonal_airflow_m3_per_hour,
        "flushed": tx_core.near_field_flushed_volume_m3_per_epoch,
        "mode": near.mode,
    }


def run_cell(  # pragma: no cover - runs a truncated sim, exercised by hand
    design,
    cell,
    repo_root: str,
    epochs: int,
    extra_readback=None,
) -> dict[str, Any]:
    """Run a truncated cell with the ring recorder and read back the engine."""
    records = install_ring_recorder()
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=epochs, repo_root=repo_root,
    )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=ledger.observe)
    payload = cell_payload(design, cell, sim, ledger, raw)
    missing = [k for k in REQUIRED_PAYLOAD_KEYS if k not in payload]
    assert not missing, f"{cell.arm_id}: payload missing {missing}"
    assert abs(payload["index_onset_day"] + 1.0) < 1e-9
    assert payload["index_shedding_at_day0"] is True
    grouped: dict[str, list[int]] = defaultdict(list)
    for activity, _role, value in records["ring_draws"]:
        grouped[activity].append(value)
    result = {
        "ring_calls": records["ring_calls"],
        "ring_draws": grouped,
        "engine_rates": engine_rates(sim.tx_core),
        "engine_droplet_split_mode": sim.tx_core.droplet_field_split.mode,
        "recorded_onsets": payload["observables"]["recorded_onsets"],
    }
    if extra_readback is not None:
        result.update(extra_readback(sim))
    return result


def repo_root_of(file_name: str) -> str:  # pragma: no cover - path helper
    """The repository root a tools/ script lives under."""
    return os.path.abspath(os.path.join(os.path.dirname(file_name), ".."))


def load_declared_cells(  # pragma: no cover - CLI-driven check
    repo_root: str, design_rel: str,
):
    """Load the design plus its declared cell count from the JSON."""
    design_path = confine_to_base(repo_root, design_rel)
    design = load_design(design_path)
    with validated_open(
        design_path, "r", allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        declared_cells = int(json.load(handle)["cells"])
    return design, declared_cells


def enumerate_per_arm(  # pragma: no cover - CLI-driven check
    design, repo_root: str, check=None,
) -> int:
    """Run ``check`` once per arm; returns the number of arms checked."""
    seen: set[str] = set()
    for cell in enumerate_cells(design):
        if cell.arm_id not in seen:
            seen.add(cell.arm_id)
            if check is not None:
                check(design, cell, repo_root)
    return len(seen)
