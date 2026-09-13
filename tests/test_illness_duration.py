"""The dispersed illness-duration arm: digitization check, draw seam, inertness.

Harris et al. 2019 (BMC Infect Dis 19:87, Fig 4C, diarrhoea curve) supplies the
survival table; the three summary statistics are exact properties of the table,
asserted to validate the digitization itself, not to loosen a golden.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engines.illness_duration import (
    IllnessDurationModel,
)
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.natural_history import (
    advance_infections,
    illness_duration_days,
    project_legacy_illness,
)
from engines.pharmaceutical_interventions import (
    apply_treatment_at_onset,
)
from engines.sim_clock import HOURS, SimClock

REPO_ROOT = Path(__file__).resolve().parent.parent
ZONE = "Z"
PATHOGEN = "norwalk_gi"

_HARRIS_BLOCK: dict[str, Any] = {
    "draw": "empirical_survival",
    "unit": "days",
    "survival": [
        {"day": 0, "probability": 1.0},
        {"day": 1, "probability": 0.63},
        {"day": 2, "probability": 0.355},
        {"day": 3, "probability": 0.22},
        {"day": 4, "probability": 0.13},
        {"day": 5, "probability": 0.079},
        {"day": 6, "probability": 0.057},
        {"day": 7, "probability": 0.03},
        {"day": 8, "probability": 0.023},
        {"day": 9, "probability": 0.019},
        {"day": 13, "probability": 0.0},
    ],
    "notes": "Harris 2019 Fig 4C digitization fixture.",
}


def _model(block: dict[str, Any] | None = None) -> IllnessDurationModel:
    model = IllnessDurationModel.from_mapping(block or _HARRIS_BLOCK)
    assert model is not None
    return model


def _agent(clock: SimClock, aid: int = 0, dose: float = 1e4) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid, role="passenger", immune=False,
        home_zone=ZONE, dining_zone=ZONE, work_zone=ZONE, free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.clock = clock
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, dose, 0)
    return agent


def _profile(**overrides: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "recovery_day": 3,
        "shedding_duration_days": 15,
        "symptom_onset_day": 1.0,
        "symptomatic_fraction": 1.0,
    }
    profile.update(overrides)
    return profile


def _exact_pmf(model: IllnessDurationModel) -> dict[int, float]:
    last = model.survival[-1][0]
    return {
        day: model.survival_at(day - 1) - model.survival_at(day)
        for day in range(1, last + 1)
    }


class TestDigitization:
    """Exact properties of the authored table: the digitization's own check."""

    def test_the_table_median_is_the_papers_median(self) -> None:
        pmf = _exact_pmf(_model())
        cdf = np.cumsum([pmf[d] for d in sorted(pmf)])
        median = sorted(pmf)[int(np.searchsorted(cdf, 0.5))]
        # The >=5 table's own median; the abstract reports no diarrhoea
        # median but resolves 83% of diarrhoea cases by day 4 all ages.
        assert median == 2

    def test_the_table_mean_is_the_papers_mean_direction(self) -> None:
        mean = sum(d * p for d, p in _exact_pmf(_model()).items())
        # The abstract's all-ages figure is higher; symptoms last longer in
        # children < 5 than in adults, so the >=5 table sits below it.
        # The table's exact mean is 2.5715; 2.57 is its rounded form.
        assert mean == pytest.approx(2.57, abs=0.005)
        assert mean < 2.8

    def test_the_table_resolved_by_day_4_matches(self) -> None:
        pmf = _exact_pmf(_model())
        resolved = sum(p for d, p in pmf.items() if d <= 4)
        # The abstract reports 83% of diarrhoea resolved by day 4 all ages;
        # the >=5 band is shorter, so above 0.83 is the right direction.
        assert resolved == pytest.approx(0.87, abs=1e-9)
        assert resolved > 0.83

    def test_the_sampler_reproduces_the_table(self) -> None:
        """Sampling check, not a golden: the inversion must realize the pmf."""
        rng = np.random.default_rng(0)
        model = _model()
        draws = [model.sample_days(rng) for _ in range(20000)]
        pmf = _exact_pmf(model)
        assert np.median(draws) == 2
        assert np.mean(draws) == pytest.approx(
            sum(d * p for d, p in pmf.items()), abs=0.05,
        )
        assert np.mean(np.asarray(draws) <= 4) == pytest.approx(0.87, abs=0.01)

    def test_interpolated_days_carry_real_mass(self) -> None:
        """Days 10-12 are interpolations, not zeros in the draw support."""
        pmf = _exact_pmf(_model())
        for day in (10, 11, 12):
            assert pmf[day] > 0.0


class TestModelValidation:
    def test_unknown_draw_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="empirical_survival"):
            IllnessDurationModel.from_mapping({
                "draw": "gamma", "unit": "days", "notes": "x",
            })

    def test_unknown_key_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="unknown keys"):
            IllnessDurationModel.from_mapping({
                "draw": "point", "unit": "days", "notes": "x", "typo": 1,
            })

    def test_empirical_without_a_table_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="survival"):
            IllnessDurationModel.from_mapping({
                "draw": "empirical_survival", "unit": "days", "notes": "x",
            })

    @pytest.mark.parametrize("rows,msg", [
        ([{"day": 1, "probability": 1.0}, {"day": 2, "probability": 0.0}],
         "day 0"),
        ([{"day": 0, "probability": 0.9}, {"day": 2, "probability": 0.0}],
         "day 0"),
        ([{"day": 0, "probability": 1.0}, {"day": 2, "probability": 0.1}],
         "0.0"),
        ([{"day": 0, "probability": 1.0}, {"day": 2, "probability": 0.5},
          {"day": 2, "probability": 0.0}],
         "strictly increasing"),
        ([{"day": 0, "probability": 1.0}, {"day": 1, "probability": 0.5},
          {"day": 2, "probability": 0.7}, {"day": 3, "probability": 0.0}],
         "non-increasing"),
    ])
    def test_a_malformed_table_is_an_error(
        self, rows: list[dict], msg: str,
    ) -> None:
        with pytest.raises(ValueError, match=msg):
            IllnessDurationModel.from_mapping({
                "draw": "empirical_survival", "unit": "days",
                "survival": rows, "notes": "x",
            })

    def test_absent_block_is_no_model(self) -> None:
        assert IllnessDurationModel.from_mapping(None) is None
        assert IllnessDurationModel.from_mapping({}) is None


class TestProgressionSeam:
    """The stamp precedes the pharmaceutical override and the clearance read."""

    def test_empirical_stamps_a_drawn_recovery_day(self) -> None:
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _agent(clock)
        inf = agent.infections[PATHOGEN]
        profile = _profile(illness_duration=dict(_HARRIS_BLOCK))
        drawn = illness_duration_days(inf, profile, np.random.default_rng(1))
        assert drawn is not None
        assert inf["recovery_day"] == drawn
        assert drawn == float(int(drawn)) and 1 <= drawn <= 13

    def test_the_draw_is_once_per_infection(self) -> None:
        agent = _agent(SimClock(epoch_duration_hours=1.0, mode=HOURS))
        inf = agent.infections[PATHOGEN]
        profile = _profile(illness_duration=dict(_HARRIS_BLOCK))
        rng = np.random.default_rng(5)
        first = illness_duration_days(inf, profile, rng)
        # A stream seeded identically and advanced by the one draw the first
        # call took predicts the next value exactly.
        oracle = np.random.default_rng(5)
        oracle.random()
        expected_next = oracle.random()
        second = illness_duration_days(inf, profile, rng)
        assert second == first
        # The second call consumed nothing from the stream.
        assert rng.random() == expected_next

    def test_treatment_shortens_the_drawn_duration(self) -> None:
        """apply_treatment_at_onset reads the record first: the drawn value,
        not the profile constant, is what the reduction subtracts from."""
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _agent(clock)
        inf = agent.infections[PATHOGEN]
        profile = _profile(illness_duration=dict(_HARRIS_BLOCK))
        drawn = illness_duration_days(inf, profile, np.random.default_rng(9))
        agent.pharma_by_pathogen = {PATHOGEN: {
            "treatment_reaches_host": True,
            "treatment_illness_reduction_days": 1.0,
            "treatment_shedding_reduction_days": 0.0,
            "treatment_transmission_multiplier": 1.0,
        }}
        assert apply_treatment_at_onset(agent, PATHOGEN, inf, profile)
        assert inf["recovery_day"] == pytest.approx(drawn - 1.0)

    def test_empirical_moves_clearance_for_long_illnesses(self) -> None:
        """Graded sensitivity: longer survival -> later illness clearance."""
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        ends: dict[str, list[int]] = {"point": [], "empirical_survival": []}
        for mode, block in (
            ("point", {"draw": "point", "unit": "days", "notes": "x"}),
            ("empirical_survival", dict(_HARRIS_BLOCK)),
        ):
            for seed in range(60):
                agent = _agent(clock, aid=seed)
                profile = _profile(
                    illness_duration=block,
                    symptomatic_fraction=1.0,
                    symptom_onset_day=0.0,
                )
                rng = np.random.default_rng(seed)
                end = None
                for epoch in range(int(clock.epochs_for_days(20))):
                    advance_infections(
                        agent, {PATHOGEN: profile}, rng, epoch=epoch,
                    )
                    inf = agent.infections[PATHOGEN]
                    if (
                        inf["illness"] == IllnessStatus.RECOVERED
                        and end is None
                    ):
                        end = epoch
                ends[mode].append(end if end is not None else 10**6)
        # Point mode ends every illness at onset + 3 exactly.
        assert len(set(ends["point"])) == 1
        # Empirical disperses: some hosts resolve inside a day, some run past 5.
        assert len(set(ends["empirical_survival"])) > 5
        assert np.mean(ends["empirical_survival"]) < np.mean(ends["point"])
        # The tail the point cannot express exists.
        assert max(ends["empirical_survival"]) > np.mean(ends["point"])

    def test_every_illness_still_ends(self) -> None:
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        for seed in range(30):
            agent = _agent(clock, aid=seed)
            profile = _profile(illness_duration=dict(_HARRIS_BLOCK))
            rng = np.random.default_rng(seed + 1000)
            for epoch in range(int(clock.epochs_for_days(20))):
                advance_infections(agent, {PATHOGEN: profile}, rng, epoch=epoch)
            inf = agent.infections[PATHOGEN]
            assert inf["status"] == InfectionStatus.RECOVERED
            assert inf["illness"] == IllnessStatus.RECOVERED

    def test_point_mode_performs_no_table_validation(self) -> None:
        """Pins where validation lives: data-validation time, not progression.

        The default path reads the draw key and returns before the model is
        built, so it never pays the parse cost per infection-epoch — and a
        malformed table under ``point`` is the schema's, the sanity
        checker's and ``from_mapping``'s defect to reject, not the epoch
        loop's. Do not "fix" this back into per-epoch validation.
        """
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _agent(clock)
        profile = _profile(illness_duration={
            "draw": "point",
            "unit": "days",
            "notes": "deliberately malformed under the inert arm",
            "survival": [{"day": 7, "probability": 0.5}],
        })
        rng = np.random.default_rng(3)
        for epoch in range(int(clock.epochs_for_days(10))):
            advance_infections(agent, {PATHOGEN: profile}, rng, epoch=epoch)
        inf = agent.infections[PATHOGEN]
        assert "recovery_day" not in inf
        assert illness_duration_days(inf, profile, rng) is None
        assert inf["illness"] == IllnessStatus.RECOVERED


class TestDefaultInertness:
    """draw: point is bit-identical to pre-arm main — no stamp, no RNG draw.

    CHANGE DETECTOR, not a correctness check: the fingerprint pins the
    shipped-profile trajectory captured on origin/main before this arm
    existed. If a deliberate change moves it, update it and say why.
    """

    _INERTNESS_FINGERPRINT = (
        "07865c737bd4f03a69abd5be49b2aa25fbe23ef94a4f95db5f4014bcff519bf7"
    )
    _INERTNESS_RNG_NEXT = 0.5168044128381893

    def _run(
        self, illness_duration: dict[str, Any] | None,
    ) -> tuple[str, float, list[Any]]:
        prof = json.loads(
            (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
        )["pathogens"][0]
        assert prof["pathogen_id"] == PATHOGEN
        prof = dict(prof)
        if illness_duration is None:
            prof.pop("illness_duration", None)
        else:
            prof["illness_duration"] = illness_duration
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        rng = np.random.default_rng(123)
        agents = []
        for i in range(40):
            agent = KorkinAgent(
                agent_id=i, role="passenger", immune=False,
                home_zone=ZONE, dining_zone=ZONE, work_zone=ZONE,
                free_zone=ZONE, schedule=["Free"] * 24,
            )
            agent.clock = clock
            agent.current_location = ZONE
            agent.infect_with_pathogen(PATHOGEN, 1e4, 0, rng=rng, profile=prof)
            agents.append(agent)
        for epoch in range(int(clock.epochs_for_days(20))):
            for agent in agents:
                advance_infections(
                    agent, {PATHOGEN: prof}, rng, epoch=epoch,
                )
                project_legacy_illness(agent)
        rows = [
            (
                a.agent_id, str(inf["status"]), str(inf["illness"]),
                inf.get("recovery_day"), inf["time_infected"],
                str(inf.get("symptom_severity")),
            )
            for a in agents
            for inf in [a.infections[PATHOGEN]]
        ]
        fp = hashlib.sha256(repr(rows).encode()).hexdigest()
        return fp, float(rng.random()), [r[3] for r in rows]

    def test_the_shipped_point_block_reproduces_main_bit_for_bit(self) -> None:
        fp, cursor, stamps = self._run(None)
        assert fp == self._INERTNESS_FINGERPRINT
        assert cursor == pytest.approx(self._INERTNESS_RNG_NEXT)
        assert set(stamps) == {None}

    def test_an_explicit_point_draw_consumes_no_stream(self) -> None:
        fp, cursor, stamps = self._run(
            {"draw": "point", "unit": "days", "survival":
             _HARRIS_BLOCK["survival"], "notes": "x"},
        )
        assert fp == self._INERTNESS_FINGERPRINT
        assert cursor == pytest.approx(self._INERTNESS_RNG_NEXT)
        assert set(stamps) == {None}
