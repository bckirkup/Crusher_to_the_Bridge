#!/usr/bin/env python3
"""TRANSPORT-FIT-01 readout: native vs ContamX vs the outbreak record.

Reads the synced cell payloads (``scripts/campaign readout
covid/transport_fit_01 -- --cells-dir <dir>``), audits coverage and the
resolved-engine echoes, and scores each (scenario, arm) row against the
record anchors from ``data/observation/covid_fit_targets.json``:

- DP: recorded_onsets vs 197 [197,199], before_share vs 0.173,
  lab_confirmed vs 712, lab-confirmed crew share vs 0.29, dated share
  vs 0.277, asymptomatic share vs 0.5047, T2 onset-turn direction.
- GM: campaign positives vs 128/217 (0.5899), asymptomatic share vs
  0.8125, takeoff share (>=10 recorded onsets).

Plus the seed-paired contamx-minus-native deltas — the quantity this
campaign actually exists to measure.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DP_RECORD = {
    "recorded_onsets": 197,
    "recorded_onsets_range": [197, 199],
    "before_share": 0.173,
    "lab_confirmed": 712,
    "crew_share": 0.29,
    "dated_share": 0.277,
    "asym_share": 0.5047,
}
GM_RECORD = {
    "positives": 128,
    "tested": 217,
    "share": 0.5899,
    "asym_share": 0.8125,
    "takeoff_min_onsets": 10,
}


def _q(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    i = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[i]


def _row(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "median": statistics.median(values) if values else float("nan"),
        "q05": _q(values, 0.05),
        "q95": _q(values, 0.95),
        "mean": statistics.fmean(values) if values else float("nan"),
    }


def _load_cells(cells_dir: Path) -> list[dict]:
    cells = []
    for path in sorted(cells_dir.rglob("cell_*.json")):
        try:
            cells.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            print(f"WARN unparsable {path}", file=sys.stderr)
    return cells


def _channels(p: dict) -> dict[str, float]:
    obs = p.get("observables") or {}
    recorded = obs.get("recorded_onsets", 0)
    before = obs.get("onsets_before_split_day", 0)
    lab = p.get("lab_confirmed_total", 0)
    by_role = p.get("lab_confirmed_by_role") or {}
    crew = by_role.get("crew", 0)
    dated = sum(
        (v.get("crew", 0) + v.get("passenger", 0))
        for v in (p.get("onset_curve") or {}).values()
    ) or recorded
    inf = p.get("infections_total", 0)
    return {
        "recorded_onsets": recorded,
        "before_share": before / recorded if recorded else 0.0,
        "lab_confirmed": lab,
        "crew_share": crew / lab if lab else 0.0,
        "dated_share": dated / lab if lab else 0.0,
        "asym_share": (obs.get("campaign_asymptomatic_positives", 0)
                       / obs["campaign_positives"])
        if obs.get("campaign_positives") else 0.0,
        "campaign_positives": obs.get("campaign_positives", 0),
        "positive_share": obs.get("positive_share"),
        "infections_total": inf,
    }


def _score_dp(rows: list[dict]) -> dict:
    ch = [_channels(r) for r in rows]
    takeoffs = [c for c in ch if c["recorded_onsets"] >= 10]
    dp_scale = [c for c in ch if c["lab_confirmed"] >= 100]
    return {
        "recorded_onsets": _row([c["recorded_onsets"] for c in ch]),
        "before_share": _row([c["before_share"] for c in ch]),
        "lab_confirmed": _row([c["lab_confirmed"] for c in ch]),
        "crew_share_pooled": (
            sum(c["lab_confirmed"] * c["crew_share"] for c in ch)
            / max(1, sum(c["lab_confirmed"] for c in ch))
        ),
        "crew_share_dp_scale": _row(
            [c["crew_share"] for c in dp_scale],
        ),
        "dated_share": _row([c["dated_share"] for c in ch]),
        "asym_share": _row([c["asym_share"] for c in ch]),
        "takeoff_share": len(takeoffs) / len(ch) if ch else 0.0,
        "infections_total": _row([c["infections_total"] for c in ch]),
    }


def _score_gm(rows: list[dict]) -> dict:
    ch = [_channels(r) for r in rows]
    return {
        "campaign_positives": _row([c["campaign_positives"] for c in ch]),
        "asym_share": _row([c["asym_share"] for c in ch]),
        "takeoff_share": (
            sum(1 for c in ch
                if c["recorded_onsets"] >= GM_RECORD["takeoff_min_onsets"])
            / len(ch) if ch else 0.0
        ),
        "infections_total": _row([c["infections_total"] for c in ch]),
    }


def _paired_delta(
    native: list[dict], contamx: list[dict], key: str,
) -> dict:
    by_seed = {
        (r.get("cell") or {}).get("seed"): _channels(r)[key]
        for r in native
    }
    deltas = [
        _channels(r)[key] - by_seed[(r.get("cell") or {}).get("seed")]
        for r in contamx
        if (r.get("cell") or {}).get("seed") in by_seed
    ]
    return _row(deltas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    cells = _load_cells(Path(args.cells_dir))
    audit = {
        "cells": len(cells),
        "missing_resolved_echo": 0,
        "blocked_engine_fallback": 0,
        "wrong_engine": [],
    }
    rows: dict[tuple[str, str], list[dict]] = {}
    for p in cells:
        delivery = p.get("delivery") or {}
        arm = (p.get("cell") or {}).get("arm_id")
        resolved = delivery.get("transport_engine_resolved")
        declared = delivery.get("transport_engine", "native")
        if resolved is None:
            audit["missing_resolved_echo"] += 1
        elif arm == "contamx" and resolved != "ContamXTransportEngine":
            audit["blocked_engine_fallback"] += 1
            audit["wrong_engine"].append((p.get("cell") or {}).get("seed"))
        elif arm == "native" and resolved != "ContamTransportEngine":
            audit["blocked_engine_fallback"] += 1
            audit["wrong_engine"].append((p.get("cell") or {}).get("seed"))
        if arm != declared:
            audit["wrong_engine"].append(
                f"declared {declared} vs arm {arm}",
            )
        rows.setdefault((p.get("design_id"), arm), []).append(p)

    report: dict = {"audit": audit, "record": {
        "diamond_princess": DP_RECORD, "greg_mortimer": GM_RECORD,
    }, "scenarios": {}}
    for (design_id, arm), group in sorted(rows.items()):
        hull = "dp" if "dp" in design_id else "gm"
        score = _score_dp(group) if hull == "dp" else _score_gm(group)
        report["scenarios"].setdefault(design_id, {})[arm] = score

    for design_id, arms in report["scenarios"].items():
        native_rows = rows.get((design_id, "native"), [])
        contamx_rows = rows.get((design_id, "contamx"), [])
        if not native_rows or not contamx_rows:
            continue
        hull = "dp" if "dp" in design_id else "gm"
        keys = (
            ["recorded_onsets", "before_share", "lab_confirmed",
             "crew_share", "dated_share", "asym_share", "infections_total"]
            if hull == "dp"
            else ["campaign_positives", "asym_share", "infections_total"]
        )
        arms["paired_delta_contamx_minus_native"] = {
            k: _paired_delta(native_rows, contamx_rows, k) for k in keys
        }

    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"WROTE {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
