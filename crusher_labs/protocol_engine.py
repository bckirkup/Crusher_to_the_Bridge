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
from typing import Any

from crusher_labs.cost_ledger import CostLedger, CATEGORY_INTERVENTION, CATEGORY_SURVEILLANCE
from crusher_labs.stoplight import (
    stoplight_from_ct,
    stoplight_from_anomaly,
    stoplight_from_rdt,
    stoplight_from_disruption,
    stoplight_from_long_read_verification,
    stoplight_from_wearable_agent,
    stoplight_from_wearable_fleet_rates,
    stoplight_from_sick_call_count,
    aggregate_stoplight_max,
    meets_threshold,
)

WEARABLE_AGENT_INSTRUMENT = "wearable_physiological_monitor"
WEARABLE_FLEET_INSTRUMENT = "wearable_fleet_monitor"
DETECTION_ESCALATION_INSTRUMENT = "detection_escalation"


# ── Compute stoplight arrays from instrument results ─────────────────────

def _default_wearable_fleet_thresholds(
    cfg: dict[str, Any] | None,
) -> dict[str, float]:
    """Resolve fleet wearable rate thresholds from config."""
    wm = (cfg or {}).get("wearable_monitoring", {})
    thresholds = wm.get("stoplight_thresholds", {})
    return {
        "amber_fever_rate": float(thresholds.get("fleet_fever_rate_amber", 0.03)),
        "red_fever_rate": float(thresholds.get("fleet_fever_rate_red", 0.08)),
        "amber_anomaly_rate": float(thresholds.get("fleet_anomaly_rate_amber", 0.05)),
        "red_anomaly_rate": float(thresholds.get("fleet_anomaly_rate_red", 0.12)),
    }


def _default_detection_mode_thresholds(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve integrated detection-mode thresholds from config."""
    esc = (cfg or {}).get("escalation", {})
    modes = esc.get("detection_modes", {})
    syndromic = modes.get("syndromic", {})
    return {
        "syndromic_amber": int(syndromic.get("amber_sick_call_count", 2)),
        "syndromic_red": int(syndromic.get("red_sick_call_count", 5)),
    }


def compute_wearable_stoplights(
    wearable_result: dict[str, Any] | None,
    cfg: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Derive per-agent and fleet wearable stoplights.

    Returns ``(agent_lights, fleet_lights)`` where fleet uses key ``fleet``.
    """
    if not wearable_result:
        return {}, {}

    fleet_thresholds = _default_wearable_fleet_thresholds(cfg)
    agent_lights: dict[str, str] = {}
    for aid, data in wearable_result.get("agent_results", {}).items():
        agent_lights[str(aid)] = stoplight_from_wearable_agent(
            fever=bool(data.get("fever", False)),
            anomaly_count=int(data.get("anomaly_count", 0)),
        )

    fleet = wearable_result.get("fleet_summary", {})
    fleet_level = stoplight_from_wearable_fleet_rates(
        float(fleet.get("fever_rate", 0.0)),
        float(fleet.get("anomaly_rate", 0.0)),
        **fleet_thresholds,
    )
    return agent_lights, {"fleet": fleet_level}


def compute_detection_escalation_stoplights(
    base_lights: dict[str, dict[str, str]],
    syndromic_result: dict[str, Any] | None,
    wearable_result: dict[str, Any] | None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Integrate syndromic, wearable, environmental, and clinical detection modes.

    Each mode contributes one stoplight used by escalation-category SOPs that
    require multiple concurrent detection signals (``min_modes_affected``).
    """
    mode_thresholds = _default_detection_mode_thresholds(cfg)
    modes: dict[str, str] = {}

    sick_calls = int((syndromic_result or {}).get("sick_call_count", 0))
    modes["syndromic"] = stoplight_from_sick_call_count(
        sick_calls,
        amber_threshold=mode_thresholds["syndromic_amber"],
        red_threshold=mode_thresholds["syndromic_red"],
    )

    agent_wearable, fleet_wearable = compute_wearable_stoplights(wearable_result, cfg)
    if agent_wearable:
        modes["wearable_individual"] = aggregate_stoplight_max(list(agent_wearable.values()))
    else:
        modes["wearable_individual"] = "GREEN"
    modes["wearable_fleet"] = fleet_wearable.get("fleet", "GREEN")

    env_levels: list[str] = []
    for instrument in (
        "continuous_air_sampler",
        "targeted_surface_swab",
        "wastewater_sequencing_grid",
    ):
        env_levels.extend(base_lights.get(instrument, {}).values())
    modes["environmental"] = aggregate_stoplight_max(env_levels)

    clinical_levels: list[str] = []
    for instrument in (
        "clinical_rdt",
        "clinical_qpcr",
        "clinical_microbiology",
        "long_read_verification_sequencing",
    ):
        clinical_levels.extend(base_lights.get(instrument, {}).values())
    modes["clinical"] = aggregate_stoplight_max(clinical_levels)

    return modes


def compute_stoplights(
    air_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    ww_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
    wearable_result: dict[str, Any] | None = None,
    syndromic_result: dict[str, Any] | None = None,
    long_read_results: dict[str, dict[str, Any]] | None = None,
    cfg: dict[str, Any] | None = None,
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
            "wearable_physiological_monitor": {<agent_id_str>: ...},
            "wearable_fleet_monitor": {"fleet": "GREEN"|"AMBER"|"RED"},
            "detection_escalation": {mode: "GREEN"|"AMBER"|"RED", ...},
        }
    """
    lights: dict[str, dict[str, str]] = {}

    # Environmental instruments (keyed by zone)
    air_lights: dict[str, str] = {}
    for zone, data in air_results.items():
        air_lights[zone] = stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["continuous_air_sampler"] = air_lights

    swab_lights: dict[str, str] = {}
    for zone, data in swab_results.items():
        swab_lights[zone] = stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["targeted_surface_swab"] = swab_lights

    ww_lights: dict[str, str] = {}
    for zone, data in ww_results.items():
        anomaly = data.get("anomaly_score", 0.0)
        ww_lights[zone] = stoplight_from_anomaly(anomaly)
    lights["wastewater_sequencing_grid"] = ww_lights

    # Clinical instruments (keyed by agent id string)
    rdt_lights: dict[str, str] = {}
    for aid, data in clin_rdt_results.items():
        rdt_lights[str(aid)] = stoplight_from_rdt(data.get("positive", False))
    lights["clinical_rdt"] = rdt_lights

    qpcr_lights: dict[str, str] = {}
    for aid, data in clin_qpcr_results.items():
        qpcr_lights[str(aid)] = stoplight_from_ct(data.get("ct_value"), data.get("detected", False))
    lights["clinical_qpcr"] = qpcr_lights

    microbio_lights: dict[str, str] = {}
    for aid, data in clin_microbio_results.items():
        disruption = data.get("microflora_disruption_level", 0.0)
        microbio_lights[str(aid)] = stoplight_from_disruption(disruption)
    lights["clinical_microbiology"] = microbio_lights

    lr_lights: dict[str, str] = {}
    for req_id, data in (long_read_results or {}).items():
        lr_lights[str(req_id)] = stoplight_from_long_read_verification(data)
    if lr_lights:
        lights["long_read_verification_sequencing"] = lr_lights

    agent_wearable, fleet_wearable = compute_wearable_stoplights(wearable_result, cfg)
    if agent_wearable:
        lights[WEARABLE_AGENT_INSTRUMENT] = agent_wearable
    if fleet_wearable:
        lights[WEARABLE_FLEET_INSTRUMENT] = fleet_wearable

    lights[DETECTION_ESCALATION_INSTRUMENT] = compute_detection_escalation_stoplights(
        lights, syndromic_result, wearable_result, cfg,
    )

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
        self.required_cascade_tier: int | None = config.get("required_cascade_tier")

    def is_triggered(
        self,
        stoplights: dict[str, dict[str, str]],
        cascade_context: dict[str, Any] | None = None,
    ) -> bool:
        """Check whether this protocol's trigger condition is met.

        When a ``required_cascade_tier`` is set and *cascade_context* is
        provided, the protocol only fires if enough agents have reached
        that tier in the cascade (or the cascade has unlocked this SOP
        via fleet escalation rules).
        """
        if self.required_cascade_tier is not None and cascade_context is not None:
            tier_req = self.required_cascade_tier
            unlocked_sops = set(cascade_context.get("unlocked_sops", []))
            fleet_sops = set(cascade_context.get("fleet_sops_unlocked", []))
            tier_distribution = cascade_context.get("tier_distribution", {})

            if self.protocol_id in unlocked_sops or self.protocol_id in fleet_sops:
                pass  # cascade explicitly unlocked this SOP
            else:
                agents_at_tier = sum(
                    count for tid, count in tier_distribution.items()
                    if int(tid) >= tier_req
                )
                min_agents = self.trigger.get("min_agents_affected", 1)
                if agents_at_tier < max(min_agents, 1):
                    return False

        instrument_class = self.trigger.get("instrument_class", "")
        required_level = self.trigger.get("stoplight_level", "RED")
        instrument_lights = stoplights.get(instrument_class, {})

        if not instrument_lights:
            return False

        matching = sum(
            1 for light in instrument_lights.values()
            if meets_threshold(light, required_level)
        )

        if instrument_class == DETECTION_ESCALATION_INSTRUMENT:
            min_modes = self.trigger.get("min_modes_affected", 2)
            return matching >= min_modes

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
        forced_protocol_ids: set[str] | None = None,
        authorized_sop_ids: list[str] | None = None,
        cascade_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate all protocols and return the list of active modifiers.

        Protocols activate when stoplight-triggered or listed in
        *forced_protocol_ids*. Costs debit only when authorized (if a CO
        subset is set) or when explicitly forced via command action.

        When *cascade_context* is provided, protocols with a
        ``required_cascade_tier`` are gated by the cascade engine's
        current state.

        Returns a list of dicts, each containing:
        - ``protocol_id``, ``name``, ``modifiers``
        - ``newly_activated`` (True if just turned on this epoch)
        """
        active_modifiers: list[dict[str, Any]] = []
        forced = forced_protocol_ids or set()
        authorized = set(authorized_sop_ids) if authorized_sop_ids is not None else None

        for protocol in self.protocols:
            pid = protocol.protocol_id
            triggered = protocol.is_triggered(stoplights, cascade_context)
            forced_on = pid in forced
            should_active = triggered or forced_on
            was_active = self._active[pid]

            if should_active:
                newly_activated = not was_active
                may_debit = (
                    authorized is None
                    or pid in authorized
                    or forced_on
                )

                if newly_activated:
                    self._active[pid] = True
                    self._activation_epoch[pid] = epoch

                    if may_debit and protocol.activation_costs:
                        self.ledger.debit_protocol(
                            epoch=epoch,
                            protocol_id=pid,
                            protocol_name=protocol.name,
                            costs=protocol.activation_costs,
                            category=protocol.category,
                            is_activation=True,
                        )

                    self.protocol_log.append({
                        "epoch": epoch,
                        "protocol_id": pid,
                        "name": protocol.name,
                        "event": "ACTIVATED",
                        "modifiers": protocol.modifiers,
                        "forced": forced_on and not triggered,
                    })

                if may_debit and protocol.costs_per_epoch:
                    self.ledger.debit_protocol(
                        epoch=epoch,
                        protocol_id=pid,
                        protocol_name=protocol.name,
                        costs=protocol.costs_per_epoch,
                        category=protocol.category,
                        is_activation=False,
                    )

                active_modifiers.append({
                    "protocol_id": pid,
                    "name": protocol.name,
                    "modifiers": protocol.modifiers,
                    "newly_activated": newly_activated,
                    "active_since_epoch": self._activation_epoch[pid],
                    "forced": forced_on and not triggered,
                })

            elif was_active:
                self._active[pid] = False
                self.protocol_log.append({
                    "epoch": epoch,
                    "protocol_id": pid,
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
