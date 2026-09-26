#!/usr/bin/env python3
"""Per-import secondary yield for norwalk_gi, for ledger NORO-IMPORT-YIELD-01.

Purpose
-------
The introduction realism ladder (``docs/norovirus/realism_ladder_v1_readout.md``)
reports the shipped boarding channel at ~5-20 secondaries per infectious
import on the 7/12-day rungs (spirit 7d: 52.0 mean secondary / 6.91 mean
imports ≈ 7.5). That ratio conflates three different hosts — a symptomatic
course boarding mid-illness, an incubating/presymptomatic draw, and a
convalescent tail-shedder — with a generation cascade that counts every
onboard-acquired infection against the import line. This probe decomposes it:

    arm ``baseline``:  the frozen NORO-COINCIDENCE cell (spirit_cruise_3000
                       x norwalk_only x 168 epochs) run as shipped. Per seed:
                       drawn imports and their boarding-state composition,
                       onboard-acquired infections with acquisition day and
                       dominant route, and the pooled yield ratio.

    arm ``single``:    the same cell with the boarding draw switched off
                       (``initiation.boarding.norwalk_gi.enabled: false``)
                       and exactly one explicit seed introduced at a stated
                       onset geometry — one import per voyage, so the
                       secondary count *is* the per-import yield
                       distribution for that state, generation cascade
                       included.

Seed geometries emulate the states the boarding draw produces:

    --onset-day -1 --age-days 2.2   symptomatic course ~1 d into illness
                                    (incubation = age + onset - seed_day
                                    must stay positive; norwalk median
                                    incubation is 1.2 d)
    --onset-day 0.5 --age-days 0.4  presymptomatic draw (onset next day)
    --onset-day -4 --age-days 5.2   convalescent tail-shedder (illness
                                    ended ~day -1, RNA-positive still)

Known fidelity gap vs the symptomatic stream: an explicit seed's illness
duration is the profile ``recovery_day`` (3 d), not the stream's
length-biased illness draw (E[T] = 2.5715 d); the emesis schedule and
axis draws go through the same ``_stamp_symptomatic_history`` path.
Declared before the runs in the ledger entry.

Method
------
Read-only instrumentation only: ``build_spec`` writes the shipped spec;
the ``single`` arm adds exactly one ``config_overrides.initiation`` block
(boarding off, one seed). The harvest reads the engine's own
``initiation_manifest`` (``drawn_by_role``, ``composition``) and each
infection record's ``boarding_state``, ``infection_epoch`` and
``acquired_particles_by_route`` (dominant route = argmax). Nothing draws
from the engine's RNG; the observer path is not used.

Inputs
------
``--arm baseline|single``, ``--seeds``, ``--platform`` (default
``spirit_cruise_3000``), ``--bundle norwalk_only``, ``--pathogen-id
norwalk_gi``, ``--epochs 168``, ``--onset-day``, ``--age-days``,
``--seed-role`` (default ``passenger``), ``--out``.

Outputs
-------
One gzipped JSON per seed plus a pooled ``*_readout.json``: per-seed
imports-by-state, secondaries, yields, day-of-acquisition histograms,
route splits; pooled means/medians for the ledger.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.noro_diag import per_host_dose_challenge as _pdc  # noqa: E402
from tools.noro_diag.dose_response import load_dose_response  # noqa: E402


def _role_group(role: Any) -> str:
    text = str(role or "").lower()
    if "crew" in text:
        return "crew"
    if text == "passenger" or "passenger" in text:
        return "passenger"
    return "other"


def _dominant_route(inf: dict[str, Any]) -> str | None:
    ledger = inf.get("acquired_particles_by_route") or {}
    if sum(ledger.values()) <= 0.0:
        return None
    return max(ledger, key=ledger.get)


def harvest_infections(
    sim: Any, pathogen_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(imports, onboard-acquired) — the ladder's own denominator split."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", set()) or ())
    imports: list[dict[str, Any]] = []
    secondaries: list[dict[str, Any]] = []
    for agent in sim.engine.agents:
        inf = agent.infections.get(pathogen_id)
        if inf is None or agent.agent_id in seeded:
            continue
        axes = inf.get("symptom_axes") or {}
        record = {
            "agent_id": int(agent.agent_id),
            "role": _role_group(getattr(agent, "role", None)),
            "infection_epoch": int(inf.get("infection_epoch") or 0),
            "boarding_state": inf.get("boarding_state"),
            "days_since_onset_at_boarding": (
                inf.get("days_since_onset_at_boarding")
            ),
            "severity_peak": str(
                inf.get("symptom_severity_peak")
                or inf.get("symptom_severity") or "none",
            ),
            "vomiting": bool(axes.get("vomiting")),
            "diarrhoea": bool(axes.get("diarrhoea")),
            "dominant_route": _dominant_route(inf),
        }
        if inf.get("boarding_state") is not None:
            imports.append(record)
        else:
            secondaries.append(record)
    return imports, secondaries


def boarding_manifest(sim: Any, pathogen_id: str) -> dict[str, Any]:
    manifest = getattr(sim.engine, "initiation_manifest", {}) or {}
    return dict((manifest.get("boarding") or {}).get(pathogen_id) or {})


def build_probe_spec(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    num_agents: int,
    pathogen_id: str,
    beta: float,
    arm: str,
    seed_role: str,
    onset_day: float | None,
    age_days: float | None,
) -> dict[str, Any]:
    spec = _pdc.build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=num_agents,
        pathogen_id=pathogen_id, alpha=None, beta=beta,
    )
    if arm == "single":
        if onset_day is None or age_days is None:
            raise ValueError(
                "arm 'single' needs --onset-day and --age-days",
            )
        spec["config_overrides"]["initiation"] = {
            "boarding": {pathogen_id: {"enabled": False}},
            "explicit_seeds": [{
                "pathogen": pathogen_id,
                "count": 1,
                "role": seed_role,
                "epoch": 0,
                "infection_age_days": float(age_days),
                "onset_day": float(onset_day),
            }],
        }
    return spec


def run_seed(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    pathogen_id: str,
    arm: str,
    seed_role: str,
    onset_day: float | None,
    age_days: float | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    num_agents = declared_total(platform)
    _alpha, beta = load_dose_response(pathogen_id, bundle)
    spec_dict = build_probe_spec(
        seed=seed, platform=platform, bundle=bundle, epochs=epochs,
        num_agents=num_agents, pathogen_id=pathogen_id, beta=beta,
        arm=arm, seed_role=seed_role,
        onset_day=onset_day, age_days=age_days,
    )
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        sim = ShipSimulation(picard_spec, display=False)
        sim.run()

    imports, secondaries = harvest_infections(sim, pathogen_id)
    seeded_ids = set(
        getattr(sim.engine, "explicit_seed_agent_ids", set()) or (),
    )
    manifest = boarding_manifest(sim, pathogen_id)
    seeded_records = []
    for agent in sim.engine.agents:
        if agent.agent_id in seeded_ids:
            inf = agent.infections.get(pathogen_id) or {}
            axes = inf.get("symptom_axes") or {}
            seeded_records.append({
                "agent_id": int(agent.agent_id),
                "role": _role_group(getattr(agent, "role", None)),
                "vomiting": bool(axes.get("vomiting")),
                "diarrhoea": bool(axes.get("diarrhoea")),
                "severity_peak": str(
                    inf.get("symptom_severity_peak")
                    or inf.get("symptom_severity") or "none",
                ),
                "onset_time_infected": inf.get("onset_time_infected"),
                "incubation_days": inf.get("incubation_days"),
            })
    composition = dict(manifest.get("composition") or {})
    drawn = dict(manifest.get("drawn_by_role") or {})
    return {
        "seed": int(seed),
        "arm": arm,
        "seed_geometry": {
            "onset_day": onset_day, "age_days": age_days, "role": seed_role,
        } if arm == "single" else None,
        "wall_clock_s": round(time.perf_counter() - started, 1),
        "imports_drawn": drawn,
        "imports_drawn_total": sum(drawn.values()),
        "composition": composition,
        "imports": imports,
        "seeded": seeded_records,
        "secondaries_total": len(secondaries),
        "secondaries_by_day": dict(Counter(
            str(sim.clock.day_index(int(r["infection_epoch"])))
            for r in secondaries
        )),
        "secondaries_by_route": dict(Counter(
            str(r["dominant_route"]) for r in secondaries
        )),
        "secondaries_by_role": dict(Counter(
            r["role"] for r in secondaries
        )),
        "yield_per_import": (
            len(secondaries) / sum(drawn.values())
            if sum(drawn.values()) else None
        ),
    }


def _quantiles(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0}
    ordered = sorted(float(v) for v in vals)
    n = len(ordered)

    def q(p: float) -> float:
        k = (n - 1) * p
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)

    return {
        "n": n, "min": ordered[0], "q25": q(0.25), "median": q(0.5),
        "q75": q(0.75), "max": ordered[-1], "mean": sum(ordered) / n,
    }


def build_readout(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    imports = [s["imports_drawn_total"] for s in per_seed]
    secondaries = [s["secondaries_total"] for s in per_seed]
    yields = [
        s["yield_per_import"] for s in per_seed
        if s["yield_per_import"] is not None
    ]
    total_imports = sum(imports)
    total_secondaries = sum(secondaries)
    composition: Counter = Counter()
    route: Counter = Counter()
    for s in per_seed:
        composition.update(s.get("composition") or {})
        route.update(s.get("secondaries_by_route") or {})
    return {
        "n_seeds": len(per_seed),
        "imports_per_voyage": _quantiles(imports),
        "composition_total": dict(composition),
        "secondaries_per_voyage": _quantiles(secondaries),
        "yield_per_import_per_seed": _quantiles(yields),
        "pooled_yield": (
            total_secondaries / total_imports if total_imports else None
        ),
        "p_zero_secondary": (
            sum(1 for s in secondaries if s == 0) / len(secondaries)
            if secondaries else None
        ),
        "secondaries_by_route_total": dict(route),
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", choices=("baseline", "single"), required=True)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8000],
    )
    parser.add_argument("--platform", default="spirit_cruise_3000")
    parser.add_argument("--bundle", default="norwalk_only")
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--onset-day", type=float, default=None)
    parser.add_argument("--age-days", type=float, default=None)
    parser.add_argument("--seed-role", default="passenger")
    parser.add_argument(
        "--out", default="docs/norovirus/import_yield_probe",
        help="output directory for per-seed JSON + pooled readout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(
            str(args.out), allowed_roots=(str(REPO_ROOT),),
        ),
    )
    tag = (
        f"{args.arm}_onset{args.onset_day:g}_age{args.age_days:g}"
        if args.arm == "single" else args.arm
    )
    per_seed = []
    for seed in args.seeds:
        summary = run_seed(
            seed=seed, platform=args.platform, bundle=args.bundle,
            epochs=args.epochs, pathogen_id=args.pathogen_id, arm=args.arm,
            seed_role=args.seed_role,
            onset_day=args.onset_day, age_days=args.age_days,
        )
        per_seed.append(summary)
        path = resolve_child_path(
            str(out_dir), f"import_yield_{tag}_seed{seed}.json.gz",
        )
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=1)
        print(
            f"seed {seed}: imports={summary['imports_drawn_total']} "
            f"secondaries={summary['secondaries_total']} "
            f"yield={summary['yield_per_import']} -> {path}",
            flush=True,
        )
    readout = build_readout(per_seed)
    readout["arm"] = args.arm
    readout["seed_geometry"] = {
        "onset_day": args.onset_day, "age_days": args.age_days,
        "role": args.seed_role,
    } if args.arm == "single" else None
    readout_path = resolve_child_path(
        str(out_dir), f"import_yield_{tag}_readout.json",
    )
    with validated_open(
        readout_path, "w", allowed_roots=(str(out_dir),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(readout, indent=1))
    print(f"readout: {readout_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
