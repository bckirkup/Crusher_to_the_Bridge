#!/usr/bin/env python3
"""D8 witness: which ContamX element carries two-way ambient exchange.

CONTAM-AMBIENT-OPENING-SCHEMA-01. One scratch ``ambient_openings`` record is
declared **in memory** on one hull (nothing under ``data/`` is read-modified
or written), the hull is exported once per ``ambient_opening_model`` and
solved by ContamX, and the solved flows through the opening are reported:

* ``single_orifice`` — one ``plr_orfc`` of the declared area
* ``two_way_door`` — one ContamX ``dor_door`` two-way element
* ``paired_orifices`` — two ``plr_orfc`` of half the area at 1/4 and 3/4 of
  the zone height

Each model is solved isothermal (zone at ambient temperature) and with the
witness deck offset from ambient, because buoyancy is what drives
counter-flow through an opening with near-zero net pressure difference.

``flow0`` is what the ``.sim`` reader hands the field lane; ``flow1`` is the
two-way element's counter-flow, which no transport consumer reads.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import Any

_SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPT_ROOT)

from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.py_contam_bridge import AMBIENT_OPENING_KIND, AMBIENT_OPENINGS_KEY  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)
from tools.contamw34_prj import AMBIENT_OPENING_MODELS, export_contamw34  # noqa: E402

DEFAULT_HULL = "expedition_cruise_300"
DEFAULT_ZONE = "Pool_Deck"
DEFAULT_AREA_M2 = 40.0
DEFAULT_OFFSETS_K = (0.0, 5.0)
_PLATFORMS_REL = os.path.join("data", "platforms")
_PRJ_NAME = "platform.prj"
_SECONDS_PER_HOUR = 3600.0


def _load_json(rel_path: str) -> Any:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def scratch_airflow(airflow: dict[str, Any], zone: str, area_m2: float) -> dict[str, Any]:
    """Copy of *airflow* with one in-memory open-deck record on *zone*."""
    record = {
        "zone": zone, "type": "open_deck", "area_m2": area_m2,
        "exchange_m3h": None, "azimuth_deg": None, "schedule": "always_open",
    }
    return {**airflow, AMBIENT_OPENINGS_KEY: [record]}


def _solve(prj_text: str, binary: str) -> SimResults:
    with tempfile.TemporaryDirectory(prefix="ambient_opening_d8_") as tmp_dir:
        roots = (REPO_ROOT, tmp_dir)
        prj_path = os.path.join(tmp_dir, _PRJ_NAME)
        with validated_open(prj_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(prj_text)
        return SimResults(run_contamx(prj_path, binary, allowed_roots=roots))


def _opening_rows(
    results: SimResults, path_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    frame = results.steady_state_frame()
    flow0 = results.path_volumetric_flow_m3h(frame)
    # Same kg/s -> m3/h factor the reader applied to Flow0, recovered per path.
    flow1_kg_s = dict(zip(frame.path_nr.tolist(), frame.path_flow1_kg_s.tolist(), strict=True))
    flow0_kg_s = dict(zip(frame.path_nr.tolist(), frame.path_flow_kg_s.tolist(), strict=True))
    rows = []
    for entry in path_map:
        if entry["kind"] != AMBIENT_OPENING_KIND:
            continue
        nr = int(entry["path_nr"])
        factor = flow0[nr] / flow0_kg_s[nr] if flow0_kg_s[nr] else 0.0
        rows.append({
            "path_nr": nr,
            "flow0_m3h": flow0[nr],
            "flow1_m3h": flow1_kg_s[nr] * factor,
        })
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, float]:
    """What the field lane can see (Flow0 only) versus what ContamX solved."""
    flow0 = [r["flow0_m3h"] for r in rows]
    return {
        "n_paths": len(rows),
        "flow0_outward_m3h": sum(f for f in flow0 if f > 0.0),
        "flow0_inward_m3h": -sum(f for f in flow0 if f < 0.0),
        "flow0_net_outward_m3h": sum(flow0),
        "flow1_unread_m3h": sum(abs(r["flow1_m3h"]) for r in rows),
    }


def run_witness(
    hull: str, zone: str, area_m2: float, offsets_k: tuple[float, ...], binary: str,
) -> dict[str, Any]:
    base = os.path.join(_PLATFORMS_REL, validate_path_component(hull, label="hull"))
    spatial = _load_json(os.path.join(base, "spatial_layout.json"))
    airflow = scratch_airflow(
        _load_json(os.path.join(base, "air_flow_paths.json")), zone, area_m2,
    )
    deck = next(z["deck"] for z in spatial["zones"] if z["id"] == zone)
    cases = []
    for offset in offsets_k:
        for model in AMBIENT_OPENING_MODELS:
            overrides = {
                "ambient_opening_model": model,
                "deck_temp_offset_K": {deck: offset},
            }
            prj_text, path_map = export_contamw34(
                spatial, airflow, hobbyist=True, overrides=overrides,
            )
            rows = _opening_rows(_solve(prj_text, binary), path_map)
            cases.append({
                "deck_temp_offset_K": offset,
                "model": model,
                "paths": rows,
                **summarize(rows),
            })
    return {
        "hull": hull, "zone": zone, "deck": deck, "area_m2": area_m2,
        "lane": "hobbyist_design", "cases": cases,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hull", default=DEFAULT_HULL)
    parser.add_argument("--zone", default=DEFAULT_ZONE)
    parser.add_argument("--area-m2", type=float, default=DEFAULT_AREA_M2)
    parser.add_argument(
        "--offset-k", type=float, action="append",
        help="Witness-deck temperature offset from ambient [K]; repeatable.",
    )
    parser.add_argument(
        "--out", default="telemetry_buffer/ambient_opening_d8_witness/results.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    binary = find_contamx()
    if binary is None:
        raise ContamXUnavailable("ContamX binary not found")
    report = run_witness(
        args.hull, args.zone, args.area_m2,
        tuple(args.offset_k or DEFAULT_OFFSETS_K), binary,
    )
    out_path = resolve_repo_path(REPO_ROOT, args.out)
    prepare_output_directory(os.path.dirname(out_path), allowed_roots=(REPO_ROOT,))
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("dT_K model n_paths flow0_out flow0_in flow0_net flow1_unread [m3/h]")
    for case in report["cases"]:
        print(
            f"{case['deck_temp_offset_K']:g} {case['model']} {case['n_paths']} "
            f"{case['flow0_outward_m3h']:.2f} {case['flow0_inward_m3h']:.2f} "
            f"{case['flow0_net_outward_m3h']:.2f} {case['flow1_unread_m3h']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
