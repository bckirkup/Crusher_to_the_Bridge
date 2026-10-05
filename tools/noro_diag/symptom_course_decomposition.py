#!/usr/bin/env python3
"""NORO-SYMPTOM-COURSE-01 infected -> onboard-ill decomposition readout.

Splits the infected -> not-ill loss into three terms:

(a) never-symptomatic course draw — measured directly on clip-free
    acquisitions (``num_epochs - epoch_acquired`` exceeds the incubation
    maximum, so incubation is guaranteed to elapse aboard and a non-ill
    host is a realized never-present draw);
(b) presented course never visible aboard — on the census leg only the
    marker bound is measurable (non-ill infected imports, with
    vomiting_axis/emesis_scheduled as a partial presented marker); on the
    CHANNEL-03 funnel dumps the term is exact:
    ``symptomatic_course - symptomatic_onboard``;
(c) infected too late for an onboard-visible course — a certain-clip
    count (remaining window below the incubation minimum) plus an
    inferred split of the clip band from the declared incubation
    survival function, evaluated at the reference median and the
    dose-conditioned shortening/lengthening clamps. Labelled inferred,
    not measured.

Census leg: the mega a1 fleet zips under
``campaign/noro_mega_impact_01/fl_mega_impact_a1/`` — ``summary.json``
plus the ``hosts[]`` head of ``growth_census.json.gz`` via ranged reads
(the member inflates to ~1 GB; hosts[] closes within ~6 MB of deflate
input).

Funnel leg: the 180 CHANNEL-03 observation dumps under
``campaign/noro_channel_03/`` (aggregates only — no per-host records).

Read-only; no voyage is rerun and nothing is fitted.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import channel_03_readout as _funnel  # noqa: E402
from onset_curve_readout import (  # noqa: E402
    _ACQ_RE,
    _SYMP_RE,
    _census_prefix,
    _host_field,
    _host_records,
    _list_zip_keys,
    _parse_key,
)
from outbreak_anchor_readout import (  # noqa: E402
    _s3_client,
    _s3_member_blob,
    _s3_parse_uri,
)

from simulation_utils.paths import validated_open  # noqa: E402
from tools.diag.readout_common import emit_report_outputs  # noqa: E402

_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_A1_PREFIX = f"s3://{_BUCKET}/campaign/noro_mega_impact_01/fl_mega_impact_a1"
_FUNNEL_ROOT = f"s3://{_BUCKET}/campaign/noro_channel_03"
_PROFILE = Path("data/pathogens/active_profiles.json")

_INF_RE = re.compile(r'"infected_epochs": (\d+)')
_GEN_RE = re.compile(r'"gen": (-?\d+)')
_VOMIT_RE = re.compile(r'"vomiting_axis": (true|false)')
_EMESIS_RE = re.compile(r'"emesis_scheduled": (\d+)')
_CONF_RE = re.compile(r'"confined_epochs": (\d+)')

_EPOCHS_PER_DAY = 24.0  # natural_history_clock "hours" at 1 h epochs

# Dose-conditioning clamps: profile dose_floor / engines.incubation
# MAX_DOSE_FACTOR — shortest and longest declared incubation medians.
_DOSE_FACTOR_LO = 0.3
_DOSE_FACTOR_HI = 2.5


def _profile_incubation(profile_path: Path) -> dict:
    resolved = str(Path(profile_path).resolve())
    with validated_open(
        resolved, "r",
        allowed_roots=(str(Path(resolved).parent),),
        encoding="utf-8",
    ) as fh:
        data = json.load(fh)
    prof = next(
        p for p in data["pathogens"] if p["pathogen_id"] == "norwalk_gi"
    )
    inc = prof["incubation"]
    return {
        "median_days": float(inc["median_days"]),
        "sigma": math.log(float(inc["dispersion"])),
        "min_days": float(inc["min_days"]),
        "max_days": float(inc["max_days"]),
    }


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _incub_sf(days: float, median: float, sigma: float, lo: float, hi: float) -> float:
    """P(T > days) for the declared truncated-lognormal incubation."""
    if days <= lo:
        return 1.0
    if days >= hi:
        return 0.0
    zl = math.log(lo / median) / sigma
    zh = math.log(hi / median) / sigma
    zx = math.log(days / median) / sigma
    return (_phi(zh) - _phi(zx)) / (_phi(zh) - _phi(zl))


def _clip_class(window_ep: float, min_ep: float, max_ep: float) -> str:
    """Onset is visible only if the incubation draw fits inside window_ep."""
    if window_ep <= min_ep:
        return "certain"
    if window_ep <= max_ep:
        return "band"
    return "free"


def _expected_clip(acqs: list[int], n_ep: int, inc: dict, dose_factor: float) -> float:
    med = inc["median_days"] * dose_factor
    return sum(
        _incub_sf(
            (n_ep - a) / _EPOCHS_PER_DAY,
            med, inc["sigma"], inc["min_days"], inc["max_days"],
        )
        for a in acqs
    )


def _is_import(rec: str) -> bool:
    """Census marks boarding infections as ``gen: 0`` (growth_chain_census);
    that marker also covers imports resolved pre-boarding, whose row shows
    ``infected_epochs: 0`` — they count in ``n_imports``/``ever_infected``
    and carry no epoch evidence at all."""
    return _host_field(rec, _GEN_RE) == 0


def _import_marker(rec: str, symp: int) -> bool:
    """Partial presented marker on a non-ill import row."""
    if symp > 0:
        return False
    return (
        _VOMIT_RE.search(rec).group(1) == "true"
        or (_host_field(rec, _EMESIS_RE) or 0) > 0
    )


def _scan_import(rec: str, inf: int, symp: int, row: dict) -> None:
    row["imp_total"] += 1
    row["imp_ill"] += 1 if symp > 0 else 0
    if inf == 0 and symp == 0:
        row["imp_resolved"] += 1
        return
    row["imp_nonill_marker"] += 1 if _import_marker(rec, symp) else 0


def _scan_host(rec: str, n_ep: int, min_ep: float, max_ep: float, row: dict) -> None:
    inf = _host_field(rec, _INF_RE) or 0
    acq = _host_field(rec, _ACQ_RE)
    symp = _host_field(rec, _SYMP_RE) or 0
    imported = _is_import(rec)
    if not (inf > 0 or acq is not None or imported):
        return
    row["infected"] += 1
    row["ill"] += 1 if symp > 0 else 0
    conf = _host_field(rec, _CONF_RE) or 0
    row["symp_epochs"] += symp
    row["confined_epochs_in_course"] += min(conf, symp)
    if imported or acq is None:
        _scan_import(rec, inf, symp, row)
        return
    row["acq_total"] += 1
    row["acq_epochs"].append(acq)
    cls = _clip_class(n_ep - acq, min_ep, max_ep)
    key = "acq_ill_" if symp > 0 else "acq_nonill_"
    row[key + cls] += 1
    row["acq_ill"] += 1 if symp > 0 else 0


def _zip_row(client, bucket: str, key: str, inc: dict) -> dict | None:
    meta = _parse_key(key)
    if meta is None:
        return None
    n_ep = meta["num_epochs"]
    blob = _s3_member_blob(client, bucket, key, "summary.json")
    if blob is None:
        return None
    summary = json.loads(blob)
    text = _census_prefix(client, bucket, key)
    if text is None:
        return None
    hi = text.find('"hosts": [')
    if hi < 0:
        return None
    close = text.find("]", hi)
    hosts = text[hi:close + 1] if close > 0 else text[hi:]
    min_ep = inc["min_days"] * _EPOCHS_PER_DAY
    max_ep = inc["max_days"] * _EPOCHS_PER_DAY
    row = {
        "seed": meta["seed"], "num_epochs": n_ep,
        "infected": 0, "ill": 0, "symp_epochs": 0,
        "confined_epochs_in_course": 0,
        "imp_total": 0, "imp_ill": 0, "imp_resolved": 0,
        "imp_nonill_marker": 0,
        "acq_total": 0, "acq_ill": 0, "acq_epochs": [],
        "acq_nonill_free": 0, "acq_nonill_band": 0, "acq_nonill_certain": 0,
        "acq_ill_free": 0, "acq_ill_band": 0, "acq_ill_certain": 0,
    }
    for rec in _host_records(hosts):
        _scan_host(rec, n_ep, min_ep, max_ep, row)
    summ = summary.get("summary") or {}
    cen = summary.get("census") or {}
    row["sum_ever_infected"] = int(summ.get("cumulative_ever_infected") or 0)
    row["sum_ever_ill"] = int(summ.get("cumulative_ever_ill") or 0)
    row["cen_n_imports"] = int(cen.get("n_imports") or 0)
    row["cen_n_acquired"] = int(cen.get("n_acquired") or 0)
    return row


def _finish_row(row: dict, inc: dict) -> dict:
    acqs = row.pop("acq_epochs")
    n_ep = row["num_epochs"]
    row["exp_clip_lo"] = _expected_clip(acqs, n_ep, inc, _DOSE_FACTOR_LO)
    row["exp_clip_ref"] = _expected_clip(acqs, n_ep, inc, 1.0)
    row["exp_clip_hi"] = _expected_clip(acqs, n_ep, inc, _DOSE_FACTOR_HI)
    row["ill_per_inf"] = row["ill"] / row["infected"] if row["infected"] else None
    free = row["acq_nonill_free"] + row["acq_ill_free"]
    row["free_total"] = free
    row["present_rate_free"] = row["acq_ill_free"] / free if free else None
    return row


def _med(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def _aggregate_voyages(rows: list[dict]) -> dict:
    keys = (
        "infected", "ill", "imp_total", "imp_ill", "imp_resolved",
        "imp_nonill_marker",
        "acq_total", "acq_ill", "acq_nonill_free", "acq_nonill_band",
        "acq_nonill_certain", "acq_ill_free", "acq_ill_band",
        "acq_ill_certain", "free_total", "exp_clip_lo", "exp_clip_ref",
        "exp_clip_hi", "symp_epochs", "confined_epochs_in_course",
    )
    sums = defaultdict(float)
    shares = defaultdict(list)
    mismatches = defaultdict(int)
    for r in rows:
        for k in keys:
            sums[k] += r[k]
        if r["ill_per_inf"] is not None:
            shares["ill_per_inf"].append(r["ill_per_inf"])
        if r["present_rate_free"] is not None:
            shares["present_free"].append(r["present_rate_free"])
        if r["imp_total"]:
            shares["nonill_imp"].append(
                (r["imp_total"] - r["imp_ill"]) / r["imp_total"])
        mismatches["ever_infected"] += int(r["infected"] != r["sum_ever_infected"])
        mismatches["ever_ill"] += int(r["ill"] != r["sum_ever_ill"])
        mismatches["imports"] += int(r["imp_total"] != r["cen_n_imports"])
        mismatches["acquired"] += int(r["acq_total"] != r["cen_n_acquired"])
    return {
        "n_voyages": len(rows),
        "pooled": dict(sums),
        "median_ill_per_inf": _med(shares["ill_per_inf"]),
        "median_present_free": _med(shares["present_free"]),
        "median_nonill_imp_share": _med(shares["nonill_imp"]),
        "crosscheck_mismatches": dict(mismatches),
    }


def _funnel_cells(root: str) -> dict:
    cells = defaultdict(list)
    for dump in _funnel.collect(root):
        cells[_funnel._bucket(dump)].append(dump)
    out = {}
    for (tier, tag), dumps in sorted(cells.items()):
        out[f"{tier}|{tag}"] = _funnel_agg(dumps)
    return out


def _funnel_agg(dumps: list[dict]) -> dict:
    inf = defaultdict(int)
    presented = onboard = 0
    nonrep = defaultdict(int)
    for d in dumps:
        rung = _funnel._rung(d, "infected")
        for k in ("total", "imported", "acquired_onboard"):
            inf[k] += int(rung.get(k) or 0)
        presented += int(_funnel._rung(d, "symptomatic_course").get("total") or 0)
        onboard += int(_funnel._rung(d, "symptomatic_onboard").get("total") or 0)
        for k, v in (d.get("non_report_decomposition") or {}).items():
            nonrep[k] += int(v)
    n = inf["total"]
    return {
        "n_dumps": len(dumps),
        "took_off": sum(1 for d in dumps if d.get("took_off")),
        "infected": n,
        "imported": inf["imported"],
        "acquired_onboard": inf["acquired_onboard"],
        "presented_course": presented,
        "onboard_ill": onboard,
        "presented_never_aboard_b": presented - onboard,
        "never_presented_a_plus_c": n - presented,
        "ill_per_inf": onboard / n if n else None,
        "non_report_decomposition": dict(nonrep),
    }


def _render_mega(lines: list[str], mega: dict) -> None:
    p = mega["pooled"]
    conf = (
        f"{p['confined_epochs_in_course'] / p['symp_epochs']:.3f}"
        if p["symp_epochs"] else "-"
    )
    lines.extend([
        "## Mega a1 census leg",
        "",
        f"voyages read: {mega['n_voyages']} (cross-check mismatches: "
        f"{mega['crosscheck_mismatches']})",
        "",
        "| term | count | share of infected |",
        "|---|---|---|",
        f"| infected | {int(p['infected'])} | 1.000 |",
        f"| onboard ill (symptomatic_epochs>0) | {int(p['ill'])} | "
        f"{p['ill'] / p['infected']:.3f} |",
        f"| imports, never ill aboard (b-side bound) | {int(p['imp_total'] - p['imp_ill'])} | "
        f"{(p['imp_total'] - p['imp_ill']) / p['infected']:.3f} |",
        f"|   of which resolved pre-boarding (0 infected epochs) | {int(p['imp_resolved'])} | "
        f"{p['imp_resolved'] / p['infected']:.3f} |",
        f"| acq non-ill, clip-free (a, measured) | {int(p['acq_nonill_free'])} | "
        f"{p['acq_nonill_free'] / p['infected']:.3f} |",
        f"| acq non-ill, clip band | {int(p['acq_nonill_band'])} | "
        f"{p['acq_nonill_band'] / p['infected']:.3f} |",
        f"| acq non-ill, certain clip (c, measured) | {int(p['acq_nonill_certain'])} | "
        f"{p['acq_nonill_certain'] / p['infected']:.3f} |",
        "",
        "Expected ramp-clip (c) over all acquisitions from the declared",
        "truncated-lognormal incubation SF — inferred, not measured:",
        f"dose factor 0.3 / 1.0 / 2.5 -> {p['exp_clip_lo']:.0f} / "
        f"{p['exp_clip_ref']:.0f} / {p['exp_clip_hi']:.0f} hosts.",
        "",
        f"Clip-free acquisitions {int(p['free_total'])}: presented "
        f"{int(p['acq_ill_free'])}, never presented {int(p['acq_nonill_free'])}",
        f"-> realized never-present share "
        f"{p['acq_nonill_free'] / p['free_total']:.3f} "
        f"(per-voyage median {mega['median_present_free']:.3f} presenting).",
        f"Median per-voyage ill/inf {mega['median_ill_per_inf']:.3f}; "
        f"median non-ill share of imports {mega['median_nonill_imp_share']:.3f}.",
        f"Presented-marker among non-ill imports (partial bound on (b)): "
        f"{int(p['imp_nonill_marker'])}.",
        f"Confined share of symptomatic epochs (report-visibility bound): {conf}.",
        "",
    ])


def _render(report: dict) -> str:
    lines = [
        "# NORO-SYMPTOM-COURSE-01 decomposition — infected -> onboard-ill loss",
        "",
        "Status: measured (readout over committed zips/dumps; no voyage reruns).",
        "",
        "## Decomposition identity",
        "",
        "`infected = onboard_ill + (a) never-symptomatic draw + (b) presented",
        "course never visible aboard + (c) infected too late for a visible",
        "course`. Census leg: (a) is measured on clip-free acquisitions",
        "(remaining window > incubation max 6 d); (c) is the certain-clip",
        "count plus an inferred incubation-SF split of the clip band; (b)",
        "is the non-ill import count with a partial presented-marker bound.",
        "Funnel leg: (b) is exact (`symptomatic_course - symptomatic_onboard`)",
        "and (a)+(c) pool into `infected - symptomatic_course`.",
        "",
    ]
    _render_mega(lines, report["mega_a1"])
    lines += [
        "## CHANNEL-03 funnel leg (small hulls, 180 dumps)",
        "",
        "| cell | dumps (tk) | infected | imp | acq | presented | onboard | b = S-O | a+c = N-S | ill/inf |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell, c in report["funnel_cells"].items():
        ill = f"{c['ill_per_inf']:.3f}" if c["ill_per_inf"] is not None else "-"
        lines.append(
            f"| {cell} | {c['n_dumps']} ({c['took_off']}) | {c['infected']} | "
            f"{c['imported']} | {c['acquired_onboard']} | "
            f"{c['presented_course']} | {c['onboard_ill']} | "
            f"{c['presented_never_aboard_b']} | "
            f"{c['never_presented_a_plus_c']} | {ill} |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a1-prefix", default=_A1_PREFIX)
    ap.add_argument("--funnel-root", default=_FUNNEL_ROOT)
    ap.add_argument("--profile", type=Path, default=_PROFILE)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--md-out", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args(argv)

    inc = _profile_incubation(args.profile)
    bucket, prefix = _s3_parse_uri(args.a1_prefix)
    client = _s3_client()
    keys = [k for k in _list_zip_keys(client, bucket, prefix) if _parse_key(k)]
    keys.sort()
    if args.limit:
        keys = keys[: args.limit]
    print(f"a1 zips: {len(keys)}", file=sys.stderr)

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_zip_row, client, bucket, k, inc) for k in keys]
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            if row is not None:
                rows.append(_finish_row(row, inc))
            if i % 25 == 0:
                print(f"  {i}/{len(keys)} zips", file=sys.stderr)
    rows.sort(key=lambda r: r["seed"])

    report = {
        "campaign": "NORO-SYMPTOM-COURSE-01",
        "a1_prefix": args.a1_prefix,
        "funnel_root": args.funnel_root,
        "incubation": inc,
        "mega_a1": _aggregate_voyages(rows),
        "mega_a1_voyages": rows,
        "funnel_cells": _funnel_cells(args.funnel_root),
    }
    emit_report_outputs(report, _render(report), args.md_out, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
