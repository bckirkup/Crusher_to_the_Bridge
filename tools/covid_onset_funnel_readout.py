#!/usr/bin/env python3
"""ONSET-FUNNEL-01 readout: decompose the onset -> specimen -> record funnel.

Reads a directory of campaign cell payloads (a synced S3 block or a local
dir), each carrying ``funnel_hosts`` and ``campaign_specimen_log`` echoes,
and decomposes the recorded-onset channel end-to-end per seed and pooled:

    infection -> presented -> specimen -> confirmed -> dated onset

so the ``recorded_onsets`` residual factorizes into the terms that can move
it: infection volume, presented share, confirmed volume (and its
campaign/passive channel split), and the dating share of confirmed. The
asymptomatic-at-specimen share decomposes the same way DATING-RES-01 /
ASYM-CONF-01 decomposed it in local replays - never-present hosts,
pre-onset catches, and post-onset catches - but reconstructed here from the
committed payload echoes, so no re-run is needed and the measurement is the
same realization the campaign scored.

Usage:
    python3 tools/covid_onset_funnel_readout.py \
        --cells <dir> [--cells <dir>] --out <json>
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from statistics import median
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import validated_open  # noqa: E402


def _host_map(hosts: dict[str, Any], field: str) -> dict[int, int]:
    return {
        int(aid): int(entry[field])
        for aid, entry in hosts.items()
        if entry.get(field) is not None
    }


def _decompose_cell(payload: dict[str, Any]) -> dict[str, Any]:
    """Decompose one cell payload's funnel echoes into per-stage counts."""
    obs = payload.get("observables") or {}
    hosts = payload.get("funnel_hosts") or {}
    log = payload.get("campaign_specimen_log") or []

    infection = _host_map(hosts, "infection_day")
    presented = _host_map(hosts, "presented_day")
    confirmed = _host_map(hosts, "confirmed_day")
    sampled = _host_map(hosts, "specimen_day")

    campaign_pos_days: dict[int, set[int]] = {}
    for entry in log:
        if entry.get("positive"):
            campaign_pos_days.setdefault(
                int(entry["agent_id"]), set(),
            ).add(int(entry["day"]))

    channel = {"campaign": 0, "passive": 0}
    pre_onset_catch = 0
    never_present_confirmed = 0
    dpi_at_confirmation: list[int] = []
    for aid, conf_day in confirmed.items():
        if conf_day in campaign_pos_days.get(aid, set()):
            channel["campaign"] += 1
        else:
            channel["passive"] += 1
        onset_day = presented.get(aid)
        if onset_day is None:
            never_present_confirmed += 1
        elif conf_day < onset_day:
            pre_onset_catch += 1
        if aid in infection:
            dpi_at_confirmation.append(conf_day - infection[aid])

    campaign_positive_hosts = {"never_presented": 0, "pre_onset": 0, "post_onset": 0}
    for aid, days in campaign_pos_days.items():
        onset_day = presented.get(aid)
        first_pos = min(days)
        if onset_day is None:
            campaign_positive_hosts["never_presented"] += 1
        elif first_pos < onset_day:
            campaign_positive_hosts["pre_onset"] += 1
        else:
            campaign_positive_hosts["post_onset"] += 1

    drains: dict[str, dict[str, int]] = {}
    for aid, inf_day in infection.items():
        if aid in confirmed:
            continue
        spec_day = sampled.get(aid)
        if spec_day is None:
            mode = "never_swabbed"
        elif spec_day < inf_day:
            mode = "swabbed_only_pre_infection"
        else:
            mode = "swabbed_while_infected_negative"
        state = "presented" if aid in presented else "never_presented"
        drains.setdefault(f"{mode}_{state}", 0)
        drains[f"{mode}_{state}"] += 1

    n_confirmed = len(confirmed)
    recorded = obs.get("recorded_onsets")
    return {
        "seed": obs.get("seed"),
        "theta": obs.get("theta"),
        "arm_id": payload.get("arm_id"),
        "design_id": payload.get("design_id"),
        "infections_total": len(infection),
        "presented_total": len(presented),
        "sampled_total": len(sampled),
        "lab_confirmed_total": n_confirmed,
        "confirmed_channel": channel,
        "confirmed_never_presented": never_present_confirmed,
        "confirmed_pre_onset_catch": pre_onset_catch,
        "dpi_at_confirmation_median": (
            median(dpi_at_confirmation) if dpi_at_confirmation else None
        ),
        "campaign_positives": obs.get("campaign_positives"),
        "campaign_positive_hosts": campaign_positive_hosts,
        "asymptomatic_share": obs.get("asymptomatic_share"),
        "recorded_onsets": recorded,
        "dated_share_of_confirmed": (
            recorded / n_confirmed if n_confirmed and recorded else None
        ),
        "unconfirmed_infected_drains": drains,
    }


def _pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    takeoff = [c for c in cells if c["infections_total"] > 1]
    pooled = {
        "cells": len(cells),
        "takeoff_cells": len(takeoff),
        "infections_total": sum(c["infections_total"] for c in cells),
        "presented_total": sum(c["presented_total"] for c in cells),
        "lab_confirmed_total": sum(c["lab_confirmed_total"] for c in cells),
        "recorded_onsets": sum(c["recorded_onsets"] or 0 for c in cells),
        "confirmed_channel": {
            k: sum(c["confirmed_channel"][k] for c in cells)
            for k in ("campaign", "passive")
        },
        "confirmed_never_presented": sum(
            c["confirmed_never_presented"] for c in cells
        ),
        "confirmed_pre_onset_catch": sum(
            c["confirmed_pre_onset_catch"] for c in cells
        ),
        "campaign_positive_hosts": {
            k: sum(c["campaign_positive_hosts"][k] for c in cells)
            for k in ("never_presented", "pre_onset", "post_onset")
        },
        "unconfirmed_infected_drains": {},
        "medians": {},
    }
    for c in cells:
        for key, n in c["unconfirmed_infected_drains"].items():
            pooled["unconfirmed_infected_drains"][key] = (
                pooled["unconfirmed_infected_drains"].get(key, 0) + n
            )
    for key in (
        "infections_total",
        "presented_total",
        "lab_confirmed_total",
        "recorded_onsets",
        "campaign_positives",
        "asymptomatic_share",
        "dated_share_of_confirmed",
        "dpi_at_confirmation_median",
    ):
        vals = [c[key] for c in takeoff if c.get(key) is not None]
        pooled["medians"][key] = median(vals) if vals else None
    return pooled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    cells: list[dict[str, Any]] = []
    for cells_dir in args.cells:
        for path in sorted(glob.glob(str(Path(cells_dir) / "cell_*.json"))):
            cells.append(_decompose_cell(json.loads(Path(path).read_text())))
    out = {"cells": cells, "pooled": _pool(cells)}
    with validated_open(args.out, "w", allowed_roots=(str(_REPO_ROOT), "/tmp")) as fh:
        fh.write(json.dumps(out, indent=1) + "\n")
    pooled = out["pooled"]
    print(json.dumps({
        "cells": pooled["cells"],
        "takeoff_cells": pooled["takeoff_cells"],
        "medians": pooled["medians"],
        "confirmed_channel": pooled["confirmed_channel"],
        "campaign_positive_hosts": pooled["campaign_positive_hosts"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
