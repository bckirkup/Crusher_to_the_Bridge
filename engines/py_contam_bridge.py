"""
engines.py_contam_bridge
~~~~~~~~~~~~~~~~~~~~~~~~

Python bridge to NIST CONTAM-style multi-zone airflow and contaminant
transport physics.

Re-implements the core mass-balance equations from the NIST CONTAM
program (https://www.nist.gov/el/energy-and-environment-division-73200/
nist-multizone-modeling) using the mathematical structures extracted
from ``py-contam/python/contam_output.py``:

- **Airflow paths**: Volumetric flow rates Q [m³/h] between zones,
  converted to mass flow via air density ρ.
- **Airflow nodes**: Zone pressure P [Pa], temperature T [K],
  air density D [kg/m³].
- **Contaminant transport**: Mass-balance per zone per time-step:

  dM_i/dt = Σ_j Q_ji·C_j·(1-η) - Q_out_i·C_i + S_i - λ·M_i

  where:
    M_i   = pathogen mass in zone i [copies]
    C_j   = M_j / V_j  concentration in source zone j [copies/m³]
    Q_ji  = volumetric airflow from zone j → i [m³/h]
    η     = HVAC filter efficiency (0 = no filter, 0.999 = HEPA)
    S_i   = source term (shedding deposits) [copies/epoch]
    λ     = natural decay rate (settling + viral inactivation)

The bridge reads ``air_flow_paths.json`` to build the airflow network
and applies transport at each epoch, replacing the flat 50% decay
previously used in ``infection_dynamics_bridge.py``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from simulation_utils.paths import resolve_repo_path, validated_open

import numpy as np


# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_AIR_DENSITY = 1.2041  # kg/m³ at 20°C, 101.325 kPa (STP)
DEFAULT_AIR_TEMP = 293.15     # K (20°C)
HOURS_PER_EPOCH = 1.0         # each epoch represents 1 hour


def derive_volume_m3(
    volume_m3: float | None,
    floor_area_m2: float | None,
    ceiling_height_m: float | None,
    default: float = 100.0,
) -> float:
    """Resolve a zone volume from explicit volume or area × height.

    CONTAM describes zones by floor area and ceiling height; this project
    historically stored only ``volume_m3``.  Resolution order:

    1. Use ``volume_m3`` when provided (preserves backward compatibility).
    2. Otherwise derive ``floor_area_m2 * ceiling_height_m`` when both
       geometry fields are present.
    3. Otherwise fall back to ``default``.
    """
    if volume_m3 is not None:
        return volume_m3
    if floor_area_m2 is not None and ceiling_height_m is not None:
        return floor_area_m2 * ceiling_height_m
    return default


class ContamZoneNode:
    """Represents a single airflow node in the CONTAM multi-zone model.

    Mirrors the zone node structure from contam_output.py:
    - T: temperature [K]
    - P: reference pressure [Pa]
    - D: air density [kg/m³]
    - volume: zone volume [m³]
    - floor_area_m2 / ceiling_height_m: CONTAM zone geometry [m², m]
    - elevation_m: relative floor elevation (CONTAM level) [m]
    - pathogen_mass: absolute pathogen mass in zone [copies]
    """

    __slots__ = (
        "zone_id", "volume_m3", "temperature_k",
        "pressure_pa", "density_kg_m3",
        "floor_area_m2", "ceiling_height_m", "elevation_m",
    )

    def __init__(
        self,
        zone_id: str,
        volume_m3: float,
        temperature_k: float = DEFAULT_AIR_TEMP,
        pressure_pa: float = 101325.0,
        density_kg_m3: float = DEFAULT_AIR_DENSITY,
        floor_area_m2: float | None = None,
        ceiling_height_m: float | None = None,
        elevation_m: float | None = None,
    ) -> None:
        self.zone_id = zone_id
        self.volume_m3 = volume_m3
        self.temperature_k = temperature_k
        self.pressure_pa = pressure_pa
        self.density_kg_m3 = density_kg_m3
        self.floor_area_m2 = floor_area_m2
        self.ceiling_height_m = ceiling_height_m
        self.elevation_m = elevation_m

    def concentration(self, pathogen_mass: float) -> float:
        """Pathogen concentration [copies/m³]."""
        if self.volume_m3 <= 0:
            return 0.0
        return pathogen_mass / self.volume_m3


class ContamAirflowPath:
    """Represents a single airflow path between two zones.

    Mirrors the airflow path structure from contam_output.py SIM format:
    - dP: pressure drop across path [Pa]
    - Flow0: primary volumetric flow [m³/h]
    - bidirectional: whether flow reverses (set to False for HVAC ducts)

    Filter efficiency is applied to contaminant mass passing through
    HVAC-ducted paths but NOT through passive openings (passageways,
    ladder wells).
    """

    __slots__ = (
        "path_id", "from_zone", "to_zone",
        "flow_rate_m3h", "path_type", "is_hvac_ducted",
    )

    def __init__(
        self,
        path_id: str,
        from_zone: str,
        to_zone: str,
        flow_rate_m3h: float,
        path_type: str = "hvac_duct",
        is_hvac_ducted: bool = True,
    ) -> None:
        self.path_id = path_id
        self.from_zone = from_zone
        self.to_zone = to_zone
        self.flow_rate_m3h = flow_rate_m3h
        self.path_type = path_type
        self.is_hvac_ducted = is_hvac_ducted


class ContamTransportEngine:
    """CONTAM-style multi-zone aerosol mass transport engine.

    Implements the NIST CONTAM contaminant transport equation as a
    discrete-time mass balance solved per epoch. The engine:

    1. Reads the airflow network from ``air_flow_paths.json``
    2. Builds zone nodes with volumes from ``spatial_layout.json``
    3. At each epoch, computes inter-zone mass transfer via:
       - HVAC recirculation within zones (with filter efficiency)
       - Cross-zone airflow through ladder wells, ventilation shafts
       - Passive adjacency exchange through passageways and hatches
    4. Applies natural aerosol decay (settling + viral inactivation)

    Parameters
    ----------
    spatial_layout : dict
        Parsed ``spatial_layout.json`` content.
    air_flow_paths : dict
        Parsed ``air_flow_paths.json`` content.
    filter_efficiency : float
        HVAC filter efficiency η ∈ [0, 1]. Standard values:
        - MERV-8:  0.20  (residential baseline)
        - MERV-13: 0.50  (commercial standard)
        - MERV-16: 0.95  (hospital grade)
        - HEPA:    0.999 (clean room / biocontainment)
    natural_decay_rate : float
        Fraction of pathogen mass lost per epoch to settling and
        viral inactivation (replaces the old flat 50% daily rate).
        Default 0.10 per epoch (≈ 10% hourly loss).
    """

    def __init__(
        self,
        spatial_layout: dict[str, Any],
        air_flow_paths: dict[str, Any],
        filter_efficiency: float = 0.50,
        natural_decay_rate: float = 0.10,
    ) -> None:
        self.filter_efficiency = filter_efficiency
        self.natural_decay_rate = natural_decay_rate

        self.zone_nodes: dict[str, ContamZoneNode] = {}
        self.airflow_paths: list[ContamAirflowPath] = []

        self._build_zone_nodes(spatial_layout)
        self._build_airflow_paths(air_flow_paths)

    def _build_zone_nodes(self, layout: dict[str, Any]) -> None:
        """Create zone nodes from spatial layout.

        Reads optional CONTAM geometry fields (``floor_area_m2``,
        ``ceiling_height_m``, ``elevation_m``) when present.  ``volume_m3``
        is used directly when specified; otherwise it is derived from
        floor area × ceiling height, falling back to 100.0 m³ when neither
        is available.  Platforms that only specify ``volume_m3`` are
        unaffected.
        """
        for zone in layout.get("zones", []):
            zone_id = zone["id"]
            floor_area = zone.get("floor_area_m2")
            ceiling_height = zone.get("ceiling_height_m")
            elevation = zone.get("elevation_m")
            volume = derive_volume_m3(
                zone.get("volume_m3"), floor_area, ceiling_height,
            )
            self.zone_nodes[zone_id] = ContamZoneNode(
                zone_id=zone_id,
                volume_m3=volume,
                floor_area_m2=floor_area,
                ceiling_height_m=ceiling_height,
                elevation_m=elevation,
            )

    def _build_hvac_recirculation_paths(self, airflow: dict[str, Any]) -> None:
        """Build room↔room HVAC edges using Contam simple-AHS semantics.

        Contam (and ContamX Path A) is the airflow source of truth. Native
        recirculation therefore mirrors Contam export + AHS bridge::

            Q_supply = ach · ΣV · hvac_duty
            Rec      = (1 − oa_fraction) · Q_supply
            Q_ij     = (Q_supply / n) · (Rec / Q_supply) · (1 / n)
                     = Rec / n²

        (equal per-room supply/return, matching Contam Fahs allocation).

        Optional ``oa_fraction`` / ``hvac_duty`` may be set per HVAC zone or
        at the air_flow_paths top level. Defaults: OA 0.2 (Contam OAFrac),
        duty 1.0 (design). Fiction Contam twins that freeze ContamX at the
        hobbyist night half-duty set ``hvac_duty: 0.5``.
        """
        default_oa = float(airflow.get("oa_fraction", 0.2))
        default_duty = float(airflow.get("hvac_duty", 1.0))
        for hvac_zone in airflow.get("hvac_zones", []):
            zone_id = hvac_zone["id"]
            rooms = [
                r for r in hvac_zone.get("rooms", [])
                if r in self.zone_nodes
            ]
            n_rooms = len(rooms)
            if n_rooms < 2:
                continue
            total_volume = sum(self.zone_nodes[r].volume_m3 for r in rooms)
            if total_volume <= 0:
                continue
            oa = float(hvac_zone.get("oa_fraction", default_oa))
            duty = float(hvac_zone.get("hvac_duty", default_duty))
            oa = min(max(oa, 0.0), 1.0)
            duty = max(duty, 0.0)
            supply_total = hvac_zone.get("ach", 6.0) * total_volume * duty
            recirc = (1.0 - oa) * supply_total
            if recirc <= 0:
                continue
            pair_flow = recirc / (n_rooms * n_rooms)
            for room_from in rooms:
                for room_to in rooms:
                    if room_from == room_to:
                        continue
                    self.airflow_paths.append(ContamAirflowPath(
                        path_id=f"hvac_{zone_id}_{room_from}_{room_to}",
                        from_zone=room_from,
                        to_zone=room_to,
                        flow_rate_m3h=pair_flow,
                        path_type="hvac_recirculation",
                        is_hvac_ducted=True,
                    ))

    def _build_cross_zone_paths(self, airflow: dict[str, Any]) -> None:
        for link in airflow.get("cross_zone_links", []):
            from_rooms = self._get_zone_rooms(link["from"], airflow)
            to_rooms = self._get_zone_rooms(link["to"], airflow)
            if not from_rooms or not to_rooms:
                continue
            flow = link.get("flow_rate_m3h", 0)
            path_name = link.get("path", f"{link['from']}_to_{link['to']}")
            is_ducted = link.get("is_hvac_ducted", False)
            n_pairs = len(from_rooms) * len(to_rooms)
            pair_flow = flow / n_pairs if n_pairs > 0 else 0
            for fr in from_rooms:
                for tr in to_rooms:
                    self.airflow_paths.append(ContamAirflowPath(
                        path_id=f"xzone_{path_name}_{fr}_{tr}",
                        from_zone=fr,
                        to_zone=tr,
                        flow_rate_m3h=pair_flow,
                        path_type="cross_zone",
                        is_hvac_ducted=is_ducted,
                    ))

    def _build_adjacency_paths(self, airflow: dict[str, Any]) -> None:
        passive_rates = {
            "passageway": 15.0,
            "service_hatch": 8.0,
            "ladder_well": 12.0,
            "sealed_door": 2.0,
        }
        for adj in airflow.get("adjacency", []):
            from_room = adj["from"]
            to_room = adj["to"]
            adj_type = adj.get("type", "passageway")
            rate = passive_rates.get(adj_type, 10.0)
            for src, dst in ((from_room, to_room), (to_room, from_room)):
                self.airflow_paths.append(ContamAirflowPath(
                    path_id=f"adj_{src}_{dst}",
                    from_zone=src,
                    to_zone=dst,
                    flow_rate_m3h=rate,
                    path_type=f"adjacency_{adj_type}",
                    is_hvac_ducted=False,
                ))

    def _build_airflow_paths(self, airflow: dict[str, Any]) -> None:
        """Build airflow paths from air_flow_paths.json.

        Creates paths from three sources:
        1. Intra-zone HVAC recirculation (within each HVAC zone)
        2. Cross-zone links (between HVAC zones)
        3. Room adjacency (passive exchange through doors/hatches)
        """
        self._build_hvac_recirculation_paths(airflow)
        self._build_cross_zone_paths(airflow)
        self._build_adjacency_paths(airflow)

    def _get_zone_rooms(
        self, zone_id: str, airflow: dict[str, Any],
    ) -> list[str]:
        """Get room list for an HVAC zone ID."""
        for hz in airflow.get("hvac_zones", []):
            if hz["id"] == zone_id:
                return [r for r in hz.get("rooms", []) if r in self.zone_nodes]
        return []

    def transport_step(
        self,
        zone_pathogen_mass: dict[str, float],
    ) -> dict[str, float]:
        """Execute one epoch of CONTAM-style aerosol mass transport.

        Implements the discrete-time contaminant mass balance:

            M_i(t+1) = M_i(t)
                       + Σ_j [Q_ji · C_j(t) · (1-η_j) · Δt]   (inflow)
                       - Σ_j [Q_ij · C_i(t) · Δt]              (outflow)
                       - λ · M_i(t)                             (decay)

        where η_j is applied only to HVAC-ducted paths.

        Parameters
        ----------
        zone_pathogen_mass : dict
            Current pathogen mass per zone {zone_id: mass}.

        Returns
        -------
        dict
            Updated pathogen mass per zone after transport and decay.
        """
        dt = HOURS_PER_EPOCH

        # Compute concentrations [copies/m³]
        concentrations: dict[str, float] = {}
        for zone_id, mass in zone_pathogen_mass.items():
            node = self.zone_nodes.get(zone_id)
            if node is not None:
                concentrations[zone_id] = node.concentration(mass)
            else:
                concentrations[zone_id] = 0.0

        # Accumulate mass transfers
        delta: dict[str, float] = dict.fromkeys(zone_pathogen_mass, 0.0)

        for path in self.airflow_paths:
            src = path.from_zone
            dst = path.to_zone
            if src not in concentrations or dst not in delta:
                continue

            c_src = concentrations[src]
            if c_src <= 0:
                continue

            # Mass transferred = Q · C · Δt
            mass_transfer = path.flow_rate_m3h * c_src * dt

            # Apply filter efficiency to HVAC-ducted paths
            if path.is_hvac_ducted:
                mass_arriving = mass_transfer * (1.0 - self.filter_efficiency)
            else:
                mass_arriving = mass_transfer

            # Cap transfer to available mass in source zone
            available = zone_pathogen_mass.get(src, 0.0)
            if mass_transfer > available:
                scale = available / mass_transfer if mass_transfer > 0 else 0
                mass_transfer *= scale
                mass_arriving *= scale

            delta[src] -= mass_transfer
            delta[dst] += mass_arriving

        # Apply transfers and natural decay
        result: dict[str, float] = {}
        for zone_id, current_mass in zone_pathogen_mass.items():
            new_mass = current_mass + delta.get(zone_id, 0.0)
            # Natural decay (settling + viral inactivation)
            new_mass *= (1.0 - self.natural_decay_rate)
            result[zone_id] = max(0.0, new_mass)

        return result

    def get_transport_summary(
        self,
        zone_pathogen_mass: dict[str, float],
    ) -> dict[str, Any]:
        """Return a diagnostic summary of the current transport state."""
        concentrations = {}
        for zone_id, mass in zone_pathogen_mass.items():
            node = self.zone_nodes.get(zone_id)
            if node is not None:
                concentrations[zone_id] = {
                    "mass": round(mass, 3),
                    "concentration_per_m3": round(
                        node.concentration(mass), 3,
                    ),
                    "volume_m3": node.volume_m3,
                }

        total_hvac_paths = sum(
            1 for p in self.airflow_paths if p.is_hvac_ducted
        )
        total_passive_paths = sum(
            1 for p in self.airflow_paths if not p.is_hvac_ducted
        )

        return {
            "filter_efficiency": self.filter_efficiency,
            "natural_decay_rate": self.natural_decay_rate,
            "total_hvac_paths": total_hvac_paths,
            "total_passive_paths": total_passive_paths,
            "zone_concentrations": concentrations,
        }


def load_air_flow_paths(repo_root: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Load air_flow_paths.json from the configured path."""
    graph_cfg = cfg.get("ship_graph", {})
    rel_path = graph_cfg.get(
        "air_flow_paths",
        "data/platforms/destroyer_baseline/air_flow_paths.json",
    )
    full_path = resolve_repo_path(repo_root, rel_path)
    if not os.path.isfile(full_path):
        return {}
    with validated_open(full_path, "r", allowed_roots=(repo_root,), encoding="utf-8") as fh:
        return json.load(fh)


def load_spatial_layout(repo_root: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Load spatial_layout.json from the configured path."""
    graph_cfg = cfg.get("ship_graph", {})
    rel_path = graph_cfg.get(
        "spatial_layout",
        "data/platforms/destroyer_baseline/spatial_layout.json",
    )
    full_path = resolve_repo_path(repo_root, rel_path)
    if not os.path.isfile(full_path):
        return {}
    with validated_open(full_path, "r", allowed_roots=(repo_root,), encoding="utf-8") as fh:
        return json.load(fh)


def _build_native_engine(
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    hvac_cfg: dict[str, Any],
) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
        filter_efficiency=hvac_cfg.get("filter_efficiency", 0.50),
        natural_decay_rate=hvac_cfg.get("natural_decay_rate", 0.10),
    )


def build_transport_engine(
    repo_root: str,
    cfg: dict[str, Any],
) -> ContamTransportEngine | None:
    """Build a CONTAM transport engine from config and layout files.

    The engine is selected by ``hvac.transport_engine``:

    - ``"native"`` (default): the pure-Python ``ContamTransportEngine``.
    - ``"contamx"``: require the real ContamX solver; fall back to native
      with a warning if it is unavailable.
    - ``"auto"``: use ContamX when a binary/valid project is available,
      otherwise silently fall back to native.

    Returns ``None`` if the platform layout files are not found.
    """
    spatial = load_spatial_layout(repo_root, cfg)
    airflow = load_air_flow_paths(repo_root, cfg)
    if not spatial or not airflow:
        return None

    hvac_cfg = cfg.get("hvac", {})
    selection = str(hvac_cfg.get("transport_engine", "native")).lower()

    if selection in ("contamx", "auto"):
        # Imported lazily so the native path never depends on the ContamX seam.
        from engines.contamx_runner import ContamXUnavailable
        from engines.contamx_transport import build_contamx_engine
        try:
            return build_contamx_engine(repo_root, cfg)
        except ContamXUnavailable as exc:
            if selection == "contamx":
                print(
                    f"  [hvac] ContamX requested but unavailable "
                    f"({exc}); using native transport engine."
                )
            # "auto" falls back silently.

    return _build_native_engine(spatial, airflow, hvac_cfg)
