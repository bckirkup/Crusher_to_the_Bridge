#!/usr/bin/env python3
"""Paper 3 variant-surveillance campaign tiers (``vs*``).

The five Paper 3 designs (``docs/paper3/variant_surveillance_spec.md`` §6) sweep
mutational supply rather than pinning it: a *diversity* regime (multi-genotype
embarkation, 1–4 founders, nominal per-pathogen rates) and an *emergence*
regime (one founder, per-transmission and within-host rates swept over roughly
two decades around nominal), each crossed with voyage length so a detection
result is a timescale rather than a single number. Co-infection interference
(``superinfection_susceptibility``) and ``recombination_rate`` get one
sensitivity tier each.

Two labels are mandatory on every ``vs*`` manifest and are written into both
the run id and ``campaign_parameters``:

``natural_history_clock``
    ``hours`` (the physical mainline) or ``legacy_epoch_day`` (retired; kept
    only to reproduce a pre-#303 result).
``incubation_arm``
    ``distribution`` (per-infection draw, #290) or ``fixed_onset`` (the
    pre-#290 data-generating process, for a paired control tier).

Both appear in the run id because they are *different models of the same
voyage*: pooling them would average two data-generating processes. Tier-level
``incubation_arm`` overrides the manifest default so one manifest can carry a
paired control tier without a second file.

Voyage length is declared in days and converted to epochs by the manifest's
declared ``epoch_duration_hours`` (1 by default), so no tier multiplies by 24.
"""
from __future__ import annotations

import os
import warnings
from itertools import product
from typing import Any, Iterator, Mapping, Sequence

from picard_framework.pathogen_overrides import load_pathogen_bundle
from picard_framework.runs.mega_cruise_campaign.boarding_axis import (
    IndexCaseAxis,
)

CLOCK_HOURS = "hours"
CLOCK_LEGACY_EPOCH_DAY = "legacy_epoch_day"
CLOCKS = (CLOCK_HOURS, CLOCK_LEGACY_EPOCH_DAY)
_CLOCK_TAGS = {CLOCK_HOURS: "hrs", CLOCK_LEGACY_EPOCH_DAY: "legacy"}

ARM_DISTRIBUTION = "distribution"
ARM_FIXED_ONSET = "fixed_onset"
INCUBATION_ARMS = (ARM_DISTRIBUTION, ARM_FIXED_ONSET)
_ARM_TAGS = {ARM_DISTRIBUTION: "dist", ARM_FIXED_ONSET: "fixed"}

REGIMES = ("diversity", "emergence", "interference", "recombination", "investment")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)),
)))
BUNDLE_DIR = os.path.join("data", "pathogens")

_DEFAULT_EPOCH_DURATION_HOURS = 1.0
_HOURS_PER_DAY = 24.0

# (tier key, run-id tag prefix, campaign_parameters name, strain_evolution key)
_RATE_AXES: tuple[tuple[str, str, str, str], ...] = (
    ("mutation_rates", "mu", "mutation_rate", "mutation_rate"),
    (
        "within_host_mutation_rates_per_day",
        "wh",
        "within_host_mutation_rate_per_day",
        "within_host_mutation_rate_per_day",
    ),
    (
        "recombination_rates_per_day",
        "rec",
        "recombination_rate_per_day",
        "recombination_rate_per_day",
    ),
    (
        "superinfection_susceptibilities",
        "sup",
        "superinfection_susceptibility",
        "superinfection_susceptibility",
    ),
)
_RATE_AXIS_ALIASES = {
    "within_host_mutation_rates_per_day": "within_host_mutation_rates",
    "recombination_rates_per_day": "recombination_rates",
}


class VariantManifestError(ValueError):
    """Raised when a ``vs*`` manifest or tier is not self-describing."""


def _require_choice(value: Any, choices: Sequence[str], label: str) -> str:
    text = str(value)
    if text not in choices:
        raise VariantManifestError(
            f"{label} must be one of {tuple(choices)}, got {value!r}",
        )
    return text


def manifest_clock(manifest: Mapping[str, Any]) -> str:
    """Declared natural-history clock arm of a ``vs*`` manifest."""
    if "natural_history_clock" not in manifest:
        raise VariantManifestError(
            "a variant-surveillance manifest must declare natural_history_clock: "
            "hourly and legacy_epoch_day runs are different models and must not pool",
        )
    return _require_choice(
        manifest["natural_history_clock"], CLOCKS, "natural_history_clock",
    )


def incubation_arm(manifest: Mapping[str, Any], tier: Mapping[str, Any]) -> str:
    """Incubation arm for one tier (tier override wins over the manifest)."""
    if "incubation_arm" in tier:
        return _require_choice(
            tier["incubation_arm"], INCUBATION_ARMS, "tier incubation_arm",
        )
    if "incubation_arm" not in manifest:
        raise VariantManifestError(
            "a variant-surveillance manifest must declare incubation_arm: "
            "the drawn and fixed-onset arms are different data-generating processes",
        )
    return _require_choice(
        manifest["incubation_arm"], INCUBATION_ARMS, "incubation_arm",
    )


def tier_regime(tier: Mapping[str, Any]) -> str:
    """Scientific regime label a ``vs*`` tier belongs to."""
    if "regime" not in tier:
        raise VariantManifestError("a vs* tier must declare a regime")
    return _require_choice(tier["regime"], REGIMES, "regime")


def epochs_for_days(manifest: Mapping[str, Any], voyage_days: int) -> int:
    """Physical epochs spanning ``voyage_days`` under the manifest's epoch."""
    duration = float(
        manifest.get("epoch_duration_hours", _DEFAULT_EPOCH_DURATION_HOURS),
    )
    if duration <= 0.0:
        raise VariantManifestError(
            f"epoch_duration_hours must be positive, got {duration!r}",
        )
    days = int(voyage_days)
    if days <= 0:
        raise VariantManifestError(f"voyage_days must be positive, got {days!r}")
    epochs = int(round(days * _HOURS_PER_DAY / duration))
    if epochs <= 0:
        raise VariantManifestError(
            f"voyage_days={days} at epoch_duration_hours={duration} is under one epoch",
        )
    return epochs


def _axis(tier: Mapping[str, Any], key: str) -> tuple[Any, ...]:
    """Swept values for one optional axis; ``(None,)`` means profile nominal."""
    if key not in tier:
        return (None,)
    values = tier[key]
    if not isinstance(values, list) or not values:
        raise VariantManifestError(f"tier {key} must be a non-empty list")
    return tuple(values)


def _platforms(
    tier: Mapping[str, Any],
    manifest: Mapping[str, Any],
    platform_override: str | None,
) -> tuple[str, ...]:
    if platform_override:
        return (str(platform_override),)
    if tier.get("platforms"):
        return tuple(str(p) for p in tier["platforms"])
    if tier.get("platform"):
        return (str(tier["platform"]),)
    return (str(manifest["platform"]),)


def _voyage_days(tier: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[int, ...]:
    days = tier.get("voyage_days") or (manifest.get("defaults") or {}).get("voyage_days")
    if not days:
        raise VariantManifestError(
            "a vs* tier needs voyage_days (a detection result is a timescale)",
        )
    return tuple(int(d) for d in days)


def _founders(tier: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[int, ...]:
    founders = (
        tier.get("founder_strains")
        or (manifest.get("defaults") or {}).get("founder_strains")
        or [1]
    )
    return tuple(int(f) for f in founders)


def tier_axes(
    manifest: Mapping[str, Any],
    tier: Mapping[str, Any],
    *,
    platform_override: str | None = None,
) -> dict[str, tuple[Any, ...]]:
    """Every swept axis of a ``vs*`` tier, in run-ordering order."""
    axes: dict[str, tuple[Any, ...]] = {
        "platform": _platforms(tier, manifest, platform_override),
        "voyage_days": _voyage_days(tier, manifest),
        "founder_strains": _founders(tier, manifest),
    }
    for key, _tag, _param, _field in _RATE_AXES:
        source_key = _RATE_AXIS_ALIASES.get(key, key)
        axes[key] = _axis(
            tier,
            key if key in tier else source_key,
        )
    axes["surveillance"] = tuple(
        str(s) for s in (tier.get("surveillance_strategies") or ["syndromic"])
    )
    axes["seeds"] = tuple(int(s) for s in tier["seeds"])
    return axes


def tier_run_count(manifest: Mapping[str, Any], tier: Mapping[str, Any]) -> int:
    """Arithmetic run count for one ``vs*`` tier."""
    count = 1
    for values in tier_axes(manifest, tier).values():
        count *= len(values)
    return count


def _rate_tag(prefix: str, value: float) -> str:
    text = f"{float(value):g}".replace(".", "p").replace("-", "m")
    return f"{prefix}{text}"


def strip_incubation(profile: Mapping[str, Any]) -> dict[str, Any]:
    """The profile as it was before the incubation block existed (#290)."""
    return {key: value for key, value in profile.items() if key != "incubation"}


def fixed_onset_profile(bundle: str, pathogen_id: str) -> dict[str, Any]:
    """Full profile for the fixed-onset arm, with its incubation block removed."""
    profiles = load_pathogen_bundle(
        os.path.join(REPO_ROOT, BUNDLE_DIR, f"{bundle}.json"),
    )
    profile = profiles.get(pathogen_id)
    if profile is None:
        raise VariantManifestError(
            f"bundle {bundle!r} has no profile for {pathogen_id!r}",
        )
    if "incubation" not in profile:
        raise VariantManifestError(
            f"{pathogen_id} carries no incubation block, so the fixed_onset arm "
            "would be a silent no-op rather than a control",
        )
    return strip_incubation(profile)


def _strain_evolution_patch(cell: Mapping[str, Any]) -> dict[str, float]:
    patch: dict[str, float] = {}
    for key, _tag, _param, field in _RATE_AXES:
        value = cell[key]
        if value is not None:
            patch[field] = float(value)
    return patch


def _pathogen_overrides(
    *,
    base_overrides: Mapping[str, Any] | None,
    bundle: str,
    pathogen_id: str,
    arm: str,
    dose_adjustment: float,
    index_axis: IndexCaseAxis,
    index_point: Any,
    cell: Mapping[str, Any],
) -> dict[str, Any]:
    over: dict[str, Any] = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in (base_overrides or {}).items()
    }
    if arm == ARM_FIXED_ONSET:
        over["add"] = [
            *(over.get("add") or []),
            fixed_onset_profile(bundle, pathogen_id),
        ]
    over = index_axis.pathogen_overrides(
        over, index_point, dose_adjustment=float(dose_adjustment),
    )
    patch = dict(over.get(pathogen_id) or {})
    strain_patch = _strain_evolution_patch(cell)
    if strain_patch:
        patch["strain_evolution"] = {
            **dict(patch.get("strain_evolution") or {}),
            **strain_patch,
        }
    over[pathogen_id] = patch
    return over


def _variant_config(
    manifest: Mapping[str, Any],
    founder_strains: int,
    clock: str,
) -> dict[str, Any]:
    defaults = manifest.get("defaults") or {}
    if "census_interval_hours" in defaults:
        census = int(defaults["census_interval_hours"])
    else:
        if "census_interval_epochs" in defaults:
            warnings.warn(
                "census_interval_epochs is deprecated; "
                "use census_interval_hours",
                DeprecationWarning,
                stacklevel=2,
            )
        census = int(defaults.get("census_interval_epochs", 1))
    return {
        "variant_surveillance": {
            "enabled": True,
            "founder_strains_per_pathogen": int(founder_strains),
            "census_interval_hours": census,
        },
        "natural_history_clock": clock,
    }


def wastewater_binding(
    manifest: Mapping[str, Any],
    pathogen: str,
    pathogen_id: str,
    surveillance_cfg: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Point an enabled wastewater channel at this tier's pathogen.

    The shipped ``wastewater_surveillance`` block names norovirus, so a SARS-CoV-2
    or Federation tier that enabled the channel without rebinding it would sample
    a tank with no shedders and report a null result as an operational one.
    """
    block = (surveillance_cfg or {}).get("wastewater_surveillance") or {}
    if not block.get("enabled"):
        return None
    cfg = (manifest.get("pathogen_configs") or {}).get(pathogen) or {}
    label = str(cfg.get("wastewater_label", pathogen))
    return {
        "wastewater_surveillance": {"pathogen": label, "pathogen_id": pathogen_id},
    }


def _run_id(
    *,
    short: str,
    tier: Mapping[str, Any],
    regime: str,
    clock: str,
    arm: str,
    pathogen: str,
    cell: Mapping[str, Any],
    index_tags: Sequence[str] = (),
) -> str:
    parts = [
        short,
        regime,
        _CLOCK_TAGS[clock],
        _ARM_TAGS[arm],
        pathogen,
        str(cell["platform"]),
        f"d{int(cell['voyage_days'])}",
        f"f{int(cell['founder_strains'])}",
        *index_tags,
    ]
    for key, tag, _param, _field in _RATE_AXES:
        source_key = _RATE_AXIS_ALIASES.get(key, key)
        if (key in tier or source_key in tier) and cell[key] is not None:
            parts.append(_rate_tag(tag, cell[key]))
    parts.append(str(cell["surveillance"]))
    parts.append(f"s{int(cell['seeds'])}")
    return "_".join(parts)


def _cell_parameters(cell: Mapping[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "voyage_days": int(cell["voyage_days"]),
        "founder_strains": int(cell["founder_strains"]),
    }
    for key, _tag, param, _field in _RATE_AXES:
        if cell[key] is not None:
            params[param] = float(cell[key])
    return params


def iter_variant_runs(
    *,
    manifest: Mapping[str, Any],
    tier: Mapping[str, Any],
    tier_id: str,
    surv_cfgs: Mapping[str, Any],
    platform_override: str | None,
    num_agents_override: int | None,
    epochs_override: int | None,
    get_pathogen_config: Any,
    merge_cfg: Any,
    platform_num_agents: Any,
    default_agents: int,
    yield_run: Any,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(run_id, picard_spec)`` for one Paper 3 ``vs*`` tier."""
    clock = manifest_clock(manifest)
    arm = incubation_arm(manifest, tier)
    regime = tier_regime(tier)
    pathogen = str(tier["pathogen"])
    bundle, pathogen_id, base_overrides = get_pathogen_config(manifest, pathogen)
    defaults = manifest.get("defaults") or {}
    dose = float(tier.get("dose_adjustment", defaults["dose_adjustment"]))
    index_axis = IndexCaseAxis.for_tier(
        tier, pathogen_id, defaults=defaults, legacy_default=None,
    )
    short = tier_id.split("_", 1)[0]
    axes = tier_axes(manifest, tier, platform_override=platform_override)
    keys = tuple(axes)
    for point, combo in product(index_axis.points, product(*axes.values())):
        cell = dict(zip(keys, combo))
        epochs = epochs_override or epochs_for_days(manifest, cell["voyage_days"])
        run_id = _run_id(
            short=short, tier=tier, regime=regime, clock=clock, arm=arm,
            pathogen=pathogen, cell=cell, index_tags=index_axis.tags(point),
        )
        yield yield_run(
            run_id,
            bundle=bundle,
            pathogen_overrides=_pathogen_overrides(
                base_overrides=base_overrides,
                bundle=bundle,
                pathogen_id=pathogen_id,
                arm=arm,
                dose_adjustment=dose,
                index_axis=index_axis,
                index_point=point,
                cell=cell,
            ),
            config_overrides=merge_cfg(
                surv_cfgs.get(cell["surveillance"]),
                _variant_config(manifest, cell["founder_strains"], clock),
                wastewater_binding(
                    manifest,
                    pathogen,
                    pathogen_id,
                    surv_cfgs.get(cell["surveillance"]),
                ),
            ),
            seed=int(cell["seeds"]),
            num_agents=platform_num_agents(
                cell["platform"],
                num_agents_override=num_agents_override,
                tier=tier,
                default_agents=default_agents,
            ),
            pathogen=pathogen,
            platform_id=cell["platform"],
            epochs=epochs,
            surveillance=cell["surveillance"],
            regime=regime,
            incubation_arm=arm,
            dose_adjustment=dose,
            **index_axis.factors(point),
            **_cell_parameters(cell),
        )
