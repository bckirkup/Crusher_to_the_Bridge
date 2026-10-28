"""``scripts/campaign analysis <operation>`` — canonical analysis namespace.

All eleven operations, their argv and their exit codes are read from
``contracts/CANONICAL_INTERFACE.json`` (``public_cli.operations``). Ticket D0
implements the two strictly-offline operations:

- ``plan`` — offline scope reconciliation + blocking-input checklist +
  null-valued request template.
- ``validate --request-kind execution|bootstrap|query`` — schema and
  semantic request validation.

Ticket D4 wires the return-path operations — ``status``, ``resume``,
``query``, ``collect`` and ``acknowledge`` — in
``campaign_reducer.return_path``. Ticket D5 wires ``inventory`` — the
bounded metadata cold-inventory — in ``campaign_reducer.inventory``.
Ticket D6 wires ``quote`` (offline measured-evidence pricing) in
``campaign_reducer.quote`` and the pilot leg of ``submit`` in
``campaign_reducer.submit``.
Every other registered operation is present in the namespace and exits
nonzero with a ``NOT_YET_IMPLEMENTED`` status until its phased ticket
lands.
The analysis namespace never invokes the campaign simulation launcher.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from simulation_utils.paths import confine_to_base, prepare_output_directory

from .._io import cwd_root, write_json
from . import contracts, inventory, quote, return_path, submit
from .plan import run_plan
from .validate import run_validate


def _refuse_escalation(operation: str, exc: ValueError) -> int:
    print(json.dumps({
        "status": "INVALID_CONTRACT",
        "operation": operation,
        "error": str(exc),
    }))
    return contracts.EXIT_INVALID_CONTRACT


def _out_root(out_dir: Path, operation: str) -> str | None:
    """Confine ``--out`` to the invocation directory; None + print on escape."""
    try:
        safe = confine_to_base(cwd_root(), str(out_dir))
        return prepare_output_directory(safe, allowed_roots=(cwd_root(),))
    except ValueError as exc:
        _refuse_escalation(operation, exc)
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
        if name in return_path.OPS:
            optional = return_path.OPTIONAL_FLAGS
        elif name == "inventory":
            optional = inventory.OPTIONAL_FLAGS
        elif name == "submit":
            optional = submit.OPTIONAL_FLAGS
        elif name == "quote":
            optional = quote.OPTIONAL_FLAGS
        else:
            optional = ()
        for flag in optional:
            op.add_argument(flag, default="")
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
        request = confine_to_base(cwd_root(), str(args.request))
    except ValueError as exc:
        return _refuse_escalation("plan", exc)
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
    if args.operation in return_path.OPS:
        return return_path.run(args)
    if args.operation == "inventory":
        return inventory.run(args)
    if args.operation == "quote":
        return quote.run(args)
    if args.operation == "submit":
        return submit.run(args)
    return _not_implemented(args, operations[args.operation])
