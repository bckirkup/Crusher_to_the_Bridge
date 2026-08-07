"""HTML/Markdown report generation for campaign analysis bundles.

Usage::

    python3 -m picard_framework.analysis.report analysis/ [stan_fit/] --out report.html
"""

from __future__ import annotations

import argparse
import csv
import html
import os

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    read_json,
    safe_path,
)
from simulation_utils.paths import prepare_output_directory, validated_open


def _read_csv_rows(path: str) -> list[dict[str, str]]:
    if not os.path.isfile(path):
        return []
    with validated_open(path, allowed_roots=allowed_roots(), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _table_html(rows: list[dict[str, str]], columns: list[str] | None = None, limit: int = 20) -> str:
    if not rows:
        return "<p><em>No rows.</em></p>"
    cols = columns or list(rows[0].keys())
    parts = ["<table>", "<thead><tr>"]
    for c in cols:
        parts.append(f"<th>{html.escape(c)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows[:limit]:
        parts.append("<tr>")
        for c in cols:
            parts.append(f"<td>{html.escape(str(row.get(c, '')))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    if len(rows) > limit:
        parts.append(f"<p><em>Showing {limit} of {len(rows)} rows.</em></p>")
    return "".join(parts)


def _img_tag(analysis_dir: str, rel: str) -> str:
    path = os.path.join(analysis_dir, rel)
    if os.path.isfile(path):
        return f'<img src="{html.escape(rel)}" alt="{html.escape(rel)}" />'
    return ""


def build_report(
    analysis_dir: str,
    stan_fit_dir: str | None = None,
    *,
    out_path: str,
) -> str:
    """Write HTML (and sibling Markdown) report; return the HTML path."""
    analysis_dir = safe_path(analysis_dir)
    out_path = safe_path(out_path)
    parent = os.path.dirname(out_path)
    if parent:
        ensure_out_dir(parent)

    aggregate = {}
    agg_path = os.path.join(analysis_dir, "aggregate_metrics.json")
    if os.path.isfile(agg_path):
        aggregate = read_json(agg_path)

    run_rows = _read_csv_rows(os.path.join(analysis_dir, "run_summary.csv"))
    pairwise = _read_csv_rows(os.path.join(analysis_dir, "pairwise_deltas.csv"))

    posterior_bits: list[str] = []
    md_posterior: list[str] = []
    if stan_fit_dir:
        stan_fit_dir = safe_path(stan_fit_dir)
        post_dir = os.path.join(stan_fit_dir, "posterior")
        for name in (
            "dose_adj_calibration.csv",
            "platform_effects.csv",
            "surveillance_effects.csv",
            "vsp_threshold_effect.csv",
            "posterior_predictive_ar.csv",
        ):
            rows = _read_csv_rows(os.path.join(post_dir, name))
            if not rows:
                continue
            posterior_bits.append(f"<h3>{html.escape(name)}</h3>")
            posterior_bits.append(_table_html(rows, limit=30))
            md_posterior.append(f"### {name}\n")
            md_posterior.append(
                "| " + " | ".join(rows[0].keys()) + " |\n"
            )
            md_posterior.append(
                "| " + " | ".join("---" for _ in rows[0]) + " |\n"
            )
            for row in rows[:20]:
                md_posterior.append(
                    "| " + " | ".join(str(row.get(c, "")) for c in row) + " |\n"
                )
            md_posterior.append("\n")

    figures = [
        "figures/dose_response.png",
        "figures/surveillance_heatmap.png",
        "figures/vsp_threshold_sweep.png",
        "figures/epidemic_curves.png",
        "figures/pairwise_exact_match.png",
    ]
    fig_html = "".join(_img_tag(analysis_dir, rel) for rel in figures)

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Campaign Analysis Report</title>
<style>
body {{ font-family: Georgia, serif; margin: 2rem; max-width: 1100px; color: #222; }}
table {{ border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.3rem 0.5rem; }}
th {{ background: #f4f4f4; }}
img {{ max-width: 100%; margin: 0.5rem 0 1.5rem; }}
h1, h2, h3 {{ font-family: "Helvetica Neue", Arial, sans-serif; }}
code {{ background: #f0f0f0; padding: 0.1rem 0.3rem; }}
</style>
</head>
<body>
<h1>Campaign Analysis Report</h1>
<p>Runs: <strong>{html.escape(str(aggregate.get("n_runs", len(run_rows))))}</strong>
&nbsp;|&nbsp; Mean attack rate:
<strong>{html.escape(str(aggregate.get("mean_attack_rate")))}</strong>
&nbsp;|&nbsp; Outbreak rate:
<strong>{html.escape(str(aggregate.get("outbreak_rate")))}</strong></p>

<h2>Aggregate metrics</h2>
<pre>{html.escape(str(aggregate))}</pre>

<h2>Run summary (sample)</h2>
{_table_html(run_rows, columns=[
    "run_id", "platform_id", "pathogen", "dose_adjustment",
    "surveillance_strategy", "transport_engine", "attack_rate",
    "peak_prevalence", "detection_epoch",
], limit=25)}

<h2>Pairwise deltas (sample)</h2>
{_table_html(pairwise, limit=25)}

<h2>Figures</h2>
{fig_html or "<p><em>No figures found (install matplotlib analysis extra).</em></p>"}

<h2>Stan posterior summaries</h2>
{"".join(posterior_bits) if posterior_bits else "<p><em>No stan_fit directory provided or posterior files missing.</em></p>"}
</body>
</html>
"""

    with validated_open(
        out_path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
    ) as fh:
        fh.write(html_body)

    md_path = out_path.rsplit(".", 1)[0] + ".md" if "." in os.path.basename(out_path) else out_path + ".md"
    md_lines = [
        "# Campaign Analysis Report\n\n",
        f"- Runs: {aggregate.get('n_runs', len(run_rows))}\n",
        f"- Mean attack rate: {aggregate.get('mean_attack_rate')}\n",
        f"- Outbreak rate: {aggregate.get('outbreak_rate')}\n\n",
        "## Aggregate metrics\n\n",
        f"```\n{aggregate}\n```\n\n",
        "## Stan posterior summaries\n\n",
    ]
    md_lines.extend(md_posterior or ["_No posterior files._\n"])
    md_parent = os.path.dirname(md_path)
    if md_parent:
        prepare_output_directory(md_parent, allowed_roots=allowed_roots())
    with validated_open(
        md_path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
    ) as fh:
        fh.writelines(md_lines)

    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an HTML/Markdown campaign analysis report",
    )
    parser.add_argument("analysis_dir", help="Bundle directory (run_summary.csv, …)")
    parser.add_argument(
        "stan_fit_dir",
        nargs="?",
        default=None,
        help="Optional Stan fit output directory with posterior/",
    )
    parser.add_argument(
        "--out",
        default="report.html",
        help="Output HTML path (default: report.html)",
    )
    args = parser.parse_args(argv)
    path = build_report(args.analysis_dir, args.stan_fit_dir, out_path=args.out)
    print(f"Wrote report → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
