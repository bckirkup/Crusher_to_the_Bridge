"""
engines.contamx_transport
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional transport engine that uses the **real NIST ContamX solver** to
compute the inter-zone airflow field, then applies Crusher's own
contaminant mass-balance on top of it.

Design (see ``docs/CONTAM_INTEROP.md``):

    ContamX  →  per-path volumetric airflows (the "airflow field")
    Bridge   →  real↔real paths + AHS→room↔room synthesis
    Crusher  →  discrete-time pathogen mass balance on those flows

``ContamXTransportEngine`` exposes the same ``transport_step`` /
``get_transport_summary`` interface as the native engine.

PRJ resolution order for ``build_contamx_engine``:

1. ``hvac.contamx.prj_path`` (explicit config)
2. Platform-bundled ``data/platforms/<id>/contam/platform.prj``
3. Last-resort temporary ContamW 3.4 export from JSON

A matching ``path_map.json`` beside the PRJ aligns ContamX path indices
with Crusher zone pairs (adjacency + cross-zone + AHS bookkeeping paths).
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from engines.contamx_ahs_bridge import synthesize_ahs_recirculation_paths
from engines.contamx_runner import (
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.py_contam_bridge import (
    ContamAirflowPath,
    ContamTransportEngine,
    is_plenum_zone,
)
from engines.sim_clock import SimClock
from simulation_utils.paths import (
    is_path_under_base,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)

_FLOW_EPSILON_M3H = 1e-9
_PATH_MAP_JSON = "path_map.json"
_PLATFORM_PRJ = "platform.prj"


class ContamXTransportEngine(ContamTransportEngine):
    """Transport engine whose airflow field comes from the ContamX solver."""

    def __init__(
        self,
        spatial_layout: dict[str, Any],
        path_map: list[tuple[str, str, bool]] | list[dict[str, Any]],
        path_flows_m3h: dict[int, float],
        filter_efficiency: float = 0.50,
        natural_decay_rate: float = 0.10,
        *,
        path_map_entries: list[dict[str, Any]] | None = None,
        oa_fraction: float = 0.2,
        clock: SimClock | None = None,
    ) -> None:
        super().__init__(
            spatial_layout,
            {},
            filter_efficiency=filter_efficiency,
            natural_decay_rate=natural_decay_rate,
            clock=clock,
        )
        self.filter_efficiency = filter_efficiency
        self.natural_decay_rate = natural_decay_rate
        self.zone_nodes = {}
        self.airflow_paths = []
        self._oa_fraction = float(oa_fraction)

        self._build_zone_nodes(spatial_layout)
        entries = path_map_entries
        if entries is None and path_map and isinstance(path_map[0], dict):
            entries = path_map  # type: ignore[assignment]
        if entries is None:
            entries = [
                {
                    "path_nr": i + 1,
                    "from_zone": row[0],
                    "to_zone": row[1],
                    "is_hvac_ducted": bool(row[2]),
                    "kind": "unknown",
                    "ahs_nr": 0,
                }
                for i, row in enumerate(path_map)  # type: ignore[arg-type]
            ]
        self._build_airflow_paths_from_field(entries, path_flows_m3h)

    def _build_airflow_paths_from_field(
        self,
        path_map_entries: list[dict[str, Any]],
        path_flows_m3h: dict[int, float],
    ) -> None:
        """Build directed airflow paths from the ContamX flow field.

        Includes:
          - Real↔real Contam paths (adjacency, cross-zone fans) with SIM flow
          - Synthesized AHS recirculation (room↔room) from supply/return/recirc
        """
        known = set(self.zone_nodes)
        ordered = sorted(path_map_entries, key=lambda e: int(e["path_nr"]))
        for entry in ordered:
            path_nr = int(entry["path_nr"])
            from_zone = entry["from_zone"]
            to_zone = entry["to_zone"]
            is_ducted = bool(entry.get("is_hvac_ducted", False))
            kind = str(entry.get("kind", ""))
            # AHS phantom / ambient paths are bridged separately
            if kind.startswith("ahs_") or kind == "envelope_leak":
                continue
            flow = path_flows_m3h.get(path_nr, 0.0)
            if abs(flow) < _FLOW_EPSILON_M3H:
                continue
            src, dst = (from_zone, to_zone) if flow > 0 else (to_zone, from_zone)
            if src not in known or dst not in known:
                continue
            self.airflow_paths.append(ContamAirflowPath(
                path_id=f"contamx_{path_nr}_{src}_{dst}",
                from_zone=src,
                to_zone=dst,
                flow_rate_m3h=abs(flow),
                path_type="contamx_path",
                is_hvac_ducted=is_ducted,
            ))

        ahs_paths = synthesize_ahs_recirculation_paths(
            ordered, path_flows_m3h, known,
            oa_fraction=self._oa_fraction,
        )
        for path in ahs_paths:
            for zid in (path.from_zone, path.to_zone):
                if is_plenum_zone(zid):
                    self._ensure_plenum_node(zid)
        self.airflow_paths.extend(ahs_paths)

    @classmethod
    def from_flow_field(
        cls,
        spatial_layout: dict[str, Any],
        path_map: list[tuple[str, str, bool]] | list[dict[str, Any]],
        path_flows_m3h: dict[int, float],
        **kwargs: Any,
    ) -> ContamXTransportEngine:
        """Construct directly from a decoded airflow field (test/offline)."""
        return cls(spatial_layout, path_map, path_flows_m3h, **kwargs)


def _path_map_from_entries(
    entries: list[dict[str, Any]],
) -> list[tuple[str, str, bool]]:
    """Convert path_map.json entries to ContamX index order (1..N)."""
    ordered = sorted(entries, key=lambda e: int(e["path_nr"]))
    return [
        (e["from_zone"], e["to_zone"], bool(e.get("is_hvac_ducted", False)))
        for e in ordered
    ]


def _normalize_path_map_entries(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return path_map entries sorted by ContamX path number."""
    return sorted(entries, key=lambda e: int(e["path_nr"]))


def _path_map_entries_from_airflow(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build full ContamX path_map entries matching ContamW 3.4 export."""
    from tools.contamw34_prj import build_path_map

    return _normalize_path_map_entries(
        build_path_map(spatial_layout, air_flow_paths)
    )


def _path_map_from_airflow(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> list[tuple[str, str, bool]]:
    """Build full ContamX path order matching ContamW 3.4 export."""
    from tools.contamw34_prj import path_map_full_order

    return path_map_full_order(
        _path_map_entries_from_airflow(spatial_layout, air_flow_paths)
    )


def _platform_id_from_spatial(spatial: dict[str, Any]) -> str:
    """Return a validated platform id path component (rejects traversal)."""
    raw = str(spatial.get("platform", "")).strip()
    if not raw:
        return ""
    return validate_path_component(raw, label="platform id")


def resolve_contam_prj_path(
    repo_root: str,
    cfg: dict[str, Any],
    spatial: dict[str, Any],
) -> str | None:
    """Resolve a ContamW ``.prj`` path, or ``None`` if none is configured/bundled.

    All resolved paths are containment-checked under *repo_root* (Sonar
    pythonsecurity:S6549 / S2083).
    """
    contamx_cfg = cfg.get("hvac", {}).get("contamx", {}) or {}
    explicit = contamx_cfg.get("prj_path") or ""
    if explicit:
        full = resolve_repo_path(repo_root, explicit)
        if os.path.isfile(full):
            return full
        raise ContamXUnavailable(f"Configured ContamX prj_path not found: {explicit}")

    try:
        platform = _platform_id_from_spatial(spatial)
    except ValueError as exc:
        raise ContamXUnavailable(f"Invalid platform id in spatial layout: {exc}") from exc
    if not platform:
        return None

    # Constant relative segments only; platform already path-component validated.
    rel = os.path.join("data", "platforms", platform, "contam", _PLATFORM_PRJ)
    bundled = resolve_repo_path(repo_root, rel)
    if os.path.isfile(bundled):
        return bundled
    return None


def _load_path_map_entries_beside_prj(
    prj_path: str,
    *,
    allowed_roots: tuple[str, ...],
) -> list[dict[str, Any]] | None:
    """Load ``path_map.json`` beside a ContamW PRJ with root containment checks."""
    directory = os.path.dirname(os.path.realpath(prj_path))
    if not any(is_path_under_base(root, directory) for root in allowed_roots):
        return None

    safe_map_name = validate_path_component(_PATH_MAP_JSON, label="path map file")
    candidates = [
        os.path.join(directory, safe_map_name),
        os.path.splitext(os.path.realpath(prj_path))[0] + ".path_map.json",
    ]
    for cand in candidates:
        try:
            with validated_open(
                cand, "r", allowed_roots=allowed_roots, encoding="utf-8",
            ) as fh:
                entries = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(entries, list) and entries:
            return _normalize_path_map_entries(entries)
    return None


def _load_path_map_beside_prj(
    prj_path: str,
    *,
    allowed_roots: tuple[str, ...],
) -> list[tuple[str, str, bool]] | None:
    """Load path_map tuples beside a ContamW PRJ (legacy helper)."""
    entries = _load_path_map_entries_beside_prj(
        prj_path, allowed_roots=allowed_roots,
    )
    if entries is None:
        return None
    return _path_map_from_entries(entries)


def build_contamx_engine(
    repo_root: str,
    cfg: dict[str, Any],
    *,
    clock: SimClock | None = None,
) -> ContamXTransportEngine:
    """Build a ContamX-backed transport engine for the configured platform.

    Raises :class:`ContamXUnavailable` on any missing prerequisite so the
    caller can fall back to the native engine.
    """
    from engines.py_contam_bridge import load_air_flow_paths, load_spatial_layout
    from tools.contam_prj_bridge import export_prj_with_path_map

    binary = find_contamx(cfg)
    if binary is None:
        raise ContamXUnavailable(
            "ContamX binary not found; falling back to native engine."
        )

    spatial = load_spatial_layout(repo_root, cfg)
    airflow = load_air_flow_paths(repo_root, cfg)
    if not spatial or not airflow:
        raise ContamXUnavailable("Platform layout files not found.")

    hvac_cfg = cfg.get("hvac", {})
    # ContamX reloads airflow from disk; re-apply the campaign override here so
    # hvac.oa_fraction is not silently dropped (native path mutates its copy in
    # build_transport_engine before _build_native_engine).
    if "oa_fraction" in hvac_cfg:
        airflow = {**airflow, "oa_fraction": float(hvac_cfg["oa_fraction"])}
    filter_eff = hvac_cfg.get("filter_efficiency", 0.50)
    decay_rate = hvac_cfg.get("natural_decay_rate", 0.10)

    prj_path = resolve_contam_prj_path(repo_root, cfg, spatial)
    entries: list[dict[str, Any]] | None = None
    tmp_ctx = None
    allowed_roots: tuple[str, ...] = (repo_root,)

    try:
        if prj_path is None:
            # Fiction bootstrap last resort: synthesize ContamW 3.4 from JSON
            # when no authentic/bundled .prj is available.
            prj_text, exported = export_prj_with_path_map(spatial, airflow)
            tmp_ctx = tempfile.TemporaryDirectory(prefix="crusher_contamx_")
            tmp_dir = tmp_ctx.__enter__()
            allowed_roots = (repo_root, tmp_dir)
            safe_prj = validate_path_component(_PLATFORM_PRJ, label="prj file")
            safe_map = validate_path_component(_PATH_MAP_JSON, label="path map file")
            prj_path = os.path.join(tmp_dir, safe_prj)
            map_path = os.path.join(tmp_dir, safe_map)
            with validated_open(
                prj_path, "w", allowed_roots=allowed_roots, encoding="utf-8",
            ) as fh:
                fh.write(prj_text)
            with validated_open(
                map_path, "w", allowed_roots=allowed_roots, encoding="utf-8",
            ) as fh:
                json.dump(exported, fh, indent=2)
            entries = _normalize_path_map_entries(exported)
        else:
            entries = _load_path_map_entries_beside_prj(
                prj_path, allowed_roots=allowed_roots,
            )
            if entries is None:
                # Primary Path A contract: derive path_map from the PRJ itself
                # (never rebuild export order from JSON — that only matches
                # fiction bootstrap bundles).
                from tools.contamw34_prj import path_map_from_prj

                with validated_open(
                    prj_path, "r", allowed_roots=allowed_roots, encoding="utf-8",
                ) as fh:
                    entries = path_map_from_prj(fh.read())

        sim_path = run_contamx(prj_path, binary, config=cfg)
        sim = SimResults(sim_path, allowed_roots=allowed_roots)
        flows = sim.path_volumetric_flow_m3h()
    finally:
        if tmp_ctx is not None:
            tmp_ctx.__exit__(None, None, None)

    return ContamXTransportEngine(
        spatial_layout=spatial,
        path_map=entries,
        path_flows_m3h=flows,
        filter_efficiency=filter_eff,
        natural_decay_rate=decay_rate,
        path_map_entries=entries,
        oa_fraction=float(airflow.get("oa_fraction", 0.2)),
        clock=clock,
    )
