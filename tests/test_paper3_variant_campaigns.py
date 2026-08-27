"""Contract tests for the Paper 3 variant-surveillance campaigns (``vs*``).

Two properties matter more than any single count: a run must carry its clock arm
and incubation arm in its own id (so two data-generating processes cannot be
pooled by accident), and the arithmetic count must equal what the generator
actually yields (so an AWS submission is sized from the same numbers).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.runs.mega_cruise_campaign import variant_campaign  # noqa: E402
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    _campaign_parser,
    _resolve_manifest_clock,
    generate_tier_runs,
    load_manifest,
)
from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (  # noqa: E402
    summarize,
    tier_cartesian,
)

CAMPAIGN = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"

# (manifest filename, campaign id, expected total runs)
DESIGNS = (
    ("paper3_variant_emergence_v1_manifest.json", "paper3_variant_emergence_v1", 2000),
    ("paper3_federation_patrol_v1_manifest.json", "paper3_federation_patrol_v1", 996),
    (
        "paper3_fleet_network_value_v1_manifest.json",
        "paper3_fleet_network_value_v1",
        3000,
    ),
    (
        "paper3_investment_optimization_v1_manifest.json",
        "paper3_investment_optimization_v1",
        2000,
    ),
    ("paper3_risa_outbreak_v1_manifest.json", "paper3_risa_outbreak_v1", 502),
)

MANIFEST_IDS = [name for name, _campaign, _total in DESIGNS]


def _manifest(name: str) -> dict[str, Any]:
    return load_manifest(CAMPAIGN / name)


def _first(manifest: dict[str, Any], tier_id: str) -> tuple[str, dict[str, Any]]:
    return next(iter(generate_tier_runs(manifest, tier_id)))


@pytest.fixture()
def emergence() -> dict[str, Any]:
    return _manifest("paper3_variant_emergence_v1_manifest.json")


# --------------------------------------------------------------------------
# manifest shape
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "campaign", "total"), DESIGNS, ids=MANIFEST_IDS)
def test_design_manifest_is_self_describing(
    name: str, campaign: str, total: int,
) -> None:
    manifest = _manifest(name)
    assert manifest["campaign"] == campaign
    assert variant_campaign.manifest_clock(manifest) == variant_campaign.CLOCK_HOURS
    assert manifest["epoch_duration_hours"] == 1
    assert manifest["description"]
    for tier_id, tier in manifest["tiers"].items():
        assert tier_id.startswith("vs"), tier_id
        assert variant_campaign.tier_regime(tier) in variant_campaign.REGIMES
        arm = variant_campaign.incubation_arm(manifest, tier)
        assert arm in variant_campaign.INCUBATION_ARMS
        assert tier["seeds"], tier_id
        assert tier["voyage_days"], tier_id
        assert tier["pathogen"] in manifest["pathogen_configs"], tier_id
        for strategy in tier["surveillance_strategies"]:
            assert strategy in manifest["surveillance_configs"], tier_id
        # Every absolute number rides on an unpinned dose, so nothing may be
        # swept up by `--tier all` before the C1 hourly refit lands.
        assert tier["deferred"] is True, tier_id
        assert "C1 hourly refit" in tier["deferred_reason"]


@pytest.mark.parametrize(("name", "campaign", "total"), DESIGNS, ids=MANIFEST_IDS)
def test_arithmetic_count_equals_generated_count(
    name: str, campaign: str, total: int,
) -> None:
    manifest = _manifest(name)
    generated = 0
    for tier_id, tier in manifest["tiers"].items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == tier_cartesian(manifest, tier), tier_id
        generated += len(runs)
    assert generated == total
    wave1, wave2 = summarize(manifest)
    assert (wave1, wave2) == (0, total)


def test_five_designs_are_about_the_planned_scale() -> None:
    assert sum(total for _name, _campaign, total in DESIGNS) == 8498


@pytest.mark.parametrize(("name", "campaign", "total"), DESIGNS, ids=MANIFEST_IDS)
def test_run_ids_are_unique_within_a_design(
    name: str, campaign: str, total: int,
) -> None:
    manifest = _manifest(name)
    ids = [
        run_id
        for tier_id in manifest["tiers"]
        for run_id, _spec in generate_tier_runs(manifest, tier_id)
    ]
    assert len(set(ids)) == len(ids) == total


def test_run_ids_are_unique_across_the_five_designs() -> None:
    seen: set[str] = set()
    for name, _campaign, _total in DESIGNS:
        manifest = _manifest(name)
        for tier_id in manifest["tiers"]:
            for run_id, _spec in generate_tier_runs(manifest, tier_id):
                assert run_id not in seen, run_id
                seen.add(run_id)
    assert len(seen) == 8498


def test_regimes_cover_the_planned_sweep() -> None:
    by_design = {
        name: {
            variant_campaign.tier_regime(tier)
            for tier in _manifest(name)["tiers"].values()
        }
        for name, _campaign, _total in DESIGNS
    }
    # Mutational supply is swept in both regimes, never fixed at nominal only.
    for name, regimes in by_design.items():
        if name == "paper3_investment_optimization_v1_manifest.json":
            assert regimes == {"investment"}
        else:
            assert {"diversity", "emergence"} <= regimes, name
    assert set().union(*by_design.values()) == set(variant_campaign.REGIMES)


def test_emergence_design_carries_both_sensitivity_tiers(
    emergence: dict[str, Any],
) -> None:
    tiers = emergence["tiers"]
    interference = tiers["vs3_coinfection_interference_norovirus"]
    recombination = tiers["vs4_recombination_norovirus"]
    assert len(interference["superinfection_susceptibilities"]) == 5
    assert len(recombination["recombination_rates_per_day"]) == 5
    # Both sensitivity axes are crossed with voyage length.
    assert interference["voyage_days"] == [7, 14]
    assert recombination["voyage_days"] == [7, 14]


def test_diversity_arm_embarks_one_to_four_founders(
    emergence: dict[str, Any],
) -> None:
    tier = emergence["tiers"]["vs1_diversity_norovirus"]
    assert tier["founder_strains"] == [1, 2, 3, 4]
    assert "mutation_rates" not in tier  # nominal per-pathogen rates
    founders = {
        spec["campaign_parameters"]["founder_strains"]
        for _run_id, spec in generate_tier_runs(
            emergence, "vs1_diversity_norovirus",
        )
    }
    assert founders == {1, 2, 3, 4}


def test_emergence_arm_sweeps_two_decades_from_one_founder(
    emergence: dict[str, Any],
) -> None:
    tier = emergence["tiers"]["vs2_emergence_transmission_norovirus"]
    assert tier["founder_strains"] == [1]
    rates = tier["mutation_rates"]
    assert rates[-1] / rates[0] == pytest.approx(100.0, rel=0.05)
    assert 0.02 in rates  # the profile's nominal per-transmission rate


# --------------------------------------------------------------------------
# arms reach the generated spec
# --------------------------------------------------------------------------


def test_clock_and_incubation_arm_are_in_every_run_id(
    emergence: dict[str, Any],
) -> None:
    run_id, spec = _first(emergence, "vs1_diversity_norovirus")
    assert "_hrs_dist_" in run_id
    params = spec["campaign_parameters"]
    assert params["natural_history_clock"] == "hours"
    assert params["incubation_arm"] == "distribution"
    assert spec["config_overrides"]["natural_history_clock"] == "hours"


def test_legacy_clock_arm_cannot_pool_with_the_hourly_arm(
    emergence: dict[str, Any],
) -> None:
    legacy = copy.deepcopy(emergence)
    legacy["natural_history_clock"] = variant_campaign.CLOCK_LEGACY_EPOCH_DAY
    hourly_ids = {
        run_id for run_id, _s in generate_tier_runs(emergence, "vs1_diversity_norovirus")
    }
    legacy_runs = dict(generate_tier_runs(legacy, "vs1_diversity_norovirus"))
    assert not hourly_ids & set(legacy_runs)
    run_id, spec = next(iter(legacy_runs.items()))
    assert "_legacy_" in run_id
    assert spec["config_overrides"]["natural_history_clock"] == "legacy_epoch_day"


def test_fixed_onset_arm_strips_incubation_and_relabels(
    emergence: dict[str, Any],
) -> None:
    dist_id, dist_spec = _first(emergence, "vs1_diversity_norovirus")
    fixed_id, fixed_spec = _first(emergence, "vs5_fixed_onset_control_norovirus")
    assert "_dist_" in dist_id
    assert "_fixed_" in fixed_id
    assert fixed_spec["campaign_parameters"]["incubation_arm"] == "fixed_onset"
    assert "add" not in dist_spec["pathogen_overrides"]
    added = fixed_spec["pathogen_overrides"]["add"]
    assert [p["pathogen_id"] for p in added] == ["norwalk_gi"]
    assert "incubation" not in added[0]
    resolved = PicardRunSpec.from_picard_dict(str(REPO_ROOT), fixed_spec)
    assert "incubation" not in resolved.pathogen_profiles["norwalk_gi"]
    resolved_dist = PicardRunSpec.from_picard_dict(str(REPO_ROOT), dist_spec)
    assert "incubation" in resolved_dist.pathogen_profiles["norwalk_gi"]


def test_swept_rates_reach_the_pathogen_profile(emergence: dict[str, Any]) -> None:
    seen: dict[float, str] = {}
    for run_id, spec in generate_tier_runs(
        emergence, "vs2_emergence_transmission_norovirus",
    ):
        patch = spec["pathogen_overrides"]["norwalk_gi"]["strain_evolution"]
        rate = patch["mutation_rate"]
        seen.setdefault(rate, run_id)
        assert spec["campaign_parameters"]["mutation_rate"] == rate
        profile = PicardRunSpec.from_picard_dict(
            str(REPO_ROOT), spec,
        ).pathogen_profiles["norwalk_gi"]
        assert profile["strain_evolution"]["mutation_rate"] == rate
        # A patched rate must not disturb the rest of strain_evolution.
        assert profile["strain_evolution"]["recombination_rate_per_day"] == pytest.approx(
            0.01,
        )
    assert set(seen) == set(
        emergence["tiers"]["vs2_emergence_transmission_norovirus"]["mutation_rates"],
    )
    assert len(set(seen.values())) == len(seen)


def test_within_host_and_interference_axes_are_independent(
    emergence: dict[str, Any],
) -> None:
    _wid, within = _first(emergence, "vs2_emergence_within_host_norovirus")
    _iid, interference = _first(emergence, "vs3_coinfection_interference_norovirus")
    within_patch = within["pathogen_overrides"]["norwalk_gi"]["strain_evolution"]
    inter_patch = interference["pathogen_overrides"]["norwalk_gi"]["strain_evolution"]
    assert set(within_patch) == {"within_host_mutation_rate_per_day"}
    assert set(inter_patch) == {"superinfection_susceptibility"}


def test_voyage_length_sets_epochs_from_the_declared_epoch_duration(
    emergence: dict[str, Any],
) -> None:
    by_days: dict[int, set[int]] = {}
    for _run_id, spec in generate_tier_runs(emergence, "vs1_diversity_norovirus"):
        params = spec["campaign_parameters"]
        by_days.setdefault(params["voyage_days"], set()).add(params["num_epochs"])
    assert by_days == {7: {168}, 10: {240}, 14: {336}}


def test_epoch_duration_is_honoured_rather_than_a_literal_24() -> None:
    manifest = {"epoch_duration_hours": 2}
    assert variant_campaign.epochs_for_days(manifest, 7) == 84
    assert variant_campaign.epochs_for_days({}, 7) == 168
    assert variant_campaign.epochs_for_days({"epoch_duration_hours": 24}, 3) == 3


def test_wastewater_channel_is_rebound_to_the_tier_pathogen() -> None:
    manifest = _manifest("paper3_variant_emergence_v1_manifest.json")
    _rid, sars = _first(manifest, "vs1_diversity_sars_cov2")
    ww = sars["config_overrides"]["wastewater_surveillance"]
    assert (ww["pathogen"], ww["pathogen_id"]) == ("SARS-CoV-2", "sars_cov2_resp")
    risa = _manifest("paper3_risa_outbreak_v1_manifest.json")
    _bid, baseline = _first(risa, "vs1_risa_diversity_protomorphosis")
    assert "wastewater_surveillance" not in baseline["config_overrides"]


def test_variant_surveillance_is_enabled_with_the_founder_count(
    emergence: dict[str, Any],
) -> None:
    for _run_id, spec in generate_tier_runs(emergence, "vs1_diversity_norovirus"):
        block = spec["config_overrides"]["variant_surveillance"]
        assert block["enabled"] is True
        assert block["census_interval_hours"] == 6
        assert (
            block["founder_strains_per_pathogen"]
            == spec["campaign_parameters"]["founder_strains"]
        )


def test_full_investment_tier_keeps_surface_sampling_alongside_founders() -> None:
    manifest = _manifest("paper3_investment_optimization_v1_manifest.json")
    for run_id, spec in generate_tier_runs(
        manifest, "vs6_investment_long_voyage_norovirus",
    ):
        if "inv_full" in run_id:
            block = spec["config_overrides"]["variant_surveillance"]
            assert block["surface_sampling"] == {"enabled": True}
            assert block["enabled"] is True
            return
    pytest.fail("no inv_full run generated")


def test_overrides_do_not_leak_between_runs(emergence: dict[str, Any]) -> None:
    specs = [
        spec
        for _run_id, spec in generate_tier_runs(
            emergence, "vs4_recombination_norovirus",
        )
    ]
    removes = {json.dumps(s["pathogen_overrides"]["remove"]) for s in specs}
    assert removes == {json.dumps(["sars_cov2_resp"])}
    base = emergence["pathogen_configs"]["norovirus"]["overrides"]
    assert base == {"remove": ["sars_cov2_resp"]}  # manifest never mutated


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


def _tier(**over: Any) -> dict[str, Any]:
    tier: dict[str, Any] = {
        "regime": "diversity",
        "pathogen": "norovirus",
        "platforms": ["classic_cruise_1900"],
        "voyage_days": [7],
        "seeds": [1],
        "surveillance_strategies": ["inv_baseline"],
    }
    tier.update(over)
    return tier


def test_manifest_without_a_clock_is_refused() -> None:
    with pytest.raises(variant_campaign.VariantManifestError, match="clock"):
        variant_campaign.manifest_clock({})


def test_unknown_clock_is_refused() -> None:
    with pytest.raises(variant_campaign.VariantManifestError, match="hours"):
        variant_campaign.manifest_clock({"natural_history_clock": "days"})


def test_manifest_without_an_incubation_arm_is_refused() -> None:
    with pytest.raises(variant_campaign.VariantManifestError, match="incubation_arm"):
        variant_campaign.incubation_arm({}, _tier())


def test_tier_incubation_arm_overrides_the_manifest_default() -> None:
    manifest = {"incubation_arm": "distribution"}
    assert variant_campaign.incubation_arm(manifest, _tier()) == "distribution"
    assert (
        variant_campaign.incubation_arm(
            manifest, _tier(incubation_arm="fixed_onset"),
        )
        == "fixed_onset"
    )
    with pytest.raises(variant_campaign.VariantManifestError, match="tier"):
        variant_campaign.incubation_arm(manifest, _tier(incubation_arm="none"))


def test_tier_without_a_regime_is_refused() -> None:
    tier = _tier()
    del tier["regime"]
    with pytest.raises(variant_campaign.VariantManifestError, match="regime"):
        variant_campaign.tier_regime(tier)
    with pytest.raises(variant_campaign.VariantManifestError, match="regime"):
        variant_campaign.tier_regime(_tier(regime="vibes"))


def test_tier_without_voyage_days_is_refused() -> None:
    tier = _tier()
    del tier["voyage_days"]
    with pytest.raises(variant_campaign.VariantManifestError, match="voyage_days"):
        variant_campaign.tier_axes({"platform": "x"}, tier)


def test_empty_or_malformed_axis_is_refused() -> None:
    with pytest.raises(variant_campaign.VariantManifestError, match="mutation_rates"):
        variant_campaign.tier_axes({}, _tier(mutation_rates=[]))
    with pytest.raises(variant_campaign.VariantManifestError, match="mutation_rates"):
        variant_campaign.tier_axes({}, _tier(mutation_rates=0.02))


def test_nonsensical_voyage_lengths_are_refused() -> None:
    with pytest.raises(variant_campaign.VariantManifestError, match="positive"):
        variant_campaign.epochs_for_days({"epoch_duration_hours": 0}, 7)
    with pytest.raises(variant_campaign.VariantManifestError, match="voyage_days"):
        variant_campaign.epochs_for_days({}, 0)
    with pytest.raises(variant_campaign.VariantManifestError, match="under one epoch"):
        variant_campaign.epochs_for_days({"epoch_duration_hours": 1000}, 1)


def test_fixed_onset_control_needs_a_profile_that_has_an_incubation_block() -> None:
    profile = variant_campaign.fixed_onset_profile("active_profiles", "norwalk_gi")
    assert "incubation" not in profile
    assert profile["pathogen_id"] == "norwalk_gi"
    with pytest.raises(variant_campaign.VariantManifestError, match="no profile"):
        variant_campaign.fixed_onset_profile("active_profiles", "not_a_pathogen")


def test_fixed_onset_control_refuses_a_profile_that_would_be_a_no_op() -> None:
    # 13 of 15 shipped profiles still use the fixed 1-day fallback: stripping
    # nothing from them would label a control arm that changes no behaviour.
    with pytest.raises(variant_campaign.VariantManifestError, match="no-op"):
        variant_campaign.fixed_onset_profile(
            "edison_10pathogen_profiles", "measles_virus",
        )


def test_strip_incubation_leaves_everything_else_alone() -> None:
    profile = {"pathogen_id": "x", "incubation": {"median_days": 1.2}, "recovery_day": 3}
    assert variant_campaign.strip_incubation(profile) == {
        "pathogen_id": "x",
        "recovery_day": 3,
    }


def test_platform_and_seed_overrides_narrow_the_grid(
    emergence: dict[str, Any],
) -> None:
    tier = emergence["tiers"]["vs1_diversity_norovirus"]
    axes = variant_campaign.tier_axes(
        emergence, tier, platform_override="spirit_cruise_3000",
    )
    assert axes["platform"] == ("spirit_cruise_3000",)
    fallback = variant_campaign.tier_axes(
        {"platform": "mega_cruise_5000", "defaults": {"voyage_days": [7]}},
        _tier(platforms=None, voyage_days=None) | {"seeds": [1]},
    )
    assert fallback["platform"] == ("mega_cruise_5000",)
    assert fallback["founder_strains"] == (1,)


def test_single_platform_key_is_accepted() -> None:
    axes = variant_campaign.tier_axes(
        {}, _tier(platforms=None, platform="classic_cruise_1900"),
    )
    assert axes["platform"] == ("classic_cruise_1900",)


# --------------------------------------------------------------------------
# runner-level clock reconciliation
# --------------------------------------------------------------------------


def _args(clock: str | None) -> Any:
    parser = _campaign_parser()
    argv = ["--dry-run"]
    if clock is not None:
        argv += ["--natural-history-clock", clock]
    return parser.parse_args(argv)


def test_manifest_clock_is_adopted_when_the_cli_is_silent(
    emergence: dict[str, Any],
) -> None:
    assert _resolve_manifest_clock(emergence, _args(None)) == "hours"


def test_agreeing_cli_clock_is_accepted(emergence: dict[str, Any]) -> None:
    assert _resolve_manifest_clock(emergence, _args("hours")) == "hours"


def test_disagreeing_cli_clock_is_refused(emergence: dict[str, Any]) -> None:
    with pytest.raises(SystemExit, match="mismatch"):
        _resolve_manifest_clock(emergence, _args("legacy_epoch_day"))


def test_manifest_with_a_bogus_clock_is_refused() -> None:
    with pytest.raises(SystemExit, match="natural_history_clock"):
        _resolve_manifest_clock({"natural_history_clock": "weeks"}, _args(None))


def test_legacy_manifests_keep_the_cli_as_the_only_clock_source() -> None:
    manifest = load_manifest(CAMPAIGN / "campaign_manifest.json")
    assert "natural_history_clock" not in manifest
    assert _resolve_manifest_clock(manifest, _args(None)) is None
    assert _resolve_manifest_clock(manifest, _args("hours")) == "hours"


def test_existing_tier_families_are_untouched_by_the_vs_count_branch() -> None:
    manifest = load_manifest(CAMPAIGN / "vsp_degradation_v1_manifest.json")
    assert tier_cartesian(manifest, manifest["tiers"]["vd1_vsp_threshold"]) == 840
