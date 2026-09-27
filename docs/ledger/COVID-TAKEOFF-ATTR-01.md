# COVID-TAKEOFF-ATTR-01
**Date:** 2026-09-27
**Commit:** ce8e3020
**Pathogens:** sars_cov2_resp
**Status:** declared

Decomposition of the covid.H3 takeoff burn — the ~2,400–3,580 recorded
onsets the declared replay produces against the record's 197 — into
routes, rings and timing, and the mechanism class the pattern implicates.
Measurement only: no Θ selection, no clause repair, no model or constant
changes. Companion to THETA-SCREEN-V12 (§stage 2: the clause fails at
every admissible Θ in the same ~17× mass class, so the residual is
mechanism-shaped, not Θ-shaped). Engine code at this commit is identical
to the v12 measurement SHA f42901aa.

## Declared before running

**Θ choice:** 2.37e11 — the admissible band midpoint
{1.33, 1.78, 2.37, 3.16, 4.22}e11 (both the count midpoint of the five
admissible points and the V12 stage-1 lattice interior midpoint).

**Cell set:** the 20 stage-2 replay cells at Θ 2.37e11
(`covid_theta_screen_v12_stage2_design.json` row `theta1e11p37`,
seeds 20200205–20200224), declared replay onset_day −1.0,
departure_day 5.0, dwell_weighted, imports 1, infection_age 6.8,
768 epochs. These are exactly the clause-scored takeoff cells; the
instrument is a read-only observer added to the same cell path
(`cell_payload` runs unchanged underneath, so every aggregate field of
the stage-2 record is re-emitted and re-checkable).

**Route taxonomy** (channel assignment per infecting epoch, made before
results were seen):

- `cabin_mate_ring` — droplet deliveries to a cabin-mate while the pair
  sits in a Cabin_Corridor compartment (the `_cabin_mate_near_weight`
  arm of `_near_field_unit`) plus the cabin-mate addback channel
  (`_cabin_mate_droplet_addback`, dose × emitted weight ∝ copresence).
- `dining_ring` — droplet deliveries where `_table_party` finds
  shedder and target sharing a table (weight 1.0) or on an adjacent
  table (weight `neighbour_table_ratio`); where `proximity_ids`
  upgrades an otherwise-unringed pair the credit goes to
  `near_field_plume`, since the mechanism that produced it is the
  distance/radius claim, not a fixed social ring.
- `near_field_plume` — all remaining `_near_field_droplet_dose`
  deliveries (proximity-claimed, unringed partners, mate pairs outside
  the corridor).
- `zone_pool` — droplet records with no near-field resolution: the
  zone's shared-room exposure set (`source_ids` shared-pool
  contributions).
- `hvac_airborne` / `contact` / `other` — direct pathway keys
  (`hvac_airborne`, `direct_contact`; `emesis_aerosol`, `fomite`,
  `food`, `environmental` folded into `other`).

**Attribution basis:** the challenge's post-efficiency, post-NPI
per-pathway dose vector on the infecting epoch — the causal vector the
hazard was drawn on (`_resolve_pathogen_challenge`'s
`agent_pathway_doses`, `effective_dose = p_dose × (1 − protection)`,
hazard `-expm1(-susc × effective)`). Channel credit for an onset is the
infecting-epoch channel's share of that vector (with `droplet` split
into ring classes by the instrument's recorded delivery shares).
Secondary basis: the engine's own lifetime
`acquired_particles_by_route` ledger (per-infection cumulative
exposure), reported alongside as `by_lifetime_dose` to show how much of
the attribution is history vs. final push. A third view,
`by_dominant_channel`, counts which channel carried the largest share
of each onset's infecting vector — robust to the share-split choice.

**Shedder credit:** each onset distributes its credit over the sources
that produced its infecting vector, proportional to the instrument's
recorded per-source contribution for that channel (pool ∝ emitted
strength; near-field ∝ weight × emitted; addback ∝ engine weight;
hvac/contact ∝ exposure-record appearances). `onsets_per_shedder` is
then a soft distribution; `onsets_per_shedder_dominant` is the hard
version — each onset counted wholly to its largest contributor.

**Candidate mechanism classes** (named before results, per the prompt):

- (a) **Reach throttling absent** — per-shedder reach per epoch (how
  many distinct susceptibles one shedder's dose vector touches in one
  epoch) is too large; a contact ceiling or thinning rule would shrink
  it.
- (b) **Exposure-set partitioning absent** — plume/pool footprints
  cover too many susceptibles at once; venue/zone partitioning would
  shrink the set each delivery reaches.
- (c) **Susceptibility depletion absent** — susceptibles are recycled
  through challenge windows with no depletion of the effectively-
  susceptible pool, or heterogeneity is flat so nobody drops out.

Discriminating features declared: (a) implicates if
reach_per_shedder_epoch is large AND onsets are spread across shedders;
(b) implicates if footprint/dosed-targets-per-epoch is large while
reach is modest; (c) implicates if challenged_share_of_aboard is ~1
(most susceptibles get challenged) while susceptibility of the
never-challenged counterfactual group sits well above that of the
challenged-uninfected group — i.e. selection on susceptibility is
happening inside challenges, not by depletion.

**Canary gate (declared):** instrumented seed 20200205 @ Θ2.37e11 must
reproduce the stage-2 cell of record — recorded_onsets = 2,330,
infections_total = 3,590, aboard_total = 3,711, first_onset_day = 2,
index_onset_day = −1.0, index_departed_epoch = 120, and the full
observables/onset_curve block — before any array.

## Report immediately if

A single channel carries ≥80% of takeoff onsets; the burn is dominated
by epochs/venues outside the declared replay's intent (instrument
artifact); or the existing v12 records prove sufficient with zero new
runs. (v12 stage-2 cells carry only aggregate observables — no
route/shedder/event fields — so instrumented re-runs were required;
the cells still serve as the canary targets.)

## Measured

(pending — instrument canary + 20-seed array at Θ2.37e11 on image
pinned to this commit)

## Inferred

(pending)

## Hypothesis

(pending)
