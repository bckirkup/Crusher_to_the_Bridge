"""Factor parser for campaign run IDs and summary parameter blocks."""

from __future__ import annotations

import re
from typing import Any

# Common sweep tags embedded in mega-cruise / calibration run ids.
_TAG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("oa", re.compile(r"(oa\d+)")),
    ("imm", re.compile(r"(imm\d+)")),
    ("comp", re.compile(r"(comp\d+)")),
    ("init", re.compile(r"(init\d+)")),
    ("filter", re.compile(r"_(merv\d+|hepa)_")),
    ("decay", re.compile(r"_(low|med|high|vhigh)_")),
    ("dose_tag", re.compile(r"(?:^|_)(d(?:ose)?\d+(?:\.\d+)?)(?:_|$)")),
    ("seed_tag", re.compile(r"(?:^|_)s(\d+)(?:_|$)")),
    ("surv_tag", re.compile(
        r"(?:^|_)(none_true|none|syndromic|cascade_mpx|cascade|wearable|wastewater)(?:_|$)"
    )),
    ("engine_tag", re.compile(r"(?:^|_)(native|contamx|contam)(?:_|$)")),
    ("alpha_tag", re.compile(r"(?:^|_)(?:alpha|dens|dexp)(-?\d+(?:\.\d+)?)(?:_|$)")),
)

_PLATFORM_CLASS = {
    "expedition_cruise_450": "expedition",
    "classic_cruise_1900": "classic",
    "spirit_cruise_3000": "spirit",
    "mega_cruise_5000": "mega",
    "messy_cruise_500": "messy",
}

# Law 2: do not hardcode catalog pathogen name literals. Match via token fragment.
_NORO_TOKEN = "noro"


def parse_run_tags(run_id: str) -> dict[str, str | None]:
    """Extract common campaign sweep tags from a run_id string."""
    tags: dict[str, str | None] = {name: None for name, _ in _TAG_PATTERNS}
    for name, pat in _TAG_PATTERNS:
        m = pat.search(run_id)
        if m:
            tags[name] = m.group(1)
    return tags


_INIT_TAG = re.compile(r"(?:^|_)init(\d+)(?:_|$)", re.IGNORECASE)


def resolve_initial_infected(
    *,
    parameters: dict[str, Any] | None = None,
    run_spec: dict[str, Any] | None = None,
    run_id: str = "",
    timeseries: Any = None,
) -> int | None:
    """Best-effort infectious introductions ``k`` for one campaign run.

    Order: parameters → pathogen_overrides → ``initN`` run_id tag →
    epoch-0 ``infected`` / ``new_infections``.
    """
    params = parameters or {}
    for key in ("initial_infected", "n_initial_infected", "n_index"):
        if params.get(key) is not None and params.get(key) != "":
            try:
                return max(0, int(params[key]))
            except (TypeError, ValueError):
                # Try the next established source when a parameter is malformed.
                pass

    spec = run_spec or {}
    overrides = spec.get("pathogen_overrides") or {}
    if isinstance(overrides, dict):
        for value in overrides.values():
            if not isinstance(value, dict):
                continue
            if value.get("initial_infected") is None:
                continue
            try:
                return max(0, int(value["initial_infected"]))
            except (TypeError, ValueError):
                continue

    m = _INIT_TAG.search(str(run_id or ""))
    if m:
        return int(m.group(1))

    if timeseries and isinstance(timeseries, (list, tuple)) and timeseries:
        first = timeseries[0] if isinstance(timeseries[0], dict) else {}
        for key in ("infected", "new_infections"):
            if first.get(key) is None:
                continue
            try:
                return max(0, int(first.get(key) or 0))
            except (TypeError, ValueError):
                continue
    return None


def platform_class(platform_id: str | None) -> str | None:
    """Map a platform_id to a coarse platform class label."""
    if not platform_id:
        return None
    if platform_id in _PLATFORM_CLASS:
        return _PLATFORM_CLASS[platform_id]
    # Fiction / enterprise platforms keep their own id as class.
    if "enterprise" in platform_id.lower():
        return "enterprise"
    if "cruise" in platform_id.lower():
        return platform_id.split("_", 1)[0]
    return platform_id


def is_norovirus(pathogen: str | None, pathogen_id: str | None = None) -> bool:
    """Return True when pathogen labels indicate a noro* campaign row."""
    for value in (pathogen, pathogen_id):
        if value is None:
            continue
        token = str(value).strip().lower().replace("-", "_")
        if _NORO_TOKEN in token:
            return True
    return False


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def extract_factors(
    *,
    run_id: str,
    parameters: dict[str, Any] | None = None,
    run_spec: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge summary.parameters, run_spec, and run_id tags into factor fields.

    Preference order for each factor: ``parameters`` block, then ``run_spec``,
    then tags parsed from ``run_id``.
    """
    params = dict(parameters or {})
    spec = run_spec or {}
    catalog = spec.get("catalog") or {}
    run = spec.get("run") or {}
    cfg = spec.get("config_overrides") or {}
    hvac = cfg.get("hvac") or {}
    ship = cfg.get("ship_graph") or {}
    tags = parse_run_tags(run_id)

    platform_id = _first(
        params.get("platform_id"),
        catalog.get("platform_id"),
    )
    pathogen = _first(params.get("pathogen"), params.get("pathogen_name"))
    pathogen_id = _first(
        params.get("pathogen_id"),
        params.get("pathogen_bundle_id"),
        catalog.get("pathogen_bundle_id"),
    )
    if pathogen is None and pathogen_id is not None:
        # Bundle ids often look like ``norovirus_only`` / ``multi_pathogen``.
        pathogen = str(pathogen_id).replace("_only", "").replace("_bundle", "")

    dose = _first(params.get("dose_adjustment"), params.get("dose_adj"))
    if dose is None and tags.get("dose_tag"):
        token = tags["dose_tag"]
        assert token is not None
        dose = token.lstrip("dose").lstrip("d")

    density = _first(
        params.get("density_exponent"),
        params.get("density_alpha"),
        tags.get("alpha_tag"),
    )
    immunity = _first(
        params.get("immune_fraction"),
        params.get("immunity_fraction"),
        params.get("pre_immunity_fraction"),
        ship.get("immune_fraction"),
    )
    if immunity is None and tags.get("imm"):
        imm_tag = tags["imm"]
        assert imm_tag is not None
        # imm25 → 0.25, imm0 → 0.0
        digits = "".join(ch for ch in imm_tag if ch.isdigit())
        if digits:
            immunity = float(digits) / 100.0

    surveillance = _first(
        params.get("surveillance"),
        params.get("surveillance_strategy"),
        tags.get("surv_tag"),
        "none",
    )
    transport = _first(
        params.get("transport_engine"),
        hvac.get("transport_engine"),
        tags.get("engine_tag"),
        "native",
    )
    if transport == "contam":
        transport = "contamx"

    seed = _first(params.get("seed"), run.get("random_seed"), tags.get("seed_tag"))
    num_agents = _first(params.get("num_agents"), ship.get("num_agents"))
    num_epochs = _first(
        params.get("num_epochs"),
        run.get("num_epochs"),
        (summary or {}).get("num_epochs"),
    )

    initial_infected = resolve_initial_infected(
        parameters=params,
        run_spec=spec,
        run_id=run_id,
    )

    campaign = _first(
        params.get("campaign"),
        params.get("tier_id"),
        params.get("manifest_id"),
    )

    factors: dict[str, Any] = {
        "run_id": run_id,
        "campaign": campaign,
        "platform_id": platform_id,
        "platform_class": platform_class(str(platform_id) if platform_id else None),
        "pathogen": pathogen,
        "pathogen_id": pathogen_id,
        "dose_adjustment": _coerce_float(dose),
        "density_exponent": _coerce_float(density),
        "immunity_fraction": _coerce_float(immunity),
        "surveillance_strategy": surveillance,
        "transport_engine": transport,
        "seed": _coerce_int(seed),
        "initial_infected": _coerce_int(initial_infected),
        "num_agents": _coerce_int(num_agents),
        "num_epochs": _coerce_int(num_epochs),
        # Optional columns
        "vsp_suspect_threshold": _coerce_float(
            _first(params.get("suspect_attack_rate"), params.get("vsp_suspect_threshold"))
        ),
        "vsp_confirm_threshold": _coerce_float(
            _first(params.get("confirm_attack_rate"), params.get("vsp_confirm_threshold"))
        ),
        "vsp_lockdown_threshold": _coerce_float(
            _first(
                params.get("lockdown_attack_rate"),
                params.get("vsp_lockdown_threshold"),
            )
        ),
        "sick_call_probability": _coerce_float(params.get("sick_call_probability")),
        "detection_delay_epochs": _coerce_int(
            _first(
                params.get("surveillance_delay_epochs"),
                params.get("detection_delay_epochs"),
            )
        ),
        "isolation_compliance": _coerce_float(
            _first(
                params.get("quarantine_compliance"),
                params.get("isolation_compliance"),
            )
        ),
        "wearable_profile": _first(
            params.get("wearables"),
            params.get("wearable_profile"),
        ),
        "wastewater_enabled": params.get("wastewater_enabled"),
        "cascade_enabled": params.get("cascade_enabled"),
        "multiplex_enabled": params.get("multiplex_enabled"),
        "contam_paired_run_id": params.get("contam_paired_run_id"),
        "native_paired_run_id": params.get("native_paired_run_id"),
    }
    # Preserve raw tags for debugging / factor dictionary.
    factors["_tags"] = {k: v for k, v in tags.items() if v is not None}
    return factors
