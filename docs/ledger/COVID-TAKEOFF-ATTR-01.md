# COVID-TAKEOFF-ATTR-01
**Date:** 2026-09-27
**Commit:** bcf2ac95
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** bcf2ac95

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

All numbers below are measured on the 20 instrumented takeoff cells at
Θ 2.37e11 (seeds 20200205–20200224), AWS Batch array job
`95251e9a-6a1d-422e-847a-e2ee3f7fa92d`, job definition revision
`picard-covid-takeoff-attr:1`, image
`picard-campaign:covid-takeoff-attr-bcf2ac95`
(digest `sha256:ea0980f997eeb2c92388b1757b05f46b039129e89bff4f069c423a25568a235b`),
cells under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_takeoff_attr_v1/bcf2ac95/cells/`,
readout `tools/covid_takeoff_attr_readout.py`.

**Canary gate (passed, stronger than declared):** the instrumented
pipeline reproduces the stage-2 record **bitwise on all 20 cells** —
every payload observable (recorded_onsets, infections_total,
aboard_total, attack_rate, lab_confirmed_total, split-day onsets,
campaign positives), the full onset_curve and sanitary_activity, for
all 20 seeds vs `covid_theta_screen_v12_stage2/f42901aa/cells/cells/`.
The instrument is a pure observer; the local (Python 3.12) canary is
within the documented ~1% interpreter drift (3,589 vs 3,590 infections,
an uninstrumented local control bitwise-identical to the instrumented
run). Per-seed recorded onsets now range 2,330–3,556 (median 3,475) —
the same ~12–18×-over-197 mass class the clause scores.

**Takeoff-beat accounting:** 71,298 attributed infection events across
20 seeds; `droplet_unattributed_onsets = 0` — every infection's
infecting-epoch dose vector was fully apportioned; nothing fell to
`other` (share 0.0 exactly).

**Route split** (share of takeoff infections, per infecting-epoch
channel shares; per-seed median ± spread):

| channel | pooled share | per-seed median | q05–q95 |
|---|---|---|---|
| zone_pool | 43.2% | 43.3% | 39.2–48.7% |
| dining_ring | 23.7% | 24.1% | 21.0–26.6% |
| near_field_plume | 22.2% | 22.6% | 18.8–24.7% |
| cabin_mate_ring | 8.4% | 8.0% | 7.5–11.2% |
| hvac_airborne | 2.6% | 1.6% | 1.0–8.0% |
| contact | ~0.001% | ~0 | — |

No channel ≥80% (the report trigger does not fire): the burn is
multi-channel. Two other attribution bases for the same events —
infecting-epoch dose mass: plume 68.4%, dining 24.1%, cabin-mate 6.9%,
pool 0.5%; lifetime cumulative dose of the infected: cabin-mate 44.0%,
plume 37.1%, dining 16.7%, pool 2.2%, hvac 0.02% — i.e. plume carries
the rare-but-huge doses, pool carries the largest count of small
challenges, cabin-mate dominates the *cumulative* exposure of the
infected without dominating final push.

**Geometry — diffuse, not concentrated:**

- Shedders: 3,711 hosts ever credited (essentially every infected
  host sheds); median credited onsets/shedder 8.8 (q95 69.5); the top
  single shedder carries 457.6 credited onsets (~0.64%) and the top-5
  carry 2.7% pooled. Dominant-credit basis: median 9, q95 74, top-5
  2.9%. No superspreader structure.
- Epochs: 605 distinct infecting epochs produce infections; median 39
  infections/epoch, q95 447; the top-5 epochs carry only 5.1%.
- Venues: top venue Windjammer 8,401 (11.8%); second Crew_Mess_Main
  6,780 (9.5%); 16 venues each hold ≥2% — no single-venue dominance.
- Timing: infecting-day histogram peaks on day 5 (7,462 events) and
  days 4–8 jointly carry 47%; days 0–2 carry 11.5% — the burn is
  a sustained takeoff swell, not a boarding spike nor an
  off-window artifact.

**Mechanism evidence:**

- Exposure-set saturation: the number of distinct hosts receiving any
  dose per epoch has per-seed median 705 (range 577–865 across seeds;
  per-epoch q95 up to 3,621 ≈ the whole ship of 3,711). Per-channel
  footprints (median of per-seed medians, targets per epoch): hvac 560
  (q95 max 3,548 — the AHS loop effectively offers dose to most of the
  ship), cabin_mate_ring 150 (q95 860), contact 66, zone_pool 16
  (q95 2,061 — the pool's tail reaches zone-scale sets), plume 10,
  dining 10.
- Reach per shedder-epoch: hvac median 9 targets (q95 up to 306);
  zone_pool median 1 with q95 80 (a strong shedder floods a zone set);
  plume/mate/contact medians 1 — per-shedder reach is large only on
  the airborne/pool channels.
- Challenge coverage: `challenged_share_of_aboard` = 1.0 on every seed
  — **every susceptible aboard was challenged at least once**;
  never-challenged hosts = 0 in all 20 cells. Susceptibles aboard per
  epoch fall to median 186 (q95 3,710) as the burn depletes the pool.
- Heterogeneity is present and selecting: infected hosts' susceptibility
  median 2.3e10 (q05 9.9e5) vs challenged-but-uninfected median-of-
  medians ~327 (per-seed range 106–1,135) — ~5–7 decades of selection
  *within* challenge events.
- Infecting λ (susceptibility × effective dose): median 0.42; only
  34.6% of infections at λ ≥ 1 (sure things); 25.7% at λ < 0.1 —
  a lottery-volume process: enormous challenge count × modest per-
  challenge probability.

## Inferred

The takeoff burn is mechanism class **(b) exposure-set partitioning
absent**, with class (a) as the same defect seen source-side:

- Per-epoch dosed sets cover ~600–870 hosts (median-of-medians 705) on
  a 3,711-person ship, and every susceptible is challenged during the
  voyage — the model has no mechanism that partitions the exposure set
  (venue-capacity limits, occupancy windows, asymmetric contact
  sampling) so the takeoff machinery doses essentially the entire
  remaining susceptible pool every epoch.
- (a) Reach is implicated jointly: it is the source-side arithmetic of
  the same defect — a pool or AHS shedder reaches 9–306 targets in one
  epoch — rather than an independent failure.
- (c) is *not* the missing mechanism: susceptibility heterogeneity
  exists and selects strongly within challenges (infected vs
  challenged-uninfected medians ~5–7 decades apart), but with challenge
  coverage at 100% there is no residual protected pool for depletion to
  produce — selection happens inside a fully-exposed population.
- The lottery signature (median λ 0.42, 26% of infections at λ<0.1)
  means the burn does not need per-challenge doses to shrink much; it
  needs the *challenge count* per epoch to shrink — a partitioning
  mechanism, not a titre mechanism. This is consistent with the v12
  verdict that the residual is mechanism-shaped not Θ-shaped: Θ rescales
  per-challenge hazard, but with 705-host dosed sets the hazard mass
  lands regardless.

**What ~197 implies for the winning class** (sourced-quantity
statement, not a fit): for recorded takeoff onsets to sit near 197
while the instrumented run produces 2,330–3,556, the *fraction of the
aboard ever challenged* during the takeoff window must be on the order
of ~5–10% rather than the measured 100% — i.e. the exposure-set
partitioning the model lacks must cut the per-epoch reachable set by
roughly an order of magnitude (705 → ~50–100 hosts/epoch), or bound
the per-shedder reach likewise. The exact partition rule (venue
capacity? cohort? contact budget?) is a sourcing question for the next
session: what real Diamond Princess contact structure limited each
person's exposure set, and which of cabin-ring / meal-table / shared-
venue partition does that structure correspond to.

## Hypothesis

- The dining ring's 24% share is mostly the `neighbour_table_ratio`
  extension (adjacent tables), not fixed table parties — worth checking
  whether partitioning tables to fixed parties alone removes most of
  it.
- Zone pool dominance may partly be pool *spillover* into crowded
  venues (pool q95 footprint 2,061 ≈ a packed venue), i.e. (b) may fix
  itself at the venue-capacity level rather than needing a zone-pool
  cap.
- Boarding structure stays off the suspect list: days 0–2 carry only
  11.5% of infecting-day mass — consistent with COVID-REBASE-01 stage 3.
