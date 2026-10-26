"""``scripts/campaign analysis <operation>`` — canonical analysis namespace.

All eleven operations, their argv and their exit codes are read from
``contracts/CANONICAL_INTERFACE.json`` (``public_cli.operations``). Ticket D0
implements the two strictly-offline operations:

- ``plan`` — offline scope reconciliation + blocking-input checklist +
  null-valued request template.
- ``validate --request-kind execution|bootstrap|query`` — schema and
  semantic request validation.

Every other registered operation is present in the namespace and exits
nonzero with a ``NOT_YET_IMPLEMENTED`` status until its phased ticket lands.
The analysis namespace never invokes the campaign simulation launcher.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .._io import ensure_out_dir, safe_path, write_json
from . import contracts
from .plan import run_plan
from .validate import run_validate


def _out_root(out_dir: Path, operation: str) -> str | None:
    """Confine ``--out`` to the invocation directory; None + print on escape."""
    try:
        return ensure_out_dir(str(out_dir))
    except SystemExit as exc:
        print(json.dumps({
            "status": "INVALID_CONTRACT",
            "operation": operation,
            "error": str(exc),
        }))
        return None


def _extra_kwargs(metavar: str) -> dict:
    if "|" in metavar:
        return {"choices": metavar.split("|")}
    return {"metavar": metavar}


def build_parser(operations: dict) -> argparse.ArgumentParser:
    """Build the analysis subparser from CANONICAL_INTERFACE argv."""
    parser = argparse.ArgumentParser(
        prog="scripts/campaign analysis",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="operation", required=True)
    for name, spec in operations.items():
        op = sub.add_parser(
            name,
            help=f"mode={spec['mode']} status={spec['status']}",
        )
        op.add_argument("--request", metavar="FILE", required=True, type=Path)
        op.add_argument("--out", metavar="DIR", required=True, type=Path)
        extra = spec.get("extra_argv", [])
        for flag, metavar in zip(extra[::2], extra[1::2], strict=True):
            op.add_argument(flag, required=True, **_extra_kwargs(metavar))
    return parser


def _not_implemented(args: argparse.Namespace, spec: dict) -> int:
    status = {
        "status": "NOT_YET_IMPLEMENTED",
        "operation": args.operation,
        "mode": spec.get("mode"),
        "additional_required_inputs": spec.get("additional_required_inputs", []),
        "reason": "operation is registered by CANONICAL_INTERFACE.json; "
                  "implementation lands in a later phased ticket (D1-D8)",
    }
    out_root = _out_root(args.out, args.operation)
    if out_root is None:
        return contracts.EXIT_INVALID_CONTRACT
    write_json(os.path.join(out_root, "status.json"), status)
    print(json.dumps(status))
    return contracts.NOT_IMPLEMENTED_EXIT


def _plan(args: argparse.Namespace) -> int:
    try:
        request = safe_path(args.request)
    except SystemExit as exc:
        print(json.dumps({
            "status": "INVALID_CONTRACT",
            "operation": "plan",
            "error": str(exc),
        }))
        return contracts.EXIT_INVALID_CONTRACT
    if not os.path.isfile(request):
        print(json.dumps({
            "status": "INVALID_CONTRACT",
            "operation": "plan",
            "error": f"request file not found: {args.request}",
        }))
        return contracts.EXIT_INVALID_CONTRACT
    return run_plan(Path(request), args.out)


def main(argv: list[str] | None = None) -> int:
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    operations = canonical["public_cli"]["operations"]
    args = build_parser(operations).parse_args(argv)
    if args.operation == "plan":
        return _plan(args)
    if args.operation == "validate":
        return run_validate(args.request, args.request_kind, args.out)
    return _not_implemented(args, operations[args.operation])
