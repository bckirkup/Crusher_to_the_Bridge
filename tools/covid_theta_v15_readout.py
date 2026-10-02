#!/usr/bin/env python3
"""COVID-THETA-V15 stage-1 readout — the v14 lattice verbatim under the
repaired presentation draw (once_per_course, shipped default since PR #825).

Thin wrapper over the parameterized tools/covid_theta_v14_readout engine.
The v15-specific content is entirely in its arguments: the screen arm
resolves to the design's declared baseline (once_per_course), and the
delivery echoes the cell audit enforces are this screen's two resolved
mechanisms — presentation_draw_mode == once_per_course and
hand_reservoir_mode == hygiene_cycle (both shipped defaults, declared in
covid_theta_screen_v15_design.json's audit_invariants block). Cells pair
seed-for-seed against the v14 prefix, the pre-repair surface of record.

Usage:
    python3 tools/covid_theta_v15_readout.py \
        --design picard_framework/runs/covid_theta_screen_v15_design.json \
        --s3-prefix s3://<bucket>/campaign/covid_theta_screen_v15/<sha>/ \
        --parent-design picard_framework/runs/covid_theta_screen_v14_design.json \
        --parent-s3-prefix s3://<bucket>/campaign/covid_theta_screen_v14/02740187/ \
        --out telemetry_buffer/covid_theta_v15_readout.json \
        --surface-out docs/covid/covid_theta_screen_v15_surface.csv \
        --pairs-out docs/covid/covid_theta_screen_v15_pairs.csv
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools import covid_theta_v14_readout as _v14  # noqa: E402

# The v15 audit contract verbatim from the design's audit_invariants block:
# the resolved presentation draw must be the repaired once-per-course spend
# and the hand line must still resolve hygiene_cycle (both shipped
# defaults; a pathogen_overrides arm would echo its own declared mode).
_AUDIT_ECHOES = (
    "presentation_draw_mode=once_per_course",
    "hand_reservoir_mode=hygiene_cycle",
)


def main(argv: list[str] | None = None) -> int:
    """Add the v15 audit echoes unless the caller declared their own."""
    args = list(argv) if argv is not None else sys.argv[1:]
    if "--audit-echo" not in args:
        args += [flag for echo in _AUDIT_ECHOES
                 for flag in ("--audit-echo", echo)]
    return _v14.main(args)


if __name__ == "__main__":
    sys.exit(main())
