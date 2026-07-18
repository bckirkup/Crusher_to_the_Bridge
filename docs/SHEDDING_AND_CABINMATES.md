# Shedding Variance and Cabin-Mate Parameterization

> **Status:** Implemented. Living summary also in [AGENTS.md](AGENTS.md) caveats.
> Platform cabin layout notes: [PLATFORM_CABIN_REVISION.md](PLATFORM_CABIN_REVISION.md).

## 1. Per-Agent Shedding Variance

### Mechanism
At infection time, each agent draws a shedding multiplier from a log-normal distribution:
```
agent.shedding_multiplier = 10^(rng.normal(0, shedding_variance_log10))
```
This multiplier persists for the duration of infection and scales all shedding output.
A multiplier of 1.0 (the median) gives the baseline curve value. A multiplier of 10
means 10x higher shedding. A multiplier of 0.1 means 10x lower.

The shedding function becomes:
```
shedding = 10^(curve[dpi] - dose_adjustment) * agent.shedding_multiplier
```

### Parameters per pathogen (add to pathogen profile JSON)

Based on published QMRA and epidemiological data:

| Pathogen | shedding_variance_log10 | Source / Rationale |
|---|---|---|
| norovirus_gii4 | 1.5 | Teunis et al 2015: fecal shedding ranges 10^4 to 10^11 copies/g across individuals. Atmar et al 2008 volunteer study: ~3 log10 IQR. Asymptomatic shedders at lower end. |
| sars_cov2_resp | 1.2 | Kissler et al 2021 (eLife): peak viral loads vary ~2-3 log10 across individuals. Chen et al 2021 (PMC): 20% of individuals responsible for 80% of transmission. |
| influenza_a | 1.0 | Ip et al 2017 (JID): heterogeneity in shedding, ~2 log10 range in peak viral load. Leung et al 2020: aerosol shedding varies ~2 log10 between individuals. |
| measles_virus | 0.8 | Less documented. Moderate variation expected. |
| legionella_pneumophila | 0.5 | Environmental source, not person-to-person shedding. Low individual variation — the exposure is from the water system, not the patient. |
| vibrio_cholerae_parahaemolyticus | 1.0 | Foodborne point-source. Individual susceptibility varies more than shedding. |
| campylobacter_jejuni | 1.0 | Similar to Vibrio — foodborne, moderate shedding variation. |
| clostridioides_difficile | 1.5 | Asymptomatic carriers shed highly variable amounts. Curry et al 2013: carrier shedding ranges >3 log10. |
| andes_hantavirus | 1.0 | Limited data. Moderate assumption. |
| ebola_virus | 1.5 | Extreme viral load variation documented. Towner et al 2004: peak viremia ranges 10^5 to 10^10. |

### Implementation
In `KorkinAgent.infect_with_pathogen()`:
- Draw `shedding_multiplier = 10 ** rng.normal(0, profile.get('shedding_variance_log10', 0.0))`
- Store in `inf['shedding_multiplier']`
- In `get_pathogen_shedding()`: `return math.pow(10, curve[idx] - adj) * inf.get('shedding_multiplier', 1.0)`

Default `shedding_variance_log10 = 0.0` preserves backward compatibility (no variance).

## 2. Cabin-Mate Tracking

### Mechanism
At simulation initialization, assign each agent 1-3 cabin-mates based on cabin occupancy:
- Passenger standard cabins: 2 per cabin (1 cabin-mate)
- Passenger family cabins: 3-4 per cabin
- Crew cabins: 2-4 per cabin (shared berths)
- Suites: 2-5 per cabin

### Implementation
In `ShipSimulation._init_agents()` or equivalent:
```python
# Group agents by home_zone (cabin corridor)
agents_by_zone = defaultdict(list)
for agent in agents:
    agents_by_zone[agent.home_zone].append(agent)

# Within each corridor, pair agents into cabins
for zone, zone_agents in agents_by_zone.items():
    cabin_size = get_cabin_size(zone)  # 2 for standard, 3-4 for family/crew
    for i in range(0, len(zone_agents), cabin_size):
        cabin_group = zone_agents[i:i+cabin_size]
        cabin_ids = {a.agent_id for a in cabin_group}
        for a in cabin_group:
            a.cabin_mate_ids = cabin_ids - {a.agent_id}
```

### Transmission modification
In `_pathway_direct_contact()`:
When a target is confined (`_cabin_confinement_active(target)`):
- If shedder is in `target.cabin_mate_ids`: full dose (they share the cabin)
- Else: dose *= 0.01 (minimal hallway encounter through closed door)

Replace the current uniform `confinement_isolation_factor = 0.05` with:
```python
if self._cabin_confinement_active(target):
    if shedder.agent_id in target.cabin_mate_ids:
        pass  # full contact — they share the cabin
    else:
        dose *= 0.01  # near-zero contact through closed door
```

Similarly, a confined SHEDDER only transmits at full rate to cabin-mates:
```python
if self._cabin_confinement_active(shedder):
    if target.agent_id in shedder.cabin_mate_ids:
        pass  # full shedding to cabin-mate
    else:
        dose *= 0.01  # minimal corridor contamination
```

### Cabin size configuration
Add to zone metadata in spatial_layout.json:
```json
{"id": "PC_D6_P_F", "cabin_size": 2, ...}
```
Or derive from zone type:
- Pax_Corridor zones: cabin_size = 2
- Crew_Corridor zones: cabin_size = 3
- Suite-designated zones: cabin_size = 4

### Impact
This makes individual confinement meaningful: a confirmed case confined to their
cabin transmits only to their 1 cabin-mate, not to 59 corridor neighbors.
The HVAC pathway is unaffected — HVAC air reaches all cabins on the corridor
regardless of door state.
