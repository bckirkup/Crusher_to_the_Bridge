#!/usr/bin/env python3
"""Measure recipient-inhaled dose from the event-moment emesis plume.

Frozen local measurement design (declared before the 8105/8106 runs):

* hull: ``classic_cruise_1900`` at declared complement;
* frame: 288 one-hour epochs, matching the NORO-EMESIS-BOOTSTRAP-01 cohort
  frame whose historical emitted-mass band was 9-906 GEC per voyage;
* arms: ``transmission.emesis_event_plume.mode`` = ``event_pulse`` and the
  labelled pre-change ``compartment_average`` baseline;
* paired seeds: 8105 and 8106, the norovirus attribution floor;
* statistic: voyage-total recipient-inhaled emesis-aerosol dose, summed over
  every recipient exposure row, using the exact dose returned by
  ``TransmissionCore._accumulate`` before route-efficiency, NPI, or host
  susceptibility scaling; paired arm contrast is event_pulse minus
  compartment_average on the same seed;
* firing gate: at least one emesis event must occur, and the event_pulse arm
  must emit exposure rows carrying distance class, receiving volume,
  opportunity windows/minutes, removal, and exposure hours;
* interpretation: two paired seeds prove the pathway fires and give the
  measured per-voyage magnitudes at those seeds; they do not size a
  population effect or support a significance claim.

The observer is read-only. It copies tracing rows after each epoch, wraps
``_accumulate`` only to retain full-precision doses that tracing rounds to
four decimals, wraps ``_emit_emesis`` only to copy deposition records as
they are emitted (the infection lifecycle clears those records at recovery),
and wraps ``_emesis_schedule_candidates`` only to retain the exact occupant
and candidate sets behind each row. No observer path consumes RNG.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import subprocess
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from engines.rhythm_layer import platform_has_rhythm_catalog  # noqa: E402
from picard_framework.run_spec import CRUSHER_CONFIG_REL  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402

MEASUREMENT_DESIGN = {
    "hull": "classic_cruise_1900",
    "epochs": 288,
    "paired_seeds": [8105, 8106],
    "arms": ["event_pulse", "compartment_average"],
    "statistic": (
        "voyage-total exact credited recipient-inhaled emesis-aerosol dose "
        "(GEC), summed over recipients; paired contrast is event_pulse minus "
        "compartment_average on the same seed"
    ),
    "firing_gate": (
        "emesis event count > 0 and event_pulse rows carry the declared "
        "distance/volume/opportunity/removal decomposition"
    ),
    "interpretation": (
        "mechanism-fired smoke at the paired-seed floor; no population effect "
        "size or significance claim"
    ),
}

REQUIRED_EVENT_PULSE_FIELDS = (
    "distance_class",
    "receiving_volume_m3",
    "event_epoch_fraction",
    "opportunity_windows",
    "opportunity_minutes",
    "removal_per_hour",
    "exposure_hours",
)

DISTANCE_CLASSES = ("local", "adjacent", "room")


@dataclass
class ExposureCapture:
    """Full-precision dose rows and emission-time event records."""

    pending_exact: list[dict[str, float]] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    occupant_ids_by_unit: dict[tuple[int, str], set[int]] = field(
        default_factory=dict,
    )
    schedule_candidate_ids_by_unit: dict[tuple[int, str], set[int]] = field(
        default_factory=dict,
    )

    def note_accumulate(
        self, pathway: str, input_dose: float, credited_dose: float,
    ) -> None:
        if pathway != "emesis_aerosol":
            return
        self.pending_exact.append({
            "model_input_dose_gec": float(input_dose),
            "credited_dose_gec": float(credited_dose),
        })

    def note_emit(self, agent: Any, pathogen_id: str, before: int) -> None:
        records = agent.emesis_deposition_records_by_pathogen.get(
            pathogen_id, [],
        )
        if len(records) < before:
            raise RuntimeError("emesis record capture lost rows inside _emit_emesis")
        for host_event_index, record in enumerate(records[before:], start=before):
            row = copy.deepcopy(record)
            row["agent_id"] = int(agent.agent_id)
            row["pathogen_id"] = str(pathogen_id)
            row["host_event_index"] = int(host_event_index)
            self.events.append(row)

    def note_schedule_candidates(
        self,
        zone_name: str,
        epoch: int,
        occupant_ids: set[int],
        candidates: list[Any],
    ) -> None:
        key = (int(epoch), str(zone_name))
        self.occupant_ids_by_unit[key] = {
            int(agent_id) for agent_id in occupant_ids
        }
        self.schedule_candidate_ids_by_unit[key] = {
            int(agent.agent_id) for agent in candidates
        }

    def annotate_presence(
        self,
        sim: ShipSimulation,
        row: dict[str, Any],
        agents_by_id: dict[int, Any],
    ) -> None:
        """Witness whether an event-pulse row used occupancy or a booking."""
        if row.get("exposure_model") != "event_pulse":
            return
        target = agents_by_id.get(int(row["target_id"]))
        if target is None:
            row["observer_presence_overlap"] = "target_missing"
            return
        key = (int(row["epoch"]), str(row["source_zone"]))
        target_id = int(row["target_id"])
        in_epoch_occupants = target_id in self.occupant_ids_by_unit.get(key, set())
        row["observer_target_current_location"] = str(
            getattr(target, "current_location", ""),
        )
        row["observer_target_in_epoch_occupants"] = in_epoch_occupants
        row["observer_target_in_schedule_candidates"] = (
            target_id in self.schedule_candidate_ids_by_unit.get(key, set())
        )
        schedule = getattr(sim.tx_core, "_event_schedule", None)
        if schedule is None or not hasattr(schedule, "presence_overlap_window"):
            row["observer_presence_overlap"] = "schedule_unavailable"
            row["observer_uncommitted_nonoccupant"] = False
            return
        offset = (
            float(row["event_epoch_fraction"])
            * sim.clock.hours_per_epoch
            * 60.0
        )
        windows = schedule.presence_overlap_window(
            target,
            str(row["source_zone"]),
            sim.clock.hour_of_day(int(row["epoch"])),
            offset,
            float(sim.tx_core.emesis_event_plume.pulse_minutes),
        )
        if windows is None:
            state = "no_commitment"
        elif windows:
            state = "resolved_segments"
        else:
            state = "elsewhere_or_miss"
        row["observer_presence_overlap"] = state
        row["observer_uncommitted_nonoccupant"] = bool(
            windows is None and not in_epoch_occupants,
        )

    def observe(self, sim: ShipSimulation, work: Any) -> None:
        matrix = work.tracing_matrix
        epoch_rows = [
            copy.deepcopy(row) for row in matrix.emesis_aerosol_exposures
        ]
        if len(epoch_rows) != len(self.pending_exact):
            raise RuntimeError(
                "emesis dose capture mismatch: "
                f"{len(epoch_rows)} tracing rows vs "
                f"{len(self.pending_exact)} accumulate calls in epoch "
                f"{work.epoch}",
            )
        agents_by_id = {
            int(agent.agent_id): agent for agent in sim.engine.agents
        }
        for row, exact in zip(epoch_rows, self.pending_exact, strict=True):
            row["epoch"] = int(work.epoch)
            row.update(exact)
            self.annotate_presence(sim, row, agents_by_id)
        self.rows.extend(epoch_rows)
        self.pending_exact.clear()
        if work.epoch % 24 == 0 or work.epoch + 1 == sim.num_epochs:
            print(
                f"epoch {work.epoch}: emesis exposure rows={len(self.rows)}",
                flush=True,
            )


@contextmanager
def capture_exact_emesis_doses(capture: ExposureCapture):
    """Retain exact credited emesis doses without altering the RNG stream."""
    original = tc.TransmissionCore._accumulate

    def wrapper(
        self: tc.TransmissionCore,
        target_id: int,
        pathway: str,
        dose: float,
        *args: Any,
        **kwargs: Any,
    ) -> float:
        credited = original(
            self, target_id, pathway, dose, *args, **kwargs,
        )
        capture.note_accumulate(pathway, dose, credited)
        return credited

    tc.TransmissionCore._accumulate = wrapper
    try:
        yield
    finally:
        tc.TransmissionCore._accumulate = original


@contextmanager
def capture_emesis_events(capture: ExposureCapture):
    """Copy deposition records at emission, before recovery clears them."""
    original = tc.TransmissionCore._emit_emesis

    def wrapper(
        self: tc.TransmissionCore,
        agent: Any,
        pathogen_id: str,
        profile: dict,
        zone_name: str,
        epoch: int,
        *args: Any,
        **kwargs: Any,
    ) -> float:
        records = agent.emesis_deposition_records_by_pathogen.get(pathogen_id, [])
        before = len(records)
        emitted = original(
            self, agent, pathogen_id, profile, zone_name, epoch, *args, **kwargs,
        )
        capture.note_emit(agent, pathogen_id, before)
        return emitted

    tc.TransmissionCore._emit_emesis = wrapper
    try:
        yield
    finally:
        tc.TransmissionCore._emit_emesis = original


@contextmanager
def capture_emesis_candidate_sets(capture: ExposureCapture):
    """Retain the exact occupant/candidate sets behind each exposure row."""
    original = tc.TransmissionCore._emesis_schedule_candidates

    def wrapper(
        self: tc.TransmissionCore,
        zone_name: str,
        entries: list[Any],
        epoch: int,
        occupant_ids: set[int],
    ) -> list[Any]:
        candidates = original(self, zone_name, entries, epoch, occupant_ids)
        capture.note_schedule_candidates(zone_name, epoch, occupant_ids, candidates)
        return candidates

    tc.TransmissionCore._emesis_schedule_candidates = wrapper
    try:
        yield
    finally:
        tc.TransmissionCore._emesis_schedule_candidates = original


def build_spec(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    mode: str,
) -> dict[str, Any]:
    """One shipped voyage spec with only the plume-mode arm override."""
    return {
        "schema_version": "1.0.0",
        "description": "emesis plume recipient-dose measurement",
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": int(seed),
            "num_epochs": int(epochs),
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": CRUSHER_CONFIG_REL,
        "actors": [],
        "incentives": {},
        "config_overrides": {
            "ship_graph": {"num_agents": declared_total(platform)},
            "transmission": {"emesis_event_plume": {"mode": mode}},
        },
        "pathogen_overrides": {},
    }


def git_value(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def distribution(values: list[float]) -> dict[str, Any]:
    """Compact distribution summary; null quantiles on an empty stream."""
    if not values:
        return {
            "count": 0,
            "sum": 0.0,
            "mean": None,
            "min": None,
            "q25": None,
            "median": None,
            "q75": None,
            "max": None,
        }
    array = np.asarray(values, dtype=float)
    return {
        "count": int(array.size),
        "sum": float(np.sum(array)),
        "mean": float(np.mean(array)),
        "min": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.50)),
        "q75": float(np.quantile(array, 0.75)),
        "max": float(np.max(array)),
    }


def values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if key in row]


def distance_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Exposure-row, dose, volume, time, and removal split by distance class."""
    out: dict[str, Any] = {}
    for distance_class in DISTANCE_CLASSES:
        subset = [
            row for row in rows if row.get("distance_class") == distance_class
        ]
        out[distance_class] = {
            "rows": len(subset),
            "recipients": len({int(row["target_id"]) for row in subset}),
            "dose_gec": distribution(values(subset, "credited_dose_gec")),
            "receiving_volume_m3": distribution(
                values(subset, "receiving_volume_m3"),
            ),
            "opportunity_minutes": distribution(
                values(subset, "opportunity_minutes"),
            ),
            "removal_per_hour": distribution(values(subset, "removal_per_hour")),
            "exposure_hours": distribution(values(subset, "exposure_hours")),
        }
    return out


def recipient_totals(rows: list[dict[str, Any]]) -> list[float]:
    totals: dict[int, float] = defaultdict(float)
    for row in rows:
        totals[int(row["target_id"])] += float(row["credited_dose_gec"])
    return list(totals.values())


def exposure_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    doses = values(rows, "credited_dose_gec")
    rounded_doses = values(rows, "dose")
    uncommitted_nonoccupant = [
        row for row in rows if row.get("observer_uncommitted_nonoccupant")
    ]
    return {
        "row_count": len(rows),
        "recipient_count": len({int(row["target_id"]) for row in rows}),
        "exposure_model_counts": dict(
            sorted(_counts(row.get("exposure_model") for row in rows).items()),
        ),
        "observer_presence_overlap_counts": dict(
            sorted(_counts(row.get("observer_presence_overlap") for row in rows).items()),
        ),
        "observer_uncommitted_nonoccupant": {
            "rows": len(uncommitted_nonoccupant),
            "recipients": len({
                int(row["target_id"]) for row in uncommitted_nonoccupant
            }),
            "dose_gec": distribution(
                values(uncommitted_nonoccupant, "credited_dose_gec"),
            ),
        },
        "total_recipient_inhaled_dose_gec_exact": float(sum(doses)),
        "total_recipient_inhaled_dose_gec_rounded_rows": float(
            sum(rounded_doses),
        ),
        "dose_per_exposure_row_gec": distribution(doses),
        "dose_per_exposed_recipient_gec": distribution(recipient_totals(rows)),
        "distance_classes": distance_distribution(rows),
        "receiving_volume_m3": distribution(values(rows, "receiving_volume_m3")),
        "opportunity_minutes": distribution(values(rows, "opportunity_minutes")),
        "removal_per_hour": distribution(values(rows, "removal_per_hour")),
        "exposure_hours": distribution(values(rows, "exposure_hours")),
        "event_epoch_fraction": distribution(values(rows, "event_epoch_fraction")),
    }


def _counts(items: Any) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[str(item)] += 1
    return counts


def emesis_event_rows(capture: ExposureCapture) -> list[dict[str, Any]]:
    return sorted(
        copy.deepcopy(capture.events),
        key=lambda row: (row["epoch"], row["agent_id"], row["host_event_index"]),
    )


def event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(events),
        "emitting_hosts": len({int(row["agent_id"]) for row in events}),
        "aerosol_mass_gec": distribution(values(events, "aerosol_load")),
        "episode_load_gec": distribution(values(events, "episode_load")),
        "volume_ml": distribution(values(events, "volume_ml")),
        "zones": dict(sorted(_counts(row.get("zone") for row in events).items())),
    }


def missing_pulse_fields(rows: list[dict[str, Any]]) -> dict[str, int]:
    missing: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("exposure_model") != "event_pulse":
            continue
        for key in REQUIRED_EVENT_PULSE_FIELDS:
            if key not in row:
                missing[key] += 1
    return dict(sorted(missing.items()))


def proof_block(
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    mode: str,
    resolved_mode: str,
    rhythm_active: bool,
) -> dict[str, Any]:
    pulse_rows = [
        row for row in rows if row.get("exposure_model") == "event_pulse"
    ]
    missing = missing_pulse_fields(rows)
    return {
        "mode_requested": mode,
        "mode_resolved": resolved_mode,
        "mode_matches_request": mode == resolved_mode,
        "rhythm_layer_active": rhythm_active,
        "emesis_event_count_positive": len(events) > 0,
        "event_pulse_exposure_rows_present": len(pulse_rows) > 0,
        "event_pulse_required_fields_missing": missing,
        "event_pulse_required_fields_complete": not missing,
    }


def run_voyage(args: argparse.Namespace) -> dict[str, Any]:
    spec = build_spec(
        seed=args.seed,
        platform=args.platform,
        bundle=args.bundle,
        epochs=args.epochs,
        mode=args.mode,
    )
    capture = ExposureCapture()
    started_total = time.perf_counter()
    with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
        emetic_profiles = [
            pid for pid, profile in picard_spec.pathogen_profiles.items()
            if profile.get("airborne_emission_mode") == "emesis_conditioned"
        ]
        if emetic_profiles != [args.pathogen_id]:
            raise RuntimeError(
                "measurement expects exactly one emesis-conditioned profile: "
                f"{emetic_profiles!r}",
            )
        with (
            capture_exact_emesis_doses(capture),
            capture_emesis_events(capture),
            capture_emesis_candidate_sets(capture),
        ):
            sim = ShipSimulation(picard_spec, display=False)
            sim.initialize()
            resolved_mode = sim.tx_core.emesis_event_plume.mode
            rhythm_active = sim.tx_core._event_schedule is not None
            sim.epoch_observer = capture.observe
            started_run = time.perf_counter()
            result = sim.run()
            wall_clock_run = time.perf_counter() - started_run
    events = [
        row for row in emesis_event_rows(capture)
        if row.get("pathogen_id") == args.pathogen_id
    ]
    rows = capture.rows
    epoch_hours = float(sim.clock.hours_per_epoch)
    return {
        "measurement": "emesis_plume_recipient_dose_v3",
        "design": MEASUREMENT_DESIGN,
        "identity": {
            "engine_git_sha": git_value(["rev-parse", "HEAD"]),
            "worktree_status_at_start": git_value(["status", "--porcelain"]),
            "python_version": sys.version.split()[0],
            "platform": args.platform,
            "pathogen_bundle_id": args.bundle,
            "pathogen_id": args.pathogen_id,
            "seed": int(args.seed),
            "mode": args.mode,
            "epochs": int(args.epochs),
            "epoch_duration_hours": epoch_hours,
            "num_agents": len(sim.engine.agents),
        },
        "configuration_witness": {
            "plume_mode_resolved": resolved_mode,
            "rhythm_catalogued_platform": platform_has_rhythm_catalog(args.platform),
            "rhythm_layer_active": rhythm_active,
            "room_air_removal_mode": sim.tx_core.room_air_removal.mode,
            "pulse_minutes": sim.tx_core.emesis_event_plume.pulse_minutes,
            "local_volume_m3": sim.tx_core.emesis_event_plume.local_volume_m3,
            "adjacent_volume_m3": sim.tx_core.emesis_event_plume.adjacent_volume_m3,
        },
        "proof": proof_block(
            rows,
            events,
            mode=args.mode,
            resolved_mode=resolved_mode,
            rhythm_active=rhythm_active,
        ),
        "events": {
            "summary": event_summary(events),
            "records": events,
        },
        "exposures": {
            "summary": exposure_summary(rows),
            "rows": rows,
        },
        "run": {
            "wall_clock_seconds": wall_clock_run,
            "wall_clock_seconds_total": time.perf_counter() - started_total,
            "num_epochs_completed": result.num_epochs,
            "final_trigger_status": result.final_trigger_status,
        },
    }


def write_gzip_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default=MEASUREMENT_DESIGN["hull"])
    parser.add_argument(
        "--bundle", default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID,
    )
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--mode", choices=MEASUREMENT_DESIGN["arms"], required=True,
    )
    parser.add_argument(
        "--epochs", type=int, default=MEASUREMENT_DESIGN["epochs"],
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_voyage(args)
    write_gzip_json(args.out, payload)
    summary = payload["exposures"]["summary"]
    events = payload["events"]["summary"]
    print(
        "seed {seed} {mode}: events={events} aerosol={aerosol:.6g} GEC "
        "recipient_inhaled={dose:.6g} GEC rows={rows} -> {out}".format(
            seed=args.seed,
            mode=args.mode,
            events=events["count"],
            aerosol=events["aerosol_mass_gec"]["sum"],
            dose=summary["total_recipient_inhaled_dose_gec_exact"],
            rows=summary["row_count"],
            out=args.out,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
