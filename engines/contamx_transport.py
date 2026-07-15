"""
engines.contamx_transport
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional transport engine that uses the **real NIST ContamX solver** to
compute the inter-zone airflow field, then applies Crusher's own
contaminant mass-balance on top of it.

Design (see ``docs/CONTAM_INTEROP.md`` §5):

    ContamX  →  per-path volumetric airflows (the "airflow field")
    Crusher  →  discrete-time pathogen mass balance on those flows

This keeps the contaminant semantics identical to the native
``ContamTransportEngine`` (so the two are directly comparable in the
benchmark harness) while swapping the *airflow physics* for the reference
NIST implementation.

``ContamXTransportEngine`` exposes the same ``transport_step`` /
``get_transport_summary`` interface as the native engine, so it is a
drop-in replacement selected via ``hvac.transport_engine`` in config.

The engine is **opt-in**. ``build_contamx_engine`` raises
:class:`~engines.contamx_runner.ContamXUnavailable` whenever the binary,
a valid project file, or results are missing, letting the caller fall back
to the native engine. Because the ContamX binary is not available in CI or
the offline build environment, the engine is unit-tested by injecting a
decoded airflow field (``from_flow_field``) rather than a live solver run.
"""

from __future__ import annotations

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


class ContamXTransportEngine(ContamTransportEngine):
    """Transport engine whose airflow field comes from the ContamX solver.

    Parameters
    ----------
    spatial_layout : dict
        Parsed ``spatial_layout.json`` (used for zone volumes/geometry).
    path_map : list of (from_zone, to_zone, is_hvac_ducted)
        Ordered airflow-path definitions. Index ``i`` corresponds to
        ContamX airflow-path number ``i + 1`` (the order the project file
        was exported in).
    path_flows_m3h : dict[int, float]
        ContamX-computed **signed** volumetric flow per path number
        (positive = ``from_zone`` → ``to_zone``).
    filter_efficiency, natural_decay_rate : float
        Same contaminant-side parameters as the native engine.
    """

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

        A positive ContamX flow keeps the ``from → to`` orientation; a
        negative flow is reversed so ``flow_rate_m3h`` is always the
        (non-negative) magnitude, matching the native engine's directed
        transfer convention.
        """
        for idx, (from_zone, to_zone, is_ducted) in enumerate(path_map):
            path_nr = idx + 1
            flow = path_flows_m3h.get(path_nr, 0.0)
            if flow == 0.0:
                continue
            src, dst = (from_zone, to_zone) if flow > 0 else (to_zone, from_zone)
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


def _path_map_from_airflow(air_flow_paths: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """Derive the ContamX path order from ``air_flow_paths.json`` adjacency.

    Mirrors the airflow-path section emitted by
    ``tools/contam_prj_bridge.export_prj`` (one CONTAM path per adjacency
    edge, in file order), so ContamX path number ``i + 1`` maps back to the
    same zone pair.
    """
    return [
        (adj["from"], adj["to"], False)
        for adj in air_flow_paths.get("adjacency", [])
    ]


def build_contamx_engine(
    repo_root: str,
    cfg: dict[str, Any],
) -> ContamXTransportEngine:
    """Build a ContamX-backed transport engine for the configured platform.

    Exports the platform to a temporary ``.prj``, runs ContamX, parses the
    ``.sim`` airflow field, and constructs the engine. Raises
    :class:`ContamXUnavailable` on any missing prerequisite so the caller
    can fall back to the native engine.
    """
    # Imported lazily to avoid a hard dependency cycle at module import.
    from engines.py_contam_bridge import load_air_flow_paths, load_spatial_layout
    from tools.contam_prj_bridge import export_prj

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

    prj_text = export_prj(spatial, airflow)
    with tempfile.TemporaryDirectory(prefix="crusher_contamx_") as tmp:
        prj_path = os.path.join(tmp, "platform.prj")
        with open(prj_path, "w", encoding="utf-8") as fh:
            fh.write(prj_text)

        sim_path = run_contamx(prj_path, binary, config=cfg)
        sim = SimResults(sim_path)
        flows = sim.path_volumetric_flow_m3h()

    path_map = _path_map_from_airflow(airflow)
    return ContamXTransportEngine(
        spatial_layout=spatial,
        path_map=path_map,
        path_flows_m3h=flows,
        filter_efficiency=filter_eff,
        natural_decay_rate=decay_rate,
    )
