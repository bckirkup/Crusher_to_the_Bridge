#!/usr/bin/env python3
"""NORO-VENUE-01 readout: aggregate venue-placement census zips.

Reads every ``<cell>/*.zip`` written by ``tools/noro_diag/venue_placement_census.py``
and emits the ledger-ready tables:

* the join integrity row (emitted events, unattributed, record-less calls);
* the 3xN landing table: confinement class x site group, in both event
  counts and episode-load mass;
* the NORO-VENUE-02 first-emesis table: ``first_emit`` rows only,
  site class x emitter class, with the ``ordered_mobile`` count (emits
  inside the escort window) per site class;
* the conversion check: per-cell acquisitions and attack rates read from
  each zip's ``summary.json`` ``derived`` block;
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
from tools.diag.readout_common import quantiles, wilson_interval  # noqa: E402

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

# NORO-DETECT-01 emitter-class axis: whether the emitting host was in
# the compliant mobile window (ordered or order-pending but still
# unconfined), a refuser, already confined, or never ordered.
_WINDOW_CLASSES = (
    "compliant_in_window",
    "refuser",
    "confined",
    "never_ordered",
)


def _emit_window_class(row: dict[str, Any]) -> str:
    """The emitter's order channel for this landing.

    New cells stamp ``emitter_channel`` at join time against the host's
    whole-voyage timeline; fall back to the emit-time order subclass on
    older payloads that predate the stamp.
    """
    stamped = row.get("emitter_channel")
    if stamped:
        return str(stamped)
    subclass = str(row.get("order_subclass", ""))
    if subclass == "ordered_refused":
        return "refuser"
    if subclass in (
        "pre_order", "ordered_mobile", "ordered_not_admitted",
    ):
        return "compliant_in_window"
    if row.get("confinement_class") == "post_confinement":
        return "confined"
    return "never_ordered"


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
            "escort_delay_hours": summary.get("escort_delay_hours"),
            "escort_delay_epochs": venue.get("escort_delay_epochs"),
            "clinic_wait_hours": summary.get("clinic_wait_hours"),
            "clinic_wait_epochs": venue.get("clinic_wait_epochs"),
            "symptomatic_order_trigger": venue.get(
                "symptomatic_order_trigger",
            ),
            "num_agents": summary.get("num_agents"),
            "derived": summary.get("derived") or {},
            "parameters": summary.get("parameters") or {},
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
        "n_acquired": 0,
        "n_acquired_ignited": 0,
        "by_confinement_site": {},
        "by_confinement_emitter": {},
        "by_site_class": {},
        "first_emit_table": {},
        "first_emit_mobile": 0,
        "first_emit_window": {},
        "subsequent_emit_window": {},
        "escort_delay_epochs": {
            r["escort_delay_epochs"] for r in runs
        },
        "clinic_wait_epochs": sorted({
            v for v in (r["clinic_wait_epochs"] for r in runs)
            if v is not None
        }),
        "clinic_wait_hours": sorted({
            v for v in (r["clinic_wait_hours"] for r in runs)
            if v is not None
        }),
        "symptomatic_order_trigger": sorted({
            str(v) for v in (
                r["symptomatic_order_trigger"] for r in runs
            )
            if v is not None
        }),
        "n_sign_observed": 0,
        "sign_gated_final": 0,
        "detection_channels": defaultdict(int),
        "attack_rates": defaultdict(list),
        "num_agents": set(),
        "confinement_actions": defaultdict(int),
        "confined_host_classes": defaultdict(int),
        "latency": defaultdict(list),
        "seeds": [],
    }
    agg["escort_delay_epochs"] = sorted(
        v for v in agg["escort_delay_epochs"] if v is not None
    )
    for run in runs:
        _accumulate_run(agg, run)
        _aggregate_emit_rows(agg, run["venue"])
        _aggregate_hosts(agg, run["venue"])
        agg["n_sign_observed"] += int(
            run["venue"].get("n_sign_observed", 0),
        )
        agg["sign_gated_final"] += int(
            run["venue"].get("sign_gated_final", 0),
        )
        for event in run["venue"].get("confinement_events", []):
            agg["confinement_actions"][str(event.get("action"))] += 1
            channel = event.get("detection_channel")
            if channel is not None:
                agg["detection_channels"][str(channel)] += 1
    agg["confinement_actions"] = dict(agg["confinement_actions"])
    agg["detection_channels"] = dict(agg["detection_channels"])
    agg["confined_host_classes"] = dict(agg["confined_host_classes"])
    agg["attack_rates"] = {
        key: quantiles(vals) for key, vals in agg["attack_rates"].items()
    }
    agg["num_agents"] = sorted(agg["num_agents"])
    agg["latency"] = {
        key: quantiles(vals) for key, vals in agg["latency"].items()
    }
    return agg


def _accumulate_run(agg: dict[str, Any], run: dict[str, Any]) -> None:
    venue = run["venue"]
    agg["emit_calls"] += int(venue.get("emit_calls", 0))
    agg["emit_calls_no_records"] += int(
        venue.get("emit_calls_no_records", 0),
    )
    agg["n_emesis"] += int(venue.get("n_emesis_emitted", 0))
    agg["n_unattributed"] += int(venue.get("n_unattributed", 0))
    acquired = int(venue.get("n_acquired", 0))
    agg["n_acquired"] += acquired
    if run["ignited"]:
        agg["n_acquired_ignited"] += acquired
    derived = run.get("derived") or {}
    for key in _ATTACK_RATE_KEYS:
        value = derived.get(key)
        if isinstance(value, (int, float)):
            agg["attack_rates"][key].append(float(value))
    if run.get("num_agents"):
        agg["num_agents"].add(int(run["num_agents"]))
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


def _aggregate_emit_rows(
    agg: dict[str, Any], venue: dict[str, Any],
) -> None:
    for row in venue.get("emit_rows", []):
        conf = str(row.get("confinement_class", "unclassified"))
        site = str(row.get("site_group", "other"))
        emitter = str(row.get("emitter_class", "unknown"))
        _add_emit(agg["by_confinement_site"], f"{conf}|{site}", row)
        _add_emit(agg["by_confinement_emitter"], f"{conf}|{emitter}", row)
        _add_emit(
            agg["by_site_class"],
            f"{conf}|{row.get('site_class', 'other')}",
            row,
        )
        window = _emit_window_class(row)
        window_key = f"{row.get('site_class', 'other')}|{window}"
        if not row.get("first_emit"):
            _add_emit(agg["subsequent_emit_window"], window_key, row)
            continue
        key = f"{row.get('site_class', 'other')}|{emitter}"
        _add_emit(agg["first_emit_table"], key, row)
        _add_emit(agg["first_emit_window"], window_key, row)
        # ordered_not_admitted at the confined epoch is still mobile:
        # transmission runs before the escorted admission lands
        # end-of-epoch.
        if row.get("order_subclass") in (
            "ordered_mobile", "ordered_not_admitted",
        ):
            agg["first_emit_mobile"] += 1


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
        _host_latency(agg, onset, reported, ordered, confined)


def _host_latency(
    agg: dict[str, Any],
    onset: Any,
    reported: Any,
    ordered: Any,
    confined: Any,
) -> None:
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
    lo, hi = wilson_interval(k, n, z=1.96)
    flag = " *small*" if n < SMALL_DENOMINATOR else ""
    return f"{k}/{n} ({100 * k / n:.1f}%, CI {100 * lo:.0f}-{100 * hi:.0f}){flag}"


def render_markdown(cells: dict[str, Any]) -> str:
    """The ledger-ready markdown block for every loaded cell."""
    lines: list[str] = []
    for cell, agg in cells.items():
        lines.append(f"### `{cell}`")
        lines.append("")
        trigger = "/".join(agg.get("symptomatic_order_trigger") or []) or "-"
        clinic = "/".join(
            str(v) for v in agg.get("clinic_wait_epochs") or []
        ) or "-"
        lines.append(
            f"runs {agg['n_runs']} | ignited {agg['n_ignited']} | "
            f"emit events {agg['n_emesis']} "
            f"(_emit_emesis invoked {agg['emit_calls']}x — once per "
            f"agent-epoch; record-less invocations are the idle path) | "
            f"unattributed {agg['n_unattributed']} | "
            f"trigger {trigger} | clinic wait {clinic} ep | "
            f"sign observed {agg['n_sign_observed']} hosts | "
            f"still sign-gated {agg['sign_gated_final']}",
        )
        lines.append("")
        lines += _landing_table(agg)
        lines += _first_emit_table(agg)
        lines += _window_emit_table(
            agg["first_emit_window"], "first emesis",
        )
        lines += _window_emit_table(
            agg["subsequent_emit_window"], "subsequent emeses",
        )
        lines += _conversion_block(cell, cells[cell])
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


def _first_emit_table(agg: dict[str, Any]) -> list[str]:
    """NORO-VENUE-02 first-emesis landing census (``first_emit`` rows)."""
    table = agg["first_emit_table"]
    if not table:
        return []
    escort = agg.get("escort_delay_epochs") or []
    escort_label = "/".join(str(v) for v in escort) or "-"
    lines = [
        f"First-emesis landings (escort k = {escort_label} ep; "
        f"in-window mobile rows: {agg['first_emit_mobile']}):",
        "",
        "| site class | emitter class | first landings | mass | "
        ">=1 susceptible |",
        "|---|---|---|---|---|",
    ]
    for key in sorted(table):
        site_class, emitter = key.split("|", 1)
        entry = table[key]
        lines.append(
            f"| {site_class} | {emitter} | {entry['n']} | "
            f"{entry['mass']:.3g} | "
            f"{_pct(entry['susceptible_present'], entry['n'])} |",
        )
    return lines + [""]


def _window_emit_table(
    table: dict[str, dict[str, Any]], label: str,
) -> list[str]:
    """Site-class x emitter window-class table (NORO-DETECT-01)."""
    if not table:
        return []
    lines = [
        f"{label.capitalize()} by site class x emitter channel:",
        "",
        "| site class | emitter channel | landings | mass | "
        ">=1 susceptible |",
        "|---|---|---|---|---|",
    ]
    for key in sorted(
        table,
        key=lambda k: (
            k.split("|", 1)[0],
            _WINDOW_CLASSES.index(k.split("|", 1)[1])
            if k.split("|", 1)[1] in _WINDOW_CLASSES
            else len(_WINDOW_CLASSES),
        ),
    ):
        site_class, window = key.split("|", 1)
        entry = table[key]
        lines.append(
            f"| {site_class} | {window} | {entry['n']} | "
            f"{entry['mass']:.3g} | "
            f"{_pct(entry['susceptible_present'], entry['n'])} |",
        )
    return lines + [""]


def _conversion_block(cell: str, agg: dict[str, Any]) -> list[str]:
    """Acquisitions + attack rates per cell for the VENUE-02 conversion check."""
    ignited = [s for s in agg["seeds"] if s["ignited"]]
    mean_acquired = (
        agg["n_acquired_ignited"] / len(ignited) if ignited else None
    )
    lines = [
        f"Conversion for `{cell}` (ignited runs only):",
        "",
        "| metric | value |",
        _SEP2,
        f"| ignited runs | {len(ignited)} / {agg['n_runs']} |",
        "| acquisitions, mean per ignited run | "
        + (f"{mean_acquired:.2f}" if mean_acquired is not None else "-")
        + " |",
    ]
    rates = agg.get("attack_rates") or {}
    for key, q in rates.items():
        if q.get("n", 0) == 0:
            continue
        lines.append(
            f"| {key} (mean over {q['n']} runs) | {q['mean']:.4f} |",
        )
    return lines + [""]


_SEP2 = "|---|---|"

_ATTACK_RATE_KEYS = (
    "infection_attack_rate",
    "infection_attack_rate_passenger",
    "infection_attack_rate_crew",
)


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
    lines = ["| action | count |", _SEP2]
    for action, count in sorted(actions.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {action} | {count} |")
    channels = agg.get("detection_channels") or {}
    if channels:
        lines.append("")
        lines += ["| detection channel | orders+refusals |", _SEP2]
        for channel, count in sorted(channels.items()):
            lines.append(f"| {channel} | {count} |")
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
            str(out), "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
        ) as handle:
            json.dump(cells, handle, indent=2, default=str)


if __name__ == "__main__":
    main()
