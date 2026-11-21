"""noro_existing_return extraction profile tests.

Covers all three existing norovirus cohorts:
- Explorer (`noro_explorer_reconstruction_01`): summary.json with
  introduction/initiation_manifest, onsets_by_day variants, reporting_by_day,
  derived first_role from timeseries, and absent environmental observations.
- Joint evaluation (`noro_paper1_joint_eval_01`): summary.json +
  joint_eval.json.gz sidecar with explicit first_role, curves + day0_label +
  preboarding_declared counts, and environmental swab/tank summaries.
- Solver reference (`noro_supply_solver_screen_01_bf0`): summary.json only
  (verifies large growth_census.json.gz is never read via member_allowlist),
  census n_imports/n_acquired, initiation.resolved, route aggregates, and
  daily reporting derived from hourly timeseries.
"""
from __future__ import annotations

import gzip
import io
import json
import zipfile

from picard_framework.analysis.campaign_reducer import (
    adapters,
    noro_existing_return,
    worker,
)
from picard_framework.analysis.campaign_reducer.materialize import (
    run_materialization,
)
from tests.analysis.campaign_reducer.test_d7_first_paper_scalar import (
    _rig,
    _spec,
    _src,
)

VEC = "noro_existing_return_vectors.jsonl"


def _make_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, raw in members.items():
            zf.writestr(name, raw)
    return buf.getvalue()


def _explorer_zip(seed: int = 101) -> bytes:
    summary = {
        "campaign": "noro_explorer_reconstruction_01",
        "tier": "tier_1_baseline",
        "declared_arm": {"arm": "baseline_v1", "status": "ok"},
        "seed": seed,
        "platform": "explorer_of_the_seas",
        "engine_git_sha": "bf0ec168",
        "status": "completed",
        "effective_state": {"transmission_mode": "mechanistic", "rhythm": "cruise"},
        "initially_infected_agent_ids": ["pax-1", "pax-2", "crew-1"],
        "introduction": {
            "declared_seed_agent_ids": ["pax-1"],
            "initiation_manifest": {
                "mode": "boarding+seeds",
                "boarding": {
                    "norovirus": {
                        "drawn_by_role": {"passenger": 2, "crew": 1},
                        "composition": {"exposed": 2, "infectious": 1},
                    },
                },
            },
        },
        "summary": {
            "passenger_complement": 3100,
            "crew_complement": 1180,
            "cumulative_ever_infected": 42,
            "cumulative_ever_infected_passenger": 35,
            "cumulative_ever_infected_crew": 7,
            "cumulative_ever_ill": 30,
            "cumulative_ever_ill_passenger": 25,
            "cumulative_ever_ill_crew": 5,
            "cumulative_reported_cases": 18,
            "cumulative_reported_cases_passenger": 15,
            "cumulative_reported_cases_crew": 3,
            "cumulative_reported_noise_cases": 4,
            "trigger_status": "OUTBREAK",
            "infections_by_dominant_route": {"fomite": 28, "droplet": 11},
            "infection_dose_share_by_route": {"fomite": 0.72, "droplet": 0.28},
        },
        "derived": {"vsp_trigger_epoch": 120, "detection_epoch": 48},
        "role_checkpoints": {"day_3": {"passenger": 3, "crew": 1}},
        "onsets_by_day": {
            "all": [1, 2, 5],
            "excluding_declared_seeds": [0, 2, 5],
            "incident": [0, 1, 5],
        },
        "reporting_by_day": {
            "passenger": [0, 2, 5],
            "crew": [0, 0, 1],
        },
        "line_list_cases": 18,
        "timeseries": [
            {
                "epoch": 24,
                "cumulative_reported_cases_passenger": 2,
                "cumulative_reported_cases_crew": 0,
                "cumulative_reported_cases": 2,
            },
            {
                "epoch": 48,
                "cumulative_reported_cases_passenger": 5,
                "cumulative_reported_cases_crew": 1,
                "cumulative_reported_cases": 6,
            },
        ],
    }
    return _make_zip({
        "summary.json": json.dumps(summary).encode(),
        "sentinel_line_list.json": json.dumps({"clinical_cases": []}).encode(),
    })


def _joint_eval_zip(seed: int = 202) -> bytes:
    summary = {
        "run_id": f"fl_je_meg_12d_quiet__s{seed}",
        "parameters": {
            "tier_id": "fl_je_meg_12d_quiet",
            "seed": seed,
            "platform_id": "mega_cruise_5000",
            "engine_git_sha": "90aa3ec2",
        },
        "summary": {
            "passenger_complement": 4000,
            "crew_complement": 1500,
            "cumulative_ever_infected": 90,
            "cumulative_ever_infected_passenger": 75,
            "cumulative_ever_infected_crew": 15,
            "cumulative_ever_ill": 60,
            "cumulative_ever_ill_passenger": 50,
            "cumulative_ever_ill_crew": 10,
            "cumulative_reported_cases": 35,
            "cumulative_reported_cases_passenger": 30,
            "cumulative_reported_cases_crew": 5,
            "cumulative_reported_noise_cases": 6,
            "infections_by_dominant_route": {"fomite": 60, "aerosol": 30},
        },
        "derived": {"vsp_trigger_epoch": 96},
        "role_checkpoints": {"day_3": {"passenger": 10, "crew": 2}},
        "joint_eval": {
            "arm": {"arm": "bridge", "hull": "mega_cruise_5000", "epochs": 288},
            "effective_config": {"observation_mode": "full_env"},
            "burden": {
                "passenger_complement": 4000,
                "crew_complement": 1500,
                "cumulative_reported_cases_passenger": 30,
                "cumulative_reported_cases_crew": 5,
            },
            "threshold": {
                "vsp_trigger_epoch": 96,
                "posted": True,
                "trigger_status": "OUTBREAK",
            },
            "first_role": {
                "category": "crew_first",
                "first_crew_report_epoch": 18,
                "first_passenger_report_epoch": 30,
            },
        },
    }
    joint_eval = {
        "schema": "noro_paper1_joint_eval_01/1",
        "curves": {
            "preboarding_declared_passenger": 3,
            "preboarding_declared_crew": 1,
            "onsets_daily": [2, 4, 8],
            "reported_daily_passenger": [1, 3, 6],
            "reported_daily_crew": [1, 1, 0],
            "day0_label": "embarkation_day_0",
            "line_list_cases": 35,
            "line_list_channels": ["clinic", "cabin"],
        },
        "environment": {
            "units": {"swab": "copies/swab", "tank": "copies/L"},
            "swab_rows_rule": "one row per swab with recovered copies > 0; zero-recovery swabs are in swab_total only",
            "swab_total": 100,
            "swab_rows_kept": 2,
            "swab_detected_total": 2,
            "swab_censored_total": 1,
            "first_swab_detected_epoch": 36,
            "swab_rows": [
                {
                    "epoch": 36,
                    "zone": "buffet",
                    "surface_class": "high_touch",
                    "density": 12.5,
                    "recovered": 50.0,
                    "lod": 10.0,
                    "detected": True,
                    "censored_below_lod": False,
                },
                {
                    "epoch": 60,
                    "zone": "railing",
                    "surface_class": "medium_touch",
                    "density": 2.5,
                    "recovered": 8.0,
                    "lod": 10.0,
                    "detected": False,
                    "censored_below_lod": True,
                },
            ],
            "tank_assays": 2,
            "tank_detected_total": 2,
            "tank_censored_total": 0,
            "first_tank_detected_epoch": 24,
            "tank_rows": [
                {
                    "epoch": 24,
                    "instrument": "ddPCR",
                    "stream": "blackwater",
                    "concentration": 1.2e4,
                    "lod": 500.0,
                    "loq": 2000.0,
                    "detected": True,
                    "quantifiable": True,
                    "censored_below_lod": False,
                },
                {
                    "epoch": 48,
                    "instrument": "ddPCR",
                    "stream": "blackwater",
                    "concentration": 800.0,
                    "lod": 500.0,
                    "loq": 2000.0,
                    "detected": True,
                    "quantifiable": False,
                    "censored_below_lod": False,
                },
            ],
        },
    }
    return _make_zip({
        "summary.json": json.dumps(summary).encode(),
        "joint_eval.json.gz": gzip.compress(json.dumps(joint_eval).encode()),
    })


def _solver_ref_zip(seed: int = 303) -> bytes:
    summary = {
        "run_id": f"exp_station_lots_continuous__s{seed}",
        "parameters": {
            "tier_id": "exp_station_lots_continuous",
            "seed": seed,
            "platform_id": "expedition_cruise_450",
            "engine_git_sha": "bf0ec168",
        },
        "initiation": {"resolved": {"mode": "preboarding_binomial"}},
        "census": {"n_imports": 4, "n_acquired": 21},
        "summary": {
            "passenger_complement": 3000,
            "crew_complement": 1200,
            "cumulative_ever_infected": 25,
            "cumulative_ever_ill": 19,
            "cumulative_reported_cases": 11,
            "cumulative_reported_cases_passenger": 9,
            "cumulative_reported_cases_crew": 2,
            "infections_by_dominant_route": {"fomite": 15, "droplet": 6},
        },
        "derived": {"vsp_trigger_epoch": None},
        "timeseries": [
            {
                "epoch": 0,
                "cumulative_reported_cases_passenger": 0,
                "cumulative_reported_cases_crew": 0,
                "cumulative_reported_cases": 0,
            },
            {
                "epoch": 23,
                "cumulative_reported_cases_passenger": 2,
                "cumulative_reported_cases_crew": 0,
                "cumulative_reported_cases": 2,
            },
            {
                "epoch": 47,
                "cumulative_reported_cases_passenger": 9,
                "cumulative_reported_cases_crew": 2,
                "cumulative_reported_cases": 11,
            },
        ],
    }
    # Deliberately invalid gzip in growth_census.json.gz to prove the adapter
    # never reads it when member_allowlist is applied.
    return _make_zip({
        "summary.json": json.dumps(summary).encode(),
        "growth_census.json.gz": b"NOT_VALID_GZIP_MUST_NOT_BE_READ" * 200,
        "rss_samples.json": json.dumps({"samples": []}).encode(),
    })


def _load_vec_rows(store, rid: str = "red-fp") -> list[dict]:
    prefix = f"campaign/_derived/reducer/v1/attempts/{rid}/shards/"
    return [
        json.loads(line)
        for key in store.list(prefix)
        if key.endswith("/" + VEC)
        for line in store.get(key).splitlines()
        if line.strip()
    ]


def test_registry_and_worker_defaults():
    assert adapters.verify_registry()["ok"] is True
    defaults = worker._profile_defaults({"extraction_profile": "noro_existing_return"})
    assert defaults["member_allowlist"] == ("summary.json", "joint_eval.json.gz")
    assert defaults["emit_scalars"] is False
    assert noro_existing_return.definition_version() == "noro_existing_return/1.0.0"
    assert noro_existing_return._design_stratum(
        "paper1_joint_eval", "fl_je_exp_12d_eval_contaminated", "campaign/noro_paper1_joint_eval_01/fl_je_exp_12d_eval_contaminated/r.zip",
    ) == "evaluation"
    assert noro_existing_return._design_stratum(
        "paper1_joint_eval", "fl_je_meg_7d_near", "campaign/noro_paper1_joint_eval_01/fl_je_meg_7d_near/r.zip",
    ) == "diagnostic"
    assert noro_existing_return._design_stratum(
        "paper1_joint_eval", "repro_exp_12d", "campaign/noro_paper1_joint_eval_01/repro_exp_12d/r.zip", arm="reproduction",
    ) == "reproduction"


def test_mixed_three_cohorts_materialization():
    transport, store, ledger = _rig()
    k_exp = "campaign/noro_explorer_reconstruction_01/tier_1_baseline/run_101.zip"
    k_je = "campaign/noro_paper1_joint_eval_01/fl_je_meg_12d_quiet/run_202.zip"
    k_bf0 = "campaign/noro_supply_solver_screen_01_bf0/exp_station_lots_continuous/run_303.zip"
    transport.put(k_exp, _explorer_zip(101))
    transport.put(k_je, _joint_eval_zip(202))
    transport.put(k_bf0, _solver_ref_zip(303))

    defaults = noro_existing_return.defaults()
    sources = [
        _src(
            k_exp,
            family="campaign_summary_zip",
            source_id="src-exp",
            campaign_id="noro_explorer_reconstruction_01",
            seed=101,
            member_allowlist=defaults["member_allowlist"],
            emit_scalars=False,
        ),
        _src(
            k_je,
            family="campaign_summary_zip",
            source_id="src-je",
            campaign_id="noro_paper1_joint_eval_01",
            seed=202,
            member_allowlist=defaults["member_allowlist"],
            emit_scalars=False,
        ),
        _src(
            k_bf0,
            family="growth_census_zip",
            source_id="src-bf0",
            campaign_id="noro_supply_solver_screen_01_bf0",
            seed=303,
            member_allowlist=defaults["member_allowlist"],
            emit_scalars=False,
        ),
    ]
    spec = _spec(sources, extraction_profile="noro_existing_return")
    res = run_materialization(spec, transport, store, ledger)
    assert res.status == "completed"

    rows = _load_vec_rows(store)
    assert len(rows) == 3
    by_cohort = {r["values"]["cohort"]: r for r in rows}
    assert set(by_cohort) == {
        "explorer_reconstruction",
        "paper1_joint_eval",
        "supply_solver_reference",
    }

    # Explorer checks
    exp = by_cohort["explorer_reconstruction"]
    ev = exp["values"]
    assert ev["arm"] == "baseline_v1"
    assert ev["total_passengers"] == 3100
    assert ev["total_crew"] == 1180
    assert ev["burden"]["ever_ill_total"] == 30
    assert ev["initial_infected_total"] == 3
    assert ev["initial_infected_by_role"] == {"passenger": 2, "crew": 1}
    assert ev["initial_disease_states"] == {"exposed": 2, "infectious": 1}
    assert ev["daily_onset_curves"]["variants"]["excluding_declared_seeds"] == [0, 2, 5]
    assert ev["first_role"]["category"] == "passenger_first"
    assert ev["environment_summary"] is None
    assert exp["provenance"]["environment_summary"]["reason"] == "not_recorded_in_cohort"
    assert ev["image_digest"] is None
    assert exp["provenance"]["image_digest"]["availability"] == "not_recorded_in_run_archive"

    # Joint-eval checks (verifies joint_eval.json.gz sidecar was decoded)
    je = by_cohort["paper1_joint_eval"]
    jv = je["values"]
    assert je["sidecar_member"] == "joint_eval.json.gz"
    assert jv["tier"] == "fl_je_meg_12d_quiet"
    assert jv["arm"] == "bridge"
    assert jv["platform"] == "mega_cruise_5000"
    assert jv["engine_git_sha"] == "90aa3ec2"
    assert jv["design_stratum"] == "diagnostic"
    assert jv["first_role"]["category"] == "crew_first"
    assert jv["initial_infected_by_role"]["scope"] == "preboarding_declared_only"
    assert jv["initial_disease_states"] is None
    assert jv["cumulative_reporting_curves"]["cumulative_reported_passenger"] == [1, 4, 10]
    env = jv["environment_summary"]
    assert env["swab"]["total"] == 100
    assert env["swab"]["rows_kept"] == 2
    assert env["swab"]["detected_total"] == 2
    assert env["swab"]["censored_below_lod_total"] == 1
    assert env["swab"]["zones"] == ["buffet", "railing"]
    assert env["swab"]["recovered_summary"]["max"] == 50.0
    assert env["tank"]["assays_total"] == 2
    assert env["tank"]["quantifiable_total"] == 1
    assert env["tank"]["instruments"] == ["ddPCR"]
    assert env["tank"]["loq_values"] == [2000.0]

    # Solver reference checks (verifies growth_census.json.gz was NOT read)
    bf0 = by_cohort["supply_solver_reference"]
    bv = bf0["values"]
    assert bv["tier"] == "exp_station_lots_continuous"
    assert bv["platform"] == "expedition_cruise_450"
    assert bv["engine_git_sha"] == "bf0ec168"
    assert bv["design_stratum"] == "solver_reference_bf0"
    assert bv["initial_infected_total"] == 4
    assert bv["burden"]["acquired_total"] == 21
    assert bv["daily_onset_curves"] is None
    assert bv["cumulative_reporting_curves"]["cumulative_reported_total"] == [2, 11]
    assert bv["route_aggregates"]["granularity"] == "voyage_aggregate_only"
    assert bv["environment_summary"] is None
    assert bf0["provenance"]["sequencing_observations"]["availability"] == "not_harvested"
