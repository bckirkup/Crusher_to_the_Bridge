"""Render the role-checkpoint evidence ledgers as Markdown tables.

Reads the JSON ledgers written by ``tools/diag/role_checkpoint_invariance.py``
and prints the tables pasted into
``docs/campaign_reduction/FIRST_PAPER_ROLE_CHECKPOINT_REPORT.md``.  Pure
rendering: no simulation, no RNG, no recomputation of any count.

Usage::

    python tools/diag/role_checkpoint_report_tables.py \
        docs/campaign_reduction/role_checkpoint_evidence/*.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.analysis._io import read_json, safe_path  # noqa: E402

MEASURES: tuple[str, ...] = (
    "infected", "ill", "unique_etiologic_reporters",
    "unique_clinical_noise_reporters", "reporter_overlap",
    "unique_person_union", "union_ever_ill", "union_not_ill", "complement",
)
MEASURE_ABBR: dict[str, str] = {
    "infected": "inf", "ill": "ill", "unique_etiologic_reporters": "etio",
    "unique_clinical_noise_reporters": "noise", "reporter_overlap": "overlap",
    "unique_person_union": "union", "union_ever_ill": "union∩ill",
    "union_not_ill": "union−ill", "complement": "N",
}
DAYS: tuple[str, ...] = ("day_3", "day_7", "day_10", "day_12")


NO = "**no**"


def _yn(value: Any) -> str:
    return "yes" if value else NO


def _yn_plain(value: Any) -> str:
    return "yes" if value else "no"


def _load_runs(paths: list[Path]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in paths:
        ledger = read_json(safe_path(path))
        for rec in ledger["runs"]:
            runs.append(rec | {"_ledger": path.name})
    return sorted(runs, key=lambda r: (r["tier"], r["seed"]))


def _row(cells: list[Any]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _header(cols: list[str]) -> list[str]:
    return [_row(cols), "|" + "---|" * len(cols)]


def paired_replay_table(runs: list[dict[str, Any]]) -> list[str]:
    lines = _header(["tier", "seed", "ledger", "voyage blocks off==on",
                     "census off==on", "initiation off==on",
                     "RNG state off==on", "history off==on (minus sidecar)",
                     "sidecar off/on", "pass"])
    for r in runs:
        w = r.get("rng_witness") or {}
        lines.append(_row([
            r["tier"], r["seed"], r["_ledger"], _yn(r["voyage_equal"]),
            _yn(r["census_equal"]), _yn(r["initiation_equal"]),
            _yn(w["rng_state_equal"]) if w else "not run",
            _yn(w["history_equal_minus_sidecar"]) if w else "not run",
            f"{'present' if r['off_has_sidecar'] else 'absent'}/"
            f"{'present' if r['on_has_sidecar'] else 'absent'}",
            _yn(r["pass"]),
        ]))
    return lines


def baseline_table(runs: list[dict[str, Any]]) -> list[str]:
    lines = _header(["tier", "seed", "baseline zip has sidecar", "bit-identical",
                     "identical modulo float drift", "float-drift leaves",
                     "float-drift paths", "day-12 sidecar == baseline summary"])
    for r in runs:
        b = r.get("baseline")
        if not b:
            lines.append(_row([r["tier"], r["seed"], "—", "no baseline", "", "", "", ""]))
            continue
        lines.append(_row([
            r["tier"], r["seed"], _yn_plain(b["baseline_has_sidecar"]),
            _yn_plain(b["blocks_equal"]),
            _yn(b.get("blocks_equal_modulo_float_drift", b["blocks_equal"])),
            b.get("n_float_drift_leaves", 0),
            ", ".join(f"`{p}`" for p in b.get("float_drift_paths", [])) or "—",
            _yn(b["day12_vs_baseline_summary"]["agree"]),
        ]))
    return lines


def endpoint_table(runs: list[dict[str, Any]], key: str) -> list[str]:
    first = next((r[key] for r in runs if r.get(key)), None)
    if first is None:
        return ["(no endpoint agreement records)"]
    checks = [k for k in first if k not in ("agree", "available")]
    lines = _header(["tier", "seed", *[c.replace("==", " == ") for c in checks], "agree"])
    for r in runs:
        rec = r.get(key) or {}
        lines.append(_row([r["tier"], r["seed"],
                           *[f"{rec[c][0]} / {rec[c][1]}" if c in rec else "—" for c in checks],
                           _yn(rec.get("agree"))]))
    return lines


def checkpoint_table(runs: list[dict[str, Any]]) -> list[str]:
    cols = ["tier", "seed", "day", "epoch", "role",
            *[MEASURE_ABBR[m] for m in MEASURES]]
    lines = _header(cols)
    for r in runs:
        for day in DAYS:
            cp = r["checkpoints"].get(day)
            if not cp or not cp.get("available"):
                lines.append(_row([r["tier"], r["seed"], day, "—", "unavailable",
                                   *["" for _ in MEASURES]]))
                continue
            for role in ("passenger", "crew", "all"):
                lines.append(_row([r["tier"], r["seed"], day, cp["epoch_index"], role,
                                   *[cp[role][m] for m in MEASURES]]))
    return lines


def render(paths: list[Path]) -> str:
    runs = _load_runs(paths)
    out: list[str] = []
    out.append("### Paired replay (emitter off vs on, same implementation)")
    out += paired_replay_table(runs)
    out.append("")
    out.append("### Day-12 sidecar vs the run's own `summary` endpoints")
    out += endpoint_table(runs, "day12_vs_own_summary")
    out.append("")
    out.append("### Baseline agreement (same seed vs the venue02 526cf856 zip)")
    out += baseline_table(runs)
    out.append("")
    out.append("### Day-12 sidecar vs the 526cf856 baseline `summary` endpoints")
    out += endpoint_table(
        [r | {"day12_vs_baseline_summary": (r.get("baseline") or {}).get("day12_vs_baseline_summary")}
         for r in runs], "day12_vs_baseline_summary")
    out.append("")
    out.append("### Cumulative checkpoints (emitter on)")
    out += checkpoint_table(runs)
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ledgers", nargs="+", type=Path)
    args = parser.parse_args()
    print(render(args.ledgers), end="")


if __name__ == "__main__":
    main()
