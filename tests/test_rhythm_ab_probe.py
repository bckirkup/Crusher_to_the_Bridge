"""NORO-RHYTHM-01 probe + readout unit coverage.

The probe's ``--arm`` flag must write exactly
``config_overrides.rhythm.enabled`` and nothing else; the readout's rate
helpers must keep rare-event cells honest (Wilson intervals, paired-seed
discordance keyed on run id).
"""

from __future__ import annotations

import pytest

from tools.noro_diag import rhythm_ab_probe as probe
from tools.noro_diag import rhythm_ab_readout as readout


def _spec() -> dict:
    return {
        "config_overrides": {
            "transmission": {"sanitary_visit_mode": "dwell_weighted"},
        },
    }


def test_inject_arm_on_writes_only_rhythm_enabled() -> None:
    spec = _spec()
    probe._inject_arm(spec, "on")
    assert spec["config_overrides"]["rhythm"] == {"enabled": True}
    assert spec["config_overrides"]["transmission"] == (
        _spec()["config_overrides"]["transmission"]
    )


def test_inject_arm_off_writes_only_rhythm_enabled() -> None:
    spec = _spec()
    probe._inject_arm(spec, "off")
    assert spec["config_overrides"]["rhythm"] == {"enabled": False}


def test_inject_arm_none_leaves_spec_untouched() -> None:
    spec = _spec()
    probe._inject_arm(spec, None)
    assert spec == _spec()
    assert "rhythm" not in spec["config_overrides"]


def test_inject_arm_preserves_existing_rhythm_keys() -> None:
    spec = _spec()
    spec["config_overrides"]["rhythm"] = {"other_key": 1}
    probe._inject_arm(spec, "off")
    assert spec["config_overrides"]["rhythm"] == {
        "other_key": 1,
        "enabled": False,
    }


def test_inject_arm_rejects_unknown_arm() -> None:
    with pytest.raises(ValueError):
        probe._inject_arm(_spec(), "sideways")


def test_wilson_zero_of_zero_is_empty() -> None:
    assert readout._wilson(0, 0) == (0.0, 0.0)


def test_wilson_all_fail_bounds_are_small() -> None:
    lo, hi = readout._wilson(0, 2000)
    assert lo <= 1e-9
    assert 0.0 < hi < 0.01


class _P:
    def __init__(self, name: str) -> None:
        self.stem = name


def test_paired_discordance_keys_on_run_id() -> None:
    off = [
        (_P("r1"), {}, {"ignited": True}),
        (_P("r2"), {}, {"ignited": False}),
        (_P("r3"), {}, {"ignited": True}),
    ]
    on = [
        (_P("r1"), {}, {"ignited": True}),
        (_P("r2"), {}, {"ignited": True}),
        (_P("r9"), {}, {"ignited": False}),
    ]
    d = readout._paired_discordance(off, on)
    assert d == {
        "n_paired": 2, "off_only": 0, "on_only": 1, "both": 1, "neither": 0,
    }


def test_landing_partition_splits_immune_cabin_and_venue() -> None:
    rhythm = {
        "emesis_rows": [
            {"gen_class": "acquired", "zone_type": "Cabin",
             "n_occupants": 2, "n_susceptible": 0},
            {"gen_class": "acquired", "zone_type": "Cabin",
             "n_occupants": 3, "n_susceptible": 2},
            {"gen_class": "acquired", "zone_type": "Cabin",
             "n_occupants": 0, "n_susceptible": 0},
            {"gen_class": "acquired", "zone_type": "Dining",
             "n_occupants": 160, "n_susceptible": 150},
            {"gen_class": "import", "zone_type": "Dining",
             "n_occupants": 160, "n_susceptible": 150},
        ],
    }
    part = readout._landing_partition([(_P("r"), {}, rhythm)])
    assert part["secondary_emesis"] == 4
    assert part["secondary_cabin"] == 3
    assert part["secondary_cabin_immune_occupancy"] == 1
    assert part["secondary_cabin_susceptible_present"] == 1
    assert part["secondary_cabin_empty"] == 1
    assert part["immune_cabin_share"] == pytest.approx(1 / 3)
    assert part["empty_cabin_share"] == pytest.approx(1 / 3)
    assert part["shared_venue_share"] == pytest.approx(0.25)
    assert part["shared_venue_median_susceptibles"] == 150


def test_defect_witness_flags_unconsumed_flag() -> None:
    runs = [(_P("r"), {}, {"rhythm_attached": False, "emit_calls": {}})]
    w = readout._defect_witnesses(runs, "on")
    assert w["runs_attached"] == 0
    assert w["runs_total"] == 1
