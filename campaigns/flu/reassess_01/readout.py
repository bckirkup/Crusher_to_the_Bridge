#!/usr/bin/env python3
"""FLU-REASSESS-01 readout: aggregate the post-enhancement
``cell_<seed>.json`` payloads and contrast the new-engine surfaces
against the committed FLU-OPEN-01 / FLU-VIS-01 baselines.

Reads ``--root`` laid out as ``flu_<tier>_12d_<arm>/cell_<seed>.json``
(arms ``r100_dec`` = census, ``r200_dec`` = the sign-reversal arm).
The paired r200-vs-r100 contrast is computed within this campaign —
both arms ran on the same engine — so it isolates the reporting
feedback under the shipped enhancement generation.

Baseline numbers are constants transcribed from the committed readouts
(docs/flu/flu_open_voyage_01_readout.md measured at ``7f4702ef`` and
docs/flu/flu_visibility_01_readout.md measured at ``ca775a0b``); this
file measures the new cells against them — it never selects an arm and
never tunes a constant. The frozen predictions live in ``DESIGN.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.diag.readout_common import quantiles, wilson_interval  # noqa: E402

_WARD_PRESENTING = 0.007
_WARD_PRESENTING_BAND = (0.004, 0.010)
_F5_FRAME = (0.03, 0.15)
_BLOCK_RE = re.compile(r"^flu_(?P<tier>\w+?)_12d_r(?P<scale>\d+)_(?P<corner>dec|str)$")
_ARM_ORDER = {"r100_dec": 0, "r200_dec": 1}
_SCHEMA = "flu_reassess_01.v1"

# Committed baselines (OPEN-01 @7f4702ef, VIS-01 @ca775a0b) — the
# pre-enhancement engine. Keys: tier = exp/spr/cls/mega.
_BASE = {
    "exp": {
        "infected": 755, "index_or_import": 473, "onboard": 282,
        "attack": 0.0168,
        "rep_inf": 0.531, "acq_rep_inf": 0.681, "ill_inf": 0.597,
        "outbreak": 0.67, "confined_cells": 95, "alert": 0.67,
        "caregiver_dominant": 137, "droplet_dominant": 142,
        "presenting_r100": 0.0089, "presenting_r200": 0.0107,
        "r200_d_onboard_mean": 1.62, "r200_d_infected_mean": 1.56,
        "r200_d_reported_mean": 0.82, "r200_d_quarantined_mean": 1.44,
    },
    "cls": {
        "infected": 1686, "index_or_import": 1324, "onboard": 362,
        "attack": 0.0088,
        "rep_inf": 0.279, "acq_rep_inf": 0.395, "ill_inf": 0.366,
        "outbreak": 0.80, "confined_cells": 100, "alert": 0.97,
        "caregiver_dominant": 188, "droplet_dominant": 167,
        "presenting_r100": 0.0025, "presenting_r200": 0.0025,
        "r200_d_onboard_mean": -0.26, "r200_d_infected_mean": -0.25,
        "r200_d_reported_mean": 0.00, "r200_d_quarantined_mean": 0.14,
    },
    "spr": {
        "infected": 2448, "index_or_import": 1941, "onboard": 507,
        "attack": 0.0082,
        "rep_inf": 0.255, "acq_rep_inf": 0.377, "ill_inf": 0.347,
        "outbreak": 0.88, "confined_cells": 100, "alert": 0.96,
        "caregiver_dominant": 278, "droplet_dominant": 229,
        "presenting_r100": 0.0021, "presenting_r200": 0.0022,
        "r200_d_onboard_mean": 0.17, "r200_d_infected_mean": 0.17,
        "r200_d_reported_mean": 0.42, "r200_d_quarantined_mean": -0.33,
    },
    "mega": {
        "infected": 5067, "index_or_import": 4204, "onboard": 863,
        "attack": 0.0072,
        "rep_inf": 0.203, "acq_rep_inf": 0.293, "ill_inf": 0.290,
        "outbreak": 0.97, "confined_cells": 100, "alert": 0.99,
        "caregiver_dominant": 444, "droplet_dominant": 419,
        "presenting_r100": 0.0015, "presenting_r200": 0.0016,
        "r200_d_onboard_mean": 0.68, "r200_d_infected_mean": 0.56,
        "r200_d_reported_mean": 1.12, "r200_d_quarantined_mean": 2.38,
    },
}

_TIER_LABELS = {
    "exp": "expedition_cruise_450",
    "cls": "classic_cruise_1900",
    "spr": "spirit_cruise_3000",
    "mega": "mega_cruise_5000",
}


def _wilson(k: int, n: int) -> dict[str, float]:
    lo, hi = wilson_interval(k, n)
    return {"lo": lo, "hi": hi}


def _arm_tier(block: str) -> tuple[str, str] | None:
    m = _BLOCK_RE.match(block)
    if not m:
        return None
    return m["tier"], f"r{m['scale']}_{m['corner']}"


def _iter_cells(root: Path) -> dict[str, list[dict[str, Any]]]:
    blocks: dict[str, list[dict[str, Any]]] = {}
    for block_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for cell_file in sorted(block_dir.glob("cell_*.json")):
            cell = json.loads(cell_file.read_text())
            cell["_block"] = block_dir.name
            blocks.setdefault(block_dir.name, []).append(cell)
    return blocks


def _first_status_epoch(cell: dict[str, Any], status: str) -> int | None:
    for e in cell.get("escalation_log") or []:
        if str(e.get("to")) == status and not e.get("pending"):
            return int(e["epoch"])
    return None


def _sum_rows(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-cell infection rows into arm×class counters, plus the
    enhancement-witness tallies this campaign added."""
    out: dict[str, Any] = {
        "cells": len(cells),
        "infected": 0,
        "ill": 0,
        "reported": 0,
        "index": 0,
        "onboard": 0,
        "acq_reported": 0,
        "acq_ill": 0,
        "acq_infected": 0,
        "outbreak_cells": 0,
        "index_invariant_fails": 0,
        "confined_cells": 0,
        "quarantined": 0,
        "isolated": 0,
        "alert_cells": 0,
        "alert_epochs": [],
        "presenting_attack": [],
        "cell_infected": [],
        "cell_onboard": [],
        "cell_reported": [],
        "trigger": {},
        "routes": {},
        "caregiver_dom": 0,
        "mild_onsets": 0,
        "complement": 0,
        "per_seed": {},
        "enforced_events": 0,
        "enforced_cells": 0,
        "enforced_epochs": [],
        "refusal_events": 0,
        "refusal_cells": 0,
        "service_deliveries": 0,
        "service_dose_credited": 0.0,
        "service_dose_to_host_credited": 0.0,
        "service_reports": 0,
        "audit_fails": [],
    }
    for cell in cells:
        c = cell["counts"]
        out["cell_infected"].append(c["ever_infected"])
        out["cell_reported"].append(c["ever_reported"])
        complement = (cell.get("complement") or {}).get("total") or 0
        out["complement"] += complement
        out["presenting_attack"].append(
            c["ever_reported"] / complement if complement else 0.0,
        )
        out["outbreak_cells"] += int(c["onboard_acquired"] > 0)
        out["index_invariant_fails"] += int(c["index_cases"] < 2)
        confined = c["quarantined_end"] + c["isolated_end"]
        out["confined_cells"] += int(confined > 0)
        out["quarantined"] += c["quarantined_end"]
        out["isolated"] += c["isolated_end"]
        out["cell_onboard"].append(c["onboard_acquired"])
        trig = str(cell.get("final_trigger_status"))
        out["trigger"][trig] = out["trigger"].get(trig, 0) + 1
        alert_epoch = _first_status_epoch(cell, "ALERT")
        if alert_epoch is not None or trig == "ALERT":
            out["alert_cells"] += 1
        if alert_epoch is not None:
            out["alert_epochs"].append(alert_epoch)
        out["mild_onsets"] += int(
            (cell.get("onset_severity_counts") or {}).get("mild", 0),
        )
        _sum_infections(cell["infections"], out)
        _sum_witnesses(cell, out)
        out["per_seed"][cell["seed"]] = {
            "infected": c["ever_infected"],
            "reported": c["ever_reported"],
            "onboard": c["onboard_acquired"],
            "quarantined": confined,
        }
        _audit_cell(cell, out)
    return out


def _sum_infections(rows: list[dict[str, Any]], out: dict[str, Any]) -> None:
    for r in rows:
        out["infected"] += 1
        out["ill"] += int(r["ill"])
        out["reported"] += int(r["reported"])
        out["index"] += int(r["index"])
        is_acq = not r["index"]
        out["onboard"] += int(is_acq)
        if is_acq:
            out["acq_infected"] += 1
            out["acq_ill"] += int(r["ill"])
            out["acq_reported"] += int(r["reported"])
        dom = r.get("dominant_route") or ("index_or_boarding" if r["index"] else "unknown")
        out["routes"][dom] = out["routes"].get(dom, 0) + 1
        if dom == "caregiver":
            out["caregiver_dom"] += 1


def _sum_witnesses(cell: dict[str, Any], out: dict[str, Any]) -> None:
    enforced = cell.get("enforced_events") or []
    refusals = cell.get("refusal_events") or []
    out["enforced_events"] += len(enforced)
    out["enforced_cells"] += int(bool(enforced))
    out["enforced_epochs"].extend(
        int(e["epoch"]) for e in enforced if e.get("epoch") is not None
    )
    out["refusal_events"] += len(refusals)
    out["refusal_cells"] += int(bool(refusals))
    cg = cell.get("caregiver_telemetry") or {}
    out["service_deliveries"] += int(cg.get("service_deliveries") or 0)
    out["service_dose_credited"] += float(
        cg.get("service_dose_credited") or 0.0,
    )
    out["service_dose_to_host_credited"] += float(
        cg.get("service_dose_to_host_credited") or 0.0,
    )
    out["service_reports"] += int(cg.get("service_reports") or 0)


def _audit_cell(cell: dict[str, Any], out: dict[str, Any]) -> None:
    """Per-cell audit invariants — frozen in DESIGN.md. A violation is a
    defect, not a failed criterion."""
    seed = cell.get("seed")
    if cell.get("schema") != _SCHEMA:
        out["audit_fails"].append(f"{seed}: schema {cell.get('schema')!r}")
    echo = cell.get("mechanism_echo") or {}
    if echo.get("service_contact_factor") != ["uniform", 0.05, 0.3]:
        out["audit_fails"].append(
            f"{seed}: contact_factor {echo.get('service_contact_factor')!r}",
        )
    if echo.get("defiant_escalation_epochs") != 24:
        out["audit_fails"].append(
            f"{seed}: defiant_escalation_epochs "
            f"{echo.get('defiant_escalation_epochs')!r}",
        )
    if echo.get("service_direction") != "responder":
        out["audit_fails"].append(
            f"{seed}: service_direction {echo.get('service_direction')!r}",
        )
    if echo.get("service_responder_mode") != "uniform":
        out["audit_fails"].append(
            f"{seed}: responder_mode "
            f"{echo.get('service_responder_mode')!r}",
        )
    n_enforced = len(cell.get("enforced_events") or [])
    n_refused = len(cell.get("refusal_events") or [])
    if n_enforced > n_refused:
        out["audit_fails"].append(
            f"{seed}: enforced {n_enforced} > refusals {n_refused}",
        )
    cg = cell.get("caregiver_telemetry") or {}
    if float(cg.get("service_dose_to_host_credited") or 0.0) > 0.0:
        out["audit_fails"].append(
            f"{seed}: service_to_host credited "
            f"{cg.get('service_dose_to_host_credited')!r}",
        )


def _surfaces(tot: dict[str, Any]) -> dict[str, Any]:
    """The frozen-frame surfaces for one arm×class cell group."""
    n = tot["infected"]
    na = tot["acq_infected"]
    res: dict[str, Any] = {
        "cells": tot["cells"],
        "infected": n,
        "onboard": tot["onboard"],
        "complement": tot["complement"],
    }
    attack = tot["presenting_attack"]
    res["presenting_attack"] = {
        "mean": sum(attack) / max(1, len(attack)),
        "median": quantiles(attack).get("median"),
        "ward": _WARD_PRESENTING,
        "ward_band": list(_WARD_PRESENTING_BAND),
        "brackets_ward": bool(
            attack
            and _WARD_PRESENTING_BAND[0]
            <= sum(attack) / len(attack)
            <= _WARD_PRESENTING_BAND[1],
        ),
    }
    if n:
        res["reported_per_infected"] = {
            "p": tot["reported"] / n,
            "k": tot["reported"],
            "n": n,
            "wilson": _wilson(tot["reported"], n),
            "f5_frame": list(_F5_FRAME),
            "in_frame": _F5_FRAME[0] <= tot["reported"] / n <= _F5_FRAME[1],
        }
        res["ill_per_infected"] = {"p": tot["ill"] / n}
    if na:
        res["acq_reported_per_infected"] = {
            "p": tot["acq_reported"] / na,
            "k": tot["acq_reported"],
            "n": na,
            "wilson": _wilson(tot["acq_reported"], na),
        }
        res["acq_ill_per_infected"] = {"p": tot["acq_ill"] / na}
    res["outbreak_rate"] = tot["outbreak_cells"] / max(1, tot["cells"])
    res["alert_rate"] = tot["alert_cells"] / max(1, tot["cells"])
    res["alert_epoch"] = quantiles(tot["alert_epochs"])
    res["confinement"] = {
        "cells_with_confinement": tot["confined_cells"],
        "quarantined_end": tot["quarantined"],
        "isolated_end": tot["isolated"],
    }
    res["infected_dist"] = quantiles(tot["cell_infected"])
    res["onboard_dist"] = quantiles(tot["cell_onboard"])
    res["index_invariant_fails"] = tot["index_invariant_fails"]
    res["mild_onsets"] = tot["mild_onsets"]
    res["dominant_routes"] = tot["routes"]
    res["caregiver_dominant"] = tot["caregiver_dom"]
    res["caregiver_share_acq"] = (
        tot["caregiver_dom"] / na if na else None
    )
    res["witnesses"] = {
        "enforced_events": tot["enforced_events"],
        "enforced_cells": tot["enforced_cells"],
        "enforced_epoch": quantiles(tot["enforced_epochs"]),
        "refusal_events": tot["refusal_events"],
        "refusal_cells": tot["refusal_cells"],
        "service_deliveries": tot["service_deliveries"],
        "service_dose_credited": tot["service_dose_credited"],
        "service_dose_to_host_credited": tot["service_dose_to_host_credited"],
        "service_reports": tot["service_reports"],
    }
    res["audit_fails"] = tot["audit_fails"]
    return res


def _paired_deltas(
    arm_cells: list[dict[str, Any]],
    baseline_per_seed: dict[int, dict[str, int]],
) -> dict[str, Any]:
    """Per-seed feedback contrast vs the same-campaign r100 arm."""
    deltas: dict[str, list[int]] = {"infected": [], "onboard": [],
                                   "reported": [], "quarantined": []}
    paired = 0
    for cell in arm_cells:
        base = baseline_per_seed.get(cell["seed"])
        if base is None:
            continue
        paired += 1
        cur = (cell["counts"]["ever_infected"], cell["counts"]["onboard_acquired"],
               cell["counts"]["ever_reported"],
               cell["counts"]["quarantined_end"] + cell["counts"]["isolated_end"])
        deltas["infected"].append(cur[0] - base["infected"])
        deltas["onboard"].append(cur[1] - base["onboard"])
        deltas["reported"].append(cur[2] - base["reported"])
        deltas["quarantined"].append(cur[3] - base["quarantined"])
    out: dict[str, Any] = {"paired_seeds": paired}
    for key, vals in deltas.items():
        out[key] = {
            "mean": sum(vals) / len(vals) if vals else None,
            "median": quantiles(vals).get("median"),
            "share_positive": (
                sum(1 for v in vals if v > 0) / len(vals) if vals else None
            ),
        }
    return out


def _tier_rows(
    arms: dict[str, list[dict[str, Any]]],
    tier: str,
) -> dict[str, Any]:
    """One tier's arm surfaces + the same-campaign r200−r100 pairing."""
    arm_rows: dict[str, Any] = {}
    baseline_per_seed: dict[int, dict[str, int]] = {}
    for arm, cells in sorted(
        arms.items(), key=lambda kv: _ARM_ORDER.get(kv[0], 99),
    ):
        tot = _sum_rows(cells)
        if arm == "r100_dec":
            baseline_per_seed = tot["per_seed"]
        arm_rows[arm] = {"surfaces": _surfaces(tot)}
    for arm, cells in arms.items():
        if arm == "r100_dec":
            continue
        arm_rows[arm]["paired_vs_r100"] = _paired_deltas(
            cells, baseline_per_seed,
        )
    base = _BASE.get(tier) or {}
    arm_rows["_baseline"] = base
    arm_rows["_delta_vs_baseline"] = _delta_rows(arm_rows, base)
    return arm_rows


def build_readout(root: Path) -> dict[str, Any]:
    """Aggregate every arm×class block; the r200 arm pairs against the
    same-campaign r100 arm."""
    tiers: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for block, cells in _iter_cells(root).items():
        at = _arm_tier(block)
        if at is None:
            continue
        tier, arm = at
        tiers.setdefault(tier, {})[arm] = cells

    per_tier: dict[str, Any] = {}
    for tier, arms in sorted(tiers.items()):
        per_tier[tier] = _tier_rows(arms, tier)
    return {
        "schema": "flu_reassess_01.readout.v1",
        "root": str(root),
        "cells": sum(
            len(c) for arms in tiers.values() for c in arms.values()
        ),
        "baseline_commit": {"open01": "7f4702ef", "vis01": "ca775a0b"},
        "per_tier": per_tier,
    }


def _delta_rows(arm_rows: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """New-engine surfaces minus the committed pre-enhancement values."""
    out: dict[str, Any] = {}
    r100 = (arm_rows.get("r100_dec") or {}).get("surfaces") or {}
    r200 = (arm_rows.get("r200_dec") or {}).get("surfaces") or {}
    if r100 and base:
        out["r100"] = {
            "d_infected": r100["infected"] - base.get("infected", 0),
            "d_onboard": r100["onboard"] - base.get("onboard", 0),
            "d_presenting_mean": (
                r100["presenting_attack"]["mean"]
                - base.get("presenting_r100", 0.0)
            ),
            "d_rep_inf": (
                (r100.get("reported_per_infected") or {}).get("p", 0.0)
                - base.get("rep_inf", 0.0)
            ),
            "d_outbreak": r100["outbreak_rate"] - base.get("outbreak", 0.0),
            "d_alert": r100["alert_rate"] - base.get("alert", 0.0),
            "d_caregiver_dominant": (
                r100["caregiver_dominant"]
                - base.get("caregiver_dominant", 0)
            ),
        }
    if r200 and base:
        out["r200"] = {
            "d_presenting_mean": (
                r200["presenting_attack"]["mean"]
                - base.get("presenting_r200", 0.0)
            ),
        }
        paired = (arm_rows.get("r200_dec") or {}).get("paired_vs_r100") or {}
        out["r200_paired"] = {
            "new_d_onboard_mean": (paired.get("onboard") or {}).get("mean"),
            "old_d_onboard_mean": base.get("r200_d_onboard_mean"),
            "new_d_infected_mean": (paired.get("infected") or {}).get("mean"),
            "old_d_infected_mean": base.get("r200_d_infected_mean"),
            "new_d_quarantined_mean": (
                paired.get("quarantined") or {}
            ).get("mean"),
            "old_d_quarantined_mean": base.get("r200_d_quarantined_mean"),
        }
    return out


def _pct(p: float | None) -> str:
    return f"{p * 100:.1f}%" if p is not None else "n/a"


def _fmt_p(p: float | None) -> str:
    return f"{p * 100:.2f}%" if p is not None else "n/a"


def _signed(v: float | None, pct: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:+.2f}pp" if pct else f"{v:+.2f}"


def render_markdown(readout: dict[str, Any]) -> str:
    lines = ["# FLU-REASSESS-01 readout — post-enhancement engine", ""]
    lines.append(
        f"cells={readout['cells']}  tiers={len(readout['per_tier'])}  "
        f"baseline: OPEN-01@{readout['baseline_commit']['open01']}, "
        f"VIS-01@{readout['baseline_commit']['vis01']}",
    )
    for tier, arms in readout["per_tier"].items():
        _render_tier(lines, tier, arms)
    return "\n".join(lines) + "\n"


def _render_surface_row(lines: list[str], arm: str, s: dict[str, Any]) -> None:
    pa = s["presenting_attack"]
    rpi = s.get("reported_per_infected") or {}
    acq = s.get("acq_reported_per_infected") or {}
    lines.append(
        f"| {arm} | {s['cells']} | {s['infected']} | {s['onboard']} "
        f"| {_fmt_p(pa['mean'])} "
        f"{'≈Ward' if pa['brackets_ward'] else ''} "
        f"| {_pct(rpi.get('p'))} "
        f"{'in-frame' if rpi.get('in_frame') else ''} "
        f"| {_pct(acq.get('p'))} "
        f"| {_pct(s['outbreak_rate'])} "
        f"| {_pct(s['alert_rate'])} "
        f"| {s['confinement']['cells_with_confinement']} |",
    )


def _render_deltas(lines: list[str], d: dict[str, Any]) -> None:
    if d.get("r100"):
        r = d["r100"]
        lines.append("")
        lines.append(
            f"r100 vs OPEN-01: Δinfected {_signed(float(r['d_infected']))}, "
            f"Δonboard {_signed(float(r['d_onboard']))}, "
            f"Δpresenting {_signed(r['d_presenting_mean'], pct=True)}, "
            f"Δrep/inf {_signed(r['d_rep_inf'], pct=True)}, "
            f"Δoutbreak {_signed(r['d_outbreak'], pct=True)}, "
            f"Δcaregiver-dom {_signed(float(r['d_caregiver_dominant']))}",
        )
    if d.get("r200_paired"):
        p = d["r200_paired"]
        lines.append(
            f"r200−r100 paired: Δonboard mean "
            f"{_signed(p['new_d_onboard_mean'])} "
            f"(was {_signed(p['old_d_onboard_mean'])}), "
            f"Δinfected {_signed(p['new_d_infected_mean'])} "
            f"(was {_signed(p['old_d_infected_mean'])}), "
            f"Δquarantined {_signed(p['new_d_quarantined_mean'])} "
            f"(was {_signed(p['old_d_quarantined_mean'])})",
        )


def _render_witnesses(lines: list[str], arm: str, s: dict[str, Any]) -> None:
    w = s["witnesses"]
    lines.append("")
    lines.append(
        f"{arm} witnesses: enforced {w['enforced_events']} "
        f"on {w['enforced_cells']} cells "
        f"(epoch med {w['enforced_epoch'].get('median', '—')}), "
        f"refusals {w['refusal_events']} on {w['refusal_cells']} cells, "
        f"deliveries {w['service_deliveries']}, "
        f"svc_dose_credited {w['service_dose_credited']:.1f}, "
        f"to_host {w['service_dose_to_host_credited']:.1f}",
    )
    fails = s["audit_fails"]
    if fails:
        lines.append(f"AUDIT FAILS: {fails[:10]}")


def _render_tier(
    lines: list[str],
    tier: str,
    arms: dict[str, Any],
) -> None:
    label = _TIER_LABELS.get(tier, tier)
    real_arms = sorted(a for a in arms if not a.startswith("_"))
    lines.append("")
    lines.append(f"## {tier} ({label})")
    lines.append(
        "| arm | cells | infected | onboard | presenting attack | "
        "rep/inf pooled | rep/inf acq | outbreak | ALERT | confined |",
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for arm in real_arms:
        _render_surface_row(lines, arm, arms[arm]["surfaces"])
    _render_deltas(lines, arms.get("_delta_vs_baseline") or {})
    for arm in real_arms:
        _render_witnesses(lines, arm, arms[arm]["surfaces"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", required=True,
        help="dir laid out as flu_<tier>_12d_r<scale>_<corner>/cell_<seed>.json",
    )
    parser.add_argument(
        "--out", default=None, help="write JSON readout here (markdown -> stdout)",
    )
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
