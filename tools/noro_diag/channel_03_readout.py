#!/usr/bin/env python3
"""NORO-CHANNEL-03 funnel readout — per-cell conversion-link attribution.

Reads the per-seed funnel dumps the ``noro_channel_03`` Batch entrypoint
uploads under ``<prefix>/<tier>/<matchtag>/*.json.gz`` (layout mirrors the
map prefix), pools each declared cell, and renders the frozen design's
attribution: the infection -> illness -> report rung chain pooled over the
exact voyages NORO-OUTBREAK-01 scored, twice (all voyages and
takeoff-conditional), plus the not-reported decomposition and the
pre-declared link verdict.

Verdict thresholds (frozen in docs/norovirus/noro_channel_03_design.md):

- infected -> symptomatic course below ~0.6 while reporting works -> the
  A2 link (symptom-course draw) carries the gap;
- symptomatic -> eligible below ~0.7 while reporting works -> the
  severity/eligibility wall;
- eligible -> reported below ~0.4 with hazard exposure present -> the A4
  link (reporting hazard / trust scaling);
- eligible hosts absent onboard while symptomatic -> the censoring path
  (isolation/departure), split recorded in the dump.

With ``--map-root`` (a campaign run-zip root, local dir or ``s3://``
prefix), each seed's funnel ``took_off`` is checked against the map
voyage's ``peak_prevalence >= 10`` — a disagreement voids the per-voyage
join and is reported per seed.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import validated_open  # noqa: E402
from tools.noro_diag.outbreak_anchor_readout import (  # noqa: E402
    _collect_s3,
)

TAKEOFF_PEAK_PREVALENCE = 10  # score_anchors.TAKEOFF_PEAK_PREVALENCE

# Pre-declared link thresholds (design doc, do not tune).
THRESH_SYMPTOMATIC = 0.6    # infected -> symptomatic course
THRESH_ELIGIBLE = 0.7       # symptomatic -> syndrome-eligible
THRESH_REPORTED = 0.4       # eligible -> reported (hazard exposure present)

# NORO-CAREGIVER-01 report-immediately triggers (frozen in the
# caregiver design doc; evaluated on the re-measurement cells).
TRIGGER_CAREGIVER_TX_SHARE = 0.10  # caregiver share of transmissions

_SEED_ART = re.compile(r"observation_channel_funnel_(?P<arm>.+)_seed(?P<seed>\d+)\.json\.gz$")


def _s3_list_dumps(prefix: str) -> list[str]:
    """Keys of every funnel dump under an ``s3://`` prefix."""
    from deploy.aws.dose_challenge_entrypoint import _s3_client, _s3_uri

    bucket, pre = _s3_uri(prefix)
    client = _s3_client()
    found = []
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": pre + "/"}
        if token:
            kw["ContinuationToken"] = token
        page = client.list_objects_v2(**kw)
        for obj in page.get("Contents", []):
            if _SEED_ART.search(obj["Key"]):
                found.append(obj["Key"])
        token = page.get("NextContinuationToken")
        if not token:
            return found


def _s3_fetch_json(key: str, prefix: str) -> dict:
    from deploy.aws.dose_challenge_entrypoint import _s3_client, _s3_uri

    bucket, _ = _s3_uri(prefix)
    obj = _s3_client().get_object(Bucket=bucket, Key=key)
    return json.loads(gzip.decompress(obj["Body"].read()))


def collect(root: str) -> list[dict]:
    """Per-seed funnel dumps under a local dir or an s3:// prefix."""
    root = root.rstrip("/")
    dumps = []
    if root.startswith("s3://"):
        for key in _s3_list_dumps(root):
            d = _s3_fetch_json(key, root)
            d["_cell_dir"] = key.rsplit("/", 2)[-2] if "/" in key else "cell"
            dumps.append(d)
        return dumps
    for path in sorted(Path(root).rglob("*_seed*.json.gz")):
        d = json.loads(gzip.decompress(path.read_bytes()))
        d["_cell_dir"] = path.parent.name
        dumps.append(d)
    return dumps


def _bucket(dump: dict) -> tuple[str, str]:
    """(tier, matchtag) — the entrypoint's <tier>/<matchtag> dirs."""
    cell = dump.get("cell") or {}
    tier = cell.get("tier", "")
    return (str(tier), str(dump.get("_cell_dir") or "cell"))


def _rung(dump: dict, name: str) -> dict:
    return (dump.get("rungs") or {}).get(name) or {}


def _med_iqr(values: list[float]) -> str:
    if not values:
        return "-"
    xs = sorted(values)
    n = len(xs)
    med = xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])
    q1 = xs[n // 4]
    q3 = xs[min(n - 1, (3 * n) // 4)]
    return f"{med:.3f} [{q1:.3f}, {q3:.3f}]"


def _agg_cell(dumps: list[dict], takeoff_only: bool) -> dict:
    sel = [d for d in dumps if not takeoff_only or d.get("took_off")]
    rung_names = [
        "infected", "symptomatic_course", "symptomatic_onboard",
        "syndrome_eligible", "eligible_onboard", "reported_infirmary",
        "lab_sampled", "lab_confirmed", "onset_dated",
    ]
    pooled = {r: {"total": 0, "passenger": 0, "crew": 0} for r in rung_names}
    per_seed = defaultdict(list)
    nonrep = defaultdict(int)
    hazard_epochs = 0
    seeds = []
    cg = defaultdict(float)
    cg_voyages = 0
    for d in sel:
        seeds.append(int(d["seed"]))
        for r in rung_names:
            rec = _rung(d, r)
            for k in ("total", "passenger", "crew"):
                pooled[r][k] += int(rec.get(k) or 0)
        ratios = d.get("ratios") or {}
        for key in ("symptomatic_per_infected", "eligible_per_symptomatic",
                    "reported_per_eligible"):
            v = ratios.get(key)
            if v is not None:
                per_seed[key].append(float(v))
        for k, v in (d.get("non_report_decomposition") or {}).items():
            nonrep[k] += int(v)
        if (d.get("channel_totals") or {}).get("beliefs_nonempty_epochs"):
            hazard_epochs += 1
        block = d.get("caregiver") or {}
        if not block:
            continue
        cg_voyages += 1
        engine = block.get("engine_counters") or {}
        cg["responses"] += float(engine.get("caregiver_responses") or 0)
        cg["steward_responses"] += float(engine.get("steward_responses") or 0)
        cg["reports"] += float(engine.get("caregiver_reports") or 0)
        cg["dose_credited"] += float(engine.get("caregiver_dose_credited") or 0)
        via = (_rung(d, "reported_infirmary").get("via_caregiver") or {})
        cg["reported_via"] += int(via.get("total") or 0)
        cg["dominant_tx"] += int(block.get("transmissions_dominant_caregiver") or 0)
        cg["any_dose_tx"] += int(block.get("transmissions_any_caregiver_dose") or 0)
        cg["attributed_tx"] += int(block.get("transmissions_attributed") or 0)
        cg["stamped"] += int(block.get("stamped_hosts") or 0)
        cg["stamped_not_reported"] += int(block.get("stamped_not_reported") or 0)
        cg["nonemetic"] += len(block.get("reports_on_nonemetic_course") or [])
        responses = (
            float(engine.get("caregiver_responses") or 0)
            + float(engine.get("steward_responses") or 0)
        )
        if block.get("vomiting_course_hosts") and not responses:
            cg["zero_response_voyages"] += 1
    inf = pooled["infected"]["total"]
    sym = pooled["symptomatic_course"]["total"]
    eli = pooled["syndrome_eligible"]["total"]
    rep = pooled["reported_infirmary"]["total"]
    conf = pooled["lab_confirmed"]["total"]
    dated = pooled["onset_dated"]["total"]
    return {
        "seeds": sorted(seeds),
        "n": len(sel),
        "takeoff": sum(1 for d in sel if d.get("took_off")),
        "pooled": pooled,
        "caregiver": {
            "voyages_with_block": cg_voyages,
            **{k: (int(v) if v == int(v) else v) for k, v in cg.items()},
            "share_of_reported": (
                cg["reported_via"] / rep if rep else None
            ),
            "share_of_transmissions": (
                cg["dominant_tx"] / cg["attributed_tx"]
                if cg["attributed_tx"] else None
            ),
        },
        "ratios": {
            "symptomatic_per_infected": sym / inf if inf else None,
            "eligible_per_symptomatic": eli / sym if sym else None,
            "reported_per_eligible": rep / eli if eli else None,
            "confirmed_per_reported": conf / rep if rep else None,
            "dated_per_confirmed": dated / conf if conf else None,
        },
        "per_seed_median_iqr": {k: _med_iqr(v) for k, v in per_seed.items()},
        "non_report_decomposition": dict(nonrep),
        "hazard_exposure_seeds": hazard_epochs,
    }


def _link_verdict(agg: dict) -> str:
    """Frozen threshold read: which link carries the gap, or none."""
    r = agg["ratios"]
    if r["symptomatic_per_infected"] is not None and r["symptomatic_per_infected"] < THRESH_SYMPTOMATIC:
        rest = (
            "A2 link — symptom-course draw under-fires "
            f"({r['symptomatic_per_infected']:.3f} < {THRESH_SYMPTOMATIC})"
        )
        return rest
    if r["eligible_per_symptomatic"] is not None and r["eligible_per_symptomatic"] < THRESH_ELIGIBLE:
        return (
            "severity/eligibility wall — "
            f"{r['eligible_per_symptomatic']:.3f} < {THRESH_ELIGIBLE}"
        )
    if r["reported_per_eligible"] is not None and r["reported_per_eligible"] < THRESH_REPORTED:
        detail = ""
        if agg["non_report_decomposition"]:
            detail = "; non-report split " + ", ".join(
                f"{k}={v}" for k, v in sorted(
                    agg["non_report_decomposition"].items())
            )
        return (
            "A4 link — reporting hazard under-fires "
            f"({r['reported_per_eligible']:.3f} < {THRESH_REPORTED})"
            + detail
        )
    return "no single link under its declared threshold"


def _map_takeoff_lookup(map_root: str) -> dict[str, bool]:
    """run_id -> took_off under the map's scoring (peak_prevalence >= 10).

    ``_collect_s3`` reads the map run zips' ``summary.json`` members via
    ranged S3 GETs — the same streaming path the anchor readout uses.
    """
    rows = _collect_s3(map_root)
    return {
        row["run_id"]: int(row.get("peak_prevalence") or 0) >= TAKEOFF_PEAK_PREVALENCE
        for row in rows
    }


def _trigger_lines(name: str, agg: dict) -> list[str]:
    """Frozen report-immediately triggers evaluated on a cell's pool."""
    cg = agg["caregiver"]
    if not cg["voyages_with_block"]:
        return []
    fired = []
    share = cg["share_of_transmissions"]
    if share is not None and share > TRIGGER_CAREGIVER_TX_SHARE:
        fired.append(
            f"{name}: caregiver share of transmissions {share:.3f} "
            f"> {TRIGGER_CAREGIVER_TX_SHARE}"
        )
    if cg["nonemetic"]:
        fired.append(
            f"{name}: {int(cg['nonemetic'])} caregiver report(s) on "
            "non-emetic courses"
        )
    if cg["zero_response_voyages"]:
        fired.append(
            f"{name}: {int(cg['zero_response_voyages'])} voyage(s) with "
            "vomiting courses but zero caregiver/steward responses"
        )
    return fired


def render(cells: dict[tuple[str, str], list[dict]], map_root: str | None) -> tuple[str, dict]:
    lines = [
        "| cell | n (tookoff) | symp/infected | elig/symp | rep/elig | viaCG | CGtx | conf/rep | dated/conf | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    out = {"cells": {}, "join_violations": [], "triggers": []}
    for (tier, match), dumps in sorted(cells.items()):
        name = f"{tier}/{match}"
        allagg = _agg_cell(dumps, takeoff_only=False)
        tkagg = _agg_cell(dumps, takeoff_only=True)
        verdict = _link_verdict(tkagg if tkagg["n"] else allagg)
        r = tkagg["ratios"] if tkagg["n"] else allagg["ratios"]
        cgagg = tkagg if tkagg["n"] else allagg
        cg = cgagg["caregiver"]
        out["triggers"].extend(_trigger_lines(name, cgagg))

        def f(x):
            return "-" if x is None else f"{x:.3f}"

        via_cg = (
            f(cg["share_of_reported"]) if cg["voyages_with_block"] else "-"
        )
        cg_tx = (
            f(cg["share_of_transmissions"]) if cg["voyages_with_block"]
            else "-"
        )
        lines.append(
            f"| {name} | {allagg['n']} ({allagg['takeoff']}) | "
            f"{f(r['symptomatic_per_infected'])} | "
            f"{f(r['eligible_per_symptomatic'])} | "
            f"{f(r['reported_per_eligible'])} | "
            f"{via_cg} | {cg_tx} | "
            f"{f(r['confirmed_per_reported'])} | "
            f"{f(r['dated_per_confirmed'])} | {verdict} |"
        )
        out["cells"][name] = {
            "all": allagg,
            "takeoff_only": tkagg,
            "verdict": verdict,
        }
        if map_root:
            lookup = _map_takeoff_lookup(map_root)
            for d in dumps:
                rid = d.get("run_id")
                if rid in lookup and lookup[rid] != bool(d.get("took_off")):
                    out["join_violations"].append(
                        {"cell": name, "run_id": rid,
                         "funnel_took_off": bool(d.get("took_off")),
                         "map_took_off": lookup[rid]})
    if out["join_violations"]:
        lines.append("")
        lines.append(
            f"**JOIN VOID**: {len(out['join_violations'])} seeds disagree "
            "between funnel `took_off` and the map's `peak_prevalence >= 10` — "
            "the funnel voyage is not its scored twin; all attributions above are void.")
    if out["triggers"]:
        lines.append("")
        lines.append("**Report-immediately triggers fired**:")
        lines.extend(f"- {line}" for line in out["triggers"])
    return "\n".join(lines) + "\n", out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True,
                   help="local dump dir or s3:// prefix of the funnel artifacts")
    p.add_argument("--map-root", default=None,
                   help="optional campaign run root (dir or s3://) to verify "
                        "the per-seed takeoff join against the scored map")
    p.add_argument("--md-out", type=Path, default=None)
    p.add_argument("--json-out", type=Path, default=None)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    dumps = collect(args.root)
    if not dumps:
        raise SystemExit(f"no funnel dumps under {args.root}")
    cells = defaultdict(list)
    for d in dumps:
        cells[_bucket(d)].append(d)
    md, out = render(cells, args.map_root)
    print(md)
    if args.md_out:
        allowed = (str(args.md_out.parent.resolve()),)
        with validated_open(
            str(args.md_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            fh.write(md)
    if args.json_out:
        allowed = (str(args.json_out.parent.resolve()),)
        with validated_open(
            str(args.json_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            fh.write(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
