#!/usr/bin/env python3
"""NORO-ENTRAIN-01 reporting-funnel scan — wire stages from summary.json.

Emits one JSONL row per voyage carrying the observation-chain funnel
fields the implications doc (``docs/norovirus/noro_entrain_01_implications.md``
§2.2) reads to decompose the infection -> reported-case chain:

- ``cumulative_ever_infected_*`` / ``cumulative_ever_ill_*`` /
  ``cumulative_reported_cases_*`` / ``cumulative_reported_noise_cases``
  (per-role, plus the noise-case tally the wire also emits);
- the capture-stage counters ``sick_call_count``,
  ``campaign_specimens``, ``campaign_confirmed``,
  ``onset_observation_count``;
- the derived rates ``ever_ill_rate_*``, ``infection_attack_rate_*``,
  ``reported_case_rate_*`` and end-state ``symptomatic``/``infected``/
  ``isolated``/``quarantined`` snapshot plus complements.

Read path is the same ranged zip-member fetch as ``entrain_01_scan.py``:
EOCD -> central directory -> ``summary.json`` blob, nothing touches the
engine and nothing is written to S3. ``--resume`` skips keys already in
the JSONL out.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_source_readout import _list_keys  # noqa: E402
from outbreak_anchor_readout import (  # noqa: E402
    _s3_client,
    _s3_member_blob,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_entrain_01/"
_SUMMARY_MEMBER = "summary.json"

_FUNNEL_FIELDS = (
    "cumulative_ever_infected_passenger",
    "cumulative_ever_infected_crew",
    "cumulative_ever_ill_passenger",
    "cumulative_ever_ill_crew",
    "cumulative_reported_cases_passenger",
    "cumulative_reported_cases_crew",
    "cumulative_reported_noise_cases",
    "sick_call_count",
    "campaign_specimens",
    "campaign_confirmed",
    "onset_observation_count",
    "ever_ill_rate_passenger",
    "ever_ill_rate_crew",
    "infection_attack_rate_passenger",
    "infection_attack_rate_crew",
    "reported_case_rate_passenger",
    "reported_case_rate_crew",
    "symptomatic",
    "infected",
    "isolated",
    "quarantined",
    "passenger_complement",
    "crew_complement",
)


def _fetch(client, bucket: str, key: str) -> dict:
    try:
        blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
        if blob is None:
            return {"key": key, "error": "no summary member"}
        body = json.loads(blob).get("summary") or {}
        return {"key": key, **{f: body.get(f) for f in _FUNNEL_FIELDS}}
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": key, "error": str(exc)}


def _already_scanned(out_path: Path, resume: bool) -> set[str]:
    if not (resume and out_path.exists()):
        return set()
    root = str(out_path.parent.resolve())
    done = set()
    with validated_open(str(out_path), encoding="utf-8",
                        allowed_roots=(root,)) as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "key" in row:
                done.add(row["key"])
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    help="s3:// URI or bucket-relative prefix; repeatable")
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    prefixes = [
        p.split("/", 3)[-1] if p.startswith("s3://") else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    out_path = Path(args.out)
    done = _already_scanned(out_path, args.resume)
    client = _s3_client()
    out_root = str(out_path.parent.resolve())
    with validated_open(
        str(out_path), "a", allowed_roots=(out_root,), encoding="utf-8",
    ) as fh:
        for prefix in prefixes:
            tier = prefix.rstrip("/") + "/"
            keys = [k for k in _list_keys(client, args.bucket, tier)
                    if k not in done]
            if not keys:
                print(f"{tier}: nothing new", file=sys.stderr)
                continue
            n_rows = n_err = 0
            with ThreadPoolExecutor(args.workers) as pool:
                futs = [
                    pool.submit(_fetch, client, args.bucket, k)
                    for k in keys
                ]
                for i, fut in enumerate(as_completed(futs)):
                    row = fut.result()
                    fh.write(json.dumps(row) + "\n")
                    n_rows += 1
                    n_err += bool(row.get("error"))
                    if (i + 1) % 500 == 0:
                        fh.flush()
                        print(f"  {tier}: {i + 1}/{len(keys)}",
                              file=sys.stderr)
            fh.flush()
            print(f"{tier}: {n_rows} rows, {n_err} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
