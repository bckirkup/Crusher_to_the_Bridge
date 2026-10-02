"""COVID-TAKEOFF-ATTR-01 readout: pool instrumented cells into the ledger.

Reads the per-seed cell JSONs the Batch array wrote
(``tools/covid_takeoff_attribution.analyse_cell`` payloads — either fetched
from S3 or a local directory) and pools them into the numbers the ledger
reports: per-seed route shares and their median/IQR, pooled shedder and
epoch geometry, and the mechanism evidence bundle.

Usage:
    python3 tools/covid_takeoff_attr_readout.py \
        --cells-dir /path/to/cells --out readout.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    safe_listdir,
    validated_open,
)
from tools.covid_route_attribution import _quantiles  # noqa: E402

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

CHANNELS = (
    "cabin_mate_ring",
    "dining_ring",
    "near_field_plume",
    "zone_pool",
    "hvac_airborne",
    "contact",
    "other",
)


def _cell_summaries(cells_dir: str) -> list[dict[str, Any]]:
    safe_dir = resolve_repo_path(REPO_ROOT, cells_dir)
    rows = []
    for name in sorted(
        safe_listdir(safe_dir, allowed_roots=(REPO_ROOT,)),
    ):
        if not name.endswith(".json"):
            continue
        with validated_open(
            os.path.join(safe_dir, name), "r",
            allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            payload = json.load(handle)
        if "summary" not in payload:
            continue
        payload["_file"] = name
        rows.append(payload)
    return rows


def _median_band(dicts: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool same-shape quantile dicts by per-seed median + extremes."""
    vals = [d for d in dicts if d and d.get("median") is not None]
    if not vals:
        return {"n": 0}
    medians = sorted(float(d["median"]) for d in vals)
    q95s = sorted(float(d["q95"]) for d in vals if d.get("q95") is not None)
    return {
        "n": len(vals),
        "median_of_medians": _quantiles(medians)["median"],
        "median_min": medians[0],
        "median_max": medians[-1],
        "q95_max": q95s[-1] if q95s else None,
    }


def _mechanism_pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool the per-seed mechanism blocks (reach/footprint/susceptibility)."""
    mechanisms = [c["summary"]["mechanism"] for c in cells]
    footprint: dict[str, dict[str, Any]] = {}
    reach: dict[str, dict[str, Any]] = {}
    for channel in CHANNELS:
        footprint[channel] = _median_band([
            m.get("footprint_targets_by_epoch", {})
            .get(channel, {})
            .get("targets_by_epoch_quantiles")
            for m in mechanisms
        ])
        reach[channel] = _median_band([
            m.get("reach_per_shedder_epoch", {})
            .get(channel, {})
            .get("quantiles")
            for m in mechanisms
        ])
    return {
        "dosed_targets_by_epoch": _median_band([
            m.get("dosed_targets_by_epoch") for m in mechanisms
        ]),
        "footprint_targets_by_epoch": footprint,
        "reach_per_shedder_epoch": reach,
        "susceptibles_aboard": _median_band([
            m.get("susceptibles_aboard") for m in mechanisms
        ]),
        "challenged_share_of_aboard": {
            "mean": sum(
                float(m["susceptibility"]["challenged_share_of_aboard"])
                for m in mechanisms
            ) / len(mechanisms),
        },
        "challenged_uninfected_susceptibility": _median_band([
            m["susceptibility"].get("challenged_uninfected")
            for m in mechanisms
        ]),
        "challenged_hosts_total": sum(
            int(m["susceptibility"].get("challenged_hosts", 0))
            for m in mechanisms
        ),
        "never_challenged_hosts": sum(
            int(m["susceptibility"]
                .get("never_challenged_counterfactual", {})
                .get("n") or 0)
            for m in mechanisms
        ),
    }


_DROPLET_RINGS = (
    "cabin_mate_ring", "dining_ring", "near_field_plume", "zone_pool",
)


def _accumulate_cell(acc: dict[str, Any], cell: dict[str, Any]) -> None:
    summary = cell["summary"]
    acc["per_seed"].append({
        "seed": cell["cell"]["seed"],
        "infections": summary["infections_total"],
        "recorded_onsets": summary["recorded_onsets"],
        "route_split": (
            summary["route_split"].get("by_onset_share")
            or summary["route_split"]["by_infecting_epoch_dose"]
        ),
    })
    acc["infected_total"] += summary["infections_total"]
    acc["recorded_total"] += summary["recorded_onsets"]
    acc["takeoff_seeds"] += 1 if summary["takeoff"] else 0
    acc["confined"] += summary["confined_onsets"]
    acc["unattr"] += summary["mechanism"]["droplet_unattributed_onsets"]
    for row in cell.get("onsets", []):
        _accumulate_onset(acc, row)


def _accumulate_onset(acc: dict[str, Any], row: dict[str, Any]) -> None:
    for channel, dose in row["channel_dose_post"].items():
        acc["pooled_dose"][channel] += dose
    acc["pooled_lt"].update(_onset_lifetime_doses(row))
    acc["pooled_dom"][row["dominant_channel"]] += 1
    shares = row.get("shedder_credit") or {}
    if shares:
        top = max(shares.items(), key=lambda kv: kv[1])
        acc["pooled_dom_shedder"][int(top[0])] += 1
        for sid, share in shares.items():
            acc["pooled_credit"][int(sid)] += float(share)
    acc["epoch_hist"][row["epoch"]] += 1
    acc["day_hist"][row["day"]] += 1
    acc["venue_hist"][str(row["venue"])] += 1
    if row.get("susceptibility") is not None:
        acc["susc_infected"].append(float(row["susceptibility"]))
    acc["lam"].append(float(row["lambda_infecting"]))


def _onset_lifetime_doses(row: dict[str, Any]) -> Counter:
    """One onset's lifetime route dose, mapped onto the channels."""
    out: Counter = Counter()
    lt = row.get("lifetime_route", {})
    sub = row.get("lifetime_sub", {})
    sub_drop = sum(sub.get(c, 0.0) for c in _DROPLET_RINGS)
    for route, dose in lt.items():
        route = str(route).split(":", 1)[0]
        if route == "droplet" and sub_drop > 0:
            for channel in _DROPLET_RINGS:
                out[channel] += (
                    dose * sub.get(channel, 0.0) / sub_drop
                )
        elif route in ("contact", "direct_contact"):
            out["contact"] += dose
        elif route == "hvac_airborne":
            out["hvac_airborne"] += dose
        else:
            out["other"] += dose
    return out


def _pool_route_split(
    acc: dict[str, Any], cells: list[dict[str, Any]],
) -> dict[str, Any]:
    total_dose = sum(acc["pooled_dose"].values())
    total_lt = sum(acc["pooled_lt"].values())
    # Per-seed route-share distributions (the seed-to-seed spread is the
    # uncertainty the ledger reports, not the pooled mean).
    shares_by_channel = {
        c: _quantiles([
            row["route_split"][c] for row in acc["per_seed"]
            if row["route_split"].get(c) is not None
        ])
        for c in CHANNELS
    }
    return {
        "pooled_onset_share": {
            c: (
                sum(
                    row["channel_shares"].get(c, 0.0)
                    for cell in cells for row in cell.get("onsets", [])
                ) / max(acc["infected_total"], 1)
            )
            for c in CHANNELS
        },
        "pooled_infecting_epoch_dose": {
            c: (acc["pooled_dose"].get(c, 0.0) / total_dose
                if total_dose else None)
            for c in CHANNELS
        },
        "per_seed_share_quantiles": shares_by_channel,
        "dominant_channel_counts": dict(acc["pooled_dom"]),
        "pooled_lifetime_dose": {
            c: (acc["pooled_lt"].get(c, 0.0) / total_lt
                if total_lt else None)
            for c in CHANNELS
        },
    }


def _pool_geometry(acc: dict[str, Any], n: int) -> dict[str, Any]:
    sorted_credit = sorted(acc["pooled_credit"].values(), reverse=True)
    sorted_dom = sorted(acc["pooled_dom_shedder"].values(), reverse=True)
    epoch_hist = acc["epoch_hist"]
    return {
        "onsets_per_shedder_credit": {
            "n_shedders": len(sorted_credit),
            "top1": sorted_credit[0] if sorted_credit else None,
            "top5_share": sum(sorted_credit[:5]) / n,
            "quantiles": _quantiles(sorted_credit),
        },
        "onsets_per_shedder_dominant": {
            "n_shedders": len(sorted_dom),
            "top1": sorted_dom[0] if sorted_dom else None,
            "top5_share": sum(sorted_dom[:5]) / n,
            "quantiles": _quantiles([float(v) for v in sorted_dom]),
        },
        "onsets_by_epoch": {
            "n_epochs": len(epoch_hist),
            "top5_share": (
                sum(sorted(epoch_hist.values(), reverse=True)[:5]) / n
            ),
            "max_epoch": max(epoch_hist, key=epoch_hist.get)
            if epoch_hist else None,
            "quantiles": _quantiles(
                [float(v) for v in epoch_hist.values()],
            ),
        },
        "onsets_per_day": {
            str(d): n_ for d, n_ in sorted(acc["day_hist"].items())
        },
        "onsets_per_venue": dict(acc["venue_hist"].most_common(16)),
    }


def pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-seed summaries into the campaign readout."""
    acc: dict[str, Any] = {
        "per_seed": [],
        "pooled_dose": Counter(),
        "pooled_lt": Counter(),
        "pooled_dom": Counter(),
        "pooled_dom_shedder": Counter(),
        "pooled_credit": Counter(),
        "epoch_hist": Counter(),
        "day_hist": Counter(),
        "venue_hist": Counter(),
        "confined": 0,
        "infected_total": 0,
        "recorded_total": 0,
        "takeoff_seeds": 0,
        "susc_infected": [],
        "lam": [],
        "unattr": 0,
    }
    for cell in cells:
        _accumulate_cell(acc, cell)
    n = max(acc["infected_total"], 1)
    return {
        "n_cells": len(cells),
        "takeoff_seeds": acc["takeoff_seeds"],
        "infections_total": acc["infected_total"],
        "recorded_onsets_total": acc["recorded_total"],
        "confined_onsets": acc["confined"],
        "droplet_unattributed_onsets": acc["unattr"],
        "route_split": _pool_route_split(acc, cells),
        "geometry": _pool_geometry(acc, n),
        "susceptibility_infected": _quantiles(acc["susc_infected"]),
        "lambda_infecting": _quantiles(acc["lam"]),
        "mechanism": _mechanism_pool(cells),
        "per_seed": acc["per_seed"],
    }


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cells-dir", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    cells = _cell_summaries(args.cells_dir)
    if not cells:
        raise SystemExit(f"no cell payloads under {args.cells_dir}")
    text = json.dumps(pool(cells), indent=1, default=str)
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
