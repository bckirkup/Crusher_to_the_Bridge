#!/usr/bin/env python3
"""Fleet enumeration of solved ``envelope_leak`` flows (CONTAM-FIELD-ENVELOPE-BOUNDARY-01).

Solves each hull's ContamX field and reports, per hull and lane, which
``envelope_leak`` paths run outward (zone -> ambient, positive Flow0) and how
much air they carry. Lanes:

* ``authored`` — the committed ``contam/platform.prj`` + ``path_map.json``
* ``design`` — a fresh in-memory export with ``ahs_terminal_mode="design"``

Nothing is written into ``data/``; the report goes under ``telemetry_buffer/``.
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
from engines.contamx_transport import (  # noqa: E402
    ENVELOPE_LEAK_KIND,
    is_outward_envelope_leak,
)
from simulation_utils.paths import (  # noqa: E402
    REPO_ROOT,
    prepare_output_directory,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

LANES = ("authored", "design")
_PLATFORMS_REL = os.path.join("data", "platforms")


def _load_json(rel_path: str) -> Any:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _read_text(rel_path: str) -> str:
    full = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(full, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return fh.read()


def bundled_hulls() -> list[str]:
    """Hulls that commit a ``contam/path_map.json`` beside a ``platform.prj``."""
    root = resolve_repo_path(REPO_ROOT, _PLATFORMS_REL)
    return sorted(
        name
        for name in os.listdir(root)
        if os.path.isfile(os.path.join(root, name, "contam", "path_map.json"))
        and os.path.isfile(os.path.join(root, name, "contam", "platform.prj"))
    )


def _solve(prj_text: str, binary: str) -> dict[int, float]:
    with tempfile.TemporaryDirectory(prefix="contam_envelope_enum_") as tmp_dir:
        roots = (REPO_ROOT, tmp_dir)
        prj_path = os.path.join(tmp_dir, "platform.prj")
        with validated_open(prj_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(prj_text)
        sim_path = run_contamx(prj_path, binary, allowed_roots=roots)
        return SimResults(sim_path, allowed_roots=roots).path_volumetric_flow_m3h()


def _lane_inputs(hull: str, lane: str) -> tuple[str, list[dict[str, Any]]]:
    base = os.path.join(_PLATFORMS_REL, hull)
    if lane == "authored":
        return (
            _read_text(os.path.join(base, "contam", "platform.prj")),
            _load_json(os.path.join(base, "contam", "path_map.json")),
        )
    spatial = _load_json(os.path.join(base, "spatial_layout.json"))
    airflow = _load_json(os.path.join(base, "air_flow_paths.json"))
    overrides = load_hobbyist_overrides(resolve_repo_path(REPO_ROOT, base))
    return export_prj_with_path_map(
        spatial, airflow, hobbyist=True, overrides=overrides,
        ahs_terminal_mode="design",
    )


def summarize_envelope_leaks(
    entries: list[dict[str, Any]],
    flows: dict[int, float],
    known_zones: set[str],
) -> dict[str, Any]:
    """Split solved envelope leaks into outward (boundary sink) and inward."""
    outward: list[dict[str, Any]] = []
    inward_total = 0.0
    leak_count = 0
    for entry in sorted(entries, key=lambda e: int(e["path_nr"])):
        if str(entry.get("kind", "")) != ENVELOPE_LEAK_KIND:
            continue
        leak_count += 1
        flow = float(flows.get(int(entry["path_nr"]), 0.0))
        if is_outward_envelope_leak(entry, flow, known_zones):
            outward.append({
                "path_nr": int(entry["path_nr"]),
                "from_zone": entry["from_zone"],
                "flow_m3h": flow,
            })
        elif flow < 0.0:
            inward_total += -flow
    return {
        "envelope_leak_count": leak_count,
        "outward_count": len(outward),
        "outward_total_m3h": sum(row["flow_m3h"] for row in outward),
        "outward_max_m3h": max((row["flow_m3h"] for row in outward), default=0.0),
        "inward_total_m3h": inward_total,
        "outward": outward,
    }


def _hull_lane_row(hull: str, lane: str, binary: str) -> dict[str, Any]:
    row: dict[str, Any] = {"hull": hull, "lane": lane}
    try:
        prj_text, entries = _lane_inputs(hull, lane)
        flows = _solve(prj_text, binary)
    except (ContamXUnavailable, OSError, ValueError, KeyError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row
    spatial = _load_json(os.path.join(_PLATFORMS_REL, hull, "spatial_layout.json"))
    known = {str(z["id"]) for z in spatial.get("zones", [])}
    row.update(summarize_envelope_leaks(entries, flows, known))
    return row


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hull", action="append")
    parser.add_argument("--lane", action="append", choices=LANES)
    parser.add_argument(
        "--out",
        default="telemetry_buffer/contam_envelope_leak_enumeration/results.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    binary = find_contamx()
    if binary is None:
        raise ContamXUnavailable("ContamX binary not found")
    hulls = [
        validate_path_component(h, label="platform id") for h in (args.hull or bundled_hulls())
    ]
    lanes = args.lane or list(LANES)
    rows = [_hull_lane_row(hull, lane, binary) for hull in hulls for lane in lanes]
    out_path = resolve_repo_path(REPO_ROOT, args.out)
    prepare_output_directory(os.path.dirname(out_path), allowed_roots=(REPO_ROOT,))
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        json.dump({"lanes": lanes, "rows": rows}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with_outward = [r for r in rows if r.get("outward_count")]
    print(f"wrote {len(rows)} rows ({len(with_outward)} with outward leaks) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
