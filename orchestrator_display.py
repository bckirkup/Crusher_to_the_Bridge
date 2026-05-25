"""
orchestrator_display.py – Terminal display and print helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All stdout printing: initialization banners, engine summaries,
epoch progress bar, and the final executive summary box.
"""

from __future__ import annotations

import sys
from typing import Any

from engines.infection_dynamics_bridge import KorkinShipEngine
from engines.py_contam_bridge import ContamTransportEngine
from crusher_labs.cost_ledger import CostLedger


# ── Initialization banners ───────────────────────────────────────────────

def print_initialization(
    ship: dict[str, Any],
    seeds: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> None:
    """Print the t=0 initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  INITIALIZATION  ·  Ship Graph + GRUMB Seeding + FRED/EMOD Params")
    print(thin)

    print(f"\n  Ship graph: {ship['num_agents']} agents  "
          f"({sum(1 for r in ship['agent_roles'].values() if r == 'passenger')} passengers, "
          f"{sum(1 for r in ship['agent_roles'].values() if r == 'crew')} crew)")
    if "agent_classes" in ship:
        print("  Agent classes:")
        for cls in ship["agent_classes"]:
            cid = cls.get("class_id", "?")
            frac = cls.get("fraction", 0)
            print(f"    {cid:25s} {frac:.0%}")
    if "gender_distribution" in ship:
        gd = ship["gender_distribution"]
        gd_str = "  ".join(f"{k}={v:.0%}" for k, v in gd.items())
        print(f"  Gender distribution: {gd_str}")
    print(f"  Zones: {', '.join(ship['zone_names'])}")
    print(f"  High-traffic: {', '.join(ship['high_traffic_zones'])}")

    print(f"\n  GRUMB multi-kingdom seeding (t=0):")
    for zone_name, seed in seeds.items():
        kf = seed["kingdom_fractions"]
        kf_str = "  ".join(f"{k}={v:.3f}" for k, v in kf.items())
        print(f"    {zone_name:15s} [{seed['zone_type']:7s}]  {kf_str}")

    fred_cfg = cfg.get("fred_behavior", {})
    print(f"\n  FRED behavioral params:")
    print(f"    Quarantine compliance:   {fred_cfg.get('quarantine_compliance', 0.85):.0%}")
    print(f"    Compliance delay:        {fred_cfg.get('compliance_delay_epochs', 1)} epoch(s)")
    cats = fred_cfg.get("healthy_noise_categories", [])
    for cat in cats:
        print(f"    Noise: {cat['reason']:15s}  P={cat['probability']:.3f}")

    emod_cfg = cfg.get("emod_progression", {})
    phases = emod_cfg.get("shedding_phases", [])
    print(f"\n  EMOD clinical progression:")
    print(f"    Incubation:  {emod_cfg.get('incubation_epochs', 2)} epochs")
    for ph in phases:
        print(f"    Phase {ph['name']:6s}  max_rate={ph['max_rate']:5.1f}  "
              f"sensitivity_cap={ph['sensitivity_cap']:.2f}")

    print(thin)
    print()


def print_korkin_engine(engine: KorkinShipEngine) -> None:
    """Print Korkin Lab engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  KORKIN LAB ENGINE  ·  infection-dynamics ABM initialized")
    print(thin)
    engine_summary = engine.get_summary()
    print(f"\n  Population: {engine_summary['total']} agents "
          f"({engine.num_passengers} passengers, {engine.num_crew} crew)")
    print(f"  Immune (negative secretors): {engine_summary['immune']}")
    print(f"  Initial infected: {engine_summary['infected']}")
    if engine_summary.get("agent_classes"):
        cls_str = "  ".join(
            f"{c}={n}" for c, n in sorted(engine_summary["agent_classes"].items())
        )
        print(f"  Agent classes: {cls_str}")
    if engine_summary.get("gender_distribution"):
        g_str = "  ".join(
            f"{g}={n}" for g, n in sorted(engine_summary["gender_distribution"].items())
        )
        print(f"  Gender: {g_str}")
    print(f"  Zones: {', '.join(z['name'] for z in engine.zones)}")
    print(f"  VSP isolation: {'enabled' if engine.vsp_isolation else 'disabled'}")
    print()


def print_wearable_monitoring(
    monitor: Any,
) -> None:
    """Print wearable physiological monitoring initialization summary."""
    thin = "─" * 80
    if monitor is not None:
        fleet = monitor.get_fleet_summary()
        print(thin)
        print("  WEARABLE MONITORING  ·  physiological device fleet initialized")
        print(thin)
        print(f"\n  Monitored agents: {fleet['total_monitored']}")
        for did, dev in fleet["devices"].items():
            channels = ", ".join(dev["channels"])
            print(f"  Device: {did:20s}  channels: {channels}")
        print(f"  Class → device mapping:")
        for cls, did in fleet["class_device_map"].items():
            print(f"    {cls:25s} → {did}")
        print()
    else:
        print("  [INFO] Wearable monitoring: disabled (no wearable_monitoring config)")
        print()


def print_contam_engine(
    contam_engine: ContamTransportEngine | None,
    engine: KorkinShipEngine,
    cfg: dict[str, Any],
) -> None:
    """Print CONTAM transport engine initialization summary."""
    thin = "─" * 80
    if contam_engine is not None:
        hvac_cfg = cfg.get("hvac", {})
        filter_type = hvac_cfg.get("filter_type", "MERV-13")
        print(thin)
        print("  CONTAM TRANSPORT ENGINE  ·  py-contam multi-zone airflow initialized")
        print(thin)
        transport_summary = contam_engine.get_transport_summary(engine.zone_pathogen_mass)
        print(f"\n  Filter type:        {filter_type}")
        print(f"  Filter efficiency:  {contam_engine.filter_efficiency:.1%}")
        print(f"  Natural decay rate: {contam_engine.natural_decay_rate:.1%} per epoch")
        print(f"  HVAC-ducted paths:  {transport_summary['total_hvac_paths']}")
        print(f"  Passive paths:      {transport_summary['total_passive_paths']}")
        print(f"  Zone nodes:         {len(contam_engine.zone_nodes)}")
        print()
    else:
        print("  [WARN] CONTAM transport engine not available – using legacy flat decay")
        print()


def print_multi_pathogen(
    pathogen_profiles: dict[str, dict[str, Any]],
    immunocompromised_ids: set[int],
    engine: KorkinShipEngine,
    imm_mult: float,
    enable_dual_signal: bool,
) -> None:
    """Print multi-pathogen engine initialization summary."""
    thin = "─" * 80
    if pathogen_profiles:
        print(thin)
        print("  MULTI-PATHOGEN ENGINE  ·  active profiles loaded")
        print(thin)
        for pid, prof in pathogen_profiles.items():
            print(f"    {pid:20s}  {prof['name']}")
            print(f"      Category: {prof.get('category', '?')}")
            print(f"      Routes:   {', '.join(prof.get('transmission_routes', []))}")
            intro = prof.get("introduction_epoch", 0)
            print(f"      Intro:    epoch {intro}")
            mf = prof.get("microflora_disruption", {})
            if mf.get("causes_disruption"):
                print(f"      Microflora disruption: {mf.get('disruption_type')} "
                      f"(mag={mf.get('disruption_magnitude', 0)})")
        print()
        print(f"  Immunocompromised agents: {len(immunocompromised_ids)}/{len(engine.agents)} "
              f"(mult={imm_mult}x)")
        print(f"  Dual-signal shedding: {'enabled' if enable_dual_signal else 'disabled'}")
        print()


def print_transmission_core(
    hvac_downstream: dict[str, list[str]],
    pathogen_profiles: dict[str, dict[str, Any]],
) -> None:
    """Print transmission core initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  TRANSMISSION CORE  ·  four-pathway model initialized")
    print(thin)
    print("    1. Direct Contact      (zone-colocation, avgR scaling)")
    print("    2. Short-Range Droplet (immediate room aerosol)")
    print("    3. Long-Range Airborne (HVAC drift via py-contam)")
    print("    4. Fomite Deposition   (surface pools + stochastic pickup)")
    print(f"   HVAC downstream links: {sum(len(v) for v in hvac_downstream.values())}")
    if pathogen_profiles:
        print(f"   Active pathogens: {', '.join(pathogen_profiles.keys())}")
    print()


def print_observation_engine(
    fidelity_name: str,
    xcontam_rate: float,
    ctrl_intensity: str,
    lab_notebook_enabled: bool,
) -> None:
    """Print observation engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  OBSERVATION ENGINE  ·  instrument-level diagnostics initialized")
    print(thin)
    print(f"    ENV 1. Continuous Air Sniffer   (aerosol Ct)")
    print(f"    ENV 2. Targeted Surface Swab    (fomite PCR + compliance variance)")
    print(f"    ENV 3. Wastewater Seq Grid      (Dirichlet-multinomial metagenomics)")
    print(f"    CLN 4. Clinical RDT             (lateral-flow antigen, binary)")
    print(f"    CLN 5. Clinical qPCR            (patient viral load Ct)")
    print(f"    CLN 6. Clinical Microbiology    (culture/staining, flora shifts)")
    print(f"   Logging fidelity:   {fidelity_name}")
    print(f"   Cross-contamination: {xcontam_rate:.4%} carryover")
    print(f"   QC control intensity: {ctrl_intensity}")
    print(f"   Lab notebook: {'enabled' if lab_notebook_enabled else 'disabled'}")
    print()


def print_protocol_engine(
    standing_protocols: list,
    cost_ledger: CostLedger,
) -> None:
    """Print reactive protocol engine initialization summary."""
    thin = "─" * 80
    print(thin)
    print("  REACTIVE PROTOCOL ENGINE  ·  standing protocols loaded")
    print(thin)
    for sp in standing_protocols:
        trigger = sp.trigger
        print(f"    {sp.protocol_id}  {sp.name}")
        print(f"      Trigger: {trigger['instrument_class']} ≥ {trigger['stoplight_level']}")
    print(f"   Protocols loaded: {len(standing_protocols)}")
    print(f"   Starting allocation: ${cost_ledger.financial_balance:,.2f}")
    print(f"   Starting labor:  {cost_ledger.labor_remaining:.1f} person-hours")
    print(f"   Material items:  {len(cost_ledger.inventory)}")
    print()


# ── Epoch progress ───────────────────────────────────────────────────────

def print_progress(
    epoch: int,
    num_epochs: int,
    trigger_status: str,
    n_active_sops: int,
    total_spent: float,
    prev_status: str,
) -> None:
    """Overwrite a single terminal line with a dynamic progress bar."""
    pct = (epoch + 1) / num_epochs * 100
    bar_width = 30
    filled = int(bar_width * (epoch + 1) / num_epochs)
    bar = "█" * filled + "░" * (bar_width - filled)

    status_icon = {"BASELINE": "●", "SUSPECTED": "▲", "CONFIRMED": "■"}.get(
        trigger_status, "?"
    )

    transition = ""
    if trigger_status != prev_status:
        transition = f"  *** {prev_status} → {trigger_status} ***"

    line = (
        f"\r  {bar} {pct:5.1f}%  "
        f"Epoch {epoch + 1:02d}/{num_epochs:02d}  "
        f"{status_icon} {trigger_status:<10s}  "
        f"SOPs:{n_active_sops}  "
        f"Spent:${total_spent:>10,.0f}"
        f"{transition}"
    )

    sys.stdout.write(line)
    sys.stdout.flush()

    if epoch == num_epochs - 1:
        sys.stdout.write("\n")


# ── Executive summary ────────────────────────────────────────────────────

def print_executive_summary(
    *,
    num_agents: int,
    num_epochs: int,
    engine_summary: dict[str, Any],
    audit: dict[str, Any],
    proto_summary: dict[str, Any],
    escalation_log: list[dict[str, Any]],
    compliance_log: list[dict[str, Any]],
    trigger_status: str,
    isolated_count: int,
    refuser_count: int,
    contam_engine: Any | None,
    zone_pathogen_mass: dict[str, float],
    hvac_cfg: dict[str, Any],
    pathogen_profiles: dict[str, Any] | None,
) -> None:
    """Print a highly visible ASCII executive summary box."""
    W = 80
    border = "╔" + "═" * (W - 2) + "╗"
    bottom = "╚" + "═" * (W - 2) + "╝"
    divider = "╠" + "═" * (W - 2) + "╣"
    thin_div = "╟" + "─" * (W - 2) + "╢"

    def row(text: str = "") -> str:
        stripped = text.rstrip()
        pad = W - 4 - len(stripped)
        if pad < 0:
            stripped = stripped[: W - 4]
            pad = 0
        return f"║ {stripped}{' ' * pad}  ║"

    lines: list[str] = []
    lines.append(border)
    lines.append(row("CRUSHER TO THE BRIDGE  ─  EXECUTIVE SUMMARY"))
    lines.append(divider)

    lines.append(row("EPIDEMIOLOGICAL METRICS"))
    lines.append(thin_div)
    lines.append(row(f"Total crew:          {num_agents}"))
    lines.append(row(f"Total infected:      {engine_summary['infected'] + engine_summary['recovered'] + engine_summary['isolated']}"))
    lines.append(row(f"  Currently infected: {engine_summary['infected']}"))
    lines.append(row(f"  Recovered:          {engine_summary['recovered']}"))
    lines.append(row(f"  Isolated:           {engine_summary['isolated']}"))
    lines.append(row(f"  Immune (neg sec):   {engine_summary['immune']}"))
    lines.append(row(f"  Symptomatic:        {engine_summary['symptomatic']}"))
    lines.append(row(f"VSP triggered:       {'Yes' if engine_summary['vsp_triggered'] else 'No'}"))
    lines.append(row(f"Final status:        {trigger_status}"))

    if pathogen_profiles and len(pathogen_profiles) > 1:
        lines.append(row(f"Pathogen count:      {len(pathogen_profiles)}"))
        for pid in pathogen_profiles:
            lines.append(row(f"  - {pid}"))

    if escalation_log:
        lines.append(row())
        lines.append(row("Escalation timeline:"))
        for entry in escalation_log:
            lines.append(row(f"  Epoch {entry['epoch']:02d}:  {entry['from']}  ->  {entry['to']}"))

    if compliance_log:
        refused = sum(1 for c in compliance_log if c["action"] == "refused_quarantine")
        immediate = sum(1 for c in compliance_log if c["action"] == "immediate_compliance")
        lines.append(row(f"Compliance:          {immediate} immediate, {refused} refused"))

    summary = audit["summary"]
    lines.append(row(f"Person-hours used: {summary['total_labor_consumed_hours']:.1f} / {summary['starting_labor_capacity_hours']:.0f}"))

    lines.append(divider)

    lines.append(row("FINANCIAL & RESOURCE AUDIT"))
    lines.append(thin_div)
    lines.append(row(f"Starting allocation: ${summary['starting_financial_budget_usd']:>10,.2f}"))
    lines.append(row(f"Total spent:         ${summary['total_expenditure_usd']:>10,.2f}"))
    lines.append(row(f"  Surveillance:      ${summary['surveillance_cost_usd']:>10,.2f}"))
    lines.append(row(f"  Intervention:      ${summary['intervention_cost_usd']:>10,.2f}"))
    lines.append(row(f"Remaining:           ${summary['remaining_balance_usd']:>10,.2f}"))
    lines.append(row())
    lines.append(row(f"Labor consumed:      {summary['total_labor_consumed_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Surveillance:      {summary['surveillance_labor_hours']:>8.1f} person-hours"))
    lines.append(row(f"  Intervention:      {summary['intervention_labor_hours']:>8.1f} person-hours"))

    depleted = [
        item for item, data in audit["material_inventory"].items()
        if data["remaining"] == 0 and data["consumed"] > 0
    ]
    if depleted:
        lines.append(row())
        lines.append(row("DEPLETED SUPPLIES (fully consumed)"))
        for item in depleted:
            data = audit["material_inventory"][item]
            lines.append(row(f"  {item}: {data['starting']} -> 0  (${data['total_cost_usd']:.2f})"))

    lines.append(divider)

    lines.append(row("SOP ACTIVATION HISTORY"))
    lines.append(thin_div)

    activations = [e for e in proto_summary["event_log"] if e["event"] == "ACTIVATED"]
    if activations:
        seen: set[str] = set()
        for ev in activations:
            pid = ev["protocol_id"]
            if pid not in seen:
                seen.add(pid)
                lines.append(row(f"  {pid}  {ev['name'][:40]:<40s}  Epoch {ev['epoch']:02d}"))
    else:
        lines.append(row("  (no protocols activated)"))

    still_active = proto_summary["protocols_still_active"]
    if still_active:
        lines.append(row())
        lines.append(row(f"Still active at end: {', '.join(still_active)}"))

    lines.append(row(f"Total activations:   {proto_summary['total_activations']}"))
    lines.append(row(f"Total deactivations: {proto_summary['total_deactivations']}"))

    lines.append(divider)

    lines.append(row(f"{num_epochs} epochs completed.  Data bridged cleanly."))
    lines.append(row(f"Isolated: {isolated_count}/{num_agents}   Non-compliant: {refuser_count}"))
    lines.append(bottom)

    print()
    print("\n".join(lines))
