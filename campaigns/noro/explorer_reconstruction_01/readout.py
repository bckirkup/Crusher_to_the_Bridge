#!/usr/bin/env python3
"""Reconstruction table for noro_explorer_reconstruction_01.

Reads the cell archives ``cell.py`` wrote (``<results>/**/<run_id>.zip``),
audits each against the design's invariants, and scores the frozen engine
against the Explorer of the Seas target in ``empirical_target.json``. Every
criterion applied here is the one frozen in ``DESIGN.md`` before any cell
ran; the readout computes them and tunes nothing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import zipfile
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CAMPAIGN_DIR = Path(__file__).resolve().parent
ROLES = ("passenger", "crew")

# Frozen in DESIGN.md ("Evaluable cells").
MIN_ABOARD_ONSETS = {"passenger": 20, "crew": 5}
CENTRAL_INTERVAL = (0.05, 0.95)
REFERENCE_ARM = "reference"
RESPONSE_SOPS = ("SOP-007", "SOP-009")
# The itinerary spans eight calendar dates and seven elapsed days.
ELAPSED_DAYS = 7


def confined(path: Path | str) -> Path:
    """Resolve ``path`` and refuse anything outside the repository."""
    root = os.path.realpath(_REPO_ROOT)
    resolved = os.path.realpath(os.path.join(root, str(path)))
    if resolved != root and not resolved.startswith(root + os.sep):
        raise SystemExit(f"path leaves the repository: {path}")
    return Path(resolved)


def peak_day(counts: list[int]) -> int | None:
    """Day of the maximum daily count; the earliest day on a tie."""
    if not counts or max(counts) <= 0:
        return None
    return counts.index(max(counts))


def peak_tied(counts: list[int]) -> bool:
    return bool(counts) and max(counts) > 0 and counts.count(max(counts)) > 1


def total_variation(model: list[int], target: list[int]) -> float | None:
    """Half the L1 distance between the two normalized daily curves."""
    if sum(model) <= 0 or sum(target) <= 0:
        return None
    return 0.5 * sum(
        abs(m / sum(model) - t / sum(target)) for m, t in zip(model, target)
    )


def quantile(values: list[float], q: float) -> float | None:
    """Linear-interpolated quantile of ``values``."""
    if not values:
        return None
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def cell_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """One cell's curve metrics, from its archive summary."""
    aboard = payload["onsets_by_day"]["excluding_declared_seeds"]
    every = payload["onsets_by_day"]["all"]
    reported = payload["reporting_by_day"]["cumulative_end_of_day"]
    complement = payload["introduction"]["complement"]
    peaks = {role: peak_day(aboard[role]) for role in ROLES}
    evaluable = all(
        sum(aboard[role]) >= MIN_ABOARD_ONSETS[role] for role in ROLES
    )
    lag = None
    if evaluable and None not in peaks.values():
        lag = peaks["crew"] - peaks["passenger"]
    first_active = payload["protocols"]["first_active_epoch"]
    return {
        "seed": int(payload["seed"]),
        "tier": payload["tier"],
        "evaluable": evaluable,
        "peak_day": peaks,
        "peak_tied": {role: peak_tied(aboard[role]) for role in ROLES},
        "lag_days": lag,
        "onset_total": {role: sum(every[role]) for role in ROLES},
        "onset_total_aboard": {role: sum(aboard[role]) for role in ROLES},
        "onset_attack_rate": {
            role: sum(every[role]) / complement[role] for role in ROLES
        },
        "reported_final": {role: reported[role][-1] for role in ROLES},
        "reported_attack_rate": {
            role: reported[role][-1] / complement[role] for role in ROLES
        },
        "epoch_zero_reported": payload["reporting_by_day"][
            "epoch_zero_cumulative"
        ],
        "preboarding_reportable": payload["introduction"][
            "preboarding_reportable"
        ],
        "aboard_curve": aboard,
        "onset_curve": every,
        "reported_curve": reported,
        "effective_state": payload["effective_state"],
        "onset_total_first_seven_days": {
            role: sum(every[role][:ELAPSED_DAYS]) for role in ROLES
        },
        "response_sop_first_epoch": {
            sop: first_active.get(sop) for sop in RESPONSE_SOPS
        },
    }


def audit_cell(
    payload: dict[str, Any], manifest: dict[str, Any], expect_sha: str | None,
) -> list[str]:
    """Design invariants; a violation is a defect, not a failed criterion."""
    problems = []
    tier = manifest["tiers"][payload["tier"]]
    if payload["frozen_block_witness"]["mismatches"]:
        problems.append("frozen block not resolved verbatim")
    if payload["num_epochs"] != tier["epoch_durations"][0]:
        problems.append(f"ran {payload['num_epochs']} epochs")
    declared = manifest["introduction_blocks"][tier["introduction"]]
    wanted = sum(s["count"] for s in declared.get("explicit_seeds") or ())
    roles = payload["introduction"]["declared_seed_roles"]
    if len(roles) != wanted or any(role != "passenger" for role in roles):
        problems.append(f"declared seeds {roles}, design declares {wanted}")
    complement = payload["introduction"]["complement"]
    intended = manifest["complement_blocks"][tier["complement"]]["intended"]
    if sum(complement.values()) != tier["num_agents"]:
        problems.append("complement does not sum to num_agents")
    if complement != intended or payload["intended_complement"] != intended:
        problems.append(f"complement {complement}, declared {intended}")
    state = payload["effective_state"]
    if state["exposure_cap_requested"] != state["exposure_cap_active"]:
        problems.append(
            "exposure cap requested "
            f"{state['exposure_cap_requested']} but active "
            f"{state['exposure_cap_active']} on {payload['platform']}",
        )
    if payload["introduction"]["preboarding_reportable"]["passenger"]:
        problems.append("passenger in the embarkation report counter")
    problems += audit_arm(payload, tier)
    if expect_sha and not str(payload["engine_git_sha"]).startswith(expect_sha):
        problems.append(f"engine {payload['engine_git_sha']}")
    return problems


def audit_arm(payload: dict[str, Any], tier: dict[str, Any]) -> list[str]:
    """The cell ran the tier's declared arm and resolved it as declared."""
    wanted = tier.get("arm", REFERENCE_ARM)
    witness = payload.get("declared_arm")
    if witness is None:
        # Archives written before any arm was declared are reference cells.
        return [] if wanted == REFERENCE_ARM else ["no declared-arm witness"]
    problems = []
    if witness["arm"] != wanted:
        problems.append(f"ran arm {witness['arm']}, tier declares {wanted}")
    if witness["mismatches"]:
        problems.append(f"arm not resolved as declared: {witness['mismatches']}")
    return problems


def load_cells(results: Path) -> list[dict[str, Any]]:
    cells = []
    for zip_path in sorted(results.rglob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            cells.append(json.loads(archive.read("summary.json")))
    return cells


def _share(values: list[Any], wanted: Any, tolerance: int = 0) -> float | None:
    if not values:
        return None
    return sum(abs(v - wanted) <= tolerance for v in values) / len(values)


def _states(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distinct effective mechanism states seen in a tier."""
    seen = {json.dumps(c["effective_state"], sort_keys=True) for c in cells}
    return [json.loads(state) for state in sorted(seen)]


def _interval(values: list[float]) -> dict[str, Any]:
    return {
        "median": statistics.median(values) if values else None,
        "q05": quantile(values, CENTRAL_INTERVAL[0]),
        "q95": quantile(values, CENTRAL_INTERVAL[1]),
    }


def _covers(interval: dict[str, Any], value: float) -> bool | None:
    if interval["q05"] is None:
        return None
    return interval["q05"] <= value <= interval["q95"]


def tier_summary(
    cells: list[dict[str, Any]], target: dict[str, Any], same_ship: bool,
) -> dict[str, Any]:
    """Seed-ensemble summary of one tier against the target."""
    evaluable = [c for c in cells if c["evaluable"]]
    lags = [c["lag_days"] for c in evaluable if c["lag_days"] is not None]
    target_lag = target["crew_minus_passenger_peak_lag_days"]
    out: dict[str, Any] = {
        "cells": len(cells),
        "evaluable": len(evaluable),
        "lag_days": {
            **_interval(lags),
            "p_equal_target": _share(lags, target_lag),
            "p_crew_later": (
                None if not lags else sum(v >= 1 for v in lags) / len(lags)
            ),
            "target": target_lag,
            "target_in_central_90": _covers(_interval(lags), target_lag),
        },
        "response_sop_cells": {
            sop: sum(c["response_sop_first_epoch"][sop] is not None for c in cells)
            for sop in RESPONSE_SOPS
        },
        "effective_state": _states(cells),
        "embarkation_declarations_max": {
            role: max(
                (c["preboarding_reportable"][role] for c in cells), default=0,
            )
            for role in ROLES
        },
        "epoch_zero_reported_max": {
            role: max((c["epoch_zero_reported"][role] for c in cells), default=0)
            for role in ROLES
        },
    }
    for role in ROLES:
        peaks = [c["peak_day"][role] for c in evaluable]
        finals = target["investigation_finals"][role]
        posting = target["posting_figures"][role]
        onset_rate = [c["onset_attack_rate"][role] for c in cells]
        reported_rate = [c["reported_attack_rate"][role] for c in cells]
        curve_distance = [
            d for d in (
                total_variation(
                    c["aboard_curve"][role], target["onsets_by_day"][role],
                )
                for c in evaluable
            ) if d is not None
        ]
        block = {
            "peak_day": {
                **_interval(peaks),
                "p_equal_target": _share(peaks, target["peak_day_index"][role]),
                "p_within_one_day": _share(
                    peaks, target["peak_day_index"][role], 1,
                ),
                "target": target["peak_day_index"][role],
                "target_in_central_90": _covers(
                    _interval(peaks), target["peak_day_index"][role],
                ),
                "tied_cells": sum(c["peak_tied"][role] for c in evaluable),
            },
            "onset_attack_rate": {
                **_interval(onset_rate),
                "target": finals["cases"] / finals["denominator"],
            },
            "reported_attack_rate_vs_posting": {
                **_interval(reported_rate),
                "target": posting["cases"] / posting["denominator"],
            },
            "curve_total_variation": _interval(curve_distance),
        }
        if same_ship:
            totals = [float(c["onset_total"][role]) for c in evaluable]
            block["onset_total_all_cells"] = _interval(
                [float(c["onset_total"][role]) for c in cells],
            )
            block["onset_total"] = {
                **_interval(totals),
                "target": finals["cases"],
                "target_in_central_90": _covers(
                    _interval(totals), finals["cases"],
                ),
            }
            block["onset_total_first_seven_days"] = _interval([
                float(c["onset_total_first_seven_days"][role])
                for c in evaluable
            ])
        out[role] = block
    return out


def paired_contrast(
    explorer: list[dict[str, Any]], mega: list[dict[str, Any]],
) -> dict[str, Any]:
    """Explorer minus mega on shared seed labels (bundle, not geometry)."""
    by_seed = {c["seed"]: c for c in mega}
    pairs = [(c, by_seed[c["seed"]]) for c in explorer if c["seed"] in by_seed]
    both = [(e, m) for e, m in pairs if e["evaluable"] and m["evaluable"]]
    out: dict[str, Any] = {
        "pairs": len(pairs),
        "pairs_both_evaluable": len(both),
        "lag_days_diff": _interval([
            float(e["lag_days"] - m["lag_days"]) for e, m in both
            if e["lag_days"] is not None and m["lag_days"] is not None
        ]),
    }
    for role in ROLES:
        out[role] = {
            "peak_day_diff": _interval([
                float(e["peak_day"][role] - m["peak_day"][role])
                for e, m in both
            ]),
            "onset_attack_rate_diff": _interval([
                e["onset_attack_rate"][role] - m["onset_attack_rate"][role]
                for e, m in pairs
            ]),
        }
    return out


def _mean_daily_diff(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]], curve: str,
) -> dict[str, list[float] | None]:
    """Mean over pairs of the per-day difference of one curve, per role."""
    out: dict[str, list[float] | None] = {}
    for role in ROLES:
        rows = [
            [a - b for a, b in zip(left[curve][role], right[curve][role])]
            for left, right in pairs
        ]
        out[role] = (
            [sum(day) / len(rows) for day in zip(*rows)] if rows else None
        )
    return out


def arm_contribution(
    reference: list[dict[str, Any]], arm: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reference minus arm on paired seeds of one hull: what the arm removed.

    Every pair is used, quiet cells included; nothing here is a criterion.
    """
    by_seed = {c["seed"]: c for c in arm}
    pairs = [(c, by_seed[c["seed"]]) for c in reference if c["seed"] in by_seed]
    curves = ("onset_curve", "reported_curve")
    out: dict[str, Any] = {
        "pairs": len(pairs),
        "pairs_identical_curves": sum(
            all(r[c] == a[c] for c in curves) for r, a in pairs
        ),
        "mean_daily_onset_diff": _mean_daily_diff(pairs, "onset_curve"),
        "mean_cumulative_reported_diff": _mean_daily_diff(
            pairs, "reported_curve",
        ),
    }
    for role in ROLES:
        out[role] = {
            key: _interval([r[key][role] - a[key][role] for r, a in pairs])
            for key in ("onset_attack_rate", "reported_attack_rate")
        }
    out["contrast"] = paired_contrast(reference, arm)
    return out


def _hull_contrasts(
    manifest: dict[str, Any], by_tier: dict[str, list[dict[str, Any]]],
    arm: str,
) -> dict[str, Any]:
    """Explorer minus mega per introduction, within one arm."""
    explorer_platform = manifest["platform"]
    contrasts = {}
    for introduction in manifest["introduction_blocks"]:
        names = {
            tier["platform"]: name for name, tier in manifest["tiers"].items()
            if tier["introduction"] == introduction
            and tier.get("arm", REFERENCE_ARM) == arm
        }
        mega = [p for p in names if p != explorer_platform]
        if explorer_platform in names and mega:
            contrasts[introduction] = paired_contrast(
                by_tier[names[explorer_platform]], by_tier[names[mega[0]]],
            )
    return contrasts


def _arm_readouts(
    manifest: dict[str, Any], by_tier: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Per declared arm: its contribution per hull and its hull contrast."""
    out = {}
    for arm, block in (manifest.get("arm_blocks") or {}).items():
        out[arm] = {
            "changed_paths": block["changed_paths"],
            "reference_minus_arm": {
                arm_tier: {
                    "reference_tier": reference_tier,
                    "platform": manifest["tiers"][arm_tier]["platform"],
                    **arm_contribution(
                        by_tier[reference_tier], by_tier[arm_tier],
                    ),
                }
                for arm_tier, reference_tier in block["paired_with"].items()
            },
            "explorer_minus_mega": _hull_contrasts(manifest, by_tier, arm),
        }
    return out


def build_readout(
    payloads: list[dict[str, Any]], manifest: dict[str, Any],
    target: dict[str, Any], expect_sha: str | None = None,
) -> dict[str, Any]:
    defects: list[dict[str, Any]] = []
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in manifest["tiers"]}
    for payload in payloads:
        problems = audit_cell(payload, manifest, expect_sha)
        if problems:
            defects.append({
                "tier": payload["tier"], "seed": payload["seed"],
                "problems": problems,
            })
        by_tier[payload["tier"]].append(cell_metrics(payload))
    explorer_platform = manifest["platform"]
    tiers = {
        tier: tier_summary(
            cells, target,
            manifest["tiers"][tier]["platform"] == explorer_platform,
        )
        for tier, cells in by_tier.items()
    }
    contrasts = _hull_contrasts(manifest, by_tier, REFERENCE_ARM)
    return {
        "campaign": manifest["campaign"],
        "expected_cells": sum(len(t["seeds"]) for t in manifest["tiers"].values()),
        "cells": len(payloads),
        "engine_git_sha": sorted({str(p["engine_git_sha"]) for p in payloads}),
        "defects": defects,
        "target": target,
        "tiers": tiers,
        "explorer_minus_mega": contrasts,
        "arms": _arm_readouts(manifest, by_tier),
    }


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _span(stats: dict[str, Any], digits: int = 2) -> str:
    return (
        f"{_fmt(stats['median'], digits)} "
        f"[{_fmt(stats['q05'], digits)}, {_fmt(stats['q95'], digits)}]"
    )


def _curve(values: list[float] | None) -> str:
    if values is None:
        return "—"
    return ", ".join(f"{value:+.2f}" for value in values)


def _arm_markdown(arm: str, block: dict[str, Any]) -> list[str]:
    changed = "; ".join(
        f"`{c['path']}` {c['baseline']} → {c['arm']}"
        for c in block["changed_paths"]
    )
    lines = [
        "",
        f"Declared arm `{arm}` ({changed}). Reference tier minus arm tier "
        "on paired seeds of the same hull: what the changed path "
        "contributes. All pairs, quiet cells included; reported, never "
        "judged:",
        "",
        "| Arm tier | Pairs | Identical curves | Pax onset AR diff | "
        "Crew onset AR diff | Pax reported AR diff | Crew reported AR diff |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for tier, row in block["reference_minus_arm"].items():
        lines.append(
            f"| `{tier}` | {row['pairs']} | {row['pairs_identical_curves']} | "
            f"{_span(row['passenger']['onset_attack_rate'], 4)} | "
            f"{_span(row['crew']['onset_attack_rate'], 4)} | "
            f"{_span(row['passenger']['reported_attack_rate'], 4)} | "
            f"{_span(row['crew']['reported_attack_rate'], 4)} |",
        )
    lines += [
        "",
        "Mean paired difference by voyage day (reference minus arm):",
        "",
        "| Arm tier | Curve | Passengers | Crew |",
        "|---|---|---|---|",
    ]
    for tier, row in block["reference_minus_arm"].items():
        for label, key in (
            ("daily onsets", "mean_daily_onset_diff"),
            ("cumulative reported", "mean_cumulative_reported_diff"),
        ):
            lines.append(
                f"| `{tier}` | {label} | {_curve(row[key]['passenger'])} | "
                f"{_curve(row[key]['crew'])} |",
            )
    lines += [
        "",
        f"Explorer minus mega within arm `{arm}` (both hulls on the arm "
        "value):",
        "",
        "| Introduction | Pairs | Both evaluable | Lag diff | "
        "Pax onset AR diff | Crew onset AR diff |",
        "|---|---:|---:|---|---|---|",
    ]
    for introduction, row in block["explorer_minus_mega"].items():
        lines.append(
            f"| {introduction} | {row['pairs']} | "
            f"{row['pairs_both_evaluable']} | "
            f"{_span(row['lag_days_diff'], 1)} | "
            f"{_span(row['passenger']['onset_attack_rate_diff'], 4)} | "
            f"{_span(row['crew']['onset_attack_rate_diff'], 4)} |",
        )
    return lines


def build_markdown(readout: dict[str, Any]) -> str:
    target = readout["target"]
    lines = [
        f"# {readout['campaign']} reconstruction table",
        "",
        f"Cells read: {readout['cells']} of {readout['expected_cells']}. "
        f"Engine: {', '.join(readout['engine_git_sha']) or 'n/a'}. "
        f"Audit defects: {len(readout['defects'])}.",
        "",
        "Model entries are median [5th, 95th percentile] over seeds. Peak "
        "days count from 0 = embarkation day "
        f"({target['day_labels'][0]}). Peaks and the lag use onsets "
        "excluding the declared seeds, on evaluable cells only.",
        "",
        "| Tier | Cells | Evaluable | Pax peak day | Crew peak day | "
        "Lag (crew - pax) | P(lag = target) | Pax onset AR | Crew onset AR | "
        "Target lag in central 90% |",
        "|---|---:|---:|---|---|---|---:|---|---|---|",
        f"| Empirical ({target['voyage']}) | | | "
        f"{target['peak_day_index']['passenger']} | "
        f"{target['peak_day_index']['crew']} | "
        f"{target['crew_minus_passenger_peak_lag_days']} | | "
        + " | ".join(
            _fmt(
                target["investigation_finals"][role]["cases"]
                / target["investigation_finals"][role]["denominator"], 4,
            )
            for role in ROLES
        ) + " | |",
    ]
    for tier, block in readout["tiers"].items():
        lines.append(
            f"| `{tier}` | {block['cells']} | {block['evaluable']} | "
            f"{_span(block['passenger']['peak_day'], 1)} | "
            f"{_span(block['crew']['peak_day'], 1)} | "
            f"{_span(block['lag_days'], 1)} | "
            f"{_fmt(block['lag_days']['p_equal_target'])} | "
            f"{_span(block['passenger']['onset_attack_rate'], 4)} | "
            f"{_span(block['crew']['onset_attack_rate'], 4)} | "
            f"{_fmt(block['lag_days']['target_in_central_90'])} |",
        )
    lines += [
        "",
        "Reported-case attack rates against the posting figures "
        "(cross-posting comparison only):",
        "",
        "| Tier | Pax reported AR | Crew reported AR | "
        "Embarkation declarations, max (pax / crew) | "
        "Reported by end of epoch 0, max (pax / crew) | "
        "Cells with SOP-007 / SOP-009 |",
        "|---|---|---|---|---|---|",
        "| Posting | " + " | ".join(
            _fmt(
                target["posting_figures"][role]["cases"]
                / target["posting_figures"][role]["denominator"], 4,
            )
            for role in ROLES
        ) + " | | | |",
    ]
    for tier, block in readout["tiers"].items():
        declared = block["embarkation_declarations_max"]
        zero = block["epoch_zero_reported_max"]
        sop = block["response_sop_cells"]
        lines.append(
            f"| `{tier}` | "
            f"{_span(block['passenger']['reported_attack_rate_vs_posting'], 4)} | "
            f"{_span(block['crew']['reported_attack_rate_vs_posting'], 4)} | "
            f"{declared['passenger']} / {declared['crew']} | "
            f"{zero['passenger']} / {zero['crew']} | "
            f"{sop['SOP-007']} / {sop['SOP-009']} |",
        )
    lines += [
        "",
        "Hull-dependent effective state and timing sensitivity "
        "(share of evaluable cells with the peak within one day of the "
        "target; Explorer onset totals over the first seven days):",
        "",
        "| Tier | Exposure cap requested / active | Rhythm layer active | "
        "Pax peak within 1 day | Crew peak within 1 day | "
        "Pax onsets, days 0-6 | Crew onsets, days 0-6 |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for tier, block in readout["tiers"].items():
        states = block["effective_state"]
        first_seven = [
            _span(block[role]["onset_total_first_seven_days"], 0)
            if "onset_total_first_seven_days" in block[role] else "n/a"
            for role in ROLES
        ]
        lines.append(
            f"| `{tier}` | "
            + ", ".join(
                f"{_fmt(s['exposure_cap_requested'])} / "
                f"{_fmt(s['exposure_cap_active'])}" for s in states
            ) + " | "
            + ", ".join(_fmt(s["rhythm_layer_active"]) for s in states)
            + f" | {_fmt(block['passenger']['peak_day']['p_within_one_day'])}"
            f" | {_fmt(block['crew']['peak_day']['p_within_one_day'])}"
            f" | {first_seven[0]} | {first_seven[1]} |",
        )
    lines += [
        "",
        "Embarkation declarations are the engine's pre-boarding report "
        "counter (crew only; the VSP 4.1.1.2 reportable clause does not "
        "cover passengers). Reports by the end of epoch 0 add sick-call "
        "reports made during that epoch.",
        "",
        "Explorer minus mega on shared seed labels. The two hulls differ in "
        "geometry and in complement, so a difference is attributed to the "
        "bundle, not to geometry:",
        "",
        "| Introduction | Pairs | Both evaluable | Lag diff | "
        "Pax peak-day diff | Crew peak-day diff | Pax onset AR diff | "
        "Crew onset AR diff |",
        "|---|---:|---:|---|---|---|---|---|",
    ]
    for introduction, block in readout["explorer_minus_mega"].items():
        lines.append(
            f"| {introduction} | {block['pairs']} | "
            f"{block['pairs_both_evaluable']} | "
            f"{_span(block['lag_days_diff'], 1)} | "
            f"{_span(block['passenger']['peak_day_diff'], 1)} | "
            f"{_span(block['crew']['peak_day_diff'], 1)} | "
            f"{_span(block['passenger']['onset_attack_rate_diff'], 4)} | "
            f"{_span(block['crew']['onset_attack_rate_diff'], 4)} |",
        )
    for arm, block in readout.get("arms", {}).items():
        lines += _arm_markdown(arm, block)
    if readout["defects"]:
        lines += ["", "Audit defects:", ""]
        lines += [
            f"- `{d['tier']}` seed {d['seed']}: {'; '.join(d['problems'])}"
            for d in readout["defects"]
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results", default="out/noro/explorer_reconstruction_01",
        help="directory holding the cell zips (searched recursively)",
    )
    parser.add_argument(
        "--out", default="telemetry_buffer/noro_explorer_reconstruction_01",
        help="directory for readout.json and reconstruction_table.md",
    )
    parser.add_argument(
        "--expect-sha", default=None,
        help="named reference commit; a cell from another engine is a defect",
    )
    args = parser.parse_args(argv)
    manifest = json.loads(
        (_CAMPAIGN_DIR / "manifest.json").read_text(encoding="utf-8"),
    )
    target = json.loads(
        (_CAMPAIGN_DIR / "empirical_target.json").read_text(encoding="utf-8"),
    )
    payloads = load_cells(confined(args.results))
    readout = build_readout(payloads, manifest, target, args.expect_sha)
    out_dir = confined(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    table = build_markdown(readout)
    confined(out_dir / "readout.json").write_text(
        json.dumps(readout, indent=1) + "\n", encoding="utf-8",
    )
    confined(out_dir / "reconstruction_table.md").write_text(
        table, encoding="utf-8",
    )
    print(table)
    return 1 if readout["defects"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
