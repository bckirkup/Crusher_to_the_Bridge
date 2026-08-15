"""Narrative report for a sentinel fit directory.

The report is written for someone deciding whether to act on a port, so every
section that could be over-read carries its own caveat inline rather than in a
footnote: a reference-walker run says so in its first line, a pooled hazard that
is not separable from the week says so in its own row, and the wastewater
section states that the reads share the clinical incidence curve instead of
supplying a second, independent hazard.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from picard_framework.analysis.sentinel.artifacts import (
    MODE_FLEET,
    SentinelArtifacts,
    as_bool,
    as_float,
)
from simulation_utils.paths import validated_open

_REPORT_NAME = "report.md"
_NO_VALUE = "—"


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or value == "":
        return _NO_VALUE
    try:
        return f"{float(value):.{digits}g}"
    except (TypeError, ValueError):
        return str(value)


def _interval(summary: dict[str, Any], stem: str, digits: int = 3) -> str:
    """``mean (q05–q95)`` for the ``<stem>_mean``/``_q05``/``_q95`` convention."""
    mean = _fmt(summary.get(f"{stem}_mean"), digits)
    lo = summary.get(f"{stem}_q05")
    hi = summary.get(f"{stem}_q95")
    if lo is None or hi is None:
        return mean
    return f"{mean} ({_fmt(lo, digits)}–{_fmt(hi, digits)})"


def _header(artifacts: SentinelArtifacts) -> list[str]:
    scope = "fleet" if artifacts.mode == MODE_FLEET else "single voyage"
    lines = [
        "# Sentinel Port-Hazard Report",
        "",
        f"- Scope: {scope}",
        f"- Pathogen: `{artifacts.pathogen}`",
        f"- Sampler: `{artifacts.engine}`",
        f"- Fit status: `{artifacts.status.get('status', 'unknown')}`",
        f"- Clinical cases in the fit: {artifacts.meta.get('n_cases', _NO_VALUE)}",
        f"- Right-censoring corrected: {artifacts.meta.get('censoring_corrected', _NO_VALUE)}",
        "",
    ]
    if artifacts.is_reference_walker:
        lines.extend(
            [
                "> **Reference walker, not NUTS.** These draws come from the numpy",
                "> random-walk Metropolis sampler used when CmdStan is unavailable",
                "> (or from the committed fixture posterior it generated). Point",
                "> estimates are indicative and the intervals are not calibrated;",
                "> do not quote them as posterior credible intervals.",
                "",
            ],
        )
    return lines


def _hazard_table(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Ranked pooled hazards per person-hour ashore, with the confounding flag."""
    lines = [
        "## Port introduction hazards",
        "",
        "Hazard is per person-hour ashore, so a port is not penalised for the",
        "size of the ships that call there. `confounded` marks a port whose",
        "hazard is not separable from its week's fleet-wide effect.",
        "",
        "| port | hazard (90% CrI) | attributed cases | share | visits | person-hours ashore | confounded |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    ordered = sorted(rows, key=lambda r: -as_float(r.get("hazard_mean"), 0.0))
    for row in ordered:
        interval = (
            f"{_fmt(row.get('hazard_mean'))} "
            f"({_fmt(row.get('hazard_q05'))}–{_fmt(row.get('hazard_q95'))})"
        )
        lines.append(
            "| {port} | {hz} | {cases} | {share} | {visits} | {hours} | {conf} |".format(
                port=row.get("port_id", _NO_VALUE),
                hz=interval,
                cases=_fmt(row.get("n_attributed_cases")),
                share=_fmt(row.get("attribution_share")),
                visits=row.get("n_visits", _NO_VALUE),
                hours=_fmt(row.get("person_hours_ashore"), 6),
                conf="yes" if as_bool(row.get("fleet_time_confounded")) else "no",
            ),
        )
    lines.append("")
    return lines


def _visit_section(artifacts: SentinelArtifacts) -> list[str]:
    """Per-visit hazards — the number to quote for one specific port call."""
    if artifacts.mode != MODE_FLEET or not artifacts.visit_rows:
        return []
    lines = [
        "## Per-visit hazards",
        "",
        "The pooled port hazard above is identified only up to the (uncentered)",
        "fleet-time level, so quote the per-visit hazard for a specific call.",
        "",
        "| visit | port | week | hazard (90% CrI) | attributed cases |",
        "|---|---|---|---:|---:|",
    ]
    for row in artifacts.visit_rows:
        lines.append(
            "| {key} | {port} | {week} | {hz} ({lo}–{hi}) | {cases} |".format(
                key=row.get("visit_key", _NO_VALUE),
                port=row.get("port_id", _NO_VALUE),
                week=row.get("week", _NO_VALUE),
                hz=_fmt(row.get("hazard_mean")),
                lo=_fmt(row.get("hazard_q05")),
                hi=_fmt(row.get("hazard_q95")),
                cases=_fmt(row.get("n_attributed_cases")),
            ),
        )
    lines.append("")
    return lines


def _fleet_time_section(artifacts: SentinelArtifacts) -> list[str]:
    """Fleet-wide weekly effect — the rival explanation for a hot port."""
    if not artifacts.week_rows:
        return []
    lines = [
        "## Fleet-time effect",
        "",
        "A week-wide shift is the rival explanation for a hot port: a multiplier",
        "far from 1.0 means the whole fleet moved that week, not one call.",
        "",
        "| week | log effect (90% CrI) | hazard multiplier |",
        "|---|---:|---:|",
    ]
    for row in artifacts.week_rows:
        lines.append(
            "| {week} | {mean} ({lo}–{hi}) | {mult} |".format(
                week=row.get("week", _NO_VALUE),
                mean=_fmt(row.get("log_effect_mean")),
                lo=_fmt(row.get("log_effect_q05")),
                hi=_fmt(row.get("log_effect_q95")),
                mult=_fmt(row.get("hazard_multiplier_mean")),
            ),
        )
    lines.append("")
    return lines


def _ship_rows(ships: Sequence[dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "| ship | aboard hazard / person-hour | R_onboard (90% CrI) |",
        "|---|---:|---:|",
    ]
    for ship in ships:
        lines.append(
            "| {sid} | {lam} | {r} |".format(
                sid=ship.get("ship_id", _NO_VALUE),
                lam=_fmt(ship.get("lambda_aboard_mean")),
                r=_interval(dict(ship), "r_onboard"),
            ),
        )
    return lines


def _onboard_section(artifacts: SentinelArtifacts) -> list[str]:
    """Imported vs onboard split, with R_onboard sampled rather than asserted."""
    onboard = artifacts.onboard
    if not onboard:
        return []
    lines = [
        "## Imported versus onboard",
        "",
        f"- Import share: {_interval(onboard, 'import_share')}",
        f"- Aboard-baseline cases (mean): {_fmt(onboard.get('aboard_cases_mean'))}",
        f"- Secondary cases (mean): {_fmt(onboard.get('secondary_cases_mean'))}",
    ]
    ships = onboard.get("ships")
    if isinstance(ships, list) and ships:
        lines.extend(_ship_rows(ships))
    elif onboard.get("r_onboard_mean") is not None:
        # A single-voyage fit has one ship, so it reports R_onboard directly.
        lines.append(f"- R_onboard: {_interval(onboard, 'r_onboard')}")
    lines.append("")
    return lines


def _crew_section(artifacts: SentinelArtifacts) -> list[str]:
    """Crew shore leave and repeat exposure — direction, not magnitude."""
    crew = artifacts.crew
    if not crew:
        return []
    return [
        "## Crew exposure",
        "",
        f"- Crew:passenger hazard ratio: {_interval(crew, 'crew_hazard_ratio')}",
        f"- Repeat-call hazard ratio: {_interval(crew, 'repeat_hazard_ratio')}",
        "",
        "The repeat-call ratio supports a directional claim only; with the",
        "voyage counts a fleet fit typically has, its magnitude is not",
        "identified.",
        "",
    ]


def _wastewater_section(artifacts: SentinelArtifacts) -> list[str]:
    """Wastewater evidence, stated as a second view of the same incidence."""
    ww = artifacts.wastewater
    if not ww:
        return []
    lines = ["## Wastewater channel", ""]
    if not as_bool(ww.get("enabled")):
        lines.extend(["Disabled for this fit; clinical onsets only.", ""])
        return lines
    if not as_bool(ww.get("fitted")):
        lines.extend(
            [
                "Enabled but not fitted — no usable samples were present, so no",
                "slope or concentration is reported rather than a prior echoed",
                "back as a result.",
                "",
            ],
        )
        return lines
    lines.extend(
        [
            "Reads observe the **same latent incidence curve** as the clinical",
            "onsets through the shedding convolution; they never get a port",
            "hazard of their own, so a wastewater spike cannot by itself",
            "implicate a port.",
            "",
            f"- Pooled samples: {ww.get('n_pooled_samples', _NO_VALUE)}"
            f" (from {ww.get('n_raw_samples', _NO_VALUE)} raw)",
            f"- Shedding-to-read slope: {_interval(ww, 'slope')}",
            f"- Concentration scale (mean): {_fmt(ww.get('concentration_mean'), 6)}",
            f"- Residence lag (epochs): {ww.get('residence_lag_epochs', _NO_VALUE)}",
            f"- Log-likelihood, clinical: {_fmt(ww.get('loglik_clinical'), 6)}",
            f"- Log-likelihood, wastewater: {_fmt(ww.get('loglik_wastewater'), 6)}",
            "",
            "The two log-likelihoods are reported separately so the weight each",
            "channel carries is visible instead of pooled into one number.",
            "",
        ],
    )
    return lines


def _figure_section(out: str, figure_paths: Sequence[str]) -> list[str]:
    if not figure_paths:
        return []
    lines = ["## Figures", ""]
    for path in figure_paths:
        rel = os.path.relpath(path, out).replace(os.sep, "/")
        lines.append(f"![{os.path.basename(rel)}]({rel})")
    lines.append("")
    return lines


def write_report(
    out_dir: str,
    artifacts: SentinelArtifacts,
    *,
    figure_paths: Sequence[str] | None = None,
) -> str:
    """Write ``report.md`` for a loaded fit; returns the path written."""
    out = ensure_out_dir(out_dir)
    path = os.path.join(out, _REPORT_NAME)
    lines: list[str] = []
    lines.extend(_header(artifacts))
    lines.extend(_hazard_table(artifacts.port_rows))
    lines.extend(_visit_section(artifacts))
    lines.extend(_fleet_time_section(artifacts))
    lines.extend(_onboard_section(artifacts))
    lines.extend(_crew_section(artifacts))
    lines.extend(_wastewater_section(artifacts))
    lines.extend(_figure_section(out, figure_paths or ()))
    with validated_open(
        path, "w", allowed_roots=allowed_roots(), encoding="utf-8",
    ) as fh:
        fh.write("\n".join(lines) + "\n")
    return path
