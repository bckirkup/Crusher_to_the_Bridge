# Contact Model Revision: Density-Dependent Contact Scaling

> **Superseded by PR #329:** The former `total_shedding / n_occupants` zone-average
> dose applied aerosol-style dilution to physical contact. It created an
> `n^(α−1)` per-capita dilution artifact, so per-capita exposure fell as hull
> size increased. PR #329 replaced that path with per-partner contact draws,
> now the default `transmission.contact_mode`. `density_dependent`,
> `heterogeneous_zone_dose`, and `legacy` remain selectable historical or
> sensitivity modes. Hull-specific dose adjustments are **not** the model's
> answer to the hull gradient: one pathogen profile and one dose must serve all
> hull classes.

## For: Crusher to the Bridge — Implementation Spec

### Problem

The current contact model uses a fixed contact pool (`AVG_R_POOL = [1,2,1,2,1,1,1,2,1,1,1,2]`,
mean 1.33) inherited from Korkin's Person.java. This is frequency-dependent transmission:
`dose = total_shedding / n_occupants * r0_draw`. Per-person dose is inversely proportional
to zone occupancy — a 500-person buffet gives the same per-person risk as a 5-person library.

This produces platform-dependent calibration: dose_adj=12 for mega (7000 pax) but dose_adj=18
for expedition (450 pax) to match VSP data. The same pathogen parameters should work across
all ship sizes — the contact structure should account for the difference.

### Root Cause

Larger ships have more agents per zone. With frequency-dependent transmission, more agents
per zone → lower per-person dose → lower AR at the same dose_adj. The model needs
density-dependent contacts: more people in a space → more close contacts per person.

### Design

#### Config selection

In `crusher_labs/config.yaml`:
```yaml
transmission:
  contact_mode: "per_partner_contact"  # "per_partner_contact" | "density_dependent" | "heterogeneous_zone_dose" | "legacy"
  # Legacy: fixed AVG_R_POOL draws (Korkin default, frequency-dependent)
  # density_dependent: effective contacts scale with zone occupancy

  # Density-dependent parameters
  density_dependent:
    reference_occupancy: 50            # occupancy at which contacts = base_contacts
    base_contacts: 1.33               # mean contacts at reference_occupancy (matches legacy)
    max_contacts: 20                   # cap on contacts per agent per zone per epoch
    exponent: 0.5                      # α: contacts = base * (n/ref)^α

    # Role-specific overrides
    crew_contact_multiplier: 2.0       # food employees on shift in their service zone contact more people
                                       # (they serve many passengers sequentially)
```

#### Core change in `engines/transmission_core.py`

Replace the fixed `r0_draw` with an occupancy-dependent draw:

```python
# Current (legacy):
r0_draw = int(self.rng.choice(AVG_R_POOL))

# New (density_dependent):
def _effective_contacts(self, n_occupants: int, agent: KorkinAgent) -> int:
    cfg = self.density_cfg
    ref = cfg["reference_occupancy"]
    base = cfg["base_contacts"]
    alpha = cfg["exponent"]
    max_c = cfg["max_contacts"]

    # Scale contacts with occupancy
    raw = base * (n_occupants / ref) ** alpha

    # Crew multiplier in service zones
    if agent.role == "crew" and agent.current_location in self._service_zones:
        raw *= cfg.get("crew_contact_multiplier", 1.0)

    # Cap and draw
    mean_contacts = min(raw, max_c)
    # Poisson draw around the mean for stochasticity
    return max(0, int(self.rng.poisson(mean_contacts)))
```

Then in `_pathway_direct_contact`:
```python
# Replace:
r0_draw = int(self.rng.choice(AVG_R_POOL))

# With:
if self.contact_mode == "density_dependent":
    r0_draw = self._effective_contacts(n_occupants, target)
else:
    r0_draw = int(self.rng.choice(AVG_R_POOL))
```

The dose formula stays the same: `dose = total_shedding / n_occupants * r0_draw`.
The density dependence enters through r0_draw scaling with n_occupants.

Net effect: dose ∝ total_shedding / n_occupants * (n_occupants/ref)^α
         = total_shedding * n_occupants^(α-1) / ref^α

At α=0: dose ∝ total_shedding / n_occupants (pure frequency-dependent, legacy)
At α=0.5: dose ∝ total_shedding / sqrt(n_occupants) (intermediate)
At α=1: dose ∝ total_shedding (pure density-dependent, dose independent of occupancy)

#### Initialization

In `engines/transmission_core.py` `__init__`:
```python
DEFAULT_DENSITY_CFG = {
    "reference_occupancy": 50,
    "base_contacts": 1.33,
    "max_contacts": 20,
    "exponent": 0.5,
    "crew_contact_multiplier": 2.0,
}
tx = (cfg or {}).get("transmission", {})
self.contact_mode = tx.get("contact_mode", "density_dependent")
self.density_cfg = {**DEFAULT_DENSITY_CFG, **(tx.get("density_dependent") or {})}
# Service zones: type == "Dining" or "Galley" in zone id (from zone_types)
```

#### Service zone identification

Crew in dining zones (waiters, galley workers) have fundamentally different contact
patterns than passengers. A waiter contacts 30-50 passengers per meal service.
A passenger contacts their tablemates (~6-8). The crew_contact_multiplier captures
this without needing a separate contact model for crew.

Service zones = all zones with type "Dining" or containing "Galley" in the ID.
Populated at engine initialization from the spatial layout.

The multiplier is a duty state, not a room (FOOD-ROLE-01): it applies to a
food employee — crew whose work zone is a service zone, the same definition the
VSP duty exclusion uses (`engines/crew_duty_exclusion.is_food_employee`) —
while the schedule has that agent at `Work` in its own work zone. Crew eating
in `CrewMess` or any dining room are diners, and take the diner rate. The same
rule gates `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR` and
`FOOD_HANDLER_CONTACT_MULTIPLIER` in the fomite and food routes.

### Campaign parameters for calibration

The key parameter to sweep is `exponent` (α):
```
transmission.density_dependent.exponent: [0.0, 0.25, 0.5, 0.75, 1.0]
```

At each α, run the same dose_adj=15 across all 4 platforms. The α that produces
the same conditional AR (~7%) on all platforms is the correct density scaling.

Also sweep crew_contact_multiplier to check sensitivity:
```
transmission.density_dependent.crew_contact_multiplier: [1.0, 2.0, 3.0, 5.0]
```

### Calibration campaign tier

```json
{
  "c5_density_calibration": {
    "description": "Density-dependent contact model calibration",
    "platforms": ["expedition_cruise_450", "classic_cruise_1900", 
                  "spirit_cruise_3000", "mega_cruise_5000"],
    "pathogen": "norovirus",
    "dose_adjustments": [12, 15, 18],
    "density_exponents": [0.0, 0.25, 0.5, 0.75, 1.0],
    "pre_immunity_fractions": [0.0, 0.2],
    "surveillance_strategies": ["none_true", "syndromic"],
    "initial_infected_values": [1],
    "epochs": 168,
    "seeds": [700, 701, 702, 703, 704, 705, 706, 707, 708, 709,
              710, 711, 712, 713, 714]
  }
}
```

Runs: 4 platforms × 3 dose_adj × 5 α × 2 immunity × 2 surveillance × 15 seeds = 3,600

### Tests

1. `test_legacy_contact_mode_unchanged`: with contact_mode="legacy", output matches
   existing behavior exactly (r0_draw from AVG_R_POOL)
2. `test_density_dependent_contacts_scale`: at α=0.5, doubling occupancy increases
   effective contacts by ~41%
3. `test_density_dependent_alpha_zero_matches_legacy`: α=0.0 should produce identical
   effective contacts as legacy mode (1.33 mean regardless of occupancy)
4. `test_crew_multiplier_applies_in_dining`: crew agents in Dining zones get
   multiplied contacts; crew in cabins do not
5. `test_max_contacts_cap`: contacts never exceed max_contacts even at high occupancy
6. `test_campaign_generator_c5`: dry-run produces correct run count

### Backward compatibility

- Default contact_mode is **per_partner_contact** (new model); set
  `contact_mode: legacy` to restore fixed AVG_R_POOL draws
- The density_dependent config block is optional; missing keys fall back to defaults
- Campaign manifests can override contact_mode / exponent per-tier via config_overrides

---

## Optional second stage: `heterogeneous_zone_dose`

Lasso-style optional layer (not default). Keeps the density-dependent mean
dose, then multiplies each susceptible’s direct-contact dose by a **mean-1
lognormal** within-zone exposure factor. Captures “roll of the dice” inside a
space without pretending to know plume geometry.

```yaml
transmission:
  contact_mode: "heterogeneous_zone_dose"   # opt-in; default remains density_dependent
  heterogeneous_zone_dose:
    sigma_by_zone_type:
      Cabin_Corridor: 0.25   # low — high within-stateroom mixing uniformity
      Dining: 1.0            # high
      Free: 0.75             # medium-high
    sigma_service: 1.0       # Galley / service IDs (high)
    default_sigma: 0.75
```

Factor: `exp(N(-σ²/2, σ))` so `E[factor] = 1`. Density mean is preserved in
expectation; only the within-zone variance changes.

Zone-type intent:

| Space | Heterogeneity | σ default |
|-------|---------------|-----------|
| Cabin_Corridor | low | 0.25 |
| Dining | high | 1.0 |
| Free / common | medium-high | 0.75 |
| Galley / service | high | 1.0 (`sigma_service`) |

Use for sensitivity only: compare conclusions under `density_dependent` vs
`heterogeneous_zone_dose` at a pinned α / dose_adj (see campaign tier
`c6_heterogeneous_sensitivity`). Empirically: reject inherited Korkin kernel →
test density-dependent across platforms → test whether within-zone stochasticity
materially changes conclusions (realism vs overfitting).

---

## `CONTACT-SCALE-01`: class-directed scaling under `per_partner_contact`

**Status: implemented, off by default** (`transmission.contact_class_exponent`,
default `0.0`, which is the shipped model and the same code path).

The default mode draws a host's contacts from POLYMOD 13.4/day and lets the zone
decide only *who* the partners are, uniformly over co-located occupants — the
`φ = 0` end of this document's axis, in the aggregate. Shirreff et al. 2024
(*Epidemics* 47:100807, 2,114 proximity-sensor wearers, 15 hospital wards,
33,946 contacts) fits `c = a(φ)·N^φ` ward by ward against the number of persons
present and finds the aggregate frequency-dependent — so the fixed daily total
stands as measured and is **not** rescaled here — while contacts *directed at a
subpopulation* scale with that subpopulation's density, above unity in several
wards and below zero in a few.

So the exponent divides a draw whose size it never changes:

```yaml
transmission:
  contact_class_exponent: 0.0   # φ; 0 = the shipped uniform draw, bit-identical
```

- a target's classes are the passenger/crew roles **eligible in its own pool**,
  which is the table party, the rest of the dining room, the cabin, or the zone,
  whichever the target is drawing from;
- class `c` receives `N_c^(1+φ)` of the draw, normalised over the classes
  present — the `+1` because `N_c` eligible partners already hold `N_c` of the
  uniform draw's weight, so `φ = 0` reproduces the share-of-the-room draw
  exactly;
- each class's share is then sampled from that class's own pool by the unchanged
  hypergeometric draw, so partners stay distinct and present;
- a pool with one class present keeps the uniform path at every `φ`, consuming
  no extra RNG.

`φ` is a **declared swept axis**, not a value: nothing measures it for a dining
room, a crew mess or a cruise ship, and the ward exponents differ by pair type,
by ward and between day and night. The configured `[-2, 3]` is a refusal band
around the reported posteriors, not an interval. `φ` may not be chosen because
it moves an anchor — this is the first mechanism by which passenger density can
reach the crew arm, which makes the sweep the test.

Invariants held by `tests/test_contact_class_scaling.py`: default and `φ = 0`
run-identical; one class present identical at every `φ`; a rising `φ` directs
monotonically fewer contacts at the sparser class; `n_contacts ≤ r0_draw`
always, with equality whenever no class's pool is exhausted; doses finite and
non-negative; partners distinct and present; weights normalised.

---

## `CONTACT-ARCH-01`: the draw derived from the schedule and the architecture

**Status: implemented, off by default** (`transmission.activity_contacts`;
absent or `enabled: false` is the uniform POLYMOD draw above on the same code
path). Specified in [contact_architecture_spec.md](contact_architecture_spec.md)
with the sourcing in
[tranche 37](literature/consensus_tranche_37_contact_architecture.md).

POLYMOD 13.4/day stays in this document, and in the tree, as the
general-population reference and the control arm. What `CONTACT-ARCH-01` adds
is the alternative generator: the schedule token, the zone type, the mixing
unit and the duty state resolve one of eight activities (`cabin`, `corridor`,
`work_service`, `work_other`, `dining_table`, `dining_venue`, `leisure`,
`other`), and the run declares each activity's rate in distinct partners per
hour — a number or a `{passenger, crew}` mapping. Enabling the block without
every activity declared is refused; nothing in the engine supplies a default
rate. The partner sampler, table party, cabin compartment, hallway residual
and `φ` are unchanged; only the count a target draws in each unit differs.
