#!/usr/bin/env python3
"""LEVERAGE-01 driver: one endpoint perturbation of one register row, one seed.

Each register row's declared interval gives one axis; the endpoints of that
interval are the only points run. A run is one (axis, endpoint, seed) cell of
the scored channel the row is reachable through: the norovirus channel is the
isolated ``classic_cruise_1900`` boarding cell the anchor scorer reads
(``score_anchors`` A1/A2/A5/A8/A9), and the covid channel is the hull-scenario
harness at the fitted Theta (``covid_theta_fit`` H1/H2/H3).

The design file ``picard_framework/runs/leverage01_design.json`` is the frozen
record: axes, endpoints, transforms, the seed pair, the noise gate, and the
override-blocked / not-rankable lists. Nothing here picks values — every point
is a declared interval endpoint.

Usage::

    python3 -m picard_framework.leverage_screen --list
    python3 -m picard_framework.leverage_screen --axis noro_dose_alpha \
        --endpoint 0.161 --seed 8105 --out out_dir/
    python3 -m picard_framework.leverage_screen --axis cov_theta \
        --endpoint 1e4 --hull greg_mortimer_2020 --seed 20200315 --out out_dir/
    python3 -m picard_framework.leverage_screen --classify out_dir/ \
        --out classification.json
    python3 -m picard_framework.leverage_screen --write-lev \
        --classification classification.json
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from picard_framework.covid_theta_fit import (
    PATHOGEN_ID as COVID_ID,
)
from picard_framework.covid_theta_fit import (
    build_fit_run_spec,
    load_covid_profile,
    observables_from_modality,
    run_fit_spec,
    theta_profile_overrides,
)
from picard_framework.run_spec import PicardRunSpec
from picard_framework.runs.mega_cruise_campaign.campaign_execution import (
    compute_derived_metrics,
    extract_timeseries,
)
from simulation_utils.paths import resolve_child_path, validated_open
from simulation_utils.platform_complement import declared_complement
from telemetry_buffer.observation_model.bounded_screen import (
    ScreenRunParams,
    build_run_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_REL = "picard_framework/runs/leverage01_design.json"
BASELINE_AXIS = "baseline"


def load_design(path: Path | None = None) -> dict[str, Any]:
    """The frozen LEVERAGE-01 design: axes, endpoints, gate, seed pair."""
    design_path = path or (REPO_ROOT / DESIGN_REL)
    with validated_open(
        design_path, allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as handle:
        return json.load(handle)


def axis_by_id(design: dict[str, Any], axis_id: str) -> dict[str, Any]:
    """One axis declaration, or the synthetic baseline axis."""
    if axis_id == BASELINE_AXIS:
        return {
            "axis_id": BASELINE_AXIS,
            "channel": "",
            "kind": "field",
            "scope": "pathogen",
            "path": "",
            "endpoints": [],
            "register_rows": [],
        }
    for axis in design["axes"]:
        if axis["axis_id"] == axis_id:
            return axis
    raise KeyError(
        f"unknown axis {axis_id!r}; declared: "
        f"{[a['axis_id'] for a in design['axes']]}",
    )


def _set_dotted(block: dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    cursor = block
    for key in keys[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[keys[-1]] = value


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_merge(dst[key], value)
        else:
            dst[key] = copy.deepcopy(value)
    return dst


# ── endpoint transforms ──────────────────────────────────────────────────
#
# A transform reads the shipped profile field and returns the patched value.
# None of them invent interior structure: each realizes the interval endpoint
# on the quantity the row declares.


def _peak_to(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    curve = [float(v) for v in profile[path]]
    shift = float(endpoint) - max(curve)
    return [round(v + shift, 6) for v in curve]


def _shift_peak(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    curve = [float(v) for v in profile[path]]
    delta = int(endpoint) - curve.index(max(curve))
    n = len(curve)
    return [curve[min(max(i - delta, 0), n - 1)] for i in range(n)]


def _decline_slope(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    curve = [float(v) for v in profile[path]]
    peak_idx = curve.index(max(curve))
    peak = curve[peak_idx]
    return [
        max(peak - float(endpoint) * (i - peak_idx), 0.0) if i > peak_idx else v
        for i, v in enumerate(curve)
    ]


def _asym_offset(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    symptomatic = [float(v) for v in profile["shedding_curve_log10"]]
    asymptomatic = [float(v) for v in profile[path]]
    target_peak = max(symptomatic) - float(endpoint)
    shift = target_peak - max(asymptomatic)
    return [round(v + shift, 6) for v in asymptomatic]


def _survival_point(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    days = int(endpoint)
    table = [
        {"day": d, "probability": 1.0} for d in range(days)
    ]
    table.append({"day": days, "probability": 0.0})
    field = dict(profile[path])
    field["survival"] = table
    return field


def _median_field(profile: dict[str, Any], path: str, endpoint: float) -> Any:
    field = dict(profile[path])
    endpoint_f = float(endpoint)
    field["median"] = endpoint_f
    field["min"] = min(float(field.get("min", endpoint_f)), endpoint_f)
    field["max"] = max(float(field.get("max", endpoint_f)), endpoint_f)
    return field


def _range_point(_profile: dict[str, Any], _path: str, endpoint: float) -> Any:
    return [float(endpoint), float(endpoint)]


def _incubation_median(
    profile: dict[str, Any], path: str, endpoint: float,
) -> dict[str, Any]:
    """Median at the endpoint with the window bound relaxed one ULP.

    The register's interval for the incubation row is the shipped field's
    own truncation window; the engine requires the median strictly inside
    (min, max). Realizing the endpoint exactly means relaxing only the
    bound on the endpoint's side, by the smallest relative step.
    """
    parent, _, leaf = path.rpartition(".")
    spec = dict(_get_dotted(profile, parent))
    e = float(endpoint)
    spec[leaf] = e
    spec["min_days"] = min(float(spec.get("min_days", e)), e * (1 - 1e-9))
    spec["max_days"] = max(float(spec.get("max_days", e)), e * (1 + 1e-9))
    return spec


def _renewal_prevalence(
    profile: dict[str, Any], _path: str, endpoint: float,
) -> dict[str, float]:
    """Incidence realizing the endpoint as the renewal-derived prevalence."""
    boarding = profile["boarding"]
    split = boarding["state_split"]
    detectable = float(boarding["renewal"]["detectable_duration_days"])
    presenting = 1.0 - float(split["never_symptomatic_fraction"])
    incidence = (
        float(endpoint) * presenting * 1000.0 * 365.25 / detectable
    )
    return {"passenger": incidence, "crew": incidence}


TRANSFORMS = {
    "field": None,
    "field_multi": None,
    "range_point": _range_point,
    "peak_to": _peak_to,
    "shift_peak": _shift_peak,
    "decline_slope": _decline_slope,
    "asym_offset": _asym_offset,
    "survival_point": _survival_point,
    "median_field": _median_field,
    "renewal_prevalence": _renewal_prevalence,
}


def axis_patch(
    axis: dict[str, Any],
    endpoint: float,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """The pathogen-profile patch one endpoint of one axis writes."""
    kind = axis["kind"]
    if kind == "theta":
        return {}
    if kind == "obs_vectors":
        return _observation_vectors_patch(profile, endpoint)
    if kind == "field":
        patch: dict[str, Any] = {}
        _set_dotted(patch, axis["path"], endpoint)
        return patch
    if kind == "field_multi":
        patch = {}
        for path in axis["path"].split(","):
            _set_dotted(patch, path.strip(), endpoint)
        return patch
    if kind == "renewal_prevalence":
        return {
            "boarding": {
                "renewal": {
                    "case_incidence_per_1000_py": _renewal_prevalence(
                        profile, axis["path"], endpoint,
                    ),
                },
            },
        }
    if kind == "incubation_median":
        parent, _, _leaf = axis["path"].rpartition(".")
        return {parent: _incubation_median(profile, axis["path"], endpoint)}
    transform = TRANSFORMS[kind]
    return {axis["path"]: transform(profile, axis["path"], endpoint)}


def _observation_vectors_patch(
    profile: dict[str, Any], endpoint: float,
) -> dict[str, Any]:
    """All ascertainment rungs to the endpoint, as one whole-vector move."""
    model = profile.get("observation_model") or {}
    patch: dict[str, Any] = {}
    for key in (
        "syndrome_case_eligibility_by_severity",
        "reporting_probability_by_severity_pre_recognition",
        "reporting_probability_by_severity_post_recognition",
    ):
        vector = model.get(key)
        if isinstance(vector, list):
            _set_dotted(patch, f"observation_model.{key}", [endpoint] * len(vector))
    return patch


def _get_dotted(block: dict[str, Any], path: str) -> Any:
    cursor: Any = block
    for key in path.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def readback(axis: dict[str, Any], picard_spec: PicardRunSpec, pid: str) -> Any:
    """The resolved value the engine will use -- the override witness."""
    if axis["kind"] == "theta" or axis["axis_id"] == BASELINE_AXIS:
        return None
    if axis["scope"] == "config":
        return _get_dotted(picard_spec.legacy_cfg, axis["path"])
    profile = picard_spec.pathogen_profiles.get(pid) or {}
    if axis["kind"] in (
        "field", "range_point", "median_field", "survival_point",
        "incubation_median",
    ):
        return _get_dotted(profile, axis["path"])
    if axis["kind"] == "field_multi":
        return {
            path.strip(): _get_dotted(profile, path.strip())
            for path in axis["path"].split(",")
        }
    if axis["kind"] == "renewal_prevalence":
        return _get_dotted(
            profile, "boarding.renewal.case_incidence_per_1000_py",
        )
    return _get_dotted(profile, axis["path"])


# ── norovirus channel ────────────────────────────────────────────────────


def build_noro_spec(
    design: dict[str, Any],
    axis: dict[str, Any],
    endpoint: float | None,
    seed: int,
) -> dict[str, Any]:
    """The isolated classic_cruise_1900 boarding cell, one endpoint moved."""
    channel = design["channels"]["noro"]
    params = ScreenRunParams(
        seed=int(seed),
        pathogen_id=channel["pathogen_id"],
        bundle=channel["bundle"],
        platform=channel["platform"],
        epochs=channel["epochs"],
        num_agents=channel["num_agents"],
        description="leverage01",
    )
    spec = build_run_spec([], [], params)
    if endpoint is None:
        return spec
    patch = axis_patch(axis, float(endpoint), _noro_profile())
    if axis["scope"] == "config":
        _deep_merge(spec["config_overrides"], patch)
    else:
        overrides = spec.setdefault("pathogen_overrides", {})
        pid_block = overrides.setdefault(channel["pathogen_id"], {})
        _deep_merge(pid_block, patch)
    return spec


_NORO_PROFILE: dict[str, Any] | None = None


def _noro_profile() -> dict[str, Any]:
    """The shipped norwalk_gi profile (the transform's reference field)."""
    global _NORO_PROFILE
    if _NORO_PROFILE is None:
        from picard_framework.pathogen_overrides import load_pathogen_bundle
        from simulation_utils import asset_defaults
        bundle_path = REPO_ROOT / asset_defaults.pathogen_bundle_rel(
            "active_profiles",
        )
        _NORO_PROFILE = load_pathogen_bundle(str(bundle_path))["norwalk_gi"]
    return _NORO_PROFILE


def run_noro_point(
    design: dict[str, Any],
    axis_id: str,
    endpoint: float | None,
    seed: int,
) -> dict[str, Any]:
    """One scored run of the norovirus channel, with the scorer row payload."""
    axis = axis_by_id(design, axis_id)
    channel = design["channels"]["noro"]
    spec = build_noro_spec(design, axis, endpoint, seed)
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        Path(spec_path).write_text(json.dumps(spec), encoding="utf-8")
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
        witness = readback(axis, picard_spec, channel["pathogen_id"])
        resolved_profile = picard_spec.pathogen_profiles[channel["pathogen_id"]]
        dose_adjustment = float(resolved_profile.get("dose_adjustment") or 0.0)
        from picard_framework.simulation.ship_simulation import ShipSimulation
        result = ShipSimulation(picard_spec, display=False).run()
    ts = extract_timeseries(result.history)
    num_agents = channel["num_agents"]
    derived = compute_derived_metrics(ts, num_agents)
    if "passenger_complement" not in derived:
        pax, crew = declared_complement(channel["platform"])
        derived["passenger_complement"] = pax
        derived["crew_complement"] = crew
    run_id = f"leverage01_{axis_id}_{endpoint}_{seed}"
    return {
        "run_id": run_id,
        "axis_id": axis_id,
        "endpoint": endpoint,
        "seed": seed,
        "channel": "noro",
        "resolved_witness": witness,
        "parameters": {
            "run_id": run_id,
            "platform_id": channel["platform"],
            "seed": int(seed),
            "num_epochs": channel["epochs"],
            "num_agents": num_agents,
            "natural_history_clock": "hours",
            "surveillance": "syndromic",
            "sick_call_probability_per_day": 0.70,
            "dose_adjustment": dose_adjustment,
        },
        "derived": derived,
        "summary": {},
    }


# ── covid channel ─────────────────────────────────────────────────────────


def run_covid_point(
    design: dict[str, Any],
    axis_id: str,
    endpoint: float | None,
    hull: str,
    seed: int,
) -> dict[str, Any]:
    """One hull run at one endpoint: profile patched, then Theta applied."""
    axis = axis_by_id(design, axis_id)
    channel = design["channels"]["covid"]
    theta = channel["theta"]
    profile = load_covid_profile(str(REPO_ROOT))
    if axis["kind"] == "theta" and endpoint is not None:
        theta = float(endpoint)
    elif endpoint is not None:
        profile = _deep_merge(profile, axis_patch(axis, float(endpoint), profile))
    raw = build_fit_run_spec(
        hull,
        theta,
        int(seed),
        repo_root=str(REPO_ROOT),
        cabin_air_mode=channel["cabin_air_mode"],
        pathogen_pool_transport=channel["pathogen_pool_transport"],
    )
    raw["pathogen_overrides"][COVID_ID] = theta_profile_overrides(
        profile, theta,
    )
    sim = run_fit_spec(raw, repo_root=str(REPO_ROOT))
    observables = observables_from_modality(
        sim.modalities["syndromic"],
        scenario_id=hull,
        theta=theta,
        seed=int(seed),
        split_day=channel["split_day"],
        turn_day=channel["turn_day"],
    )
    return {
        "run_id": f"leverage01_{axis_id}_{endpoint}_{hull}_{seed}",
        "axis_id": axis_id,
        "endpoint": endpoint,
        "seed": int(seed),
        "hull": hull,
        "theta": theta,
        "channel": "covid",
        "observables": observables.as_dict(),
    }


# ── cell enumeration ─────────────────────────────────────────────────────


def enumerate_runs(design: dict[str, Any]) -> list[dict[str, Any]]:
    """Every (axis, endpoint, seed[, hull]) point the design declares."""
    runs: list[dict[str, Any]] = []
    noro_seeds = design["channels"]["noro"]["seeds"]
    hulls = design["channels"]["covid"]["hulls"]
    cells = [{"axis_id": BASELINE_AXIS, "endpoints": [None], "channel": "noro"}]
    cells += [{"axis_id": BASELINE_AXIS, "endpoints": [None], "channel": "covid"}]
    cells += design["axes"]
    for cell in cells:
        for endpoint in cell["endpoints"]:
            if cell["channel"] == "noro":
                for seed in noro_seeds:
                    runs.append({
                        "channel": "noro",
                        "axis_id": cell["axis_id"],
                        "endpoint": endpoint,
                        "seed": seed,
                    })
            elif cell["channel"] == "covid":
                for hull, hull_cfg in hulls.items():
                    for seed in hull_cfg["seeds"]:
                        runs.append({
                            "channel": "covid",
                            "axis_id": cell["axis_id"],
                            "endpoint": endpoint,
                            "hull": hull,
                            "seed": seed,
                        })
    return runs


def run_one(design: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    if ref["channel"] == "noro":
        return run_noro_point(
            design, ref["axis_id"], ref.get("endpoint"), ref["seed"],
        )
    return run_covid_point(
        design, ref["axis_id"], ref.get("endpoint"),
        ref["hull"], ref["seed"],
    )


# ── classification ───────────────────────────────────────────────────────
#
# The frozen rule (design noise_gate): paired deltas same-sign AND |mean
# delta| > baseline seed-pair spread -> measurable movement. A verdict
# (PASS/FAIL, hit/miss) changing baseline->endpoint is a flip -> L2.


def _paired_gate(
    baseline: list[float | None],
    endpoint: list[float | None],
) -> bool:
    """Whether the paired movement clears the seed-pair noise gate."""
    deltas = [
        e - b
        for b, e in zip(baseline, endpoint)
        if b is not None and e is not None
    ]
    if len(deltas) < 2:
        return False
    if not (all(d > 0.0 for d in deltas) or all(d < 0.0 for d in deltas)):
        return False
    defined = [b for b in baseline if b is not None]
    spread = abs(defined[0] - defined[-1]) if len(defined) >= 2 else 0.0
    mean_delta = sum(deltas) / len(deltas)
    return abs(mean_delta) > spread


def _classify_noro_cell(
    baseline_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Anchor-cell comparison on the norovirus channel."""
    from telemetry_buffer.observation_model.score_anchors import (
        summarise_cell,
        verdicts,
    )
    from telemetry_buffer.observation_model.vsp_class_era_scoring import (
        vsp_attack_rate_targets,
    )
    baseline_cell = summarise_cell(baseline_rows)
    endpoint_cell = summarise_cell(endpoint_rows)
    targets = vsp_attack_rate_targets("pre")
    hull = baseline_rows[0]["hull"]
    baseline_verdicts, _ = verdicts(hull, baseline_cell, targets, "pre")
    endpoint_verdicts, _ = verdicts(hull, endpoint_cell, targets, "pre")
    flips = [
        name for name in baseline_verdicts
        if baseline_verdicts.get(name) in ("PASS", "FAIL")
        and endpoint_verdicts.get(name) in ("PASS", "FAIL")
        and baseline_verdicts[name] != endpoint_verdicts[name]
    ]
    moved = _moved_quantities(baseline_rows, endpoint_rows)
    return {
        "baseline_verdicts": baseline_verdicts,
        "endpoint_verdicts": endpoint_verdicts,
        "verdict_flips": flips,
        "moved_quantities": moved,
        "baseline_cell": baseline_cell,
        "endpoint_cell": endpoint_cell,
    }


def _per_seed(
    rows: list[dict[str, Any]], key: str,
) -> dict[int, float | None]:
    return {int(r["seed"]): r.get(key) for r in rows}


def _moved_quantities(
    baseline_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
) -> list[str]:
    """Scored quantities whose paired deltas clear the noise gate."""
    quantities = (
        "A1_ever_ill_passenger",
        "infection_attack_rate_passenger",
        "reported_case_attack_rate_passenger",
        "reported_case_attack_rate_crew",
        "A5_passenger_crew_ratio",
    )
    moved: list[str] = []
    for key in quantities:
        base = _per_seed(baseline_rows, key)
        endp = _per_seed(endpoint_rows, key)
        seeds = sorted(set(base) & set(endp))
        if _paired_gate([base[s] for s in seeds], [endp[s] for s in seeds]):
            moved.append(key)
    posted_base = [
        1.0 if r.get("vsp_trigger_epoch") is not None else 0.0
        for r in sorted(baseline_rows, key=lambda r: r["seed"])
    ]
    posted_end = [
        1.0 if r.get("vsp_trigger_epoch") is not None else 0.0
        for r in sorted(endpoint_rows, key=lambda r: r["seed"])
    ]
    if _paired_gate(posted_base, posted_end):
        moved.append("vsp_posted")
    return moved


def _classify_covid_cell(
    design: dict[str, Any],
    baseline_runs: list[dict[str, Any]],
    endpoint_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """H1/H2 per-seed hit/miss plus H3 placement, on the hull channel."""
    from picard_framework.covid_fit_targets import load_fit_targets
    targets = load_fit_targets()
    h1 = float(targets.by_id("covid.H1").values["share"])
    h2 = float(targets.by_id("covid.H2").values["share"])
    h3_quartile = float(targets.by_id("covid.H3").values["iqr_attack_rate"][1])
    hulls = sorted(design["channels"]["covid"]["hulls"])

    def score(runs: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        gm = [
            r for r in runs if r["hull"] == hulls[-1]
        ]
        dp = [
            r for r in runs if r["hull"] == hulls[0]
        ]
        out["h1_verdicts"] = [
            abs(r["observables"]["positive_share"] - h1) <= 0.1
            if r["observables"]["positive_share"] is not None else None
            for r in gm
        ]
        out["h2_verdicts"] = [
            abs(r["observables"]["asymptomatic_share"] - h2) <= 0.1
            if r["observables"]["asymptomatic_share"] is not None else None
            for r in gm
        ]
        out["h3_verdicts"] = [
            min(
                g["observables"]["positive_share"] or 0.0,
                d["observables"]["positive_share"] or 0.0,
            ) > h3_quartile
            for g, d in zip(gm, dp)
        ]
        out["positive_share"] = {
            hulls[-1]: [x["observables"]["positive_share"] for x in gm],
            hulls[0]: [x["observables"]["positive_share"] for x in dp],
        }
        return out

    baseline = score(baseline_runs)
    endpoint = score(endpoint_runs)
    flips: list[str] = []
    for anchor in ("h1_verdicts", "h2_verdicts", "h3_verdicts"):
        b, e = baseline[anchor], endpoint[anchor]
        if b == e:
            continue
        if all(v is True for v in b) and all(v is False for v in e):
            flips.append(anchor)
        elif all(v is False for v in b) and all(v is True for v in e):
            flips.append(anchor)
    moved: list[str] = []
    for hull in hulls:
        b = baseline["positive_share"].get(hull, [])
        e = endpoint["positive_share"].get(hull, [])
        if _paired_gate(b, e):
            moved.append(f"positive_share:{hull}")
    gm_base = [
        r["observables"]["asymptomatic_share"]
        for r in sorted(
            (r for r in baseline_runs if r["hull"] == hulls[-1]),
            key=lambda r: r["seed"],
        )
    ]
    gm_end = [
        r["observables"]["asymptomatic_share"]
        for r in sorted(
            (r for r in endpoint_runs if r["hull"] == hulls[-1]),
            key=lambda r: r["seed"],
        )
    ]
    if _paired_gate(gm_base, gm_end):
        moved.append(f"asymptomatic_share:{hulls[-1]}")
    return {
        "baseline_verdicts": baseline,
        "endpoint_verdicts": endpoint,
        "verdict_flips": flips,
        "moved_quantities": moved,
    }


def classify(
    design: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-axis L0/L1/L2 from the collected run records."""
    from telemetry_buffer.observation_model.score_anchors import row_from_summary
    noro_records = [
        row_from_summary(r, r["run_id"])
        for r in records if r["channel"] == "noro"
    ]
    noro_raw = [r for r in records if r["channel"] == "noro"]
    axes_out: list[dict[str, Any]] = []
    for axis in design["axes"]:
        channel = axis["channel"]
        per_endpoint: list[dict[str, Any]] = []
        for endpoint in axis["endpoints"]:
            if channel == "noro":
                rows_b = [
                    r for r, raw in zip(noro_records, noro_raw)
                    if raw["axis_id"] == BASELINE_AXIS
                ]
                rows_e = [
                    r for r, raw in zip(noro_records, noro_raw)
                    if raw["axis_id"] == axis["axis_id"]
                    and raw["endpoint"] == endpoint
                ]
                if not rows_b or not rows_e:
                    per_endpoint.append({
                        "endpoint": endpoint,
                        "status": "missing",
                        "verdict_flips": [],
                        "moved_quantities": [],
                    })
                    continue
                per_endpoint.append({
                    "endpoint": endpoint,
                    **_classify_noro_cell(rows_b, rows_e),
                })
            else:
                runs_e = [
                    r for r in records
                    if r["channel"] == "covid"
                    and r["axis_id"] == axis["axis_id"]
                    and r["endpoint"] == endpoint
                ]
                runs_b = [
                    r for r in records
                    if r["channel"] == "covid" and r["axis_id"] == BASELINE_AXIS
                ]
                if not runs_b or not runs_e:
                    per_endpoint.append({
                        "endpoint": endpoint,
                        "status": "missing",
                        "verdict_flips": [],
                        "moved_quantities": [],
                    })
                    continue
                per_endpoint.append({
                    "endpoint": endpoint,
                    **_classify_covid_cell(design, runs_b, runs_e),
                })
        lev = "L0"
        if any(e.get("status") == "missing" for e in per_endpoint):
            lev = "incomplete"
        elif any(e["verdict_flips"] for e in per_endpoint):
            lev = "L2"
        elif any(e["moved_quantities"] for e in per_endpoint):
            lev = "L1"
        axes_out.append({
            "axis_id": axis["axis_id"],
            "register_rows": axis["register_rows"],
            "lev": lev,
            "endpoints": per_endpoint,
        })
    return {"axes": axes_out, "design": "leverage01"}


_LEV_RANK = {"L0": 0, "L1": 1, "L2": 2}
_REGISTER = REPO_ROOT / "docs" / "parameter_provenance_register.md"


def row_levs(report: dict[str, Any]) -> dict[int, str]:
    """Per register row the max level over the axes covering it."""
    levs: dict[int, str] = {}
    for axis in report["axes"]:
        lev = axis["lev"]
        for row in axis["register_rows"]:
            if lev == "incomplete":
                continue
            if row not in levs or _LEV_RANK[lev] > _LEV_RANK[levs[row]]:
                levs[row] = lev
    return levs


def write_lev(report: dict[str, Any], register: Path | None = None) -> dict[int, str]:
    """Rewrite the ``Lev`` cell of each classified register row in place.

    Only cell 8 of the 12-column row is touched; blocked and not-rankable
    rows keep ``L?``.
    """
    register = register or _REGISTER
    levs = row_levs(report)
    lines = register.read_text(encoding="utf-8").splitlines(keepends=True)
    for row, lev in levs.items():
        cells = re.split(r"(?<!\\)\|", lines[row - 1])
        if cells[8].strip() not in ("L?", "—"):
            raise SystemExit(
                f"register row {row} Lev cell already set: {cells[8].strip()}",
            )
        cells[8] = f" {lev} "
        lines[row - 1] = "|".join(cells)
    register.write_text("".join(lines), encoding="utf-8")
    return levs


def collect_records(run_dir: Path) -> list[dict[str, Any]]:
    """Every per-run record under a results directory."""
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*.json")):
        with validated_open(path, allowed_roots=(run_dir,), encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict) and "channel" in payload:
            records.append(payload)
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", dest="list_cells",
                        help="print the run count and exit")
    parser.add_argument("--axis", default=None)
    parser.add_argument("--endpoint", type=float, default=None)
    parser.add_argument("--hull", default=None)
    parser.add_argument("--channel", choices=("noro", "covid"), default=None,
                        help="which channel a baseline run executes on")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--classify", type=Path, default=None,
                        help="results directory to classify")
    parser.add_argument("--write-lev", action="store_true",
                        help="write classified Levs into the register")
    parser.add_argument("--classification", type=Path, default=None,
                        help="classification JSON for --write-lev")
    parser.add_argument("--design", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def _write_record(out: Path, record: dict[str, Any]) -> Path:
    name = f"{record['run_id']}.json"
    out.mkdir(parents=True, exist_ok=True)
    path = Path(resolve_child_path(str(out), name))
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    design = load_design(args.design)
    if args.list_cells:
        runs = enumerate_runs(design)
        noro = sum(1 for r in runs if r["channel"] == "noro")
        covid = sum(1 for r in runs if r["channel"] == "covid")
        print(f"{len(runs)} runs ({noro} noro + {covid} covid)")
        return 0
    if args.classify is not None:
        records = collect_records(args.classify)
        report = classify(design, records)
        out = args.out or args.classify / "leverage01_classification.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        counts = {}
        for axis in report["axes"]:
            counts[axis["lev"]] = counts.get(axis["lev"], 0) + 1
        print(f"classified {len(report['axes'])} axes: {counts}")
        return 0
    if args.write_lev:
        if not args.classification:
            raise SystemExit("--classification is required for --write-lev")
        report = json.loads(args.classification.read_text(encoding="utf-8"))
        levs = write_lev(report)
        counts: dict[str, int] = {}
        for lev in levs.values():
            counts[lev] = counts.get(lev, 0) + 1
        print(f"wrote {len(levs)} rows: {counts}")
        return 0
    if not (args.axis and args.seed is not None and args.out):
        raise SystemExit("--axis, --seed and --out are required for a run")
    axis = axis_by_id(design, args.axis)
    endpoint = args.endpoint
    if axis["axis_id"] != BASELINE_AXIS and endpoint is None:
        raise SystemExit("--endpoint is required for a non-baseline axis")
    channel = args.channel or axis["channel"] or "noro"
    ref = {
        "channel": channel,
        "axis_id": axis["axis_id"],
        "endpoint": endpoint,
        "seed": args.seed,
        "hull": args.hull,
    }
    if channel == "covid" and not args.hull:
        raise SystemExit("--hull is required for a covid-channel run")
    record = run_one(design, ref)
    path = _write_record(args.out, record)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
