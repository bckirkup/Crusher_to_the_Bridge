"""
test_contam_analytic_fixtures.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Closed-form analytic controls for the CONTAM mass operator and propagator.

Implements the study-design fixtures F1-F6 from Edison's computational
study protocol (2026-11-07, Section 7 and Table 7). Each fixture states a
physical definition in hours, m^3, m^3/h and tracer mass, and an
independently derived closed form. Expected values in this file are
computed from those ODEs here - never by calling the engine under test
(``engines.py_contam_bridge.ContamTransportEngine``) - and the protocol's
published check values are reproduced as regression anchors.

Two source semantics are kept strictly separate, per the protocol:

- ``exact``: continuous forcing,
  ``M(t+h) = expm(A h) M(t) + ∫ expm(A(h-u)) S(u) du``, evaluated in closed
  form per constant-source segment.
- ``start_impulse`` (the production epoch recurrence): emissions deposit
  into the zone pool and the propagator then runs the whole step,
  ``M(t+h) = expm(A h) (M(t) + S h)``.  ``ship_simulation`` adds each
  epoch's emissions before calling ``transport_step``, so this is the
  recurrence the model actually realizes.  It is labeled discrete and its
  difference from continuous forcing is characterized, never passed off
  as the continuous solution.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import ContamTransportEngine
from engines.sim_clock import HOURS, SimClock

# Protocol Section 8.1 float64 engineering budgets, tightened where the
# closed forms allow it: no factor-of-ten grace anywhere.
REL = 1e-11
ABS = 1e-11


# ── Independent closed-form helpers (derived from the ODEs, not the engine) ──

def _exact_const_source_step(
    mass: float, k: float, source: float, hours: float,
) -> float:
    """Exact dM/dt = -k M + S over one constant-source segment."""
    if k == 0.0:
        return mass + source * hours
    decay = math.exp(-k * hours)
    return mass * decay + (source / k) * (1.0 - decay)


def _start_impulse_step(
    mass: float, k: float, source: float, hours: float,
) -> float:
    """Production epoch recurrence: deposit S*h, then propagate."""
    return math.exp(-k * hours) * (mass + source * hours)


def _production_epoch_step(
    engine: ContamTransportEngine,
    mass: dict[str, float],
    source_rate: dict[str, float],
    hours: float,
    decay: float = 0.0,
) -> dict[str, float]:
    """Deposit this epoch's emissions, then run the production propagator.

    Mirrors ``ship_simulation``: emissions land in the zone pool during the
    epoch and ``transport_step`` moves the whole pool afterwards.
    """
    deposited = {
        zone: value + source_rate.get(zone, 0.0) * hours
        for zone, value in mass.items()
    }
    return engine.transport_step(deposited, natural_decay_rate=decay)


def _concentration(
    engine: ContamTransportEngine, zone: str, mass: float,
) -> float:
    return mass / engine.zone_nodes[zone].volume_m3


# ── Fixture network builders (production constructors only) ──────────────

def _layout(*zones: tuple[str, float]) -> dict:
    return {"zones": [{"id": zid, "volume_m3": vol} for zid, vol in zones]}


def _exhaust_airflow(room: str, ach: float) -> dict:
    """Duty-0, declared-OA-1 terminal: the production exhaust realization."""
    return {
        "hvac_zones": [{
            "id": "AHU_ex", "rooms": [room], "ach": ach,
            "oa_fraction": 1.0, "hvac_duty": 0.0,
        }],
        "cross_zone_links": [],
        "adjacency": [],
    }


def _ahu_airflow(
    rooms: list[str], ach: float, oa: float, duty: float = 1.0,
) -> dict:
    return {
        "oa_fraction": oa,
        "hvac_duty": duty,
        "hvac_zones": [{"id": "hz", "rooms": rooms, "ach": ach}],
        "cross_zone_links": [],
        "adjacency": [],
    }


def _engine(
    layout: dict, airflow: dict, *, eta: float = 0.5, decay: float = 0.0,
    clock: SimClock | None = None, **kwargs,
) -> ContamTransportEngine:
    return ContamTransportEngine(
        layout, airflow,
        filter_efficiency=eta, natural_decay_rate=decay, clock=clock,
        **kwargs,
    )


def _operator(engine: ContamTransportEngine) -> np.ndarray:
    """Decay-free mass operator A_M (dM/dt = A_M M), rows = destination."""
    return engine._build_decay_free_operator()


# ── F1: single-room exhaust, V=100, Q=120 (k=1.2/h) ───────────────────────

class TestF1SingleRoomExhaust:
    """Protocol Table 7 F1: V=100; Q=120; M0=1000; source-free k=1.2/h."""

    def _make(self) -> ContamTransportEngine:
        return _engine(
            _layout(("A", 100.0)), _exhaust_airflow("A", ach=1.2),
            eta=0.0, decay=0.0,
        )

    def test_operator_is_pure_removal_at_ach_over_volume(self) -> None:
        assert _operator(self._make()) == pytest.approx(
            np.array([[-1.2]]), rel=REL, abs=ABS,
        )

    def test_source_free_state_and_concentration(self) -> None:
        engine = self._make()
        mass = engine.transport_step({"A": 1000.0}, natural_decay_rate=0.0)
        # Protocol anchors: M(1)=301.194211912202, C=3.01194211912202.
        assert mass["A"] == pytest.approx(301.194211912202, rel=REL, abs=ABS)
        assert _concentration(engine, "A", mass["A"]) == pytest.approx(
            3.01194211912202, rel=REL, abs=ABS,
        )

    def test_continuous_source_exact_reference(self) -> None:
        """Reference check: S=600/h, lambda=0 -> M(1)=650.597105956101."""
        exact = _exact_const_source_step(1000.0, k=1.2, source=600.0, hours=1.0)
        assert exact == pytest.approx(650.597105956101, rel=REL, abs=ABS)

    def test_production_start_impulse_matches_own_recurrence(self) -> None:
        """Legacy discrete semantics: e^-kh (M + S h) = 481.910739059523."""
        engine = self._make()
        mass = _production_epoch_step(
            engine, {"A": 1000.0}, {"A": 600.0}, hours=1.0, decay=0.0,
        )
        expected = _start_impulse_step(1000.0, k=1.2, source=600.0, hours=1.0)
        assert expected == pytest.approx(481.910739059523, rel=REL, abs=ABS)
        assert mass["A"] == pytest.approx(expected, rel=REL, abs=ABS)

    def test_source_semantics_difference_is_predicted_not_hidden(self) -> None:
        """Continuous vs start-impulse differ by the predicted ~168.7 mass."""
        exact = _exact_const_source_step(1000.0, 1.2, 600.0, 1.0)
        discrete = _start_impulse_step(1000.0, 1.2, 600.0, 1.0)
        difference = exact - discrete
        assert difference == pytest.approx(168.686366896578, rel=1e-9)
        assert difference > 100.0, "the two semantics must not be conflated"

    def test_source_with_decay_exact_and_discrete(self) -> None:
        """S=600/h, lambda=0.3 -> k=1.5; exact M(1)=533.878096089058."""
        exact = _exact_const_source_step(1000.0, k=1.5, source=600.0, hours=1.0)
        assert exact == pytest.approx(533.878096089058, rel=REL, abs=ABS)
        engine = self._make()
        mass = _production_epoch_step(
            engine, {"A": 1000.0}, {"A": 600.0}, hours=1.0, decay=0.3,
        )
        discrete = _start_impulse_step(1000.0, k=1.5, source=600.0, hours=1.0)
        assert mass["A"] == pytest.approx(discrete, rel=REL, abs=ABS)
        assert exact - discrete > 100.0


# ── F2: unequal-volume exchange, V=(100,200), Q=60 each way ───────────────

class TestF2UnequalVolumeExchange:
    """Protocol Table 7 F2: C1(1)=6.04379773160399, C2(1)=1.97810113419800."""

    def _make(self, volume_a: float = 100.0, volume_b: float = 200.0) -> (
        ContamTransportEngine
    ):
        layout = _layout(("A", volume_a), ("B", volume_b))
        airflow = {
            "hvac_zones": [],
            "cross_zone_links": [
                {"from": "A", "to": "B", "flow_rate_m3h": 60.0},
            ],
            "adjacency": [],
        }
        return _engine(layout, airflow, eta=0.0, decay=0.0)

    def test_operator_mass_form_with_volume_asymmetry(self) -> None:
        # Independently derived: probe unit mass per zone, Q=60 m3/h.
        # Column A: -Q/V_A on the diagonal, Q*(1/V_A) arriving at B.
        # Column B: Q*(1/V_B) arriving at A, -Q/V_B on the diagonal.
        expected = np.array([
            [-60.0 / 100.0, 60.0 / 200.0],
            [60.0 / 100.0, -60.0 / 200.0],
        ])
        assert _operator(self._make()) == pytest.approx(expected, rel=REL, abs=ABS)

    def test_concentrations_match_closed_form_and_conserve_mass(self) -> None:
        engine = self._make()
        mass = engine.transport_step({"A": 1000.0, "B": 0.0},
                                     natural_decay_rate=0.0)
        c1 = _concentration(engine, "A", mass["A"])
        c2 = _concentration(engine, "B", mass["B"])
        assert c1 == pytest.approx(6.04379773160399, rel=REL, abs=ABS)
        assert c2 == pytest.approx(1.97810113419800, rel=REL, abs=ABS)
        # Unfiltered closed exchange conserves tracer mass exactly.
        assert mass["A"] + mass["B"] == pytest.approx(1000.0, rel=1e-12)

    def test_volume_initial_condition_permutation_mirrors_solution(self) -> None:
        """Swap volumes AND initial conditions together: solutions mirror."""
        engine = self._make(volume_a=200.0, volume_b=100.0)
        mass = engine.transport_step({"A": 0.0, "B": 1000.0},
                                     natural_decay_rate=0.0)
        # The permuted run is the F2 solution with A<->B exchanged.
        assert _concentration(engine, "A", mass["A"]) == pytest.approx(
            1.97810113419800, rel=REL, abs=ABS,
        )
        assert _concentration(engine, "B", mass["B"]) == pytest.approx(
            6.04379773160399, rel=REL, abs=ABS,
        )

    def test_wrong_extra_volume_factor_is_rejected(self) -> None:
        """Negative oracle: a second volume fraction on the deviation fails."""
        engine = self._make()
        mass = engine.transport_step({"A": 1000.0, "B": 0.0},
                                     natural_decay_rate=0.0)
        c1 = _concentration(engine, "A", mass["A"])
        ceq = 1000.0 / 300.0
        alpha = 60.0 * (1.0 / 100.0 + 1.0 / 200.0)
        wrong = ceq + (10.0 - ceq) * (1.0 / 3.0) * math.exp(-alpha)
        assert abs(c1 - wrong) > 0.5, "engine must not match the wrong form"


# ── F3: balanced three-room star, q=120/room, f=0.2, eta=0.5 ─────────────

class TestF3BalancedStar:
    """Protocol Table 7 F3: C(1)=(3.63046893261459, .618526813492565, .6185...)."""

    def _make(self, eta: float = 0.5, oa: float = 0.2) -> ContamTransportEngine:
        return _engine(
            _layout(("A", 100.0), ("B", 100.0), ("C", 100.0)),
            _ahu_airflow(["A", "B", "C"], ach=1.2, oa=oa, duty=1.0),
            eta=eta, decay=0.0,
        )

    def test_operator_matches_beta_J_form(self) -> None:
        # a=q/V=1.2, beta=(1-f)(1-eta)=0.4; diagonal a(beta/3-1)=-1.04,
        # off-diagonal a*beta/3=0.16 (mass form; volumes are equal).
        expected = np.full((3, 3), 0.16)
        np.fill_diagonal(expected, -1.04)
        assert _operator(self._make()) == pytest.approx(expected, rel=REL, abs=ABS)

    def test_trajectory_matches_closed_form(self) -> None:
        engine = self._make()
        mass = engine.transport_step(
            {"A": 1000.0, "B": 0.0, "C": 0.0}, natural_decay_rate=0.0,
        )
        c = {z: _concentration(engine, z, mass[z]) for z in ("A", "B", "C")}
        assert c["A"] == pytest.approx(3.63046893261459, rel=REL, abs=ABS)
        assert c["B"] == pytest.approx(0.618526813492565, rel=REL, abs=ABS)
        assert c["C"] == pytest.approx(0.618526813492565, rel=REL, abs=ABS)

    def test_wrong_rate_0_6_is_rejected(self) -> None:
        """Negative oracle: the rate-0.6 misreading must not match."""
        engine = self._make()
        mass = engine.transport_step(
            {"A": 1000.0, "B": 0.0, "C": 0.0}, natural_decay_rate=0.0,
        )
        c_a = _concentration(engine, "A", mass["A"])
        mean0 = 10.0 / 3.0
        wrong = mean0 * math.exp(-0.6) + (10.0 - mean0) * math.exp(-1.2)
        assert abs(c_a - wrong) > 0.05

    def test_conservative_limit_conserves_mass_and_equilibrates(self) -> None:
        """f=eta=lambda=0: mean concentration constant, deviations decay."""
        engine = _engine(
            _layout(("A", 100.0), ("B", 100.0), ("C", 100.0)),
            _ahu_airflow(["A", "B", "C"], ach=1.2, oa=0.0, duty=1.0),
            eta=0.0, decay=0.0,
        )
        mass = {"A": 1000.0, "B": 0.0, "C": 0.0}
        for _ in range(20):
            mass = engine.transport_step(mass, natural_decay_rate=0.0)
        total = sum(mass.values())
        assert total == pytest.approx(1000.0, rel=1e-12)
        concentrations = [
            _concentration(engine, z, mass[z]) for z in ("A", "B", "C")
        ]
        mean_c = 10.0 / 3.0
        assert all(
            c == pytest.approx(mean_c, rel=1e-9, abs=1e-9)
            for c in concentrations
        )


# ── DC03: exact mean-loss / different-mixing control (Phase 2 §2.3) ──────

class TestDC03ExactMeanLossDifferentMixing:
    """Phase 2 DC03: two balanced three-room stars with equal mean loss
    a(1 - r) = 1.08/h but different mixing rate a.

    Case 1 is the DC04 high-turnover shape (ach 1.8, OA 0.2, eta 0.5, r = 0.4)
    and case 2 the matched-removal shape (ach 1.2, OA 0.8, eta 0.5, r = 0.1).
    Expected values are derived here from the ODE: for the balanced star
    A_M = a (r J/3 - I) the mean concentration obeys d c_bar/dt = -a(1-r) c_bar
    and each deviation from the mean decays at rate a, so with C0 = (10, 0, 0)
    C_source(t) = c_bar0 e^{-a(1-r)t} + (10 - c_bar0) e^{-a t} and
    C_remote(t) = c_bar0 e^{-a(1-r)t} - c_bar0 e^{-a t}, c_bar0 = 10/3.
    The protocol's published controls (mean 1.13198508548 at 1 h; source
    2.23397767363 / 3.13994649823; remote .580988791411 / .128004379109) are
    cited as provenance and cross-checked, never used as the derivation.
    """

    CASES = {
        "high_turnover": {"ach": 1.8, "oa": 0.2, "eta": 0.5},
        "matched_removal": {"ach": 1.2, "oa": 0.8, "eta": 0.5},
    }
    PROTOCOL = {
        "mean": 1.13198508548,
        "high_turnover": {"source": 2.23397767363, "remote": 0.580988791411},
        "matched_removal": {"source": 3.13994649823, "remote": 0.128004379109},
    }
    VOLUME = 100.0
    C0_SOURCE = 10.0
    HOURS = 1.0

    @staticmethod
    def _gain(oa: float, eta: float) -> float:
        return (1.0 - oa) * (1.0 - eta)

    @classmethod
    def _closed_form(cls, ach: float, oa: float, eta: float) -> dict[str, float]:
        r = cls._gain(oa, eta)
        mean0 = cls.C0_SOURCE / 3.0
        mean = mean0 * math.exp(-ach * (1.0 - r) * cls.HOURS)
        deviation = math.exp(-ach * cls.HOURS)
        return {
            "mean_rate": ach * (1.0 - r),
            "mean": mean,
            "source": mean + (cls.C0_SOURCE - mean0) * deviation,
            "remote": mean - mean0 * deviation,
        }

    def _make(self, ach: float, oa: float, eta: float) -> ContamTransportEngine:
        return _engine(
            _layout(("A", self.VOLUME), ("B", self.VOLUME), ("C", self.VOLUME)),
            _ahu_airflow(["A", "B", "C"], ach=ach, oa=oa, duty=1.0),
            eta=eta, decay=0.0,
        )

    def _engine_concentrations(self, ach: float, oa: float, eta: float) -> dict[str, float]:
        engine = self._make(ach, oa, eta)
        mass = engine.transport_step(
            {"A": self.C0_SOURCE * self.VOLUME, "B": 0.0, "C": 0.0},
            natural_decay_rate=0.0,
        )
        return {z: _concentration(engine, z, mass[z]) for z in ("A", "B", "C")}

    def test_both_cases_share_the_mean_loss_rate(self) -> None:
        rates = [self._closed_form(**case)["mean_rate"] for case in self.CASES.values()]
        assert rates[0] == pytest.approx(1.08, rel=REL, abs=ABS)
        assert rates[1] == pytest.approx(1.08, rel=REL, abs=ABS)

    def test_closed_form_reproduces_protocol_controls(self) -> None:
        for name, case in self.CASES.items():
            expected = self._closed_form(**case)
            assert expected["mean"] == pytest.approx(self.PROTOCOL["mean"], rel=REL, abs=ABS)
            assert expected["source"] == pytest.approx(self.PROTOCOL[name]["source"], rel=REL, abs=ABS)
            assert expected["remote"] == pytest.approx(self.PROTOCOL[name]["remote"], rel=REL, abs=ABS)

    @pytest.mark.parametrize("name", sorted(CASES))
    def test_operator_matches_balanced_star_form(self, name: str) -> None:
        case = self.CASES[name]
        a = case["ach"]
        r = self._gain(case["oa"], case["eta"])
        expected = np.full((3, 3), a * r / 3.0)
        np.fill_diagonal(expected, a * (r / 3.0 - 1.0))
        assert _operator(self._make(**case)) == pytest.approx(expected, rel=REL, abs=ABS)

    @pytest.mark.parametrize("name", sorted(CASES))
    def test_engine_matches_closed_form(self, name: str) -> None:
        case = self.CASES[name]
        expected = self._closed_form(**case)
        c = self._engine_concentrations(**case)
        assert c["A"] == pytest.approx(expected["source"], rel=REL, abs=ABS)
        assert c["B"] == pytest.approx(expected["remote"], rel=REL, abs=ABS)
        assert c["C"] == pytest.approx(expected["remote"], rel=REL, abs=ABS)

    def test_equal_mean_different_mixing(self) -> None:
        high = self._engine_concentrations(**self.CASES["high_turnover"])
        low = self._engine_concentrations(**self.CASES["matched_removal"])
        mean_high = sum(high.values()) / 3.0
        mean_low = sum(low.values()) / 3.0
        assert mean_high == pytest.approx(mean_low, rel=REL, abs=ABS)
        assert mean_high == pytest.approx(self.PROTOCOL["mean"], rel=REL, abs=ABS)
        # Faster mixing lowers the source room and raises the remote rooms.
        assert high["A"] < low["A"]
        assert high["B"] > low["B"]
        assert abs(high["A"] - low["A"]) > 0.5

    def test_single_rate_misreading_is_rejected(self) -> None:
        """Negative oracle: a one-rate well-mixed guess misses both cases."""
        for case in self.CASES.values():
            c = self._engine_concentrations(**case)
            wrong_source = self.C0_SOURCE * math.exp(-case["ach"] * self.HOURS)
            assert abs(c["A"] - wrong_source) > 0.1


# ── F4: head exhaust, V=50, ACH=2, duty=0, declared OA=1 ─────────────────

class TestF4HeadExhaust:
    """Protocol Table 7 F4: extract C=1.35335283236613; sealed C=10."""

    def _make(self, mode: str) -> ContamTransportEngine:
        layout = _layout(("HEAD", 50.0))
        airflow = {
            "hvac_zones": [{
                "id": "AHU_HD", "rooms": ["HEAD"], "ach": 2.0,
                "oa_fraction": 1.0, "hvac_duty": 0.0,
            }],
            "cross_zone_links": [],
            "adjacency": [],
        }
        return _engine(layout, airflow, eta=0.0, decay=0.0,
                       duty0_terminal_mode=mode)

    def test_extract_matches_exp_decay(self) -> None:
        engine = self._make("extract")
        mass = engine.transport_step({"HEAD": 500.0}, natural_decay_rate=0.0)
        assert mass["HEAD"] == pytest.approx(67.66764161830635, rel=REL, abs=ABS)
        assert _concentration(engine, "HEAD", mass["HEAD"]) == pytest.approx(
            1.35335283236613, rel=REL, abs=ABS,
        )

    def test_sealed_retains_everything(self) -> None:
        engine = self._make("sealed")
        mass = engine.transport_step({"HEAD": 500.0}, natural_decay_rate=0.0)
        assert mass["HEAD"] == pytest.approx(500.0, rel=REL, abs=ABS)
        assert _concentration(engine, "HEAD", mass["HEAD"]) == pytest.approx(
            10.0, rel=REL, abs=ABS,
        )


# ── F5: OA/filter/decay single room, V=120, Q=360, f=0.25, eta=0.5 ───────

class TestF5OAFilterDecay:
    """Protocol Table 7 F5: k=2.475/h, C(1)=0.841629902573104."""

    def _make(self, oa: float = 0.25, eta: float = 0.5) -> ContamTransportEngine:
        return _engine(
            _layout(("A", 120.0)), _ahu_airflow(["A"], ach=3.0, oa=oa),
            eta=eta, decay=0.0,
        )

    def test_operator_and_closure(self) -> None:
        # k = ACH [f + (1-f) eta] + lambda = 3(0.25+0.375)+0.6 = 2.475/h.
        engine = self._make()
        assert _operator(engine) == pytest.approx(
            np.array([[-1.875]]), rel=REL, abs=ABS,
        )
        mass = engine.transport_step({"A": 1200.0}, natural_decay_rate=0.6)
        assert _concentration(engine, "A", mass["A"]) == pytest.approx(
            0.841629902573104, rel=REL, abs=ABS,
        )

    def test_pure_recirculation_companion(self) -> None:
        """V=100, Q=300, f=0, eta=0.5, lambda=0 -> k=1.5, C(1)=2.23130160148430."""
        engine = _engine(
            _layout(("A", 100.0)), _ahu_airflow(["A"], ach=3.0, oa=0.0),
            eta=0.5, decay=0.0,
        )
        assert _operator(engine) == pytest.approx(
            np.array([[-1.5]]), rel=REL, abs=ABS,
        )
        mass = engine.transport_step({"A": 1000.0}, natural_decay_rate=0.0)
        assert _concentration(engine, "A", mass["A"]) == pytest.approx(
            2.23130160148430, rel=REL, abs=ABS,
        )

    def test_filter_grades_removal_with_ordered_span(self) -> None:
        """eta in {0, .5, 1} at f=.25 gives k = 1.35, 2.475, 3.6 (1/h)."""
        masses = []
        for eta in (0.0, 0.5, 1.0):
            engine = self._make(eta=eta)
            mass = engine.transport_step({"A": 1200.0}, natural_decay_rate=0.6)
            masses.append(mass["A"])
        expected = [1200.0 * math.exp(-k) for k in (1.35, 2.475, 3.6)]
        for got, want in zip(masses, expected):
            assert got == pytest.approx(want, rel=REL, abs=ABS)
        assert masses[0] > masses[1] > masses[2]
        span = (masses[0] - masses[2]) / masses[0]
        assert span > 0.5, "filter efficiency must be a live knob"

    def test_full_outdoor_air_makes_filter_irrelevant(self) -> None:
        """Negative control: f=1 recirculates nothing, so eta cannot matter."""
        results = []
        for eta in (0.0, 1.0):
            engine = self._make(oa=1.0, eta=eta)
            mass = engine.transport_step({"A": 1200.0}, natural_decay_rate=0.6)
            results.append(mass["A"])
        assert results[0] == pytest.approx(results[1], rel=1e-12)
        assert results[0] == pytest.approx(
            1200.0 * math.exp(-3.6), rel=REL, abs=ABS,
        )


# ── F6: piecewise source and control event, V=100 ─────────────────────────

class TestF6EventAndSourceSemantics:
    """Protocol Table 7 F6: S=600/h on [0,.5), Q=120 then 240; dt=0.5 h.

    Exact continuous reference: M(1)=123.808712090912,
    M(2)=M(1) exp(-2.4).  Production realizes start-impulse epochs, so the
    two are compared as labeled, separate semantics.
    """

    _SEGMENTS = ((1.2, 600.0, 0.5), (1.2, 0.0, 0.5),
                 (2.4, 0.0, 0.5), (2.4, 0.0, 0.5))

    def _exact_reference(self) -> tuple[float, float]:
        mass = 0.0
        checkpoints = []
        for k, source, hours in self._SEGMENTS:
            mass = _exact_const_source_step(mass, k, source, hours)
            checkpoints.append(mass)
        return checkpoints[1], checkpoints[3]

    def test_exact_reference_reproduces_published_values(self) -> None:
        m1, m2 = self._exact_reference()
        assert m1 == pytest.approx(123.808712090912, rel=REL, abs=ABS)
        assert m2 == pytest.approx(m1 * math.exp(-2.4), rel=REL, abs=ABS)

    def _make_engine(self, ach: float) -> ContamTransportEngine:
        clock = SimClock(epoch_duration_hours=0.5, mode=HOURS)
        return _engine(
            _layout(("A", 100.0)), _exhaust_airflow("A", ach=ach),
            eta=0.0, decay=0.0, clock=clock,
        )

    def test_production_start_impulse_characterization(self) -> None:
        """Engine epochs reproduce the discrete recurrence, not the exact one."""
        engine120 = self._make_engine(ach=1.2)
        engine240 = self._make_engine(ach=2.4)
        mass = {"A": 0.0}
        # [0, 0.5): source on; [0.5, 1.0): source off.
        mass = _production_epoch_step(engine120, mass, {"A": 600.0}, 0.5)
        mass = _production_epoch_step(engine120, mass, {}, 0.5)
        m1 = mass["A"]
        # Independent discrete recurrence for the same two epochs.
        discrete = _start_impulse_step(0.0, 1.2, 600.0, 0.5)
        discrete = _start_impulse_step(discrete, 1.2, 0.0, 0.5)
        assert m1 == pytest.approx(discrete, rel=REL, abs=ABS)
        exact_m1, _ = self._exact_reference()
        assert exact_m1 - m1 > 10.0, "semantics difference must stay visible"
        # [1, 2): control event - the Q=240 operator governs both epochs.
        mass = engine240.transport_step(mass, natural_decay_rate=0.0)
        mass = engine240.transport_step(mass, natural_decay_rate=0.0)
        m2 = mass["A"]
        assert m2 == pytest.approx(discrete * math.exp(-2.4), rel=REL, abs=ABS)

    def test_event_switch_applies_new_operator_immediately(self) -> None:
        """Rebuilding at the event must not reuse the stale propagator."""
        engine120 = self._make_engine(ach=1.2)
        engine240 = self._make_engine(ach=2.4)
        state = {"A": 90.35826357366064}  # M(1) under start-impulse
        via240 = engine240.transport_step(state, natural_decay_rate=0.0)
        assert via240["A"] == pytest.approx(
            state["A"] * math.exp(-1.2), rel=REL, abs=ABS,
        )
        via120 = engine120.transport_step(state, natural_decay_rate=0.0)
        assert via120["A"] == pytest.approx(
            state["A"] * math.exp(-0.6), rel=REL, abs=ABS,
        )
        assert via240["A"] < via120["A"]


# ── Propagator cache, decay folding, and zero floors ──────────────────────

class TestPropagatorCacheAndDecay:
    def _make(self) -> ContamTransportEngine:
        return _engine(
            _layout(("A", 100.0)), _exhaust_airflow("A", ach=1.2),
            eta=0.0, decay=0.0,
        )

    def test_cache_returns_identical_object_and_keys_differ(self) -> None:
        engine = self._make()
        first = engine._get_propagator(0.0, 1.0)
        assert engine._get_propagator(0.0, 1.0) is first
        assert not np.allclose(first, engine._get_propagator(0.0, 0.5))
        assert not np.allclose(first, engine._get_propagator(0.3, 1.0))

    def test_decay_folds_as_exact_scalar_factor(self) -> None:
        """expm((A0 - lambda I) t) = exp(-lambda t) expm(A0 t): decay once."""
        engine = self._make()
        base = engine._get_propagator(0.0, 1.0)
        decayed = engine._get_propagator(0.3, 1.0)
        assert decayed == pytest.approx(
            math.exp(-0.3) * base, rel=1e-12, abs=1e-14,
        )

    def test_zero_mass_and_zero_source_stay_exactly_zero(self) -> None:
        engine = self._make()
        assert engine.transport_step({}) == {"A": 0.0}
        mass = _production_epoch_step(engine, {"A": 0.0}, {"A": 0.0}, 1.0)
        assert mass["A"] == pytest.approx(0.0, abs=1e-15)
