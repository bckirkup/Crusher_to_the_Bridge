"""The direct-contact route has one efficiency owner (#22).

``contact_transfer_fraction`` multiplied the direct-contact pathway dose in
``_direct_contact_dose`` / ``_per_partner_contact_dose``, and
``route_efficiency_multipliers["direct_contact"]`` multiplies the same
pathway's dose immediately afterwards in ``_apply_route_efficiencies``. Two
scalars in the same position in a product are one degree of freedom: no run
can distinguish (a, b) from (a·b, 1), so the field is retired and refused at
load rather than defaulted to 1.0.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

try:
    import jsonschema
except ImportError:  # pragma: no cover - mirrors test_json_schema_validation
    jsonschema = None  # type: ignore[assignment]

from engines.transmission_core import TransmissionCore
from orchestrator_init import _validate_route_parameterisation
from telemetry_buffer.observation_model import bounded_screen
from tools.sanity_checker import PathogenProfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_BUNDLE = "data/pathogens/active_profiles.json"
RETIRED_KEY = "contact_transfer_fraction"


def _delivered(direct_contact_efficiency: float, dose: float = 8.0) -> float:
    """Dose delivered to one host through the direct-contact pathway."""
    core = TransmissionCore(rng=np.random.default_rng(0), zone_types={})
    agent_doses = {1: dose}
    pathway_doses = {1: {"direct_contact": dose}}
    core._apply_route_efficiencies(
        {"route_efficiency_multipliers": {
            "direct_contact": direct_contact_efficiency,
        }},
        agent_doses,
        pathway_doses,
    )
    return agent_doses[1]


class TestTheSurvivingOwnerIsLive:
    """Removing the second multiplier left the route's efficiency working."""

    @pytest.mark.parametrize(
        ("efficiency", "expected"),
        [(0.06, 0.48), (0.25, 2.0), (0.5, 4.0), (1.0, 8.0)],
    )
    def test_dose_scales_linearly_with_the_route_efficiency(
        self, efficiency: float, expected: float,
    ) -> None:
        assert _delivered(efficiency) == pytest.approx(expected, rel=1e-12)

    def test_the_route_still_spans_the_retired_interval(self) -> None:
        """The 0.06-0.50 span is still reachable, through one field."""
        span = _delivered(0.50) / _delivered(0.06)
        assert span == pytest.approx(0.50 / 0.06, rel=1e-12)
        assert span > 8.0, f"direct-contact efficiency looks dead: {span:.3f}"


class TestOnlyTheProductWasIdentifiable:
    """Why the field is retired rather than sourced."""

    @pytest.mark.parametrize(
        ("efficiency", "retired_value"),
        [(1.0, 0.25), (0.5, 0.5), (0.25, 1.0), (0.0625, 4.0)],
    )
    def test_every_factorisation_of_one_product_delivers_one_dose(
        self, efficiency: float, retired_value: float,
    ) -> None:
        """(a, b) and (a·b, 1) are the same run, so b is unmeasurable."""
        assert _delivered(efficiency * retired_value) == pytest.approx(
            _delivered(0.25), rel=1e-12,
        )

    def test_the_engine_no_longer_reads_the_retired_key(self) -> None:
        """A profile carrying it changes nothing, so nothing is silent."""
        core = TransmissionCore(rng=np.random.default_rng(0), zone_types={})
        with_key = {"route_efficiency_multipliers": {"direct_contact": 0.5}}
        without_key = deepcopy(with_key)
        with_key[RETIRED_KEY] = 0.01
        assert core._route_efficiencies(with_key) == core._route_efficiencies(
            without_key,
        )


class TestTheRetiredFieldIsRefused:
    """Refused at every gate, so it cannot come back as a live layer."""

    def test_the_loader_refuses_it(self) -> None:
        with pytest.raises(ValueError, match="identifiable"):
            _validate_route_parameterisation({"p": {RETIRED_KEY: 0.25}})

    def test_the_loader_refuses_an_inert_one_too(self) -> None:
        """Shipping it at 1.0 is how it becomes live later."""
        with pytest.raises(ValueError, match="identifiable"):
            _validate_route_parameterisation({"p": {RETIRED_KEY: 1.0}})

    @pytest.mark.parametrize("value", [0.25, 1.0, 0.0, {}, "0.25"])
    def test_the_sanity_checker_refuses_it_in_any_shape(
        self, value: object,
    ) -> None:
        """Refused for existing, not for being malformed."""
        with pytest.raises(ValidationError, match="identifiable"):
            PathogenProfile(
                pathogen_id="p", name="P", **{RETIRED_KEY: value},
            )

    def test_the_shipped_bundle_does_not_declare_it(self) -> None:
        data = json.loads(
            (REPO_ROOT / SHIPPED_BUNDLE).read_text(encoding="utf-8"),
        )
        assert all(RETIRED_KEY not in p for p in data["pathogens"])

    @pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
    def test_the_schema_refuses_it(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "pathogen_profiles.schema.json").read_text(
                encoding="utf-8",
            ),
        )
        data = json.loads(
            (REPO_ROOT / SHIPPED_BUNDLE).read_text(encoding="utf-8"),
        )
        data["pathogens"][0][RETIRED_KEY] = 0.25
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=schema)


def test_the_screen_box_no_longer_ranges_the_retired_field() -> None:
    """A design ranging half of a product reports an aliased effect."""
    paths = [factor.path for factor in bounded_screen.NOROVIRUS_FACTORS]
    assert (RETIRED_KEY,) not in paths
    assert len(set(paths)) == len(paths)
