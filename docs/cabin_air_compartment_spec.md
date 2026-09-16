# AERO-CABIN-01: the stateroom is the air unit inside a cabin corridor

> **Status:** **Implemented, off by default** —
> `transmission.cabin_air_mode` in `engines/transmission_core.py`, with
> `zone_pool` (the default, and an absent key) taking the pre-change
> whole-corridor code path and `cabin_compartment` running the short-range
> inhalation route on staterooms. **No constant is added, moved or fitted**: a
> stateroom's dilution volume is its berth share of the block volume the hull
> already declares, so the partition conserves declared geometry and invents no
> cabin volume. Filed pathogen-general; measurable only on a continuously
> emitting arm (see §5).

## 1. The defect

`BERTH-01` (#475) made the stateroom the direct-contact unit and gave it its
own surface pool. `AERO-NEAR-01` (`near_field_air`) added a near-field *bonus*
for a cabin mate on top of the corridor pool. Neither changed the unit the
inhalation route runs on: `_pathway_droplet` grouped occupants by ship zone, so
inside a `Cabin_Corridor` every occupant breathed one 900–1,200 m³ pool shared
with ~35 other people, whether or not they shared a stateroom.

That is not a detail on a quarantined ship. Under cabin confinement the model
attenuates emission and inhalation by `confinement_isolation_factor`
(0.05 × 0.05), and then leaves the attenuated remainder pooled across the whole
block for the rest of the voyage. Measured on Diamond Princess (COVID arm,
Θ = 3.16e7, seed 20200216, full voyage): of the droplet dose accumulated by the
2,039 passengers infected in a `Cabin_Corridor` after the 5 February
confinement, **92% arrived through shared block air and 8% through the
cabin-mate add-back**. Six days at 24 h/day against several 1e9-copy shedders
beats a 400× attenuation, so confinement did not bound the outbreak: incidence
peaked *inside* the quarantine. The published record is the opposite.

`confinement_isolation_factor` cannot express the repair, because it scales
every occupant of the block together — the archetype recorded in
`.agents/skills/model-parameter-provenance/SKILL.md` ("cabins are not
environmental compartments … ~37 people in 800 m³ where reality is 2 people in
~40 m³"), and open item 8 of the norovirus ledger, whose air half `BERTH-01`
explicitly left undone.

## 2. What the mode does

`transmission.cabin_air_mode: cabin_compartment` groups a `Cabin_Corridor`'s
occupants into the staterooms `BERTH-01` already assigns — the same
`_cabin_compartments` split the direct-contact and fomite routes use, keyed by
`cabin_mate_ids`, so no new membership rule and no new declaration is
introduced. Each stateroom is then one air unit: its occupants breathe the
aerosol its own occupants emit, and nobody else's.

Four properties, each carried by a test in
`tests/test_cabin_air_compartments.py`:

1. **Volume is partitioned, not invented.** A stateroom's dilution volume is
   `V_block × berths / Σ berths`, from the berthing plan read off the roster
   once at initialisation (`register_cabin_berths`), so it is the same on an
   epoch when half the block is at dinner as on an epoch when nobody is. The
   partition sums to the block's declared `volume_m3` exactly. This is what
   keeps the change clear of the one magnitude `AERO-NEAR-01`'s sourcing
   tranche returned **∅ null** on (the near-field effective volume): nothing
   here is measured or chosen, only divided.
2. **The drift route reads the same air.** Emitted mass is credited to the
   parent ship zone, as before, so `_pathway_hvac_airborne` and the aerosol
   reservoir see the whole block's emission at unchanged magnitude. Only the
   *inhaled* concentration is local. No emission is created or destroyed.
3. **The cabin mate is unattenuated, once.** The far-field term inside the
   stateroom carries both confinement factors and
   `_cabin_mate_droplet_addback` restores exactly the withheld remainder, so a
   mate's total is the unattenuated dose at the stateroom's volume — the sum is
   the pre-existing composition applied to a smaller unit, not a second dose.
4. **Everything outside a cabin corridor is untouched.** Dining rooms,
   corridors of other types, crew work zones and unconfined behaviour take the
   identical code path; a run with the default `zone_pool` writes the
   pre-change exposure payload field-for-field.

## 3. What it deliberately does not do

- **The hallway loses its airborne residual.** Two non-mates in a cabin
  corridor now share no air at all, where before they shared all of it. The
  corridor encounter survives as the direct-contact residual
  (`_direct_contact_units`, `DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR`) and the
  fomite pool, exactly as `BERTH-01` filed it. A corridor-air residual — a
  transient dose for someone passing through, at the block's volume — is a
  separate change and is not attempted here; the mode as written is therefore
  a *lower* bound on cabin-corridor airborne transmission.
- **No cabin geometry is declared.** The partition uses the block's volume, so
  a hull whose `Cabin_Corridor` volume is itself wrong stays wrong; that is a
  platform declaration, not this change.
- **Nothing is fitted.** The mode is off by default and measured against a
  matched baseline before any campaign reads it, on the rule the sanitary zones
  (`sanitary_visit_mode`), the near field (`retained_fraction`) and the droplet
  deletion (`droplet_emission_mode`) each shipped under.

## 4. Configuration

```yaml
transmission:
  cabin_air_mode: zone_pool   # default; the pre-change whole-corridor pool
  # cabin_air_mode: cabin_compartment
```

An undeclared value is a load error rather than a silent fallback.

## 5. Which arms it can move

Only an arm with a continuous respiratory emission share. An
`emesis_conditioned` profile (`norwalk_gi`) has `_droplet_emission_fraction`
0 under the default `droplet_emission_mode`, so every dose this route computes
is zero and the mode is a null by construction on the norovirus arm — measured,
not assumed (norovirus ledger item 44). The measurable arm is
`sars_cov2_resp`, whose out-of-sample check is the Diamond Princess plateau
after 5 February: a quarantine that bounds the outbreak rather than hosting it.

## 6. Tests the change carries

`tests/test_cabin_air_compartments.py`, in the shape
`.agents/skills/ci-test-design/SKILL.md` asks for (graded sensitivity and
invariants, goldens only as labelled change-detectors):

- the partition sums to the block volume; a four-berth cabin takes twice the
  air of a two-berth cabin; the share ignores who is aboard this epoch; an
  unregistered block falls back to the block volume (the pre-change dilution);
- a non-mate stops receiving the shedder's aerosol; the mate still receives it;
  the mate's dose rises by exactly the berth-share factor as the block is
  partitioned, and scales as declared block volume changes;
- the emitted mass credited to the parent zone is unchanged, so the drift route
  is untouched; confinement no longer carries the block;
- a non-cabin zone is bit-identical under both modes; the default is the
  pre-change pool; an undeclared mode raises.
