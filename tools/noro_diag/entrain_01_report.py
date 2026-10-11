#!/usr/bin/env python3
"""NORO-ENTRAIN-01 readout report — aggregates entrain_01_scan JSONL.

Reads the summary-side rows (all 27,000 cells), the full-census rows
(posted voyages at 100% + per-block stride samples of unposted) and the
exp head-census rows (burst baseline) emitted by ``entrain_01_scan.py``
and prints the markdown tables for the readout document:

- per-hull posting rate vs the declared 0.4-0.9% VSP band (Wilson CIs);
- posted-conditional passenger reported AR vs the 0.04-0.10 band;
- excursion -> posting conversion by arm: P(>=1 early event) on the
  unposted census sample, posted added back explicitly (SCORE-01
  convention — the censused subpopulation over-represents posted
  voyages, so rates come off the unposted sample);
- the route decomposition (source_kind mix of early events on posted
  and on all censused voyages, plus the voyage-max early event's
  source_kind on posted voyages);
- burst48 on exp: posted/excursion-vs-rest separation per arm;
- per-window serving shape on a_ext/a_thin vs ship;
- arriving-shedder echo for bc*/bmix: boarding draws, import rolls,
  early object source attribution (arriving import vs onboard-acquired);
- must-not-move: off zero-witness, object-integrity counters,
  windows_covered vs minted life, composition sums, immune echo.

An early event is a contamination object with ``seeded_epoch <= 48``
(object arms) or a pan-window serving event with ``start_epoch <= 48``
(the v1 ``ind`` arm) — the SCORE-01 convention verbatim.

All inputs are local JSONL row files — no AWS access required.
"""

from __future__ import annotations

import argparse
import statistics as stats
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from early_event_report import _load_rows  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.diag.readout_common import wilson_interval  # noqa: E402

_ARMS = ("off", "ind", "ship", "ext", "thin",
         "bc40", "bc80", "bi50", "bmix")
_HULLS = ("exp", "cls", "spr")
_KINDS = ("provisioned_lot", "ill_handler", "ill_diner")
_KIND_SHORT = {"provisioned_lot": "lot", "ill_handler": "handler",
               "ill_diner": "diner"}
_ARM_LABEL = {"ext": "a_ext", "thin": "a_thin"}

# Declared anchors (design §6).
_POSTING_BAND = (0.004, 0.009)
_AR_BAND = (0.04, 0.10)


def _pct(num: int | float, den: int | float) -> str:
    return f"{100.0 * num / den:.1f}%" if den else "-"


def _med(xs: list[float], nd: int = 3) -> str:
    return f"{stats.median(xs):.{nd}f}" if xs else "-"


def _q(xs: list[float], p: float) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def _cell_of(row: dict) -> tuple[str, str]:
    tier = row["key"].rsplit("/", 2)[-2]
    parts = tier.split("_")
    hull = parts[1] if len(parts) >= 2 else tier
    arm = parts[-1] if len(parts) >= 2 else tier
    return hull, arm


def _cen(row: dict) -> dict:
    c = row.get("census")
    if not isinstance(c, dict) or c.get("error"):
        return {}
    return c


def _early_events(row: dict) -> list[dict]:
    return _cen(row).get("early") or []


def _has_early(row: dict) -> bool:
    return bool(_early_events(row))


def _obj_rows(row: dict) -> list[dict]:
    return _cen(row).get("obj_rows") or []


def _posting_table(cells: dict[tuple[str, str], list[dict]]) -> list[str]:
    lines = [
        "| cell | n | posted n | posting rate [95% CI] | vs 0.4-0.9% |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            n = len(rows)
            if not n:
                continue
            k = sum(1 for r in rows if r["posted"])
            lo, hi = wilson_interval(k, n)
            rate = k / n
            band = (
                "in" if _POSTING_BAND[0] <= rate <= _POSTING_BAND[1]
                else ("below" if rate < _POSTING_BAND[0] else "above")
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {n} | {k} |"
                f" {100 * rate:.2f}% [{100 * lo:.2f},{100 * hi:.2f}]"
                f" | {band} |"
            )
    return lines


def _posted_ar_table(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    lines = [
        "| cell | posted n | med rep pax AR [p10,p90] | med reach"
        " | vs 0.04-0.10 |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            posted = [
                r for r in cells.get((hull, arm), []) if r["posted"]
            ]
            if not posted:
                lines.append(f"| {hull} {_ARM_LABEL.get(arm, arm)} | 0 | - | - | - |")
                continue
            ars = [r["rep_pax_ar"] for r in posted]
            med = stats.median(ars)
            p10 = _q(ars, 0.10)
            p90 = _q(ars, 0.90)
            reach = stats.median(r["reach"] for r in posted)
            verdict = (
                "in" if _AR_BAND[0] <= med <= _AR_BAND[1]
                else ("below" if med < _AR_BAND[0] else "above")
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {len(posted)} |"
                f" {med:.4f} [{p10:.4f},{p90:.4f}] | {reach:.2f}"
                f" | {verdict} |"
            )
    return lines


def _conversion_table(
    cells: dict[tuple[str, str], list[dict]],
    summ_cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """Excursion->posting conversion.  P(early) estimated on the
    unposted census sample; posted voyages added back explicitly."""
    lines = [
        "| cell | unposted censused | >=1 early | P(early) [CI]"
        " | posted n | posted w/ early | P(post|early)"
        " | P(post|no early) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            cen = [r for r in rows if _cen(r)]
            unp_cen = [r for r in cen if not r["posted"]]
            unp_early = sum(1 for r in unp_cen if _has_early(r))
            n_unp = len(unp_cen)
            lo, hi = wilson_interval(unp_early, n_unp)
            p_early = unp_early / n_unp if n_unp else None
            posted = [r for r in rows if r["posted"]]
            post_early = sum(1 for r in posted if _has_early(r))
            n_posted_all = sum(
                1 for r in summ_cells.get((hull, arm), []) if r["posted"]
            )
            n_all = len(summ_cells.get((hull, arm), []))
            n_unposted_all = n_all - n_posted_all
            post_noearly = n_posted_all - post_early
            if p_early is None:
                conv = conv_no = "-"
            else:
                est_early = p_early * n_unposted_all
                est_noearly = (1 - p_early) * n_unposted_all
                conv = _pct(post_early, post_early + est_early)
                conv_no = _pct(post_noearly, post_noearly + est_noearly)
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {n_unp}"
                f" | {unp_early}"
                f" | {_pct(unp_early, n_unp)}"
                f" [{100 * lo:.0f},{100 * hi:.0f}]"
                f" | {n_posted_all} | {post_early} | {conv}"
                f" | {conv_no} |"
            )
    return lines


def _route_tables(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """Early-event source_kind: posted-voyage mix, all-censused mix,
    voyage-max driver on posted voyages — per hull, rows per arm."""
    lines = []
    for hull in _HULLS:
        lines += [
            f"#### {hull}",
            "",
            "| arm | early events on posted (lot/hdl/dnr)"
            " | early events, all censused (lot/hdl/dnr)"
            " | voyage-max driver on posted (lot/hdl/dnr/none) |",
            "|---|---|---|---|",
        ]
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            cen = [r for r in rows if _cen(r)]
            mix_post: Counter[str] = Counter()
            mix_all: Counter[str] = Counter()
            driver: Counter[str] = Counter()
            for r in cen:
                evs = _early_events(r)
                for e in evs:
                    mix_all[e.get("k") or "?"] += 1
                if r["posted"]:
                    for e in evs:
                        mix_post[e.get("k") or "?"] += 1
                    if evs:
                        top = max(evs, key=lambda e: int(e.get("t") or 0))
                        driver[top.get("k") or "?"] += 1
                    else:
                        driver["(none)"] += 1
            lines.append(
                f"| {_ARM_LABEL.get(arm, arm)}"
                f" | {'/'.join(str(mix_post.get(k, 0)) for k in _KINDS)}"
                f" | {'/'.join(str(mix_all.get(k, 0)) for k in _KINDS)}"
                f" | {'/'.join(str(driver.get(k, 0)) for k in _KINDS)}"
                f"/{driver.get('(none)', 0)} |"
            )
        lines.append("")
    return lines


def _size_join(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    lines = [
        "| cell | posted n | max-early med [p90] posted"
        " | unposted n | max-early med [p90] unposted"
        " | smallest posted max-early |",
        "|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            cen = [
                r for r in cells.get((hull, arm), []) if _cen(r)
            ]
            def vmax(r: dict) -> int:
                return max(
                    (int(e.get("t") or 0) for e in _early_events(r)),
                    default=0,
                )
            post = [vmax(r) for r in cen if r["posted"]]
            unp = [vmax(r) for r in cen if not r["posted"]]
            mp = (
                f"{stats.median(post):g} [{_q(post, 0.9):g}]"
                if post else "-"
            )
            mu = (
                f"{stats.median(unp):g} [{_q(unp, 0.9):g}]"
                if unp else "-"
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {len(post)}"
                f" | {mp} | {len(unp)} | {mu}"
                f" | {min(post) if post else '-'} |"
            )
    return lines


def _burst_table(
    cells: dict[tuple[str, str], list[dict]],
    head_rows: list[dict],
) -> list[str]:
    """burst48 = max share of acquisition epochs in a 48-epoch window.
    Posted + cs-excursion cells vs the unposted rest, per arm."""
    lines = [
        "| arm | set | n | burst48 med | burst12 med | centre med |",
        "|---|---|---|---|---|---|",
    ]
    for arm in _ARMS:
        cen = [
            r for r in cells.get(("exp", arm), []) if _cen(r)
        ]
        posted = [r for r in cen if r["posted"]]
        exc = [
            r for r in cen
            if (_cen(r).get("cs_acq_n") or 0) > 0
        ]
        for label, group in (("posted", posted), ("cs-excursion", exc)):
            if not group:
                continue
            b48 = [_cen(r).get("burst48") or 0.0 for r in group]
            b12 = [_cen(r).get("burst12") or 0.0 for r in group]
            cen_e = [
                _cen(r).get("burst48_centre") or 0.0
                for r in group if _cen(r).get("burst48_centre")
            ]
            lines.append(
                f"| {_ARM_LABEL.get(arm, arm)} | {label} | {len(group)}"
                f" | {_med(b48)} | {_med(b12)} | {_med(cen_e, 0)} |"
            )
    rest = [r for r in head_rows if _cen(r)]
    if rest:
        b48 = [_cen(r).get("burst48") or 0.0 for r in rest]
        b12 = [_cen(r).get("burst12") or 0.0 for r in rest]
        lines.append(
            f"| (all) | unposted rest (head) | {len(rest)}"
            f" | {_med(b48)} | {_med(b12)} | - |"
        )
    return lines


def _serving_table(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """Per-window serving shape on the object arms: windows_covered,
    servings_served, per-window takers, lot budget, close reasons."""
    lines = [
        "| cell | voyages w/ objs | objects | windows med [p90]"
        " | srvs_served med [p90] | pw med [p90]"
        " | lot_srv med | top close reasons |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            if arm in ("off", "ind"):
                continue
            rows = cells.get((hull, arm), [])
            objs: list[dict] = []
            voy = 0
            reasons: Counter[str] = Counter()
            for r in rows:
                ors = _obj_rows(r)
                if ors:
                    voy += 1
                objs.extend(ors)
                for o in ors:
                    reasons[o.get("end") or "?"] += 1
            if not objs:
                continue
            wins = [int(o.get("w") or 0) for o in objs]
            srvs = [int(o.get("t") or 0) for o in objs]
            pw = [
                int(x) for o in objs for x in (o.get("pw") or [])
            ]
            lots = [
                int(o["lot_srv"]) for o in objs
                if o.get("lot_srv") is not None
            ]
            top = ", ".join(
                f"{k}:{v}" for k, v in reasons.most_common(3)
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {voy}"
                f" | {len(objs)}"
                f" | {_med(wins, 0)} [{_q(wins, 0.9)}]"
                f" | {_med(srvs, 0)} [{_q(srvs, 0.9)}]"
                f" | {_med(pw, 0)} [{_q(pw, 0.9)}]"
                f" | {_med(lots, 0)} | {top} |"
            )
    return lines


def _shedder_table(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """Arriving-shedder echo: boarding draws (all 27k summaries),
    import rolls and early-object source attribution (census)."""
    lines = [
        "| cell | drawn crew med [p10,p90] | imports med"
        " | censused voy | early objs src import/acq"
        " | all objs src import/acq/none |",
        "|---|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            if not rows:
                continue
            dc = [r["drawn_crew"] or 0 for r in rows]
            imp = [r["n_imports"] or 0 for r in rows]
            cen = [r for r in rows if _cen(r)]
            e_imp = e_acq = o_imp = o_acq = o_none = 0
            for r in cen:
                c = _cen(r)
                e_imp += int(c.get("early_obj_src_import") or 0)
                e_acq += sum(
                    1 for e in _early_events(r)
                    if e.get("f") == "obj" and e.get("src") == "acq"
                )
                o_imp += int(c.get("obj_src_import") or 0)
                o_acq += int(c.get("obj_src_acq") or 0)
                o_none += int(c.get("obj_src_none") or 0)
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)}"
                f" | {_med(dc, 0)} [{_q(dc, 0.1):g},{_q(dc, 0.9):g}]"
                f" | {_med(imp, 0)} | {len(cen)}"
                f" | {e_imp}/{e_acq}"
                f" | {o_imp}/{o_acq}/{o_none} |"
            )
    return lines


def _integrity_table(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    lines = [
        "| cell | censused | objects | ev rows | missing oid/serial"
        " | unresolved oid | open | srvs>lot | non-noro | pw>80* |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            cen = [r for r in rows if _cen(r)]
            if not cen:
                continue
            agg: Counter[str] = Counter()
            pw_over = 0
            multi_pan = 0
            for r in cen:
                c = _cen(r)
                integ = c.get("integrity") or {}
                for k, v in integ.items():
                    agg[k] += int(v or 0)
                tel = c.get("telemetry") or {}
                multi_pan += int(tel.get("multi_pan_windows") or 0)
                for o in _obj_rows(r):
                    if int(o.get("pw_max") or 0) > 80:
                        pw_over += 1
            n_obj = sum(int(_cen(r).get("n_objects") or 0) for r in cen)
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {len(cen)}"
                f" | {n_obj} | {agg['ev_rows']}"
                f" | {agg['ev_missing_oid']}/{agg['ev_missing_serial']}"
                f" | {agg['ev_unresolved_oid']} | {agg['obj_open']}"
                f" | {agg['lot_srv_exceeds']} | {agg['non_noro_objects']}"
                f" | {pw_over} |"
            )
    lines.append(
        "\n\\* pw>80 counts objects whose busiest window served >80 "
        "takers; a window may emit multiple pans (multi_pan_windows "
        "telemetry), so it is an upper-bound flag, not a pan-size "
        "violation."
    )
    return lines


def _witness_table(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """off zero-witness + telemetry echoes per cell."""
    lines = [
        "| cell | censused | voy w/ any cs | objects | events"
        " | takers | pans |",
        "|---|---|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in _ARMS:
            rows = cells.get((hull, arm), [])
            cen = [r for r in rows if _cen(r)]
            if not cen:
                continue
            saw = sum(1 for r in cen if _cen(r).get("saw_cs"))
            n_obj = sum(int(_cen(r).get("n_objects") or 0) for r in cen)
            n_ev = sum(int(_cen(r).get("n_events") or 0) for r in cen)
            tak = sum(
                int((_cen(r).get("telemetry") or {})
                    .get("takers_served") or 0)
                for r in cen
            )
            pans = sum(
                int((_cen(r).get("telemetry") or {})
                    .get("pans_emitted") or 0)
                for r in cen
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {len(cen)}"
                f" | {saw} | {n_obj} | {n_ev} | {tak} | {pans} |"
            )
    return lines


def _windows_check(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """windows_covered vs minted-life cap: ship objects must sit <= the
    shipped shelf-life envelope; a_ext may run longer (its arm)."""
    lines = [
        "| cell | objects | windows max | objects w>8 | w>16 |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in ("ship", "ext", "thin"):
            rows = cells.get((hull, arm), [])
            objs = [
                o for r in rows for o in _obj_rows(r)
            ]
            if not objs:
                continue
            wins = [int(o.get("w") or 0) for o in objs]
            over8 = sum(1 for w in wins if w > 8)
            over16 = sum(1 for w in wins if w > 16)
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)} | {len(objs)}"
                f" | {max(wins)} | {over8} | {over16} |"
            )
    return lines


def _immune_echo(
    cells: dict[tuple[str, str], list[dict]],
) -> list[str]:
    """Embarkation-immunity echo vs declared pools, plus the
    zero-import check on censused immune cells."""
    lines = [
        "| cell | immune_init med | expected* | imports med"
        " | crew comp |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULLS:
        for arm in ("ship", "bi50", "bmix"):
            rows = cells.get((hull, arm), [])
            if not rows:
                continue
            im = [r["immune_init"] or 0 for r in rows]
            imp = [r["n_imports"] or 0 for r in rows]
            crew = rows[0]["crew_comp"]
            pax = rows[0]["pax_comp"]
            exp_n = (
                0.2 * (pax + crew) if arm == "ship"
                else 0.5 * crew + 0.2 * pax
            )
            lines.append(
                f"| {hull} {_ARM_LABEL.get(arm, arm)}"
                f" | {_med(im, 0)} | ~{exp_n:.0f} | {_med(imp, 0)}"
                f" | {crew} |"
            )
    lines.append(
        "\n\\* ship = role-blind 0.2 pool over the whole complement;"
        " bi50/bmix = crew 0.5 + passenger 0.2 per-role pools."
    )
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summaries", required=True)
    ap.add_argument("--census", action="append", default=[])
    ap.add_argument("--head", action="append", default=[])
    args = ap.parse_args()
    summ = _load_rows([args.summaries])
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in summ.values():
        cells[_cell_of(r)].append(r)

    cen_rows = _load_rows(args.census) if args.census else {}
    cen_cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for k, r in cen_rows.items():
        base = summ.get(k, {})
        merged = {**r, **{kk: vv for kk, vv in base.items()
                          if vv is not None}}
        cen_cells[_cell_of(r)].append(merged)

    head_rows = []
    for r in (_load_rows(args.head) if args.head else {}).values():
        if _cen(r):
            head_rows.append(r)

    print("## posting vs band\n")
    print("\n".join(_posting_table(cells)))
    print("\n## posted-conditional pax AR\n")
    print("\n".join(_posted_ar_table(cells)))
    print("\n## conversion\n")
    print("\n".join(_conversion_table(cen_cells, cells)))
    print("\n## size join\n")
    print("\n".join(_size_join(cen_cells)))
    print("\n## routes\n")
    print("\n".join(_route_tables(cen_cells)))
    print("\n## burst48 — exp\n")
    print("\n".join(_burst_table(cen_cells, head_rows)))
    print("\n## serving shape\n")
    print("\n".join(_serving_table(cen_cells)))
    print("\n## arriving-shedder echo\n")
    print("\n".join(_shedder_table(cen_cells)))
    print("\n## integrity\n")
    print("\n".join(_integrity_table(cen_cells)))
    print("\n## witness\n")
    print("\n".join(_witness_table(cen_cells)))
    print("\n## windows check\n")
    print("\n".join(_windows_check(cen_cells)))
    print("\n## immune echo\n")
    print("\n".join(_immune_echo(cells)))


if __name__ == "__main__":
    main()
