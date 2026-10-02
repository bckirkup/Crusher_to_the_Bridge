#!/usr/bin/env python3
"""NORO-OUTBREAK-01 anchor readout for small-hull outbreak cells.

Reads the campaign-layout ``summary.json`` / ``growth_census.json.gz``
inside each run zip written by ``growth_chain_census.py`` (layout
``<root>/<tier>/<run_id>.zip``), groups the runs into the design's cells
(hull x voyage length x arm coordinate), and renders the three views the
design freezes:

- **frequency**: per-cell fractions with Wilson 95% intervals for
  imported (``n_imports > 0``), emesis-ignited, established
  (``n_acquired > 0``), takeoff (``peak_prevalence >= 10``), VSP-flagged
  (``vsp_trigger_epoch`` set), and posted (the A9 rule: reported case
  rate >= 3% on either channel, over A9-eligible runs only);
- **ultimate attack rate**: the anchor table per
  ``telemetry_buffer.observation_model.score_anchors``
  (``row_from_summary`` -> ``summarise_cell`` -> ``verdicts``, era
  ``pre``) -- A1/A2/A5 bands, A4 vs the hull-class VSP IQR, A8/A9
  channels, plus the A3 construction band as a diagnostic;
- **progression**: among takeoff voyages, distribution of onset epoch
  (first ``new_infections > 0``), last-infecting epoch, outbreak span,
  ``detection_epoch``/``peak_epoch``/``vsp_trigger_epoch``, and
  ``peak_prevalence``; among posted voyages, the reported passenger
  attack-rate distribution against the class IQR.

With ``--import-root`` pointing at a synced NORO-IMPORT-01 results tree
(``campaign/noro_import_01/`` layout), the readout additionally pairs each
shared (cell, seed) against the pre-hand/presentation-merge voyages:
discordant establishment/takeoff/posted counts and the signed shift in
acquired counts, infection AR and reported AR.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools" / "noro_diag") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

from simulation_utils.paths import validated_open  # noqa: E402
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
    row_from_summary,
    summarise_cell,
    verdicts,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (  # noqa: E402
    vsp_attack_rate_targets,
)
from tools.diag.readout_common import (  # noqa: E402
    iter_tier_zips,
    load_zip_json,
    rate_summary,
    seed_from_params,
)

_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

_HULL_LABEL = {
    "expedition_cruise_450": "exp",
    "classic_cruise_1900": "cls",
    "spirit_cruise_3000": "spr",
    "mega_cruise_5000": "mega",
}
_RUNG_LABEL = {
    "shipped": "scr",
    "renewal_stationary": "ren-off",
    "symptomatic": "ren+stream",
    "reportable": "ren",
}


def _load_member(zip_path: Path, member: str, *, gunzipped: bool = False) -> dict | None:
    return load_zip_json(zip_path, member, gunzipped=gunzipped)


def _seed_of(params: dict) -> int:
    return seed_from_params(params)


def _cell_key(params: dict) -> tuple:
    """The design's cell coordinate: hull x length x arm x prevalence x nsf."""
    return (
        str(params.get("platform_id") or params.get("platform") or ""),
        int(params.get("num_epochs", 0)),
        _RUNG_LABEL.get(
            str(params.get("boarding_mechanism_rung") or ""),
            str(params.get("boarding_mechanism_rung") or "?"),
        ),
        round(float(params.get("boarding_passenger_prevalence") or 0.0), 4),
        round(float(params.get("boarding_crew_prevalence") or 0.0), 4),
        round(float(params.get("never_symptomatic_fraction") or -1.0), 2),
    )


def _cell_label(key: tuple) -> str:
    hull, epochs, rung, pax_prev, crew_prev, nsf = key
    days = epochs / 24.0  # clock-exempt: label only; manifest pins clock='hours'
    day_tag = f"{days:g}d"
    prev_tag = f"bp{pax_prev * 1000:g}c{crew_prev * 1000:g}"
    if rung == "scr":
        arm = f"scr {prev_tag}"
    else:
        arm = f"{rung} {prev_tag}"
    return (
        f"{_HULL_LABEL.get(hull, hull)} {day_tag} {arm} nsf{round(nsf * 100)}"
    )


def _posted(row: dict[str, Any]) -> bool:
    return (
        row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
    )


def _progression(summary: dict[str, Any]) -> dict[str, Any]:
    """Within-voyage outbreak trajectory descriptors from one summary."""
    derived = summary.get("derived", {})
    ts = summary.get("timeseries") or []
    new_infect = [int(e.get("new_infections", 0) or 0) for e in ts]
    active = [i for i, n in enumerate(new_infect) if n > 0]
    out = {
        "onset_epoch": active[0] if active else None,
        "last_infecting_epoch": active[-1] if active else None,
        "peak_epoch": derived.get("peak_epoch"),
        "detection_epoch": derived.get("detection_epoch"),
        "vsp_trigger_epoch": derived.get("vsp_trigger_epoch"),
        "peak_prevalence": int(derived.get("peak_prevalence", 0) or 0),
    }
    if out["onset_epoch"] is not None and out["last_infecting_epoch"] is not None:
        out["active_span"] = out["last_infecting_epoch"] - out["onset_epoch"]
    else:
        out["active_span"] = None
    return out


def collect_run(zip_path: Path) -> dict[str, Any] | None:
    """One voyage's scoring row + census counters + trajectory descriptors."""
    summary = _load_member(zip_path, _MEMBER)
    if summary is None:
        return None
    params = summary.get("parameters", {})
    census_block = summary.get("census", {})
    run = {
        "run_id": summary.get("run_id", zip_path.stem),
        "cell_key": _cell_key(params),
        "seed": _seed_of(params),
        "anchor_row": row_from_summary(summary, str(zip_path)),
        "n_imports": int(census_block.get("n_imports", 0) or 0),
        "n_acquired": int(census_block.get("n_acquired", 0) or 0),
        "ignited": bool(census_block.get("ignited", False)),
    }
    run.update(_progression(summary))
    return run


def collect(root: Path, tiers: list[str] | None = None) -> dict[tuple, list[dict]]:
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for _tier, zip_path in iter_tier_zips(root, tiers):
        run = collect_run(zip_path)
        if run is not None:
            cells[run["cell_key"]].append(run)
    return dict(cells)


def _quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    n = len(ordered)
    q = statistics.quantiles(ordered, n=4) if n >= 4 else None
    return {
        "n": n,
        "min": ordered[0],
        "q1": q[0] if q else ordered[0],
        "median": statistics.median(ordered),
        "q3": q[2] if q else ordered[-1],
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


def _rate(x: int, n: int) -> dict[str, float]:
    return rate_summary(x, n)


def _frequency(runs: list[dict]) -> dict[str, Any]:
    n = len(runs)
    rows = [r["anchor_row"] for r in runs]
    eligible = [
        r for r in rows
        if r["passenger_complement"] >= 100 and 3.0 <= r["voyage_days"] <= 21.0
    ]
    return {
        "n": n,
        "imported": _rate(sum(r["n_imports"] > 0 for r in runs), n),
        "ignited": _rate(sum(r["ignited"] for r in runs), n),
        "established": _rate(sum(r["n_acquired"] > 0 for r in runs), n),
        "takeoff": _rate(sum(r["anchor_row"]["took_off"] for r in runs), n),
        "vsp_flagged": _rate(
            sum(r["vsp_trigger_epoch"] is not None for r in rows),
            n,
        ),
        "posted": _rate(sum(_posted(r) for r in eligible), len(eligible)),
        "median_acquired": (
            statistics.median(r["n_acquired"] for r in runs) if runs else None
        ),
        "median_imports": (
            statistics.median(r["n_imports"] for r in runs) if runs else None
        ),
    }


def _progression_block(runs: list[dict]) -> dict[str, Any]:
    """Distribution of trajectory descriptors over the takeoff voyages."""
    off = [r for r in runs if r["anchor_row"]["took_off"]]
    fields = (
        "onset_epoch",
        "peak_epoch",
        "detection_epoch",
        "vsp_trigger_epoch",
        "active_span",
        "peak_prevalence",
    )
    out = {"n_takeoff": len(off)}
    for field in fields:
        vals = [float(r[field]) for r in off if r.get(field) is not None]
        out[field] = _quantiles(vals)
    posted = [r for r in off if _posted(r["anchor_row"])]
    out["n_posted_of_takeoff"] = len(posted)
    out["posted_pax_ar"] = _quantiles(
        [
            r["anchor_row"]["reported_case_attack_rate_passenger"]
            for r in posted
        ],
    )
    return out


def _scored_cell(runs: list[dict], era: str) -> dict[str, Any]:
    rows = [r["anchor_row"] for r in runs]
    hull = rows[0]["hull"]
    cell = summarise_cell(rows)
    anchors, ratios = verdicts(
        hull,
        cell,
        vsp_attack_rate_targets(era),
        era,
    )
    targets = vsp_attack_rate_targets(era).get(hull)
    return {
        "hull": hull,
        "anchors": anchors,
        "ratios": ratios,
        "A4_target": targets,
        "A1": cell.get("A1_ever_ill_passenger"),
        "A1_per_seed_median": cell.get("A1_ever_ill_passenger__per_seed_median"),
        "A2_per_seed_median": cell.get("A2_ill_per_infected__per_seed_median"),
        "A3_per_seed_median": cell.get("A3_reported_per_symptomatic__per_seed_median"),
        "A5_per_seed_median": cell.get("A5_passenger_crew_ratio__per_seed_median"),
        "A8_pax": cell.get("A8_pax_incidence"),
        "A8_crew": cell.get("A8_crew_incidence"),
        "A9": cell.get("A9_posting_probability"),
        "A9_pax_channel": cell.get("A9_posting_probability_passenger_channel"),
        "A9_posted": cell.get("A9_posted_eligible"),
        "A9_eligible": cell.get("A9_eligible_runs"),
        "takeoff_fraction": cell.get("takeoff_fraction"),
        "infection_ar_pax_median": cell.get(
            "infection_attack_rate_passenger__per_seed_median",
        ),
        "reported_ar_pax_median": cell.get(
            "reported_case_attack_rate_passenger__per_seed_median",
        ),
    }


def build_report(
    root: Path,
    tiers: list[str] | None = None,
    era: str = "pre",
    import_root: Path | None = None,
) -> dict[str, Any]:
    cells = collect(root, tiers)
    report: dict[str, Any] = {"cells": {}}
    for key, runs in sorted(cells.items(), key=lambda kv: _cell_label(kv[0])):
        label = _cell_label(key)
        report["cells"][label] = {
            "frequency": _frequency(runs),
            "progression": _progression_block(runs),
            "scored": _scored_cell(runs, era),
        }
    if import_root is not None:
        report["paired"] = _paired_delta(cells, import_root)
    return report


def _paired_delta(cells: dict[tuple, list[dict]], import_root: Path) -> dict[str, Any]:
    """Seed-paired contrasts vs the pre-hand/presentation-merge zips.

    IMPORT-01 ran the same arm coordinates on the same seeds at three
    nsf levels; the pairing restricts its rows to the nsf coordinate this
    campaign declares, then joins on (cell, seed).
    """
    old_cells = collect(import_root)
    out: dict[str, Any] = {}
    for key, runs in cells.items():
        pairs = _paired_runs(key, runs, old_cells)
        if not pairs:
            continue
        out[_cell_label(key)] = _paired_entry(pairs)
    return out


def _paired_runs(
    key: tuple,
    runs: list[dict],
    old_cells: dict,
) -> list[tuple[dict, dict]]:
    # Pair on hull x length x rung x prevalence, ignoring nsf level
    # only when it already matches; the old cells carry the same
    # coordinate family at several nsf values.
    old_pool: dict[int, dict] = {}
    for old_key, old_runs in old_cells.items():
        if old_key[:5] == key[:5] and old_key[5] == key[5]:
            for r in old_runs:
                old_pool[r["seed"]] = r
    return [(r, old_pool[r["seed"]]) for r in runs if r["seed"] in old_pool]


def _paired_entry(pairs: list[tuple[dict, dict]]) -> dict[str, Any]:
    entry: dict[str, Any] = {"n_pairs": len(pairs)}
    for name, extract in (
        ("established", lambda r: r["n_acquired"] > 0),
        ("takeoff", lambda r: r["anchor_row"]["took_off"]),
        ("posted", lambda r: _posted(r["anchor_row"])),
    ):
        discordant = sum(
            extract(new) != extract(old) for new, old in pairs
        )
        gained = sum(extract(new) and not extract(old) for new, old in pairs)
        lost = sum(not extract(new) and extract(old) for new, old in pairs)
        entry[name] = {"discordant": discordant, "gained": gained, "lost": lost}
    for name, extract in (
        ("n_acquired", lambda r: float(r["n_acquired"])),
        ("peak_prevalence", lambda r: float(r["peak_prevalence"])),
        (
            "reported_ar_pax",
            lambda r: r["anchor_row"]["reported_case_attack_rate_passenger"],
        ),
    ):
        diffs = [extract(new) - extract(old) for new, old in pairs]
        entry[f"delta_{name}"] = _quantiles(diffs)
    return entry


def _pct(x: dict[str, float]) -> str:
    return f"{100 * x['rate']:6.2f}  [{100 * x['lo']:5.2f},{100 * x['hi']:5.2f}]"


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or not isinstance(value, (int, float)):
        return "  --"
    return f"{value:.{digits}f}"


def _quant_cell(q: dict[str, Any], digits: int = 1) -> str:
    if not q or q.get("n", 0) == 0:
        return "--"
    return (
        f"{q['median']:.{digits}f} [{q['q1']:.{digits}f}-{q['q3']:.{digits}f}]"
    )


def _frequency_lines(report: dict) -> list[str]:
    lines = [
        "| cell | n | ignited | imported | established | takeoff | vsp flag | posted | med acquired |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, block in report["cells"].items():
        f = block["frequency"]
        lines.append(
            f"| {label} | {f['n']} | {_pct(f['ignited'])} | {_pct(f['imported'])}"
            f" | {_pct(f['established'])} | {_pct(f['takeoff'])}"
            f" | {_pct(f['vsp_flagged'])} | {_pct(f['posted'])}"
            f" | {_fmt(f['median_acquired'], 0)} |"
        )
    return lines


def _anchor_lines(report: dict) -> list[str]:
    lines = [
        "| cell | A1 ever-ill | A2 ill/inf | A3 rep/ill | A4 rep AR vs IQR | A5 pax/crew | A8 pax | A8 crew | A9 post | verdicts |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for label, block in report["cells"].items():
        s = block["scored"]
        t = s.get("A4_target") or {}
        a4 = (
            f"{_fmt(s.get('reported_ar_pax_median'))} vs "
            f"[{_fmt(t.get('q1'))}-{_fmt(t.get('q3'))}]"
            if t
            else "no target"
        )
        v = s["anchors"]
        verdict = ", ".join(
            f"{k.split('_')[0]}={vv}" for k, vv in sorted(v.items())
        )
        a9 = s.get("A9")
        a9_str = f"{100 * a9:.2f}%" if isinstance(a9, (int, float)) else "--"
        lines.append(
            f"| {label} | {_fmt(s.get('A1'))} | {_fmt(s.get('A2_per_seed_median'))}"
            f" | {_fmt(s.get('A3_per_seed_median'))} | {a4}"
            f" | {_fmt(s.get('A5_per_seed_median'))}"
            f" | {_fmt(s.get('A8_pax'))} | {_fmt(s.get('A8_crew'))}"
            f" | {a9_str} ({s.get('A9_posted')}/{s.get('A9_eligible')})"
            f" | {verdict} |"
        )
    return lines


def _progression_lines(report: dict) -> list[str]:
    lines = [
        "| cell | n takeoff | onset ep med [IQR] | peak ep | detect ep | vsp flag ep | span ep | peak prev | n posted | posted pax AR med [IQR] |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for label, block in report["cells"].items():
        p = block["progression"]
        lines.append(
            f"| {label} | {p['n_takeoff']}"
            f" | {_quant_cell(p['onset_epoch'], 0)}"
            f" | {_quant_cell(p['peak_epoch'], 0)}"
            f" | {_quant_cell(p['detection_epoch'], 0)}"
            f" | {_quant_cell(p['vsp_trigger_epoch'], 0)}"
            f" | {_quant_cell(p['active_span'], 0)}"
            f" | {_quant_cell(p['peak_prevalence'], 0)}"
            f" | {p['n_posted_of_takeoff']}"
            f" | {_quant_cell(p['posted_pax_ar'], 3)} |"
        )
    return lines


def _paired_lines(report: dict) -> list[str]:
    paired = report.get("paired") or {}
    if not paired:
        return []
    lines = [
        "| cell | n pairs | estab gained/lost | takeoff gained/lost | posted gained/lost | Δ acquired med | Δ peak med | Δ rep AR med |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, e in paired.items():
        lines.append(
            f"| {label} | {e['n_pairs']}"
            f" | {e['established']['gained']}/{e['established']['lost']}"
            f" | {e['takeoff']['gained']}/{e['takeoff']['lost']}"
            f" | {e['posted']['gained']}/{e['posted']['lost']}"
            f" | {_fmt(e['delta_n_acquired'].get('median'), 1)}"
            f" | {_fmt(e['delta_peak_prevalence'].get('median'), 1)}"
            f" | {_fmt(e['delta_reported_ar_pax'].get('median'), 4)} |"
        )
    return lines


def render_markdown(report: dict) -> str:
    """Canonical NORO-OUTBREAK-01 markdown."""
    out = ["# NORO-OUTBREAK-01 readout", ""]
    out += ["## Frequency (rates % with Wilson 95% intervals)", ""]
    out += _frequency_lines(report)
    out += ["", "## Anchors (era=pre, takeoff-conditional unless noted)", ""]
    out += _anchor_lines(report)
    out += ["", "## Progression (takeoff voyages only)", ""]
    out += _progression_lines(report)
    if report.get("paired"):
        out += ["", "## Paired delta vs NORO-IMPORT-01 (same seeds)", ""]
        out += _paired_lines(report)
    out += [""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--import-root", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--tiers", nargs="*", default=None)
    parser.add_argument("--era", default="pre")
    args = parser.parse_args()
    report = build_report(
        args.runs_dir,
        args.tiers,
        era=args.era,
        import_root=args.import_root,
    )
    if args.md_out:
        allowed = (str(args.md_out.parent.resolve()),)
        with validated_open(
            str(args.md_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            fh.write(render_markdown(report))
    if args.json_out:
        allowed = (str(args.json_out.parent.resolve()),)
        with validated_open(
            str(args.json_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=1, default=str)
    if not args.md_out and not args.json_out:
        print(render_markdown(report))


if __name__ == "__main__":
    main()
