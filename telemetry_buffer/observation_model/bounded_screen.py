"""Morris elementary-effects screen over the sourced parameter box.

Design: docs/proposals/bounded_sensitivity_and_admissible_region_spec.md.

This screen answers which parameters the *scored observable outputs* move on
when every parameter is allowed to range over its sourced interval. It selects
no value. The elementary effects it reports rank the factors; they do not
locate an optimum, and nothing here may be written back into a profile.

Two properties of the design matter more than the arithmetic:

Common random numbers. An elementary effect is a difference between two design
points, so the same seed set is used at every point. Without that, the seed
variance appears in every difference and the ranking measures noise.

The noise floor. `--mode floor` runs the box centre over many seeds and
records the seed-to-seed standard deviation of each output. A factor whose
mu-star falls below that floor is reported as indistinguishable from
stochastic noise at this design size. It is NOT reported as insensitive: the
second claim would license freezing the parameter, and this design cannot
support it.

Two factors named in the spec are deliberately absent, both for the same
reason -- they are not simulation parameters:

  * The factor the spec's section 3.2 lists as "cabin-localization fraction f"
    at 0.80-0.99 is the fraction of a host's emesis episodes happening in its
    own cabin, and it is a parameter of the Park surface harness only
    (park_surface_check.EMESIS_IN_OWN_CABIN_SWEEP). It enters the Park anchor
    channel and cannot be screened here. It is a different quantity from the
    register's cabin-localization fraction f, which is a share of transmission
    events bounded by cabin_localization_ceiling; that one is emergent from
    berthing and confinement rather than set, so it is not a factor either.
  * The dose-response model family is categorical. Per spec section 2.2 the
    whole design is re-run per family (`--dose-family`) and the between-family
    spread is reported separately, never interpolated.

The observation model's ascertainment vectors are absent for the third reason
and are handled the same way. They are declared rather than sourced (#27) and
they are not separately identifiable, so they are not continuous factors: the
design is re-run per declared scenario (`--observation-scenario`, a member of
the profile's `observation_model.prior.scenarios`) and the between-scenario
spread is reported separately. A screen that ranged one reporting probability
over an interval would be sweeping a component of a ladder no observer could
exhibit.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.transmission_core import EMESIS_TOTAL_SHED_GEC_RANGE  # noqa: E402
from orchestrator_init import SCENARIO_VECTORS  # noqa: E402
from picard_framework.catalog.registry import CatalogRegistry  # noqa: E402
from picard_framework.pathogen_overrides import (  # noqa: E402
    load_pathogen_bundle,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    compute_derived_metrics,
    extract_timeseries,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

Transform = Literal["linear", "log10"]


@dataclass(frozen=True)
class Factor:
    """One continuous factor, its sourced interval, and where it lands."""

    name: str
    path: tuple[str, ...]
    low: float
    high: float
    transform: Transform
    grade: str

    def value(self, unit: float) -> float:
        """Map a unit-hypercube coordinate onto the sourced interval."""
        if self.transform == "log10":
            lo, hi = math.log10(self.low), math.log10(self.high)
            return 10.0 ** (lo + unit * (hi - lo))
        return self.low + unit * (self.high - self.low)


# Norovirus box, spec section 3.2. Every interval is the study spread or an
# explicitly declared plausible range, never a fitted width.
NOROVIRUS_FACTORS: tuple[Factor, ...] = (
    # secretor_negative_relative_susceptibility: susceptibility of a
    # secretor-negative (FUT2 non-secretor) host relative to a secretor. The
    # interval is genotype-specific, from Kambhampati et al. 2015's pooled
    # secretor:non-secretor odds ratios -- 9.9 (3.9-24.8) for GII.4 and
    # 2.2 (1.2-4.2) for GII non-4, i.e. relative susceptibility 0.10
    # (0.04-0.26) and 0.45 (0.24-0.83). The declared genotype mixture
    # GII.4 / GII.17 / GII.2 straddles both rows, so the box spans both:
    # [0.04, 0.83]. Its width is genotype composition, not measurement error
    # (docs/literature/consensus_tranche_6.md section 4). Grade B: measured for
    # GII in outbreak and challenge populations, not in this setting.
    # secretor_negative_fraction stays fixed at 0.20 and out of the box: it is
    # a demographic input (FUT2 se428 homozygote prevalence), not a biological
    # free parameter of the transmission model.
    Factor(
        "secretor_negative_relative_susceptibility",
        ("secretor_negative_relative_susceptibility",),
        0.04,
        0.83,
        "linear",
        "B",
    ),
    Factor(
        "contact_transfer_fraction",
        ("contact_transfer_fraction",),
        0.06,
        0.50,
        "linear",
        "B",
    ),
    # emesis_total_shed_gec: upper end of the per-subject cumulative emesis
    # shed interval. Kirby et al. 2016 Table 3 -- low end is the GII.2 mean plus
    # one SEM (1.8e7 + 1.8e7 = 3.6e7), high end the largest per-subject
    # cumulative mean the paper measures (GI.1, 3.1e8). Grade B: surrogate
    # genotype. This factor replaces the retired titre and volume factors: the
    # per-subject total is the quantity Kirby identifies, and titre x volume as
    # independent inputs overstates it 7.5x.
    Factor(
        "emesis_total_shed_gec",
        ("emesis_total_shed_gec_range", 1),
        3.6e7,
        3.1e8,
        "log10",
        "B",
    ),
    # hand_to_surface_drying_multiplier: drying state of the donor hand on the
    # deposit direction. Low end is Tuladhar 2013's dried/immediate ratio
    # (0.1% / 13% = 0.0077); high end is fully wet contact. Grade B. Which
    # drying state applies to a hand that is continuously recontaminated by its
    # own shedding is NOT measured, which is exactly why this enters as an axis
    # to be swept and not as a value.
    Factor(
        "hand_to_surface_drying_multiplier",
        ("hand_to_surface_drying_multiplier",),
        0.008,
        1.0,
        "log10",
        "B",
    ),
    # surface_decay_log10_per_day: span of the MNV-1 surrogate literature on
    # non-porous surfaces at indoor temperature, in the units it is measured
    # in. Low end 0.067 log10/day (Fallahi & Mattison 2011, ~1 log10 in 15 d on
    # stainless steel); high end 0.79 log10/day (Kim et al., 25 C / 50% RH,
    # provenance in doubt -- see docs/literature/consensus_tranche_5.md
    # section 1). Grade B: human norovirus is not culturable, so no direct
    # measurement exists. The conversion to the engine's fractional daily loss
    # lives at the resolution site in transmission_core._surface_survival.
    Factor(
        "surface_decay_log10_per_day",
        ("surface_decay_log10_per_day",),
        0.067,
        0.79,
        "linear",
        "B",
    ),
    Factor(
        "shedding_variance_log10",
        ("shedding_variance_log10",),
        0.5,
        1.5,
        "linear",
        "C",
    ),
    Factor(
        "environmental_faecal_release_log10_g_per_epoch",
        ("environmental_faecal_release_log10_g_per_epoch",),
        4.0,
        24.0,
        "linear",
        "D",
    ),
)

# Engine defaults for the profile keys a factor addresses by index. An
# indexed factor moves one end of a pair; the other end must keep the value
# the engine would otherwise use, not zero.
INDEXED_PATH_DEFAULTS: dict[str, tuple[float, ...]] = {
    "emesis_total_shed_gec_range": tuple(EMESIS_TOTAL_SHED_GEC_RANGE),
}

SCORED_OUTPUTS: tuple[str, ...] = (
    "attack_rate",
    "ever_ill_attack_rate_passenger",
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "vsp_posted",
    "peak_epoch",
)


def build_overrides(
    factors: Sequence[Factor],
    units: Sequence[float],
    pathogen_id: str,
) -> dict[str, dict[str, object]]:
    """Turn unit-hypercube coordinates into a pathogen override block."""
    profile: dict[str, object] = {}
    for factor, unit in zip(factors, units, strict=True):
        value = factor.value(float(unit))
        key = factor.path[0]
        if len(factor.path) == 1:
            profile[key] = value
            continue
        index = int(factor.path[1])
        current = profile.get(key)
        if not isinstance(current, list):
            default = INDEXED_PATH_DEFAULTS.get(key)
            if default is None:
                raise KeyError(f"no engine default recorded for indexed key {key!r}")
            current = list(default)
        pair = list(current)
        pair[index] = value
        profile[key] = pair
    return {pathogen_id: profile}


def observation_scenario_patch(
    bundle: str,
    pathogen_id: str,
    scenario: str,
) -> dict[str, object]:
    """The whole declared ascertainment ladder a named scenario stands for.

    Read from the profile rather than written here, because the screen selects
    no value: a scenario is a declaration the profile already carries. All
    three vectors and the active name move together, which is also what the
    loader requires of the resolved profile.
    """
    path = CatalogRegistry.from_repo(str(REPO_ROOT)).resolve_pathogen_bundle(bundle)
    profile = load_pathogen_bundle(path).get(pathogen_id, {})
    prior = (profile.get("observation_model") or {}).get("prior") or {}
    scenarios = prior.get("scenarios") or {}
    declared = scenarios.get(scenario)
    if declared is None:
        raise KeyError(
            f"{pathogen_id} declares no observation scenario {scenario!r}; "
            f"declared: {sorted(scenarios)}",
        )
    patch: dict[str, object] = {
        key: list(declared[key]) for key in SCENARIO_VECTORS
    }
    patch["prior"] = {"active_scenario": scenario}
    return patch


def run_point(
    factors: Sequence[Factor],
    units: Sequence[float],
    *,
    seed: int,
    pathogen_id: str,
    bundle: str,
    platform: str,
    epochs: int,
    num_agents: int,
    observation_scenario: str | None = None,
) -> dict[str, float]:
    """Run one design point at one seed and return the scored outputs."""
    overrides = build_overrides(factors, units, pathogen_id)
    if observation_scenario is not None:
        overrides[pathogen_id]["observation_model"] = observation_scenario_patch(
            bundle, pathogen_id, observation_scenario,
        )
    spec = {
        "schema_version": "1.0.0",
        "description": "bounded_screen",
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": int(seed),
            "num_epochs": int(epochs),
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
        "config_overrides": {"ship_graph": {"num_agents": int(num_agents)}},
        "pathogen_overrides": overrides,
    }
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
        result = ShipSimulation(picard_spec, display=False).run()
    derived = compute_derived_metrics(extract_timeseries(result.history), num_agents)
    scored = {
        name: float(derived.get(name, 0.0) or 0.0)
        for name in SCORED_OUTPUTS
        if name != "vsp_posted"
    }
    scored["vsp_posted"] = 1.0 if derived.get("vsp_trigger_epoch") is not None else 0.0
    return scored


def seed_mean(
    factors: Sequence[Factor],
    units: Sequence[float],
    seeds: Sequence[int],
    **run_kwargs: object,
) -> dict[str, float]:
    """Mean scored output over the shared seed set at one design point."""
    draws = [
        run_point(factors, units, seed=seed, **run_kwargs)  # type: ignore[arg-type]
        for seed in seeds
    ]
    return {
        name: statistics.fmean([draw[name] for draw in draws])
        for name in SCORED_OUTPUTS
    }


def morris_trajectory(
    k: int,
    rng: np.random.Generator,
    *,
    levels: int = 4,
) -> tuple[np.ndarray, list[int]]:
    """One Morris trajectory: k+1 points, each differing in one factor.

    Standard construction -- a random base point on the level grid, a random
    factor order, and a step of delta = p / (2 (p - 1)), which for p = 4 gives
    the 2/3 step that keeps every move inside the unit hypercube.
    """
    delta = levels / (2.0 * (levels - 1))
    grid = np.arange(levels) / (levels - 1.0)
    admissible = grid[grid <= 1.0 - delta + 1e-12]
    point = rng.choice(admissible, size=k)
    order = list(rng.permutation(k))
    points = [point.copy()]
    for index in order:
        point = point.copy()
        point[index] += delta
        points.append(point.copy())
    return np.array(points), order


def elementary_effects(
    factors: Sequence[Factor],
    trajectories: int,
    seeds: Sequence[int],
    rng: np.random.Generator,
    **run_kwargs: object,
) -> dict[str, dict[str, dict[str, float]]]:
    """Run the Morris design and return mu-star and sigma per factor/output."""
    levels = 4
    delta = levels / (2.0 * (levels - 1))
    effects: dict[str, dict[str, list[float]]] = {
        factor.name: {name: [] for name in SCORED_OUTPUTS} for factor in factors
    }
    for _ in range(trajectories):
        points, order = morris_trajectory(len(factors), rng, levels=levels)
        previous = seed_mean(factors, points[0], seeds, **run_kwargs)
        for step, index in enumerate(order, start=1):
            current = seed_mean(factors, points[step], seeds, **run_kwargs)
            for name in SCORED_OUTPUTS:
                effects[factors[index].name][name].append(
                    (current[name] - previous[name]) / delta,
                )
            previous = current
    return {
        factor_name: {
            name: {
                "mu_star": statistics.fmean([abs(v) for v in values]),
                "mu": statistics.fmean(values),
                "sigma": statistics.stdev(values) if len(values) > 1 else 0.0,
                "n": float(len(values)),
            }
            for name, values in per_output.items()
        }
        for factor_name, per_output in effects.items()
    }


def noise_floor(
    factors: Sequence[Factor],
    seeds: Sequence[int],
    **run_kwargs: object,
) -> dict[str, float]:
    """Seed-to-seed standard deviation of each output at the box centre."""
    centre = [0.5] * len(factors)
    draws = [
        run_point(factors, centre, seed=seed, **run_kwargs)  # type: ignore[arg-type]
        for seed in seeds
    ]
    return {
        name: statistics.stdev([draw[name] for draw in draws])
        if len(draws) > 1
        else 0.0
        for name in SCORED_OUTPUTS
    }


def _validated_cli_path(path: Path, root: Path) -> Path:
    """Resolve a CLI path under a fixed root before any filesystem access."""
    return Path(resolve_repo_path(str(root), str(path)))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Command line for the screen."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("floor", "screen"), default="screen")
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--bundle", default="active_profiles")
    parser.add_argument("--platform", default="mega_cruise_5000")
    parser.add_argument(
        "--observation-scenario",
        default=None,
        help=(
            "Name a declared observation_model.prior scenario to run the whole "
            "design under. Categorical: re-run per scenario and report the "
            "spread, never interpolate between them."
        ),
    )
    parser.add_argument("--num-agents", type=int, default=450)
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--trajectories", type=int, default=10)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--floor-seeds", type=int, default=20)
    parser.add_argument("--seed-base", type=int, default=500)
    parser.add_argument("--design-seed", type=int, default=17)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the floor or the screen and write the result as JSON."""
    args = parse_args(argv)
    factors = NOROVIRUS_FACTORS
    run_kwargs = {
        "pathogen_id": args.pathogen_id,
        "bundle": args.bundle,
        "platform": args.platform,
        "epochs": args.epochs,
        "num_agents": args.num_agents,
        "observation_scenario": args.observation_scenario,
    }
    if args.mode == "floor":
        seeds = [args.seed_base + i for i in range(args.floor_seeds)]
        payload: dict[str, object] = {
            "mode": "floor",
            "seeds": seeds,
            "noise_floor": noise_floor(factors, seeds, **run_kwargs),
        }
    else:
        seeds = [args.seed_base + i for i in range(args.seeds)]
        rng = np.random.default_rng(args.design_seed)
        payload = {
            "mode": "screen",
            "seeds": seeds,
            "trajectories": args.trajectories,
            "factors": [
                {
                    "name": f.name,
                    "low": f.low,
                    "high": f.high,
                    "transform": f.transform,
                    "grade": f.grade,
                }
                for f in factors
            ],
            "effects": elementary_effects(
                factors, args.trajectories, seeds, rng, **run_kwargs,
            ),
        }
    payload["run"] = run_kwargs
    report = json.dumps(payload, indent=2)
    with validated_open(
        str(_validated_cli_path(args.out, REPO_ROOT)),
        "w",
        allowed_roots=(str(REPO_ROOT),),
        encoding="utf-8",
    ) as handle:
        handle.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
