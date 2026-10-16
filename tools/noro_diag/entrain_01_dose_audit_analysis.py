"""ENTRAIN-01 dose-position audit — analysis over census_rows.jsonl.

Reads the per-voyage rows emitted by ``entrain_01_dose_audit.py`` and
prints the tables the audit doc quotes:

1. Dose-position census per hull x posted/unposted: delivered-dose
   (reconstructed ``acquired_particles``) distribution among acquired
   infections, Hill ``p`` landmarks, E[Hill(dose)] vs realized
   presentation share.
2. Unposted mint census per hull x arm: fraction minting >=1
   common-source object by source_kind, events, takers, credited dose.
3. Cross-check arm ``ind``: same dose-position table split posted vs
   unposted.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

ROWS = Path(
    "telemetry_buffer/entrain_01_dose_audit/census_rows.jsonl"
)
HILLS = {"eta": 0.508, "gamma": 0.095}


def _q(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return float("nan")
    i = min(len(s) - 1, int(q * len(s)))
    return s[i]


def _dose_for_p(p: float) -> float:
    eta, g = HILLS["eta"], HILLS["gamma"]
    return (((1.0 - p) ** (-1.0 / g)) - 1.0) / eta


def dose_position(acqs: list[dict]) -> dict:
    cums = [a["cum"] for a in acqs]
    ps = [a["p"] for a in acqs]
    prs = [bool(a["pr"]) for a in acqs]
    out = {
        "n_voyages": len({a["key"] for a in acqs}),
        "n_acq": len(acqs),
        "cum_med": round(median(cums), 2) if cums else None,
        "cum_p10": round(_q(cums, 0.10), 2),
        "cum_p25": round(_q(cums, 0.25), 2),
        "cum_p75": round(_q(cums, 0.75), 2),
        "cum_p90": round(_q(cums, 0.90), 2),
        "cum_max": round(max(cums), 2) if cums else None,
        "p_med": round(median(ps), 4) if ps else None,
        "p_mean": round(mean(ps), 4) if ps else None,
        "p_p90": round(_q(ps, 0.90), 4),
        "frac_p_lt_0.05": round(mean(p < 0.05 for p in ps), 4),
        "frac_p_lt_0.10": round(mean(p < 0.10 for p in ps), 4),
        "frac_p_lt_0.20": round(mean(p < 0.20 for p in ps), 4),
        "frac_p_gt_0.50": round(mean(p > 0.50 for p in ps), 4),
        "realized_present": round(mean(prs), 4) if prs else None,
    }
    return out


def _mint_cell_frac(cell: list[dict], pred) -> float:
    return round(mean(bool(pred(r)) for r in cell), 4)


def _mint_cell_entry(cell: list[dict]) -> dict:
    return {
        "n": len(cell),
        "frac_any_object": _mint_cell_frac(
            cell,
            lambda r: (r.get("mint") or {}).get("objects_total", 0) >= 1,
        ),
        "frac_lot": _mint_cell_frac(
            cell,
            lambda r: (r["mint"].get("by_kind") or {}).get(
                "provisioned_lot", 0) >= 1,
        ),
        "frac_handler": _mint_cell_frac(
            cell,
            lambda r: (r["mint"].get("by_kind") or {}).get(
                "ill_handler", 0) >= 1,
        ),
        "frac_diner": _mint_cell_frac(
            cell,
            lambda r: (r["mint"].get("by_kind") or {}).get(
                "ill_diner", 0) >= 1,
        ),
        "frac_events": _mint_cell_frac(
            cell,
            lambda r: sum(
                (r.get("mint") or {}).get("events_by_kind", {}).values()
            ) >= 1,
        ),
        "frac_takers": _mint_cell_frac(
            cell,
            lambda r: ((r.get("mint") or {}).get("telemetry") or {}).get(
                "takers_served", 0) >= 1,
        ),
        "frac_dose": _mint_cell_frac(
            cell,
            lambda r: ((r.get("mint") or {}).get("telemetry") or {}).get(
                "dose_credited", 0.0) > 0,
        ),
        "mean_objects": round(mean(
            (r.get("mint") or {}).get("objects_total", 0) for r in cell
        ), 2),
        "mean_imports": round(mean(
            r.get("n_imports") or 0 for r in cell
        ), 2),
        "frac_acq": _mint_cell_frac(
            cell, lambda r: len(r.get("acq") or []) >= 1,
        ),
    }


def mint_census(rows: list[dict]) -> dict:
    unposted = [r for r in rows if r.get("posted") is False]
    out: dict = {}
    for hull in ("exp", "cls", "spr"):
        for arm in (
            "off", "ind", "ship", "a_ext", "a_thin",
            "bc40", "bc80", "bi50", "bmix",
        ):
            cell = [
                r for r in unposted
                if r["hull"] == hull and r["arm"] == arm
            ]
            if not cell:
                continue
            out[f"{hull}/{arm}"] = _mint_cell_entry(cell)
    return out


def _flatten_acquisitions(rows: list[dict]) -> list[dict]:
    acqs = []
    for r in rows:
        for a in r.get("acq") or []:
            a["key"] = r["key"]
            a["hull"] = r["hull"]
            a["arm"] = r["arm"]
            a["posted"] = r.get("posted")
            acqs.append(a)
    return acqs


def _print_dose_by_hull_posted(acqs: list[dict], title: str,
                               arm_filter: str | None = None) -> None:
    print(title)
    for hull in ("exp", "cls", "spr"):
        for posted in (True, False):
            cell = [
                a for a in acqs
                if a["hull"] == hull and a["posted"] == posted
                and (arm_filter is None or a["arm"] == arm_filter)
            ]
            if not cell:
                continue
            label = hull
            if arm_filter:
                label = f"{hull} {arm_filter}"
            print(label,
                  "posted" if posted else "unposted",
                  json.dumps(dose_position(cell)))


def _print_dose_landmarks() -> None:
    print("\n=== dose-position landmarks ===")
    for p in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.71):
        print(f"  Hill dose for p={p}: {_dose_for_p(p):,.1f}")


def _print_posted_mint_ref(rows: list[dict]) -> None:
    print("\n=== posted-cell mint reference ===")
    for hull in ("exp", "cls", "spr"):
        cell = [r for r in rows
                if r["hull"] == hull and r.get("posted")]
        if cell:
            fr = mean(
                (r.get("mint") or {}).get("objects_total", 0) >= 1 for r in cell
            )
            print(hull, "posted n:", len(cell),
                  "frac any object:", round(fr, 4))


def _voyage_present_shares(cell: list[dict]) -> tuple[list[float], list[float]]:
    shares, means = [], []
    for r in cell:
        acq = r.get("acq") or []
        if not acq:
            continue
        aids = {a["a"] for a in acq}
        pres = {a["a"] for a in acq if a["pr"]}
        shares.append(len(pres) / len(aids))
        means.append(mean(a["p"] for a in acq))
    return shares, means


def _print_host_present_share(rows: list[dict]) -> None:
    print("\n=== per-voyage host-level present share (Hill cohort) ===")
    for hull in ("exp", "cls", "spr"):
        for posted in (True, False):
            cell = [
                r for r in rows
                if r["hull"] == hull and r.get("posted") == posted
            ]
            shares, means = _voyage_present_shares(cell)
            if shares:
                print(
                    hull, "posted" if posted else "unposted",
                    "n_voy:", len(shares),
                    "med_share:", round(median(shares), 4),
                    "pooled_share:", round(mean(shares), 4),
                    "med_E_p:", round(median(means), 4),
                )


def _funnel_ep_ratios(rows: list[dict]) -> list[tuple]:
    diffs = []
    for r in rows:
        acq = r.get("acq") or []
        inf = r.get("cumulative_ever_infected_passenger") or 0
        ill = r.get("cumulative_ever_ill_passenger") or 0
        if not acq or not inf:
            continue
        ratio = ill / inf
        ep = mean(a["p"] for a in acq)
        diffs.append((ep, ratio, r["hull"], r.get("posted")))
    return diffs


def _print_funnel_vs_hill(rows: list[dict]) -> None:
    print("\n=== funnel ratio vs Hill E[p] per voyage (all cells) ===")
    diffs = _funnel_ep_ratios(rows)
    for hull in ("exp", "cls", "spr"):
        d = [x for x in diffs if x[2] == hull]
        if d:
            print(
                hull, "n:", len(d),
                "med_E[p]:", round(median(x[0] for x in d), 4),
                "med_ill/inf:", round(median(x[1] for x in d), 4),
            )


def _print_pathway_mix(acqs: list[dict]) -> None:
    print("\n=== pathway mix of acquisitions ===")
    pc = Counter(a.get("w") for a in acqs)
    for k, v in pc.most_common():
        print(f"  {k}: {v} ({v / len(acqs):.3f})")


def _print_dose_bands(acqs: list[dict]) -> None:
    print("\n=== presentation vs dose band (all hulls pooled) ===")
    bands = [(0, 4), (4, 7), (7, 22), (22, 2900), (2900, 1e15)]
    for lo, hi in bands:
        cell = [a for a in acqs if lo <= a["cum"] < hi]
        if cell:
            print(f"  cum in [{lo},{hi}): n={len(cell)}",
                  f"E[p]={round(mean(a['p'] for a in cell), 4)}",
                  f"realized={round(mean(bool(a['pr']) for a in cell), 4)}")


def main() -> None:
    rows = [
        json.loads(ln) for ln in open(ROWS, encoding="utf-8")
    ]
    rows = [r for r in rows if not r.get("error")]
    print(f"rows: {len(rows)}")
    acqs = _flatten_acquisitions(rows)
    print(f"acquisition rows: {len(acqs)}")

    _print_dose_by_hull_posted(
        acqs, "\n=== dose-position: per hull x posted ===",
    )
    _print_dose_landmarks()
    print("\n=== mint census: unposted per hull x arm ===")
    for k, v in mint_census(rows).items():
        print(k, json.dumps(v))
    _print_posted_mint_ref(rows)
    _print_dose_by_hull_posted(
        acqs, "\n=== ind cross-check: dose-position ===", arm_filter="ind",
    )
    _print_host_present_share(rows)
    _print_funnel_vs_hill(rows)
    _print_pathway_mix(acqs)
    _print_dose_bands(acqs)


if __name__ == "__main__":
    main()
