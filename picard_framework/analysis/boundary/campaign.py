"""High-volume scenario matrix expansion and resume-friendly runner."""

from __future__ import annotations

import json
import os
from importlib import resources
from itertools import product
from typing import Any, Iterable

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    read_json,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.boundary.costs import cost_params_from_mapping
from picard_framework.analysis.boundary.decision_model import run_monte_carlo
from picard_framework.analysis.boundary.posterior_lookup import OutbreakSurface
from simulation_utils.paths import validated_open


def _load_package_json(*parts: str) -> dict[str, Any]:
    """Read JSON bundled under this package (not a CLI path)."""
    root = resources.files("picard_framework.analysis.boundary")
    node = root
    for part in parts:
        node = node / part
    return json.loads(node.read_text(encoding="utf-8"))


def load_platform_defaults() -> dict[str, Any]:
    return _load_package_json("data", "platform_defaults.json")


def load_scenario_matrix(path: str | None, *, smoke: bool = False) -> dict[str, Any]:
    if path is None:
        name = "smoke_scenario_matrix.json" if smoke else "scenario_matrix.json"
        return _load_package_json("data", name)
    return read_json(safe_path(path))


def _policy_adoption(
    policy: str,
    defaults: dict[str, Any],
    overrides: dict[str, Any],
) -> tuple[float, float]:
    adoption = defaults.get("adoption", {})
    a_pax = float(overrides.get("adoption_pax", adoption.get("byod", 0.43)))
    a_crew = float(overrides.get("adoption_crew", adoption.get("crew_mandatory", 1.0)))
    if policy == "P4":
        a_pax = float(adoption.get("incentivized", 0.70))
    if policy == "P5":
        a_crew = float(adoption.get("crew_mandatory", 1.0))
    return a_pax, a_crew


def expand_scenarios(matrix: dict[str, Any], defaults_doc: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Cartesian product of matrix axes into concrete scenario dicts."""
    defaults_doc = defaults_doc or load_platform_defaults()
    base = dict(matrix.get("defaults") or {})
    axes = matrix.get("axes") or {}
    platform_axis = list(axes.get("platform_class") or ["mega"])
    pi_axis = list(axes.get("pi_inf") or [0.002])
    policy_axis = list(axes.get("policy") or ["P0"])
    cost_axis = list(axes.get("cost_scenario") or [base.get("cost_scenario", "mid")])

    platforms = defaults_doc.get("platforms", {})
    wearable = defaults_doc.get("wearable_defaults", {})
    confirm = defaults_doc.get("confirm_defaults", {})
    cost_scenarios = defaults_doc.get("cost_scenarios", {})

    scenarios: list[dict[str, Any]] = []
    for platform_class, pi_inf, policy, cost_name in product(
        platform_axis, pi_axis, policy_axis, cost_axis
    ):
        plat = platforms.get(platform_class, {})
        pathogen = str(base.get("pathogen", "norovirus"))
        wdef = wearable.get(pathogen) or wearable.get("default") or {
            "Se_w": 0.65,
            "Sp_w": 0.85,
        }
        merged = dict(base)
        merged.update(
            {
                "platform_class": platform_class,
                "platform_id": plat.get("platform_id"),
                "pi_inf": float(pi_inf),
                "policy": policy,
                "cost_scenario": cost_name,
            }
        )
        if "N_pax" not in merged:
            merged["N_pax"] = int(plat.get("N_pax", 500))
        if "N_crew" not in merged:
            merged["N_crew"] = int(plat.get("N_crew", 0))
        if "voyage_length_days" not in merged and plat.get("voyage_length_days"):
            merged["voyage_length_days"] = plat["voyage_length_days"]

        merged.setdefault("Se_w", wdef.get("Se_w", 0.65))
        merged.setdefault("Sp_w", wdef.get("Sp_w", 0.85))
        merged.setdefault("Se_confirm", confirm.get("Se_confirm", 0.90))
        merged.setdefault("Sp_confirm", confirm.get("Sp_confirm", 0.98))

        a_pax, a_crew = _policy_adoption(policy, defaults_doc, merged)
        merged["adoption_pax"] = a_pax
        merged["adoption_crew"] = a_crew

        cost_map = cost_scenarios.get(cost_name) or cost_scenarios.get("mid") or {}
        if "costs" not in merged:
            merged["costs"] = cost_params_from_mapping(cost_map).to_dict()

        pi_tag = f"{float(pi_inf):.4f}".replace(".", "p")
        merged["scenario_id"] = (
            f"{platform_class}_{pathogen}_{policy}_pi{pi_tag}_{cost_name}"
        )
        scenarios.append(merged)
    return scenarios


def _completed_path(out_dir: str) -> str:
    return os.path.join(out_dir, "completed_runs.txt")


def _read_completed(out_dir: str) -> set[str]:
    path = _completed_path(out_dir)
    if not os.path.isfile(path):
        return set()
    with validated_open(path, allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def _append_completed(out_dir: str, scenario_id: str) -> None:
    path = _completed_path(out_dir)
    with validated_open(path, "a", allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        fh.write(scenario_id + "\n")


def _baseline_key(scenario: dict[str, Any]) -> tuple[Any, ...]:
    return (
        scenario.get("platform_class"),
        scenario.get("pathogen"),
        float(scenario["pi_inf"]),
        scenario.get("cost_scenario"),
        scenario.get("baseline_response", "vsp"),
    )


SUMMARY_FIELDS = [
    "scenario_id",
    "policy",
    "platform_class",
    "pathogen",
    "pi_inf",
    "n_mc",
    "seed",
    "expected_intercepted",
    "expected_K_intro",
    "expected_K_board",
    "expected_P_trigger",
    "expected_P_accel",
    "expected_attack_rate",
    "expected_total_cost",
    "expected_screening_cost",
    "expected_false_positive_cost",
    "expected_true_positive_cost",
    "expected_onboard_cost",
    "expected_reputational_cost",
    "false_positives_per_true_positive",
    "false_positives_per_vsp_avoided",
    "cost_per_vsp_avoided",
    "value_of_information_per_pax",
]


def run_campaign(
    scenarios: Iterable[dict[str, Any]],
    surface: OutbreakSurface,
    *,
    out_dir: str,
    n_mc: int,
    seed: int,
    resume: bool = False,
) -> list[dict[str, Any]]:
    """Run all scenarios; write per-scenario summary.json and policy_comparison.csv."""
    out = ensure_out_dir(out_dir)
    runs_dir = ensure_out_dir(os.path.join(out, "runs"))
    completed = _read_completed(out) if resume else set()
    if not resume and os.path.isfile(_completed_path(out)):
        # Fresh run: truncate completed list
        with validated_open(
            _completed_path(out), "w", allowed_roots=allowed_roots(), encoding="utf-8"
        ) as fh:
            fh.write("")

    scenario_list = list(scenarios)
    # Precompute P0 baselines within the batch for VoI / VSP-avoided metrics.
    baselines: dict[tuple[Any, ...], dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []

    # First pass: load resumed summaries
    for sc in scenario_list:
        sid = sc["scenario_id"]
        summary_path = os.path.join(runs_dir, f"{sid}.json")
        if resume and sid in completed and os.path.isfile(summary_path):
            summaries.append(read_json(summary_path))

    for sc in scenario_list:
        if sc["policy"] != "P0":
            continue
        key = _baseline_key(sc)
        existing = next(
            (s for s in summaries if s.get("scenario_id") == sc["scenario_id"]), None
        )
        if existing is not None:
            baselines[key] = existing
            continue
        summary = run_monte_carlo(sc, surface, n_mc=n_mc, seed=seed)
        write_json(os.path.join(runs_dir, f"{sc['scenario_id']}.json"), summary)
        _append_completed(out, sc["scenario_id"])
        completed.add(sc["scenario_id"])
        summaries.append(summary)
        baselines[key] = summary

    for sc in scenario_list:
        if sc["policy"] == "P0":
            continue
        sid = sc["scenario_id"]
        existing = next((s for s in summaries if s.get("scenario_id") == sid), None)
        if existing is not None:
            continue
        baseline = baselines.get(_baseline_key(sc))
        summary = run_monte_carlo(
            sc, surface, n_mc=n_mc, seed=seed, baseline_summary=baseline
        )
        write_json(os.path.join(runs_dir, f"{sid}.json"), summary)
        _append_completed(out, sid)
        completed.add(sid)
        summaries.append(summary)

    # Stable CSV order: follow scenario_list order when possible
    by_id = {s["scenario_id"]: s for s in summaries}
    ordered = [by_id[s["scenario_id"]] for s in scenario_list if s["scenario_id"] in by_id]
    # Flatten None for CSV
    csv_rows = []
    for row in ordered:
        flat = {k: row.get(k) for k in SUMMARY_FIELDS}
        csv_rows.append(flat)
    write_csv(os.path.join(out, "policy_comparison.csv"), csv_rows, SUMMARY_FIELDS)
    write_json(
        os.path.join(out, "campaign_meta.json"),
        {
            "n_scenarios": len(scenario_list),
            "n_completed": len(ordered),
            "n_mc": n_mc,
            "seed": seed,
            "surface_source": surface.source,
        },
    )
    return ordered
