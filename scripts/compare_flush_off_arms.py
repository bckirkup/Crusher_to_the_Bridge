#!/usr/bin/env python3
"""Does one stage's disabled-path arm reproduce another's on the shared seeds?

`off` is re-run in every stage rather than re-read, which only buys anything if
the re-run is checked against its predecessor. The engine tree is unchanged
between the two stages this compares, so voyage-for-voyage equality is the
expectation, and any inequality is a defect in the image, the manifest or the
seeding rather than a result: a silently mis-built arm otherwise produces a
perfectly plausible-looking contrast.

Compared per (tier, seed) present in both: final cumulative ever-infected,
the epoch-0 count, posting, and the flush witness (which must be zero in both,
because `off` is the disabled path and not the sweep evaluated at zero).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from read_flush_sweep import load_arm  # noqa: E402

FIELDS = ["ever", "epoch0", "posted", "flush_events", "flush_emitted"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="s4")
    parser.add_argument("--against", default="s3")
    parser.add_argument("--archives", type=Path, default=None)
    args = parser.parse_args()

    root = args.archives or Path("~/campaign_results").expanduser()
    new = load_arm("off", root / f"flush_{args.stage}", args.stage)
    old = load_arm("off", root / f"flush_{args.against}", args.against)
    shared = sorted(set(new["runs"]) & set(old["runs"]))

    print(f"{args.stage}: n={len(new['runs'])} sha={sorted(new['shas'])}")
    print(f"{args.against}: n={len(old['runs'])} sha={sorted(old['shas'])}")
    print(f"shared (tier, seed) pairs: {len(shared)}")

    mismatches = {f: [] for f in FIELDS}
    for key in shared:
        for field in FIELDS:
            if new["runs"][key][field] != old["runs"][key][field]:
                mismatches[field].append(key)

    for field in FIELDS:
        bad = mismatches[field]
        print(f"{field:>15}: {len(shared) - len(bad)}/{len(shared)} equal")
        for key in bad[:5]:
            print(
                f"{'':>17}{key}: {args.stage}={new['runs'][key][field]!r} "
                f"{args.against}={old['runs'][key][field]!r}"
            )

    emitting = {
        tag: [k for k, v in arm["runs"].items() if v["flush_events"] > 0]
        for tag, arm in ((args.stage, new), (args.against, old))
    }
    for tag, keys in emitting.items():
        print(f"{tag} off voyages with any flush event: {len(keys)} (must be 0)")
    if any(mismatches.values()) or any(emitting.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
