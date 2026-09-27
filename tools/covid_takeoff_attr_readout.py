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

from tools.covid_route_attribution import _quantiles  # noqa: E402

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
    rows = []
    for name in sorted(os.listdir(cells_dir)):
        if not name.endswith(".json"):
            continue
        payload = json.load(open(os.path.join(cells_dir, name)))
        if "summary" not in payload:
            continue
        payload["_file"] = name
        rows.append(payload)
    return rows


def pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-seed summaries into the campaign readout."""
    per_seed = []
    pooled_dose = Counter()
    pooled_lt = Counter()
    pooled_dom = Counter()
    pooled_dom_shedder = Counter()
    pooled_credit: Counter = Counter()
    epoch_hist = Counter()
    day_hist = Counter()
    venue_hist = Counter()
    confined = 0
    infected_total = 0
    recorded_total = 0
    takeoff_seeds = 0
    susc_infected: list[float] = []
    lam: list[float] = []
    unattr = 0
    for cell in cells:
        summary = cell["summary"]
        per_seed.append({
            "seed": cell["cell"]["seed"],
            "infections": summary["infections_total"],
            "recorded_onsets": summary["recorded_onsets"],
            "route_split": (
                summary["route_split"].get("by_onset_share")
                or summary["route_split"]["by_infecting_epoch_dose"]
            ),
        })
        infected_total += summary["infections_total"]
        recorded_total += summary["recorded_onsets"]
        takeoff_seeds += 1 if summary["takeoff"] else 0
        confined += summary["confined_onsets"]
        unattr += summary["mechanism"]["droplet_unattributed_onsets"]
        for row in cell.get("onsets", []):
            for channel, dose in row["channel_dose_post"].items():
                pooled_dose[channel] += dose
            lt = row.get("lifetime_route", {})
            sub = row.get("lifetime_sub", {})
            sub_drop = sum(
                sub.get(c, 0.0)
                for c in ("cabin_mate_ring", "dining_ring",
                          "near_field_plume", "zone_pool")
            )
            for route, dose in lt.items():
                route = str(route).split(":", 1)[0]
                if route == "droplet" and sub_drop > 0:
                    for channel in ("cabin_mate_ring", "dining_ring",
                                    "near_field_plume", "zone_pool"):
                        pooled_lt[channel] += (
                            dose * sub.get(channel, 0.0) / sub_drop
                        )
                elif route in ("contact", "direct_contact"):
                    pooled_lt["contact"] += dose
                elif route == "hvac_airborne":
                    pooled_lt["hvac_airborne"] += dose
                else:
                    pooled_lt["other"] += dose
            pooled_dom[row["dominant_channel"]] += 1
            shares = row.get("shedder_credit") or {}
            if shares:
                top = max(shares.items(), key=lambda kv: kv[1])
                pooled_dom_shedder[int(top[0])] += 1
                for sid, share in shares.items():
                    pooled_credit[int(sid)] += float(share)
            epoch_hist[row["epoch"]] += 1
            day_hist[row["day"]] += 1
            venue_hist[str(row["venue"])] += 1
            if row.get("susceptibility") is not None:
                susc_infected.append(float(row["susceptibility"]))
            lam.append(float(row["lambda_infecting"]))
    total_dose = sum(pooled_dose.values())
    total_lt = sum(pooled_lt.values())
    sorted_credit = sorted(pooled_credit.values(), reverse=True)
    sorted_dom = sorted(pooled_dom_shedder.values(), reverse=True)
    n = max(infected_total, 1)
    # Per-seed route-share distributions (the seed-to-seed spread is the
    # uncertainty the ledger reports, not the pooled mean).
    shares_by_channel = {
        c: _quantiles([
            row["route_split"][c] for row in per_seed
            if row["route_split"].get(c) is not None
        ])
        for c in CHANNELS
    }
    return {
        "n_cells": len(cells),
        "takeoff_seeds": takeoff_seeds,
        "infections_total": infected_total,
        "recorded_onsets_total": recorded_total,
        "confined_onsets": confined,
        "droplet_unattributed_onsets": unattr,
        "route_split": {
            "pooled_onset_share": {
                c: (
                    sum(
                        row["channel_shares"].get(c, 0.0)
                        for cell in cells for row in cell.get("onsets", [])
                    ) / max(infected_total, 1)
                )
                for c in CHANNELS
            },
            "pooled_infecting_epoch_dose": {
                c: (pooled_dose.get(c, 0.0) / total_dose
                    if total_dose else None)
                for c in CHANNELS
            },
            "per_seed_share_quantiles": shares_by_channel,
            "dominant_channel_counts": dict(pooled_dom),
            "pooled_lifetime_dose": {
                c: (pooled_lt.get(c, 0.0) / total_lt if total_lt else None)
                for c in CHANNELS
            },
        },
        "geometry": {
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
            "onsets_per_epoch": {
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
                str(d): n_ for d, n_ in sorted(day_hist.items())
            },
            "onsets_per_venue": dict(venue_hist.most_common(16)),
        },
        "susceptibility_infected": _quantiles(susc_infected),
        "lambda_infecting": _quantiles(lam),
        "per_seed": per_seed,
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
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
