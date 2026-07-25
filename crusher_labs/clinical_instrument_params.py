"""
Load and resolve JSON clinical instrument / panel / impression parameters.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from simulation_utils.paths import resolve_repo_path, validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_REL = "data/config/clinical_instrument_params.json"


@dataclass(frozen=True)
class ResolvedInstrumentParams:
    """Resolved per-pathogen assay parameters."""

    covers_pathogen: bool
    sensitivity: float = 0.0
    specificity: float = 0.0
    sensitivity_peak: float = 0.0
    sensitivity_early: float = 0.0
    sensitivity_late: float = 0.0
    sensitivity_by_day: dict[str, float] | None = None
    outbreak_awareness_sensitivity_bonus: float = 0.0
    raw: dict[str, Any] | None = None


def load_clinical_instrument_params(
    path: str | None = None,
    *,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Load clinical instrument parameter JSON."""
    root = repo_root or REPO_ROOT
    rel = path or DEFAULT_CONFIG_REL
    config_path = resolve_repo_path(root, rel)
    with validated_open(config_path, "r", allowed_roots=(root,), encoding="utf-8") as fh:
        return json.load(fh)


def clinical_instruments_config_path(cfg: dict[str, Any] | None) -> str:
    block = (cfg or {}).get("clinical_instruments") or {}
    return str(block.get("config_path", DEFAULT_CONFIG_REL))


def active_pathogen_ids(agent: dict[str, Any]) -> list[str]:
    """Return pathogen IDs with an active infection on *agent*."""
    infections = agent.get("pathogen_infections") or {}
    active: list[str] = []
    for pid, info in infections.items():
        if not isinstance(info, dict):
            continue
        if str(info.get("status", "")).upper() == "INFECTED":
            active.append(str(pid))
    return active


def primary_pathogen_id(agent: dict[str, Any]) -> str | None:
    active = active_pathogen_ids(agent)
    return active[0] if active else None


def resolve_instrument_params(
    params: dict[str, Any],
    instrument_key: str,
    pathogen_id: str | None,
) -> ResolvedInstrumentParams:
    """Resolve instrument defaults + optional by_pathogen override."""
    instruments = params.get("instruments") or {}
    block = instruments.get(instrument_key) or {}
    merged: dict[str, Any] = dict(block.get("default") or {})
    if pathogen_id:
        by_path = (block.get("by_pathogen") or {}).get(pathogen_id)
        if isinstance(by_path, dict):
            merged.update(by_path)
    covers = bool(merged.get("covers_pathogen", True))
    sens_by_day = merged.get("sensitivity_by_day")
    return ResolvedInstrumentParams(
        covers_pathogen=covers,
        sensitivity=float(merged.get("sensitivity", merged.get("sensitivity_peak", 0.0)) or 0.0),
        specificity=float(merged.get("specificity", 0.0) or 0.0),
        sensitivity_peak=float(merged.get("sensitivity_peak", merged.get("sensitivity", 0.0)) or 0.0),
        sensitivity_early=float(merged.get("sensitivity_early", merged.get("sensitivity_peak", 0.0)) or 0.0),
        sensitivity_late=float(merged.get("sensitivity_late", merged.get("sensitivity_peak", 0.0)) or 0.0),
        sensitivity_by_day=(
            {str(k): float(v) for k, v in sens_by_day.items()}
            if isinstance(sens_by_day, dict)
            else None
        ),
        outbreak_awareness_sensitivity_bonus=float(
            merged.get("outbreak_awareness_sensitivity_bonus", 0.0) or 0.0,
        ),
        raw=merged,
    )


def resolve_panel_params(
    params: dict[str, Any],
    panel_id: str,
    pathogen_id: str,
) -> ResolvedInstrumentParams | None:
    """Return multiplex panel params for *pathogen_id*, or None if off-panel."""
    panel = (params.get("panels") or {}).get(panel_id) or {}
    pathogens = panel.get("pathogens") or {}
    row = pathogens.get(pathogen_id)
    if not isinstance(row, dict):
        return None
    return ResolvedInstrumentParams(
        covers_pathogen=True,
        sensitivity=float(row.get("sensitivity", 0.0)),
        specificity=float(row.get("specificity", 0.0)),
        sensitivity_peak=float(row.get("sensitivity", 0.0)),
        raw=row,
    )


def panels_for_syndromes(
    params: dict[str, Any],
    syndromes: list[str],
) -> list[str]:
    """Union of multiplex panel IDs routed from observed syndromes."""
    routing = params.get("syndrome_routing") or {}
    ordered: list[str] = []
    seen: set[str] = set()
    for syn in syndromes:
        entry = routing.get(syn) or {}
        for panel_id in entry.get("multiplex_panels") or []:
            if panel_id not in seen:
                seen.add(panel_id)
                ordered.append(str(panel_id))
    return ordered


def impression_pathogens_for_syndromes(
    params: dict[str, Any],
    syndromes: list[str],
) -> list[str]:
    routing = params.get("syndrome_routing") or {}
    ordered: list[str] = []
    seen: set[str] = set()
    for syn in syndromes:
        entry = routing.get(syn) or {}
        for pid in entry.get("clinical_impression_pathogens") or []:
            if pid not in seen:
                seen.add(pid)
                ordered.append(str(pid))
    return ordered


def expand_tier_tests_for_agent(
    params: dict[str, Any],
    tier_tests: list[str] | tuple[str, ...],
    agent: dict[str, Any],
    *,
    prefer_multiplex: bool = False,
) -> list[str]:
    """Expand abstract tier test keys into concrete ordered assay keys.

    ``clinical_multiplex_panel`` expands to one logical multiplex run (still one
    test key) but panel_id is chosen at run time. When no panel maps and the
    tier lists multiplex, keep the key so an uninformative result is emitted.

    When multiplex is preferred and panels map, multiplex is kept and RDT may
    still run if also listed. Clinical impression is appended when syndromes
    route impression pathogens and the key is present or no lab assay covers
    the agent's active infections.
    """
    syndromes = list(agent.get("observed_syndromes") or [])
    panels = panels_for_syndromes(params, syndromes)
    impression_pids = impression_pathogens_for_syndromes(params, syndromes)
    active = active_pathogen_ids(agent)
    out: list[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key not in seen:
            seen.add(key)
            out.append(key)

    for key in tier_tests:
        if key == "clinical_multiplex_panel":
            if prefer_multiplex or panels or not syndromes:
                _add("clinical_multiplex_panel")
            continue
        if key == "clinical_rdt":
            if prefer_multiplex and panels:
                continue
            _add("clinical_rdt")
            continue
        if key == "clinical_impression":
            if impression_pids:
                _add("clinical_impression")
            continue
        _add(key)

    def _multiplex_covers_any_active() -> bool:
        if not active or not panels:
            return False
        for panel_id in panels:
            panel = (params.get("panels") or {}).get(panel_id) or {}
            covered = set((panel.get("pathogens") or {}).keys())
            if any(pid in covered for pid in active):
                return True
        return False

    if prefer_multiplex and impression_pids and not _multiplex_covers_any_active():
        _add("clinical_impression")

    if (
        "clinical_rdt" in tier_tests
        and "clinical_multiplex_panel" not in tier_tests
        and impression_pids
        and "clinical_impression" not in out
    ):
        has_rdt_cover = False
        for pid in active:
            rp = resolve_instrument_params(params, "clinical_rdt", pid)
            if rp.covers_pathogen:
                has_rdt_cover = True
                break
        if not has_rdt_cover:
            _add("clinical_impression")

    return out


def impression_sensitivity_for_day(
    resolved: ResolvedInstrumentParams,
    days_since_symptom_onset: int,
    *,
    outbreak_aware: bool = False,
) -> float:
    """Stepwise day curve with optional outbreak awareness bonus."""
    curve = resolved.sensitivity_by_day or {}
    if not curve:
        base = resolved.sensitivity
    else:
        day = max(1, int(days_since_symptom_onset))
        # Keys are typically 1, 3, 5 — use highest key <= day, else lowest.
        numeric = sorted((int(k), float(v)) for k, v in curve.items())
        base = numeric[0][1]
        for threshold, value in numeric:
            if day >= threshold:
                base = value
            else:
                break
    if outbreak_aware:
        base = min(1.0, base + resolved.outbreak_awareness_sensitivity_bonus)
    return float(base)


def rdt_phase_sensitivity(
    resolved: ResolvedInstrumentParams,
    shedding_rate: float,
    *,
    early_max: float = 20.0,
    peak_max: float = 80.0,
) -> float:
    """Map shedding intensity to early/peak/late RDT sensitivity."""
    if shedding_rate <= early_max:
        return resolved.sensitivity_early
    if shedding_rate <= peak_max:
        return resolved.sensitivity_peak
    return resolved.sensitivity_late
