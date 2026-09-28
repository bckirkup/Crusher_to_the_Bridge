#!/usr/bin/env python3
"""NORO-IMPORT-01 import-region readout.

Reads the campaign-layout ``summary.json`` inside each run zip written by
``growth_chain_census.py`` (layout ``<root>/<tier>/<run_id>.zip``), groups
the runs into the design's cells, and renders the sourced-region map:

- per-cell ignition / takeoff / posting rates with Wilson CIs;
- peak-prevalence distribution and growth depth (peak concurrent
  infected hosts, ignited voyages only);
- the emesis placement partition (emit zone_type shares);
- paired discordance counts between cells that share seeds;
- the symptomatic-stream consumption witness that gates the renewal
  rows (resolved spec fields + drawn ``composition.symptomatic``
  counts checked against the binomial expectation).

Cells on the ``fl_exp_12d_flag`` (community-cohort bound),
``fl_exp_12d_dose`` (Axis D endpoints) and ``fl_exp_12d_alpha`` (flagged
what-if) tiers render in their own tables, never mixed into the licensed
map.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "tools" / "noro_diag") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

from rhythm_ab_readout import TAKEOFF_PEAK_PREVALENCE, _wilson  # noqa: E402

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    validated_open,
)

_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

_DOSE_TIER = "fl_exp_12d_dose"
_ALPHA_TIER = "fl_exp_12d_alpha"
_FLAG_TIER = "fl_exp_12d_flag"

_RUNG_LABEL = {
    "shipped": "screening",
    "renewal_stationary": "renewal (stream off)",
    "symptomatic": "renewal+stream",
    "reportable": "renewal+stream+pbc",
}


def _load_summary(zip_path: Path) -> dict | None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return json.loads(zf.read(_MEMBER))
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        return None


def _load_census(zip_path: Path) -> dict | None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return json.loads(gzip.decompress(zf.read(_CENSUS_MEMBER)))
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError, OSError):
        return None


def _seed_of(params: dict) -> int:
    return int(str(params.get("run_id", "")).rsplit("_s", 1)[-1])


def _cell_key(params: dict) -> tuple:
    return (
        params.get("boarding_mechanism_rung"),
        params.get("never_symptomatic_fraction"),
        params.get("boarding_passenger_prevalence"),
        params.get("boarding_crew_prevalence"),
        params.get("dose_adjustment"),
        params.get("pathogen"),
    )


def _cell_label(params: dict) -> str:
    rung = _RUNG_LABEL.get(
        params.get("boarding_mechanism_rung"), str(
            params.get("boarding_mechanism_rung"),
        ),
    )
    nsf = params.get("never_symptomatic_fraction")
    prev_pax = params.get("boarding_passenger_prevalence")
    prev_crew = params.get("boarding_crew_prevalence")
    prev = (
        f" prev={prev_pax}/{prev_crew}"
        if prev_pax is not None else ""
    )
    dose = params.get("dose_adjustment")
    dose_s = f" dose={dose}" if dose is not None else ""
    return f"{rung} nsf={nsf}{prev}{dose_s}"


def _outcomes(summary: dict) -> dict:
    census = summary.get("census") or {}
    derived = summary.get("derived") or {}
    return {
        "ignited": bool(census.get("ignited")),
        "took_off": float(derived.get("peak_prevalence") or 0.0)
        >= TAKEOFF_PEAK_PREVALENCE,
        "posted": derived.get("vsp_trigger_epoch") is not None,
        "n_acquired": int(census.get("n_acquired") or 0),
        "peak": float(derived.get("peak_prevalence") or 0.0),
    }


def _cell_metrics(rows: list[dict]) -> dict:
    n = len(rows)
    ign = sum(r["ignited"] for r in rows)
    off = sum(r["took_off"] for r in rows)
    post = sum(r["posted"] for r in rows)
    peaks = sorted(r["peak"] for r in rows)
    acq = sorted(r["n_acquired"] for r in rows)
    return {
        "n": n,
        "ignited": ign,
        "ignition_ci": _wilson(ign, n),
        "took_off": off,
        "takeoff_ci": _wilson(off, n),
        "posted": post,
        "posting_ci": _wilson(post, n),
        "median_acquired": acq[n // 2] if acq else 0,
        "peak_median": peaks[n // 2] if peaks else 0.0,
        "peak_max": peaks[-1] if peaks else 0.0,
    }


def _concurrent_peak(census: dict) -> int:
    rows = census.get("census_epochs") or []
    return max((int(r.get("infected", 0)) for r in rows), default=0)


def _placement(censuses: list[dict]) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for census in censuses:
        for emit in census.get("emits") or []:
            counts[str(emit.get("zone_type") or "unknown")] += 1
    total = sum(counts.values()) or 1
    return {
        "total_emits": sum(counts.values()),
        "by_zone_type": {
            k: {"n": v, "share": v / total}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
        },
    }


def _stream_witness(summaries: list[dict], num_agents: float) -> dict:
    """Resolved-stream fields plus drawn symptomatic counts vs binomial."""
    resolved = []
    total_sym = 0
    n = 0
    for summary in summaries:
        block = (summary.get("initiation") or {})
        res = block.get("resolved") or {}
        manifest = block.get("manifest") or {}
        comp = ((manifest.get("boarding") or {}).get("norwalk_gi")
                or {}).get("composition") or {}
        resolved.append(res)
        total_sym += int(comp.get("symptomatic") or 0)
        n += 1
    first = resolved[0] if resolved else {}
    uniform = all(r == first for r in resolved)
    p_sym = float(first.get("symptomatic_passenger_prevalence") or 0.0)
    expected = p_sym * num_agents * n
    sd = math.sqrt(max(expected * (1 - p_sym), 1e-9))
    z = (total_sym - expected) / sd if sd else 0.0
    return {
        "n_runs": n,
        "resolved_rate_mode": first.get("rate_mode"),
        "resolved_stream": (first.get("symptomatic_stream") or {}).get(
            "enabled",
        ) if isinstance(first.get("symptomatic_stream"), dict)
        else first.get("symptomatic_stream"),
        "p_sym_passenger": p_sym,
        "p_sym_crew": first.get("symptomatic_crew_prevalence"),
        "fields_uniform": bool(uniform),
        "symptomatic_drawn_total": total_sym,
        "symptomatic_expected_approx": expected,
        "symptomatic_z": z,
    }


def collect(root: Path, tiers: list[str] | None = None) -> dict:
    """Walk <root>/<tier>/*.zip into per-tier cell + witness tables."""
    out: dict[str, dict] = {}
    for tier_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        tier = tier_dir.name
        if tiers and tier not in tiers:
            continue
        cells: dict[tuple, dict] = {}
        censuses: dict[tuple, list[dict]] = defaultdict(list)
        summaries: dict[tuple, list[dict]] = defaultdict(list)
        for zip_path in sorted(tier_dir.glob("*.zip")):
            summary = _load_summary(zip_path)
            if summary is None:
                continue
            params = summary.get("parameters") or {}
            key = _cell_key(params)
            entry = cells.setdefault(key, {
                "params": params, "rows": [], "by_seed": {},
            })
            row = {"seed": _seed_of(params), **_outcomes(summary)}
            entry["rows"].append(row)
            entry["by_seed"][row["seed"]] = row
            summaries[key].append(summary)
            if row["ignited"]:
                census = _load_census(zip_path)
                if census:
                    entry.setdefault("peaks", []).append(
                        _concurrent_peak(census),
                    )
                    censuses[key].append(census)
        table = []
        witness = []
        for key, entry in sorted(
            cells.items(), key=lambda kv: str(kv[0]),
        ):
            metrics = _cell_metrics(entry["rows"])
            metrics["label"] = _cell_label(entry["params"])
            metrics["params"] = entry["params"]
            peaks = sorted(entry.get("peaks") or [])
            metrics["depth_median"] = (
                peaks[len(peaks) // 2] if peaks else 0
            )
            metrics["depth_max"] = peaks[-1] if peaks else 0
            metrics["placement"] = _placement(censuses.get(key, []))
            table.append(metrics)
            witness.append({
                "label": metrics["label"],
                **_stream_witness(
                    summaries[key],
                    float(entry["params"].get("num_agents") or 0),
                ),
            })
        out[tier] = {"cells": cells, "table": table, "witness": witness}
    return out


def _discordance(collected: dict) -> list[dict]:
    """Shared-seed ignited/not counts between rung-paired cells."""
    rows = []
    for tier, blob in collected.items():
        cells = blob["cells"]
        rungs: dict[float, dict[str, dict]] = defaultdict(dict)
        for key, entry in cells.items():
            rungs[key[1] or 0.0][key[0] or ""] = entry["by_seed"]
        for nsf, arms in rungs.items():
            rung_names = sorted(arms)
            for i, a in enumerate(rung_names):
                for b in rung_names[i + 1:]:
                    shared = set(arms[a]) & set(arms[b])
                    if not shared:
                        continue
                    a_only = sum(
                        arms[a][s]["ignited"] and not arms[b][s]["ignited"]
                        for s in shared
                    )
                    b_only = sum(
                        arms[b][s]["ignited"] and not arms[a][s]["ignited"]
                        for s in shared
                    )
                    rows.append({
                        "tier": tier, "nsf": nsf,
                        "arm_a": a, "arm_b": b, "shared": len(shared),
                        "a_only": a_only, "b_only": b_only,
                    })
    return rows


def build_report(root: Path, tiers: list[str] | None = None) -> dict:
    collected = collect(root, tiers)
    return {
        "tiers": collected,
        "discordance": _discordance(collected),
    }


def _rate(x: int, n: int) -> str:
    if not n:
        return "-"
    lo, hi = _wilson(x, n)
    return f"{x}/{n} ({100 * x / n:.2f}% [{100 * lo:.2f},{100 * hi:.2f}])"


def _cell_lines(rows: list[dict]) -> list[str]:
    lines = [
        "| cell | n | ignited | takeoff | posted | med acq | peak med/max | depth med/max |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['label']} | {r['n']} | {_rate(r['ignited'], r['n'])} | "
            f"{_rate(r['took_off'], r['n'])} | {_rate(r['posted'], r['n'])} | "
            f"{r['median_acquired']} | {r['peak_median']:.0f}/{r['peak_max']:.0f} | "
            f"{r['depth_median']}/{r['depth_max']} |"
        )
    return lines


def _witness_lines(rows: list[dict]) -> list[str]:
    lines = [
        "| cell | rate_mode | stream | p_sym pax | drawn sym (exp) | z |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['label']} | {r['resolved_rate_mode']} | "
            f"{r['resolved_stream']} | {r['p_sym_passenger']} | "
            f"{r['symptomatic_drawn_total']} "
            f"({r['symptomatic_expected_approx']:.1f}) | "
            f"{r['symptomatic_z']:.1f} |"
        )
    return lines


def render_markdown(report: dict) -> str:
    lines = ["# NORO-IMPORT-01 region map readout", ""]
    tiers = report["tiers"]
    for tier in sorted(tiers):
        blob = tiers[tier]
        flagged = tier in (_DOSE_TIER, _ALPHA_TIER, _FLAG_TIER)
        lines.append(
            f"## {tier} {'(flagged — outside the licensed map)' if flagged else ''}",
        )
        lines += _cell_lines(blob["table"])
        lines.append("")
    disc = report["discordance"]
    if disc:
        lines += ["## Paired discordance (shared seeds)", "",
                  "| tier | nsf | arm a | arm b | shared | a only | b only |",
                  "|---|---|---|---|---|---|---|"]
        for r in disc:
            lines.append(
                f"| {r['tier']} | {r['nsf']} | {r['arm_a']} | {r['arm_b']} | "
                f"{r['shared']} | {r['a_only']} | {r['b_only']} |"
            )
        lines.append("")
    lines += ["## Symptomatic-stream witness", ""]
    for tier in sorted(tiers):
        lines += _witness_lines(tiers[tier]["witness"])
        lines.append("")
    lines += ["## Emesis placement partition (ignited voyages)", "",
              "| tier | cell | total emits | share by zone_type |",
              "|---|---|---|---|"]
    for tier in sorted(tiers):
        for r in tiers[tier]["table"]:
            pl = r["placement"]
            shares = ", ".join(
                f"{k}: {v['share']:.0%}" for k, v in pl["by_zone_type"].items()
            )
            lines.append(
                f"| {tier} | {r['label']} | {pl['total_emits']} | {shares} |",
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--tiers", nargs="*", default=None)
    args = parser.parse_args()
    report = build_report(args.runs_dir, args.tiers)
    md = render_markdown(report)
    if args.md_out:
        out_dir = prepare_output_directory(
            str(args.md_out.parent), allowed_roots=(str(_REPO_ROOT),),
        )
        with validated_open(
            str(Path(out_dir) / args.md_out.name), "w",
            encoding="utf-8", allowed_roots=(str(_REPO_ROOT),),
        ) as fh:
            fh.write(md + "\n")
    else:
        print(md)
    if args.json_out:
        json_dir = prepare_output_directory(
            str(args.json_out.parent), allowed_roots=(str(_REPO_ROOT),),
        )
        with validated_open(
            str(Path(json_dir) / args.json_out.name), "w",
            encoding="utf-8", allowed_roots=(str(_REPO_ROOT),),
        ) as fh:
            fh.write(json.dumps(report, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
