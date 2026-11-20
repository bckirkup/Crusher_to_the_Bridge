#!/usr/bin/env python3
"""Commission a platform's Contam bundle after generation.

Performs the post-generation steps of the commissioning layer
(skill ``commissioning-contam-platform``):

1. Re-export ``contam/platform.prj`` + ``path_map.json`` in commissioned
   AHS terminal mode (``--ahs-terminal-mode commissioned``, hobbyist pack).
2. Solve the field with ContamX and write each ``open_deck``
   ``ambient_openings`` record's ``exchange_m3h`` (the gross solved outward
   flow) back into ``air_flow_paths.json``. ``makeup_louvre`` records stay
   0.0 — their solved flow is inward only.
3. Report the commissioned pressure picture (interior max |dP|).

Requires the ContamX binary (``third_party/contamx/contamx3``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engines.contamx_runner import SimResults, find_contamx, run_contamx  # noqa: E402
from tools.contam_prj_bridge import export_platform_to_prj  # noqa: E402


def commission(platform_id: str) -> dict[str, float]:
    platform_dir = os.path.join(REPO, "data", "platforms", platform_id)
    airflow_path = os.path.join(platform_dir, "air_flow_paths.json")
    prj_path = os.path.join(platform_dir, "contam", "platform.prj")
    path_map_path = os.path.join(platform_dir, "contam", "path_map.json")

    prj = export_platform_to_prj(
        platform_dir, prj_path, write_path_map=True,
        hobbyist=True, ahs_terminal_mode="commissioned",
    )
    print(f"Wrote {prj} + path_map.json")

    results = SimResults(
        run_contamx(prj_path, find_contamx(), allowed_roots=(REPO,)),
    )
    frame = results.steady_state_frame()
    flow0 = results.path_volumetric_flow_m3h(frame)

    path_map = json.loads(open(path_map_path, encoding="utf-8").read())
    entries = path_map if isinstance(path_map, list) else path_map.get("paths", path_map)
    outward: dict[str, float] = {}
    for entry in entries:
        if entry.get("kind") != "ambient_opening":
            continue
        nr = int(entry["path_nr"])
        if flow0[nr] > 0.0:
            zone = entry["from_zone"]
            outward[zone] = outward.get(zone, 0.0) + float(flow0[nr])

    airflow = json.loads(open(airflow_path, encoding="utf-8").read())
    # The path map has no per-opening identity, so a zone's solved outward
    # total can only be attributed when every opening on the zone is an
    # open_deck (makeup_louvre legs are inward-only and contribute nothing).
    by_zone: dict[str, list[dict]] = {}
    for opening in airflow.get("ambient_openings", []):
        by_zone.setdefault(opening["zone"], []).append(opening)
    fillable = {
        zone
        for zone, recs in by_zone.items()
        if all(r.get("type") in ("open_deck", "makeup_louvre") for r in recs)
    }
    filled: dict[str, float] = {}
    for opening in airflow.get("ambient_openings", []):
        if opening.get("type") != "open_deck":
            continue
        zone = opening["zone"]
        if zone not in fillable:
            print(f"WARNING: {zone} mixes open_deck with other opening "
                  "types; set its exchange_m3h per opening by hand")
            continue
        solved = outward.get(zone, 0.0)
        if solved <= 0.0:
            print(f"WARNING: no solved outward flow for open_deck on {zone}")
        opening["exchange_m3h"] = round(solved, 1)
        filled[zone] = opening["exchange_m3h"]
    with open(airflow_path, "w", encoding="utf-8") as fh:
        json.dump(airflow, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    for zone, value in filled.items():
        print(f"{platform_id}/{zone}: exchange_m3h = {value}")
    return filled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True,
                        help="Platform id under data/platforms/")
    args = parser.parse_args(argv)
    commission(args.platform)
    print("Next: tools/diag/contam_pressure_balance_diagnostic.py --hull "
          f"{args.platform} --lane commissioned && "
          f"tools/contam_commissioned_check.py --platform {args.platform}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
