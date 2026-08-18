"""CLI: fit a sentinel port-hazard model, then draw its figures and report.

This is the operator entry point over the pieces the earlier sentinel work put
in place. It does three things the individual fit runners deliberately do not:
it chooses fleet or single-voyage mode from the inputs given, it renders figures
and a narrative report from whatever the fit wrote, and with ``--from-fit`` it
does the rendering alone — a fit is expensive, a plot is not, and a report drawn
from the committed CSVs can never disagree with the numbers a reader was handed.

``--smoke`` stages the bundled example fleet into the output directory and runs
the numpy reference walker, so CI exercises manifest → hazards → figures →
report with no CmdStan present. The staging is why smoke works from any working
directory: analysis paths are confined to the CWD, and the fixtures live in the
installed package.
"""

from __future__ import annotations

import argparse
import json
import os
from importlib import resources
from typing import Any

from picard_framework.analysis._fit_exit import (
    POSTERIOR_STATUSES,
    add_allow_skipped_argument,
    fit_exit_code,
)
from picard_framework.analysis._io import allowed_roots, ensure_out_dir, safe_path
from picard_framework.analysis.sentinel.artifacts import load_fit_artifacts
from picard_framework.analysis.sentinel.figures import (
    have_matplotlib,
    write_sentinel_figures,
)
from picard_framework.analysis.sentinel.report import write_report
from picard_framework.analysis.stan._sampler_options import SamplerOptions
from picard_framework.analysis.stan.fit_sentinel_attribution import (
    fit_sentinel_attribution,
)
from picard_framework.analysis.stan.fit_sentinel_fleet import fit_sentinel_fleet
from simulation_utils.paths import validated_open

_PACKAGE = "picard_framework.analysis.sentinel"
_SMOKE_MANIFEST = "example_fleet.json"
_SMOKE_INPUTS = "inputs"
_OK_STATUSES = POSTERIOR_STATUSES


def _packaged_data(name: str) -> str:
    """Text of a bundled fixture, confined to the package data directory.

    The names come from the manifest's own entries, so they are confined rather
    than trusted: a manifest is data, and a fixture that could name
    ``../../secrets`` would be a path-traversal sink.
    """
    with resources.as_file(resources.files(_PACKAGE) / "data") as data_dir:
        root = str(data_dir)
        with validated_open(
            os.path.join(root, name),
            allowed_roots=(root,),
            encoding="utf-8",
        ) as fh:
            return fh.read()


def stage_smoke_inputs(out_dir: str) -> str:
    """Copy the bundled example fleet under ``out_dir``; return the manifest path.

    The fixtures are copied rather than read in place because analysis paths are
    confined to the working directory, and an installed package normally is not
    under it.
    """
    dest = ensure_out_dir(os.path.join(out_dir, _SMOKE_INPUTS))
    manifest_text = _packaged_data(_SMOKE_MANIFEST)
    names = {_SMOKE_MANIFEST}
    for entry in json.loads(manifest_text).get("voyages", []):
        for field in ("itinerary", "observations"):
            value = entry.get(field)
            if isinstance(value, str) and value:
                names.add(value)
    for name in sorted(names):
        target = os.path.join(dest, name)
        with validated_open(
            target, "w", allowed_roots=allowed_roots(), encoding="utf-8",
        ) as fh:
            fh.write(_packaged_data(name))
    return os.path.join(dest, _SMOKE_MANIFEST)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m picard_framework.analysis.sentinel",
        description=(
            "Fit sentinel port-introduction hazards and write figures + report"
        ),
    )
    p.add_argument(
        "--manifest",
        default=None,
        help="fleet manifest listing itinerary/observation pairs (fleet mode)",
    )
    p.add_argument(
        "--itinerary", default=None, help="single-voyage itinerary JSON",
    )
    p.add_argument(
        "--observations", default=None, help="single-voyage observation bundle JSON",
    )
    p.add_argument(
        "--from-fit",
        default=None,
        metavar="DIR",
        help="redraw figures and report from an existing fit directory; no sampling",
    )
    p.add_argument("--out", default="sentinel_run", help="output directory under CWD")
    p.add_argument(
        "--pathogen",
        default=None,
        help="delay-catalog key; defaults to the catalog's default_pathogen",
    )
    p.add_argument("--reporting", type=float, default=1.0)
    p.add_argument("--care-seeking", type=float, default=1.0)
    p.add_argument("--testing", type=float, default=1.0)
    p.add_argument(
        "--engine",
        choices=("auto", "stan", "numpy"),
        default="auto",
        help="auto uses CmdStan when installed and the numpy walker otherwise",
    )
    p.add_argument("--chains", type=int, default=None)
    p.add_argument("--iter-sampling", type=int, default=None)
    p.add_argument("--iter-warmup", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--show-progress", action=argparse.BooleanOptionalAction, default=None,
    )
    p.add_argument(
        "--wastewater",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "include wastewater reads as a second observation of the incidence "
            "curve; --no-wastewater is the clinical-only baseline"
        ),
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="run the bundled example fleet with the numpy walker (no CmdStan)",
    )
    p.add_argument(
        "--no-figures", action="store_true", help="write the report without figures",
    )
    add_allow_skipped_argument(p)
    return p


def _sampler_from_args(args: argparse.Namespace) -> SamplerOptions:
    """Sampler knobs, leaving anything the caller did not set at its default.

    ``--smoke`` does not shrink the draw counts: the smoke path is the reference
    walker, whose fixture-scale draw count is fixed inside the fit runner, and a
    knob that silently does nothing is worse than no knob.
    """
    base = SamplerOptions()
    return SamplerOptions(
        chains=base.chains if args.chains is None else args.chains,
        iter_sampling=(
            base.iter_sampling if args.iter_sampling is None else args.iter_sampling
        ),
        iter_warmup=(
            base.iter_warmup if args.iter_warmup is None else args.iter_warmup
        ),
        seed=base.seed if args.seed is None else args.seed,
        show_progress=(
            base.show_progress if args.show_progress is None else args.show_progress
        ),
    )


def _fit_fleet(
    args: argparse.Namespace, out_dir: str, manifest: str,
) -> dict[str, Any]:
    return fit_sentinel_fleet(
        manifest,
        out_dir,
        pathogen=args.pathogen,
        reporting=args.reporting,
        care_seeking=args.care_seeking,
        testing=args.testing,
        engine="numpy" if args.smoke else args.engine,
        sampler=_sampler_from_args(args),
        smoke=args.smoke,
        wastewater=args.wastewater,
    )


def _fit_single(args: argparse.Namespace, out_dir: str) -> dict[str, Any]:
    return fit_sentinel_attribution(
        safe_path(args.itinerary),
        safe_path(args.observations),
        out_dir,
        pathogen=args.pathogen,
        reporting=args.reporting,
        care_seeking=args.care_seeking,
        testing=args.testing,
        sampler=_sampler_from_args(args),
        smoke=args.smoke,
    )


def run_fit(args: argparse.Namespace, out_dir: str) -> dict[str, Any]:
    """Fit in fleet mode unless a single voyage was named explicitly.

    ``--smoke`` alone means the bundled fleet; ``--smoke`` with an itinerary and
    observations is a single-voyage smoke off the committed fixture posterior.
    """
    single = bool(args.itinerary and args.observations)
    if args.manifest or (args.smoke and not single):
        manifest = (
            safe_path(args.manifest) if args.manifest else stage_smoke_inputs(out_dir)
        )
        return _fit_fleet(args, out_dir, manifest)
    return _fit_single(args, out_dir)


def render(out_dir: str, fit_dir: str, *, figures: bool = True) -> tuple[list[str], str]:
    """Load a fit directory and write its figures and report."""
    artifacts = load_fit_artifacts(fit_dir)
    figure_paths = write_sentinel_figures(out_dir, artifacts) if figures else []
    report_path = write_report(out_dir, artifacts, figure_paths=figure_paths)
    return figure_paths, report_path


def _require_inputs(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.from_fit or args.manifest or args.smoke:
        return
    if not (args.itinerary and args.observations):
        parser.error(
            "give --manifest (fleet), --itinerary with --observations "
            "(single voyage), --from-fit (render only), or --smoke",
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _require_inputs(parser, args)

    out_dir = ensure_out_dir(args.out)
    if args.from_fit:
        fit_dir = safe_path(args.from_fit)
    else:
        status = run_fit(args, out_dir)
        label = str(status.get("status"))
        print(f"fit: {label}", flush=True)
        if label not in _OK_STATUSES:
            # A skipped fit (no CmdStan, no --smoke) wrote no hazards; reporting
            # on it would mean inventing them.
            return fit_exit_code(status, allow_skipped=args.allow_skipped_fit)
        fit_dir = out_dir

    want_figures = not args.no_figures
    if want_figures and not have_matplotlib():
        print("matplotlib unavailable; writing the report without figures")
        want_figures = False
    figure_paths, report_path = render(out_dir, fit_dir, figures=want_figures)
    print(f"report: {report_path}", flush=True)
    for path in figure_paths:
        print(f"figure: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
