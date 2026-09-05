"""Route efficiency has one parameterisation, and clearance derives it (#25).

``route_efficiency_multipliers`` owns per-route efficiency. A measured
per-route clearance rate is a *derivation* of that field through
``route_efficiency_from_clearance_rates``, never a second live layer beside it:
the two parameterise the same quantity and neither is identifiable while both
exist.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

try:
    import jsonschema
except ImportError:  # pragma: no cover - mirrors test_json_schema_validation
    jsonschema = None  # type: ignore[assignment]

from engines.transmission_core import (
    DEFAULT_ROUTE_EFFICIENCY,
    route_efficiency_from_clearance_rates,
)
from orchestrator_init import (
    CLEARANCE_PARAMETERISATION_KEYS,
    _validate_route_parameterisation,
)
from tools.sanity_checker import PathogenProfile

# Rates spanning the range a portal-clearance layer would plausibly carry:
# mucociliary transit measured in hours against gastric transit measured in
# minutes. Only the ratios matter.
RATES_PER_HOUR = {
    "food_contamination": 0.25,
    "direct_contact": 0.5,
    "fomite": 0.5,
    "droplet": 3.5,
    "hvac_airborne": 3.5,
}
REFERENCE = "food_contamination"

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_BUNDLES = (
    "data/pathogens/active_profiles.json",
    "data/pathogens/edison_10pathogen_profiles.json",
)


class TestSensitivity:
    """Graded response: efficiency falls as the clearance rate rises."""

    def test_efficiency_is_ordered_inversely_to_the_clearance_rate(self) -> None:
        rates = {
            "food_contamination": 0.25,
            "direct_contact": 0.5,
            "droplet": 1.0,
            "hvac_airborne": 4.0,
        }
        efficiencies = route_efficiency_from_clearance_rates(rates, REFERENCE)
        ordered = [efficiencies[route] for route in rates]
        assert ordered == sorted(ordered, reverse=True)
        span = max(ordered) / min(ordered)
        assert span > 10.0, f"clearance looks dead: span={span:.3f}"

    def test_efficiency_is_the_reciprocal_rate_ratio(self) -> None:
        efficiencies = route_efficiency_from_clearance_rates(
            RATES_PER_HOUR, REFERENCE,
        )
        for route, rate in RATES_PER_HOUR.items():
            assert efficiencies[route] == pytest.approx(
                RATES_PER_HOUR[REFERENCE] / rate, rel=1e-12,
            )

    def test_a_uniform_clearance_rate_is_the_identity(self) -> None:
        """A pathogen-wide rate cannot express a route contrast."""
        rates = dict.fromkeys(DEFAULT_ROUTE_EFFICIENCY, 0.75)
        efficiencies = route_efficiency_from_clearance_rates(rates, REFERENCE)
        assert all(
            value == pytest.approx(1.0, rel=1e-12)
            for value in efficiencies.values()
        )

    @pytest.mark.parametrize("factor", [1e-3, 0.5, 2.0, 1e3])
    def test_a_common_factor_on_every_rate_moves_nothing(
        self, factor: float,
    ) -> None:
        """Absolute rate scale is the dose scale's, not efficiency's.

        Negative control on the confounding the conversion exists to keep
        visible: only ratios survive, so a clearance layer cannot smuggle in a
        second dose-scale degree of freedom.
        """
        base = route_efficiency_from_clearance_rates(RATES_PER_HOUR, REFERENCE)
        scaled = route_efficiency_from_clearance_rates(
            {route: rate * factor for route, rate in RATES_PER_HOUR.items()},
            REFERENCE,
        )
        assert scaled == pytest.approx(base, rel=1e-12)

    def test_changing_the_reference_rescales_every_route_alike(self) -> None:
        food = route_efficiency_from_clearance_rates(
            RATES_PER_HOUR, "food_contamination",
        )
        droplet = route_efficiency_from_clearance_rates(
            RATES_PER_HOUR, "droplet",
        )
        ratios = [droplet[route] / food[route] for route in RATES_PER_HOUR]
        assert ratios == pytest.approx([ratios[0]] * len(ratios), rel=1e-12)
        assert ratios[0] != pytest.approx(1.0, rel=1e-9)


class TestInvariants:
    """Bounds, and the reference route's defining property."""

    def test_the_reference_route_is_exactly_one(self) -> None:
        """Exactly, not nearly: it is the route the dose scale is fitted at."""
        for reference in RATES_PER_HOUR:
            efficiencies = route_efficiency_from_clearance_rates(
                RATES_PER_HOUR, reference,
            )
            assert efficiencies[reference] == pytest.approx(1.0, abs=0.0)

    def test_only_the_supplied_routes_are_returned(self) -> None:
        """Silence about a route is not a claim that it is the reference."""
        efficiencies = route_efficiency_from_clearance_rates(
            {"food_contamination": 0.25, "fomite": 0.5}, REFERENCE,
        )
        assert set(efficiencies) == {"food_contamination", "fomite"}

    def test_multipliers_are_finite_and_positive(self) -> None:
        efficiencies = route_efficiency_from_clearance_rates(
            RATES_PER_HOUR, REFERENCE,
        )
        assert all(0.0 < value < float("inf") for value in efficiencies.values())

    @pytest.mark.parametrize("rate", [0.0, -1.0, float("nan"), float("inf")])
    def test_an_unphysical_rate_is_refused(self, rate: float) -> None:
        rates = dict(RATES_PER_HOUR) | {"fomite": rate}
        with pytest.raises(ValueError, match="finite and positive"):
            route_efficiency_from_clearance_rates(rates, REFERENCE)

    def test_an_unknown_route_is_refused(self) -> None:
        rates = dict(RATES_PER_HOUR) | {"handshake": 1.0}
        with pytest.raises(ValueError, match="unknown route"):
            route_efficiency_from_clearance_rates(rates, REFERENCE)

    def test_an_unknown_reference_route_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a transmission route"):
            route_efficiency_from_clearance_rates(RATES_PER_HOUR, "oral")

    def test_a_reference_without_a_rate_is_refused(self) -> None:
        """Without the reference rate the multipliers have no scale."""
        rates = {
            route: rate
            for route, rate in RATES_PER_HOUR.items()
            if route != REFERENCE
        }
        with pytest.raises(ValueError, match="reference route"):
            route_efficiency_from_clearance_rates(rates, REFERENCE)


class TestLoaderRefusesASecondParameterisation:
    """The loader refuses the duplicate rather than silently ignoring it."""

    def test_a_lone_multiplier_field_loads(self) -> None:
        _validate_route_parameterisation(
            {
                "p": {
                    "route_efficiency_multipliers": dict(
                        DEFAULT_ROUTE_EFFICIENCY,
                    ),
                },
            },
        )

    def test_the_deprecated_alias_alone_still_loads(self) -> None:
        _validate_route_parameterisation(
            {"p": {"transmission_route_weights": {"fomite": 0.3}}},
        )

    def test_both_spellings_at_once_are_refused(self) -> None:
        with pytest.raises(ValueError, match="deprecated alias"):
            _validate_route_parameterisation(
                {
                    "p": {
                        "route_efficiency_multipliers": {"fomite": 0.3},
                        "transmission_route_weights": {"fomite": 0.3},
                    },
                },
            )

    @pytest.mark.parametrize("key", CLEARANCE_PARAMETERISATION_KEYS)
    def test_a_clearance_layer_is_refused(self, key: str) -> None:
        with pytest.raises(ValueError, match="second time"):
            _validate_route_parameterisation({"p": {key: {"fomite": 0.5}}})

    @pytest.mark.parametrize("key", CLEARANCE_PARAMETERISATION_KEYS)
    def test_a_no_op_clearance_layer_is_refused_too(self, key: str) -> None:
        """Shipping the layer inert is how it becomes live later."""
        with pytest.raises(ValueError, match="second time"):
            _validate_route_parameterisation({"p": {key: {}}})

    def test_the_shipped_bundles_declare_one_parameterisation(self) -> None:
        for name in SHIPPED_BUNDLES:
            data = json.loads((REPO_ROOT / name).read_text(encoding="utf-8"))
            _validate_route_parameterisation(
                {p["pathogen_id"]: deepcopy(p) for p in data["pathogens"]},
            )


class TestSanityCheckerRefusesASecondParameterisation:
    """The pre-run check says the same thing the loader does."""

    BASE = {"pathogen_id": "p", "name": "P"}

    def test_a_profile_with_only_multipliers_is_accepted(self) -> None:
        profile = PathogenProfile(
            **self.BASE, route_efficiency_multipliers={"fomite": 0.3},
        )
        assert profile.route_efficiency_multipliers == {"fomite": 0.3}

    @pytest.mark.parametrize(
        "value", [0.5, {}, {"fomite": 0.5}, [0.5], "0.5"],
    )
    @pytest.mark.parametrize("key", CLEARANCE_PARAMETERISATION_KEYS)
    def test_a_clearance_layer_of_any_shape_is_refused(
        self, key: str, value: object,
    ) -> None:
        """Refused for existing, not for being malformed."""
        with pytest.raises(ValidationError, match="second time"):
            PathogenProfile(**self.BASE, **{key: value})

    def test_both_spellings_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="declare one"):
            PathogenProfile(
                **self.BASE,
                route_efficiency_multipliers={"fomite": 0.3},
                transmission_route_weights={"fomite": 0.3},
            )


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
class TestSchemaRefusesASecondParameterisation:
    """The authoring gate says the same thing the loader does."""

    @staticmethod
    def _shipped(mutation: dict[str, object]) -> tuple[dict, dict]:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "pathogen_profiles.schema.json").read_text(
                encoding="utf-8",
            ),
        )
        data = json.loads(
            (REPO_ROOT / SHIPPED_BUNDLES[0]).read_text(encoding="utf-8"),
        )
        data["pathogens"][0].update(deepcopy(mutation))
        return schema, data

    def test_the_shipped_bundle_is_valid_unmutated(self) -> None:
        schema, data = self._shipped({})
        jsonschema.validate(instance=data, schema=schema)

    @pytest.mark.parametrize("key", CLEARANCE_PARAMETERISATION_KEYS)
    def test_a_clearance_layer_fails_the_schema(self, key: str) -> None:
        schema, data = self._shipped({key: {"fomite": 0.5}})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=schema)

    def test_both_spellings_fail_the_schema(self) -> None:
        schema, data = self._shipped(
            {"transmission_route_weights": {"fomite": 0.3}},
        )
        assert "route_efficiency_multipliers" in data["pathogens"][0]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=schema)
