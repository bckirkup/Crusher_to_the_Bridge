"""Export a sentinel line list from simulation history (CLI).

Two supply paths exist. A run configured with ``run.sentinel_line_list``
writes the bundle directly from ``SentinelLedger`` (the only path that works
under ``compact`` retention). This module covers the retrospective case:
rebuilding the line list from a ``full``-retention ``simulation_history.json``
that was written before the ledger existed. Sick-call identities are not
retained in history, so channels there are limited to what history keeps
(cascade tiers, wearable visibility) and everything else is ``unreported``.
"""

from __future__ import annotations

import argparse
from typing import Any, Mapping, Sequence

from engines.voyage_itinerary import LOCATION_ASHORE
from picard_framework.analysis._io import read_json, safe_path, write_json
from picard_framework.analysis.sentinel.itinerary import (
    port_calls_from_config,
    slugify_port,
)
from picard_framework.analysis.sentinel.line_list import SentinelLedger


def port_id_lookup(voyage_config: Mapping[str, Any] | None) -> dict[str, str]:
    """Map itinerary port names to their stable ``port_id``."""
    if not voyage_config:
        return {}
    return {
        call.port_name: call.port_id
        for call in port_calls_from_config(dict(voyage_config))
        if call.port_name
    }


def _detections_from_record(record: Mapping[str, Any]) -> dict[str, list[int]]:
    detections: dict[str, list[int]] = {}
    cascade = record.get("diagnostic_cascade") or {}
    if isinstance(cascade, Mapping):
        tiers = [
            int(a)
            for key in ("new_tier0_agents", "new_tier1_agents")
            for a in cascade.get(key) or []
        ]
        if tiers:
            detections["cascade"] = tiers
    wearable = record.get("wearable_monitoring") or {}
    if isinstance(wearable, Mapping):
        visible = [int(a) for a in wearable.get("staff_visible_agents") or []]
        if visible:
            detections["wearable"] = visible
    return detections


def ledger_from_history(
    history: Sequence[Mapping[str, Any]],
    *,
    port_ids: Mapping[str, str] | None = None,
    epoch_duration_hours: float = 1.0,
) -> SentinelLedger:
    """Replay epoch history into a ledger.

    Ashore exposure is read from each agent's recorded location, so hours
    ashore come from the same locations the transmission core used.
    """
    lookup = dict(port_ids or {})
    ledger = SentinelLedger(epoch_duration_hours=epoch_duration_hours)
    for record in history:
        agents = record.get("agents") or []
        if not isinstance(agents, list):
            continue
        voyage = record.get("voyage_epoch") or {}
        port_name = str(voyage.get("port") or "") if isinstance(voyage, Mapping) else ""
        port_id = lookup.get(port_name, slugify_port(port_name) if port_name else "")
        ashore = [
            int(a["agent_id"])
            for a in agents
            if str(a.get("location") or "") == LOCATION_ASHORE
        ]
        ledger.observe_epoch(
            int(record.get("epoch", 0)),
            agents,
            port_id=port_id,
            ashore_ids=ashore,
            detections=_detections_from_record(record),
        )
    return ledger


def export_from_history(
    history_path: str,
    out_path: str,
    *,
    voyage_id: str,
    ship_id: str,
    voyage_config_path: str | None = None,
    platform_class: str | None = None,
    n_passengers: int = 0,
    n_crew: int = 0,
) -> dict[str, Any]:
    """Write a sentinel observation bundle rebuilt from epoch history."""
    history = read_json(safe_path(history_path))
    if not isinstance(history, list):
        raise SystemExit(f"simulation history must be a JSON array: {history_path}")
    voyage_config = None
    epoch_hours = 1.0
    if voyage_config_path:
        loaded = read_json(safe_path(voyage_config_path))
        if not isinstance(loaded, dict):
            raise SystemExit(f"voyage_config must be an object: {voyage_config_path}")
        voyage_config = loaded
        epoch_hours = float(
            (loaded.get("voyage") or {}).get("epoch_duration_hours", 1) or 1,
        )
    ledger = ledger_from_history(
        history,
        port_ids=port_id_lookup(voyage_config),
        epoch_duration_hours=epoch_hours,
    )
    payload = ledger.to_payload(
        voyage_id=voyage_id,
        ship_id=ship_id,
        n_passengers=n_passengers,
        n_crew=n_crew,
        platform_class=platform_class,
    )
    write_json(safe_path(out_path), payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    """CLI for rebuilding a line list from a full-retention history file."""
    parser = argparse.ArgumentParser(
        prog="python -m picard_framework.analysis.sentinel",
        description="Export a sentinel line list from a simulation_history.json.",
    )
    parser.add_argument("--history", required=True, help="Path to simulation_history.json")
    parser.add_argument("--out", required=True, help="Output observation bundle JSON")
    parser.add_argument("--voyage-id", required=True)
    parser.add_argument("--ship-id", required=True)
    parser.add_argument("--voyage-config", default=None, help="voyage_config.json for port ids")
    parser.add_argument("--platform-class", default=None)
    parser.add_argument("--n-passengers", type=int, default=0)
    parser.add_argument("--n-crew", type=int, default=0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: rebuild and write the bundle, printing a one-line summary."""
    args = build_parser().parse_args(argv)
    payload = export_from_history(
        args.history,
        args.out,
        voyage_id=args.voyage_id,
        ship_id=args.ship_id,
        voyage_config_path=args.voyage_config,
        platform_class=args.platform_class,
        n_passengers=args.n_passengers,
        n_crew=args.n_crew,
    )
    print(
        f"sentinel line list: {len(payload['clinical_cases'])} cases, "
        f"{len(payload['exposure_totals'])} ports with ashore exposure → {args.out}",
    )
    return 0
