#!/usr/bin/env python3
"""Aggregate the NORO-DOSE-REFIT-01 canary zips into the ledger tables.

For every ``<tier>/<run_id>.zip`` under ``--out`` this reads both members --
``summary.json`` (campaign layout) and ``refit.json`` (probe payload) -- and
emits, per cell and pooled:

* the ignition chain: importing hosts, ill imports, how many of those carried
  the vomiting axis (``vomiting_axis`` on the schedule draw), how many actually
  emitted an episode this voyage (``emitted_episodes`` > 0), and the voyage
  flag ``ignited`` = at least one import emitted;
* establishment conditioned on ignition: ``outbreak_occurred`` /
  ``attack_rate >= POSTING_THRESHOLD`` split by ignited vs cold voyages;
* the release composition: deposit callsite + venue-class GEC totals,
  sanitary-delivered GEC, emesis patch/aerosol GEC, over ill host-days
  (``ill_host_epochs / 24`` at the hours clock).

The ignition-conditioning is the whole point of the refit readout: a naive
seed-pair reads a coin flip (P(import vomits) ~4-8% per import), so
establishment is reported only on the ignited subset, with the cold subset
carried separately as a consistency check.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.diag.readout_common import wilson_centered  # noqa: E402

EPOCHS_PER_DAY = 24  # natural_history_clock "hours"


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    return wilson_centered(k, n, z)


def _rows(zip_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for zpath in sorted(zip_dir.glob("**/*.zip")):
        with zipfile.ZipFile(zpath) as zf:
            anchor = json.loads(zf.read("summary.json"))
            refit = json.loads(zf.read("refit.json"))
        derived = anchor.get("derived") or {}
        import_ids = set(refit.get("import_ids") or [])
        emesis = refit.get("emesis_by_host") or {}
        axis = [i for i in import_ids
                if emesis.get(str(i), {}).get("vomiting_axis")]
        emitted = [i for i in import_ids
                   if emesis.get(str(i), {}).get("emitted_episodes", 0) > 0]
        rel = refit.get("release_composition") or {}
        em = refit.get("emesis_mass_gec") or {}
        rows.append({
            "tier": zpath.parent.name,
            "run_id": anchor.get("run_id") or zpath.stem,
            "seed": (anchor.get("parameters") or {}).get("seed"),
            "platform": (anchor.get("parameters") or {}).get("platform_id"),
            "num_agents": refit.get("num_agents"),
            "imports": len(import_ids),
            "axis_imports": len(axis),
            "emitted_imports": len(emitted),
            "ignited": bool(emitted),
            "secondaries": (refit.get("transmission") or {}).get(
                "secondaries", 0,
            ),
            "attack_rate": derived.get("attack_rate"),
            "outbreak_occurred": bool(derived.get("outbreak_occurred")),
            "peak_prevalence": derived.get("peak_prevalence"),
            "deposit_gec": sum(
                (rel.get("deposit_by_callsite_gec") or {}).values(),
            ),
            "deposit_by_callsite": rel.get("deposit_by_callsite_gec") or {},
            "sanitary_delivered_gec": rel.get("sanitary_delivered_gec", 0.0),
            "emesis_patch_gec": em.get("patch", 0.0),
            "emesis_aerosol_gec": em.get("aerosol", 0.0),
            "ill_host_days": (
                rel.get("ill_host_epochs", 0) / EPOCHS_PER_DAY
            ),
        })
    return rows


def _cell_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    voyages = len(rows)
    imports = sum(r["imports"] for r in rows)
    axis_imports = sum(r["axis_imports"] for r in rows)
    emitted_imports = sum(r["emitted_imports"] for r in rows)
    ignited = [r for r in rows if r["ignited"]]
    cold = [r for r in rows if not r["ignited"]]
    est_ignited = sum(1 for r in ignited if r["outbreak_occurred"])
    est_cold = sum(1 for r in cold if r["outbreak_occurred"])
    ar = [r["attack_rate"] for r in ignited if r["attack_rate"] is not None]
    dep_gec = sum(r["deposit_gec"] for r in rows)
    ill_days = sum(r["ill_host_days"] for r in rows)
    callsite_totals: dict[str, float] = defaultdict(float)
    for r in rows:
        for site, mass in r["deposit_by_callsite"].items():
            callsite_totals[site] += mass
    return {
        "voyages": voyages,
        "imports": imports,
        "imports_per_voyage": imports / max(voyages, 1),
        "p_import_vomiting_axis": _wilson(axis_imports, imports),
        "p_import_emits": _wilson(emitted_imports, imports),
        "voyages_ignited": len(ignited),
        "p_voyage_ignited": _wilson(len(ignited), voyages),
        "establishment_given_ignited": _wilson(est_ignited, len(ignited)),
        "establishment_when_cold": _wilson(est_cold, len(cold)),
        "attack_rate_ignited_mean": (
            sum(ar) / len(ar) if ar else 0.0
        ),
        "secondaries_total": sum(r["secondaries"] for r in rows),
        "deposit_callsite_gec": dict(sorted(callsite_totals.items())),
        "deposit_gec_per_ill_day": dep_gec / ill_days if ill_days else 0.0,
        "emesis_patch_gec": sum(r["emesis_patch_gec"] for r in rows),
        "emesis_aerosol_gec": sum(r["emesis_aerosol_gec"] for r in rows),
        "ill_host_days": ill_days,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = _rows(args.zip_dir)
    if not rows:
        raise SystemExit(f"no run zips under {args.zip_dir}")
    tiers = sorted({r["tier"] for r in rows})
    report = {
        "cells": {
            tier: _cell_table([r for r in rows if r["tier"] == tier])
            for tier in tiers
        },
        "pooled": _cell_table(rows),
        "runs": rows,
    }
    text = json.dumps(report, indent=1)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")  # NOSONAR — operator-specified report path in a local diagnostic tool
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
