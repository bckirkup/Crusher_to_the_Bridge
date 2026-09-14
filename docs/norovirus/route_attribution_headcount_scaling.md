# Which route carries the headcount scaling

**Status: measurement of record for `hull_compounding_route_v1`.** 1,800 runs,
Arm B only, same architecture, same 300 matched seeds per cell, occupancy
0.25 / 0.5 / 1.0 of declared complement, 7 days, baseline configuration.
AWS Batch `dd30e656-5aeb-48bc-a052-75964ebe6677`, 128/128 shards succeeded,
0 failed, 1,800/1,800 runs. **Nothing was fitted and no default moved**; this
campaign exists only to attribute the Arm B result of
[hull_compounding_v1](hull_compounding_v1_cells.md) to routes.

These cells are a **mechanism probe**. Away from declared complement they are
not a VSP/A9-scoreable posting rate and no posting, attack-rate or anchor claim
may be read off them.

## The answer

Dominant-route attribution of established infections, mean per voyage:

| platform | agents | imports | droplet | fomite | direct_contact | all other routes |
|---|---:|---:|---:|---:|---:|---:|
| classic | 478 | 1.08 | 0.400 (99.2%) | 0.003 (0.8%) | 0 | 0 |
| classic | 955 | 2.15 | 4.753 (91.4%) | 0.450 (8.6%) | 0 | 0 |
| classic | 1,910 | 4.37 | 24.443 (84.8%) | 4.390 (15.2%) | 0.003 | 0 |
| spirit | 750 | 1.75 | 1.163 (88.6%) | 0.150 (11.4%) | 0 | 0 |
| spirit | 1,500 | 3.49 | 6.013 (89.1%) | 0.733 (10.9%) | 0 | 0 |
| spirit | 3,000 | 7.04 | 49.200 (87.8%) | 6.817 (12.2%) | 0.007 | 0 |

`hvac_airborne`, `emesis_aerosol`, `food_contamination`,
`environmental_source` and the `unknown` fallback are **exactly zero in all six
cells**, across all 1,800 voyages.

Secondaries per import, quarter → full complement (a 4× headcount step), and
the exponent that implies:

| platform | route | per-import ×  | implied exponent | total × | implied exponent |
|---|---|---:|---:|---:|---:|
| classic | droplet | 15.05 | N^1.96 | 61.1 | N^2.97 |
| spirit | droplet | 10.50 | N^1.70 | 42.3 | N^2.70 |
| spirit | fomite | 11.27 | N^1.75 | 45.4 | N^2.75 |
| classic | fomite | (335) | — | (1,463) | — |

Classic fomite's quarter cell contains **one event in 300 voyages**, so its
ratio is a degenerate 1/1 and is excluded rather than reported. Where the
denominator is populated, **both reservoir routes carry the same exponent**,
≈ N^1.7–2.0 per import; the difference between them is level, not shape, and
droplet holds ~88% of the level.

## The mechanism, read from the code rather than inferred

`TransmissionCore._pathway_droplet` sums `DROPLET_AEROSOL_FRACTION` (0.05) of
every shedder's emission in a zone into one pool, divides by the zone's
declared `volume_m3`, and gives every susceptible occupant
`concentration × inhaled_air_volume × vent_factor`:

```text
dose(target) = ( Σ_shedders emission_s × 0.05 ) / V_zone × inhaled × vent × confinement
```

`V_zone` is a property of the architecture and is **fixed** across the
occupancy probe. So shedders per zone scale with N, the per-susceptible dose
scales with N, and the number of susceptibles receiving it scales with N —
droplet infections go as N², and because imports also scale with N, total
secondaries go as N³. That is what the table measures (N^2.70–2.97 total,
N^1.70–1.96 per import).

**This retires the description I gave of the kernel.** "Frequency-dependent by
construction" was only ever true of `per_partner_contact`, which governs the
*direct* route — and the direct route establishes **3 infections in 1,800
voyages**. The kernel that actually transmits is a well-mixed room
concentration with a fixed denominator, which is density-dependent. Arm A's
inertness (φ redistributing a fixed contact draw) and Arm C's explosion are
both consistent with that: the class-composition axis moves a route that does
nothing, and the density kernel replaced the one route that already had
density in it.

My earlier inference — that the surplus sat in "surface/fomite, zone air,
emesis aerosol" — is **half right and specifically wrong**: the reservoir
reading holds, but the carrier is the in-room aerosol pool, not the surfaces
(8–15%), and not emesis aerosol or the environmental reservoir (both zero).

## What that makes of the constant

`DROPLET_AEROSOL_FRACTION = 0.05`, "fraction of total shedding that becomes
immediate room-level aerosol", is a module constant in
`engines/transmission_core.py` with **no row in
[parameter_provenance_register.md](../parameter_provenance_register.md)** and no
entry in the freedom audit's unsourced list. It is now measured to carry
85–99% of all established infections and the entire headcount scaling.

The register has already ruled on this exact quantity, for the airborne route:

> The continuous-shedding definition remains **∅ null-confirmed-by-search**: no
> study reports emission to air as a fraction of a host's shedding, for
> norovirus or, in six unfiltered Consensus queries, for any pathogen. Shedding
> is measured in copies/g of stool or vomitus and airborne virus in copies/m³
> of room air, never in the same subjects, so that fraction has no commensurable
> numerator and denominator.

On that finding the continuous fraction was **deleted** from the norovirus
profiles and replaced by `airborne_emission_mode = emesis_conditioned`, drawing
per emesis event over Tung-Thompson 2015's measured
`emesis_aerosol_fraction_range = [7.2e-7, 2.67e-4]`. The droplet route kept the
same null definition, at 0.05, applied **continuously, every epoch, to every
shedder** — 2 to 5 orders of magnitude above the only air-emission fraction in
the repository that a study measures, and unconditional where the measured one
is conditioned on an event.

So the composition is inverted against the evidence: the route with a sourced
emission definition (`emesis_aerosol`) establishes **zero** infections, and the
route with a null one establishes nearly all of them. Three zeros are their own
claims and need checking on their own terms — `food_contamination` at exactly
zero across 1,800 cruise-ship voyages is not a credible reading of VSP outbreak
investigation, and `hvac_airborne` and `environmental_source` at zero say the
reservoir routes that were built are not reaching a dose that establishes.

## What must not be concluded

Lowering 0.05 would lower posting, and **that is not a reason to lower it**.
The admissible move is the definitional one the register already took for the
airborne route: either give the droplet route a commensurable, measured
emission definition (event-conditioned, as the evidence is), or declare the
fraction null and report the route's contribution as unidentified. Either is a
change to a physical definition, gets a register row and an evidence grade, and
is measured as its own matched arm — not folded into a default and not selected
against A8/A9/Park. That it moves the anchors in the wanted direction is
recorded here as a coincidence, exactly as with the boarding corrections.

Separately, [#505](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/505)
recorded direct contact carrying 99.7% of *delivered dose*. That figure is in
the void ledger and predates the hand-bridge correction, so it is not in
contradiction with three establishments in 1,800 voyages — but dose-dominant
and establishment-absent is a gap worth measuring rather than assuming, and it
is not measured here.

## Artifacts

- `telemetry_buffer/observation_model/hull_compounding_route_v1.json` and
  [hull_compounding_route_v1_readout.md](hull_compounding_route_v1_readout.md)
  — realism-ladder readout with the per-cell `secondary_route_attribution`
  block.
- `telemetry_buffer/observation_model/hull_compounding_route_v1_routes.json`
  and [hull_compounding_route_v1_routes.md](hull_compounding_route_v1_routes.md)
  — the per-route tables above and the paired-seed full/quarter ratios.
