"""#37 feasibility gate: is any point of the sourced box admissible at all?

Design: docs/proposals/bounded_sensitivity_and_admissible_region_spec.md 2.3.

The question is not which parameter values are best. It is whether *any* point
inside the literature-bounded box satisfies every anchor at once. The gate
therefore selects nothing, fits nothing, and reports an empty region as a
result rather than as a failure to be repaired: widening an interval, moving to
a favourable endpoint, or dropping an anchor after seeing the answer would turn
the box into an instrument for producing agreement.

What this gate scores against is the canonical scorer, not a copy of it. Rows
are built by ``score_anchors.row_from_summary`` and cells by
``score_anchors.summarise_cell`` / ``verdicts``, so a point here means the same
thing a campaign cell means, and an anchor cannot pass here and fail there.

Four differences from the spec's own section 2.3, each deliberate:

*The whole box, not the screened subset.* Section 2.3 sweeps only the factors
that cleared #36's noise floor and holds the rest at a central estimate. That
restriction is not available: #36 was measured under the retired one-index-case
arrival, #54/#440 replaced it with a boarding prevalence draw, and at the box
centre the passenger infection attack rate moved from about 0.005 to 0.076 (see
docs/norovirus/bounded_screen_isolated_36.md section 0). Its ranking and its
floor describe a model that no longer exists, so neither may restrict this
search. Restricting to the one factor that had cleared the floor would also
have made the gate a fit of a single Grade D construction knob.

*A point is a cell, not a run.* Every anchor is a property of a set of voyages:
A8 is incidence over travel-days, A9 is a posting frequency over eligible
voyages, and the conditional anchors are medians over the runs that took off.
The gate therefore runs a matched seed set at each point -- common random
numbers, as in the screen -- and scores the resulting cell.

*Design-limited anchors are named, not waived.* A9's target interval is 0.0042
to 0.0056 postings per eligible voyage. A cell of n runs can only exhibit k/n,
so below about 180 runs per point the interval contains no attainable value and
A9 is unresolvable *by arithmetic of the design*, whatever the model does. Such
an anchor is removed from the verdict and reported as a design limitation, and
a point that passes everything else is reported as ``admissible_pending``
rather than admissible. That is the opposite of dropping an anchor: it is
refusing to count it as satisfied.

*Three outcomes, not two.* A point is ``inadmissible`` if any scored anchor
FAILs, ``unscored`` if a required anchor has no verdict for a reason the design
did not predict (no take-off, an undefined ratio), and admissible only if every
required anchor returns PASS. Unscored points are neither admissible nor
inadmissible: an empty region made of unscored points is insufficient coverage,
not structural incompatibility, and the two must not be reported as one thing.

A3 is absent from the required set on purpose: it became a construction band in
#23 and carries no verdict anywhere. Its band state is recorded per point as a
diagnostic.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from scipy.stats import qmc

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    compute_derived_metrics,
    extract_timeseries,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402
from telemetry_buffer.observation_model import score_anchors  # noqa: E402
from telemetry_buffer.observation_model.bounded_screen import (  # noqa: E402
    NOROVIRUS_FACTORS,
    Factor,
    build_run_spec,
)
from telemetry_buffer.observation_model.midrs_incidence_targets import (  # noqa: E402
    a8_targets,
    a9_targets,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (  # noqa: E402
    vsp_attack_rate_targets,
)

# The anchors a point must satisfy simultaneously. A3 is not here: it is a
# construction band (#23) and has no verdict to satisfy.
REQUIRED_ANCHORS: tuple[str, ...] = (
    "A1_ever_ill_passenger",
    "A2_ill_per_infected",
    "A5_passenger_crew_ratio",
    "A4_vsp_iqr",
    "A8",
    "A9",
)

# The gate runs the shipped legacy configuration rather than a surveillance
# arm, and says so in the row: the scorer keys cells by strategy and refuses an
# unlabelled one, and naming a campaign arm this run is not would be a false
# label rather than a missing one.
SURVEILLANCE_LABEL = "legacy_config_baseline"

ADMISSIBLE = "admissible"
ADMISSIBLE_PENDING = "admissible_pending_design_limited"
INADMISSIBLE = "inadmissible"
UNSCORED = "unscored"

INSIDE = "inside"
BELOW = "below"
ABOVE = "above"
UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class Design:
    """Everything about a point that is not a box coordinate."""

    pathogen_id: str = "norwalk_gi"
    bundle: str = "active_profiles"
    platform: str = "mega_cruise_5000"
    epochs: int = 168
    num_agents: int = 450
    era: str = "pre"
    co_seeded: str = "isolated"
    observation_scenario: str | None = None

    def run_kwargs(self) -> dict[str, Any]:
        return {
            "pathogen_id": self.pathogen_id,
            "bundle": self.bundle,
            "platform": self.platform,
            "epochs": self.epochs,
            "num_agents": self.num_agents,
            "co_seeded": self.co_seeded,
            "observation_scenario": self.observation_scenario,
        }


def sobol_units(dimensions: int, log2_points: int, seed: int) -> list[list[float]]:
    """A scrambled Sobol' sequence of 2**log2_points points in the unit cube."""
    engine = qmc.Sobol(d=dimensions, scramble=True, seed=seed)
    return [list(map(float, row)) for row in engine.random_base2(log2_points)]


def factor_values(
    factors: Sequence[Factor],
    units: Sequence[float],
) -> dict[str, float]:
    """The sourced-interval coordinates a unit-cube point stands for."""
    return {
        factor.name: factor.value(float(unit))
        for factor, unit in zip(factors, units, strict=True)
    }


def _effective_reporting_hazard(cfg: dict[str, Any]) -> float:
    """The sick-call hazard the run actually used, under either unit name.

    Read off the resolved configuration rather than restated here, so the
    parameters block records what the simulation did and not what this module
    believes the default to be.
    """
    syndromic = cfg.get("syndromic") or {}
    for key in ("sick_call_probability_per_day", "sick_call_probability"):
        if key in syndromic:
            return float(syndromic[key])
    raise RuntimeError(
        "the resolved configuration declares no syndromic sick-call hazard: "
        "whether a run reports at all decides which anchors can score it",
    )


def run_row(
    factors: Sequence[Factor],
    units: Sequence[float],
    *,
    seed: int,
    design: Design,
    point_index: int,
) -> dict[str, Any]:
    """Run one point at one seed and return a canonical scorer row."""
    spec = build_run_spec(
        factors,
        units,
        seed=seed,
        description=f"admissible_region_p{point_index:04d}_s{seed}",
        **design.run_kwargs(),
    )
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
        simulation = ShipSimulation(picard_spec, display=False)
        result = simulation.run()
        clock_mode = simulation.clock.mode
        hazard = _effective_reporting_hazard(dict(simulation.cfg))
    derived = compute_derived_metrics(
        extract_timeseries(result.history), design.num_agents,
    )
    run_id = f"{spec['description']}"
    summary = {
        "run_id": run_id,
        "parameters": {
            "platform_id": design.platform,
            "pathogen_bundle_id": design.bundle,
            "surveillance": SURVEILLANCE_LABEL,
            "seed": int(seed),
            "num_epochs": int(design.epochs),
            "num_agents": int(design.num_agents),
            "natural_history_clock": clock_mode,
            "sick_call_probability_per_day": hazard,
            "era": design.era,
        },
        "derived": derived,
    }
    return score_anchors.row_from_summary(summary, run_id)


def _interval_of(anchor: str) -> tuple[float, float]:
    return score_anchors.ANCHORS[anchor]


def position(value: float | None, bounds: tuple[float, float] | None) -> str:
    """Where a measured value sits relative to its target interval."""
    if value is None or bounds is None:
        return UNDETERMINED
    low, high = bounds
    if value < low:
        return BELOW
    if value > high:
        return ABOVE
    return INSIDE


def _conditional_measurements(cell: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """A1, A2 and A5 as measured value against literature interval."""
    out: dict[str, dict[str, Any]] = {}
    for anchor in score_anchors.ANCHORS:
        key = (
            anchor
            if anchor == "A1_ever_ill_passenger"
            else f"{anchor}__per_seed_median"
        )
        value = cell.get(key)
        bounds = _interval_of(anchor)
        out[anchor] = {
            "value": value,
            "interval": list(bounds),
            "position": position(value, bounds),
        }
    return out


def _a4_measurement(
    hull: str,
    cell: dict[str, Any],
    targets: dict[str, dict[str, float] | None],
) -> dict[str, Any]:
    target = targets.get(hull)
    bounds = None if target is None else (target["q1"], target["q3"])
    value = cell.get("reported_case_attack_rate_passenger")
    return {
        "value": value,
        "interval": None if bounds is None else list(bounds),
        "position": position(value, bounds),
    }


def _a8_measurements(hull: str, cell: dict[str, Any], era: str) -> dict[str, Any]:
    """Passenger and crew incidence against their plausibility envelopes."""
    try:
        target = a8_targets(hull, era)
    except ValueError:
        target = None
    out: dict[str, Any] = {}
    for role, cell_key in (("passenger", "A8_pax_incidence"), ("crew", "A8_crew_incidence")):
        value = cell.get(cell_key)
        numeric = value if isinstance(value, (int, float)) else None
        bounds = None if target is None else score_anchors.a8_band(target[role])
        out[role] = {
            "value": numeric,
            "interval": None if bounds is None else list(bounds),
            "position": position(numeric, bounds),
        }
    return out


def _a9_measurement(cell: dict[str, Any], era: str) -> dict[str, Any]:
    target = a9_targets(era)
    bounds = None
    if target is not None:
        low, high = target["fleet"]["interval"]
        bounds = (low / 1000.0, high / 1000.0)
    value = cell.get("A9_posting_probability")
    numeric = value if isinstance(value, (int, float)) else None
    return {
        "value": numeric,
        "interval": None if bounds is None else list(bounds),
        "position": position(numeric, bounds),
        "eligible_runs": cell.get("A9_eligible_runs"),
        "posted_eligible": cell.get("A9_posted_eligible"),
    }


def measurements(
    hull: str,
    cell: dict[str, Any],
    targets: dict[str, dict[str, float] | None],
    era: str,
) -> dict[str, Any]:
    """Every anchor's measured value, its interval, and which side it is on.

    The verdicts themselves come from the canonical scorer; this records the
    direction of a miss, which a PASS/FAIL cannot carry and which is what an
    empty region has to be explained by.
    """
    out = _conditional_measurements(cell)
    out["A4_vsp_iqr"] = _a4_measurement(hull, cell, targets)
    out["A8"] = _a8_measurements(hull, cell, era)
    out["A9"] = _a9_measurement(cell, era)
    return out


def a9_design_resolution(n_runs: int, era: str = "pre") -> dict[str, Any]:
    """Whether a cell of ``n_runs`` voyages can exhibit A9's target at all.

    A cell of n runs can only report k/n postings per eligible voyage. If no k
    puts that fraction inside the target interval, A9 says nothing about the
    model at this design size, and the honest report is that the design cannot
    resolve it -- not that the model passed or failed it.
    """
    target = a9_targets(era)
    if target is None:
        return {"resolvable": False, "reason": f"no A9 target for era {era!r}"}
    low, high = (bound / 1000.0 for bound in target["fleet"]["interval"])
    attainable = [k / n_runs for k in range(n_runs + 1)]
    resolvable = any(low <= value <= high for value in attainable)
    smallest = math.ceil(1.0 / high) if high > 0 else None
    return {
        "resolvable": resolvable,
        "interval": [low, high],
        "n_runs": n_runs,
        "coarsest_nonzero_attainable": 1.0 / n_runs,
        "min_runs_for_one_posting_inside": smallest,
        "reason": (
            ""
            if resolvable
            else (
                f"a cell of {n_runs} runs can only exhibit multiples of "
                f"{1.0 / n_runs:.4g} postings per eligible voyage, and none of "
                f"them lies in [{low:.5f}, {high:.5f}]"
            )
        ),
    }


def observed_voyage_days(points: Sequence[dict[str, Any]]) -> float | None:
    """The voyage length the scored cells imply, read back off their own units.

    A8 is the passenger reported attack rate spread over travel-days, so the
    ratio of the two recovers the duration the scorer used, rather than this
    module assuming an epoch length the clock might not have.
    """
    for point in points:
        cell = point.get("cell", {})
        rate = cell.get("reported_case_attack_rate_passenger")
        incidence = cell.get("A8_pax_incidence")
        if rate and incidence:
            return float(rate) / float(incidence) * 1e5
    return None


def a4_a8_definitional_conflict(
    hull: str,
    era: str,
    voyage_days: float | None,
) -> dict[str, Any]:
    """Whether one cell of voyages can satisfy A4 and A8 at the same time.

    Both anchors read the same numerator -- reported passenger cases -- but they
    are conditioned differently. A4 is the attack-rate distribution of voyages
    VSP *posted*, and A8 is incidence over *all* travel-days, outbreak voyages
    and quiet ones together. Dividing A4's interval by the voyage length puts it
    in A8's units, and if the two do not overlap then no parameter value can
    pass both in a cell of identically distributed voyages: passing both
    requires a mixture in which posted voyages are as rare as A9 says, which a
    cell of a few runs cannot represent. An empty region caused by this pair is
    therefore a statement about the anchor mapping and the design size, not
    about the model, and is reported separately from a structural miss.
    """
    targets = vsp_attack_rate_targets(era)
    target = targets.get(hull)
    try:
        a8_target = a8_targets(hull, era)
    except ValueError:
        a8_target = None
    if target is None or a8_target is None or not voyage_days:
        return {
            "comparable": False,
            "reason": (
                f"no A4 or A8 target for {hull} {era}"
                if voyage_days
                else "no cell defines a voyage length to convert A4 into A8 units"
            ),
        }
    implied = [
        target["q1"] / voyage_days * 1e5,
        target["q3"] / voyage_days * 1e5,
    ]
    band = list(score_anchors.a8_band(a8_target["passenger"]))
    overlaps = implied[0] <= band[1] and band[0] <= implied[1]
    return {
        "comparable": True,
        "voyage_days": voyage_days,
        "a4_implied_incidence_per_100k_travel_days": implied,
        "a8_passenger_band": band,
        "overlaps": overlaps,
        "separation_factor": implied[0] / band[1] if band[1] > 0 else None,
    }


def design_limited_anchors(n_runs: int, era: str) -> dict[str, str]:
    """Anchors whose target this design size cannot represent, with reasons."""
    resolution = a9_design_resolution(n_runs, era)
    if resolution["resolvable"]:
        return {}
    return {"A9": str(resolution["reason"])}


def classify(
    verdicts: dict[str, str],
    design_limited: Iterable[str],
    required: Sequence[str] = REQUIRED_ANCHORS,
) -> dict[str, Any]:
    """Sort one point into admissible / pending / inadmissible / unscored."""
    limited = set(design_limited)
    scored = [anchor for anchor in required if anchor not in limited]
    states = {anchor: verdicts.get(anchor, "missing") for anchor in scored}
    failed = [anchor for anchor, state in states.items() if state == "FAIL"]
    passed = [anchor for anchor, state in states.items() if state == "PASS"]
    unresolved = [
        anchor for anchor, state in states.items() if state not in ("PASS", "FAIL")
    ]
    if failed:
        verdict = INADMISSIBLE
    elif unresolved:
        verdict = UNSCORED
    elif limited:
        verdict = ADMISSIBLE_PENDING
    else:
        verdict = ADMISSIBLE
    return {
        "class": verdict,
        "failed": failed,
        "passed": passed,
        "unresolved": {anchor: states[anchor] for anchor in unresolved},
        "design_limited": sorted(limited),
    }


def evaluate_point(
    units: Sequence[float],
    *,
    point_index: int,
    seeds: Sequence[int],
    design: Design,
    factors: Sequence[Factor] = NOROVIRUS_FACTORS,
) -> dict[str, Any]:
    """Run one box point over the matched seed set and score its cell."""
    rows = [
        run_row(
            factors,
            units,
            seed=seed,
            design=design,
            point_index=point_index,
        )
        for seed in seeds
    ]
    cell = score_anchors.summarise_cell(rows)
    targets = vsp_attack_rate_targets(design.era)
    verdicts, ratios = score_anchors.verdicts(
        design.platform, cell, targets, design.era,
    )
    limited = design_limited_anchors(len(rows), design.era)
    return {
        "point_index": point_index,
        "units": [float(unit) for unit in units],
        "factors": factor_values(factors, units),
        "cell": cell,
        "verdicts": verdicts,
        "ratios": ratios,
        "measurements": measurements(design.platform, cell, targets, design.era),
        "construction_bands": score_anchors.construction_band_states(cell),
        "classification": classify(verdicts, limited),
    }


def marginal_ranges(
    points: Sequence[dict[str, Any]],
    classes: Sequence[str],
) -> dict[str, list[float]] | None:
    """Per-factor min and max over the points in the named classes.

    An output of the search and nothing else: the spec forbids writing a
    marginal range back into a profile as a new central estimate.
    """
    selected = [
        point for point in points
        if point["classification"]["class"] in classes
    ]
    if not selected:
        return None
    names = sorted(selected[0]["factors"])
    return {
        name: [
            min(point["factors"][name] for point in selected),
            max(point["factors"][name] for point in selected),
        ]
        for name in names
    }


def anchor_tally(points: Sequence[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Per-anchor verdict counts and, for FAILs, which side they missed on."""
    tally: dict[str, dict[str, int]] = {}
    for anchor in REQUIRED_ANCHORS:
        counts = {"PASS": 0, "FAIL": 0, "no_verdict": 0, BELOW: 0, ABOVE: 0}
        for point in points:
            state = point["verdicts"].get(anchor, "missing")
            counts[state if state in ("PASS", "FAIL") else "no_verdict"] += 1
            if state == "FAIL":
                for side in _fail_sides(point["measurements"].get(anchor)):
                    counts[side] += 1
        tally[anchor] = counts
    return tally


def _fail_sides(measurement: Any) -> list[str]:
    """Which side(s) of its interval a failing anchor's measurement sits on."""
    if not isinstance(measurement, dict):
        return []
    if "position" in measurement:
        return [measurement["position"]] if measurement["position"] in (BELOW, ABOVE) else []
    sides = []
    for role_measurement in measurement.values():
        sides.extend(_fail_sides(role_measurement))
    return sides


def joint_pass_pairs(points: Sequence[dict[str, Any]]) -> dict[str, int]:
    """How many points pass each pair of anchors together.

    A pair with zero joint passes over the whole sample is the reportable form
    of "these two anchors are not simultaneously satisfiable in this box" --
    subject, always, to the sample being a sample.
    """
    out: dict[str, int] = {}
    for first, second in combinations(REQUIRED_ANCHORS, 2):
        out[f"{first}+{second}"] = sum(
            point["verdicts"].get(first) == "PASS"
            and point["verdicts"].get(second) == "PASS"
            for point in points
        )
    return out


def summarise_design(
    points: Sequence[dict[str, Any]],
    design: Design,
    seeds: Sequence[int],
) -> dict[str, Any]:
    """The gate's verdict over the sampled box."""
    classes = [point["classification"]["class"] for point in points]
    counts = {
        name: classes.count(name)
        for name in (ADMISSIBLE, ADMISSIBLE_PENDING, INADMISSIBLE, UNSCORED)
    }
    total = len(points) or 1
    admissible_like = (ADMISSIBLE, ADMISSIBLE_PENDING)
    return {
        "n_points": len(points),
        "class_counts": counts,
        "admissible_volume_fraction": counts[ADMISSIBLE] / total,
        "admissible_pending_volume_fraction": counts[ADMISSIBLE_PENDING] / total,
        "unscored_fraction": counts[UNSCORED] / total,
        "marginal_ranges_admissible": marginal_ranges(points, admissible_like),
        "anchor_tally": anchor_tally(points),
        "joint_pass_pairs": joint_pass_pairs(points),
        "a9_design_resolution": a9_design_resolution(len(seeds), design.era),
        "design_limited_anchors": design_limited_anchors(len(seeds), design.era),
        "a4_a8_definitional_conflict": a4_a8_definitional_conflict(
            design.platform, design.era, observed_voyage_days(points),
        ),
    }


def _point_job(payload: tuple[Sequence[float], int, Sequence[int], Design]) -> dict[str, Any]:
    units, index, seeds, design = payload
    return evaluate_point(units, point_index=index, seeds=seeds, design=design)


def evaluate_design(
    units_grid: Sequence[Sequence[float]],
    *,
    seeds: Sequence[int],
    design: Design,
    workers: int = 1,
    on_point: Any = None,
    start_index: int = 0,
    completed: Sequence[int] = (),
    shard_count: int = 1,
    shard_index: int = 0,
) -> list[dict[str, Any]]:
    """Evaluate this shard's sampled points, streaming each to ``on_point``.

    Points are independent cells, so a shard takes the design indices
    congruent to ``shard_index`` and the union over shards is the whole grid.
    ``completed`` names indices already on disk, which is what makes a resume
    safe when the shard's indices are not contiguous.
    """
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError(f"shard {shard_index} outside 0..{shard_count - 1}")
    already = set(completed)
    jobs = [
        (units, index, seeds, design)
        for index, units in enumerate(units_grid)
        if index >= start_index
        and index % shard_count == shard_index
        and index not in already
    ]
    results: list[dict[str, Any]] = []
    if workers <= 1:
        for job in jobs:
            point = _point_job(job)
            results.append(point)
            if on_point is not None:
                on_point(point)
        return results
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for point in pool.map(_point_job, jobs):
            results.append(point)
            if on_point is not None:
                on_point(point)
    return results


def _validated_cli_path(path: Path, root: Path) -> Path:
    return Path(resolve_repo_path(str(root), str(path)))


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    report = json.dumps(payload, indent=2)
    with validated_open(
        str(_validated_cli_path(path, REPO_ROOT)),
        "w",
        allowed_roots=(str(REPO_ROOT),),
        encoding="utf-8",
    ) as handle:
        handle.write(report)
    return report


def _read_completed(path: Path) -> list[dict[str, Any]]:
    """Points already recorded in a stream file, in index order."""
    resolved = _validated_cli_path(path, REPO_ROOT)
    if not resolved.exists():
        return []
    with validated_open(
        str(resolved), allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        points = [json.loads(line) for line in handle if line.strip()]
    return sorted(points, key=lambda point: point["point_index"])


def _pooled_points(
    streams: Sequence[Path],
    *,
    expected: int,
) -> list[dict[str, Any]]:
    """Pool shard streams into one point list, refusing gaps and repeats.

    A partial grid is refused rather than summarised: the gate's verdict is a
    statement about the whole box, and a summary over the shards that happened
    to finish would silently narrow it.
    """
    pooled: dict[int, dict[str, Any]] = {}
    for stream in streams:
        for point in _read_completed(stream):
            index = int(point["point_index"])
            if index in pooled:
                raise SystemExit(
                    f"point {index} appears in more than one shard stream",
                )
            pooled[index] = point
    missing = sorted(set(range(expected)) - set(pooled))
    if missing:
        raise SystemExit(
            f"{len(missing)} of {expected} design points are absent "
            f"(first: {missing[:5]}); the gate scores a whole grid",
        )
    return [pooled[index] for index in sorted(pooled)]


def _run_shard(
    args: argparse.Namespace,
    grid: Sequence[Sequence[float]],
    seeds: Sequence[int],
    design: Design,
) -> list[dict[str, Any]]:
    """Evaluate this worker's share of the design, resuming its own stream."""
    shard_index = args.shard_index
    if shard_index is None:
        raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
        if args.shard_count > 1 and raw is None:
            raise SystemExit(
                "--shard-count > 1 needs --shard-index or "
                "AWS_BATCH_JOB_ARRAY_INDEX",
            )
        shard_index = int(raw) if raw is not None else 0
    done = _read_completed(args.stream) if (args.resume and args.stream) else []
    stream_path = (
        _validated_cli_path(args.stream, REPO_ROOT) if args.stream else None
    )

    def record(point: dict[str, Any]) -> None:
        if stream_path is None:
            return
        with validated_open(
            str(stream_path),
            "a",
            allowed_roots=(str(REPO_ROOT),),
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(point) + "\n")

    fresh = evaluate_design(
        grid,
        seeds=seeds,
        design=design,
        workers=args.workers,
        on_point=record,
        completed=[int(point["point_index"]) for point in done],
        shard_count=args.shard_count,
        shard_index=shard_index,
    )
    return [*done, *fresh]


def _require_scoring_inputs(design: Design) -> None:
    """Load every anchor target before the first voyage runs.

    A cell is scored only after all its seeds have run, so a missing VSP
    series would surface hours in and discard the whole shard; the anchors
    the cell will be scored against are read here, at the price of one file
    open, and an absent one is refused before any compute is spent.
    """
    try:
        vsp_attack_rate_targets(design.era)
        a9_targets(design.era)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"anchor scoring input missing: {exc.filename}; the gate cannot "
            "score a cell without it, so it refuses to run one",
        ) from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command line for the gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--bundle", default="active_profiles")
    parser.add_argument("--platform", default="mega_cruise_5000")
    parser.add_argument("--era", default="pre", choices=("pre", "post"))
    parser.add_argument("--num-agents", type=int, default=450)
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument(
        "--sobol-m",
        type=int,
        default=7,
        help="2**m design points; the spec's own figure is m = 10",
    )
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--seed-base", type=int, default=500)
    parser.add_argument("--design-seed", type=int, default=37)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Split the design points across this many workers",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=None,
        help=(
            "This worker's shard; defaults to AWS_BATCH_JOB_ARRAY_INDEX when "
            "--shard-count > 1"
        ),
    )
    parser.add_argument(
        "--merge",
        type=Path,
        nargs="*",
        default=(),
        help=(
            "Point streams (JSONL) to pool into one gate report instead of "
            "running the design"
        ),
    )
    parser.add_argument(
        "--observation-scenario",
        default=None,
        help="A declared observation_model.prior scenario to run the box under",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--stream",
        type=Path,
        default=None,
        help="JSONL of per-point results, written as they complete",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep the points already in --stream and evaluate only the rest",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Sample the box, score every point, and write the gate's report."""
    args = parse_args(argv)
    # Resolved before the grid runs: an unwritable destination is a typo, and
    # discovering it after the last Sobol' point discards the whole run.
    out = _validated_cli_path(args.out, REPO_ROOT)
    design = Design(
        pathogen_id=args.pathogen_id,
        bundle=args.bundle,
        platform=args.platform,
        epochs=args.epochs,
        num_agents=args.num_agents,
        era=args.era,
        observation_scenario=args.observation_scenario,
    )
    factors = NOROVIRUS_FACTORS
    seeds = [args.seed_base + index for index in range(args.seeds)]
    grid = sobol_units(len(factors), args.sobol_m, args.design_seed)
    if args.merge:
        points = _pooled_points(args.merge, expected=len(grid))
    else:
        _require_scoring_inputs(design)
        points = _run_shard(args, grid, seeds, design)

    sharded = not args.merge and args.shard_count > 1
    payload = {
        "mode": "feasibility_gate_shard" if sharded else "feasibility_gate",
        "box": f"full {len(factors)}-factor norovirus box (no #36 restriction)",
        "factors": [
            {
                "name": factor.name,
                "low": factor.low,
                "high": factor.high,
                "transform": factor.transform,
                "grade": factor.grade,
            }
            for factor in factors
        ],
        "design": {
            "sobol_log2_points": args.sobol_m,
            "design_seed": args.design_seed,
            "seeds": seeds,
            "required_anchors": list(REQUIRED_ANCHORS),
            "construction_only": list(score_anchors.CONSTRUCTION_BANDS),
            **design.run_kwargs(),
            "era": design.era,
        },
        "summary": summarise_design(points, design, seeds),
        "points": points,
    }
    if sharded:
        payload["shard"] = {
            "shard_count": args.shard_count,
            "points_in_shard": len(points),
            "design_points": len(grid),
            "note": (
                "a shard's summary describes its own points only; pool the "
                "streams with --merge before reading a gate verdict"
            ),
        }
    if args.merge:
        payload["merged_streams"] = [str(path) for path in args.merge]
    report = _write_json(out, payload)
    print(json.dumps(payload["summary"], indent=2))
    return 0 if report else 1


if __name__ == "__main__":
    raise SystemExit(main())
