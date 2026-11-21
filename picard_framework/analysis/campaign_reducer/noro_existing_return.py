"""``noro_existing_return`` extraction profile.

One wide ``noro_existing_return_vectors`` row per completed voyage archive
across three existing norovirus campaigns on S3:

- ``noro_explorer_reconstruction_01`` (Explorer: 600 voyages across 6 tiers)
- ``noro_paper1_joint_eval_01`` (Four-hull joint evaluation: 896 voyages across
  diagnostic/evaluation/reproduction; excludes census children)
- ``noro_supply_solver_screen_01_bf0`` (Same-version solver reference: 16
  voyages, kept strictly separate from joint evaluation; excludes the large
  ``growth_census.json.gz`` member via ``member_allowlist``)

Each row preserves campaign/cohort/tier/arm/seed/archive provenance, resolved
effective modes, realized passenger/crew complements, initial imported/explicit
infections where retained, cumulative burden and thresholds with explicit field
definitions, daily onset/reporting curves where retained, voyage-level
environmental swab/tank summaries (units, LOD/LOQ, detections, censoring,
quantitative summaries from ``joint_eval.json.gz``), and voyage-level route
aggregates. Unrecorded fields emit ``null`` with typed provenance/availability
metadata and are never inferred.
"""
from __future__ import annotations

from statistics import median
from typing import Any

from . import contracts, first_paper
from .rows import ReductionContext, SourceSpec

PROFILE_ID = "noro_existing_return"
SCAN_ROLE = "scan_rows"

_SUMMARY_MEMBER = "summary.json"
_JOINT_EVAL_MEMBER = "joint_eval.json.gz"

_COHORT_BY_CAMPAIGN = {
    "noro_explorer_reconstruction_01": "explorer_reconstruction",
    "noro_paper1_joint_eval_01": "paper1_joint_eval",
    "noro_supply_solver_screen_01_bf0": "supply_solver_reference",
}


def profile() -> dict[str, Any]:
    """The frozen contract document for this extraction profile."""
    return contracts.load(contracts.NORO_EXISTING_RETURN)


def defaults() -> dict[str, Any]:
    doc = profile()
    return {
        "member_allowlist": tuple(doc["member_allowlist"]),
        "suppress_tables": frozenset(doc["suppress_tables"]),
        "emit_scalars": bool(doc["emit_scalars"]),
        "scan_role": doc["scan_role"],
    }


def definition_version() -> str:
    return profile()["definition_version"]


def definition_sha256() -> str:
    return contracts.sha256(contracts.NORO_EXISTING_RETURN)


def absorb_scan_rows(_acc, _spec: SourceSpec, _result) -> None:
    """No external scan-row join is needed for this profile."""


def _folder_and_base(member_path: str | None) -> tuple[str, str]:
    path = (member_path or "").strip("/")
    if "/" in path:
        folder, base = path.rsplit("/", 1)
        return folder, base
    return "", path


def _group_docs_by_folder(docs: list) -> list[tuple[Any, Any | None]]:
    """Pair each ``summary.json`` doc with any sibling ``joint_eval.json.gz``."""
    by_folder: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for ddoc in docs:
        folder, base = _folder_and_base(ddoc.member_path)
        if base not in (_SUMMARY_MEMBER, _JOINT_EVAL_MEMBER):
            continue
        if folder not in by_folder:
            by_folder[folder] = {}
            order.append(folder)
        by_folder[folder][base] = ddoc
    pairs: list[tuple[Any, Any | None]] = []
    for folder in order:
        bucket = by_folder[folder]
        summary_doc = bucket.get(_SUMMARY_MEMBER)
        if summary_doc is not None:
            pairs.append((summary_doc, bucket.get(_JOINT_EVAL_MEMBER)))
    return pairs


def _cohort_kind(
    summary: dict[str, Any],
    joint_eval: dict[str, Any] | None,
    src: SourceSpec,
) -> str:
    campaign = summary.get("campaign") or src.campaign_id or ""
    if campaign in _COHORT_BY_CAMPAIGN:
        return _COHORT_BY_CAMPAIGN[campaign]
    if joint_eval is not None or "joint_eval" in summary:
        return "paper1_joint_eval"
    if "introduction" in summary and "onsets_by_day" in summary:
        return "explorer_reconstruction"
    if "census" in summary and "initiation" in summary:
        return "supply_solver_reference"
    return "unknown"


def _set_field(
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
    name: str,
    val: Any,
    source: str,
    absent_reason: str = "absent_in_archive",
) -> None:
    if val is None:
        values[name] = None
        prov[name] = {"status": "absent", "reason": absent_reason}
        missing.append(name)
        return
    values[name] = val
    prov[name] = {"status": "present", "source": source}


def _first_non_null(*candidates: Any) -> Any:
    for item in candidates:
        if item is not None:
            return item
    return None


def _design_stratum(
    cohort: str,
    tier: Any,
    object_key: str,
) -> str | None:
    if cohort == "paper1_joint_eval":
        for label in ("diagnostic", "evaluation", "reproduction"):
            if tier == label or f"/{label}/" in object_key:
                return label
        return str(tier) if tier is not None else None
    if cohort == "explorer_reconstruction":
        return str(tier) if tier is not None else None
    if cohort == "supply_solver_reference":
        return "solver_reference_bf0"
    return None


def _arm_label(raw: Any) -> str | None:
    if isinstance(raw, dict):
        val = raw.get("arm")
        return str(val) if val is not None else None
    if raw is None:
        return None
    return str(raw)


def _extract_identity(
    summary: dict[str, Any],
    joint_eval: dict[str, Any] | None,
    src: SourceSpec,
    object_key: str,
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> str:
    je = joint_eval or {}
    je_scalars = summary.get("joint_eval") if isinstance(summary.get("joint_eval"), dict) else {}
    params = summary.get("parameters") if isinstance(summary.get("parameters"), dict) else {}
    cohort = _cohort_kind(summary, joint_eval, src)
    campaign = _first_non_null(summary.get("campaign"), je.get("campaign"), src.campaign_id)
    tier = _first_non_null(
        summary.get("tier"),
        params.get("tier_id"),
        je.get("tier"),
        src.cell_id,
    )
    arm = _first_non_null(
        _arm_label(summary.get("declared_arm")),
        _arm_label(je_scalars.get("arm")),
        _arm_label(summary.get("arm")),
        _arm_label(je.get("arm")),
    )
    seed = _first_non_null(
        summary.get("seed"),
        params.get("seed"),
        params.get("random_seed"),
        je.get("seed"),
        src.seed,
    )
    platform = _first_non_null(
        summary.get("platform"),
        params.get("platform_id"),
        params.get("platform"),
        je.get("platform"),
        src.hull_id,
    )
    engine_sha = _first_non_null(
        summary.get("engine_git_sha"),
        params.get("engine_git_sha"),
        je.get("engine_git_sha"),
        src.engine_sha,
    )
    image_digest = _first_non_null(summary.get("image_digest"), src.image_digest)
    effective_modes = _first_non_null(
        summary.get("effective_state"),
        je_scalars.get("effective_config"),
        je.get("effective_config"),
        summary.get("effective_config"),
        (summary.get("initiation") or {}).get("resolved"),
    )

    _set_field(values, prov, missing, "cohort", cohort, "derived:cohort_classifier")
    _set_field(values, prov, missing, "campaign", campaign, "summary.campaign")
    _set_field(values, prov, missing, "tier", tier, "summary.tier")
    _set_field(values, prov, missing, "arm", arm, "summary.arm")
    _set_field(values, prov, missing, "seed", seed, "summary.seed")
    _set_field(values, prov, missing, "platform", platform, "summary.platform")
    _set_field(
        values, prov, missing, "design_stratum",
        _design_stratum(cohort, tier, object_key), "derived:design_stratum",
    )
    _set_field(
        values, prov, missing, "engine_git_sha", engine_sha,
        "summary.engine_git_sha", "not_recorded_in_archive",
    )
    _set_field(
        values, prov, missing, "image_digest", image_digest,
        "source.image_digest", "not_recorded_in_run_archive",
    )
    _set_field(
        values, prov, missing, "attempt_outcome",
        _first_non_null(summary.get("status"), "completed"),
        "summary.status",
    )
    _set_field(
        values, prov, missing, "effective_modes", effective_modes,
        "summary.effective_state|joint_eval.effective_config|initiation.resolved",
    )
    return cohort


def _extract_complements_and_initial(
    summary: dict[str, Any],
    joint_eval: dict[str, Any] | None,
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> None:
    sblock = summary.get("summary") or {}
    je_scalars = summary.get("joint_eval") if isinstance(summary.get("joint_eval"), dict) else {}
    je_burden = je_scalars.get("burden") or (joint_eval or {}).get("burden") or {}
    je_curves = (joint_eval or {}).get("curves") or {}
    intro = summary.get("introduction") or {}
    init_manifest = intro.get("initiation_manifest") or {}
    census = summary.get("census") or {}

    n_pax = _first_non_null(
        sblock.get("passenger_complement"),
        je_burden.get("passenger_complement"),
        sblock.get("total_passengers"),
        je_burden.get("total_passengers"),
        (summary.get("parameters") or {}).get("total_passengers"),
    )
    n_crew = _first_non_null(
        sblock.get("crew_complement"),
        je_burden.get("crew_complement"),
        sblock.get("total_crew"),
        je_burden.get("total_crew"),
        (summary.get("parameters") or {}).get("total_crew"),
    )
    _set_field(
        values, prov, missing, "total_passengers", n_pax,
        "summary.summary.passenger_complement",
    )
    _set_field(
        values, prov, missing, "total_crew", n_crew,
        "summary.summary.crew_complement",
    )

    init_ids = summary.get("initially_infected_agent_ids")
    init_total = len(init_ids) if isinstance(init_ids, list) else census.get("n_imports")
    init_by_role = init_manifest.get("drawn_by_role")
    if init_by_role is None and (
        je_curves.get("preboarding_declared_passenger") is not None
        or je_curves.get("preboarding_declared_crew") is not None
    ):
        init_by_role = {
            "passenger_preboarding_declared": je_curves.get("preboarding_declared_passenger"),
            "crew_preboarding_declared": je_curves.get("preboarding_declared_crew"),
            "scope": "preboarding_declared_only",
        }
    init_states = init_manifest.get("drawn_by_state") or init_manifest.get("initial_states")

    _set_field(
        values, prov, missing, "initial_infected_total", init_total,
        "summary.initially_infected_agent_ids|summary.census.n_imports",
        "not_recorded_in_archive",
    )
    _set_field(
        values, prov, missing, "initial_infected_by_role", init_by_role,
        "summary.introduction.initiation_manifest|joint_eval.curves.preboarding_declared",
        "not_recorded_in_archive",
    )
    _set_field(
        values, prov, missing, "initial_disease_states", init_states,
        "summary.introduction.initiation_manifest",
        "not_recorded_in_archive",
    )


def _first_role_from_timeseries(series: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not series:
        return None
    pax_ep: int | None = None
    crew_ep: int | None = None
    for row in series:
        ep = row.get("epoch")
        if ep is None:
            continue
        if pax_ep is None and (row.get("cumulative_reported_cases_passenger") or 0) > 0:
            pax_ep = int(ep)
        if crew_ep is None and (row.get("cumulative_reported_cases_crew") or 0) > 0:
            crew_ep = int(ep)
    if pax_ep is None and crew_ep is None:
        category = "none"
    elif crew_ep is None or (pax_ep is not None and pax_ep < crew_ep):
        category = "passenger_first"
    elif pax_ep is None or crew_ep < pax_ep:
        category = "crew_first"
    else:
        category = "tie"
    return {
        "category": category,
        "first_passenger_report_epoch": pax_ep,
        "first_crew_report_epoch": crew_ep,
        "source": "derived_from_timeseries",
    }


def _final_role_category(rep_pax: Any, rep_crew: Any) -> str | None:
    if rep_pax is None and rep_crew is None:
        return None
    p = int(rep_pax or 0)
    c = int(rep_crew or 0)
    if p == 0 and c == 0:
        return "none"
    if p > 0 and c == 0:
        return "passenger_only"
    if c > 0 and p == 0:
        return "crew_only"
    return "both_roles"


def _extract_burden_and_thresholds(
    summary: dict[str, Any],
    joint_eval: dict[str, Any] | None,
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> None:
    sblock = summary.get("summary") or {}
    derived = summary.get("derived") or {}
    je = joint_eval or {}
    je_scalars = summary.get("joint_eval") if isinstance(summary.get("joint_eval"), dict) else {}
    je_burden = je_scalars.get("burden") or je.get("burden") or {}
    je_thresh = je_scalars.get("threshold") or je.get("threshold") or {}
    census = summary.get("census") or {}

    rep_pax = _first_non_null(
        sblock.get("cumulative_reported_cases_passenger"),
        je_burden.get("cumulative_reported_cases_passenger"),
        je_burden.get("reported_passenger"),
    )
    rep_crew = _first_non_null(
        sblock.get("cumulative_reported_cases_crew"),
        je_burden.get("cumulative_reported_cases_crew"),
        je_burden.get("reported_crew"),
    )
    burden = {
        "ever_infected_total": _first_non_null(
            sblock.get("cumulative_ever_infected"), je_burden.get("ever_infected_total"),
        ),
        "ever_infected_passenger": _first_non_null(
            sblock.get("cumulative_ever_infected_passenger"),
            je_burden.get("cumulative_ever_infected_passenger"),
            je_burden.get("ever_infected_passenger"),
        ),
        "ever_infected_crew": _first_non_null(
            sblock.get("cumulative_ever_infected_crew"),
            je_burden.get("cumulative_ever_infected_crew"),
            je_burden.get("ever_infected_crew"),
        ),
        "acquired_total": census.get("n_acquired"),
        "ever_ill_total": _first_non_null(
            sblock.get("cumulative_ever_ill"),
            sblock.get("cumulative_ever_symptomatic"),
            je_burden.get("cumulative_ever_ill"),
            je_burden.get("ever_ill_total"),
        ),
        "ever_ill_passenger": _first_non_null(
            sblock.get("cumulative_ever_ill_passenger"),
            sblock.get("cumulative_ever_symptomatic_passenger"),
            je_burden.get("cumulative_ever_ill_passenger"),
            je_burden.get("ever_ill_passenger"),
        ),
        "ever_ill_crew": _first_non_null(
            sblock.get("cumulative_ever_ill_crew"),
            sblock.get("cumulative_ever_symptomatic_crew"),
            je_burden.get("cumulative_ever_ill_crew"),
            je_burden.get("ever_ill_crew"),
        ),
        "reported_total": _first_non_null(
            sblock.get("cumulative_reported_cases"), je_burden.get("reported_total"),
        ),
        "reported_passenger": rep_pax,
        "reported_crew": rep_crew,
        "reported_noise_total": _first_non_null(
            sblock.get("cumulative_reported_noise_cases"),
            je_burden.get("reported_noise_total"),
        ),
        "definitions": {
            "ever_infected": "Cumulative unique agents infected (imports + onboard acquisitions unless acquired_total is separately reported).",
            "acquired_total": "Onboard acquisitions excluding imports (present only when census.n_acquired is recorded).",
            "ever_ill": "Cumulative unique agents reaching symptomatic disease.",
            "reported": "Cumulative etiologic reported cases by role (excludes non-norovirus noise reports).",
        },
    }
    _set_field(values, prov, missing, "burden", burden, "summary.summary|joint_eval.burden")

    vsp_epoch = _first_non_null(
        je_thresh.get("vsp_trigger_epoch"), derived.get("vsp_trigger_epoch"),
    )
    thresholds = {
        "vsp_trigger_epoch": vsp_epoch,
        "vsp_posted": _first_non_null(je_thresh.get("posted"), vsp_epoch is not None),
        "detection_epoch": derived.get("detection_epoch"),
        "trigger_status": _first_non_null(
            je_thresh.get("trigger_status"),
            sblock.get("trigger_status"),
            summary.get("trigger_status"),
        ),
    }
    _set_field(values, prov, missing, "thresholds", thresholds, "summary.derived|joint_eval.threshold")

    ts = summary.get("timeseries")
    series = ts if isinstance(ts, list) else []
    first_role = _first_non_null(
        je_scalars.get("first_role"),
        je.get("first_role"),
        _first_role_from_timeseries(series),
    )
    _set_field(
        values, prov, missing, "first_role", first_role,
        "summary.joint_eval.first_role|joint_eval.first_role|derived:timeseries",
    )
    _set_field(
        values, prov, missing, "final_role_category",
        _final_role_category(rep_pax, rep_crew),
        "derived:reported_by_role",
    )
    _set_field(
        values, prov, missing, "role_checkpoints",
        summary.get("role_checkpoints"),
        "summary.role_checkpoints",
        "not_recorded_in_archive",
    )


def _cumulative_from_daily(daily: list[int | float] | None) -> list[int | float] | None:
    if not isinstance(daily, list):
        return None
    out: list[int | float] = []
    running: int | float = 0
    for val in daily:
        running += val
        out.append(running)
    return out


def _daily_reporting_from_timeseries(
    series: list[dict[str, Any]],
    epochs_per_day: int = 24,
) -> dict[str, Any] | None:
    if not series:
        return None
    by_day: dict[int, dict[str, Any]] = {}
    for row in series:
        ep = row.get("epoch")
        if ep is None:
            continue
        day = int(ep) // epochs_per_day
        by_day[day] = row
    days = sorted(by_day)
    return {
        "days": days,
        "cumulative_reported_passenger": [
            by_day[d].get("cumulative_reported_cases_passenger") for d in days
        ],
        "cumulative_reported_crew": [
            by_day[d].get("cumulative_reported_cases_crew") for d in days
        ],
        "cumulative_reported_total": [
            by_day[d].get("cumulative_reported_cases") for d in days
        ],
        "source": "derived_daily_terminal_from_timeseries",
    }


def _extract_curves(
    summary: dict[str, Any],
    joint_eval: dict[str, Any] | None,
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> None:
    je_curves = (joint_eval or {}).get("curves") or {}
    if isinstance(summary.get("onsets_by_day"), dict):
        onsets = {
            "variants": summary["onsets_by_day"],
            "named_exclusions": ["all", "excluding_declared_seeds", "incident"],
            "line_list_cases": summary.get("line_list_cases"),
        }
        onsets_src = "summary.onsets_by_day"
    elif "onsets_daily" in je_curves:
        onsets = {
            "variants": {"all_line_list_onsets": je_curves.get("onsets_daily")},
            "named_exclusions": [],
            "day0_label": je_curves.get("day0_label"),
            "line_list_cases": je_curves.get("line_list_cases"),
            "line_list_channels": je_curves.get("line_list_channels"),
        }
        onsets_src = "joint_eval.curves.onsets_daily"
    else:
        onsets = None
        onsets_src = "absent"

    _set_field(
        values, prov, missing, "daily_onset_curves", onsets,
        onsets_src, "not_recorded_in_archive",
    )

    if isinstance(summary.get("reporting_by_day"), dict):
        reporting = summary["reporting_by_day"]
        rep_src = "summary.reporting_by_day"
    elif "reported_daily_passenger" in je_curves or "reported_daily_crew" in je_curves:
        rep_p = je_curves.get("reported_daily_passenger")
        rep_c = je_curves.get("reported_daily_crew")
        reporting = {
            "daily_reported_passenger": rep_p,
            "daily_reported_crew": rep_c,
            "cumulative_reported_passenger": _cumulative_from_daily(rep_p),
            "cumulative_reported_crew": _cumulative_from_daily(rep_c),
            "day0_label": je_curves.get("day0_label"),
        }
        rep_src = "joint_eval.curves.reported_daily"
    else:
        ts = summary.get("timeseries")
        reporting = _daily_reporting_from_timeseries(ts if isinstance(ts, list) else [])
        rep_src = "derived:timeseries"

    _set_field(
        values, prov, missing, "cumulative_reporting_curves", reporting,
        rep_src, "not_recorded_in_archive",
    )


def _numeric_summary(nums: list[float]) -> dict[str, float | int] | None:
    if not nums:
        return None
    return {
        "n": len(nums),
        "min": min(nums),
        "median": float(median(nums)),
        "max": max(nums),
        "mean": sum(nums) / len(nums),
    }


def _collect_floats(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [
        float(r[key]) for r in rows
        if isinstance(r, dict) and isinstance(r.get(key), (int, float))
    ]


def _collect_unique(rows: list[dict[str, Any]], key: str) -> list[Any]:
    seen = {r.get(key) for r in rows if isinstance(r, dict) and r.get(key) is not None}
    return sorted(seen)


def _extract_environment(
    joint_eval: dict[str, Any] | None,
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> None:
    env = (joint_eval or {}).get("environment")
    if not isinstance(env, dict):
        _set_field(
            values, prov, missing, "environment_summary", None,
            "joint_eval.environment", "not_recorded_in_cohort",
        )
        return

    swabs = env.get("swab_rows") if isinstance(env.get("swab_rows"), list) else []
    tanks = env.get("tank_rows") if isinstance(env.get("tank_rows"), list) else []
    env_summary = {
        "units": env.get("units"),
        "swab_rows_rule": env.get("swab_rows_rule"),
        "swab": {
            "total": env.get("swab_total"),
            "rows_kept": env.get("swab_rows_kept", len(swabs)),
            "detected_total": env.get("swab_detected_total"),
            "censored_below_lod_total": env.get("swab_censored_total"),
            "first_detected_epoch": env.get("first_swab_detected_epoch"),
            "zones": _collect_unique(swabs, "zone"),
            "surface_classes": _collect_unique(swabs, "surface_class"),
            "epochs_with_recovery": _collect_unique(swabs, "epoch"),
            "lod_values": _collect_unique(swabs, "lod"),
            "recovered_summary": _numeric_summary(_collect_floats(swabs, "recovered")),
            "density_summary": _numeric_summary(_collect_floats(swabs, "density")),
        },
        "tank": {
            "assays_total": env.get("tank_assays", len(tanks)),
            "detected_total": env.get("tank_detected_total"),
            "censored_below_lod_total": env.get("tank_censored_total"),
            "quantifiable_total": sum(
                1 for r in tanks if isinstance(r, dict) and r.get("quantifiable")
            ),
            "first_detected_epoch": env.get("first_tank_detected_epoch"),
            "instruments": _collect_unique(tanks, "instrument"),
            "streams": _collect_unique(tanks, "stream"),
            "epochs_observed": _collect_unique(tanks, "epoch"),
            "lod_values": _collect_unique(tanks, "lod"),
            "loq_values": _collect_unique(tanks, "loq"),
            "concentration_summary": _numeric_summary(
                _collect_floats(tanks, "concentration"),
            ),
        },
    }
    _set_field(
        values, prov, missing, "environment_summary",
        env_summary, "joint_eval.environment",
    )


def _extract_routes(
    summary: dict[str, Any],
    values: dict[str, Any],
    prov: dict[str, Any],
    missing: list[str],
) -> None:
    sblock = summary.get("summary") or {}
    by_dom = sblock.get("infections_by_dominant_route")
    dose_share = sblock.get("infection_dose_share_by_route")
    routes = None
    if by_dom is not None or dose_share is not None:
        routes = {
            "infections_by_dominant_route": by_dom,
            "infection_dose_share_by_route": dose_share,
            "granularity": "voyage_aggregate_only",
        }
    _set_field(
        values, prov, missing, "route_aggregates", routes,
        "summary.summary.route_aggregates", "not_recorded_in_archive",
    )


def _apply_availability_declarations(
    doc: dict[str, Any],
    values: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    for entry in doc.get("availability_fields") or []:
        col = entry["column"]
        if col in values and values[col] is not None:
            continue
        values.setdefault(col, None)
        prov[col] = {
            "status": "absent",
            "availability": entry["availability"],
            "reason": entry["reason"],
        }


def vector_rows(
    _spec,
    src: SourceSpec,
    result,
    ctx: ReductionContext,
    _acc,
) -> list[dict[str, Any]]:
    """Build ``noro_existing_return_vectors`` rows for one archive source."""
    doc = profile()
    defn_sha = definition_sha256()
    object_key = first_paper._object_key(src.uri)
    rows: list[dict[str, Any]] = []

    for summary_ddoc, je_ddoc in _group_docs_by_folder(result.docs):
        summary = summary_ddoc.doc if isinstance(summary_ddoc.doc, dict) else {}
        joint_eval = (
            je_ddoc.doc
            if je_ddoc is not None and isinstance(je_ddoc.doc, dict)
            else None
        )
        values: dict[str, Any] = {}
        prov: dict[str, Any] = {}
        missing: list[str] = []

        _extract_identity(summary, joint_eval, src, object_key, values, prov, missing)
        _extract_complements_and_initial(summary, joint_eval, values, prov, missing)
        _extract_burden_and_thresholds(summary, joint_eval, values, prov, missing)
        _extract_curves(summary, joint_eval, values, prov, missing)
        _extract_environment(joint_eval, values, prov, missing)
        _extract_routes(summary, values, prov, missing)
        _apply_availability_declarations(doc, values, prov)

        row = first_paper._row_envelope(
            "ner",
            summary_ddoc,
            src,
            ctx,
            object_key,
            _SUMMARY_MEMBER,
            doc,
            values,
            prov,
            missing,
            defn_sha,
        )
        if je_ddoc is not None:
            row["sidecar_member"] = _JOINT_EVAL_MEMBER
            row["sidecar_asset_id"] = je_ddoc.asset_id
        rows.append(row)
    return rows
