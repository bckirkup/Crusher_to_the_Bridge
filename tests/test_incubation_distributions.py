"""Incubation is drawn per host, conditioned on dose and biology (Paper 3).

The previous model gave every host of a pathogen the same onset day, which made
symptom onset a property of the pathogen alone: detection timing could not
respond to how much a host swallowed, to who the host was, or to a variant's
incubation phenotype below the baseline. These tests hold the replacement to
the standards that matter for a surveillance claim — the marginal distribution
reproduces its literature median and dispersion, each conditioning term moves
onset in the documented direction and only in that direction, the draw happens
once per infection, and a pathogen without a distribution keeps the old fixed
day exactly.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import jsonschema
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.incubation import (  # noqa: E402
    DISTRIBUTION_GAMMA,
    MAX_DOSE_FACTOR,
    MIN_DOSE_FACTOR,
    HostIncubationFactors,
    HostIncubationState,
    IncubationModel,
    host_incubation_state,
)
from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    KorkinAgent,
)
from engines.natural_history import (  # noqa: E402
    ONSET_DAY,
    advance_infections,
    incubation_days,
)
from engines.strain_state import ImmuneRecord, Phenotype  # noqa: E402
from tools.sanity_checker import (  # noqa: E402
    PathogenProfile,
    PathogensFile,
    Report,
    _check_incubation_models,
)

PATHOGEN = "norwalk_gi"
RESPIRATORY = "sars_cov2_resp"
INFLUENZA = "influenza_a"
NEUTRAL_HOST = HostIncubationState()
REFERENCE_DOSE = 1e4
SAMPLE_SIZE = 4000


def _profile(pathogen_id: str = PATHOGEN) -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = next(p for p in data["pathogens"] if p["pathogen_id"] == pathogen_id)
    return copy.deepcopy(profile)


def _edison_profile(pathogen_id: str = INFLUENZA) -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/edison_10pathogen_profiles.json").read_text(),
    )
    profile = next(p for p in data["pathogens"] if p["pathogen_id"] == pathogen_id)
    return copy.deepcopy(profile)


def _agent(aid: int = 1) -> KorkinAgent:
    return KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone="Cabin_A",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="Cabin_A",
        schedule=["Cabin_A"] * 24,
    )


def _model(**overrides: object) -> IncubationModel:
    block: dict[str, object] = {
        "distribution": "lognormal",
        "median_days": 2.0,
        "dispersion": 1.5,
        "min_days": 0.0,
        "max_days": 60.0,
        "dose_reference_log10": 4.0,
    }
    block.update(overrides)
    model = IncubationModel.from_mapping(block)
    assert model is not None
    return model


def _draws(model: IncubationModel, *, host: HostIncubationState = NEUTRAL_HOST,
           dose: float = REFERENCE_DOSE, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.array([
        model.sample_days(dose=dose, host=host, rng=rng)
        for _ in range(SAMPLE_SIZE)
    ])


# ── Configuration ───────────────────────────────────────────────────────

class TestModelConfiguration:
    def test_absent_block_is_the_legacy_path(self) -> None:
        assert IncubationModel.from_mapping(None) is None
        assert IncubationModel.from_mapping({}) is None

    def test_median_is_required(self) -> None:
        with pytest.raises(ValueError, match="median_days"):
            IncubationModel.from_mapping({"dispersion": 1.4})

    def test_unknown_distribution_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="distribution"):
            _model(distribution="weibull")

    def test_lognormal_dispersion_must_exceed_one(self) -> None:
        """A GSD of 1 is a point mass, which is the model this replaces."""
        with pytest.raises(ValueError, match="geometric"):
            _model(dispersion=1.0)

    def test_gamma_accepts_a_coefficient_of_variation_below_one(self) -> None:
        model = _model(distribution=DISTRIBUTION_GAMMA, dispersion=0.5)
        assert model.dispersion == pytest.approx(0.5)

    def test_non_positive_median_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="median_days"):
            _model(median_days=0.0)

    def test_window_must_be_ordered(self) -> None:
        with pytest.raises(ValueError, match="max_days"):
            _model(min_days=5.0, max_days=5.0)

    def test_negative_lower_bound_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="min_days"):
            _model(min_days=-1.0)

    def test_non_positive_gamma_dispersion_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="dispersion"):
            _model(distribution=DISTRIBUTION_GAMMA, dispersion=0.0)

    def test_negative_dose_term_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="dose_log10_shortening"):
            _model(dose_log10_shortening=-0.1)

    def test_non_positive_host_factor_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="immunocompromised"):
            _model(host_factors={"immunocompromised": 0.0})

    def test_non_positive_age_factor_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="age_bands.senior"):
            _model(host_factors={"age_bands": {"senior": -1.0}})

    def test_a_misspelled_parameter_is_rejected_not_defaulted(self) -> None:
        """Silently defaulting a typo would move onset with nothing to show it."""
        with pytest.raises(ValueError, match=r"unknown keys.*dispresion"):
            _model(dispresion=1.8)

    def test_a_misspelled_host_factor_is_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"host_factors has unknown keys"):
            _model(host_factors={"immunosuppressed": 1.2})

    def test_the_median_must_sit_inside_the_truncation_window(self) -> None:
        """A median at or past a bound makes the typical host present at the
        clamp, so the profile's literature anchor stops being observable."""
        with pytest.raises(ValueError, match="truncation window"):
            _model(median_days=6.0, min_days=1.0, max_days=6.0)
        with pytest.raises(ValueError, match="truncation window"):
            _model(median_days=1.0, min_days=1.0, max_days=6.0)


# ── Marginal distribution ───────────────────────────────────────────────

class TestMarginalDistribution:
    def test_lognormal_recovers_its_median(self) -> None:
        drawn = _draws(_model(median_days=5.1, dispersion=1.6))
        assert float(np.median(drawn)) == pytest.approx(5.1, rel=0.05)

    def test_lognormal_recovers_its_dispersion(self) -> None:
        """The geometric standard deviation is the width knob, so it must land."""
        drawn = _draws(_model(median_days=5.1, dispersion=1.6))
        gsd = math.exp(float(np.std(np.log(drawn))))
        assert gsd == pytest.approx(1.6, rel=0.06)

    def test_wider_dispersion_widens_the_onset_spread(self) -> None:
        tight = _draws(_model(dispersion=1.2))
        loose = _draws(_model(dispersion=2.0))
        assert float(np.std(loose)) > float(np.std(tight))

    def test_gamma_mean_matches_its_target(self) -> None:
        drawn = _draws(_model(distribution=DISTRIBUTION_GAMMA, median_days=5.0,
                              dispersion=0.6))
        assert float(np.mean(drawn)) == pytest.approx(5.0, rel=0.05)

    def test_draws_are_truncated_to_the_plausible_window(self) -> None:
        model = _model(median_days=1.2, dispersion=2.0, min_days=0.5, max_days=4.0)
        drawn = _draws(model)
        assert float(drawn.min()) >= 0.5
        assert float(drawn.max()) <= 4.0

    def test_draws_are_never_negative_for_a_short_incubation(self) -> None:
        drawn = _draws(_model(median_days=0.6, dispersion=1.9, min_days=0.0))
        assert float(drawn.min()) >= 0.0

    def test_the_same_seed_reproduces_the_same_period(self) -> None:
        model = _model()
        first = _draws(model, seed=5)
        second = _draws(model, seed=5)
        assert np.array_equal(first, second)


# ── Dose conditioning ───────────────────────────────────────────────────

class TestDoseConditioning:
    def test_no_dose_term_makes_the_median_dose_independent(self) -> None:
        model = _model(dose_log10_shortening=0.0)
        assert model.dose_factor(1e1) == pytest.approx(1.0)
        assert model.dose_factor(1e9) == pytest.approx(1.0)

    def test_reference_dose_leaves_the_median_alone(self) -> None:
        model = _model(dose_log10_shortening=0.1)
        assert model.dose_factor(REFERENCE_DOSE) == pytest.approx(1.0)

    def test_a_larger_inoculum_shortens_onset(self) -> None:
        model = _model(dose_log10_shortening=0.1)
        light = float(np.median(_draws(model, dose=1e3)))
        heavy = float(np.median(_draws(model, dose=1e6)))
        assert heavy < light

    def test_dose_response_is_graded_and_monotone(self) -> None:
        model = _model(dose_log10_shortening=0.08)
        medians = [
            float(np.median(_draws(model, dose=dose)))
            for dose in (1e2, 1e3, 1e4, 1e5, 1e6)
        ]
        assert medians == sorted(medians, reverse=True), medians
        assert medians[0] > medians[-1]

    def test_extreme_doses_cannot_abolish_the_incubation_period(self) -> None:
        """Bounds keep an implausible inoculum from producing same-day onset."""
        model = _model(dose_log10_shortening=0.5)
        assert model.dose_factor(1e30) == pytest.approx(MIN_DOSE_FACTOR)
        assert model.dose_factor(0.0) == pytest.approx(MAX_DOSE_FACTOR)

    def test_the_dose_floor_is_per_pathogen(self) -> None:
        """The spec gives each pathogen its own floor on how far a heavy
        inoculum may compress onset."""
        floors = [0.2, 0.3, 0.5]
        factors = [
            _model(dose_log10_shortening=0.5, dose_floor=floor).dose_factor(1e30)
            for floor in floors
        ]
        assert factors == pytest.approx(floors)

    def test_a_dose_floor_outside_the_unit_interval_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="dose_floor"):
            _model(dose_floor=0.0)
        with pytest.raises(ValueError, match="dose_floor"):
            _model(dose_floor=1.5)

    def test_a_zero_dose_is_handled_without_a_domain_error(self) -> None:
        model = _model(dose_log10_shortening=0.1)
        assert model.dose_factor(0.0) > 1.0


# ── Host conditioning ───────────────────────────────────────────────────

class TestHostConditioning:
    def test_neutral_host_has_no_effect(self) -> None:
        factors = HostIncubationFactors.from_mapping({
            "immunocompromised": 1.4, "prior_immunity": 1.2,
            "age_bands": {"senior": 1.3},
        })
        assert factors.multiplier(NEUTRAL_HOST) == pytest.approx(1.0)

    def test_immunosuppression_delays_presentation(self) -> None:
        model = _model(host_factors={"immunocompromised": 1.3})
        neutral = float(np.median(_draws(model)))
        immuno = float(np.median(
            _draws(model, host=HostIncubationState(immunocompromised=True)),
        ))
        assert immuno > neutral
        assert immuno == pytest.approx(1.3 * neutral, rel=0.05)

    def test_prior_immunity_delays_presentation(self) -> None:
        model = _model(host_factors={"prior_immunity": 1.25})
        neutral = float(np.median(_draws(model)))
        experienced = float(np.median(
            _draws(model, host=HostIncubationState(prior_immunity=True)),
        ))
        assert experienced > neutral

    def test_age_band_factors_apply_only_to_their_band(self) -> None:
        factors = HostIncubationFactors.from_mapping({
            "age_bands": {"child": 0.9, "senior": 1.2},
        })
        assert factors.multiplier(HostIncubationState(age_band="child")) == 0.9
        assert factors.multiplier(HostIncubationState(age_band="senior")) == 1.2
        assert factors.multiplier(HostIncubationState(age_band="adult")) == 1.0

    def test_unlisted_age_band_is_inert(self) -> None:
        """An unpopulated axis must not bias onset in either direction."""
        factors = HostIncubationFactors.from_mapping({"age_bands": {"senior": 1.2}})
        assert factors.multiplier(HostIncubationState(age_band="")) == 1.0

    def test_host_axes_compound(self) -> None:
        factors = HostIncubationFactors.from_mapping({
            "immunocompromised": 1.2, "prior_immunity": 1.1,
            "age_bands": {"senior": 1.5},
        })
        host = HostIncubationState(
            age_band="senior", immunocompromised=True, prior_immunity=True,
        )
        assert factors.multiplier(host) == pytest.approx(1.2 * 1.1 * 1.5)

    def test_dose_and_host_terms_compound_on_the_median(self) -> None:
        model = _model(median_days=4.0, dose_log10_shortening=0.1,
                       host_factors={"immunocompromised": 1.5})
        host = HostIncubationState(immunocompromised=True)
        expected = 4.0 * model.dose_factor(1e6) * 1.5
        assert model.conditional_median(1e6, host) == pytest.approx(expected)


# ── Reading host biology off an agent ───────────────────────────────────

class TestHostStateFromAgent:
    def test_a_fresh_agent_is_neutral(self) -> None:
        assert host_incubation_state(_agent(), PATHOGEN) == NEUTRAL_HOST

    def test_agent_attributes_are_read(self) -> None:
        agent = _agent()
        agent.age_band = "senior"
        agent.immunocompromised = True
        state = host_incubation_state(agent, PATHOGEN)
        assert state.age_band == "senior"
        assert state.immunocompromised is True

    def test_immune_history_counts_as_prior_immunity(self) -> None:
        agent = _agent()
        agent.record_immunity(ImmuneRecord(
            pathogen_id=PATHOGEN, genotype="GII.4", strain_id="s:1", epoch=3,
        ))
        assert host_incubation_state(agent, PATHOGEN).prior_immunity is True

    def test_immunity_to_another_pathogen_does_not_count(self) -> None:
        agent = _agent()
        agent.record_immunity(ImmuneRecord(
            pathogen_id=RESPIRATORY, genotype="BA.2", strain_id="s:9", epoch=3,
        ))
        assert host_incubation_state(agent, PATHOGEN).prior_immunity is False


# ── The progression seam ────────────────────────────────────────────────

def _onset_day(
    profile: dict,
    *,
    dose: float = 1e12,
    modifier: float = 0.0,
    seed: int = 3,
    agent: KorkinAgent | None = None,
) -> int:
    """First day post-infection on which symptoms appear.

    A large dose makes the illness draw all but certain, so what comes back is
    the incubation gate rather than a coin flip.
    """
    host = agent if agent is not None else _agent()
    host.infect_with_pathogen(
        PATHOGEN, dose, 0,
        strain_id="s:1",
        strain_phenotype=Phenotype(incubation_modifier=modifier),
    )
    prof = {**profile, "recovery_day": 40}
    rng = np.random.default_rng(seed)
    for _ in range(30):
        advance_infections(host, {PATHOGEN: prof}, rng)
        inf = host.infections[PATHOGEN]
        if inf["illness"] == IllnessStatus.SYMPTOMATIC:
            return int(inf["time_infected"])
    return -1


class TestProgressionSeam:
    def test_period_is_drawn_once_and_remembered(self) -> None:
        """A period redrawn each epoch would be a new host every day."""
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e6, 0)
        profile = _profile()
        rng = np.random.default_rng(1)
        first = incubation_days(agent, PATHOGEN, agent.infections[PATHOGEN],
                                 profile, rng)
        for _ in range(5):
            again = incubation_days(agent, PATHOGEN, agent.infections[PATHOGEN],
                                     profile, rng)
            assert again == first

    def test_hosts_of_one_pathogen_no_longer_share_an_onset_day(self) -> None:
        profile = _profile(RESPIRATORY)
        rng = np.random.default_rng(19)
        periods = set()
        for aid in range(40):
            agent = _agent(aid)
            agent.infect_with_pathogen(RESPIRATORY, 1e4, 0)
            periods.add(round(incubation_days(
                agent, RESPIRATORY, agent.infections[RESPIRATORY], profile, rng,
            ), 6))
        assert len(periods) > 1

    def test_a_pathogen_without_a_distribution_keeps_its_fixed_onset(self) -> None:
        profile = _profile()
        profile.pop("incubation")
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e12, 0)
        rng = np.random.default_rng(3)
        drawn = incubation_days(agent, PATHOGEN, agent.infections[PATHOGEN],
                                 profile, rng)
        assert drawn == pytest.approx(ONSET_DAY)

    def test_a_fixed_onset_day_is_still_honoured_without_a_distribution(self) -> None:
        profile = _profile()
        profile.pop("incubation")
        profile["symptom_onset_day"] = 4.0
        assert _onset_day(profile) == 4

    def test_the_modifier_does_not_perturb_the_host_draw(self) -> None:
        """Host biology and variant phenotype stay separable: the modifier is
        applied to the drawn period, it does not change what was drawn."""
        profile = _profile(RESPIRATORY)
        agent = _agent()
        agent.infect_with_pathogen(RESPIRATORY, 1e4, 0)
        inf = agent.infections[RESPIRATORY]
        rng = np.random.default_rng(7)
        base = incubation_days(agent, RESPIRATORY, inf, profile, rng)
        inf["strain_incubation_modifier"] = 2.0
        del inf["incubation_days"]
        rng = np.random.default_rng(7)
        assert incubation_days(agent, RESPIRATORY, inf, profile, rng) == base

    def test_the_variant_modifier_shifts_the_drawn_period(self) -> None:
        """The modifier moves this host's own period, not a shared onset day."""
        profile = _profile(RESPIRATORY)
        rng = np.random.default_rng(23)
        agent = _agent()
        agent.infect_with_pathogen(RESPIRATORY, 1e4, 0)
        inf = agent.infections[RESPIRATORY]
        drawn = incubation_days(agent, RESPIRATORY, inf, profile, rng)
        assert drawn > 1.0
        inf["strain_incubation_modifier"] = -drawn - 5.0
        from engines.natural_history import onset_day
        assert onset_day(agent, RESPIRATORY, inf, profile, rng) == 0.0

    def test_faster_variants_are_live_for_a_slow_pathogen(self) -> None:
        profile = _profile()
        onsets = [_onset_day(profile, dose=1e4, modifier=m, seed=41)
                  for m in (-1.0, 0.0, 2.0, 5.0)]
        assert all(day >= 0 for day in onsets), onsets
        assert onsets == sorted(onsets), onsets
        assert onsets[0] < onsets[-1]

    def test_a_heavier_exposure_presents_no_later_than_a_light_one(self) -> None:
        profile = _profile(RESPIRATORY)
        rng = np.random.default_rng(31)
        light = np.median([
            _period(profile, RESPIRATORY, dose=1e2, rng=rng) for _ in range(200)
        ])
        heavy = np.median([
            _period(profile, RESPIRATORY, dose=1e7, rng=rng) for _ in range(200)
        ])
        assert heavy < light

    def test_host_biology_is_inert_on_the_shipped_profiles(self) -> None:
        """The shipped profiles carry no host_factors on purpose (spec §3.3), so
        an immunocompromised host must present on the same schedule until a
        sensitivity arm turns the axis on."""
        profile = _profile(RESPIRATORY)
        neutral = np.median([
            _period(profile, RESPIRATORY, rng=np.random.default_rng(37 + i))
            for i in range(200)
        ])
        immuno = np.median([
            _period(profile, RESPIRATORY, rng=np.random.default_rng(37 + i),
                    immunocompromised=True)
            for i in range(200)
        ])
        assert immuno == pytest.approx(neutral)

    def test_a_host_factor_sensitivity_arm_delays_presentation(self) -> None:
        """Same profile, host axis switched on: the mechanism is live and only
        the configuration keeps it out of the main line."""
        profile = _profile(RESPIRATORY)
        profile["incubation"]["host_factors"] = {"immunocompromised": 1.3}
        neutral = np.median([
            _period(profile, RESPIRATORY, rng=np.random.default_rng(37 + i))
            for i in range(200)
        ])
        immuno = np.median([
            _period(profile, RESPIRATORY, rng=np.random.default_rng(37 + i),
                    immunocompromised=True)
            for i in range(200)
        ])
        assert immuno > neutral


def _period(
    profile: dict,
    pathogen_id: str,
    *,
    rng: np.random.Generator,
    dose: float = 1e4,
    immunocompromised: bool = False,
) -> float:
    """One host's drawn incubation period through the progression seam."""
    agent = _agent()
    agent.immunocompromised = immunocompromised
    agent.infect_with_pathogen(pathogen_id, dose, 0)
    return incubation_days(
        agent, pathogen_id, agent.infections[pathogen_id], profile, rng,
    )


# ── Shipped profiles ────────────────────────────────────────────────────

class TestShippedProfiles:
    @pytest.mark.parametrize("pathogen_id", [PATHOGEN, RESPIRATORY])
    def test_shipped_distribution_parses(self, pathogen_id: str) -> None:
        model = IncubationModel.from_mapping(_profile(pathogen_id)["incubation"])
        assert model is not None
        assert model.median_days > 0.0

    def test_shipped_distributions_cite_their_source(self) -> None:
        for pathogen_id in (PATHOGEN, RESPIRATORY):
            notes = _profile(pathogen_id)["incubation"].get("notes", "")
            assert notes, pathogen_id

    def test_norovirus_stays_inside_its_observed_window(self) -> None:
        model = IncubationModel.from_mapping(_profile()["incubation"])
        assert model is not None
        drawn = _draws(model, seed=101, dose=10 ** model.dose_reference_log10)
        assert float(np.median(drawn)) == pytest.approx(1.2, rel=0.1)
        assert float(drawn.min()) >= model.min_days
        assert float(drawn.max()) <= model.max_days

    @pytest.mark.parametrize("pathogen_id", [PATHOGEN, RESPIRATORY])
    def test_shipped_profiles_leave_host_biology_neutral(
        self, pathogen_id: str,
    ) -> None:
        """docs/ctb_incubation_spec.md §3.3: the literature does not support a
        frailty effect on incubation, so the main line ships without one."""
        assert "host_factors" not in _profile(pathogen_id)["incubation"]

    @pytest.mark.parametrize("pathogen_id", [PATHOGEN, RESPIRATORY])
    def test_shipped_profiles_carry_a_dose_term_and_its_floor(
        self, pathogen_id: str,
    ) -> None:
        model = IncubationModel.from_mapping(_profile(pathogen_id)["incubation"])
        assert model is not None
        assert model.dose_log10_shortening > 0.0
        assert model.dose_floor == pytest.approx(0.3)

    @pytest.mark.parametrize("pathogen_id", [PATHOGEN, RESPIRATORY])
    def test_the_dose_reference_is_in_the_units_the_simulator_uses(
        self, pathogen_id: str,
    ) -> None:
        """A reference expressed in a literature assay unit would sit orders of
        magnitude below any simulated inoculum, pinning every host to the dose
        floor and turning the conditioning term into a constant shift. Each
        shipped reference is the profile's own beta-Poisson N50, so a typical
        host is unshifted and both directions stay reachable.
        """
        profile = _profile(pathogen_id)
        model = IncubationModel.from_mapping(profile["incubation"])
        assert model is not None
        response = profile["dose_response"]
        n50 = response["beta"] * (2 ** (1 / response["alpha"]) - 1)
        assert model.dose_factor(n50) == pytest.approx(1.0, abs=0.02)
        assert model.dose_factor(n50 * 10) > model.dose_floor

    def test_the_respiratory_pathogen_incubates_longer_than_the_enteric_one(
        self,
    ) -> None:
        enteric = IncubationModel.from_mapping(_profile()["incubation"])
        respiratory = IncubationModel.from_mapping(_profile(RESPIRATORY)["incubation"])
        assert enteric is not None
        assert respiratory is not None
        assert respiratory.median_days > enteric.median_days

    def test_influenza_draws_a_stochastic_dose_conditioned_incubation(self) -> None:
        profile = _edison_profile()
        model = IncubationModel.from_mapping(profile["incubation"])
        assert model is not None
        low_dose = np.array([
            _period(
                profile,
                INFLUENZA,
                dose=1.0,
                rng=np.random.default_rng(seed),
            )
            for seed in range(200, 400)
        ])
        high_dose = np.array([
            _period(
                profile,
                INFLUENZA,
                dose=1e4,
                rng=np.random.default_rng(seed),
            )
            for seed in range(200, 400)
        ])
        assert len(set(low_dose)) > 1
        assert float(np.median(high_dose)) < float(np.median(low_dose))
        assert low_dose.min() >= model.min_days
        assert low_dose.max() <= model.max_days


# ── Schema contract ─────────────────────────────────────────────────────

_SCHEMA = json.loads(
    (REPO_ROOT / "schemas/pathogen_profiles.schema.json").read_text(),
)


def _validate_block(block: dict) -> None:
    """Validate one ``incubation`` block against the shipped schema."""
    jsonschema.validate(
        instance=block,
        schema={**_SCHEMA["$defs"]["Incubation"], "$defs": _SCHEMA["$defs"]},
    )


class TestSchemaContract:
    """The schema is what a hand-written or externally supplied profile meets.

    A block that only the Python loader rejects is a gap: field data arriving
    as JSON is validated by the schema alone.
    """

    @pytest.mark.parametrize("pathogen_id", [PATHOGEN, RESPIRATORY])
    def test_shipped_blocks_satisfy_the_schema(self, pathogen_id: str) -> None:
        _validate_block(_profile(pathogen_id)["incubation"])

    @pytest.mark.parametrize("block", [
        pytest.param({"dispersion": 1.4, "notes": "x"}, id="no-median"),
        pytest.param({"median_days": 2.0}, id="no-provenance"),
        pytest.param({"median_days": 2.0, "notes": ""}, id="empty-provenance"),
        pytest.param({"median_days": 0.0, "notes": "x"}, id="zero-median"),
        pytest.param({"median_days": -1.0, "notes": "x"}, id="negative-median"),
        pytest.param(
            {"median_days": 2.0, "dispersion": 1.0, "notes": "x"},
            id="lognormal-point-mass",
        ),
        pytest.param(
            {"median_days": 2.0, "distribution": "lognormal",
             "dispersion": 0.8, "notes": "x"},
            id="lognormal-inverted-gsd",
        ),
        pytest.param(
            {"median_days": 2.0, "distribution": "weibull", "notes": "x"},
            id="unsupported-family",
        ),
        pytest.param(
            {"median_days": 2.0, "dispresion": 1.4, "notes": "x"},
            id="misspelled-key",
        ),
        pytest.param(
            {"median_days": 2.0, "min_days": -1.0, "notes": "x"},
            id="negative-lower-bound",
        ),
        pytest.param(
            {"median_days": 2.0, "dose_log10_shortening": -0.1, "notes": "x"},
            id="negative-dose-term",
        ),
        pytest.param(
            {"median_days": 2.0, "notes": "x",
             "host_factors": {"immunocompromised": 0.0}},
            id="zero-host-factor",
        ),
        pytest.param(
            {"median_days": 2.0, "notes": "x",
             "host_factors": {"age_bands": {"senior": -1.0}}},
            id="negative-age-factor",
        ),
        pytest.param(
            {"median_days": 2.0, "notes": "x",
             "host_factors": {"immunosuppressed": 1.2}},
            id="misspelled-host-factor",
        ),
    ])
    def test_the_schema_rejects_a_malformed_block(self, block: dict) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _validate_block(block)

    def test_a_gamma_may_have_a_coefficient_of_variation_below_one(self) -> None:
        """The lognormal-only ``dispersion > 1`` rule must not catch a gamma."""
        _validate_block({
            "median_days": 2.0, "distribution": "gamma",
            "dispersion": 0.6, "notes": "x",
        })

    @pytest.mark.parametrize("block", [
        pytest.param({"median_days": 2.0, "min_days": 5.0, "max_days": 3.0,
                      "notes": "x"}, id="inverted-window"),
        pytest.param({"median_days": 9.0, "min_days": 1.0, "max_days": 6.0,
                      "notes": "x"}, id="median-outside-window"),
    ])
    def test_cross_field_rules_live_in_python_not_the_schema(
        self, block: dict,
    ) -> None:
        """Documents the split: JSON Schema cannot compare two numbers, so the
        loader and the sanity checker are the only gate on window ordering."""
        _validate_block(block)
        with pytest.raises(ValueError):
            IncubationModel.from_mapping(block)


# ── Sanity checker ──────────────────────────────────────────────────────

def _checked(incubation: dict, **profile_fields: object) -> Report:
    """Run the incubation checks over one synthetic profile."""
    report = Report()
    profile = PathogenProfile(
        pathogen_id=PATHOGEN, name="test", incubation=incubation,
        **profile_fields,
    )
    _check_incubation_models(PathogensFile(pathogens=[profile]), report)
    return report


def _messages(report: Report) -> str:
    return " | ".join(f.message for f in report.findings)


class TestSanityChecker:
    def test_the_shipped_profiles_pass(self) -> None:
        report = Report()
        data = json.loads(
            (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
        )
        _check_incubation_models(PathogensFile(**data), report)
        assert report.passed, _messages(report)

    def test_no_incubation_block_is_not_a_finding(self) -> None:
        report = _checked({})
        assert not report.findings

    def test_an_invalid_distribution_is_an_error(self) -> None:
        report = _checked({"median_days": 2.0, "distribution": "weibull",
                           "notes": "x"})
        assert not report.passed
        assert "invalid" in _messages(report)

    def test_an_inverted_window_is_an_error(self) -> None:
        report = _checked({"median_days": 2.0, "min_days": 5.0, "max_days": 3.0,
                           "notes": "x"})
        assert not report.passed
        assert "max_days" in _messages(report)

    def test_an_unanchored_distribution_is_an_error(self) -> None:
        report = _checked({"median_days": 2.0, "dispersion": 1.4})
        assert not report.passed
        assert "provenance" in _messages(report)

    def test_a_median_past_recovery_is_a_warning(self) -> None:
        report = _checked(
            {"median_days": 9.0, "min_days": 0.5, "max_days": 20.0, "notes": "x"},
            recovery_day=5,
        )
        assert report.passed, _messages(report)
        assert "recover before presenting" in _messages(report)

    def test_a_leftover_fixed_onset_day_is_a_warning(self) -> None:
        report = _checked(
            {"median_days": 2.0, "notes": "x"},
            recovery_day=10, symptom_onset_day=1.0,
        )
        assert report.passed, _messages(report)
        assert "never read" in _messages(report)
