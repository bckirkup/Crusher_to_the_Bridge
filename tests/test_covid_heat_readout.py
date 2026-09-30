"""HEAT-V1 readout: delivery audit echoes and the both-legs test."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_heat_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_heat_v1_design.json"
)
THETA = 2.37e11
SEED = 20200205

UNIT_RATES = dict(mod.SHIPPED_ACTIVITY_RATES)


def _resolved_contacts(rates: dict | None) -> dict | None:
    if rates is None:
        return None
    return {
        act: {"passenger": float(r), "crew": float(r)}
        for act, r in rates.items()
    }


def _delivery(
    *,
    half_life: float = 1.1,
    route_eff: dict | None = None,
    pool: str = "airflow",
    cap: dict | None = None,
    cap_active: bool = True,
    contacts: dict | None = None,
    contacts_absent: bool = False,
) -> dict:
    eff = dict(mod.SHIPPED_ROUTE_EFFICIENCIES)
    eff.update(route_eff or {})
    return {
        "airborne_half_life_hours": half_life,
        "route_efficiency_multipliers": eff,
        "pathogen_pool_transport": pool,
        "exposure_cap": dict(cap or {}),
        "exposure_cap_active": cap_active,
        "activity_contacts": (
            None if contacts_absent else _resolved_contacts(
                UNIT_RATES if contacts is None else contacts
            )
        ),
    }


def _payload(
    arm: str = "D0_declared",
    *,
    theta: float = THETA,
    seed: int = SEED,
    rec: int = 3000,
    before: int = 1800,
    inf: float = 3550.0,
    inf_before: float | None = 3400.0,
    inf_during: float | None = 150.0,
    delivery: dict | None = None,
    expo_flag: bool | None = None,
    onset_recording: dict | None = None,
    eligibility: list | None = None,
    spec: dict | None = None,
    seeded_count: int = 1,
    hosts: list[dict] | None = None,
    aboard_route: dict | None = None,
    during_route: dict | None = None,
    during_zone: dict | None = None,
    during_role: dict | None = None,
    onset_curve: dict | None = None,
    with_ring: bool = True,
) -> dict:
    p = {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": inf_before,
        "infections_during_quarantine": inf_during,
        "during_quarantine_by_route": during_route,
        "during_quarantine_by_zone_class": during_zone,
        "during_quarantine_by_role": during_role,
        "onset_curve": onset_curve
        or {str(d): {"passenger": 10} for d in range(13, 19)},
        "exposure_cap_include_fixed_rings": expo_flag,
        "delivery": delivery if delivery is not None else _delivery(),
    }
    if onset_recording is not None:
        p["onset_recording"] = onset_recording
    if eligibility is not None:
        p["onset_eligibility_by_severity"] = eligibility
    if with_ring:
        p["seed_ring"] = {
            "seed_spec": spec
            or {"onset_day": -1.0, "count": 1, "role": "passenger"},
            "seeded_count": seeded_count,
            "seeded_hosts": hosts if hosts is not None else [
                {"role": "passenger"},
            ],
            "aboard_window_by_route": aboard_route,
        }
    return p


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def test_declared_defaults_and_corners():
    d = _declared_for()
    assert d["half_life"] == pytest.approx(1.1)
    assert d["route_eff"]["droplet"] == pytest.approx(0.3)
    assert d["pool_transport"] == "airflow"
    assert d["exposure_cap"] == {}
    assert d["activity_contacts"] == UNIT_RATES
    assert d["onset_recording"] is None

    d = _declared_for({
        "pathogen_overrides": {"sars_cov2_resp": {
            "airborne_half_life_hours": 0.5,
        }},
        "profile_route_efficiency_multipliers": {
            "droplet": 0.03, "hvac_airborne": 0.03,
        },
        "pathogen_pool_transport": "none",
        "transmission_overrides": {
            "exposure_cap": {"include_fixed_rings": True},
        },
    })
    assert d["half_life"] == pytest.approx(0.5)
    assert d["route_eff"]["droplet"] == pytest.approx(0.03)
    assert d["route_eff"]["direct_contact"] == pytest.approx(0.25)
    assert d["pool_transport"] == "none"
    assert d["exposure_cap"] == {"include_fixed_rings": True}

    d = _declared_for({
        "transmission_overrides": {
            "activity_contacts": {"enabled": False},
        },
    })
    assert d["activity_contacts"] is None

    halved = {k: v / 2 for k, v in UNIT_RATES.items()}
    d = _declared_for({
        "transmission_overrides": {
            "activity_contacts": {
                "enabled": True, "rates_per_hour": halved,
            },
        },
    })
    assert d["activity_contacts"] == halved


def test_audit_cell_clean_and_delivery_failures():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared, THETA) == []
    assert mod.audit_cell(
        _payload(with_ring=False), declared, THETA,
    ) == ["missing seed_ring block"]

    fails = mod.audit_cell(
        _payload(delivery=_delivery(half_life=0.5)), declared, THETA,
    )
    assert fails
    assert "airborne_half_life_hours" in fails[0]

    fails = mod.audit_cell(
        _payload(delivery=_delivery(route_eff={"droplet": 0.03})),
        declared, THETA,
    )
    assert fails
    assert "route_efficiency_multipliers" in fails[0]

    fails = mod.audit_cell(
        _payload(delivery=_delivery(pool="none")), declared, THETA,
    )
    assert fails
    assert "pathogen_pool_transport" in fails[0]

    fails = mod.audit_cell(
        _payload(delivery=_delivery(cap_active=False)), declared, THETA,
    )
    assert fails
    assert "exposure_cap_active" in fails[0]

    fails = mod.audit_cell(
        _payload(delivery=_delivery(contacts_absent=True)),
        declared, THETA,
    )
    assert fails
    assert "activity_contacts" in fails[0]


def test_audit_cell_armed_corners():
    heat = _declared_for({
        "pathogen_overrides": {"sars_cov2_resp": {
            "airborne_half_life_hours": 0.5,
        }},
        "profile_route_efficiency_multipliers": {
            "droplet": 0.03, "hvac_airborne": 0.03,
        },
        "pathogen_pool_transport": "none",
        "transmission_overrides": {
            "exposure_cap": {"include_fixed_rings": True},
        },
    })
    good = _payload(
        delivery=_delivery(
            half_life=0.5,
            route_eff={"droplet": 0.03, "hvac_airborne": 0.03},
            pool="none",
            cap={"include_fixed_rings": True},
        ),
        expo_flag=True,
    )
    assert mod.audit_cell(good, heat, THETA) == []

    poly = _declared_for({
        "transmission_overrides": {
            "activity_contacts": {"enabled": False},
        },
    })
    assert mod.audit_cell(
        _payload(delivery=_delivery(contacts_absent=True)), poly, THETA,
    ) == []

    fails = mod.audit_cell(
        _payload(spec={"onset_day": -2.0, "count": 2, "role": "crew"},
                 seeded_count=2),
        _declared_for(), THETA,
    )
    assert any("seed_spec.onset_day" in f for f in fails)
    assert any("seed_spec.count" in f for f in fails)
    assert any("seeded_count" in f for f in fails)
    assert fails


def test_audit_cell_ref_channel_echoes():
    ref = _declared_for({
        "pathogen_overrides": {"sars_cov2_resp": {
            "observation_model": {
                "onset_recording": {
                    "symptomatic_at_confirmation_required": True,
                    "report_probability": 0.56,
                },
                "syndrome_case_eligibility_by_severity": [0, 0, 0, 1, 1],
            }}}})
    good = _payload(
        onset_recording={
            "symptomatic_at_confirmation_required": True,
            "report_probability": 0.56,
        },
        eligibility=[0, 0, 0, 1, 1],
    )
    assert mod.audit_cell(good, ref, THETA) == []
    bad = _payload(
        onset_recording={"report_probability": 0.28},
        eligibility=[0, 0, 1, 1, 1],
    )
    fails = mod.audit_cell(bad, ref, THETA)
    assert "onset_recording echo != declared block" in fails
    assert "onset_eligibility_by_severity echo != declared ladder" in fails


def test_row_stats_takeoff_bands_strata_and_kink():
    payloads = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(payloads)
    assert stats["takeoff_n"] == 10
    assert stats["timing_leg_in_band"] is True
    assert stats["truth_leg_in_band"] is False
    assert stats["both_legs"] is False
    assert stats["during_dominant"] is False
    assert stats["day16_kink"]["post_over_pre_median"] == pytest.approx(
        1.0,
    )

    # A fizzle-majority row: fewer than half the seeds reach takeoff.
    fizzle = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200209)
    ] + [
        _payload(seed=s, rec=0, before=0, inf=0.0)
        for s in range(20200209, 20200215)
    ]
    stats = mod._row_stats(fizzle)
    assert stats["fizzle_majority"] is True
    stats = mod._row_stats(payloads[:4])
    assert stats["fizzle_majority"] is False
    assert stats["timing_leg_in_band"] is False

    in_band = [
        _payload(seed=s, rec=200, before=34, inf=800.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(in_band)
    assert stats["both_legs"] is True

    late = [
        _payload(
            seed=s, rec=200, before=20, inf=800.0,
            inf_before=300.0, inf_during=500.0,
        )
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(late)
    assert stats["during_dominant"] is True
    assert stats["during_share"]["median"] == pytest.approx(0.625)

    payloads = [_payload(rec=0, before=0, inf=0.0)]
    stats = mod._row_stats(payloads)
    assert stats["takeoff_n"] == 0
    assert stats["before_share"]["median"] is None


def test_row_stats_route_decomposition_pools_takeoff_only():
    payloads = [
        _payload(
            seed=s, rec=200, before=40, inf=800.0,
            aboard_route={"droplet": 20, "hvac_airborne": 10},
            during_route={"droplet": 5},
            during_zone={"public": 4, "cabin": 1},
            during_role={"passenger": 4, "crew": 1},
        )
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(payloads)
    assert stats["aboard_window_by_route_pooled"] == {
        "droplet": 200, "hvac_airborne": 100,
    }
    assert stats["during_quarantine_by_route_pooled"] == {"droplet": 50}
    assert stats["during_quarantine_by_zone_class_pooled"] == {
        "public": 40, "cabin": 10,
    }
    assert stats["during_quarantine_by_role_pooled"] == {
        "passenger": 40, "crew": 10,
    }


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "campaign_results/hv/cells"
    cells_dir.mkdir(parents=True)
    design_path = tmp_path / "design.json"
    shutil.copy(DESIGN, design_path)

    cells_dir.joinpath("a.json").write_text(json.dumps(_payload()))
    cells_dir.joinpath("b.json").write_text(json.dumps(
        _payload(arm="NOPE", seed=20200206),
    ))
    cells_dir.joinpath("skip.txt").write_text("not json")

    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
        "--out", str(out), "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 2
    assert list(report["audit_failures"]) == ["b.json"]
    assert "theta=2.37e+11|arm=D0_declared" in report["rows"]

    capsys.readouterr()
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
    ])
    assert rc == 2
    assert "660" in capsys.readouterr().err

    with pytest.raises(ValueError, match="escapes"):
        mod.main([
            "--cells", "/etc", "--design", str(design_path),
            "--allow-partial",
        ])
