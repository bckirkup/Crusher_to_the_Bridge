"""
orchestrator_display.py – Terminal display and print helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All stdout printing: initialization banners, engine summaries,
epoch progress bar, and the final executive summary box.
"""

from __future__ import annotations

import sys
from typing import Any

from crusher_labs.cost_ledger import CostLedger
from engines.infection_dynamics_bridge import KorkinShipEngine
from engines.py_contam_bridge import ContamTransportEngine

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
        # codeql[py/clear-text-logging-sensitive-data]
        print(f"  Gender distribution: {gd_str}")
    print(f"  Zones: {', '.join(ship['zone_names'])}")
    print(f"  High-traffic: {', '.join(ship['high_traffic_zones'])}")

    print("\n  GRUMB multi-kingdom seeding (t=0):")
    for zone_name, seed in seeds.items():
        kf = seed["kingdom_fractions"]
        kf_str = "  ".join(f"{k}={v:.3f}" for k, v in kf.items())
        print(f"    {zone_name:15s} [{seed['zone_type']:7s}]  {kf_str}")

    counter_defs = cfg.get("ship_graph", {}).get("infection_counters", [])
    if counter_defs:
        print(f"\n  Infection counters: {len(counter_defs)} configured")
        for cdef in counter_defs:
            cid = cdef.get("counter_id", "?")
            _label = cdef.get("label", cid)
            metric = cdef.get("metric", "?")
            threshold = cdef.get("threshold")
            on_exceed = cdef.get("on_exceed", "log_only")
            thr_str = f"  threshold={threshold}  on_exceed={on_exceed}" if threshold is not None else ""
            print(f"    {cid:30s} {metric:20s}{thr_str}")

    fred_cfg = cfg.get("fred_behavior", {})
    print("\n  FRED behavioral params:")
    print(f"    Quarantine compliance:   {fred_cfg.get('quarantine_compliance', 0.85):.0%}")
    print(f"    Reluctant fraction:      {fred_cfg.get('reluctant_fraction', 0.75):.0%}")
    print(
        "    Reluctant delay:         "
        f"{fred_cfg.get('reluctant_delay_hours', 48)} hour(s)",
    )
    cats = fred_cfg.get("healthy_noise_categories", [])
    for cat in cats:
        reason = cat.get("reason", "")
        probability = cat.get("probability_per_day", cat.get("probability", 0.0))
        print(f"    Noise: {reason:15s}  P/day={probability:.3f}")

    emod_cfg = cfg.get("emod_progression", {})
    phases = emod_cfg.get("shedding_phases", [])
    print("\n  EMOD clinical progression:")
    print(
        f"    Incubation:  {emod_cfg.get('incubation_days', 2)} days "
        "(advisory; pathogen profiles drive progression)",
    )
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
    # codeql[py/clear-text-logging-sensitive-data]
    print(f"\n  Population: {engine_summary['total']} agents "
          f"({engine.num_passengers} passengers, {engine.num_crew} crew)")
    # codeql[py/clear-text-logging-sensitive-data]
    print(f"  Immune (negative secretors): {engine_summary['immune']}")
    # codeql[py/clear-text-logging-sensitive-data]
    print(f"  Initial infected: {engine_summary['infected']}")
    if engine_summary.get("agent_classes"):
        cls_str = "  ".join(
            f"{c}={n}" for c, n in sorted(engine_summary["agent_classes"].items())
        )
        # codeql[py/clear-text-logging-sensitive-data]
        print(f"  Agent classes: {cls_str}")
    if engine_summary.get("gender_distribution"):
        g_str = "  ".join(
            f"{g}={n}" for g, n in sorted(engine_summary["gender_distribution"].items())
        )
        # codeql[py/clear-text-logging-sensitive-data]
        print(f"  Gender: {g_str}")
    print(f"  Zones: {', '.join(z['name'] for z in engine.zones)}")
    print("  VSP isolation: counter-driven (engine-internal disabled)")
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
        total_instances = fleet.get("total_device_instances", fleet["total_monitored"])
        print(f"  Total device instances: {total_instances}")
        for did, dev in fleet["devices"].items():
            channels = ", ".join(dev["channels"])
            print(f"  Device: {did:20s}  channels: {channels}")
        deployment = fleet.get("device_deployment_counts", {})
        if deployment:
            print("  Device deployment:")
            for did, count in deployment.items():
                print(f"    {did:25s}  × {count}")
        vis = fleet.get("visibility_breakdown", {})
        if vis:
            parts = [f"{k}={v}" for k, v in vis.items() if v > 0]
            if parts:
                print(f"  Visibility: {', '.join(parts)}")
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


def _print_pathogen_profile(pid: str, prof: dict[str, Any]) -> None:
    print(f"    {pid:20s}  {prof['name']}")
    print(f"      Category: {prof.get('category', '?')}")
    print(f"      Routes:   {', '.join(prof.get('transmission_routes', []))}")
    intro = prof.get("introduction_epoch", 0)
    print(f"      Intro:    epoch {intro}")
    fc = prof.get("food_contamination", {})
    if fc.get("enabled"):
        gr = fc.get("growth_rate_per_day", fc.get("growth_rate_per_epoch", 0))
        dr = fc.get("decay_rate_per_day", fc.get("decay_rate_per_epoch", 0))
        print(f"      Food contam: growth={gr}/day  decay={dr}/day")
    ec = prof.get("environmental_contamination", {})
    if ec.get("enabled"):
        src = ec.get("source_type", "?")
        p2p = ec.get("person_to_person", True)
        bl = ec.get("baseline_environmental_load", 0)
        print(f"      Env contam:  source={src}  load={bl}  "
              f"person-to-person={'yes' if p2p else 'no'}")
    mf = prof.get("microflora_disruption", {})
    if mf.get("causes_disruption"):
        print(f"      Microflora disruption: {mf.get('disruption_type')} "
              f"(mag={mf.get('disruption_magnitude', 0)})")


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
            _print_pathogen_profile(pid, prof)
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
    print("    ENV 1. Continuous Air Sniffer   (aerosol Ct)")
    print("    ENV 2. Targeted Surface Swab    (fomite PCR + compliance variance)")
    print("    ENV 3. Wastewater Seq Grid      (Dirichlet-multinomial metagenomics)")
    print("    CLN 4. Clinical RDT             (lateral-flow antigen, binary)")
    print("    CLN 5. Clinical qPCR            (patient viral load Ct)")
    print("    CLN 6. Clinical Microbiology    (culture/staining, flora shifts)")
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
        exempt = sp.modifiers.get("exempt_classes", [])
        if exempt:
            print(f"      Exempt:  {', '.join(exempt)}")
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

    status_icon = {
        "BASELINE": "●",
        "ALERT": "◆",
        "SUSPECTED": "▲",
        "CONFIRMED": "■",
        "LOCKDOWN": "✖",
    }.get(trigger_status, "?")

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

def _executive_epidemiology_rows(
    row: Any,
    thin_div: str,
    *,
    num_agents: int,
    engine_summary: dict[str, Any],
    trigger_status: str,
) -> list[str]:
    return [
        row("EPIDEMIOLOGICAL METRICS"),
        thin_div,
        row(f"Total crew:          {num_agents}"),
        row(
            f"Total infected:      "
            f"{engine_summary['infected'] + engine_summary['recovered'] + engine_summary['isolated']}"
        ),
        row(f"  Currently infected: {engine_summary['infected']}"),
        row(f"  Recovered:          {engine_summary['recovered']}"),
        row(f"  Isolated:           {engine_summary.get('isolated', 0)}"),
        row(f"  Quarantined:        {engine_summary.get('quarantined', 0)}"),
        row(f"  Immune (neg sec):   {engine_summary['immune']}"),
        row(f"  Symptomatic:        {engine_summary['symptomatic']}"),
        row(f"Final status:        {trigger_status}"),
    ]


def _format_counter_threshold(
    cid: str,
    threshold: Any,
    exceeded: bool,
) -> str:
    if threshold is None:
        return ""
    if "rate" in cid:
        return f"  thr={threshold:.1%}  {'EXCEEDED' if exceeded else 'ok'}"
    return f"  thr={threshold}  {'EXCEEDED' if exceeded else 'ok'}"


def _executive_counter_rows(
    row: Any,
    thin_div: str,
    infection_counters: dict[str, dict[str, Any]],
) -> list[str]:
    lines = [row(), row("INFECTION COUNTERS"), thin_div]
    for cid, cdata in infection_counters.items():
        label = cdata.get("label", cid)
        value = cdata.get("value", 0)
        pop = cdata.get("population", 0)
        threshold = cdata.get("threshold")
        exceeded = cdata.get("exceeded", False)
        val_str = f"{value:.1%}" if "rate" in cid else f"{value:.0f}"
        thr_str = _format_counter_threshold(cid, threshold, exceeded)
        lines.append(row(f"  {label:30s} {val_str:>8s}  (n={pop}){thr_str}"))
    return lines


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
    quarantined_count: int = 0,
    refuser_count: int = 0,
    pathogen_profiles: dict[str, Any] | None,
    infection_counters: dict[str, dict[str, Any]] | None = None,
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
    lines.extend(_executive_epidemiology_rows(
        row, thin_div, num_agents=num_agents,
        engine_summary=engine_summary, trigger_status=trigger_status,
    ))

    if infection_counters:
        lines.append(thin_div)
        lines.extend(_executive_counter_rows(row, thin_div, infection_counters))

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
    confined = isolated_count + quarantined_count
    lines.append(row(f"Isolated: {isolated_count}  Quarantined: {quarantined_count}  Total confined: {confined}/{num_agents}   Non-compliant: {refuser_count}"))
    lines.append(bottom)

    print()
    # codeql[py/clear-text-logging-sensitive-data]
    print("\n".join(lines))
