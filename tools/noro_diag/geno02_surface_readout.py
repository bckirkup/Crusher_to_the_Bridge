"""NORO-GENO-02 mass-surface readout.

Aggregates the three arm result trees (shard zips synced from
``campaign/noro_geno_02_{gii4,nongii4,mixture}/``) into the frozen
readouts declared in ``docs/norovirus/noro_geno_02_design.md``:

- aboard acquisitions per arm per cell (``acquired_aboard``)
- aboard non-secretor share per arm with Wilson CIs (the gate readout)
- per-class + per-genotype attribution on the mixture arm
- attack rates, imports, and postings per 1,000 (report-only)
- powered-cell flag: cell is powered iff >=40 aboard acquisitions
  across its 20 seeds (frozen admissibility criterion)
- gate table: pooled share ratio B/A per hull x voyage x prevalence
  cell where both mono cells are powered

Usage:
    python3 tools/noro_diag/geno02_surface_readout.py \
        --gii4-dir path/to/gii4 --nongii4-dir path/to/nongii4 \
        --mixture-dir path/to/mixture --out out_dir
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

SHARD_SUFFIX = ".zip"
POWERED_MIN_ABOARD = 40
EXPECTED_SEEDS = 20

# licensed interval points: passenger prevalence -> label
_PREVALENCE_LABELS = {
    0.025: "ship_lo",
    0.0325: "ship_mid",
    0.04: "ship_hi",
}


@dataclass
class Run:
    arm: str
    run_id: str
    tier_id: str
    platform: str
    seed: int
    epochs: int
    num_agents: int
    rung: str
    pax_prev: float | None
    crew_prev: float | None
    acquired_aboard: int
    non_secretor_aboard: int
    imported: int
    ever_infected: int
    attack_ever: float
    attack_aboard: float
    reported_cases: int
    trigger_status: str
    classes_aboard: dict
    classes_ever: dict
    genotypes_ever: dict
    init_prevalence: dict = field(default_factory=dict)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Wilson score interval; returns (center, lo, hi)."""
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def prevalence_label(rung: str, pax_prev: float | None) -> str:
    if rung != "shipped":
        return f"rep_{rung}"
    for val, label in _PREVALENCE_LABELS.items():
        if pax_prev is not None and abs(pax_prev - val) < 1e-6:
            return label
    return f"ship_{pax_prev}"


def _parse_member(zf: zipfile.ZipFile, member: str, run: Run) -> None:
    with zf.open(member) as fh:
        summary = json.loads(fh.read().decode())
    params = summary.get("parameters", {})
    inner = summary.get("summary", {})
    attr = (summary.get("strain_attribution") or {}).get("norwalk_gi", {})
    run.rung = params.get("boarding_mechanism_rung", "?")
    run.pax_prev = params.get("boarding_passenger_prevalence")
    run.crew_prev = params.get("boarding_crew_prevalence")
    run.acquired_aboard = attr.get("acquired_aboard", 0)
    run.non_secretor_aboard = attr.get("non_secretor_acquired_aboard", 0)
    run.imported = attr.get("imported", 0)
    run.ever_infected = attr.get("ever_infected", 0)
    run.attack_ever = attr.get("attack_rate_ever_infected", 0.0)
    run.attack_aboard = attr.get("attack_rate_acquired_aboard", 0.0)
    run.reported_cases = inner.get("cumulative_reported_cases", 0)
    run.trigger_status = str(summary.get("trigger_status", ""))
    run.classes_aboard = attr.get("classes_acquired_aboard", {})
    run.classes_ever = attr.get("classes_ever_infected", {})
    run.genotypes_ever = attr.get("genotypes_ever_carried", {})


def _parse_run_spec(zf: zipfile.ZipFile, prefix: str, run: Run) -> None:
    with zf.open(f"{prefix}/run_spec.json") as fh:
        spec = json.loads(fh.read().decode())
    cp = spec.get("campaign_parameters", {})
    run.run_id = cp.get("run_id", run.run_id)
    run.tier_id = cp.get("tier_id", "?")
    run.platform = cp.get("platform_id", "?")
    run.seed = int(cp.get("seed", -1))
    run.epochs = int(cp.get("num_epochs", -1))
    run.num_agents = int(cp.get("num_agents", -1))


def _parse_init_prevalence(zf: zipfile.ZipFile, prefix: str, run: Run) -> None:
    try:
        with zf.open(f"{prefix}/resolved_pathogen_profiles.json") as fh:
            rp = json.loads(fh.read().decode())
        run.init_prevalence = (
            rp.get("initiation", {}).get("prevalence", {}).get("norwalk_gi", {})
        )
    except KeyError:
        # member absent in shard zips from pre-instrument images
        pass


def iter_runs(arm: str, directory: Path) -> list[Run]:
    runs: list[Run] = []
    for zpath in sorted(directory.rglob(f"*{SHARD_SUFFIX}")):
        if "canary" in str(zpath) or "sweep" in str(zpath):
            continue
        try:
            zf = zipfile.ZipFile(zpath)
        except zipfile.BadZipFile:
            print(f"WARN bad zip: {zpath}", file=sys.stderr)
            continue
        with zf:
            prefixes = {
                n.rsplit("/", 1)[0]
                for n in zf.namelist()
                if n.endswith("/summary.json")
            }
            for prefix in sorted(prefixes):
                run = Run(
                    arm=arm, run_id=prefix.split("/")[-1], tier_id="?",
                    platform="?", seed=-1, epochs=-1, num_agents=-1,
                    rung="?", pax_prev=None, crew_prev=None,
                    acquired_aboard=0, non_secretor_aboard=0, imported=0,
                    ever_infected=0, attack_ever=0.0, attack_aboard=0.0,
                    reported_cases=0, trigger_status="", classes_aboard={},
                    classes_ever={}, genotypes_ever={},
                )
                _parse_member(zf, f"{prefix}/summary.json", run)
                try:
                    _parse_run_spec(zf, prefix, run)
                except KeyError:
                    # run_spec absent on failure-sidecar shards
                    pass
                _parse_init_prevalence(zf, prefix, run)
                runs.append(run)
    return runs


@dataclass
class CellAgg:
    runs: int = 0
    seeds: set = field(default_factory=set)
    aboard: int = 0
    nonsec_aboard: int = 0
    imported: int = 0
    ever: int = 0
    agents: int = 0
    reported: int = 0
    alerts: int = 0
    classes_aboard: dict = field(default_factory=lambda: defaultdict(int))
    classes_ever: dict = field(default_factory=lambda: defaultdict(int))
    genotypes_ever: dict = field(default_factory=lambda: defaultdict(int))
    missing_attribution: int = 0

    def add(self, run: Run) -> None:
        self.runs += 1
        self.seeds.add(run.seed)
        self.aboard += run.acquired_aboard
        self.nonsec_aboard += run.non_secretor_aboard
        self.imported += run.imported
        self.ever += run.ever_infected
        self.agents += run.num_agents
        self.reported += run.reported_cases
        self.alerts += 1 if run.trigger_status == "ALERT" else 0
        for k, v in run.classes_aboard.items():
            self.classes_aboard[k] += v
        for k, v in run.classes_ever.items():
            self.classes_ever[k] += v
        for k, v in run.genotypes_ever.items():
            self.genotypes_ever[k] += v
        if run.ever_infected > 0 and not run.classes_ever:
            self.missing_attribution += 1

    @property
    def powered(self) -> bool:
        return self.aboard >= POWERED_MIN_ABOARD


def cell_key(run: Run) -> tuple[str, int, str]:
    return (
        run.platform,
        run.epochs,
        prevalence_label(run.rung, run.pax_prev),
    )


def gate_row(cell: str, a: CellAgg, b: CellAgg) -> dict:
    pa, lo_a, hi_a = wilson(a.nonsec_aboard, a.aboard)
    pb, lo_b, hi_b = wilson(b.nonsec_aboard, b.aboard)
    ratio = pb / pa if pa and pa > 0 else float("nan")
    return {
        "cell": cell,
        "aboard_A": a.aboard, "nonsec_A": a.nonsec_aboard,
        "share_A": pa, "ci_A": [lo_a, hi_a],
        "aboard_B": b.aboard, "nonsec_B": b.nonsec_aboard,
        "share_B": pb, "ci_B": [lo_b, hi_b],
        "ratio_B_over_A": ratio,
    }


def build_report(arms: dict[str, list[Run]]) -> dict:
    cells: dict[tuple[str, str, int, str], CellAgg] = defaultdict(CellAgg)
    wrong_class: dict[str, int] = defaultdict(int)
    for arm, runs in arms.items():
        for run in runs:
            cells[(arm, *cell_key(run))].add(run)
            if arm == "mono_gii4" and run.classes_aboard.get("non_gii4", 0) > 0:
                wrong_class[run.run_id] += 1
            if arm == "mono_nongii4" and run.classes_aboard.get("gii4", 0) > 0:
                wrong_class[run.run_id] += 1
    per_cell = {}
    for (arm, plat, ep, imp), agg in sorted(cells.items()):
        p, lo, hi = wilson(agg.nonsec_aboard, agg.aboard)
        per_cell[f"{arm}|{plat}|{ep}|{imp}"] = {
            "runs": agg.runs, "seeds": len(agg.seeds),
            "aboard": agg.aboard, "nonsec_aboard": agg.nonsec_aboard,
            "share": p, "ci": [lo, hi], "powered": agg.powered,
            "imported": agg.imported, "ever_infected": agg.ever,
            "attack_rate_ever": agg.ever / agg.agents if agg.agents else 0.0,
            "postings_per_1000": 1000.0 * agg.reported / agg.agents if agg.agents else 0.0,
            "alert_voyages": agg.alerts,
            "missing_attribution_runs": agg.missing_attribution,
            "classes_aboard": dict(agg.classes_aboard),
            "classes_ever": dict(agg.classes_ever),
            "genotypes_ever": dict(agg.genotypes_ever),
        }
    gate = []
    for (plat, ep, imp) in sorted({cell_key(r) for rs in arms.values() for r in rs}):
        a = cells.get(("mono_gii4", plat, ep, imp))
        b = cells.get(("mono_nongii4", plat, ep, imp))
        if a and b and a.powered and b.powered:
            gate.append(gate_row(f"{plat}|{ep}|{imp}", a, b))
    pool_a = CellAgg()
    pool_b = CellAgg()
    for (arm, plat, ep, imp), agg in cells.items():
        mate = "mono_nongii4" if arm == "mono_gii4" else "mono_gii4"
        other = cells.get((mate, plat, ep, imp))
        if agg.powered and other and other.powered:
            for run in [r for r in arms[arm] if cell_key(r) == (plat, ep, imp)]:
                (pool_a if arm == "mono_gii4" else pool_b).add(run)
    pooled = gate_row("pooled_powered", pool_a, pool_b) if pool_a.aboard else None
    return {
        "n_runs": {arm: len(rs) for arm, rs in arms.items()},
        "n_cells": len(per_cell),
        "n_powered": sum(1 for c in per_cell.values() if c["powered"]),
        "per_cell": per_cell,
        "gate_surface": gate,
        "pooled_gate": pooled,
        "wrong_class_founder_runs": dict(wrong_class),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gii4-dir", type=Path, required=True)
    ap.add_argument("--nongii4-dir", type=Path, required=True)
    ap.add_argument("--mixture-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    arms = {
        "mono_gii4": iter_runs("mono_gii4", args.gii4_dir),
        "mono_nongii4": iter_runs("mono_nongii4", args.nongii4_dir),
        "mixture": iter_runs("mixture", args.mixture_dir),
    }
    for arm, rs in arms.items():
        print(f"{arm}: {len(rs)} runs", file=sys.stderr)
    report = build_report(arms)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "geno02_surface_report.json").write_text(
        json.dumps(report, indent=1))
    print(json.dumps({
        "n_runs": report["n_runs"], "n_cells": report["n_cells"],
        "n_powered": report["n_powered"],
        "n_gate_cells": len(report["gate_surface"]),
        "pooled_gate": report["pooled_gate"],
        "wrong_class_runs": len(report["wrong_class_founder_runs"]),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
