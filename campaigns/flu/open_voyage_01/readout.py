#!/usr/bin/env python3
"""FLU-OPEN-01 readout: aggregate ``cell_<seed>.json`` payloads.

Reads ``--root`` laid out as ``<block>/cell_<seed>.json`` (the layout the
generic entrypoint uploads and ``aws s3 sync`` mirrors back), aggregates
each class block and the pooled fleet, and emits JSON + Markdown. The
verdict frames applied here were frozen in ``DESIGN.md`` before any cell
ran; this file only measures, it never selects.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import resolve_repo_path  # noqa: E402
from tools.diag.readout_common import (  # noqa: E402
    quantiles,
    wilson_interval,
)

_F5_ANCHOR = 0.08
_F5_FRAME = (0.03, 0.15)
_FLAT_FRACTION = 0.669
_MIN_BAND_N = 5


def _wilson(k: int, n: int) -> dict[str, float]:
    lo, hi = wilson_interval(k, n)
    return {"lo": lo, "hi": hi}


def _load_profile(pathogen_id: str, bundle: str) -> dict[str, Any]:
    path = resolve_repo_path(
        _REPO_ROOT,
        f"data/pathogens/{bundle}.json",
    )
    profiles = json.loads(Path(path).read_text())["pathogens"]
    return next(p for p in profiles if p["pathogen_id"] == pathogen_id)


def _iter_cells(root: Path) -> dict[str, list[dict[str, Any]]]:
    blocks: dict[str, list[dict[str, Any]]] = {}
    for block_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for cell_file in sorted(block_dir.glob("cell_*.json")):
            cell = json.loads(cell_file.read_text())
            cell["_block"] = block_dir.name
            blocks.setdefault(block_dir.name, []).append(cell)
    return blocks


def _sum_rows(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-cell infection rows into class-level counters."""
    out = {
        "cells": len(cells),
        "infected": 0,
        "ill": 0,
        "reported": 0,
        "index": 0,
        "onboard": 0,
        "outbreak_cells": 0,
        "index_invariant_fails": 0,
        "confined_cells": 0,
        "quarantined": 0,
        "isolated": 0,
        "cell_infected": [],
        "trigger": {},
        "routes": {},
        "bands": {},
        "caregiver_any": 0,
        "caregiver_dom": 0,
        "caregiver_pax": 0,
        "caregiver_crew": 0,
    }
    for cell in cells:
        c = cell["counts"]
        out["cell_infected"].append(c["ever_infected"])
        out["outbreak_cells"] += int(c["onboard_acquired"] > 0)
        out["index_invariant_fails"] += int(c["index_cases"] < 2)
        confined = c["quarantined_end"] + c["isolated_end"]
        out["confined_cells"] += int(confined > 0)
        out["quarantined"] += c["quarantined_end"]
        out["isolated"] += c["isolated_end"]
        trig = str(cell.get("final_trigger_status"))
        out["trigger"][trig] = out["trigger"].get(trig, 0) + 1
        _sum_infections(cell["infections"], out)
    return out


def _sum_infections(rows: list[dict[str, Any]], out: dict[str, Any]) -> None:
    for r in rows:
        out["infected"] += 1
        out["ill"] += int(r["ill"])
        out["reported"] += int(r["reported"])
        out["index"] += int(r["index"])
        out["onboard"] += int(not r["index"])
        dom = r.get("dominant_route") or ("index_or_boarding" if r["index"] else "unknown")
        out["routes"][dom] = out["routes"].get(dom, 0) + 1
        band = r["band"]
        b = out["bands"].setdefault(
            band,
            {"infected": 0, "ill": 0, "presented": 0, "reported": 0, "severity": {}},
        )
        b["infected"] += 1
        b["ill"] += int(r["ill"])
        b["presented"] += int(r["presented"])
        b["reported"] += int(r["reported"])
        sev = r.get("severity_peak") or "none"
        b["severity"][sev] = b["severity"].get(sev, 0) + 1
        if "caregiver" in (r.get("routes") or {}):
            out["caregiver_any"] += 1
            key = "caregiver_pax" if r["role"] == "passenger" else "caregiver_crew"
            out[key] += 1
        if dom == "caregiver":
            out["caregiver_dom"] += 1


def _implied_fraction(
    bands: dict[str, dict[str, int]],
    declared: dict[str, float],
) -> float:
    """E[presentation] over the pooled measured band mix."""
    infected = sum(b["infected"] for b in bands.values())
    if not infected:
        return 0.0
    num = sum(b["infected"] * declared.get(band, _FLAT_FRACTION) for band, b in bands.items())
    return num / infected


def _funnel(tot: dict[str, Any]) -> dict[str, Any]:
    """ever_ill and reported rates with Wilson-95 + the frozen frames."""
    n = tot["infected"]
    res: dict[str, Any] = {"infected": n}
    if n:
        res["ever_ill"] = {
            "k": tot["ill"],
            "n": n,
            "p": tot["ill"] / n,
            "wilson": _wilson(tot["ill"], n),
        }
        res["reported"] = {
            "k": tot["reported"],
            "n": n,
            "p": tot["reported"] / n,
            "wilson": _wilson(tot["reported"], n),
            "f5_frame": list(_F5_FRAME),
            "f5_read": ("consistent" if _F5_FRAME[0] <= tot["reported"] / n <= _F5_FRAME[1] else "anchor_tension"),
        }
    res["outbreak_rate"] = tot["outbreak_cells"] / max(1, tot["cells"])
    res["index_invariant_fails"] = tot["index_invariant_fails"]
    res["infected_dist"] = quantiles(tot["cell_infected"])
    res["confinement"] = {
        "cells_with_confinement": tot["confined_cells"],
        "quarantined_end": tot["quarantined"],
        "isolated_end": tot["isolated"],
    }
    res["trigger_status"] = tot["trigger"]
    res["dominant_routes"] = tot["routes"]
    res["caregiver"] = {
        "any": tot["caregiver_any"],
        "dominant": tot["caregiver_dom"],
        "passenger": tot["caregiver_pax"],
        "crew": tot["caregiver_crew"],
    }
    return res


def _band_table(
    tot: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    declared_frac = profile.get("symptomatic_fraction_by_age_band") or {}
    sev_model = profile.get("severity_model") or {}
    sev_by_band = sev_model.get("base_probabilities_by_age_band") or {}
    states = sev_model.get("states") or []
    table: dict[str, Any] = {
        "implied_fraction": _implied_fraction(tot["bands"], declared_frac),
        "bands": {},
    }
    for band, b in sorted(tot["bands"].items()):
        row: dict[str, Any] = {
            "infected": b["infected"],
            "declared_frac": declared_frac.get(band, _FLAT_FRACTION),
        }
        if b["infected"] >= _MIN_BAND_N:
            row["measured_frac"] = b["presented"] / b["infected"]
            row["wilson"] = _wilson(b["presented"], b["infected"])
            lo, hi = row["wilson"]["lo"], row["wilson"]["hi"]
            f = row["declared_frac"]
            row["fraction_read"] = "consistent" if lo <= f <= hi else "flag"
            vec = sev_by_band.get(band)
            if vec:
                row["severity"] = {
                    s: {
                        "measured": b["severity"].get(s, 0) / b["infected"],
                        "declared": vec[i] if i < len(vec) else None,
                    }
                    for i, s in enumerate(states)
                }
        table["bands"][band] = row
    return table


def build_readout(root: Path) -> dict[str, Any]:
    blocks = _iter_cells(root)
    profile = None
    pooled_cells: list[dict[str, Any]] = []
    per_class: dict[str, Any] = {}
    for block, cells in blocks.items():
        if profile is None and cells:
            profile = _load_profile(
                cells[0]["pathogen_id"],
                cells[0]["bundle"],
            )
        pooled_cells.extend(cells)
        tot = _sum_rows(cells)
        per_class[block] = {
            "funnel": _funnel(tot),
            "bands": _band_table(tot, profile),
        }
    tot_all = _sum_rows(pooled_cells)
    return {
        "schema": "flu_open_voyage_01.readout.v1",
        "root": str(root),
        "cells": len(pooled_cells),
        "per_class": per_class,
        "pooled": {
            "funnel": _funnel(tot_all),
            "bands": _band_table(tot_all, profile),
        },
    }


def _pct(p: float | None) -> str:
    return f"{p * 100:.1f}%" if p is not None else "n/a"


def render_markdown(readout: dict[str, Any]) -> str:
    lines = ["# FLU-OPEN-01 open-voyage census readout", ""]
    lines.append(
        f"cells={readout['cells']}  classes={len(readout['per_class'])}",
    )
    lines.append("")
    lines.append(
        "| class | cells | infected (med/max) | outbreak | ill/inf | rep/inf | F5 read | confined cells |",
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for name in list(readout["per_class"]) + ["__pooled__"]:
        src = readout["per_class"].get(name) or {"funnel": readout["pooled"]["funnel"]}
        f = src["funnel"]
        ill = f.get("ever_ill", {})
        rep = f.get("reported", {})
        dist = f.get("infected_dist", {})
        label = "pooled" if name == "__pooled__" else name
        lines.append(
            f"| {label} | {f.get('cells', readout['cells'])} "
            f"| {f['infected']} ({dist.get('median', '?')}/"
            f"{dist.get('max', '?')}) | {_pct(f['outbreak_rate'])} "
            f"| {_pct(ill.get('p'))} [{_pct((ill.get('wilson') or {}).get('lo'))}"
            f"-{_pct((ill.get('wilson') or {}).get('hi'))}] "
            f"| {_pct(rep.get('p'))} | {rep.get('f5_read', 'n/a')} "
            f"| {f['confinement']['cells_with_confinement']} |",
        )
    lines.append("")
    for name, blk in readout["per_class"].items():
        lines.append(f"## {name} — bands")
        lines.append("| band | inf | declared f | measured f | read |")
        lines.append("|---|---|---|---|---|")
        for band, row in blk["bands"]["bands"].items():
            lines.append(
                f"| {band} | {row['infected']} "
                f"| {row['declared_frac']:.3f} "
                f"| {_pct(row.get('measured_frac'))} "
                f"| {row.get('fraction_read', 'low-n')} |",
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="dir laid out as <block>/cell_<seed>.json")
    parser.add_argument("--out", default=None, help="write JSON readout here (markdown -> stdout)")
    args = parser.parse_args(argv)
    readout = build_readout(Path(args.root))
    if args.out:
        Path(args.out).write_text(
            json.dumps(readout, indent=1) + "\n",
            encoding="utf-8",
        )
    print(render_markdown(readout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
