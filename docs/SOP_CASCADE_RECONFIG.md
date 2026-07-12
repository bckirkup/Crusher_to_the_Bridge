# SOP Cascade-Gating Reconfiguration

## Problem

The current SOP triggers depend on environmental instruments (air sniffer, wastewater, surface swab)
that never reach detection thresholds during realistic outbreaks. This means:
- PPE never deploys (SOP-004/005 gated on wastewater)  
- HEPA lockdown never activates (SOP-002 gated on air sniffer)
- Surface decon never triggers (SOP-003 gated on surface swab)

Confinement (SOP-008/009/010/011) fires from clinical/cascade triggers,
but without PPE, ventilation, or decon as supporting interventions.

## Principle

SOPs should activate in a staged escalation driven by the cascade tier system,
which is the only detection pathway that produces timely, actionable intelligence.
Environmental instruments remain as backstop triggers but the cascade provides
the primary activation pathway.

## Proposed Default SOP Configuration

### Tier 1 (Rapid Panel Positive — low regret, early)
- **SOP-004: PPE Standard** — crew in affected zones don PPE
- **SOP-006: Increased Diagnostic Cadence** — more frequent testing (already gated here)
- **SOP-013: Wearable Fleet Surveillance Escalation** (already gated here)

### Tier 2 (Confirmatory Test Positive — medium regret)
- **SOP-003: Surface Decontamination** — enhanced cleaning in zones where confirmed case was active
- **SOP-008: Individual Confinement** — confirmed case goes to cabin (already gated here)
- **SOP-010: VSP-Threshold Mass Isolation** (already gated here)
- **SOP-012: Wearable Individual Health Triage** (already gated here)

### Tier 3 (Full Confirmation — high regret, multiple cases)
- **SOP-002: HEPA Lockdown Ventilation** — cabin deck AHUs switch to high-filtration mode
- **SOP-005: PPE Full N95** — crew upgrade to N95 in all passenger zones
- **SOP-007: Galley Closure & Meal Isolation** — room service only (already gated here)
- **SOP-009: General Confinement** — all passengers to cabins (already gated here)
- **SOP-015/016: Integrated Detection Escalation** (already gated here)

### Fleet Escalation Rules (cascade_entry in diagnostic_cascade JSON)
Existing rules plus:
- **3+ crew at Tier 1** → SOP-004 (PPE Standard) — already exists
- **3+ agents at Tier 2** → SOP-003 (Surface Decon) + SOP-004 if not already active
- **5+ agents at Tier 2 OR 2+ at Tier 3** → SOP-002 (HEPA) + SOP-005 (N95)

### No Change (keep environmental triggers as parallel backstop)
- SOP-001: Enhanced Ventilation — continuous_air_sampler AMBER (if it ever fires)
- SOP-014: Wearable Fleet Outbreak Response — wearable_fleet_monitor RED (disabled by high thresholds in our runs)

### Wastewater Cadence
Change from 8 epochs to 4 epochs. Won't fire early enough to matter for SOPs,
but provides pathogen identification data that informs treatment decisions.

## Implementation

### In protocols.json:
Update `required_cascade_tier` for each SOP as specified above.

### In diagnostic_cascade_multiplex.json:
Add fleet escalation rules:
```json
{
    "rule_id": "fleet_tier2_decon",
    "description": "3+ agents at Tier 2 triggers surface decontamination",
    "tier_threshold": 2,
    "agent_count": 3,
    "category_filter": null,
    "pathogen_filter": null,
    "unlocked_sops": ["SOP-003", "SOP-004"]
},
{
    "rule_id": "fleet_tier2_ppe_escalation",
    "description": "5+ at Tier 2 or 2+ at Tier 3 triggers HEPA + N95",
    "tier_threshold": 2,
    "agent_count": 5,
    "category_filter": null,
    "pathogen_filter": null,
    "unlocked_sops": ["SOP-002", "SOP-005"]
}
```

### In config.yaml:
Update wastewater sequencing cadence from 8 to 4.

## Rationale

This configuration means:
1. First rapid-panel positive → crew put on gloves/masks (low cost, immediate)
2. First confirmatory positive → enhanced cleaning, individual confinement
3. Multiple confirmed cases → full engineering response (HEPA, N95, galley closure, general confinement)

The escalation is proportional to evidence. No mass lockdown without multiple confirmations.
No HEPA activation without clear multi-case outbreak. PPE deploys early because it's cheap
and low-regret.

## What This Replaces

The environmental instrument triggers remain in protocols.json as parallel backstops.
If the air sniffer ever reaches AMBER/RED independently, the corresponding SOP fires.
But the cascade tier gates are the primary pathway and will fire first in every scenario.
