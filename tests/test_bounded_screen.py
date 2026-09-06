from __future__ import annotations

import json
import statistics
import tempfile
from pathlib import Path

import numpy as np
import pytest

from engines.transmission_core import EMESIS_TOTAL_SHED_GEC_RANGE
from picard_framework.pathogen_overrides import deep_merge_dict
from telemetry_buffer.observation_model import bounded_screen

PATHOGEN = "norwalk_gi"


def _factor(name: str) -> bounded_screen.Factor:
    for factor in bounded_screen.NOROVIRUS_FACTORS:
        if factor.name == name:
            return factor
    raise AssertionError(f"factor {name!r} is not in the norovirus box")


def _units_at(name: str, unit: float) -> list[float]:
    return [
        unit if factor.name == name else 0.0
        for factor in bounded_screen.NOROVIRUS_FACTORS
    ]


def test_linear_factor_maps_unit_endpoints_to_the_interval() -> None:
    factor = _factor("secretor_negative_relative_susceptibility")
    assert factor.value(0.0) == pytest.approx(factor.low)
    assert factor.value(1.0) == pytest.approx(factor.high)


def test_linear_factor_midpoint_is_the_arithmetic_mean() -> None:
    factor = _factor("secretor_negative_relative_susceptibility")
    expected = 0.5 * (factor.low + factor.high)
    assert factor.value(0.5) == pytest.approx(expected)


def test_log10_factor_maps_unit_endpoints_to_the_interval() -> None:
    factor = _factor("emesis_total_shed_gec")
    assert factor.value(0.0) == pytest.approx(factor.low)
    assert factor.value(1.0) == pytest.approx(factor.high)


def test_log10_factor_midpoint_is_the_geometric_mean() -> None:
    factor = _factor("emesis_total_shed_gec")
    expected = (factor.low * factor.high) ** 0.5
    assert factor.value(0.5) == pytest.approx(expected)


def test_log10_factor_is_monotone_increasing_in_the_unit_coordinate() -> None:
    factor = _factor("emesis_total_shed_gec")
    values = [factor.value(unit) for unit in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert values == sorted(values)


def test_overrides_land_under_the_pathogen_id() -> None:
    units = [0.5] * len(bounded_screen.NOROVIRUS_FACTORS)
    overrides = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS, units, PATHOGEN,
    )
    assert list(overrides) == [PATHOGEN]


def test_overrides_carry_every_factor_key() -> None:
    units = [0.5] * len(bounded_screen.NOROVIRUS_FACTORS)
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS, units, PATHOGEN,
    )[PATHOGEN]
    expected = {factor.path[0] for factor in bounded_screen.NOROVIRUS_FACTORS}
    assert set(profile) == expected


@pytest.mark.parametrize("unit", [0.0, 0.5, 1.0])
def test_indexed_emesis_pair_keeps_the_engine_lower_bound(unit: float) -> None:
    """The screened factor is the upper bound; the lower must not move.

    An earlier revision seeded the pair as [0.0, value], which silently moved
    the emesis pair's lower bound from the engine default to zero on every
    design point.
    """
    factor = _factor("emesis_total_shed_gec")
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at(factor.name, unit),
        PATHOGEN,
    )[PATHOGEN]
    pair = profile["emesis_total_shed_gec_range"]
    assert pair[0] == pytest.approx(EMESIS_TOTAL_SHED_GEC_RANGE[0])


@pytest.mark.parametrize("unit", [0.0, 0.5, 1.0])
def test_indexed_emesis_pair_carries_the_screened_upper_bound(unit: float) -> None:
    factor = _factor("emesis_total_shed_gec")
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at(factor.name, unit),
        PATHOGEN,
    )[PATHOGEN]
    pair = profile["emesis_total_shed_gec_range"]
    assert pair[1] == pytest.approx(factor.value(unit))


def test_unrecorded_indexed_key_raises_rather_than_defaulting() -> None:
    unknown = bounded_screen.Factor(
        name="unknown_pair_high",
        path=("unknown_pair", 1),
        low=1.0,
        high=2.0,
        transform="linear",
        grade="D",
    )
    with pytest.raises(KeyError, match="unknown_pair"):
        bounded_screen.build_overrides([unknown], [0.5], PATHOGEN)


@pytest.mark.parametrize(
    ("name", "block", "key"),
    [
        ("stool_events_baseline_per_day", "stool_events_per_day", "baseline"),
        ("stool_events_diarrhoeal_per_day", "stool_events_per_day", "diarrhoeal"),
        (
            "food_hand_contacts_per_day",
            "food_contamination",
            "hand_food_contacts_per_day",
        ),
        (
            "food_ingestion_fraction_per_day",
            "food_contamination",
            "ingestion_fraction_per_day",
        ),
    ],
)
@pytest.mark.parametrize("unit", [0.0, 0.5, 1.0])
def test_nested_factor_lands_at_its_declared_key(
    name: str,
    block: str,
    key: str,
    unit: float,
) -> None:
    factor = _factor(name)
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at(name, unit),
        PATHOGEN,
    )[PATHOGEN]
    nested = profile[block]
    assert isinstance(nested, dict)
    assert nested[key] == pytest.approx(factor.value(unit))


def test_nested_factors_sharing_a_block_both_land() -> None:
    """Two factors in one block compose rather than overwrite each other."""
    units = [
        1.0 if factor.name in {
            "stool_events_baseline_per_day",
            "stool_events_diarrhoeal_per_day",
        } else 0.0
        for factor in bounded_screen.NOROVIRUS_FACTORS
    ]
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS, units, PATHOGEN,
    )[PATHOGEN]
    assert profile["stool_events_per_day"] == {
        "baseline": pytest.approx(_factor("stool_events_baseline_per_day").high),
        "diarrhoeal": pytest.approx(
            _factor("stool_events_diarrhoeal_per_day").high,
        ),
    }


def test_nested_override_leaves_the_profile_siblings_standing() -> None:
    """A partial block must deep-merge, not replace the profile's own keys.

    The food block carries decay and handler multipliers the box does not
    address; a screen that replaced the block would silently drop them.
    """
    base = {PATHOGEN: {"food_contamination": {"decay_rate_per_day": 0.1}}}
    patch = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at("food_hand_contacts_per_day", 1.0),
        PATHOGEN,
    )
    merged = deep_merge_dict(base[PATHOGEN], patch[PATHOGEN])
    assert merged["food_contamination"]["decay_rate_per_day"] == pytest.approx(0.1)
    assert merged["food_contamination"]["hand_food_contacts_per_day"] == (
        pytest.approx(_factor("food_hand_contacts_per_day").high)
    )


def test_the_box_screens_the_repaired_faecal_and_food_mechanism() -> None:
    """The stool-event and food-route axes are in the box, once each.

    SYMP-EFF-01 made the defecation rate the only channel by which symptom
    status reaches the faecal chain, and FOOD-ARCH-01 made contacts and
    ingestion the food route's own quantities; a screen that omitted them
    would rank the model as it stood before either.
    """
    names = [factor.name for factor in bounded_screen.NOROVIRUS_FACTORS]
    for name in (
        "stool_events_baseline_per_day",
        "stool_events_diarrhoeal_per_day",
        "food_hand_contacts_per_day",
        "food_ingestion_fraction_per_day",
    ):
        assert names.count(name) == 1


def _constant_run_point(weights: dict[str, float]):
    """A simulation-free stand-in whose response is exactly linear in the box."""

    def run_point(
        factors: bounded_screen.Factor,
        units: list[float],
        **_kwargs: object,
    ) -> dict[str, float]:
        total = sum(
            weights[factor.name] * float(unit)
            for factor, unit in zip(factors, units, strict=True)
        )
        return dict.fromkeys(bounded_screen.SCORED_OUTPUTS, total)

    return run_point


def _seeded_run_point(values: dict[int, float], seen_units: list[list[float]]):
    """A simulation-free stand-in that varies with the seed alone."""

    def run_point(
        factors: bounded_screen.Factor,
        units: list[float],
        *,
        seed: int,
        **_kwargs: object,
    ) -> dict[str, float]:
        seen_units.append([float(unit) for unit in units])
        return dict.fromkeys(bounded_screen.SCORED_OUTPUTS, values[seed])

    return run_point


def test_morris_trajectory_has_one_point_per_factor_plus_the_base() -> None:
    points, _order = bounded_screen.morris_trajectory(7, np.random.default_rng(17))

    assert points.shape == (8, 7)


def test_morris_trajectory_moves_exactly_one_factor_per_step() -> None:
    points, _order = bounded_screen.morris_trajectory(7, np.random.default_rng(17))
    moved = [int(np.count_nonzero(b - a)) for a, b in zip(points, points[1:])]

    assert moved == [1] * 7


def test_morris_trajectory_step_is_the_two_thirds_delta() -> None:
    """delta = p / (2 (p - 1)) = 2/3 at p = 4, the published design."""
    points, order = bounded_screen.morris_trajectory(7, np.random.default_rng(17))
    steps = [
        float(points[step][index] - points[step - 1][index])
        for step, index in enumerate(order, start=1)
    ]

    assert steps == pytest.approx([2.0 / 3.0] * 7)


def test_morris_trajectory_never_steps_below_the_interval_floor() -> None:
    points, _order = bounded_screen.morris_trajectory(7, np.random.default_rng(23))

    assert float(points.min()) >= 0.0


def test_morris_trajectory_never_steps_above_the_interval_ceiling() -> None:
    points, _order = bounded_screen.morris_trajectory(7, np.random.default_rng(23))

    assert float(points.max()) <= 1.0


def test_morris_trajectory_moves_every_factor_exactly_once() -> None:
    _points, order = bounded_screen.morris_trajectory(7, np.random.default_rng(23))

    assert sorted(int(index) for index in order) == list(range(7))


def test_elementary_effects_recover_a_linear_response_slope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a response linear in the unit coordinates, mu-star is the slope."""
    weights = {
        factor.name: 1.0 + position
        for position, factor in enumerate(bounded_screen.NOROVIRUS_FACTORS)
    }
    monkeypatch.setattr(bounded_screen, "run_point", _constant_run_point(weights))

    effects = bounded_screen.elementary_effects(
        bounded_screen.NOROVIRUS_FACTORS, 2, [1], np.random.default_rng(3),
    )

    assert {
        name: per_output["attack_rate"]["mu_star"]
        for name, per_output in effects.items()
    } == pytest.approx(weights)


def test_elementary_effects_rank_a_stronger_factor_above_a_weaker_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    weights = dict.fromkeys(
        (factor.name for factor in bounded_screen.NOROVIRUS_FACTORS), 0.1,
    )
    weights["emesis_total_shed_gec"] = 5.0
    monkeypatch.setattr(bounded_screen, "run_point", _constant_run_point(weights))

    effects = bounded_screen.elementary_effects(
        bounded_screen.NOROVIRUS_FACTORS, 2, [1], np.random.default_rng(5),
    )
    ranked = sorted(
        effects,
        key=lambda name: effects[name]["ever_ill_attack_rate_passenger"]["mu_star"],
        reverse=True,
    )

    assert ranked[0] == "emesis_total_shed_gec"


def test_elementary_effects_report_no_spread_for_a_linear_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sigma is the trajectory-to-trajectory spread; a linear box has none."""
    weights = dict.fromkeys(
        (factor.name for factor in bounded_screen.NOROVIRUS_FACTORS), 2.0,
    )
    monkeypatch.setattr(bounded_screen, "run_point", _constant_run_point(weights))

    effects = bounded_screen.elementary_effects(
        bounded_screen.NOROVIRUS_FACTORS, 3, [1], np.random.default_rng(7),
    )

    assert effects["surface_decay_log10_per_day"]["attack_rate"]["sigma"] == pytest.approx(
        0.0,
    )


def test_elementary_effects_count_one_effect_per_factor_per_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    weights = dict.fromkeys(
        (factor.name for factor in bounded_screen.NOROVIRUS_FACTORS), 1.0,
    )
    monkeypatch.setattr(bounded_screen, "run_point", _constant_run_point(weights))

    effects = bounded_screen.elementary_effects(
        bounded_screen.NOROVIRUS_FACTORS, 4, [1], np.random.default_rng(9),
    )

    first = bounded_screen.NOROVIRUS_FACTORS[0].name
    assert effects[first]["vsp_posted"]["n"] == pytest.approx(4.0)


def test_noise_floor_is_the_seed_to_seed_standard_deviation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {500: 0.01, 501: 0.02, 502: 0.06}
    monkeypatch.setattr(
        bounded_screen, "run_point", _seeded_run_point(values, []),
    )

    floor = bounded_screen.noise_floor(bounded_screen.NOROVIRUS_FACTORS, list(values))

    assert floor["attack_rate"] == pytest.approx(statistics.stdev(values.values()))


def test_noise_floor_samples_the_box_centre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[float]] = []
    monkeypatch.setattr(
        bounded_screen, "run_point", _seeded_run_point({500: 0.0, 501: 1.0}, seen),
    )

    bounded_screen.noise_floor(bounded_screen.NOROVIRUS_FACTORS, [500, 501])

    assert seen == [[0.5] * len(bounded_screen.NOROVIRUS_FACTORS)] * 2


def test_noise_floor_of_a_single_seed_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bounded_screen, "run_point", _seeded_run_point({500: 0.4}, []),
    )

    floor = bounded_screen.noise_floor(bounded_screen.NOROVIRUS_FACTORS, [500])

    assert floor["peak_epoch"] == pytest.approx(0.0)


def test_isolation_withdraws_every_other_pathogens_boarding() -> None:
    boarding = bounded_screen.withdraw_other_boarding(
        "active_profiles", PATHOGEN,
    )["boarding"]

    assert PATHOGEN not in boarding
    assert set(boarding) >= {"influenza_a", "sars_cov2_resp"}
    assert all(
        patch == {"enabled": False}
        for name, patch in boarding.items()
        if name != "enabled"
    )


def test_isolation_keeps_the_boarding_channel_itself_on() -> None:
    """The block replaces the config's section, so it carries the switch."""
    boarding = bounded_screen.withdraw_other_boarding(
        "active_profiles", PATHOGEN,
    )["boarding"]

    assert boarding["enabled"] is True


def test_isolation_of_a_pathogen_absent_from_the_bundle_is_refused() -> None:
    with pytest.raises(KeyError, match="declares no pathogen"):
        bounded_screen.withdraw_other_boarding("active_profiles", "not_a_pathogen")


def test_isolation_of_a_pathogen_that_does_not_board_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Withdrawing the others would leave the run with no arrival at all."""
    monkeypatch.setattr(
        bounded_screen,
        "load_pathogen_bundle",
        lambda path: {PATHOGEN: {}, "influenza_a": {"boarding": {}}},
    )

    with pytest.raises(KeyError, match="ships no boarding block"):
        bounded_screen.withdraw_other_boarding("active_profiles", PATHOGEN)


def _captured_spec(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Run one design point against a stub simulation and keep its spec."""
    seen: dict[str, object] = {}

    def _from_json(root: str, path: str) -> str:
        seen["spec"] = json.loads(Path(path).read_text(encoding="utf-8"))
        return "spec"

    class _Result:
        history: list[dict[str, object]] = []

    class _Sim:
        def __init__(self, spec: object, display: bool = False) -> None:
            self._spec = spec

        def run(self) -> _Result:
            return _Result()

    monkeypatch.setattr(
        bounded_screen.PicardRunSpec, "from_picard_json", staticmethod(_from_json),
    )
    monkeypatch.setattr(bounded_screen, "ShipSimulation", _Sim)
    monkeypatch.setattr(
        bounded_screen, "compute_derived_metrics", lambda ts, n: {},
    )
    monkeypatch.setattr(bounded_screen, "extract_timeseries", lambda history: [])
    return seen


def test_an_isolated_run_seeds_only_the_screened_pathogen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The scored outputs are host-level, so a co-seed would contaminate them."""
    seen = _captured_spec(monkeypatch)

    bounded_screen.run_point(
        bounded_screen.NOROVIRUS_FACTORS,
        [0.5] * len(bounded_screen.NOROVIRUS_FACTORS),
        seed=500,
        pathogen_id=PATHOGEN,
        bundle="active_profiles",
        platform="mega_cruise_5000",
        epochs=2,
        num_agents=10,
    )

    boarding = seen["spec"]["config_overrides"]["initiation"]["boarding"]
    assert boarding["influenza_a"] == {"enabled": False}
    assert PATHOGEN not in boarding
    assert "initial_infected" not in seen["spec"]["pathogen_overrides"][PATHOGEN]


def test_a_bundle_run_leaves_the_declared_seeding_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _captured_spec(monkeypatch)

    bounded_screen.run_point(
        bounded_screen.NOROVIRUS_FACTORS,
        [0.5] * len(bounded_screen.NOROVIRUS_FACTORS),
        seed=500,
        pathogen_id=PATHOGEN,
        bundle="active_profiles",
        platform="mega_cruise_5000",
        epochs=2,
        num_agents=10,
        co_seeded="bundle",
    )

    assert list(seen["spec"]["pathogen_overrides"]) == [PATHOGEN]
    assert "initiation" not in seen["spec"]["config_overrides"]


def test_the_recorded_run_declares_which_seeding_it_used(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        bounded_screen,
        "noise_floor",
        lambda factors, seeds, **_kwargs: dict.fromkeys(
            bounded_screen.SCORED_OUTPUTS, 0.0,
        ),
    )

    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        out = Path(directory) / "floor.json"
        bounded_screen.main(
            ["--mode", "floor", "--floor-seeds", "2", "--out", str(out)],
        )
        payload = json.loads(out.read_text(encoding="utf-8"))

    capsys.readouterr()

    assert payload["run"]["co_seeded"] == "isolated"


def test_parse_args_defaults_are_the_published_design() -> None:
    """Change-detector: these defaults are the executed pass on record."""
    args = bounded_screen.parse_args(["--out", "screen.json"])

    assert (
        args.mode,
        args.trajectories,
        args.seeds,
        args.floor_seeds,
        args.seed_base,
        args.design_seed,
        args.epochs,
        args.num_agents,
    ) == ("screen", 10, 5, 20, 500, 17, 168, 450)


def test_cli_output_paths_are_confined_to_the_repository_root() -> None:
    resolved = bounded_screen._validated_cli_path(
        Path("telemetry_buffer/screen.json"), bounded_screen.REPO_ROOT,
    )

    assert resolved == bounded_screen.REPO_ROOT / "telemetry_buffer/screen.json"


def test_cli_output_paths_reject_an_absolute_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        bounded_screen._validated_cli_path(
            tmp_path / "screen.json", bounded_screen.REPO_ROOT,
        )


def test_cli_output_paths_reject_a_relative_escape() -> None:
    with pytest.raises(ValueError, match="escapes"):
        bounded_screen._validated_cli_path(
            Path("../screen.json"), bounded_screen.REPO_ROOT,
        )


def test_floor_mode_writes_the_measured_floor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        bounded_screen,
        "noise_floor",
        lambda factors, seeds, **_kwargs: dict.fromkeys(
            bounded_screen.SCORED_OUTPUTS, 0.25,
        ),
    )

    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        out = Path(directory) / "floor.json"
        assert bounded_screen.main(
            ["--mode", "floor", "--floor-seeds", "3", "--out", str(out)],
        ) == 0
        payload = json.loads(out.read_text(encoding="utf-8"))

    capsys.readouterr()

    assert (payload["mode"], payload["seeds"], payload["noise_floor"]["attack_rate"]) == (
        "floor",
        [500, 501, 502],
        0.25,
    )


def test_screen_mode_writes_the_effects_and_the_declared_box(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        bounded_screen,
        "trajectory_differences",
        lambda factors, trajectories, seeds, rng, **_kwargs: {
            factor.name: {
                "attack_rate": [
                    {"trajectory": 0.0, "seeds": 2.0, "value": 1.0},
                    {"trajectory": 1.0, "seeds": 2.0, "value": -1.0},
                ],
            }
            for factor in factors
        },
    )

    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        out = Path(directory) / "screen.json"
        assert bounded_screen.main(
            ["--trajectories", "2", "--seeds", "2", "--out", str(out)],
        ) == 0
        payload = json.loads(out.read_text(encoding="utf-8"))

    capsys.readouterr()

    assert (
        payload["mode"],
        payload["seeds"],
        [entry["name"] for entry in payload["factors"]],
        sorted(payload["effects"]),
    ) == (
        "screen",
        [500, 501],
        [factor.name for factor in bounded_screen.NOROVIRUS_FACTORS],
        sorted(factor.name for factor in bounded_screen.NOROVIRUS_FACTORS),
    )


def _stub_seed_mean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a design point's score a cheap deterministic function of the point.

    The sharding claim is about which design points a worker evaluates and how
    the differences pool, not about the simulation, so the simulation is
    replaced by an arithmetic surrogate: identical shard arithmetic on a
    surrogate is the whole property under test.
    """
    def score(
        factors: list[bounded_screen.Factor],
        units: list[float],
        seeds: list[int],
        **_kwargs: object,
    ) -> dict[str, float]:
        weighted = sum((index + 1) * unit for index, unit in enumerate(units))
        return {
            name: weighted + 0.1 * position + 0.001 * len(seeds)
            for position, name in enumerate(bounded_screen.SCORED_OUTPUTS)
        }

    monkeypatch.setattr(bounded_screen, "seed_mean", score)


_SEEDS = [500, 501, 502, 503]


def _raw(
    trajectories: int,
    *,
    shard_count: int,
    shard_index: int,
    seed_shards: int = 1,
) -> dict[str, dict[str, list[bounded_screen.RawEffect]]]:
    return bounded_screen.trajectory_differences(
        bounded_screen.NOROVIRUS_FACTORS,
        trajectories,
        _SEEDS,
        np.random.default_rng(17),
        shard_count=shard_count,
        shard_index=shard_index,
        seed_shards=seed_shards,
    )


def _pooled(
    shards: list[dict[str, dict[str, list[bounded_screen.RawEffect]]]],
) -> dict[str, dict[str, list[float]]]:
    return bounded_screen.pool_effects(
        bounded_screen.merge_effects(shards), len(_SEEDS),
    )


def test_shards_partition_the_unsharded_design_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    whole = _pooled([_raw(6, shard_count=1, shard_index=0)])
    pooled = _pooled([_raw(6, shard_count=3, shard_index=i) for i in range(3)])

    for factor in bounded_screen.NOROVIRUS_FACTORS:
        for name in bounded_screen.SCORED_OUTPUTS:
            assert pooled[factor.name][name] == pytest.approx(
                whole[factor.name][name],
            )


def test_seed_block_shards_pool_to_the_unsharded_design(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3 trajectory rows x 2 seed blocks = 6 shards reproduce the whole."""
    _stub_seed_mean(monkeypatch)
    whole = _pooled([_raw(6, shard_count=1, shard_index=0)])
    pooled = _pooled([
        _raw(6, shard_count=6, shard_index=i, seed_shards=2) for i in range(6)
    ])

    for factor in bounded_screen.NOROVIRUS_FACTORS:
        for name in bounded_screen.SCORED_OUTPUTS:
            assert pooled[factor.name][name] == pytest.approx(
                whole[factor.name][name],
            )


def test_a_seed_sharded_worker_evaluates_only_its_seed_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    records = _raw(2, shard_count=2, shard_index=1, seed_shards=2)[
        bounded_screen.NOROVIRUS_FACTORS[0].name
    ]["attack_rate"]

    assert (
        sorted({int(r["trajectory"]) for r in records}),
        {int(r["seeds"]) for r in records},
    ) == ([0, 1], {2})


def test_a_missing_seed_block_is_refused_not_averaged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    shards = [_raw(2, shard_count=2, shard_index=0, seed_shards=2)]

    with pytest.raises(ValueError, match="pools 2 seeds, design has 4"):
        _pooled(shards)


def test_a_duplicated_seed_block_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    one = _raw(2, shard_count=2, shard_index=0, seed_shards=2)

    with pytest.raises(ValueError, match="pools 4 seeds, design has 2"):
        bounded_screen.pool_effects(
            bounded_screen.merge_effects([one, one]), 2,
        )


def test_seed_blocks_pool_by_a_seed_weighted_mean() -> None:
    pooled = bounded_screen.pool_effects(
        {"f": {"attack_rate": [
            {"trajectory": 0.0, "seeds": 1.0, "value": 1.0},
            {"trajectory": 0.0, "seeds": 3.0, "value": 5.0},
            {"trajectory": 1.0, "seeds": 4.0, "value": -2.0},
        ]}},
        4,
    )

    assert pooled["f"]["attack_rate"] == [4.0, -2.0]


@pytest.mark.parametrize(("shard_count", "seed_shards"), [(6, 4), (6, 0)])
def test_seed_shards_must_divide_the_shard_count(
    shard_count: int,
    seed_shards: int,
) -> None:
    with pytest.raises(ValueError, match="must divide"):
        bounded_screen.shard_coordinates(shard_count, 0, seed_shards)


def test_seed_shards_cannot_exceed_the_seeds() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        bounded_screen.seed_block(_SEEDS, 5, 0)


def test_shard_coordinates_lay_rows_of_seed_blocks() -> None:
    assert [
        bounded_screen.shard_coordinates(6, i, 2) for i in range(6)
    ] == [(3, 0, 0), (3, 0, 1), (3, 1, 0), (3, 1, 1), (3, 2, 0), (3, 2, 1)]


def test_legacy_whole_seed_effects_pool_as_complete_trajectories() -> None:
    pooled = bounded_screen.pool_effects(
        bounded_screen.merge_effects(
            [{"f": {"attack_rate": [1.0, 3.0]}}, {"f": {"attack_rate": [5.0]}}],
            4,
        ),
        4,
    )

    assert sorted(pooled["f"]["attack_rate"]) == [1.0, 3.0, 5.0]


def test_every_trajectory_lands_in_exactly_one_shard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    counts = [
        len(
            _raw(7, shard_count=3, shard_index=index)[
                bounded_screen.NOROVIRUS_FACTORS[0].name
            ]["attack_rate"],
        )
        for index in range(3)
    ]

    assert (counts, sum(counts)) == ([3, 2, 2], 7)


def test_merged_summary_equals_the_unsharded_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_seed_mean(monkeypatch)
    direct = bounded_screen.summarise_effects(
        _pooled([_raw(6, shard_count=1, shard_index=0)]),
    )
    merged = bounded_screen.summarise_effects(
        _pooled([_raw(6, shard_count=4, shard_index=i, seed_shards=2) for i in range(4)]),
    )
    name = bounded_screen.NOROVIRUS_FACTORS[1].name

    for statistic in ("mu_star", "mu", "sigma", "n"):
        assert merged[name]["attack_rate"][statistic] == pytest.approx(
            direct[name]["attack_rate"][statistic],
        )


@pytest.mark.parametrize(
    ("shard_count", "shard_index"),
    [(0, 0), (3, 3), (3, -1)],
)
def test_a_shard_outside_the_partition_is_refused(
    shard_count: int,
    shard_index: int,
) -> None:
    with pytest.raises(ValueError, match="outside"):
        _raw(2, shard_count=shard_count, shard_index=shard_index)


def test_batch_array_index_supplies_the_shard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_BATCH_JOB_ARRAY_INDEX", "5")

    assert bounded_screen.resolve_shard_index(8, None) == 5


def test_a_sharded_worker_without_an_index_refuses_to_guess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AWS_BATCH_JOB_ARRAY_INDEX", raising=False)

    with pytest.raises(SystemExit, match="shard-index"):
        bounded_screen.resolve_shard_index(8, None)


def _write_shard(directory: Path, index: int, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "mode": "screen",
        "seeds": [500, 501],
        "trajectories": 6,
        "design_seed": 17,
        "shard_count": 3,
        "shard_index": index,
        "run": {"pathogen_id": PATHOGEN},
        "raw_effects": {"f": {"attack_rate": [float(index)]}},
    }
    payload.update(overrides)
    path = directory / f"shard_{index}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_merge_refuses_two_shards_of_the_same_index() -> None:
    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        root = Path(directory)
        first = _write_shard(root, 1)
        duplicate = root / "again.json"
        duplicate.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")

        with pytest.raises(SystemExit, match="double-count"):
            bounded_screen.load_shard_reports([first, duplicate])


def test_merge_refuses_a_design_missing_a_shard() -> None:
    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        root = Path(directory)
        paths = [_write_shard(root, 0), _write_shard(root, 2)]

        with pytest.raises(SystemExit, match=r"shards \[1\] of 3 are absent"):
            bounded_screen.load_shard_reports(paths)


def test_merge_refuses_shards_drawn_from_different_designs() -> None:
    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        root = Path(directory)
        paths = [_write_shard(root, 0), _write_shard(root, 1, design_seed=99)]

        with pytest.raises(SystemExit, match="disagree on the design"):
            bounded_screen.load_shard_reports(paths)


def test_merge_mode_pools_the_shard_effects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory(dir=bounded_screen.REPO_ROOT) as directory:
        root = Path(directory)
        paths = [_write_shard(root, index) for index in (2, 0, 1)]
        out = root / "merged.json"
        argv = ["--mode", "merge", "--out", str(out), "--shards"]
        assert bounded_screen.main([*argv, *(str(path) for path in paths)]) == 0
        payload = json.loads(out.read_text(encoding="utf-8"))

    capsys.readouterr()

    assert (
        payload["merged_shards"],
        payload["effects"]["f"]["attack_rate"]["n"],
        payload["effects"]["f"]["attack_rate"]["mu"],
    ) == ([0, 1, 2], 3.0, 1.0)
