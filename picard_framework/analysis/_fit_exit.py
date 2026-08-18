"""One exit-code rule for every fit CLI: no posterior is not success.

A fit that reports ``skipped`` — CmdStan absent, nothing sampled — used to exit
0, which is indistinguishable from a fit that worked. That is tolerable when a
human is reading the console and fatal in a campaign: a shard array would come
back all-green with no posteriors in it, and the missing rungs would only surface
downstream as empty hazard tables.

So ``skipped`` exits ``EXIT_NO_POSTERIOR`` (2), kept distinct from a real failure
(1) because the operator response differs: install a toolchain, versus debug a
model. A caller that genuinely wants to exercise the data path without a sampler
says so with ``--allow-skipped-fit``.
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, Mapping

# Statuses that mean a posterior was written: a real fit, the reference walker's
# short run, or a committed fixture summarized in its place.
POSTERIOR_STATUSES = frozenset({"ok", "smoke", "fixture"})

SKIPPED_STATUS = "skipped"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NO_POSTERIOR = 2


def fit_exit_code(
    status: Mapping[str, object],
    *,
    allow_skipped: bool = False,
) -> int:
    """Map a fit status payload onto a process exit code."""
    label = str(status.get("status") or "missing")
    if label in POSTERIOR_STATUSES:
        return EXIT_OK
    reason = str(status.get("reason") or "unknown")
    if label == SKIPPED_STATUS:
        if allow_skipped:
            print(f"skipped ({reason}); tolerated by --allow-skipped-fit", flush=True)
            return EXIT_OK
        print(
            f"no posterior was written: {reason}. Pass --engine numpy to sample "
            "with the reference walker, or --allow-skipped-fit to accept this.",
            file=sys.stderr,
        )
        return EXIT_NO_POSTERIOR
    print(f"fit {label}: {reason}", file=sys.stderr)
    return EXIT_FAILED


def worst_exit_code(codes: Iterable[int]) -> int:
    """Collapse per-unit codes, keeping a real failure visible over a skip."""
    seen = set(codes)
    if EXIT_FAILED in seen:
        return EXIT_FAILED
    return EXIT_NO_POSTERIOR if EXIT_NO_POSTERIOR in seen else EXIT_OK


def add_allow_skipped_argument(parser: argparse.ArgumentParser) -> None:
    """Attach ``--allow-skipped-fit`` to a fit CLI's parser."""
    parser.add_argument(
        "--allow-skipped-fit",
        action="store_true",
        help=(
            "exit 0 when no posterior was produced (CmdStan absent). Off by "
            "default so a campaign cannot report success without a fit"
        ),
    )
