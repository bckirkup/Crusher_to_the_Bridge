# Devin Task: HVAC Recirculation Topology Fix (Star → Plenum)

> **Status:** Implemented (merged). Native + ContamX AHS use AHU star topology;
> see [CONTAM_INTEROP.md](../CONTAM_INTEROP.md). This file is the design brief.

## Problem

The native transport engine (`py_contam_bridge.py`) builds HVAC recirculation
as N×N direct room-to-room paths for all rooms sharing an AHU. This creates
(N-1)× too much inter-room mixing compared to real HVAC physics and CONTAM.

### Current (wrong): Complete graph

For an AHU with rooms {A, B, C}, the current code creates 6 paths:
```
A → B: Q_recirc  (filtered)
A → C: Q_recirc  (filtered)
B → A: Q_recirc  (filtered)
B → C: Q_recirc  (filtered)
C → A: Q_recirc  (filtered)
C → B: Q_recirc  (filtered)
```

Each path carries `Q_recirc = (1-OA) × ACH × ΣV × duty / N²` m³/h.
Total pathogen mixing: N(N-1) paths → massively over-mixed.

### Correct: Star through AHU plenum

Real HVAC and CONTAM's AHS model:
```
A → Plenum (return): Q_return = ACH × V_A × duty
B → Plenum (return): Q_return = ACH × V_B × duty
C → Plenum (return): Q_return = ACH × V_C × duty
    Plenum mixes returns, applies filter, adds outdoor air
Plenum → A (supply): Q_supply = ACH × V_A × duty  (filtered)
Plenum → B (supply): Q_supply = ACH × V_B × duty  (filtered)
Plenum → C (supply): Q_supply = ACH × V_C × duty  (filtered)
```

The plenum has zero volume — returned air mixes instantly, the filter
removes a fraction of pathogen, outdoor air dilutes, and the supply
redistributes to all rooms proportional to their design flow.

This is a **star topology** with 2N paths, not a complete graph with
N(N-1) paths.

### Measured impact

ContamX (correct physics) vs native engine (over-mixed), destroyer
baseline, 1M copies injected in Bridge, 24 epochs:

| Zone | Native (copies) | ContamX (copies) | Ratio |
|------|----------------|-----------------|-------|
| Bridge | 962 | 124 | 7.8× |
| MedBay | 0 | 0 | — |
| Mess_Hall | 3,411 | 1 | 5,292× |
| Engine_Room | 1,072 | 25 | 43× |
| Galley | 0 | 2 | — |
| Berthing | 3,415 | 24 | 140× |

The native engine retains 50× more total pathogen and distributes it
to zones that should receive almost nothing. The native engine also
shows numerical oscillations from over-extraction.

## Fix

### 1. Add virtual plenum zones

In `ContamTransportEngine.__init__` or `_build_hvac_recirculation_paths`,
create a virtual zone node for each HVAC zone:

```python
for hvac_zone in airflow['hvac_zones']:
    plenum_id = f"_plenum_{hvac_zone['id']}"
    self.zone_nodes[plenum_id] = ContamZoneNode(
        zone_id=plenum_id,
        volume_m3=0.001,  # near-zero but not zero (avoids /0)
        temperature_K=293.15,
    )
```

The plenum volume should be very small (0.001 m³ = 1 liter) so it
doesn't accumulate mass — it's a mixing junction, not a real space.

### 2. Replace N×N paths with star paths

Currently in `_build_hvac_recirculation_paths`:
```python
# CURRENT (wrong): N×N complete graph
for room_i in rooms:
    for room_j in rooms:
        if room_i != room_j:
            paths.append(ContamAirflowPath(
                from_zone=room_i, to_zone=room_j,
                flow_rate_m3h=q_recirc_per_pair,
                is_hvac_ducted=True, ...))
```

Replace with:
```python
# CORRECT: star through plenum
plenum_id = f"_plenum_{hvac_zone['id']}"
total_design_flow = ach * sum_volume  # m³/h at full duty
oa_fraction = ...  # per-AHU or default
duty = ...

for room in rooms:
    room_volume = zone_volumes[room]
    # Flow proportional to room volume (balanced AHS)
    room_flow = total_design_flow * (room_volume / sum_volume) * duty

    # Return: room → plenum (unfiltered)
    paths.append(ContamAirflowPath(
        from_zone=room,
        to_zone=plenum_id,
        flow_rate_m3h=room_flow,
        is_hvac_ducted=False,  # no filter on return
        path_type='hvac_return',
        path_id=f'{hvac_zone["id"]}_ret_{room}',
    ))

    # Supply: plenum → room (filtered, reduced by OA dilution)
    # The supply carries recirculated air (1-OA fraction) + outdoor air.
    # Only the recirculated fraction carries pathogen from the plenum.
    # Outdoor air has zero pathogen.
    # So the effective pathogen flow is: room_flow × (1 - OA)
    # But physically the TOTAL airflow (supply = return) is room_flow.
    # The filter acts on the recirculated fraction only.
    #
    # Implementation: supply path carries room_flow × (1-OA),
    # marked as HVAC-ducted (filter applies).
    # The OA fraction is "lost" pathogen (diluted by clean outdoor air).
    supply_flow = room_flow * (1.0 - oa_fraction)
    paths.append(ContamAirflowPath(
        from_zone=plenum_id,
        to_zone=room,
        flow_rate_m3h=supply_flow,
        is_hvac_ducted=True,  # filter applies here
        path_type='hvac_supply',
        path_id=f'{hvac_zone["id"]}_sup_{room}',
    ))
```

### 3. Mass balance verification

For a single-AHU, single-room system (N=1):
- Return: room → plenum at Q
- Supply: plenum → room at Q×(1-OA) (filtered)
- Net removal per epoch: room loses Q×C×dt, gains Q×(1-OA)×(1-η)×C×dt
- Net: C_new = C × [1 - Q×dt × (1 - (1-OA)(1-η))]
- = C × [1 - Q×dt × (OA + (1-OA)×η)]
- This is correct: OA dilution + filter removal both reduce pathogen.

For N rooms:
- Each room sends air to the plenum.
- Plenum mixes all returns: C_plenum = Σ(Q_i × C_i) / Σ(Q_i)
- Supply to each room carries C_plenum × (1-η).
- Rooms with high pathogen load export to the plenum; clean rooms
  receive diluted pathogen. This is the correct physics.

### 4. Transport step: plenum mass balance

The existing `transport_step` will automatically handle the plenum
because it's a zone with paths. However, because the plenum has
near-zero volume, its concentration spikes enormously for even small
mass. To prevent numerical issues:

Option A: After each transport step, zero out plenum mass (treat it
as a pass-through node that doesn't retain anything):
```python
for zone_id in result:
    if zone_id.startswith('_plenum_'):
        result[zone_id] = 0.0
```

Option B: Don't include plenums in `zone_pathogen_mass` at all.
Instead, compute the plenum concentration analytically each step:
```python
# In transport_step, before processing supply paths:
plenum_mass = sum(return_path.flow × concentration[room] × dt
                  for return_path in plenum_returns)
plenum_conc = plenum_mass / sum(return_flow_rates) / dt  # mixing concentration
```

**Recommend Option A** — simpler, and the mass-cap logic already
prevents over-extraction. The plenum starts at zero each step
because all its mass was supplied to rooms in the previous step.

### 5. Exclude plenums from epidemic model

The plenum zones should not appear in:
- Agent location assignments (no one is "in the plenum")
- Dose-response calculations
- Zone concentration reports
- Dashboard visualizations

Add a `is_virtual` flag or check for the `_plenum_` prefix.

## Files to modify

1. `../../engines/py_contam_bridge.py`:
   - `_build_hvac_recirculation_paths()` — replace N×N with star topology
   - `__init__` — create plenum zone nodes
   - `transport_step()` — zero plenum mass after each step
   - `get_transport_summary()` — exclude plenums from summary

2. `../../engines/contamx_transport.py`:
   - Verify ContamX engine already uses the star topology (it does —
     AHS synthesis creates supply/return paths through phantoms)
   - No changes expected

3. `../../orchestrator_init.py` / `../../orchestrator_epoch.py`:
   - Exclude `_plenum_` zones from agent placement and dose calculations

4. `tests/`:
   - Update recirculation tests to expect star topology
   - Add test: single-zone AHU produces same result as before
   - Add test: multi-zone AHU produces LESS mixing than N×N
   - Add test: plenum mass is zero after each step
   - Add test: native vs ContamX concentration agreement on destroyer

## Expected outcome

After this fix, the native engine and ContamX should agree to within
~10-20% on zone concentrations for AHS-dominated platforms (destroyer,
Enterprises). Remaining differences come from:
- Adjacency orifice flows (ContamX pressure-driven vs native prescribed)
- Duct pressure drops (ContamX only)
- Temporal resolution (ContamX sub-minute vs native 1-hour epochs)

The 50× over-mixing should drop to <2× disagreement.

## Epidemiological impact

This fix will REDUCE transmission rates in the native engine by
approximately (N-1)× for each HVAC zone, where N is the number of
rooms per AHU. For the mega cruise:
- 14-room dining AHU: 13× reduction in inter-room pathogen mixing
- 6-room atrium AHU: 5× reduction
- 9-room cabin deck AHUs: 8× reduction

The net effect is that outbreaks simulated with the native engine will
be SLOWER and more spatially localized — closer to reality and to
ContamX. Previous outbreak simulations with the native engine were
over-predicting airborne transmission.
