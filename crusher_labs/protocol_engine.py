"""
protocol_engine.py – Reactive Protocol Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Evaluates standing protocols (SOPs) against LOW_FIDELITY stoplight
indicators at the end of each epoch.  When an instrument class trips a
trigger condition, the engine autonomously applies the designated
physics/behavior modifiers and debits costs from the CostLedger.

The engine re-derives stoplight levels from raw instrument results using
the same threshold functions as ``lab_notebook.py`` so it works regardless
of the configured fidelity tier.
"""

from __future__ import annotations

import json
import math
from typing import Any

from crusher_labs.cost_ledger import CostLedger, CATEGORY_INTERVENTION, CATEGORY_SURVEILLANCE


# ── Stoplight derivation (mirrors lab_notebook.py thresholds) ────────────

STOPLIGHT_ORDER = {"GREEN": 0, "AMBER": 1, "RED": 2}


def _stoplight_from_ct(ct: float | None, detected: bool) -> str:
    if not detected or ct is None:
        return "GREEN"
    if ct <= 30:
        return "RED"
    if ct <= 35:
        return "AMBER"
    return "GREEN"


def _stoplight_from_anomaly(anomaly_score: float) -> str:
    if anomaly_score >= 0.7:
        return "RED"
    if anomaly_score >= 0.3:
        return "AMBER"
    return "GREEN"


def _stoplight_from_rdt(positive: bool) -> str:
    return "RED" if positive else "GREEN"


def _stoplight_from_disruption(level: float) -> str:
    if level >= 0.6:
        return "RED"
    if level >= 0.3:
        return "AMBER"
    return "GREEN"


def _meets_threshold(actual: str, required: str) -> bool:
    """Return True if *actual* stoplight level meets or exceeds *required*."""
    return STOPLIGHT_ORDER.get(actual, 0) >= STOPLIGHT_ORDER.get(required, 0)


# ── Compute stoplight arrays from instrument results ─────────────────────

def compute_stoplights(
    air_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    ww_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Derive per-zone and per-agent stoplight levels from raw instrument results.

    Returns::

        {
            "continuous_air_sampler": {"Bridge": "GREEN", "MedBay": "RED", ...},
            "targeted_surface_swab": {"Bridge": "GREEN", ...},
            "wastewater_sequencing_grid": {"Engine_Room": "AMBER", ...},
            "clinical_rdt": {<agent_id_str>: "GREEN"|"RED", ...},
            "clinical_qpcr": {<agent_id_str>: "GREEN"|"AMBER"|"RED", ...},
            "clinical_microbiology": {<agent_id_str>: "GREEN"|"AMBER"|"RED", ...},
        }
    """
    lights: dict[str, dict[str, str]] = {}

    # Environmental instruments (keyed by zone)
    air_lights: dict[str, str] = {}
    for zone, data in air_results.items():
        air_lights[zone] = _stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["continuous_air_sampler"] = air_lights

    swab_lights: dict[str, str] = {}
    for zone, data in swab_results.items():
        swab_lights[zone] = _stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["targeted_surface_swab"] = swab_lights

    ww_lights: dict[str, str] = {}
    for zone, data in ww_results.items():
        anomaly = data.get("anomaly_score", 0.0)
        ww_lights[zone] = _stoplight_from_anomaly(anomaly)
    lights["wastewater_sequencing_grid"] = ww_lights

    # Clinical instruments (keyed by agent id string)
    rdt_lights: dict[str, str] = {}
    for aid, data in clin_rdt_results.items():
        rdt_lights[str(aid)] = _stoplight_from_rdt(data.get("positive", False))
    lights["clinical_rdt"] = rdt_lights

    qpcr_lights: dict[str, str] = {}
    for aid, data in clin_qpcr_results.items():
        qpcr_lights[str(aid)] = _stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["clinical_qpcr"] = qpcr_lights

    microbio_lights: dict[str, str] = {}
    for aid, data in clin_microbio_results.items():
        disruption = data.get("microflora_disruption_level", 0.0)
        microbio_lights[str(aid)] = _stoplight_from_disruption(disruption)
    lights["clinical_microbiology"] = microbio_lights

    return lights


# ── Protocol evaluation ──────────────────────────────────────────────────

class StandingProtocol:
    """A single SOP loaded from ``protocols.json``."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.protocol_id: str = config["protocol_id"]
        self.name: str = config["name"]
        self.description: str = config.get("description", "")
        self.trigger: dict[str, Any] = config["trigger"]
        self.modifiers: dict[str, Any] = config.get("modifiers", {})
        self.costs_per_epoch: dict[str, Any] = config.get("costs_per_epoch", {})
        self.activation_costs: dict[str, Any] = config.get("activation_costs", {})
        self.category: str = config.get("category", CATEGORY_INTERVENTION)

    def is_triggered(self, stoplights: dict[str, dict[str, str]]) -> bool:
        """Check whether this protocol's trigger condition is met."""
        instrument_class = self.trigger.get("instrument_class", "")
        required_level = self.trigger.get("stoplight_level", "RED")
        instrument_lights = stoplights.get(instrument_class, {})

        if not instrument_lights:
            return False

        # Count how many zones/agents meet the threshold
        matching = sum(
            1 for light in instrument_lights.values()
            if _meets_threshold(light, required_level)
        )

        min_zones = self.trigger.get("min_zones_affected", 0)
        min_agents = self.trigger.get("min_agents_affected", 0)
        required_count = max(min_zones, min_agents, 1)

        return matching >= required_count


class ProtocolEngine:
    """Evaluates standing protocols each epoch and tracks active state."""

    def __init__(
        self,
        protocols: list[StandingProtocol],
        ledger: CostLedger,
    ) -> None:
        self.protocols = protocols
        self.ledger = ledger
        self._active: dict[str, bool] = {p.protocol_id: False for p in protocols}
        self._activation_epoch: dict[str, int] = {}
        self.protocol_log: list[dict[str, Any]] = []

    def evaluate_epoch(
        self,
        epoch: int,
        stoplights: dict[str, dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Evaluate all protocols and return the list of active modifiers.

        Returns a list of dicts, each containing:
        - ``protocol_id``, ``name``, ``modifiers``
        - ``newly_activated`` (True if just turned on this epoch)
        """
        active_modifiers: list[dict[str, Any]] = []

        for protocol in self.protocols:
            triggered = protocol.is_triggered(stoplights)
            was_active = self._active[protocol.protocol_id]

            if triggered:
                newly_activated = not was_active

                if newly_activated:
                    self._active[protocol.protocol_id] = True
                    self._activation_epoch[protocol.protocol_id] = epoch

                    # Debit activation costs
                    if protocol.activation_costs:
                        self.ledger.debit_protocol(
                            epoch=epoch,
                            protocol_id=protocol.protocol_id,
                            protocol_name=protocol.name,
                            costs=protocol.activation_costs,
                            category=protocol.category,
                            is_activation=True,
                        )

                    self.protocol_log.append({
                        "epoch": epoch,
                        "protocol_id": protocol.protocol_id,
                        "name": protocol.name,
                        "event": "ACTIVATED",
                        "modifiers": protocol.modifiers,
                    })

                # Debit per-epoch maintenance costs
                if protocol.costs_per_epoch:
                    self.ledger.debit_protocol(
                        epoch=epoch,
                        protocol_id=protocol.protocol_id,
                        protocol_name=protocol.name,
                        costs=protocol.costs_per_epoch,
                        category=protocol.category,
                        is_activation=False,
                    )

                active_modifiers.append({
                    "protocol_id": protocol.protocol_id,
                    "name": protocol.name,
                    "modifiers": protocol.modifiers,
                    "newly_activated": newly_activated,
                    "active_since_epoch": self._activation_epoch[protocol.protocol_id],
                })

            elif was_active:
                # Protocol was active but trigger no longer met — deactivate
                self._active[protocol.protocol_id] = False
                self.protocol_log.append({
                    "epoch": epoch,
                    "protocol_id": protocol.protocol_id,
                    "name": protocol.name,
                    "event": "DEACTIVATED",
                })

        return active_modifiers

    def get_active_protocols(self) -> list[str]:
        """Return IDs of currently active protocols."""
        return [pid for pid, active in self._active.items() if active]

    def get_merged_modifiers(
        self,
        active_modifiers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Merge modifiers from all active protocols.

        For scalar modifiers, the most aggressive (highest/lowest as
        appropriate) value wins.  For list modifiers (e.g., ``close_zones``),
        values are unioned.
        """
        merged: dict[str, Any] = {}

        for entry in active_modifiers:
            mods = entry["modifiers"]
            for key, value in mods.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, list):
                    existing = merged[key] if isinstance(merged[key], list) else [merged[key]]
                    merged[key] = list(set(existing + value))
                elif isinstance(value, (int, float)):
                    # For efficiency overrides, take the most aggressive
                    if "reduction" in key or "scalar" in key:
                        merged[key] = min(merged[key], value)
                    elif "override" in key or "multiplier" in key or "cap" in key:
                        if "cap" in key:
                            merged[key] = min(merged[key], value)
                        else:
                            merged[key] = max(merged[key], value)
                    else:
                        merged[key] = max(merged[key], value)

        return merged

    def generate_protocol_summary(self) -> dict[str, Any]:
        """Produce a summary of all protocol activations for reporting."""
        activations = [e for e in self.protocol_log if e["event"] == "ACTIVATED"]
        deactivations = [e for e in self.protocol_log if e["event"] == "DEACTIVATED"]
        return {
            "total_activations": len(activations),
            "total_deactivations": len(deactivations),
            "protocols_still_active": self.get_active_protocols(),
            "event_log": self.protocol_log,
        }


# ── Modifier application helpers ────────────────────────────────────────

def apply_hvac_modifiers(
    contam_engine: Any,
    merged_modifiers: dict[str, Any],
) -> None:
    """Apply HVAC-related protocol modifiers to the CONTAM transport engine."""
    if contam_engine is None:
        return
    if "hvac_filter_efficiency_override" in merged_modifiers:
        contam_engine.filter_efficiency = merged_modifiers["hvac_filter_efficiency_override"]


def apply_transmission_modifiers(
    transmission_core: Any,
    merged_modifiers: dict[str, Any],
) -> None:
    """Apply transmission-pathway scalars from protocol modifiers."""
    if transmission_core is None:
        return
    if "direct_contact_scalar" in merged_modifiers:
        transmission_core.direct_contact_scalar = merged_modifiers["direct_contact_scalar"]
    if "droplet_scalar" in merged_modifiers:
        transmission_core.droplet_scalar = merged_modifiers["droplet_scalar"]
    if "hvac_airborne_scalar" in merged_modifiers:
        transmission_core.hvac_airborne_scalar = merged_modifiers["hvac_airborne_scalar"]
    if "fomite_scalar" in merged_modifiers:
        transmission_core.fomite_scalar = merged_modifiers["fomite_scalar"]


def reset_modifiers(
    contam_engine: Any,
    transmission_core: Any,
    original_filter_eff: float,
) -> None:
    """Reset physics parameters to pre-protocol baseline values."""
    if contam_engine is not None:
        contam_engine.filter_efficiency = original_filter_eff
    if transmission_core is not None:
        transmission_core.direct_contact_scalar = 1.0
        transmission_core.droplet_scalar = 1.0
        transmission_core.hvac_airborne_scalar = 1.0
        transmission_core.fomite_scalar = 1.0


# ── Factory ──────────────────────────────────────────────────────────────

def load_protocols(config_path: str) -> list[StandingProtocol]:
    """Load standing protocols from ``protocols.json``."""
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return [StandingProtocol(p) for p in cfg.get("protocols", [])]
