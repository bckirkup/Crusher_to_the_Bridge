"""Compact provenance flags for the campaign archive's ``summary.json``.

Two silent-defect classes this block exists to make visible at readout
rather than at review:

- **shadowed** — an override key was written that the engine never
  resolves, because a preferred key shadows it. The withdrawn
  ``innate_nonsusceptible_fraction`` write is the case that motivated this
  (NORO-SUSCEPT-04): it archived as a swept axis while the profile's
  ``secretor_negative_fraction`` answered every resolution.
- **window** — the run's effective value for a factor with a declared
  sourced interval (the bounded screen's ``Factor`` tables) sits outside
  it. Out-of-window is not necessarily wrong — a deliberately extreme arm
  should flag — but the archive must say when a run stood on a value no
  source supports, because unsourced tuning hides exactly there.

Plus ``active``: the flattened override paths the spec declared, so the
archive records which knobs a run moved without a reader having to diff
against the bundle. And ``gates_off``: every ``enabled: false`` / inert
``mode`` gate found in the merged config, so an archive can no longer
read as running a mechanism that was switched off — the inverse of the
shadowed-alias defect, where the off state is the truth an arm claims
to exercise.

The window tables are keyed by pathogen id and drawn only from declared
sourced intervals — a pathogen with no declared table flags nothing
rather than inventing a window. Run-target factors are resolved at the
config path the table declares; a factor whose path does not resolve on
this run is skipped, not flagged.
"""
from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence

from telemetry_buffer.observation_model.bounded_screen import (
    EXPEDITION_SENSITIVITY_FACTORS,
    NOROVIRUS_FACTORS,
    Factor,
)

# Preferred profile key -> alias spellings that address the same
# resolution slot. An override carrying an alias while the preferred key
# resolves in the merged profile reaches no host.
_SHADOWED_BY: dict[str, tuple[str, ...]] = {
    "secretor_negative_fraction": ("innate_nonsusceptible_fraction",),
}

# Sourced-interval tables keyed by pathogen_id. Only factor sets declared
# in bounded_screen are trusted here.
_PATHOGEN_FACTOR_TABLES: dict[str, tuple[Factor, ...]] = {
    "norwalk_gi": NOROVIRUS_FACTORS + EXPEDITION_SENSITIVITY_FACTORS,
}

# Mode spellings that mean the pathway is inert. A mode set to one of
# these is a gate in the off position for this run; other mode values
# select a mechanism and are not flagged.
_INERT_MODES = frozenset({"off", "none"})

# Gates whose inert value lives in an engine default rather than the
# shipped config: the key is absent from the merged cfg when off, so the
# structural walk never sees it. path -> the inert value an explicit set
# would also carry.
_CODE_DEFAULT_GATES: dict[str, Any] = {
    "transmission.blackwater_plumbing": False,
    "observation.wastewater_assay_mode": "none",
}


def _resolve_path(block: Any, path: Sequence[Any]) -> Any:
    """Read a Factor path against a profile or config block, or None."""
    cur = block
    for elem in path:
        if isinstance(elem, int):
            if not isinstance(cur, (list, tuple)) or len(cur) <= elem:
                return None
            cur = cur[elem]
        else:
            if not isinstance(cur, Mapping) or elem not in cur:
                return None
            cur = cur[elem]
    return cur


def _leaf_paths(block: Mapping[str, Any], prefix: str) -> Iterator[str]:
    """Flatten an override tree to dotted leaf paths (lists are leaves)."""
    for key, value in sorted(block.items()):
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            yield from _leaf_paths(value, path)
        else:
            yield path


def _active_override_paths(spec: Mapping[str, Any]) -> list[str]:
    """Every override path the spec declares, ``cfg.``-prefixed for config."""
    out = [
        f"cfg.{p}"
        for p in _leaf_paths(spec.get("config_overrides") or {}, "")
    ]
    for pathogen_id, patch in sorted(
        (spec.get("pathogen_overrides") or {}).items()
    ):
        if isinstance(patch, Mapping):
            out.extend(
                f"pathogen.{pathogen_id}.{p}"
                for p in _leaf_paths(patch, "")
            )
        else:
            out.append(f"pathogen.{pathogen_id}")
    return out


def _gate_is_off(key: str, value: Any) -> bool:
    """A leaf is an off gate when it is ``enabled: false`` or a mode
    spelled ``off``/``none``."""
    if key == "enabled" and value is False:
        return True
    return (
        (key == "mode" or key.endswith("_mode"))
        and str(value).lower() in _INERT_MODES
    )


def _code_default_gates_off(block: Mapping[str, Any]) -> Iterator[str]:
    """Inert gates set by engine defaults — absent from the merged cfg."""
    for path, inert in _CODE_DEFAULT_GATES.items():
        value = _resolve_path(block, tuple(path.split(".")))
        if value is None or value == inert:
            yield path


def _gates_off(block: Mapping[str, Any], prefix: str) -> Iterator[str]:
    """Dotted paths of inert feature gates in the merged config.

    Nested blocks are walked; only the leaf is listed. The root call also
    sweeps the code-defaulted gates an absent key implies.
    """
    for key, value in sorted(block.items()):
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            yield from _gates_off(value, path)
        elif _gate_is_off(key, value):
            yield path
    if not prefix:
        yield from _code_default_gates_off(block)


def _shadowed_keys(
    spec: Mapping[str, Any],
    pathogen_profiles: Mapping[str, Any],
) -> list[str]:
    """Override paths written to a slot a preferred key already resolves."""
    out: list[str] = []
    for pathogen_id, patch in sorted(
        (spec.get("pathogen_overrides") or {}).items()
    ):
        if not isinstance(patch, Mapping):
            continue
        profile = pathogen_profiles.get(pathogen_id) or {}
        out.extend(
            f"{pathogen_id}.{alias}"
            for alias in _shadowed_aliases(patch, profile)
        )
    return out


def _shadowed_aliases(
    patch: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> Iterator[str]:
    """Alias keys in ``patch`` whose preferred key resolves in ``profile``."""
    for preferred, aliases in _SHADOWED_BY.items():
        if preferred not in profile:
            continue
        for alias in aliases:
            if alias in patch:
                yield alias


def _window_breaches(
    cfg: Mapping[str, Any],
    pathogen_profiles: Mapping[str, Any],
) -> dict[str, list[float]]:
    """Effective values outside their factor table's sourced interval."""
    out: dict[str, list[float]] = {}
    for pathogen_id, factors in sorted(_PATHOGEN_FACTOR_TABLES.items()):
        profile = pathogen_profiles.get(pathogen_id)
        if not isinstance(profile, Mapping):
            continue
        for factor in factors:
            val = _factor_value(factor, cfg, profile)
            if val is not None and not factor.low <= val <= factor.high:
                out[f"{pathogen_id}.{factor.name}"] = [
                    val,
                    factor.low,
                    factor.high,
                ]
    return out


def _factor_value(
    factor: Factor,
    cfg: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> float | None:
    """The effective float at a factor's path on this run, or None."""
    block = cfg if factor.target == "run" else profile
    value = _resolve_path(block, factor.path)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def provenance_flags(
    spec: Mapping[str, Any],
    cfg: Mapping[str, Any],
    pathogen_profiles: Mapping[str, Any],
) -> dict[str, Any]:
    """Compact flag block for ``summary.json``.

    ``spec`` is the run spec (declared overrides), ``cfg`` the merged run
    config, ``pathogen_profiles`` the merged profiles — i.e. the values
    the engine actually ran with. Empty sub-keys are omitted.
    """
    flags: dict[str, Any] = {}
    active = _active_override_paths(spec)
    if active:
        flags["active"] = active
    shadowed = _shadowed_keys(spec, pathogen_profiles)
    if shadowed:
        flags["shadowed"] = shadowed
    window = _window_breaches(cfg, pathogen_profiles)
    if window:
        flags["window"] = window
    gates = sorted(set(_gates_off(cfg, "")))
    if gates:
        flags["gates_off"] = gates
    return flags
