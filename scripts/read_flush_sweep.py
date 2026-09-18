#!/usr/bin/env python3
"""Paired-seed readout of the flush_sweep_v1 s3 re-bracket.

Reads the four synced arm archives, pairs every arm against `off` on the
shared seed, and reports the contrast per hull/length cell. No comparator
enters this script: posting is reported for contrast only and nothing here
selects a fraction.

Per voyage:
  ever         = final cumulative_ever_infected (the metric of record; the
                 paired contrast needs no import subtraction and so does not
                 depend on where the boarding cohort stops being countable)
  epoch0       = cumulative_ever_infected in the first timeseries row, which
                 is written *after* epoch 0 executes and therefore already
                 contains any same-epoch flush transmission
  posting      = passenger_reported_case_rate_exceeded on any epoch
                 (the VSP 3% reportable-case threshold)
  flush witness= sanitary_activity.flush_dose_delivered / flush_recipients
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import zipfile
from pathlib import Path

DEFAULT_ROOT = Path("~/campaign_results/flush_s3").expanduser()
DEFAULT_OUT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "norovirus"
    / "flush_sweep_v1_stage3_readout.md"
)
ARMS = ["off", "1e-9", "1e-7", "1e-5"]
CELLS = ["fl_exp_7d", "fl_exp_12d", "fl_cls_7d", "fl_cls_12d", "fl_spr_7d", "fl_spr_12d"]


def read_voyage(zf: zipfile.ZipFile, run_dir: str) -> dict:
    summary = json.loads(zf.read(f"{run_dir}/summary.json"))
    series = json.loads(zf.read(f"{run_dir}/timeseries.json"))
    imports = series[0]["cumulative_ever_infected"]
    final = series[-1]["cumulative_ever_infected"]
    sa = summary["summary"]["sanitary_activity"]
    return {
        "tier": summary["parameters"]["tier_id"],
        "seed": summary["parameters"]["seed"],
        "fraction": summary["parameters"]["flush_aerosol_fraction"],
        "sha": summary["parameters"]["engine_git_sha"],
        "epoch0": imports,
        "ever": final,
        "secondaries": final - imports,
        "posted": any(e["passenger_reported_case_rate_exceeded"] for e in series),
        "flush_dose": sa.get("flush_dose_delivered", 0.0),
        "flush_recipients": sa.get("flush_recipients", 0),
        "flush_events": sa.get("flush_events", 0),
        "flush_emitted": sa.get("flush_aerosol_emitted", 0.0),
        "routes": summary["summary"]["infections_by_dominant_route"],
        "pax_reported_rate": summary["summary"]["reported_case_rate_passenger"],
        "platform": summary["parameters"]["platform_id"],
        "days": summary["parameters"]["num_epochs"] // 24,  # clock-exempt: cell label from 1-hour-epoch archives
    }


def load_arm(arm: str, root: Path) -> dict:
    out: dict[tuple[str, int], dict] = {}
    fractions, shas = set(), set()
    for path in sorted((root / f"flush_sweep_v1_{arm}_s3").glob("shard-*.zip")):
        with zipfile.ZipFile(path) as zf:
            dirs = {n.split("/")[0] for n in zf.namelist() if "/" in n}
            for run_dir in dirs:
                v = read_voyage(zf, run_dir)
                out[(v["tier"], v["seed"])] = v
                fractions.add(v["fraction"])
                shas.add(v["sha"])
    return {"runs": out, "fractions": fractions, "shas": shas}


def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson score interval, the same posting interval the s2r readout used."""
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def emit_readout(arms: dict, out: Path) -> None:
    lines = [
        "# Which decade of the flush aerosol fraction first moves an outcome: "
        "the s3 re-bracket on the current engine",
        "",
        "**Measured at:** `65d9fb2821c4d389eb92d3470d61f0ab06b84b3a` "
        "(`parameters.engine_git_sha`, read from every archived run).",
        "",
        "Posting rule: reported cases >= 3% of passengers or of crew. "
        "`f_aero` is each arm's own archived `flush_aerosol_fraction`, read "
        "from the run parameters and not from a prefix. `ev. v.` counts "
        "voyages with any emitting flush; `recipients` counts exposure "
        "events, not hosts. `dose/exp` is pooled inhaled particles per "
        "exposure event, against N50 = 16,871. `mean ever` is mean "
        "cumulative ever-infected per voyage and `zero` the fraction of "
        "voyages with no establishment beyond the boarding cohort. Route "
        "columns are shares of dominant-route attributions. Every `off` row "
        "must show zero flush events: the baseline is the disabled path, not "
        "the sweep evaluated at zero.",
        "",
        "| platform | days | arm | f_aero | voyages | ev. v. | emitted | "
        "recipients | dose/exp | mean ever | zero | flush % | hvac % | "
        "fomite % | post/1,000 | posting CI | median pax reported AR |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell in CELLS:
        for arm in ARMS:
            runs = arms[arm]["runs"]
            keys = sorted(k for k in runs if k[0] == cell)
            v = [runs[k] for k in keys]
            n = len(v)
            emitted = sum(x["flush_emitted"] for x in v)
            recips = sum(x["flush_recipients"] for x in v)
            dose = sum(x["flush_dose"] for x in v)
            routes: dict[str, int] = {}
            for x in v:
                for r, c in x["routes"].items():
                    routes[r] = routes.get(r, 0) + c
            tot = sum(routes.values()) or 1
            posted = [x for x in v if x["posted"]]
            lo, hi = wilson(len(posted), n)
            ar = (
                f"{statistics.median([x['pax_reported_rate'] for x in posted]):.4f}"
                if posted
                else "n/a"
            )
            per_exp = f"{dose / recips:.2e}" if recips else "n/a"
            lines.append(
                f"| {v[0]['platform']} | {v[0]['days']} | {arm} "
                f"| {v[0]['fraction']:.2e} | {n} "
                f"| {sum(1 for x in v if x['flush_events'] > 0)} "
                f"| {emitted:.2e} | {recips} "
                f"| {per_exp} "
            )
            lines[-1] += (
                f"| {statistics.fmean([x['ever'] for x in v]):.2f} "
                f"| {sum(1 for x in v if x['secondaries'] == 0) / n:.3f} "
                f"| {100.0 * routes.get('flush_aerosol', 0) / tot:.1f}% "
                f"| {100.0 * routes.get('hvac_airborne', 0) / tot:.1f}% "
                f"| {100.0 * routes.get('fomite', 0) / tot:.1f}% "
                f"| {1000.0 * len(posted) / n:.1f} "
                f"| [{lo:.4f}, {hi:.4f}] | {ar} |"
            )
    out.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {out}")


def paired_delta(live: list[float], base: list[float]) -> tuple[float, float, float]:
    """Mean paired difference and its normal-approximation 95% interval."""
    diffs = [a - b for a, b in zip(live, base)]
    mean = statistics.fmean(diffs)
    if len(diffs) < 2:
        return mean, mean, mean
    half = 1.96 * statistics.stdev(diffs) / math.sqrt(len(diffs))
    return mean, mean - half, mean + half


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    arms = {arm: load_arm(arm, args.archives) for arm in ARMS}

    print("== provenance ==")
    for arm in ARMS:
        a = arms[arm]
        print(
            f"{arm:>5}: n={len(a['runs'])} fractions={sorted(a['fractions'])} "
            f"sha={sorted(a['shas'])}"
        )

    base = arms["off"]["runs"]
    print("\n== epoch-0 count vs off on the shared seed ==")
    for arm in ARMS[1:]:
        runs = arms[arm]["runs"]
        keys = sorted(set(runs) & set(base))
        diff = [k for k in keys if runs[k]["epoch0"] != base[k]["epoch0"]]
        higher = sum(runs[k]["epoch0"] > base[k]["epoch0"] for k in diff)
        print(
            f"{arm:>5}: {len(keys) - len(diff)}/{len(keys)} equal; "
            f"{len(diff)} differ, {higher} of them higher"
        )

    print("\n== ever-infected per voyage (mean), paired delta vs off ==")
    header = f"{'cell':<12}{'off':>8}"
    for arm in ARMS[1:]:
        header += f"{arm:>10}{'delta [95%]':>26}"
    print(header)
    for cell in CELLS:
        keys = sorted(k for k in base if k[0] == cell)
        b = [base[k]["ever"] for k in keys]
        row = f"{cell:<12}{statistics.fmean(b):>8.2f}"
        for arm in ARMS[1:]:
            runs = arms[arm]["runs"]
            live = [runs[k]["ever"] for k in keys]
            m, lo, hi = paired_delta(live, b)
            row += f"{statistics.fmean(live):>10.2f}"
            row += f"{f'{m:+.2f} [{lo:+.2f}, {hi:+.2f}]':>26}"
        print(row)

    print("\n== posting per 1,000 voyages (contrast only, nothing selected) ==")
    print(f"{'cell':<12}" + "".join(f"{a:>10}" for a in ARMS))
    for cell in CELLS:
        keys = sorted(k for k in base if k[0] == cell)
        row = f"{cell:<12}"
        for arm in ARMS:
            runs = arms[arm]["runs"]
            posted = sum(runs[k]["posted"] for k in keys)
            row += f"{1000.0 * posted / len(keys):>10.0f}"
        print(row)

    print("\n== flush witness: mean dose delivered / recipients / events per voyage ==")
    print(f"{'cell':<12}" + "".join(f"{a:>26}" for a in ARMS))
    for cell in CELLS:
        keys = sorted(k for k in base if k[0] == cell)
        row = f"{cell:<12}"
        for arm in ARMS:
            runs = arms[arm]["runs"]
            dose = statistics.fmean([runs[k]["flush_dose"] for k in keys])
            recip = statistics.fmean([runs[k]["flush_recipients"] for k in keys])
            ev = statistics.fmean([runs[k]["flush_events"] for k in keys])
            row += f"{f'{dose:.3g}/{recip:.0f}/{ev:.0f}':>26}"
        print(row)

    print("\n== attack rate among posted voyages (passenger reported case rate) ==")
    for arm in ARMS:
        runs = arms[arm]["runs"]
        posted = [k for k in runs if runs[k]["posted"]]
        print(f"{arm:>5}: {len(posted)} posted voyages of {len(runs)}")

    emit_readout(arms, args.out)


if __name__ == "__main__":
    main()
