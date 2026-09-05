"""Derived scalar metrics and standardized row builders for campaign bundles."""

from __future__ import annotations

from collections import Counter
from typing import Any

from picard_framework.analysis.parse_run_id import extract_factors, resolve_initial_infected
from simulation_utils.epidemic_labels import epidemic_took_off, seed_established

TRIGGER_NONE = 0
TRIGGER_SUSPECTED = 1
TRIGGER_CONFIRMED = 2

RUN_SUMMARY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "campaign",
    "platform_id",
    "platform_class",
    "pathogen",
    "pathogen_id",
    "dose_adjustment",
    "density_exponent",
    "immunity_fraction",
    "surveillance_strategy",
    "transport_engine",
    "seed",
    "initial_infected",
    "num_agents",
    "num_epochs",
    "passenger_complement",
    "crew_complement",
    "attack_rate",
    "infection_attack_rate_passenger",
    "infection_attack_rate_crew",
    "ever_ill_attack_rate_crew",
    "reported_case_attack_rate_crew",
    "outbreak_occurred",
    "peak_prevalence",
    "peak_epoch",
    "detection_epoch",
    "confirmation_epoch",
    "detection_lag",
    "total_quarantine_person_epochs",
    "r_effective_at_peak",
    "final_susceptible_fraction",
    "cumulative_cost_usd",
    "cumulative_ois",
    # Optional
    "vsp_suspect_threshold",
    "vsp_confirm_threshold",
    "vsp_lockdown_threshold",
    "sick_call_probability",
    "detection_delay_epochs",
    "isolation_compliance",
    "wearable_profile",
    "wastewater_enabled",
    "cascade_enabled",
    "multiplex_enabled",
    "contam_paired_run_id",
    "native_paired_run_id",
)

EPOCH_COLUMNS: tuple[str, ...] = (
    "run_id",
    "epoch",
    "susceptible",
    "infected",
    "symptomatic",
    "recovered",
    "immune",
    "quarantined",
    "isolated",
    "new_infections",
    "total_pathogen_mass",
    "n_zones_contaminated",
    "max_concentration",
    "max_conc_zone",
    "trigger_status",
    "trigger_state",
    "cumulative_cost_usd",
    "cumulative_ois",
    "cumulative_ever_infected",
    "cumulative_ever_infected_passenger",
    "cumulative_ever_infected_crew",
    "infection_attack_rate_passenger",
    "infection_attack_rate_crew",
    "ever_ill_rate_crew",
    "reported_case_rate_crew",
)

# Factor columns repeated on epoch rows for join-free Stan prep.
EPOCH_FACTOR_COLUMNS: tuple[str, ...] = (
    "platform_id",
    "platform_class",
    "pathogen",
    "pathogen_id",
    "dose_adjustment",
    "density_exponent",
    "immunity_fraction",
    "surveillance_strategy",
    "transport_engine",
    "seed",
    "num_agents",
    "vsp_suspect_threshold",
    "vsp_confirm_threshold",
    "vsp_lockdown_threshold",
)


def encode_trigger_status(status: Any) -> int:
    """Map trigger_status strings to Stan integers."""
    if status is None:
        return TRIGGER_NONE
    token = str(status).strip().upper()
    if token in {"", "NONE", "0"}:
        return TRIGGER_NONE
    if token in {"SUSPECTED", "SUSPECT", "1"}:
        return TRIGGER_SUSPECTED
    if token in {"CONFIRMED", "CONFIRM", "LOCKDOWN", "2"}:
        return TRIGGER_CONFIRMED
    return TRIGGER_NONE


def compute_derived_metrics(
    timeseries: list[dict[str, Any]], num_agents: int
) -> dict[str, Any]:
    """Compute publication-ready scalar metrics from an epoch time series.

    Mirrors ``campaign_runner.compute_derived_metrics`` so bundle regeneration
    matches runner-embedded ``derived`` blocks when those are absent.
    """
    if not timeseries:
        return {}

    infected_by_epoch = [int(e.get("infected", 0) or 0) for e in timeseries]
    peak_infected = max(infected_by_epoch)
    peak_epoch = infected_by_epoch.index(peak_infected)

    final = timeseries[-1]
    passenger_complement = final.get("passenger_complement")
    crew_complement = final.get("crew_complement")
    complements_present = (
        passenger_complement is not None or crew_complement is not None
    )
    if complements_present and (
        isinstance(passenger_complement, bool)
        or not isinstance(passenger_complement, int)
        or passenger_complement <= 0
        or isinstance(crew_complement, bool)
        or not isinstance(crew_complement, int)
        or crew_complement <= 0
        or passenger_complement + crew_complement != num_agents
    ):
        raise ValueError(
            "timeseries role complements must be positive integers summing "
            f"to num_agents ({num_agents})",
        )
    recovered = int(final.get("recovered", 0) or 0)
    infected_final = int(final.get("infected", 0) or 0)
    ever_infected = infected_final + recovered
    attack_rate = ever_infected / num_agents if num_agents > 0 else 0.0
    # Takeoff vs fizzle: VSP onset while incidence still accelerating.
    outbreak_occurred = epidemic_took_off(timeseries)
    seeded = seed_established(ever_infected)

    detection_epoch = None
    confirmation_epoch = None
    for e in timeseries:
        status = str(e.get("trigger_status", "none"))
        if status in ("SUSPECTED", "CONFIRMED") and detection_epoch is None:
            detection_epoch = e.get("epoch")
        if status == "CONFIRMED" and confirmation_epoch is None:
            confirmation_epoch = e.get("epoch")

    total_quarantine_epochs = sum(int(e.get("quarantined", 0) or 0) for e in timeseries)

    r_eff_at_peak = None
    if peak_epoch > 0 and infected_by_epoch[peak_epoch - 1] > 0:
        new_at_peak = int(timeseries[peak_epoch].get("new_infections", 0) or 0)
        r_eff_at_peak = new_at_peak / infected_by_epoch[peak_epoch - 1]

    derived = {
        "attack_rate": round(attack_rate, 4),
        "infection_attack_rate_passenger": round(
            float(final.get("infection_attack_rate_passenger", 0.0) or 0.0),
            4,
        ),
        "infection_attack_rate_crew": round(
            float(final.get("infection_attack_rate_crew", 0.0) or 0.0),
            4,
        ),
        "ever_ill_attack_rate_crew": round(
            float(final.get("ever_ill_rate_crew", 0.0) or 0.0), 4,
        ),
        "reported_case_attack_rate_crew": round(
            float(final.get("reported_case_rate_crew", 0.0) or 0.0), 4,
        ),
        "peak_prevalence": peak_infected,
        "peak_epoch": peak_epoch,
        "outbreak_occurred": outbreak_occurred,
        "seed_established": seeded,
        "detection_epoch": detection_epoch,
        "confirmation_epoch": confirmation_epoch,
        "detection_lag": (
            peak_epoch - detection_epoch if detection_epoch is not None else None
        ),
        "total_quarantine_person_epochs": total_quarantine_epochs,
        "r_effective_at_peak": (
            round(r_eff_at_peak, 3) if r_eff_at_peak is not None else None
        ),
        "final_susceptible_fraction": round(
            int(final.get("susceptible", 0) or 0) / max(num_agents, 1),
            4,
        ),
    }
    if complements_present:
        derived["passenger_complement"] = passenger_complement
        derived["crew_complement"] = crew_complement
    return derived


def _cost_fields(summary: dict[str, Any], timeseries: list[dict[str, Any]]) -> tuple[Any, Any]:
    cost = summary.get("cost_accounting") or {}
    usd = cost.get("total_financial_usd")
    ois = cost.get("operational_impact_cumulative")
    if timeseries:
        last = timeseries[-1]
        if usd is None:
            usd = last.get("cumulative_cost_usd")
        if ois is None:
            ois = last.get("cumulative_ois")
    return usd, ois


def build_run_summary_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Build one ``run_summary.csv`` row from a loaded run zip payload."""
    summary = payload.get("summary") or {}
    timeseries = payload.get("timeseries") or []
    if not isinstance(timeseries, list):
        timeseries = []
    params = summary.get("parameters") or {}
    derived = dict(summary.get("derived") or {})

    factors = extract_factors(
        run_id=str(payload.get("run_id") or summary.get("run_id") or ""),
        parameters=params if isinstance(params, dict) else {},
        run_spec=payload.get("run_spec") if isinstance(payload.get("run_spec"), dict) else {},
        summary=summary if isinstance(summary, dict) else {},
    )
    num_agents = int(factors.get("num_agents") or 0)
    # Timeseries is authoritative so re-bundles pick up VSP+curvature takeoff
    # even when summary.json still carries a legacy outbreak label.
    if timeseries and num_agents > 0:
        derived = compute_derived_metrics(timeseries, num_agents)
    elif not derived:
        derived = {}

    usd, ois = _cost_fields(summary, timeseries)
    row = {c: factors.get(c) for c in RUN_SUMMARY_COLUMNS}
    row.update(
        {
            "attack_rate": derived.get("attack_rate"),
            "passenger_complement": derived.get("passenger_complement"),
            "crew_complement": derived.get("crew_complement"),
            "outbreak_occurred": derived.get("outbreak_occurred"),
            "peak_prevalence": derived.get("peak_prevalence"),
            "peak_epoch": derived.get("peak_epoch"),
            "detection_epoch": derived.get("detection_epoch"),
            "confirmation_epoch": derived.get("confirmation_epoch"),
            "detection_lag": derived.get("detection_lag"),
            "total_quarantine_person_epochs": derived.get(
                "total_quarantine_person_epochs"
            ),
            "r_effective_at_peak": derived.get("r_effective_at_peak"),
            "final_susceptible_fraction": derived.get("final_susceptible_fraction"),
            "cumulative_cost_usd": usd,
            "cumulative_ois": ois,
            "infection_attack_rate_passenger": derived.get(
                "infection_attack_rate_passenger",
            ),
            "infection_attack_rate_crew": derived.get(
                "infection_attack_rate_crew",
            ),
            "ever_ill_attack_rate_crew": derived.get(
                "ever_ill_attack_rate_crew",
            ),
            "reported_case_attack_rate_crew": derived.get(
                "reported_case_attack_rate_crew",
            ),
        }
    )
    row["run_id"] = factors["run_id"]
    # Fill introductions k from epoch-0 prevalence when not in parameters.
    if row.get("initial_infected") in (None, ""):
        row["initial_infected"] = resolve_initial_infected(
            parameters=params if isinstance(params, dict) else {},
            run_spec=payload.get("run_spec")
            if isinstance(payload.get("run_spec"), dict)
            else {},
            run_id=str(row.get("run_id") or ""),
            timeseries=timeseries,
            initiation=payload.get("initiation"),
        )
    return row


def build_epoch_rows(
    payload: dict[str, Any], run_summary: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Build ``epoch_timeseries`` rows for one run, joining run-level factors."""
    timeseries = payload.get("timeseries") or []
    if not isinstance(timeseries, list):
        return []
    summary_row = run_summary or build_run_summary_row(payload)
    run_id = summary_row.get("run_id") or payload.get("run_id")
    rows: list[dict[str, Any]] = []
    for point in timeseries:
        if not isinstance(point, dict):
            continue
        status = point.get("trigger_status", "none")
        row: dict[str, Any] = {
            "run_id": run_id,
            "epoch": point.get("epoch"),
            "susceptible": point.get("susceptible"),
            "infected": point.get("infected"),
            "symptomatic": point.get("symptomatic"),
            "recovered": point.get("recovered"),
            "immune": point.get("immune"),
            "quarantined": point.get("quarantined"),
            "isolated": point.get("isolated"),
            "new_infections": point.get("new_infections"),
            "total_pathogen_mass": point.get("total_pathogen_mass"),
            "n_zones_contaminated": point.get("n_zones_contaminated"),
            "max_concentration": point.get("max_concentration"),
            "max_conc_zone": point.get("max_conc_zone"),
            "trigger_status": status,
            "trigger_state": encode_trigger_status(status),
            "cumulative_cost_usd": point.get("cumulative_cost_usd"),
            "cumulative_ois": point.get("cumulative_ois"),
            "cumulative_ever_infected": point.get("cumulative_ever_infected"),
            "cumulative_ever_infected_passenger": point.get(
                "cumulative_ever_infected_passenger",
            ),
            "cumulative_ever_infected_crew": point.get(
                "cumulative_ever_infected_crew",
            ),
            "infection_attack_rate_passenger": point.get(
                "infection_attack_rate_passenger",
            ),
            "infection_attack_rate_crew": point.get("infection_attack_rate_crew"),
            "ever_ill_rate_crew": point.get("ever_ill_rate_crew"),
            "reported_case_rate_crew": point.get("reported_case_rate_crew"),
        }
        for col in EPOCH_FACTOR_COLUMNS:
            row[col] = summary_row.get(col)
        rows.append(row)
    return rows


def build_factor_dictionary(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Enumerate unique factor levels observed in the bundle."""
    factor_keys = (
        "campaign",
        "platform_id",
        "platform_class",
        "pathogen",
        "pathogen_id",
        "dose_adjustment",
        "density_exponent",
        "immunity_fraction",
        "surveillance_strategy",
        "transport_engine",
        "vsp_suspect_threshold",
        "vsp_lockdown_threshold",
        "wearable_profile",
    )
    out: dict[str, Any] = {"n_runs": len(run_rows), "factors": {}}
    for key in factor_keys:
        levels = sorted({row.get(key) for row in run_rows}, key=lambda x: (x is None, str(x)))
        out["factors"][key] = levels
    return out


def coerce_bool(value: Any) -> bool:
    """Parse bool-ish values from in-memory rows or CSV round-trips.

    CSV DictReader yields ``\"True\"`` / ``\"False\"`` strings; both are truthy
    under plain ``bool()`` / ``if value``, which previously inflated
    ``outbreak_rate`` to 1.0 after reloading ``run_summary.csv``.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    token = str(value).strip().lower()
    if token in {"", "0", "false", "f", "no", "n", "none", "null"}:
        return False
    if token in {"1", "true", "t", "yes", "y"}:
        return True
    return False


def build_aggregate_metrics(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute bundle-level aggregate scalars for the report header."""
    if not run_rows:
        return {"n_runs": 0}

    def _mean(key: str) -> float | None:
        vals: list[float] = []
        for r in run_rows:
            raw = r.get(key)
            if raw is None or raw == "":
                continue
            try:
                vals.append(float(raw))
            except (TypeError, ValueError):
                continue
        if not vals:
            return None
        return round(sum(vals) / len(vals), 6)

    platforms = Counter(str(r.get("platform_id")) for r in run_rows)
    pathogens = Counter(str(r.get("pathogen")) for r in run_rows)
    surv = Counter(str(r.get("surveillance_strategy")) for r in run_rows)
    return {
        "n_runs": len(run_rows),
        "mean_attack_rate": _mean("attack_rate"),
        "mean_peak_prevalence": _mean("peak_prevalence"),
        "mean_detection_epoch": _mean("detection_epoch"),
        "outbreak_rate": round(
            sum(1 for r in run_rows if coerce_bool(r.get("outbreak_occurred")))
            / len(run_rows),
            4,
        ),
        "platforms": dict(platforms),
        "pathogens": dict(pathogens),
        "surveillance_strategies": dict(surv),
    }


def epoch_table_columns() -> list[str]:
    """Column order for epoch_timeseries outputs."""
    return list(EPOCH_COLUMNS) + list(EPOCH_FACTOR_COLUMNS)
