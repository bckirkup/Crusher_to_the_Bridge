#!/usr/bin/env python3
"""Conversion check for the NORO-DETECT-01 placement census.

Two questions per cell arm:

1. Did any acquisition trace to a shared-venue emesis landing? An
   acquisition is attributed to a landing when its (epoch, location)
   coincides with an emit row classed ``shared_venue`` (the aerosol /
   patch pathway carries no source id), or when ``source_agent_id``
   names a host who filed a shared-venue landing in that voyage.
2. Did non-vomiting symptomatics keep their confinement channel? The
   onset channel must still fire under the sign trigger — count
   ``detection_channel == "onset"`` confinement events per arm. Zero
   with a confinement-mass shift is a defect, not a finding.

Usage:
    python3 tools/noro_diag/venue_conversion_check.py \
        --runs results/noro_detect_01 --json out.json
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

_SHARED_SITE = "shared_venue"


def _load_venue(zip_path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            raw = zf.read("venue.json.gz")
    except (KeyError, zipfile.BadZipFile, OSError):
        return None
    return json.loads(gzip.decompress(raw))


def analyze_payload(v: dict[str, Any]) -> dict[str, Any]:
    shared_keys = {
        (r["epoch"], r["location"])
        for r in v["emit_rows"]
        if r.get("site_class") == _SHARED_SITE
    }
    shared_emitters = {
        r["agent_id"]
        for r in v["emit_rows"]
        if r.get("site_class") == _SHARED_SITE
    }
    attributed = []
    for a in v["acquisition_rows"]:
        by_spot = (a["epoch"], a["location"]) in shared_keys
        by_source = (
            a.get("source_agent_id") is not None
            and a["source_agent_id"] in shared_emitters
        )
        if by_spot or by_source:
            attributed.append(
                {
                    "agent_id": a["agent_id"],
                    "epoch": a["epoch"],
                    "location": a["location"],
                    "pathway": a.get("dominant_pathway"),
                    "via": "spot" if by_spot else "source",
                },
            )
    channels = defaultdict(int)
    for e in v["confinement_events"]:
        if e.get("action") in ("escort_order", "immediate_compliance",
                               "ordered_refused"):
            channels[e.get("detection_channel") or "unstamped"] += 1
    return {
        "seed": v["seed"],
        "ignited": v["ignited"],
        "n_acquired": v["n_acquired"],
        "n_shared_landings": len(shared_keys),
        "n_shared_emitters": len(shared_emitters),
        "n_acq_shared_attributed": len(attributed),
        "attributed": attributed,
        "order_channels": dict(channels),
        "n_unattributed": v["n_unattributed"],
        "sign_gated_final": v["sign_gated_final"],
        "n_sign_observed": v["n_sign_observed"],
        "clinic_wait_epochs": v["clinic_wait_epochs"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True,
                        help="Directory tree of <cell>/*.zip payloads")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for zpath in sorted(args.runs.glob("*/*.zip")):
        v = _load_venue(zpath)
        if v is None:
            print(f"WARN unreadable {zpath}", file=sys.stderr)
            continue
        cells[zpath.parent.name].append(analyze_payload(v))

    report: dict[str, Any] = {}
    for cell in sorted(cells):
        runs = cells[cell]
        total_acq = sum(r["n_acquired"] for r in runs)
        total_attr = sum(r["n_acq_shared_attributed"] for r in runs)
        onset_orders = sum(r["order_channels"].get("onset", 0) for r in runs)
        sign_orders = sum(r["order_channels"].get("sign", 0) for r in runs)
        unstamped = sum(r["order_channels"].get("unstamped", 0) for r in runs)
        report[cell] = {
            "n_runs": len(runs),
            "n_ignited": sum(1 for r in runs if r["ignited"]),
            "n_acquired": total_acq,
            "n_shared_landings": sum(r["n_shared_landings"] for r in runs),
            "n_acq_shared_attributed": total_attr,
            "onset_channel_orders": onset_orders,
            "sign_channel_orders": sign_orders,
            "unstamped_orders": unstamped,
            "n_unattributed": sum(r["n_unattributed"] for r in runs),
            "attributed_acquisitions": [
                {"seed": r["seed"], **a}
                for r in runs for a in r["attributed"]
            ],
        }
        print(
            f"{cell:34s} runs={len(runs):3d} ignited={report[cell]['n_ignited']:3d} "
            f"acq={total_acq:3d} shared_land={report[cell]['n_shared_landings']:3d} "
            f"acq_attr={total_attr:2d} onset_ord={onset_orders:4d} "
            f"sign_ord={sign_orders:4d} unatt={report[cell]['n_unattributed']:3d}",
        )
    if args.json:
        args.json.write_text(json.dumps(report, indent=1))
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
