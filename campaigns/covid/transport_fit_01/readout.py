#!/usr/bin/env python3
"""TRANSPORT-FIT-01 readout: native vs ContamX vs the outbreak record.

Reads the synced cell payloads (``scripts/campaign readout
covid/transport_fit_01 -- --cells-dir <dir>``), audits coverage against
the campaign spec and the resolved-engine echoes, and scores each
(scenario, arm) row against the record anchors from
``data/observation/covid_fit_targets.json``:

- DP: recorded_onsets vs 197 [197,199], before_share vs 0.173,
  lab_confirmed vs 712, lab-confirmed crew share vs 0.29, dated share
  (recorded/lab_confirmed) vs 0.277, asymptomatic-at-confirm share from
  funnel_hosts vs 0.5047 (day-31 window) and 311/712 (final), and the
  T2 onset-turn direction (passenger down, crew persists).
- GM: campaign positives vs 128/217 (H1 0.5899), asymptomatic share vs
  0.8125, takeoff share (>=10 recorded onsets).

Plus the seed-paired contamx-minus-native deltas — the quantity this
campaign actually exists to measure.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_CAMPAIGN_JSON = Path(__file__).with_name("campaign.json")
DP_DAY31 = 31

DP_RECORD = {
    "recorded_onsets": 197,
    "recorded_onsets_range": [197, 199],
    "before_share": 0.173,
    "lab_confirmed": 712,
    "crew_share": 0.29,
    "dated_share": 0.277,
    "asym_share_day31": 0.5047,   # 320/634
    "asym_share_final": 0.4368,   # 311/712
}
GM_RECORD = {
    "positives": 128,
    "tested": 217,
    "share": 0.5899,
    "asym_share": 0.8125,
    "takeoff_min_onsets": 10,
}

_RESOLVED_BY_ARM = {
    "native": "ContamTransportEngine",
    "contamx": "ContamXTransportEngine",
}


def _q(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    i = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[i]


def _row(values: list[float | None]) -> dict[str, float]:
    vals = [v for v in values if v is not None]
    return {
        "n": len(vals),
        "median": statistics.median(vals) if vals else float("nan"),
        "q05": _q(vals, 0.05),
        "q95": _q(vals, 0.95),
        "mean": statistics.fmean(vals) if vals else float("nan"),
    }


def _load_cells(cells_dir: Path) -> list[dict]:
    cells = []
    for path in sorted(cells_dir.rglob("cell_*.json")):
        try:
            cells.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            print(f"WARN unparsable {path}", file=sys.stderr)
    return cells


def _expected_cells() -> set[tuple[str, str, int]]:
    """The (design_id, arm_id, seed) set the campaign spec declares."""
    spec = json.loads(_CAMPAIGN_JSON.read_text())
    return {
        (_design_id_of(b["args"]["design"]), b["args"]["arm_id"], seed)
        for b in spec["blocks"].values() for seed in b["seeds"]
    }


def _design_id_of(design_path: str) -> str:
    return Path(design_path).stem.removesuffix("_design")


def _funnel_asym(payload: dict, day_cap: int | None) -> tuple[int, int]:
    """Confirmed hosts whose presented onset postdates the confirming
    specimen (the ASYM-CONF-01 / crew_reach definition), optionally
    restricted to confirmations on or before ``day_cap``."""
    hosts = (payload.get("funnel_hosts") or {}).values()
    confirmed = [
        h for h in hosts
        if h.get("confirmed_day") is not None
        and (day_cap is None or int(h["confirmed_day"]) <= day_cap)
    ]
    asym = [
        h for h in confirmed
        if h.get("presented_day") is None
        or int(h["presented_day"]) > int(h["confirmed_day"])
    ]
    return len(asym), len(confirmed)


def _channels(p: dict) -> dict[str, float | None]:
    obs = p.get("observables") or {}
    recorded = obs.get("recorded_onsets") or 0
    before = obs.get("onsets_before_split_day") or 0
    lab = p.get("lab_confirmed_total") or 0
    roles = p.get("lab_confirmed_by_role") or {}
    lab_crew = roles.get("crew") or 0
    asym, conf = _funnel_asym(p, None)
    asym31, conf31 = _funnel_asym(p, DP_DAY31)
    specimens = obs.get("campaign_positives") or 0
    return {
        "recorded_onsets": recorded,
        "before_share": before / recorded if recorded else None,
        "lab_confirmed": lab,
        "lab_crew_share": lab_crew / lab if lab else None,
        "dated_share": recorded / lab if lab else None,
        "asym_share_final": asym / conf if conf else None,
        "asym_share_day31": asym31 / conf31 if conf31 else None,
        "campaign_positives": specimens,
        "campaign_asym_share": (
            (obs.get("campaign_asymptomatic_positives") or 0) / specimens
            if specimens else None
        ),
        "pax_onset_before": obs.get("passenger_onsets_before") or 0,
        "pax_onset_after": obs.get("passenger_onsets_after") or 0,
        "crew_onset_before": obs.get("crew_onsets_before") or 0,
        "crew_onset_after": obs.get("crew_onsets_after") or 0,
        "infections_total": p.get("infections_total") or 0,
    }


def _onset_turn(ch: dict) -> str:
    """T2: after the quarantine turn, passenger onsets fall while crew
    onsets persist — the record's direction, not its magnitude."""
    pax = "down" if ch["pax_onset_after"] < ch["pax_onset_before"] else (
        "up" if ch["pax_onset_after"] > ch["pax_onset_before"] else "flat"
    )
    crew = "down" if ch["crew_onset_after"] < ch["crew_onset_before"] else (
        "up" if ch["crew_onset_after"] > ch["crew_onset_before"] else "flat"
    )
    return f"pax_{pax}/crew_{crew}"


def _score(rows: list[dict], keys: list[str]) -> dict:
    return {k: _row([c[k] for c in rows]) for k in keys}


def _audit(cells: list[dict]) -> dict:
    audit: dict[str, object] = {
        "cells": len(cells),
        "wrong_engine": [],
        "unexpected_cells": [],
        "duplicate_cells": [],
        "missing_cells": [],
    }
    seen: Counter[tuple] = Counter()
    for p in cells:
        cell = p.get("cell") or {}
        key = (p.get("design_id"), cell.get("arm_id"), cell.get("seed"))
        seen[key] += 1
        arm = cell.get("arm_id")
        resolved = (p.get("delivery") or {}).get("transport_engine_resolved")
        if _RESOLVED_BY_ARM.get(arm) not in (None, resolved):
            audit["wrong_engine"].append(key)
    expected = _expected_cells()
    found = set(seen)
    audit["missing_cells"] = sorted(
        map(str, expected - found), key=str,
    )
    audit["unexpected_cells"] = sorted(
        map(str, found - expected), key=str,
    )
    audit["duplicate_cells"] = sorted(
        map(str, (k for k, n in seen.items() if n > 1)), key=str,
    )
    return audit


def _paired_delta(
    native: list[dict], contamx: list[dict], key: str,
) -> dict:
    by_seed = {
        (r.get("cell") or {}).get("seed"): _channels(r).get(key)
        for r in native
    }
    deltas = []
    for r in contamx:
        seed = (r.get("cell") or {}).get("seed")
        if seed not in by_seed:
            continue
        a, b = _channels(r).get(key), by_seed[seed]
        if a is None or b is None:
            # An undefined share (zero confirmations) is not a zero — a
            # pair needs both sides measurable to score a delta.
            continue
        deltas.append(a - b)
    return _row(deltas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    cells = _load_cells(Path(args.cells_dir))
    rows: dict[tuple[str, str], list[dict]] = {}
    for p in cells:
        rows.setdefault(
            (p.get("design_id"), (p.get("cell") or {}).get("arm_id")),
            [],
        ).append(p)

    dp_keys = [
        "recorded_onsets", "before_share", "lab_confirmed",
        "lab_crew_share", "dated_share", "asym_share_day31",
        "asym_share_final", "campaign_asym_share", "infections_total",
    ]
    gm_keys = [
        "campaign_positives", "asym_share_final", "campaign_asym_share",
        "infections_total",
    ]
    report: dict = {
        "audit": _audit(cells),
        "record": {
            "diamond_princess": DP_RECORD, "greg_mortimer": GM_RECORD,
        },
        "scenarios": {},
    }
    for (design_id, arm), group in sorted(rows.items()):
        hull = "dp" if "dp" in design_id else "gm"
        keys = dp_keys if hull == "dp" else gm_keys
        channels = [_channels(p) for p in group]
        score = _score(channels, keys)
        score["takeoff_share"] = (
            sum(1 for c in channels if c["recorded_onsets"] >= 10)
            / len(channels) if channels else 0.0
        )
        if hull == "dp":
            score["onset_turn_directions"] = dict(
                Counter(_onset_turn(c) for c in channels),
            )
            dp_scale = [c for c in channels if c["lab_confirmed"] >= 100]
            score["lab_crew_share_dp_scale"] = _row(
                [c["lab_crew_share"] for c in dp_scale],
            )
            score["lab_crew_share_pooled"] = (
                sum((c["lab_confirmed"] or 0) * (c["lab_crew_share"] or 0)
                    for c in channels)
                / max(1, sum(c["lab_confirmed"] or 0 for c in channels))
            )
        report["scenarios"].setdefault(design_id, {})[arm] = score

    for design_id, arms in report["scenarios"].items():
        native_rows = rows.get((design_id, "native"), [])
        contamx_rows = rows.get((design_id, "contamx"), [])
        if not native_rows or not contamx_rows:
            continue
        keys = dp_keys if "dp" in design_id else gm_keys
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
