#!/usr/bin/env python3
"""Aggregate committed emesis-plume sensitivity voyage artifacts.

Declared seed set for the current-main readout: seed 8002 carries the
sensitivity axes as the first event-firing candidate in the predeclared
8002-then-8018 fallback order; seed 8105 is the measured zero-event witness.
This substitution is event-conditioned single-realization evidence, not a
revival of the canonical 8105/8106 attribution floor.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

DISTANCE_CLASSES = ("local", "adjacent", "room")
AXIS_SEED = 8002
ZERO_EVENT_WITNESS_SEED = 8105
EXPECTED_CELLS = {
    f"seed{AXIS_SEED}_event_pulse_p15_v1",
    f"seed{AXIS_SEED}_compartment_average_p15_v1",
    f"seed{AXIS_SEED}_event_pulse_p5_v1",
    f"seed{AXIS_SEED}_event_pulse_p30_v1",
    f"seed{AXIS_SEED}_event_pulse_p15_v0.1",
    f"seed{AXIS_SEED}_event_pulse_p15_v10",
    f"seed{ZERO_EVENT_WITNESS_SEED}_event_pulse_p15_v1",
    f"seed{ZERO_EVENT_WITNESS_SEED}_compartment_average_p15_v1",
}
EXPECTED_AXIS_VALUES = {
    "pulse_minutes": [5.0, 15.0, 30.0],
    "receiving_volume_scale": [0.1, 1.0, 10.0],
}


def load_artifacts(artifact_dir: Path) -> list[dict[str, Any]]:
    payloads = []
    for path in sorted(artifact_dir.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["artifact_file"] = path.name
        payloads.append(payload)
    if not payloads:
        raise ValueError(f"no .json.gz artifacts in {artifact_dir}")
    return payloads


def event_base_key(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(event["epoch"]),
        str(event["zone"]),
        int(event["agent_id"]),
    )


def event_identity_key(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        *event_base_key(event),
        int(event["host_event_index"]),
        float(event["aerosol_load"]),
        float(event["episode_load"]),
        float(event["volume_ml"]),
    )


def exposure_event_key(row: dict[str, Any]) -> tuple[Any, ...]:
    source_ids = row.get("source_agent_ids") or [-1]
    return (
        int(row["epoch"]),
        str(row["source_zone"]),
        int(source_ids[0]),
    )


def unique_rounded(rows: list[dict[str, Any]], key: str) -> list[float]:
    return sorted({round(float(row[key]), 6) for row in rows if key in row})


def distance_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for distance_class in DISTANCE_CLASSES:
        subset = [
            row for row in rows if row.get("distance_class") == distance_class
        ]
        out[distance_class] = {
            "rows": len(subset),
            "recipients": len({int(row["target_id"]) for row in subset}),
            "dose_gec": sum(float(row["credited_dose_gec"]) for row in subset),
            "opportunity_minutes_total": sum(
                float(row["opportunity_minutes"]) for row in subset
            ),
            "exposure_hours_total": sum(
                float(row["exposure_hours"]) for row in subset
            ),
            "receiving_volume_m3_values": unique_rounded(
                subset, "receiving_volume_m3",
            ),
            "removal_per_hour_values": unique_rounded(
                subset, "removal_per_hour",
            ),
        }
    return out


def event_rows(
    rows: list[dict[str, Any]],
    event: dict[str, Any],
) -> list[dict[str, Any]]:
    key = event_base_key(event)
    return [row for row in rows if exposure_event_key(row) == key]


def exposure_identity_digest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted(exposure_row_identity(row) for row in rows)
    encoded = json.dumps(keys, separators=(",", ":")).encode("utf-8")
    return {
        "count": len(keys),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def event_dose_summary(
    rows: list[dict[str, Any]],
    event: dict[str, Any],
) -> dict[str, Any]:
    subset = event_rows(rows, event)
    return {
        "rows": len(subset),
        "recipients": len({int(row["target_id"]) for row in subset}),
        "dose_gec": sum(float(row["credited_dose_gec"]) for row in subset),
        "distance_classes": distance_summary(subset),
        "exposure_keys": exposure_identity_digest(subset),
    }


def cell_key(payload: dict[str, Any]) -> str:
    identity = payload["identity"]
    return (
        f"seed{identity['seed']}_{identity['mode']}"
        f"_p{identity['pulse_minutes_requested']:g}"
        f"_v{identity['receiving_volume_scale']:g}"
    )


def summarize_cell(payload: dict[str, Any]) -> dict[str, Any]:
    identity = payload["identity"]
    rows = payload["exposures"]["rows"]
    events = payload["events"]["records"]
    exposure = payload["exposures"]["summary"]
    event_summaries = []
    for event in events:
        event_summaries.append({
            "key": list(event_identity_key(event)),
            "epoch": int(event["epoch"]),
            "zone": str(event["zone"]),
            "agent_id": int(event["agent_id"]),
            "host_event_index": int(event["host_event_index"]),
            "aerosol_load_gec": float(event["aerosol_load"]),
            "exposure": event_dose_summary(rows, event),
        })
    return {
        "cell": cell_key(payload),
        "artifact_file": payload["artifact_file"],
        "seed": int(identity["seed"]),
        "mode": str(identity["mode"]),
        "pulse_minutes": float(identity["pulse_minutes_requested"]),
        "receiving_volume_scale": float(identity["receiving_volume_scale"]),
        "engine_git_sha": identity["engine_git_sha"],
        "events": {
            "count": int(payload["events"]["summary"]["count"]),
            "emitting_hosts": int(payload["events"]["summary"]["emitting_hosts"]),
            "aerosol_mass_gec": float(
                payload["events"]["summary"]["aerosol_mass_gec"]["sum"],
            ),
            "records": event_summaries,
        },
        "exposures": {
            "rows": int(exposure["row_count"]),
            "recipients": int(exposure["recipient_count"]),
            "dose_gec": float(exposure["total_recipient_inhaled_dose_gec_exact"]),
            "distance_classes": distance_summary(rows),
            "observer_uncommitted_nonoccupant": exposure[
                "observer_uncommitted_nonoccupant"
            ],
        },
        "proof": payload["proof"],
        "configuration_witness": payload["configuration_witness"],
    }


def filter_cells(
    cells: list[dict[str, Any]],
    *,
    seed: int,
    mode: str,
    volume_scale: float | None = None,
    pulse_minutes: float | None = None,
) -> list[dict[str, Any]]:
    selected = [
        cell for cell in cells
        if cell["seed"] == seed
        and cell["mode"] == mode
        and (volume_scale is None or cell["receiving_volume_scale"] == volume_scale)
        and (pulse_minutes is None or cell["pulse_minutes"] == pulse_minutes)
    ]
    return selected


def shared_event_dose(
    cell: dict[str, Any],
    shared_keys: set[tuple[Any, ...]],
) -> dict[str, Any]:
    total = 0.0
    local = 0.0
    rows = 0
    for event in cell["events"]["records"]:
        key = tuple(event["key"])
        if key not in shared_keys:
            continue
        exposure = event["exposure"]
        total += float(exposure["dose_gec"])
        local += float(exposure["distance_classes"]["local"]["dose_gec"])
        rows += int(exposure["rows"])
    return {"rows": rows, "dose_gec": total, "local_dose_gec": local}


def select_axis_cells(
    cells: list[dict[str, Any]],
    *,
    axis: str,
    seed: int,
) -> list[dict[str, Any]]:
    if axis == "pulse_minutes":
        selected = filter_cells(
            cells, seed=seed, mode="event_pulse", volume_scale=1.0,
        )
    elif axis == "receiving_volume_scale":
        selected = filter_cells(
            cells, seed=seed, mode="event_pulse", pulse_minutes=15.0,
        )
    else:
        raise ValueError(f"unknown axis {axis!r}")
    return sorted(selected, key=lambda cell: cell[axis])


def shared_exposure_signature(
    cell: dict[str, Any],
    shared_keys: set[tuple[Any, ...]],
) -> tuple[tuple[int, str], ...] | None:
    signature = []
    for key in sorted(shared_keys):
        record = next(
            (
                item for item in cell["events"]["records"]
                if tuple(item["key"]) == key
            ),
            None,
        )
        if record is None:
            return None
        exposure_keys = record["exposure"]["exposure_keys"]
        signature.append((exposure_keys["count"], exposure_keys["sha256"]))
    return tuple(signature)


def shared_exposure_keys_match(
    cells: list[dict[str, Any]],
    shared_keys: set[tuple[Any, ...]],
    *,
    axis_complete: bool,
) -> bool:
    if not axis_complete or not shared_keys:
        return False
    signatures = [
        shared_exposure_signature(cell, shared_keys) for cell in cells
    ]
    return len(set(signatures)) == 1 and signatures[0] is not None


def doses_in_declared_order(doses: list[float], axis: str) -> bool:
    if axis == "pulse_minutes":
        return doses == sorted(doses)
    return doses == sorted(doses, reverse=True)


def axis_summary(
    cells: list[dict[str, Any]],
    *,
    axis: str,
    seed: int,
) -> dict[str, Any]:
    selected = select_axis_cells(cells, axis=axis, seed=seed)
    key_sets = []
    for cell in selected:
        key_sets.append({
            tuple(record["key"]) for record in cell["events"]["records"]
        })
    shared_keys = set.intersection(*key_sets) if key_sets else set()
    observed_axis_values = sorted(cell[axis] for cell in selected)
    axis_complete = observed_axis_values == EXPECTED_AXIS_VALUES[axis]
    shared_exposure_keys_identical = shared_exposure_keys_match(
        selected,
        shared_keys,
        axis_complete=axis_complete,
    )
    rows = []
    for cell in selected:
        shared = shared_event_dose(cell, shared_keys)
        rows.append({
            "cell": cell["cell"],
            "axis_value": cell[axis],
            "events": cell["events"]["count"],
            "emitted_aerosol_gec": cell["events"]["aerosol_mass_gec"],
            "voyage_dose_gec": cell["exposures"]["dose_gec"],
            "voyage_rows": cell["exposures"]["rows"],
            "shared_event_dose": shared,
            "local_dose_gec": cell["exposures"]["distance_classes"]["local"]["dose_gec"],
            "adjacent_dose_gec": cell["exposures"]["distance_classes"]["adjacent"]["dose_gec"],
            "room_dose_gec": cell["exposures"]["distance_classes"]["room"]["dose_gec"],
        })
    voyage_doses = [row["voyage_dose_gec"] for row in rows]
    shared_doses = [row["shared_event_dose"]["dose_gec"] for row in rows]
    shared_exposure_rows_positive = all(
        row["shared_event_dose"]["rows"] > 0 for row in rows
    )
    ordering_evaluable = (
        axis_complete
        and shared_exposure_keys_identical
        and shared_exposure_rows_positive
    )
    voyage_ordered = doses_in_declared_order(voyage_doses, axis)
    shared_ordered = doses_in_declared_order(shared_doses, axis)
    return {
        "axis": axis,
        "seed": seed,
        "cells": rows,
        "axis_complete": axis_complete,
        "shared_event_count": len(shared_keys),
        "shared_event_keys": [list(key) for key in sorted(shared_keys)],
        "shared_exposure_keys_identical": shared_exposure_keys_identical,
        "shared_exposure_rows_positive": shared_exposure_rows_positive,
        "voyage_dose_order_matches_arithmetic": (
            axis_complete and voyage_ordered
        ),
        "shared_event_dose_order_matches_arithmetic": (
            ordering_evaluable and shared_ordered
        ),
    }


def exposure_identity_set(payload: dict[str, Any]) -> set[tuple[Any, ...]]:
    rows = payload["exposures"]["rows"]
    return exposure_identity_set_from_rows(rows)


def exposure_row_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["epoch"]),
        int(row["target_id"]),
        str(row["source_zone"]),
        tuple(int(agent_id) for agent_id in row.get("source_agent_ids", [])),
        str(row["pathogen_id"]),
    )


def exposure_identity_set_from_rows(
    rows: list[dict[str, Any]],
) -> set[tuple[Any, ...]]:
    return {exposure_row_identity(row) for row in rows}


def exposure_identity_set_for_events(
    payload: dict[str, Any],
    event_keys: set[tuple[Any, ...]],
) -> set[tuple[Any, ...]]:
    base_keys = {key[:3] for key in event_keys}
    rows = [
        row for row in payload["exposures"]["rows"]
        if exposure_event_key(row) in base_keys
    ]
    return exposure_identity_set_from_rows(rows)


def shared_payload_event_dose(
    payload: dict[str, Any],
    shared_keys: set[tuple[Any, ...]],
) -> dict[str, Any]:
    rows = payload["exposures"]["rows"]
    total = 0.0
    local = 0.0
    row_count = 0
    for event in payload["events"]["records"]:
        if event_identity_key(event) not in shared_keys:
            continue
        exposure = event_dose_summary(rows, event)
        total += float(exposure["dose_gec"])
        local += float(exposure["distance_classes"]["local"]["dose_gec"])
        row_count += int(exposure["rows"])
    return {"rows": row_count, "dose_gec": total, "local_dose_gec": local}


def rows_for_shared_events(
    payload: dict[str, Any],
    shared_keys: set[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    base_keys = {key[:3] for key in shared_keys}
    return [
        row for row in payload["exposures"]["rows"]
        if exposure_event_key(row) in base_keys
    ]


def paired_distance_decomposition(
    pulse: dict[str, Any],
    average: dict[str, Any],
    shared_keys: set[tuple[Any, ...]],
) -> dict[str, Any]:
    pulse_rows = rows_for_shared_events(pulse, shared_keys)
    average_rows = rows_for_shared_events(average, shared_keys)
    average_by_key = {
        exposure_row_identity(row): row for row in average_rows
    }
    recipient_sets = {distance_class: set() for distance_class in DISTANCE_CLASSES}
    out = {
        distance_class: {
            "rows": 0,
            "recipients": 0,
            "event_pulse_dose_gec": 0.0,
            "compartment_average_dose_gec": 0.0,
            "contrast_gec": 0.0,
            "opportunity_minutes_total": 0.0,
            "receiving_volume_m3_values": set(),
            "removal_per_hour_values": set(),
        }
        for distance_class in DISTANCE_CLASSES
    }
    for pulse_row in pulse_rows:
        distance_class = pulse_row.get("distance_class")
        if distance_class not in out:
            continue
        average_row = average_by_key.get(exposure_row_identity(pulse_row))
        if average_row is None:
            continue
        bucket = out[distance_class]
        bucket["rows"] += 1
        recipient_sets[distance_class].add(int(pulse_row["target_id"]))
        pulse_dose = float(pulse_row["credited_dose_gec"])
        average_dose = float(average_row["credited_dose_gec"])
        bucket["event_pulse_dose_gec"] += pulse_dose
        bucket["compartment_average_dose_gec"] += average_dose
        bucket["contrast_gec"] += pulse_dose - average_dose
        bucket["opportunity_minutes_total"] += float(
            pulse_row["opportunity_minutes"],
        )
        bucket["receiving_volume_m3_values"].add(
            round(float(pulse_row["receiving_volume_m3"]), 6),
        )
        bucket["removal_per_hour_values"].add(
            round(float(pulse_row["removal_per_hour"]), 6),
        )
    for distance_class, bucket in out.items():
        bucket["recipients"] = len(recipient_sets[distance_class])
        bucket["receiving_volume_m3_values"] = sorted(
            bucket["receiving_volume_m3_values"],
        )
        bucket["removal_per_hour_values"] = sorted(
            bucket["removal_per_hour_values"],
        )
    return out


def paired_central_contrast(
    payloads: list[dict[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    selected = [
        payload for payload in payloads
        if int(payload["identity"]["seed"]) == seed
        and math.isclose(
            float(payload["identity"]["pulse_minutes_requested"]),
            15.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            float(payload["identity"]["receiving_volume_scale"]),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ]
    by_mode = {
        str(payload["identity"]["mode"]): payload for payload in selected
    }
    if set(by_mode) != {"event_pulse", "compartment_average"}:
        return {"complete": False}
    pulse = by_mode["event_pulse"]
    average = by_mode["compartment_average"]
    pulse_events = {
        event_identity_key(event) for event in pulse["events"]["records"]
    }
    average_events = {
        event_identity_key(event) for event in average["events"]["records"]
    }
    pulse_dose = float(
        pulse["exposures"]["summary"]["total_recipient_inhaled_dose_gec_exact"],
    )
    average_dose = float(
        average["exposures"]["summary"]["total_recipient_inhaled_dose_gec_exact"],
    )
    shared_keys = pulse_events & average_events
    pulse_shared = shared_payload_event_dose(pulse, shared_keys)
    average_shared = shared_payload_event_dose(average, shared_keys)
    return {
        "complete": True,
        "event_pulse_dose_gec": pulse_dose,
        "compartment_average_dose_gec": average_dose,
        "contrast_gec": pulse_dose - average_dose,
        "event_records_identical": pulse_events == average_events,
        "exposure_keys_identical": (
            exposure_identity_set(pulse) == exposure_identity_set(average)
        ),
        "shared_event_count": len(shared_keys),
        "shared_exposure_keys_identical": (
            exposure_identity_set_for_events(pulse, shared_keys)
            == exposure_identity_set_for_events(average, shared_keys)
        ),
        "shared_event_pulse_dose": pulse_shared,
        "shared_compartment_average_dose": average_shared,
        "shared_event_contrast_gec": (
            pulse_shared["dose_gec"] - average_shared["dose_gec"]
        ),
        "shared_distance_decomposition_metadata": {
            "distance_and_exposure_fields_source": "event_pulse rows only",
            "compartment_average_fields_absent": [
                "distance_class",
                "receiving_volume_m3",
                "event_epoch_fraction",
                "opportunity_windows",
                "opportunity_minutes",
                "removal_per_hour",
                "exposure_hours",
                "presence_share",
            ],
            "mapping_note": (
                "compartment_average rows are mapped onto event_pulse "
                "distance classes solely by identical exposure key; the "
                "baseline itself applies one whole-compartment average"
            ),
        },
        "shared_distance_decomposition": paired_distance_decomposition(
            pulse, average, shared_keys,
        ),
    }


def aggregate(artifact_dir: Path) -> dict[str, Any]:
    payloads = load_artifacts(artifact_dir)
    cells = [summarize_cell(payload) for payload in payloads]
    cells.sort(key=lambda cell: cell["cell"])
    shas = sorted({cell["engine_git_sha"] for cell in cells})
    cell_names = [cell["cell"] for cell in cells]
    cell_name_set = set(cell_names)
    return {
        "measurement": "emesis_plume_sensitivity_readout_v1",
        "artifact_dir": str(artifact_dir),
        "engine_git_shas": shas,
        "completeness": {
            "expected_cells": sorted(EXPECTED_CELLS),
            "observed_cells": sorted(cell_name_set),
            "missing_cells": sorted(EXPECTED_CELLS - cell_name_set),
            "unexpected_cells": sorted(cell_name_set - EXPECTED_CELLS),
            "duplicate_cells": sorted({
                cell for cell in cell_name_set if cell_names.count(cell) > 1
            }),
        },
        "seed_declaration": {
            "axis_seed": AXIS_SEED,
            "zero_event_witness_seed": ZERO_EVENT_WITNESS_SEED,
            "canonical_floor_seed_not_rerun": 8106,
            "substitution_basis": (
                "seed 8105 fired zero events in both central arms at the "
                "measurement commit on current main; historical event-bearing "
                "candidates were qualified in the predeclared order 8002 then "
                "8018, and 8002 was selected because it is first in that order"
            ),
            "power_limitation": (
                "one event-firing realization selected from historical "
                "event-bearing candidates cannot size population frequency, "
                "represent a random firing-voyage magnitude, or support a "
                "significance claim; zero-event realizations are part of the "
                "rare-event mass"
            ),
        },
        "paired_central_contrasts": {
            str(seed): paired_central_contrast(payloads, seed=seed)
            for seed in (AXIS_SEED, ZERO_EVENT_WITNESS_SEED)
        },
        "cells": cells,
        "axes": {
            "pulse_minutes": axis_summary(
                cells, axis="pulse_minutes", seed=AXIS_SEED,
            ),
            "receiving_volume_scale": axis_summary(
                cells, axis="receiving_volume_scale", seed=AXIS_SEED,
            ),
        },
    }


def safe_path(path: Path) -> Path:
    resolved = Path(os.path.realpath(path))
    base_dir = Path(os.path.realpath(Path.cwd()))
    if resolved != base_dir and base_dir not in resolved.parents:
        raise ValueError(f"path {path!r} is outside the working directory")
    return resolved


def write_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = safe_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")


def print_axis_table(axis: dict[str, Any]) -> None:
    print(f"{axis['axis']}: shared_events={axis['shared_event_count']}")
    for row in axis["cells"]:
        print(
            "  {axis_value:g}: voyage={voyage:.6g} GEC rows={rows} "
            "events={events} shared={shared:.6g} GEC".format(
                axis_value=row["axis_value"],
                voyage=row["voyage_dose_gec"],
                rows=row["voyage_rows"],
                events=row["events"],
                shared=row["shared_event_dose"]["dose_gec"],
            ),
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = aggregate(safe_path(args.artifact_dir))
    write_json(safe_path(args.out), payload)
    print_axis_table(payload["axes"]["pulse_minutes"])
    print_axis_table(payload["axes"]["receiving_volume_scale"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
