"""Narrative report for boundary decision-model runs."""

from __future__ import annotations

import os
from typing import Any

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from simulation_utils.paths import validated_open


def _fmt(x: Any, digits: int = 4) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.{digits}g}"
    except (TypeError, ValueError):
        return str(x)


def write_report(
    out_dir: str,
    rows: list[dict[str, Any]],
    *,
    meta: dict[str, Any] | None = None,
    figure_paths: list[str] | None = None,
) -> str:
    """Write report.md summarizing policy comparison."""
    out = ensure_out_dir(out_dir)
    path = os.path.join(out, "report.md")
    meta = meta or {}
    lines: list[str] = [
        "# Pre-Boarding Wearable Decision Model Report",
        "",
        "This ancillary analysis estimates ROI of voluntary pre-boarding wearable",
        "data sharing. Mid-voyage wearables add little once VSP response exists;",
        "pre-boarding value comes from preventing infectious introductions.",
        "",
        "## Run metadata",
        "",
        f"- Scenarios completed: {meta.get('n_completed', len(rows))}",
        f"- Monte Carlo draws per scenario: {meta.get('n_mc', '—')}",
        f"- Seed: {meta.get('seed', '—')}",
        f"- Outbreak surface: `{meta.get('surface_source', '—')}`",
        "",
        "## Policy comparison (selected columns)",
        "",
        "| scenario_id | policy | π_inf | E[K_board] | P(VSP) | E[cost] | VoI/pax |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            "| {sid} | {pol} | {pi} | {kb} | {pv} | {cost} | {voi} |".format(
                sid=r.get("scenario_id"),
                pol=r.get("policy"),
                pi=_fmt(r.get("pi_inf")),
                kb=_fmt(r.get("expected_K_board")),
                pv=_fmt(r.get("expected_P_trigger")),
                cost=_fmt(r.get("expected_total_cost"), 6),
                voi=_fmt(r.get("value_of_information_per_pax")),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Compare **P2/P3/P4/P5** against **P0** on expected cost and P(VSP).",
            "- Positive VoI per passenger indicates the policy beats no pre-boarding sharing.",
            "- False-positive burden matters: see `false_positives_per_vsp_avoided`.",
            "",
        ]
    )
    if figure_paths:
        lines.append("## Figures")
        lines.append("")
        for fp in figure_paths:
            rel = os.path.relpath(fp, out)
            lines.append(f"- `{rel}`")
        lines.append("")

    text = "\n".join(lines)
    with validated_open(path, "w", allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        fh.write(text)
    return path
