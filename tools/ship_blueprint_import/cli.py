"""CLI for naval general-plan → Crusher ship-class import."""

from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from simulation_utils.paths import resolve_repo_path  # noqa: E402


def _roots() -> tuple[str, ...]:
    return (_REPO_ROOT,)


def _resolve(path: str) -> str:
    return resolve_repo_path(_REPO_ROOT, path)


def cmd_ingest(args: argparse.Namespace) -> int:
    from tools.ship_blueprint_import.ingest import ingest

    workdir = _resolve(args.workdir)
    input_path = _resolve(args.input)
    manifest = ingest(
        input_path=input_path,
        workdir=workdir,
        dpi=float(args.dpi),
        allowed_roots=_roots(),
    )
    print(f"Ingested {len(manifest.get('pages', []))} page(s) → {workdir}")
    print(f"  manifest: {os.path.join(workdir, 'pages_manifest.json')}")
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    from tools.ship_blueprint_import.digest import digest_workdir

    workdir = _resolve(args.workdir)
    fixture = _resolve(args.fixture) if args.fixture else None
    digest = digest_workdir(
        workdir=workdir,
        provider_name=args.provider,
        model=args.model,
        hint=args.hint or "",
        fixture_path=fixture,
        allowed_roots=_roots(),
    )
    print(
        f"Digest ({args.provider}): platform={digest.platform_id} "
        f"zones={len(digest.zones)} → {os.path.join(workdir, 'ship_digest.json')}"
    )
    print(f"  draft overlays: {os.path.join(workdir, 'overlays')}")
    print(
        "  Edit overlays in GIMP/Krita/Inkscape, save as page_NN_approved.svg, "
        "then run synthesize."
    )
    return 0


def cmd_synthesize(args: argparse.Namespace) -> int:
    from tools.ship_blueprint_import.synthesize import synthesize

    workdir = _resolve(args.workdir)
    output = _resolve(args.output)
    result = synthesize(
        workdir=workdir,
        output_dir=output,
        platform_id=args.platform_id,
        allowed_roots=_roots(),
        copy_graphics=not args.no_graphics,
        require_approved=bool(args.require_approved),
    )
    print(
        f"Synthesized {result['zone_count']} zones → {result['output_dir']}\n"
        f"  {result['spatial_layout']}\n"
        f"  {result['air_flow_paths']}"
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from tools.ship_blueprint_import.validate import validate_platform

    platform_dir = _resolve(args.platform_dir)
    result = validate_platform(
        platform_dir,
        allowed_roots=_roots(),
        contam_bootstrap=bool(args.contam_bootstrap),
    )
    if result["schema_errors"]:
        print("Schema errors:")
        for err in result["schema_errors"]:
            print(f"  - {err}")
    print("Sanity checker:")
    print(result["sanity_report"] or "  (no findings)")
    if result["contam_bootstrap"]:
        print(result["contam_bootstrap"])
    if result["ok"]:
        print("VALIDATION PASSED")
        return 0
    print("VALIDATION FAILED")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.ship_blueprint_import",
        description=(
            "Import naval general-arrangement drawings into Crusher ship classes "
            "(ingest → digest → SVG edit → synthesize → validate)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_in = sub.add_parser("ingest", help="Rasterize PDF/images into workdir pages")
    p_in.add_argument("--input", "-i", required=True, help="PDF file or image directory")
    p_in.add_argument("--workdir", "-w", required=True, help="Working directory under repo")
    p_in.add_argument("--dpi", type=float, default=150.0)
    p_in.set_defaults(func=cmd_ingest)

    p_dg = sub.add_parser("digest", help="Vision LLM / mock digest + draft SVG overlays")
    p_dg.add_argument("--workdir", "-w", required=True)
    p_dg.add_argument(
        "--provider",
        default="mock",
        help="mock|gemini|openai_compat|anthropic (default: mock)",
    )
    p_dg.add_argument("--model", default=None, help="Provider model override")
    p_dg.add_argument("--hint", default="", help="Operator hint appended to prompt")
    p_dg.add_argument(
        "--fixture",
        default=None,
        help="Optional ShipDigest JSON for mock provider",
    )
    p_dg.set_defaults(func=cmd_digest)

    p_sy = sub.add_parser(
        "synthesize",
        help="Deterministic SVG+digest → spatial_layout + air_flow_paths",
    )
    p_sy.add_argument("--workdir", "-w", required=True)
    p_sy.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output platform directory (e.g. data/platforms/my_ship)",
    )
    p_sy.add_argument("--platform-id", default=None, help="Override digest platform_id")
    p_sy.add_argument(
        "--require-approved",
        action="store_true",
        help="Fail unless page_*_approved.svg overlays exist",
    )
    p_sy.add_argument(
        "--no-graphics",
        action="store_true",
        help="Do not copy plan overview into graphics/",
    )
    p_sy.set_defaults(func=cmd_synthesize)

    p_va = sub.add_parser("validate", help="Schema + sanity_checker gate")
    p_va.add_argument("--platform-dir", "-p", required=True)
    p_va.add_argument(
        "--contam-bootstrap",
        action="store_true",
        help="After pass, fiction-bootstrap Contam PRJ via generate_platform_contam_prj.py",
    )
    p_va.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
