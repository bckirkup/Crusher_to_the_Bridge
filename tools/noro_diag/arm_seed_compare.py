#!/usr/bin/env python3
"""Seed-for-seed payload comparison between two census cells.

NORO-DETECT-01 validation gate: the ``onset`` arm must reproduce the
VENUE-02 k=1 cells exactly on every seed — the presenting-sign path
draws nothing, so any divergence is a mechanism defect, not a finding.

Joins run zips on ``venue.seed`` and diffs the fields a seeded engine
must replay identically: emit rows (count + per-row epoch/zone), host
order/confined epochs, confinement event stream, acquisition count and
ignited flag. Field-level tolerances are zero; differences are reported
per seed and field, never aggregated away.

Usage:
    python3 tools/noro_diag/arm_seed_compare.py \
        --base results/noro_venue_02/fl_spr_12d_k1 \
        --arm  results/noro_detect_01/fl_spr_12d_onset
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.diag.readout_common import read_zip_member  # noqa: E402

# Fields compared verbatim per seed. Emit-row identity covers epoch,
# zone, and joining class; confinement events cover the order stream.
_EMIT_FIELDS = (
    "agent_id", "epoch", "zone", "site_class",
    "confinement_class", "order_subclass", "emitter_class", "first_emit",
)
_EVENT_FIELDS = ("epoch", "agent_id", "action", "compliance_class")
_HOST_FIELDS = (
    "first_symptomatic_epoch", "first_emit_epoch", "first_order_epoch",
    "first_confined_epoch", "n_confined_epochs", "n_emesis_emits",
)
_SCALAR_FIELDS = (
    "ignited", "n_emesis_emitted", "n_acquired", "n_imports",
    "n_unattributed", "escort_delay_epochs", "escort_pending_final",
)


def _load_venue(zip_path: Path) -> dict[str, Any] | None:
    raw = read_zip_member(zip_path, "venue.json.gz")
    if raw is None:
        return None
    return json.loads(gzip.decompress(raw))


def _rows_by_key(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict]]:
    out: dict[Any, list[dict]] = {}
    for row in rows:
        out.setdefault(row.get(key), []).append(row)
    return out


def _diff_field(path: str, a: Any, b: Any, diffs: list[str]) -> None:
    if a != b:
        diffs.append(f"{path}: base={a!r} arm={b!r}")


def compare_seed(base: dict[str, Any], arm: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    for field in _SCALAR_FIELDS:
        _diff_field(field, base.get(field), arm.get(field), diffs)
    _diff_emit_rows(base, arm, diffs)
    _diff_events(base, arm, diffs)
    _diff_hosts(base, arm, diffs)
    return diffs


def _diff_emit_rows(
    base: dict[str, Any], arm: dict[str, Any], diffs: list[str],
) -> None:
    base_emits = sorted(
        (tuple(r.get(f) for f in _EMIT_FIELDS) for r in base["emit_rows"]),
    )
    arm_emits = sorted(
        (tuple(r.get(f) for f in _EMIT_FIELDS) for r in arm["emit_rows"]),
    )
    if base_emits != arm_emits:
        diffs.append(
            f"emit_rows differ: base {len(base_emits)} rows, "
            f"arm {len(arm_emits)} rows",
        )
        for i, (br, ar) in enumerate(zip(base_emits, arm_emits)):
            if br != ar:
                diffs.append(f"  first emit diff @{i}: base={br} arm={ar}")
                break


def _diff_events(
    base: dict[str, Any], arm: dict[str, Any], diffs: list[str],
) -> None:
    base_events = [tuple(e.get(f) for f in _EVENT_FIELDS)
                   for e in base["confinement_events"]]
    arm_events = [tuple(e.get(f) for f in _EVENT_FIELDS)
                  for e in arm["confinement_events"]]
    if base_events != arm_events:
        diffs.append(
            f"confinement_events differ: base {len(base_events)}, "
            f"arm {len(arm_events)}",
        )
        for i, (be, ae) in enumerate(zip(base_events, arm_events)):
            if be != ae:
                diffs.append(
                    f"  first event diff @{i}: base={be} arm={ae}",
                )
                break


def _diff_hosts(
    base: dict[str, Any], arm: dict[str, Any], diffs: list[str],
) -> None:
    base_hosts = {int(h["agent_id"]): h for h in base["host_rows"]}
    arm_hosts = {int(h["agent_id"]): h for h in arm["host_rows"]}
    for aid in sorted(set(base_hosts) | set(arm_hosts)):
        bh, ah = base_hosts.get(aid), arm_hosts.get(aid)
        if bh is None or ah is None:
            diffs.append(f"host {aid}: present={bh is not None}/{ah is not None}")
            continue
        for field in _HOST_FIELDS:
            _diff_field(
                f"host {aid}.{field}", bh.get(field), ah.get(field), diffs,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--arm", type=Path, required=True)
    args = parser.parse_args(argv)

    base_by_seed = {
        v["seed"]: v
        for z in sorted(args.base.glob("*.zip"))
        if (v := _load_venue(z)) is not None
    }
    arm_by_seed = {
        v["seed"]: v
        for z in sorted(args.arm.glob("*.zip"))
        if (v := _load_venue(z)) is not None
    }
    print(f"base seeds: {len(base_by_seed)} | arm seeds: {len(arm_by_seed)}")
    missing = sorted(set(base_by_seed) - set(arm_by_seed))
    extra = sorted(set(arm_by_seed) - set(base_by_seed))
    for seed in missing:
        print(f"MISSING in arm: seed {seed}")
    for seed in extra:
        print(f"EXTRA in arm: seed {seed}")
    total_diffs = 0
    for seed in sorted(set(base_by_seed) & set(arm_by_seed)):
        diffs = compare_seed(base_by_seed[seed], arm_by_seed[seed])
        if diffs:
            total_diffs += len(diffs)
            print(f"seed {seed}: {len(diffs)} diffs")
            for d in diffs[:10]:
                print(f"  {d}")
    if not total_diffs and not missing:
        print("IDENTICAL: every shared seed reproduces the baseline payload")
        return 0
    print(f"TOTAL {total_diffs} field diffs")
    return 1


if __name__ == "__main__":
    sys.exit(main())
