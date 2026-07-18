"""
engines.contamx_transport
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional transport engine that uses the **real NIST ContamX solver** to
compute the inter-zone airflow field, then applies Crusher's own
contaminant mass-balance on top of it.

Design (see ``docs/CONTAM_INTEROP.md``):

    ContamX  →  per-path volumetric airflows (the "airflow field")
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

from engines.contamx_runner import (
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.py_contam_bridge import (
    ContamAirflowPath,
    ContamTransportEngine,
)

_FLOW_EPSILON_M3H = 1e-9
_PATH_MAP_JSON = "path_map.json"
_PLATFORM_PRJ = "platform.prj"


class ContamXTransportEngine(ContamTransportEngine):
    """Transport engine whose airflow field comes from the ContamX solver."""

    def __init__(
        self,
        spatial_layout: dict[str, Any],
        path_map: list[tuple[str, str, bool]],
        path_flows_m3h: dict[int, float],
        filter_efficiency: float = 0.50,
        natural_decay_rate: float = 0.10,
    ) -> None:
        self.filter_efficiency = filter_efficiency
        self.natural_decay_rate = natural_decay_rate
        self.zone_nodes = {}
        self.airflow_paths = []

        self._build_zone_nodes(spatial_layout)
        self._build_airflow_paths_from_field(path_map, path_flows_m3h)

    def _build_airflow_paths_from_field(
        self,
        path_map: list[tuple[str, str, bool]],
        path_flows_m3h: dict[int, float],
    ) -> None:
        """Build directed airflow paths from the ContamX flow field.

        Skips ambient / AHS-phantom endpoints that are not Crusher zone nodes.
        """
        known = set(self.zone_nodes)
        for idx, (from_zone, to_zone, is_ducted) in enumerate(path_map):
            path_nr = idx + 1
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

    @classmethod
    def from_flow_field(
        cls,
        spatial_layout: dict[str, Any],
        path_map: list[tuple[str, str, bool]],
        path_flows_m3h: dict[int, float],
        **kwargs: float,
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


def _path_map_from_airflow(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> list[tuple[str, str, bool]]:
    """Build full ContamX path order matching ContamW 3.4 export."""
    from tools.contamw34_prj import build_path_map, path_map_full_order

    return path_map_full_order(build_path_map(spatial_layout, air_flow_paths))


def _platform_id_from_spatial(spatial: dict[str, Any]) -> str:
    return str(spatial.get("platform", "")).strip()


def resolve_contam_prj_path(
    repo_root: str,
    cfg: dict[str, Any],
    spatial: dict[str, Any],
) -> str | None:
    """Resolve a ContamW ``.prj`` path, or ``None`` if none is configured/bundled."""
    contamx_cfg = cfg.get("hvac", {}).get("contamx", {}) or {}
    explicit = contamx_cfg.get("prj_path") or ""
    if explicit:
        from simulation_utils.paths import resolve_repo_path

        full = resolve_repo_path(repo_root, explicit)
        if os.path.isfile(full):
            return full
        raise ContamXUnavailable(f"Configured ContamX prj_path not found: {explicit}")

    platform = _platform_id_from_spatial(spatial)
    if platform:
        bundled = os.path.join(
            repo_root, "data", "platforms", platform, "contam", _PLATFORM_PRJ,
        )
        if os.path.isfile(bundled):
            return bundled
    return None


def _load_path_map_beside_prj(prj_path: str) -> list[tuple[str, str, bool]] | None:
    directory = os.path.dirname(prj_path)
    candidates = [
        os.path.join(directory, _PATH_MAP_JSON),
        os.path.splitext(prj_path)[0] + ".path_map.json",
    ]
    for cand in candidates:
        if not os.path.isfile(cand):
            continue
        with open(cand, encoding="utf-8") as fh:
            entries = json.load(fh)
        if isinstance(entries, list) and entries:
            return _path_map_from_entries(entries)
    return None


def build_contamx_engine(
    repo_root: str,
    cfg: dict[str, Any],
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
    filter_eff = hvac_cfg.get("filter_efficiency", 0.50)
    decay_rate = hvac_cfg.get("natural_decay_rate", 0.10)

    prj_path = resolve_contam_prj_path(repo_root, cfg, spatial)
    path_map: list[tuple[str, str, bool]] | None = None
    tmp_ctx = None

    try:
        if prj_path is None:
            # Last resort: export ContamW 3.4 to a temp dir
            prj_text, entries = export_prj_with_path_map(spatial, airflow)
            tmp_ctx = tempfile.TemporaryDirectory(prefix="crusher_contamx_")
            tmp_dir = tmp_ctx.__enter__()
            prj_path = os.path.join(tmp_dir, _PLATFORM_PRJ)
            with open(prj_path, "w", encoding="utf-8") as fh:
                fh.write(prj_text)
            map_path = os.path.join(tmp_dir, _PATH_MAP_JSON)
            with open(map_path, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, indent=2)
            path_map = _path_map_from_entries(entries)
        else:
            path_map = _load_path_map_beside_prj(prj_path)
            if path_map is None:
                path_map = _path_map_from_airflow(spatial, airflow)

        sim_path = run_contamx(prj_path, binary, config=cfg)
        sim = SimResults(sim_path)
        flows = sim.path_volumetric_flow_m3h()
    finally:
        if tmp_ctx is not None:
            tmp_ctx.__exit__(None, None, None)

    return ContamXTransportEngine(
        spatial_layout=spatial,
        path_map=path_map,
        path_flows_m3h=flows,
        filter_efficiency=filter_eff,
        natural_decay_rate=decay_rate,
    )
