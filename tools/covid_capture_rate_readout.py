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

Realized-vs-declared calibration is per-draw, not serial: confirmed
hosts' draw sequences truncate at first positive (``_specimen_barred``),
so a serial-escape expectation over observed draws is outcome-biased.
Every while-infected draw contributes one realized miss indicator and
one declared-curve expectation; their ratio says whether assay draws
miss more or less often than declared, unbiased by how many draws a
host happened to receive.

The campaign specimen log carries every campaign swab day per host;
``_lab_sampled`` carries each host's last specimen across channels, so
the per-host swab history is complete for never-presented hosts (their
only channel is the campaign) and bounded by the last specimen day for
presented hosts (the passive channel also swabs them).

``exit_screen_expected`` bounds a hypothetical universal exit swab at
the last campaign day: the sum over unconfirmed infected hosts of the
declared sensitivity at their dpi on that day.

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


def _bucket(dpi: int) -> str:
    for lo, hi in _DPI_BUCKETS:
        if lo <= dpi <= hi:
            return f"{lo}_{hi}"
    raise ValueError(f"dpi {dpi} outside buckets")


def _new_hosts_block() -> dict[str, Any]:
    return {
        "confirmed_campaign": 0,
        "confirmed_passive": 0,
        "drains": {},
        # For the swabbed-while-infected-negative drain: every while-
        # infected campaign swab's dpi bucketed on the declared curve,
        # the passive last-specimen dpi for hosts whose missed draws
        # include a passive specimen, and whether a later declared
        # campaign day existed after the host's last while-infected
        # swab (a starved retest) or not (the declared tiers were
        # exhausted).
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
        # Unbiased per-draw calibration: every while-infected draw on
        # an infected host, its realized outcome, and its declared-curve
        # miss expectation. Outcome-dependent draw counts cancel out.
        "while_infected_draws": 0,
        "expected_negative_draws": 0.0,
        "realized_negative_draws": 0,
        "swabbed_infected_hosts": 0,
        "confirmed_swab_dpi_hist": {f"{a}_{b}": 0 for a, b in _DPI_BUCKETS},
        # Universal-exit-swab bound: expected captures if every still-
        # aboard unconfirmed infected host were swabbed once at the
        # last campaign day under the declared curve.
        "exit_screen_expected": 0.0,
    }


def _record_draw(
    out: dict[str, Any], curve: list[float], dpi: int, negative: bool,
) -> None:
    out["while_infected_draws"] += 1
    out["expected_negative_draws"] += 1.0 - _sens(curve, dpi)
    if negative:
        out["realized_negative_draws"] += 1


def _record_drain(
    out: dict[str, Any], key: str, inf_day: int,
) -> None:
    out["drains"][key] = out["drains"].get(key, 0) + 1
    out["drain_infection_days"].setdefault(key, []).append(inf_day)


def _confirmed_host(
    out: dict[str, Any],
    curve: list[float],
    aid: int,
    inf_day: int,
    conf_day: int,
    campaign_pos_days: dict[int, set[int]],
    campaign_log_days: dict[int, set[int]],
    swabs_by_host: dict[int, list[int]],
) -> None:
    # Per-draw calibration over every while-infected campaign swab:
    # the confirming draw and the pre-confirmation misses it took to
    # get there.
    for d in swabs_by_host.get(aid, []):
        if d >= inf_day:
            _record_draw(
                out, curve, d - inf_day,
                negative=d not in campaign_pos_days.get(aid, set()),
            )
    if conf_day in campaign_pos_days.get(aid, set()):
        out["confirmed_campaign"] += 1
    else:
        out["confirmed_passive"] += 1
        # The confirming draw happened on the passive channel and is
        # not in the campaign log; count it as a realized hit.
        if conf_day not in campaign_log_days.get(aid, set()):
            _record_draw(out, curve, conf_day - inf_day, negative=False)
    out["confirmed_swab_dpi_hist"][_bucket(conf_day - inf_day)] += 1
    out["swabbed_infected_hosts"] += 1


def _unconfirmed_host(
    out: dict[str, Any],
    curve: list[float],
    aid: int,
    entry: dict[str, Any],
    inf_day: int,
    presented: bool,
    last_campaign_day: int | None,
    swabs_by_host: dict[int, list[int]],
) -> None:
    state = "presented" if presented else "never_presented"
    spec_day = entry.get("specimen_day")
    spec_day = int(spec_day) if spec_day is not None else None
    if spec_day is None:
        mode = "tail_infected" if (
            last_campaign_day is not None and inf_day > last_campaign_day
        ) else "starved_never_swabbed"
        _record_drain(out, f"{mode}_{state}", inf_day)
        return
    if spec_day < inf_day:
        # Every swab predates the infection: a negative the declared
        # retest tiers could still reach if a later campaign day ran
        # after the infection.
        mode = "starved_pre_infection_negative" if (
            last_campaign_day is not None and inf_day <= last_campaign_day
        ) else "tail_infected"
        _record_drain(out, f"{mode}_{state}", inf_day)
        return
    # Swabbed at least once while infected and every specimen missed.
    while_swabs = sorted(
        d for d in swabs_by_host.get(aid, []) if d >= inf_day
    )
    for d in while_swabs:
        out["miss_swab_dpi_hist"][_bucket(d - inf_day)] += 1
        _record_draw(out, curve, d - inf_day, negative=True)
    escape = 1.0
    for d in while_swabs:
        escape *= 1.0 - _sens(curve, d - inf_day)
    if spec_day not in while_swabs:
        # A passive-channel specimen the campaign log does not carry -
        # a real missed draw at its own dpi.
        out["miss_passive_dpi_hist"][_bucket(spec_day - inf_day)] += 1
        _record_draw(out, curve, spec_day - inf_day, negative=True)
        escape *= 1.0 - _sens(curve, spec_day - inf_day)
    n_draws = len(while_swabs) + (0 if spec_day in while_swabs else 1)
    out["miss_swabs_per_host"][n_draws] = (
        out["miss_swabs_per_host"].get(n_draws, 0) + 1
    )
    out["miss_expected_escape"] += escape
    last_while_infected = max(while_swabs + [spec_day])
    if last_campaign_day is not None and (
        last_while_infected < last_campaign_day
    ):
        out["miss_starved_retest"] += 1
    else:
        out["miss_exhausted"] += 1
    out["swabbed_infected_hosts"] += 1
    _record_drain(out, f"sensitivity_miss_{state}", inf_day)


def _decompose_cell(
    payload: dict[str, Any], curve: list[float],
) -> dict[str, Any]:
    obs = payload.get("observables") or {}
    hosts = payload.get("funnel_hosts") or {}
    log = payload.get("campaign_specimen_log") or []

    campaign_days = sorted({int(r["day"]) for r in log})
    last_campaign_day = campaign_days[-1] if campaign_days else None
    campaign_pos_days: dict[int, set[int]] = {}
    campaign_log_days: dict[int, set[int]] = {}
    swabs_by_host: dict[int, list[int]] = {}
    for r in log:
        aid = int(r["agent_id"])
        day = int(r["day"])
        swabs_by_host.setdefault(aid, []).append(day)
        campaign_log_days.setdefault(aid, set()).add(day)
        if r.get("positive"):
            campaign_pos_days.setdefault(aid, set()).add(day)

    out_hosts = _new_hosts_block()
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
            _confirmed_host(
                out_hosts, curve, aid, inf_day, int(conf_day),
                campaign_pos_days, campaign_log_days, swabs_by_host,
            )
            continue
        _unconfirmed_host(
            out_hosts, curve, aid, entry, inf_day, presented,
            last_campaign_day, swabs_by_host,
        )
        if last_campaign_day is not None:
            out_hosts["exit_screen_expected"] += _sens(
                curve, last_campaign_day - inf_day
            )

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
        "while_infected_draws": sum(
            c["while_infected_draws"] for c in takeoff
        ),
        "expected_negative_draws": round(
            sum(c["expected_negative_draws"] for c in takeoff), 1
        ),
        "realized_negative_draws": sum(
            c["realized_negative_draws"] for c in takeoff
        ),
        "swabbed_infected_hosts": sum(
            c["swabbed_infected_hosts"] for c in takeoff
        ),
        "exit_screen_expected": round(
            sum(c["exit_screen_expected"] for c in takeoff), 1
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
