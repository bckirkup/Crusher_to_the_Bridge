#!/usr/bin/env python3
"""NORO-VENUE-01 readout: aggregate venue-placement census zips.

Reads every ``<cell>/*.zip`` written by ``tools/noro_diag/venue_placement_census.py``
and emits the ledger-ready tables:

* the join integrity row (emitted events, unattributed, record-less calls);
* the 3xN landing table: confinement class x site group, in both event
  counts and episode-load mass;
* placement quality: fraction of landings with >=1 susceptible occupant,
  re-sliced by confinement class and site class, with Wilson CIs and
  small-denominator flags;
* the confinement-latency distribution per host class
  (symptomatic -> reported -> ordered -> confined), split detection vs
  order vs admission latency;
* the emitter-class split (symptomatic-onboard vs never-symptomatic).

``--runs`` points at the directory tree holding ``<tier>/*.zip``.
``--json`` writes the aggregate dict alongside the markdown.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.readout_stats import quantiles, wilson_interval  # noqa: E402

CONFINEMENT_CLASSES = (
    "pre_confinement",
    "post_confinement",
    "never_confined_at_emit",
    "never_confined",
)
SITE_GROUPS = (
    "stateroom_pax",
    "stateroom_crew",
    "dining_pax",
    "toilet_pax",
    "venue_free",
    "dining_crew",
    "toilet_crew",
    "crew_zone",
    "medical",
)
EMITTER_CLASSES = (
    "symptomatic_onboard",
    "never_symptomatic_onboard",
    "never_symptomatic_course",
)
SMALL_DENOMINATOR = 30


# ── Loading ───────────────────────────────────────────────────────────


def _read_zip(zip_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with zipfile.ZipFile(zip_path) as archive:
        summary = json.loads(archive.read("summary.json"))
        venue = json.loads(gzip.decompress(archive.read("venue.json.gz")))
    return summary, venue


def load_cells(runs_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Map cell label -> [{run_id, seed, ignited, venue}] across zips."""
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for zip_path in sorted(runs_dir.rglob("*.zip")):
        summary, venue = _read_zip(zip_path)
        cell = zip_path.parent.name
        cells[cell].append({
            "run_id": str(summary.get("run_id", zip_path.stem)),
            "seed": int(summary.get("seed", venue.get("seed", -1))),
            "platform": str(
                summary.get("platform", venue.get("platform", "")),
            ),
            "ignited": bool(venue.get("ignited")),
            "venue": venue,
        })
    return dict(cells)


# ── Aggregation ───────────────────────────────────────────────────────


def _empty_cell() -> dict[str, Any]:
    return {"n": 0, "mass": 0.0, "susceptible_present": 0}


def _add_emit(
    table: dict[str, dict[str, Any]], key: str, row: dict[str, Any],
) -> None:
    cell = table.setdefault(key, _empty_cell())
    cell["n"] += 1
    cell["mass"] += float(row.get("episode_load", 0.0))
    if int(row.get("n_susceptible", 0)) >= 1:
        cell["susceptible_present"] += 1


def aggregate_cell(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one cell's runs into the census tables."""
    agg: dict[str, Any] = {
        "n_runs": len(runs),
        "n_ignited": sum(1 for r in runs if r["ignited"]),
        "emit_calls": 0,
        "emit_calls_no_records": 0,
        "n_emesis": 0,
        "n_unattributed": 0,
        "by_confinement_site": {},
        "by_confinement_emitter": {},
        "by_site_class": {},
        "confinement_actions": defaultdict(int),
        "confined_host_classes": defaultdict(int),
        "latency": defaultdict(list),
        "seeds": [],
    }
    for run in runs:
        venue = run["venue"]
        agg["emit_calls"] += int(venue.get("emit_calls", 0))
        agg["emit_calls_no_records"] += int(
            venue.get("emit_calls_no_records", 0),
        )
        agg["n_emesis"] += int(venue.get("n_emesis_emitted", 0))
        agg["n_unattributed"] += int(venue.get("n_unattributed", 0))
        agg["seeds"].append({
            "seed": run["seed"],
            "ignited": run["ignited"],
            "n_emesis": int(venue.get("n_emesis_emitted", 0)),
            "n_acquired": int(venue.get("n_acquired", 0)),
            "n_confined_hosts": sum(
                1 for h in venue.get("host_rows", [])
                if h.get("first_confined_epoch") is not None
            ),
        })
        for row in venue.get("emit_rows", []):
            conf = str(row.get("confinement_class", "unclassified"))
            site = str(row.get("site_group", "other"))
            emitter = str(row.get("emitter_class", "unknown"))
            _add_emit(
                agg["by_confinement_site"], f"{conf}|{site}", row,
            )
            _add_emit(
                agg["by_confinement_emitter"], f"{conf}|{emitter}", row,
            )
            _add_emit(
                agg["by_site_class"],
                f"{conf}|{row.get('site_class', 'other')}",
                row,
            )
        _aggregate_hosts(agg, venue)
        for event in venue.get("confinement_events", []):
            agg["confinement_actions"][str(event.get("action"))] += 1
    agg["confinement_actions"] = dict(agg["confinement_actions"])
    agg["confined_host_classes"] = dict(agg["confined_host_classes"])
    agg["latency"] = {
        key: quantiles(vals) for key, vals in agg["latency"].items()
    }
    return agg


def _aggregate_hosts(agg: dict[str, Any], venue: dict[str, Any]) -> None:
    for host in venue.get("host_rows", []):
        onset = host.get("first_noro_symptomatic_epoch")
        if onset is None:
            onset = host.get("first_symptomatic_epoch")
        reported = host.get("first_reported_epoch")
        ordered = host.get("first_order_epoch")
        confined = host.get("first_confined_epoch")
        if confined is not None:
            agg["confined_host_classes"][
                str(host.get("emitter_class", "unknown"))
            ] += 1
        if onset is None:
            continue
        if reported is not None:
            agg["latency"]["detect_reported"].append(reported - onset)
        if ordered is not None:
            agg["latency"]["onset_to_order"].append(ordered - onset)
        if confined is not None:
            agg["latency"]["onset_to_confined"].append(confined - onset)
        if ordered is not None and confined is not None:
            agg["latency"]["order_to_confined"].append(confined - ordered)


# ── Rendering ─────────────────────────────────────────────────────────


def _pct(k: int, n: int) -> str:
    if n <= 0:
        return "-"
    lo, hi = wilson_interval(k, n)
    flag = " *small*" if n < SMALL_DENOMINATOR else ""
    return f"{k}/{n} ({100 * k / n:.1f}%, CI {100 * lo:.0f}-{100 * hi:.0f}){flag}"


def render_markdown(cells: dict[str, Any]) -> str:
    """The ledger-ready markdown block for every loaded cell."""
    lines: list[str] = []
    for cell, agg in cells.items():
        lines.append(f"### `{cell}`")
        lines.append("")
        lines.append(
            f"runs {agg['n_runs']} | ignited {agg['n_ignited']} | "
            f"emit events {agg['n_emesis']} "
            f"(_emit_emesis invoked {agg['emit_calls']}x — once per "
            f"agent-epoch; record-less invocations are the idle path) | "
            f"unattributed {agg['n_unattributed']}",
        )
        lines.append("")
        lines += _landing_table(agg)
        lines += _placement_quality_table(agg)
        lines += _latency_table(agg)
        lines += _actions_table(agg)
    return "\n".join(lines)


def _landing_table(agg: dict[str, Any]) -> list[str]:
    table = agg["by_confinement_site"]
    groups = sorted(
        {key.split("|", 1)[1] for key in table},
        key=lambda g: (
            SITE_GROUPS.index(g) if g in SITE_GROUPS else len(SITE_GROUPS),
            g,
        ),
    )
    if not groups:
        return []
    header = "| confinement \\ site | " + " | ".join(groups) + " | total |"
    sep = "|---|" + "---|" * (len(groups) + 1)
    lines = [header, sep]
    for conf in CONFINEMENT_CLASSES:
        cells_n, cells_mass = [], []
        total_n = total_mass = 0
        for group in groups:
            entry = table.get(f"{conf}|{group}", _empty_cell())
            total_n += entry["n"]
            total_mass += entry["mass"]
            cells_n.append(str(entry["n"]))
            cells_mass.append(f"{entry['mass']:.3g}")
        lines.append(
            f"| **{conf}** (events) | " + " | ".join(cells_n)
            + f" | {total_n} |",
        )
        lines.append(
            f"| {conf} (mass) | " + " | ".join(cells_mass)
            + f" | {total_mass:.3g} |",
        )
    return lines + [""]


def _placement_quality_table(agg: dict[str, Any]) -> list[str]:
    table = agg["by_site_class"]
    if not table:
        return []
    lines = [
        "| confinement \\ site class | landings | >=1 susceptible |",
        "|---|---|---|",
    ]
    for key in sorted(table):
        entry = table[key]
        lines.append(
            f"| {key} | {entry['n']} | "
            f"{_pct(entry['susceptible_present'], entry['n'])} |",
        )
    return lines + [""]


def _latency_table(agg: dict[str, Any]) -> list[str]:
    latency = agg["latency"]
    if not latency:
        return []
    lines = [
        "| latency (epochs) | n | median | q25-q75 | min-max | mean |",
        "|---|---|---|---|---|---|",
    ]
    for key, q in latency.items():
        if q.get("n", 0) == 0:
            continue
        lines.append(
            f"| {key} | {q['n']} | {q['median']:.1f} | "
            f"{q['q25']:.1f}-{q['q75']:.1f} | {q['min']:.0f}-{q['max']:.0f} |"
            f" {q['mean']:.1f} |",
        )
    return lines + [""]


def _actions_table(agg: dict[str, Any]) -> list[str]:
    actions = agg["confinement_actions"]
    if not actions:
        return []
    lines = ["| action | count |", "|---|---|"]
    for action, count in sorted(actions.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {action} | {count} |")
    return lines + [""]


# ── CLI ───────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--json", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    runs_dir = Path(resolve_repo_path(str(REPO_ROOT), str(args.runs)))
    cells_raw = load_cells(runs_dir)
    cells = {
        cell: aggregate_cell(runs) for cell, runs in cells_raw.items()
    }
    print(render_markdown(cells))
    if args.json is not None:
        out = Path(resolve_repo_path(str(REPO_ROOT), str(args.json)))
        with validated_open(
            out, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
        ) as handle:
            json.dump(cells, handle, indent=2, default=str)


if __name__ == "__main__":
    main()
