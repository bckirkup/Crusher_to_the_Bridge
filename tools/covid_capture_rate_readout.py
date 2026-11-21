#!/usr/bin/env python3
"""CAPTURE-01 readout: decompose the confirmed-per-infection capture rate.

Reads repo-local directories of campaign cell payloads (sync an S3 block
into the checkout first), each carrying ``funnel_hosts`` and
``campaign_specimen_log`` echoes, and decomposes the capture leg the
H5-RESCORE-01 rescore named as the next lever:

    infected -> confirmed ? / unconfirmed

The record captures ~0.85 of true infections (712 confirmed over the
serology band midpoint 836); at the right-sized-truth rows the replay
captures ~0.60. This readout localizes the missing quarter inside the
declared observation structure, splitting every unconfirmed infection
into:

- ``tail_infected``: infected after the last declared campaign day -
  no specimen channel could ever reach them (a timing fact, not a
  capacity defect).
- ``starved``: had at least one later campaign day after infection (or
  after a pre-infection negative) and was never rostered - the ladder
  spent its specimens on uninfected hosts below the cutoff.
- ``sensitivity_miss``: swabbed while infected and every specimen came
  back negative. Each swab's expected detectability under the profile's
  declared ``assay_sensitivity_by_time_since_infection`` curve is
  reported so the miss splits into swabs taken in the low-sensitivity
  dpi band (structural - the record's serial retesting is what catches
  these) and swabs in the high band (a real assay miss).

The campaign specimen log carries every campaign swab day per host;
``_lab_sampled`` carries each host's last specimen across channels, so
the per-host swab history is complete for never-presented hosts (their
only channel is the campaign) and bounded by the last specimen day for
presented hosts (the passive channel also swabs them).

Takeoff follows the scorer's gate: ``recorded_onsets >= 10``.

Usage:
    python3 tools/covid_capture_rate_readout.py \
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

from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

# dpi buckets for the declared Kucirka curve: the rising edge (declared
# 100%/67%/38% false-negative days 1/4/5), the peak window (dpi 5-14,
# detectability >= 0.62 declining from 0.80), and the waning tail
# (dpi 15+, under 0.66 and still falling).
_DPI_BUCKETS = ((0, 4), (5, 14), (15, 999))


def _sensitivity_curve(repo_root: Path) -> list[float]:
    """The declared dpi-indexed detectability curve of the covid arm."""
    profiles = json.loads(
        (repo_root / "data" / "pathogens" / "active_profiles.json").read_text()
    )
    for entry in profiles["pathogens"]:
        if entry.get("pathogen_id") == "sars_cov2_resp" or (
            entry.get("id") == "sars_cov2_resp"
        ):
            obs = entry.get("observation_model") or {}
            return [
                float(v)
                for v in (obs.get("assay_sensitivity_by_time_since_infection")
                          or [])
            ]
    raise SystemExit("sars_cov2_resp profile not found")


def _sens(curve: list[float], dpi: int) -> float:
    if not curve:
        return 1.0
    return curve[min(max(dpi, 0), len(curve) - 1)]


def _decompose_cell(
    payload: dict[str, Any], curve: list[float],
) -> dict[str, Any]:
    obs = payload.get("observables") or {}
    hosts = payload.get("funnel_hosts") or {}
    log = payload.get("campaign_specimen_log") or []

    campaign_days = sorted({int(r["day"]) for r in log})
    last_campaign_day = campaign_days[-1] if campaign_days else None
    campaign_pos_days: dict[int, set[int]] = {}
    swabs_by_host: dict[int, list[int]] = {}
    for r in log:
        aid = int(r["agent_id"])
        day = int(r["day"])
        swabs_by_host.setdefault(aid, []).append(day)
        if r.get("positive"):
            campaign_pos_days.setdefault(aid, set()).add(day)

    out_hosts: dict[str, Any] = {
        "confirmed_campaign": 0,
        "confirmed_passive": 0,
        "drains": {},
        # For the swabbed-while-infected-negative drain: every while-
        # infected campaign swab's dpi bucketed on the declared curve,
        # the passive last-specimen dpi for hosts with no campaign swab,
        # and whether a later declared campaign day existed after the
        # host's last while-infected swab (a starved retest) or not
        # (the declared tiers were exhausted).
        "miss_swab_dpi_hist": {f"{a}_{b}": 0 for a, b in _DPI_BUCKETS},
        "miss_passive_dpi_hist": {f"{a}_{b}": 0 for a, b in _DPI_BUCKETS},
        "miss_swabs_per_host": {},
        "miss_expected_escape": 0.0,
        "miss_starved_retest": 0,
        "miss_exhausted": 0,
        # Infection-day histograms by drain class (5-day buckets) - a
        # drain that clusters in the campaign window is roster reach;
        # one peaking at the last days is the incidence tail outrunning
        # the declared tiers.
        "drain_infection_days": {},
        # Denominator for the serial-escape expectation: every host
        # swabbed at least once while infected, missed or not, with the
        # sum of its declared-curve escape probability. Realized misses
        # vs this expectation says whether the misses are assay draws
        # running hot or the structure itself under-catching.
        "swabbed_infected_hosts": 0,
        "swabbed_infected_expected_escape": 0.0,
        "confirmed_swab_dpi_hist": {f"{a}_{b}": 0 for a, b in _DPI_BUCKETS},
    }
    capture_inf = 0
    capture_conf = 0
    inf_days: list[int] = []
    for aid_s, entry in hosts.items():
        inf_day = entry.get("infection_day")
        if inf_day is None:
            continue
        aid = int(aid_s)
        inf_day = int(inf_day)
        inf_days.append(inf_day)
        capture_inf += 1
        conf_day = entry.get("confirmed_day")
        presented = entry.get("presented_day") is not None
        if conf_day is not None:
            capture_conf += 1
            if int(conf_day) in campaign_pos_days.get(aid, set()):
                out_hosts["confirmed_campaign"] += 1
            else:
                out_hosts["confirmed_passive"] += 1
            conf_dpi = int(conf_day) - inf_day
            for lo, hi in _DPI_BUCKETS:
                if lo <= conf_dpi <= hi:
                    out_hosts["confirmed_swab_dpi_hist"][f"{lo}_{hi}"] += 1
                    break
            # Serial-escape denominator: this host was swabbed while
            # infected on every campaign day before the confirming
            # specimen - each of those was a missed draw it escaped.
            missed = [
                d for d in swabs_by_host.get(aid, [])
                if inf_day <= d < int(conf_day)
            ]
            out_hosts["swabbed_infected_hosts"] += 1
            escape = 1.0
            for d in missed:
                escape *= 1.0 - _sens(curve, d - inf_day)
            # The confirming draw had the same per-draw escape
            # probability; the expectation counts hosts escaping every
            # while-infected draw, positive ones included.
            escape *= 1.0 - _sens(curve, conf_dpi)
            out_hosts["swabbed_infected_expected_escape"] += escape
            continue

        spec_day = entry.get("specimen_day")
        state = "presented" if presented else "never_presented"
        if spec_day is None:
            mode = "tail_infected" if (
                last_campaign_day is not None and inf_day > last_campaign_day
            ) else "starved_never_swabbed"
            key = f"{mode}_{state}"
            out_hosts["drains"][key] = out_hosts["drains"].get(key, 0) + 1
            out_hosts["drain_infection_days"].setdefault(
                key, [],
            ).append(inf_day)
            continue
        spec_day = int(spec_day)
        if spec_day < inf_day:
            # Every swab predates the infection: a negative the declared
            # retest tiers could still reach if a later campaign day ran
            # after the infection.
            mode = "starved_pre_infection_negative" if (
                last_campaign_day is not None and inf_day <= last_campaign_day
            ) else "tail_infected"
            key = f"{mode}_{state}"
            out_hosts["drains"][key] = out_hosts["drains"].get(key, 0) + 1
            out_hosts["drain_infection_days"].setdefault(
                key, [],
            ).append(inf_day)
            continue
        # Swabbed at least once while infected and every specimen missed.
        # The campaign log gives the full swab history for this channel;
        # a host with no campaign swab shows only its channel-agnostic
        # last specimen day (the passive channel's).
        swabs = sorted(d for d in swabs_by_host.get(aid, []) if d >= inf_day)
        for d in swabs:
            dpi = d - inf_day
            for lo, hi in _DPI_BUCKETS:
                if lo <= dpi <= hi:
                    out_hosts["miss_swab_dpi_hist"][f"{lo}_{hi}"] += 1
                    break
        if swabs:
            out_hosts["miss_swabs_per_host"][len(swabs)] = (
                out_hosts["miss_swabs_per_host"].get(len(swabs), 0) + 1
            )
            # Expected serial-test escape probability under the declared
            # curve, draws treated as independent - what the record's
            # retesting structure implies for this host's swab set.
            escape = 1.0
            for d in swabs:
                escape *= 1.0 - _sens(curve, d - inf_day)
        else:
            dpi = spec_day - inf_day
            for lo, hi in _DPI_BUCKETS:
                if lo <= dpi <= hi:
                    out_hosts["miss_passive_dpi_hist"][f"{lo}_{hi}"] += 1
                    break
            out_hosts["miss_swabs_per_host"][1] = (
                out_hosts["miss_swabs_per_host"].get(1, 0) + 1
            )
            escape = 1.0 - _sens(curve, dpi)
        out_hosts["miss_expected_escape"] += escape
        last_while_infected = max(swabs + [spec_day])
        if last_campaign_day is not None and (
            last_while_infected < last_campaign_day
        ):
            out_hosts["miss_starved_retest"] += 1
        else:
            out_hosts["miss_exhausted"] += 1
        out_hosts["swabbed_infected_hosts"] += 1
        out_hosts["swabbed_infected_expected_escape"] += escape
        key = f"sensitivity_miss_{state}"
        out_hosts["drains"][key] = out_hosts["drains"].get(key, 0) + 1
        out_hosts["drain_infection_days"].setdefault(key, []).append(inf_day)

    takeoff = (obs.get("recorded_onsets") or 0) >= 10
    return {
        "seed": obs.get("seed"),
        "theta": obs.get("theta"),
        "takeoff": takeoff,
        "infections_total": capture_inf,
        "lab_confirmed": capture_conf,
        "capture": (
            capture_conf / capture_inf if capture_inf else None
        ),
        "recorded_onsets": obs.get("recorded_onsets"),
        "campaign_positives": obs.get("campaign_positives"),
        "infection_day_median": median(inf_days) if inf_days else None,
        "last_campaign_day": last_campaign_day,
        **out_hosts,
    }


def _merge_hist(hists) -> dict[str, int]:
    merged: dict[str, int] = {}
    for hist in hists:
        for k, v in hist.items():
            merged[k] = merged.get(k, 0) + v
    return merged


def _pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    takeoff = [c for c in cells if c["takeoff"]]
    pooled: dict[str, Any] = {
        "cells": len(cells),
        "takeoff_cells": len(takeoff),
        "drains": {},
        "miss_swab_dpi_hist": _merge_hist(
            c["miss_swab_dpi_hist"] for c in takeoff
        ),
        "miss_passive_dpi_hist": _merge_hist(
            c["miss_passive_dpi_hist"] for c in takeoff
        ),
        "miss_swabs_per_host": _merge_hist(
            c["miss_swabs_per_host"] for c in takeoff
        ),
        "miss_expected_escape": round(
            sum(c["miss_expected_escape"] for c in takeoff), 1
        ),
        "miss_starved_retest": sum(c["miss_starved_retest"] for c in takeoff),
        "miss_exhausted": sum(c["miss_exhausted"] for c in takeoff),
        "confirmed_campaign": sum(c["confirmed_campaign"] for c in takeoff),
        "confirmed_passive": sum(c["confirmed_passive"] for c in takeoff),
        "confirmed_swab_dpi_hist": _merge_hist(
            c["confirmed_swab_dpi_hist"] for c in takeoff
        ),
        "swabbed_infected_hosts": sum(
            c["swabbed_infected_hosts"] for c in takeoff
        ),
        "swabbed_infected_expected_escape": round(
            sum(c["swabbed_infected_expected_escape"] for c in takeoff), 1
        ),
        "drain_infection_days": {},
    }
    inf = sum(c["infections_total"] for c in takeoff)
    conf = sum(c["lab_confirmed"] for c in takeoff)
    pooled["infections_total"] = inf
    pooled["lab_confirmed"] = conf
    pooled["capture_pooled"] = conf / inf if inf else None
    caps = [c["capture"] for c in takeoff if c["capture"] is not None]
    pooled["capture_median"] = median(caps) if caps else None
    for c in takeoff:
        for k, v in c["drains"].items():
            pooled["drains"][k] = pooled["drains"].get(k, 0) + v
        for key, days in c["drain_infection_days"].items():
            hist = pooled["drain_infection_days"].setdefault(key, {})
            for day in days:
                bucket = f"{(day // 5) * 5}_{(day // 5) * 5 + 4}"
                hist[bucket] = hist.get(bucket, 0) + 1
    return pooled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    curve = _sensitivity_curve(_REPO_ROOT)
    cells: list[dict[str, Any]] = []
    for cells_arg in args.cells:
        cells_dir = resolve_repo_path(str(_REPO_ROOT), cells_arg)
        for path in sorted(glob.glob(str(Path(cells_dir) / "cell_*.json"))):
            payload = json.loads(Path(path).read_text())
            cells.append(_decompose_cell(payload, curve))
    if not cells:
        raise ValueError(
            f"no cell_*.json found under {args.cells!r} "
            "(paths resolve against the repository root)"
        )
    out = {"cells": cells, "pooled": _pool(cells)}
    out_path = Path(resolve_repo_path(str(_REPO_ROOT), args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(
        str(out_path), "w", allowed_roots=(str(_REPO_ROOT),)
    ) as fh:
        fh.write(json.dumps(out, indent=1) + "\n")
    pooled = out["pooled"]
    print(json.dumps(pooled, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
