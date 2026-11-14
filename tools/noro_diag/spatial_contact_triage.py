#!/usr/bin/env python3
"""Spatio-temporal-activity triage for the contact-constant audit.

Ranks fomite zone classes on a posted cell by post-run delivered/dose activity
and declared contact/area constants. Candidates are event spaces and
food-service spaces; berthing is excluded because cabin-mate mechanisms already
govern it. The run installs the same ``CascadeRecorder`` wrappers as
``hand_cascade_witness`` so the voyage witness matches the trusted harness, but
zone ranking is computed only after the run from ``fomite_mass_balance`` books;
there is no live per-epoch observer. ``screen_score`` is a screening index for
this triage only, not a fitted parameter.

The engine witness path is ``PYTHONHASHSEED``-sensitive, so paired comparisons
must fix ``PYTHONHASHSEED`` (the measurements below used ``PYTHONHASHSEED=1``).
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import attr_patches, install_wrappers  # noqa: E402
from tools.diag.manifest_args import identifier  # noqa: E402
from tools.noro_diag import fomite_mass_balance as fmb  # noqa: E402
from tools.noro_diag import hand_cascade_witness as witness  # noqa: E402


def _arm_spec(spec_dict: dict[str, Any], arm: str) -> dict[str, Any]:
    spec = copy.deepcopy(spec_dict)
    overrides = witness.ARMS.get(arm) or {}
    cfg = spec.setdefault("config_overrides", {})
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            merged = dict(cfg[key])
            merged.update(value)
            cfg[key] = merged
        else:
            cfg[key] = value
    return spec


SCOPE_BY_CLASS = {
    "galley": "food_service",
    "dining": "food_service",
    "crew_mess": "food_service",
    "public": "event_space",
    "sanitary": "event_space",
    "cabin": "berthing_excluded",
}
CANDIDATE_SCOPES = {"food_service", "event_space"}


def _empty_book() -> dict[str, float]:
    return {
        "zones": 0.0,
        "deposited_gec": 0.0,
        "deposit_calls": 0.0,
        "offered_gec": 0.0,
        "offer_calls": 0.0,
        "delivered_gec": 0.0,
        "delivery_calls": 0.0,
        "dose_gec": 0.0,
        "residual_gec": 0.0,
        "surface_contacts_per_hour": 0.0,
        "high_touch_area_m2": 0.0,
        "activity_mass_gec": 0.0,
        "screen_score": 0.0,
    }


def _add_contact_constants(books: dict[str, dict[str, float]]) -> None:
    for zone_class, book in books.items():
        book["surface_contacts_per_hour"] = float(
            tc.SURFACE_CONTACTS_PER_HOUR.get(zone_class, 0.0),
        )
        book["high_touch_area_m2"] = float(
            tc.HIGH_TOUCH_AREA_M2.get(zone_class, 0.0),
        )
        book["activity_mass_gec"] = book["delivered_gec"] + book["dose_gec"]
        book["screen_score"] = (
            book["activity_mass_gec"]
            * book["surface_contacts_per_hour"]
            / max(book["high_touch_area_m2"], 1e-9)
        )


def _aggregate_zone_classes(
    summary: dict[str, Any], rec: fmb.Recorder,
) -> list[dict[str, Any]]:
    books: dict[str, dict[str, float]] = defaultdict(_empty_book)
    core = rec.core
    for row in summary.get("zones", []):
        zone_name = str(row.get("zone", ""))
        zone_class = (
            core._fomite_zone_class(zone_name)
            if core is not None else "public"
        )
        book = books[zone_class]
        book["zones"] += 1.0
        for key in (
            "deposited_gec", "deposit_calls", "offered_gec", "offer_calls",
            "delivered_gec", "delivery_calls", "dose_gec", "residual_gec",
        ):
            book[key] += float(row.get(key, 0.0))
    _add_contact_constants(books)
    rows = []
    for zone_class, book in books.items():
        scope = SCOPE_BY_CLASS.get(zone_class, "unclassified")
        rows.append({
            "zone_class": zone_class,
            "scope": scope,
            "candidate": scope in CANDIDATE_SCOPES,
            **book,
        })
    rows.sort(
        key=lambda row: (
            row["candidate"],
            row["screen_score"],
            row["delivered_gec"],
            row["dose_gec"],
            row["deposited_gec"],
        ),
        reverse=True,
    )
    return rows


def _run_zone_arm(
    *, arm: str, spec_dict: dict[str, Any], seed: int, pathogen_id: str,
) -> dict[str, Any]:
    spec = _arm_spec(spec_dict, arm)
    epochs = int(spec["run"]["num_epochs"])
    rec = fmb.Recorder(pathogen_id=pathogen_id)
    cascade = witness.CascadeRecorder(pathogen_id)
    with attr_patches() as patches:
        originals = install_wrappers(tc.TransmissionCore, cascade.wrappers())
        patches.note_all(tc.TransmissionCore, originals)
        with fmb.materialized_picard_spec(
            spec, fmb.REPO_ROOT,
        ) as picard_spec:
            with fmb.instrumented(rec):
                sim = fmb.ShipSimulation(picard_spec, display=False)
                sim.run()
    summary = fmb.summarise(rec, seed, epochs)
    summary.pop("epoch_timeline", None)
    balance = summary["voyage_balance"]
    return {
        "seed": seed,
        "arm": arm,
        "run_id": spec.get("description"),
        "hosts_infected": summary["hosts_infected"],
        "hosts_symptomatic": summary["hosts_symptomatic"],
        "deposited_gec": balance["deposited_gec"],
        "delivered_all_paths_gec": balance["delivered_all_paths_gec"],
        "offered_gec": balance["offered_gec"],
        "dose_gec": sum(
            float(zone.get("dose_gec", 0.0)) for zone in summary["zones"]
        ),
        "zone_classes": _aggregate_zone_classes(summary, rec),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument(
        "--arms", nargs="+", choices=sorted(witness.ARMS),
        default=["carriers_ordered", "carriers_ordered_sub12"],
    )
    parser.add_argument("--pathogen-id", type=identifier, default="norwalk_gi")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    specs_by_seed = witness.tier_specs(args.manifest, args.tier, args.seeds)
    rows = []
    for arm in args.arms:
        for seed in args.seeds:
            row = _run_zone_arm(
                arm=arm, spec_dict=specs_by_seed[int(seed)], seed=int(seed),
                pathogen_id=args.pathogen_id,
            )
            rows.append(row)
            top = row["zone_classes"][0] if row["zone_classes"] else {}
            print(
                f"{arm:24s} seed {seed}: infected {row['hosts_infected']}, "
                f"top {top.get('zone_class', '-')}"
                f"[{top.get('scope', '-')}], "
                f"score {top.get('screen_score', 0.0):.6g}, "
                f"activity {top.get('activity_mass_gec', 0.0):.6g}, "
                f"contacts/h {top.get('surface_contacts_per_hour', 0.0):.6g}, "
                f"area_m2 {top.get('high_touch_area_m2', 0.0):.6g}",
            )
    payload = {
        "manifest": str(args.manifest),
        "tier": args.tier,
        "pathogen_id": args.pathogen_id,
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "rows": rows,
    }
    path = resolve_child_path(
        str(out_dir), "spatiotemporal_activity_triage.json.gz",
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
