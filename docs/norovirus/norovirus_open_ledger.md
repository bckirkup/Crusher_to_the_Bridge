# Norovirus fit: open ledger

> **Status:** Living

**Live status updated for R4.** What is currently withdrawn,
what each anchor last measured and *when*, and what is outstanding.

`docs/norovirus/norovirus_model_history.md` is the permanent record of defects and
corrections. This file is the volatile counterpart: it goes stale by design and
must be updated whenever a model change lands. If the head commit below is not
the current head, treat every number here as unverified.

Read this before quoting any dose figure or anchor result.

---

## 1. Currently withdrawn

**Every crew attack rate and crew-channel posting measured before
`FOOD-ROLE-01` was measured with the whole crew as food handlers at every
meal.** The transmission core's food-handler test was `role == crew and zone in
service_zones`, where the service set is every Dining zone plus every Galley;
`CrewMess` is Dining on every hull and each agent's dining zone is drawn across
the whole Dining set, so every crew member — engineer, medic, deckhand — took
the Jin 2022 restaurant-staff surface rate (`CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR`
545.4/h against the diners' 42.8/h) and the inferred 12.7× food-handler contact
multiplier for the duration of every meal, while the `crew_mess` diner rate in
the surface table was unreachable. The repair makes the channel a duty state:
the agent is a food employee by the VSP duty exclusion's own definition (crew
whose work zone is a service zone, one predicate `is_food_employee` shared by
both), is in that work zone, and is scheduled `Work`; crew eating are diners.
No constant moves. The class-mixed staged campaign (expedition/classic/spirit
stage 0–2, mega stage 0–1) and every earlier gate carried this defect, so their
crew attack rates (2–5× the observed crew medians on posted voyages), A5 ratios
(1.0–1.5 against a measured 4.3) and crew-only posting shares (23% against 1 of
208 observed) are not the declared model's and must be re-measured. Their
passenger-channel results are affected in an unmeasured direction through the
shared surface and food pools. **Measured on expedition (Batch `9004cb26`,
image `bounded-design-v10`, expedition stage 0 re-run voyage-for-voyage: 256
points × 6 seeds, seed base 500, design seed 37):** the repair changed nothing
the anchors can see — 173 → 174 postings of 1,536, mean crew infection AR
3.78% → 3.75%, passenger 6.05% → 6.02%, A5 1.60 → 1.61; 844 voyages
bit-identical, the rest differ by RNG divergence only (paired Δ crew AR −0.04
pp, sd 2.6). The withdrawal stands as written — those results were measured on
a defective structure — but on this hull the numbers are unchanged, so the
food-handler channel was not what over-infects crew; whatever does is a route
crew share with passengers.

**`BERTH-01` (PR #475) made the cabin the night mixing unit and its toilet its
own fomite pool, and it was measured the same way (Batch `0271ba38`, image
`bounded-design-v11`, same 1,536 matched voyages against the `FOOD-ROLE-01`
reprise):** postings 174 → 143 (11.3% → 9.3%; paired flips 44 off / 13 on,
exact two-sided p ≈ 5e-5), crew-only postings 13 → 7, mean passenger infection
AR 6.02% → 5.51% (paired Δ −0.51 pp, se 0.08), crew 3.75% → 3.59% (Δ −0.15
pp, se 0.08), A5 1.61 → 1.53, points at 0/6 204 → 218 of 256; posted
passenger AR median 11.1% → 12.0%. Read: dissolving the 25-berth passenger
"ward" lowers passenger infection by about a twelfth and postings by about a
sixth, but crew — whose 37-berth ward became 2–3-berth cabins — barely move,
so A5 falls further from the measured 4.3 rather than toward it. Night mixing
was not the crew's route; the posting frequency on this hull stays 6–15× above
its 0.59–1.60% band. Every pre-`BERTH-01` frequency and attack rate is
therefore also superseded, on every hull, in a direction measured only on
expedition.

**`DINE-SEG-01` (PR #476) seats crew in the crew mess and passengers in the
passenger venues** (§4 item 8), which ends the shared-dining-room structure
every result above was measured on, **and it was measured the same way (Batch
`da6275de`, image `bounded-design-v12`, same 1,536 matched voyages against the
`BERTH-01` reprise):** postings 143 → 169 (9.3% → 11.0%; paired flips 9 off /
35 on, exact two-sided p ≈ 1e-4), crew-only postings 7 → 6, mean passenger
infection AR 5.51% → 5.82% (paired Δ +0.31 pp, se 0.08), crew 3.59% → 3.55%
(Δ −0.05 pp, se 0.09 — indistinguishable from zero), A5 1.53 → 1.64, points at
0/6 218 → 211 of 256; posted passenger AR median 12.0% → 12.7%, posted crew AR
median 10.1% → 9.0%; 660 voyages bit-identical. Read: taking the quarter of
passengers out of the CrewMess and Galley puts the whole complement into two
passenger dining rooms, which are denser and infect passengers slightly more;
taking three quarters of crew out of those rooms does **not** lower crew
infection at all. So crew were not catching it as fellow diners either. Of the
routes crew share with passengers, berthing (`BERTH-01`) and dining are now
both eliminated as the source of the crew excess on this hull; what remains
shared is the work shift in passenger service zones (with the Jin 545/h
service-surface rate), the leisure catalogue (no crew recreation zone is
declared), and hallway residuals. A5 has moved 1.61 → 1.53 → 1.64 across two
structural repairs against a measured 4.3, so the asymmetry is not going to
come out of topology repairs of the size that remain; the finite-sample
reading is that the model's crew route is on the work shift. The posting
frequency stays 7–19× above expedition's 0.59–1.60% band. Every pre-`DINE-SEG-01`
frequency and attack rate is superseded, on every hull, in a direction measured
only on expedition.

**`SEAT-01` gives every Dining zone a declared number of meal seatings**, and
until it lands every venue seated its whole assigned complement in the same
hour: the passenger schedule puts every passenger at breakfast 09–10, lunch
12–13 and dinner 18–19 simultaneously, so `classic_cruise_1900` seated 1,350
passengers in 1,230 declared seats and `spirit_cruise_3000` 2,100 in 1,760, and
every crew mess (60 seats for 150 crew on expedition) held the whole crew at
once — a physical impossibility the `max_occupancy` declaration never
enforced. The declaration is operational, not epidemiological: passenger
venues on the classic, spirit and mega hulls declare **2** sittings (traditional
main-dining-room service is two assigned dinner seatings, early and late — Royal
Caribbean's own dining FAQ, and the same practice on Carnival/NCL-era hulls;
breakfast and lunch are open-seating within a service window of about two
hours, which the same cut represents), expedition's passenger venues declare
**1** (the 300-seat MainDining seats the 300-passenger complement in one open
sitting, as expedition operators describe — unassigned tables, the whole ship
dines together), and every crew mess declares **2** (crew accounts describe
mess windows of 2–3.5 hours served buffet-style across shifts; the *lower* end
is taken, since fewer sittings keep the room denser). Each diner is dealt a
cohort at spawn; a two-hour block in two sittings is two one-hour turns, so the
service window is unchanged and the room holds half its complement at any hour.
No constant moves. A venue without the declaration (every legacy and naval
hull, and every synthetic test layout) is bit-identical to before. **The
`DINE-SEG-01` and `BERTH-01` expedition figures above stand for the passenger
venues** (single sitting on that hull) **but the crew-mess half of them was
measured with the whole crew in a 60-seat room at once.** The matched
expedition reprise (Batch `f243a31c`, image `bounded-design-v13`, 1,536 voyages
matched by `run_id` to `DINE-SEG-01`) measured the crew-mess half: postings 169
(11.0%) → 182 (11.85%), crew-only postings 6 → 16, mean crew infection AR
3.55% → 3.66% (Δ +0.12 pp, se 0.08), mean passenger infection AR 5.82% → 6.03%
(Δ +0.20 pp, se 0.09), A5 1.64 → 1.65; 810 voyages bit-identical, posting flips
25 off / 38 on (exact two-sided p = 0.13). Halving crew-mess density did not
lower crew infection; nothing on this hull is resolved as changed. The classic
reprise (`88428bc0`, 48 shards) is the first classic run after all four repairs
and is read cumulatively against the original classic stage 0 when it lands.

**`SEAT-02` gives every dining venue on every hull at least two sittings, dealt
so no venue runs at or over its declared seats in any hour.** `SEAT-01` left
expedition's passenger venues at one sitting and dealt cohorts by a uniform
draw, so a venue's hourly occupancy was only bounded in expectation. Now every
Dining zone with diners declares ≥ 2 sittings and the engine deals diners to a
venue's sittings in rotation, as a fixed seating plan does, so a sitting holds
at most `ceil(assigned / seatings)` diners. The counts are set from the hull's
own declarations — the role complement's capacity-weighted share of the venue,
divided by the sittings, must sit under the venue's `max_occupancy` with
headroom for the venue draw's variance — and from nothing scored: expedition
passenger venues **2** (300 passengers in 450 seat-turns), every other
passenger venue stays at **2**, crew messes **3** on expedition (150 crew, 60
seats → 50 a sitting) and mega (2,000 crew, 1,050 seats), **4** on classic (560
crew, 200 seats → 140) and spirit (900 crew, 310 seats), where three sittings
left 187/200 and 242/250 expected in the room. A crew mess in three or four
one-hour sittings is a mess serving across shifts, which is what crew accounts
describe; a passenger two-hour block in two sittings is unchanged from
`SEAT-01`. No constant moves. Venues without the declaration are bit-identical
to before; every declared venue's RNG stream differs from `SEAT-01` because the
cohort is no longer drawn. **Every `SEAT-01` figure is superseded** by the
matched Batch reprises below.

Expedition reprise (Batch `56ecc95f`, image `bounded-design-v15`, 1,536
voyages matched by `run_id` to the `SEAT-01` reprise `f243a31c`; a first
submission, `20bd9f20`, ran the campaign image's entrypoint by build error and
produced nothing): postings 182 (11.85%) → 158 (10.29%), crew-only postings
16 → 10, mean passenger infection AR 6.03% → 5.50% (Δ −0.53 pp, se 0.09),
mean crew infection AR 3.66% → 3.55% (Δ −0.11 pp, se 0.08), A5 1.65 → 1.55,
points at 0/6 200 → 216 of 256; 822 voyages bit-identical, posting flips 45
off / 21 on (exact two-sided p = 0.004). Posted passenger AR median 11.9% →
11.7%. So taking expedition's passenger venues from one sitting to two lowers
passenger infection by about a twelfth and postings by about an eighth — a
resolved, real reduction at 1,536 voyages — while crew, whose mess went from
two to three sittings, do not move within error. A5 falls again: the fourth
structural repair in a row that lowers passenger transmission and leaves crew
where they were. Cumulatively across `FOOD-ROLE-01`, `BERTH-01`, `DINE-SEG-01`,
`SEAT-01`, `SEAT-02` on this matched grid: postings 173 → 158 (11.3% → 10.3%),
A5 1.60 → 1.55, against the hull's own record of 0.59–1.60% postings and the
literature's 4.3. Finite-sample findings on one Sobol grid, not a bound on the
box.

Classic `SEAT-01` reprise (`88428bc0`, 48 shards, 1,536 voyages matched to
the original classic stage 0, which predates all four repairs, so this reading
is cumulative `FOOD-ROLE-01` + `BERTH-01` + `DINE-SEG-01` + `SEAT-01`; it does
not carry `SEAT-02`'s crew-mess change from 2 to 4 sittings): postings 365
(23.8%) → 278 (18.1%), crew-only 68 → 71, mean passenger infection AR
7.88% → 6.41% (Δ −1.47 pp, se 0.10), mean crew 7.50% → 5.55% (Δ −1.95 pp, se
0.12), A5 1.05 → 1.16, points at 0/6 106 → 146 of 256; 23 voyages
bit-identical, flips 120 off / 33 on (p < 1e-6). Posted passenger AR median
8.3% → 11.3%, crew 10.3% → 9.8%. On the hull where passengers went from 1,350
in 1,230 seats at once to sittings, both roles fall by a fifth to a quarter,
crew slightly more — the one hull where crew moved — but the posting rate is
still ~10× the top of the classic record's 0.15–1.85% band and A5 still ~1.2
against 4.3.

The load these declarations put in a room, checked against public operating
documentation (Transcribed, documentary — not literature): a fixed-seating
dining room is observed running at roughly two-thirds of its seats, and the
published seat inventories agree — Spirit-class *Carnival Spirit*, 2,124
passengers, one 1,300-seat dining room in two fixed sittings (Cruise Critic,
Frommer's, CruiseMapper) is 82% a sitting only if every passenger attends, and
they do not (buffet 1,458 seats alongside); *Liberty of the Seas*, 3,634
passengers, 652 + 500 + 883 dining-room seats in two sittings (cruisedeckplans),
89% likewise. The hulls here seat every passenger at every meal in a declared
venue, so their expected load per sitting is the comparable figure: expedition
33%, classic 55%, spirit 60%, mega 43% — at or under the observed two-thirds
everywhere. Crew messes run 63–83% a sitting (expedition 83%, spirit 73%,
classic 70%, mega 63%); crew accounts describe the mess as buffet service over
a 2–3.5 h window per meal (breakfast 06:00–09:00, dinner 17:00–20:30, Emma
Cruises 2020; crew-center.com AIDA Hyperion; joannetai.com 2025) with crowded
tables and queues at the lunch peak, which is three to four one-hour sittings
with the room near full at the peak — so the higher crew load is what the
accounts describe, not a shortfall. The passenger two-thirds bound is now held
by test; the crew bound is the room. No literature index carries any of this,
and no seating count is chosen against a scored quantity.

**`DINE-PARTY-01` seats table-service diners at fixed tables and makes the
table, not the room, a seated diner's direct-contact pool.** Before it, a
diner's partners at every meal were drawn uniformly from everyone in the venue,
whatever the service: a main dining room and a buffet were the same well-mixed
room. Now each sitting of every `mdr` and `specialty` venue is dealt to tables
of the venue's declared `dining_table_size` (default 6; the last table takes the
remainder; a cabin is dealt contiguously so a booking shares a table), fixed
for the voyage as assigned seating is, and a diner's contact draw at its own
venue lands on the party present at its table by
`transmission.dining_party_contact_share` (default **1**: the table is the
mixing unit for the meal). The draw itself — POLYMOD 13.4/day, role-blind — is
unchanged; only who it lands on. Buffet and crew-mess diners, staff on shift in
the room, and every diner at a share of 0 keep the venue-wide draw, and a share
of 0 is bit-identical to `SEAT-02` (checked on expedition, 200 agents, 240
epochs). What the record supports (Transcribed, analogous-setting, Grade C):
restaurant video studies put a same-table diner's share of another diner's
close contact and surface exposure two orders above other tables' (Zhang 2021,
Guangzhou, >13,000 close-contact episodes and >40,000 touches, one table 97.9%
self / 2.1% same-table / 0% other-table for a surface class; Jin 2022, Table 3,
3.5% of viral load on same-table private surfaces vs 0.03% at other tables);
the hotel-restaurant norovirus reanalyses model parties as the unit and route
between them through waiters (Xiao 2017) and find attack rate falling with
distance from the index table (Marks 2000). Public cruise documentation puts
main-dining tables at 2, 4, 6, 8 and 10 with the same table and waiter each
night in traditional dining, so 6 is a declared centre of a documented 2–10
range, not a measured constant. None of it is a cruise measurement, none of it
gives a within-party contact share, and no value here is chosen against a
scored quantity: the share is the swept axis (0 = the pre-party room, 1 = the
table), the table size a per-venue declaration.

**Measured, and it is a null.** Matched expedition stage-0 reprise (Batch
`14dfa232`, image `bounded-design-v16`, the same 256-point grid, 6 seeds a
point, seed base 500, design seed 37 as the `SEAT-02` reprise `56ecc95f`; 1,536
voyages matched run-for-run, 1,066 of them bit-identical):

| | `SEAT-02` | `DINE-PARTY-01` |
|---|---:|---:|
| postings (OR rule) | 158 (10.29%) | 158 (10.29%) |
| crew-only postings | 10 | 7 |
| mean pax infection AR | 5.495% | 5.490% |
| mean crew infection AR | 3.551% | 3.527% |
| A5 (infection, pax:crew) | 1.547 | 1.557 |
| points with no posting in 6 seeds | 216 | 219 of 256 |

Paired: Δ pax −0.004 pp (se 0.06), Δ crew −0.025 pp (se 0.067), posting flips 15
off / 15 on (two-sided sign p = 1.0). At 1,536 voyages the change is
indistinguishable from RNG divergence on every channel. Read: with the contact
*count* fixed at POLYMOD 13.4/day, restricting a seated diner's partners from
the room to a fixed table of six changes who is met without changing how many,
and on this hull that reallocation carries no measurable dose — the same
readout the three preceding topology repairs gave for the crew arm. It does not
license the inverse claim: the two mechanisms that would make seating matter are
not in the tree yet, namely class-directed contact scaling
(`CONTACT-SCALE-01`, `N_target^φ` from Shirreff 2024) and a sub-room air
compartment (`AERO-NEAR-01`, §4 item 16), and the table's *repeat*-contact
structure has no representation while partners are redrawn independently each
epoch. The finite-sample statement is what is recorded here: on this grid, with
this seed set, no effect resolved.

**The three-arm expedition sensitivity: one knockout and two axes, none of them
a proposed value.** Five structural repairs have moved the crew arm by nothing
(`FOOD-ROLE-01`, `BERTH-01`, `DINE-SEG-01` and `DINE-PARTY-01` all null on crew;
`SEAT-01`/`SEAT-02` moved passengers only), so the next question is not another
topology repair but *which non-structural quantities the crew excess is even
sensitive to*. Three arms are built, and each is a diagnostic or a declared
axis, because none of the three has a cruise measurement to adopt:

- **`SURF-KO-01`** — `service_surface_knockout.enabled`, **off by default**.
  When on, a food employee **on service duty** takes the ordinary diner
  surface-touch rate (42.8/h) rather than the staff rate it was measured at
  (`CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR` 545.4/h, Jin 2022). Neither constant
  moves, `_on_service_duty` is untouched, and food-handler dose, direct contact,
  every other fomite class, off-shift crew, non-service crew, diners and
  unrelated zones are unchanged. This is the per-multiplier knockout of tranche
  33 applied to the one channel that survived those repairs; 42.8 is **not** a
  claim about what a waiter touches, and a knockout result may not be converted
  into a shipped rate.
- **Boarding prevalence, independently by role.** `engines/initiation.py`
  already draws passenger and crew boarding prevalence as separate per-person
  probabilities, so the arm needs no new mechanism — it sweeps the two sourced
  intervals independently: passenger **[0.025, 0.040]**, crew **[0.007, 0.030]**
  (Grade B, asymptomatic faecal RNA carriage on its own denominator, Kobayashi
  2021 / Qi 2018 / Jeong 2021; outbreak-population positivity excluded as
  circular). The shipped 0.0325 / 0.0185 are interval midpoints, i.e. defaults,
  not measured point estimates. The arm stays distinct from sentinel/wastewater
  positivity, from post-boarding spreading efficiency, from symptom-conditioned
  transmission and from explicit scenario seeds.
- **`IMMUNE-ROLE-01`** — `ship_graph.crew_immune_fraction`, **absent by
  default**. Unset, embarkation immunity stays one role-blind pool at
  `IMMUNE_RATIO` 0.2 and the run is bit-identical; declared, passengers and crew
  draw from separate pools. **No crew-specific level is sourced and none is
  adopted**: tranche 34 returns zero measurements of crew norovirus
  seroprevalence, crew prior-infection history, or any voyage-to-voyage carried
  immune state. What exists is analogous — Yu 2023's 2.3–4.8 yr GI
  blockade-antibody duration at 3.6–5.9 %/yr decay, on a correlate rather than a
  protection fraction — and career length and cumulative shipboard exposure are
  documentary, not immunological. Composing the three would multiply three
  quantities none of which is measured on this population, so the axis is
  declared over the whole unit interval **[0, 1]** precisely so it cannot read as
  sourced.

**The structural gap stays open.** The immunity this axis varies is
*embarkation-time* immunity: the pool is drawn at voyage start and nothing
carries across voyages. Real crew immune state would be a function of the
voyages that host has already worked, and the model has no host that persists
between voyages, so that mechanism is **absent, and is recorded as absent** —
not substituted with a crew multiplier. Whatever the sweep returns is a
statement about a declared axis, never a measurement of crew immunity.

No value in any of the three arms may be selected because it moves A5, A9, the
posting rate or an attack rate toward its anchor. `CONTACT-SCALE-01` (the
class-directed `N_target^φ` scaling from Shirreff 2024) and `AERO-NEAR-01` (the
sub-room air compartment, §4 item 16) are separate and are **not** included
here; the buffet/table-service fomite topology is separate too.

**Measured (Batch `cede0027` baseline / `799bfafc` knockout, image
`bounded-design-v17`).** Expedition, Sobol m = 8 over the 13-factor
`expedition_sensitivity` box (the ten Norovirus factors plus the two boarding
intervals and the `[0, 1]` immunity axis), design seed 37, 6 seeds a point, seed
base 500 — 1,536 voyages per arm, matched run-for-run between the two arms.
This is a **new box**, so its levels are not comparable with the 256-point
ten-factor grid the six topology reprises above share: the immunity axis alone
spreads crew infection from ~5 % to under 1 % across the design, and the pooled
means below average over that spread.

*SURF-KO-01 is a null.* Against baseline (postings 221 = 14.39 %, crew-only 8,
mean pax infection AR 6.213 %, crew 2.651 %), the knockout gives 216 (14.06 %),
crew-only 10, pax 6.196 %, crew 2.597 %; paired over 1,536 voyages, 882
bit-identical, posting flips 33 off / 28 on (sign p = 0.61), Δ pax −0.017 pp
(se 0.067), Δ crew −0.054 pp (se 0.046). Taking a food employee on service
duty from 545.4 to 42.8 surface touches an hour, all shift, every day, does not
move crew infection on this hull. Read: the service-surface channel is not the
crew arm's dose — the same verdict tranche 33's per-multiplier knockout gave
the fomite route. Nothing here licenses touching either rate.

*The two boarding intervals resolve, each on its own role.* By quartile of the
sampled unit interval (baseline arm, 384 voyages a quartile):

| axis quartile | pax AR % | crew AR % | postings % |
|---|---:|---:|---:|
| `boarding_prevalence_passenger` [0.025 → 0.040] | 5.70 / 5.96 / 6.18 / 7.02 | 3.24 / 2.15 / 2.04 / 3.17 | 13.0 / 15.9 / 10.7 / 18.0 |
| `boarding_prevalence_crew` [0.007 → 0.030] | 6.26 / 6.31 / 5.94 / 6.34 | 1.78 / 2.52 / 2.65 / 3.66 | 13.8 / 14.6 / 14.1 / 15.1 |

Spearman over the 256 point means: passenger prevalence ρ = +0.46 on pax AR,
+0.07 on crew; crew prevalence ρ = +0.08 on pax, +0.39 on crew. Each role's
boarding prevalence drives mainly its own arm, and on a 134-crew, 7-day hull
the crew arm's *level* is set by how many crew board carrying it as much as by
anything caught aboard — the crew interval's low end halves crew infection
relative to its high end. Within the sourced intervals neither axis reaches the
posting-rate or A5 record, and the intervals are not to be narrowed on that
account.

*`IMMUNE-ROLE-01` is the one axis that spans the record, and it does so by
construction.* Crew infection AR by quartile of the unit axis: 5.08 / 3.01 /
1.90 / 0.61 %; pax 6.10 / 6.18 / 6.48 / 6.08 % (unmoved); A5 1.20 / 2.05 / 3.41
/ 10.05; postings 15.4 / 16.4 / 14.6 / 11.2 %; crew-only postings 6 / 2 / 0 / 0.
Spearman ρ = −0.72 on crew AR, +0.04 on pax. The relation is close to
`crew AR ≈ (1 − f) × crew AR at f = 0`: an immune host is removed from the
crew numerator, so A5 rises as `1/(1 − f)` and passes 4.3 somewhere near
f ≈ 0.6–0.7 on this grid. That number is an **inversion of the anchor, not a
measurement**, and it is recorded here only so that it cannot later be presented
as one. Two things it does establish: (i) with no crew immunity at all (first
quartile) the model's crew are infected at ~5 %, i.e. about five-sixths as
often as passengers — the crew excess is not a 20 % effect to be found in a
route, it is a factor of ~3.5 in crew *susceptibility or exposure* that no
represented mechanism supplies; (ii) the posting rate barely moves along the
axis (postings are passenger-channel), so crew immunity is not where the
frequency excess lives either. The structural gap recorded above stands: the
model has no host that persists between voyages, so whether real crew carry
that much immunity is unmeasured and unmeasurable in this tree. No value of
`crew_immune_fraction` is adopted; the default remains unset.

Finite-sample statements, all of them: over this design and this seed set, the
knockout resolved no effect, the boarding intervals resolved role-specific
effects, and the immunity axis resolved a near-linear one. None of it is a
statement about the continuous box.

**`CONTACT-SCALE-01` divides a contact draw between the classes present, and
does not change its size.** Every topology repair so far reallocated *who* a
host could meet while `per_partner_contact` drew the same POLYMOD 13.4
contacts/day whatever the room held, so occupancy could not reach the dose at
all. Shirreff et al. 2024 (*Epidemics* 47:100807, DOI
10.1016/j.epidem.2024.100807; 2,114 proximity-sensor wearers, 15 hospital wards,
33,946 contacts, contact rate fitted against the number of persons actually
present as `c = a(φ)·N^φ` with `a(φ)` renormalised so total contact time is
conserved) measures **both halves of that question and they answer differently**:
a person's contacts with *everyone* present are frequency-dependent — most
wards' credibility intervals include zero and the aggregate favours `φ = 0`, so
the fixed daily total is the measured answer and is left alone — while contacts
*directed at a subpopulation* scale with that subpopulation's density,
superlinearly (`φ > 1`) in several wards for patient→patient and
nurse→patient pairs and negatively in a few. Grade **B** (analogous confined
institution: an acute-care ward standing in for a dining room and a service
zone), origin **R + Fig 1/3** (read from the Results text; the ward-level figure
values are not digitized).

What lands is that second half only. `transmission.contact_class_exponent`
(default **0**) allocates a target's existing draw over the classes in its pool
as `N_class^(1+φ)` normalised — the `+1` because a class of `N` eligible
partners already holds `N` of the uniform draw's weight, so `φ = 0` is exactly
the share-of-the-room draw the model has always made and takes the same code
path, RNG included. It applies inside whichever pool the target is drawing from,
so a table party, the rest of a dining room, a cabin and a corridor each divide
their own share. A pool holding one class is untouched at every `φ`. The number
of contacts is never changed: the allocation is renormalised over the classes
present, and a class can only *lose* an allocated contact by having fewer
eligible members than its share, which is the same cap a whole-room draw has
always had.

**No value is adopted.** Nothing measures `φ` for a dining room, a crew mess or
a cruise ship of any class, and the ward exponents differ by pair type, by ward
and between day and night, so a single number would be invented. It is a
declared swept axis, and the default reproduces the shipped model exactly. The
configured range **[−2, 3]** is a *refusal* band — wide enough to contain the
reported ward posteriors, which run from below zero to above one, and narrow
enough that a typo cannot enter as a kernel — not an interval and not a prior;
any campaign sweeps a sub-range it states. `φ` may not be selected because it
moves A5, A9, the posting rate or an attack rate: this is the first mechanism by
which passenger density can reach the *crew* arm (a crew member's contacts with
passengers scale with passenger density), which makes the sweep a test and would
make a fitted `φ` the destruction of that test.

**Measured (Batch `1d0b8693` φ = 0, `81e7a57e` φ = −1, `ac5ff0b7` φ = 0.5,
`15c01df4` φ = 1, `7a58b0a6` φ = 2; image `bounded-design-v18`).** Expedition,
the same 256-point Sobol design over the 13-factor `expedition_sensitivity`
box as the three-arm campaign (design seed 37, 6 seeds a point, seed base 500),
1,536 voyages per arm, five arms differing in `contact_class_exponent` alone
and matched run-for-run. The sub-range swept is stated: {−1, 0, 0.5, 1, 2},
the span of the ward exponents Shirreff reports, and nothing outside it.

*The control is the shipped model.* The φ = 0 arm is bit-identical to the
three-arm baseline (`cede0027`, image v17, pre-`CONTACT-SCALE-01` code) in
1,536 of 1,536 voyages, every row equal — the kernel's activation check, on the
campaign path and not only in the unit tests.

*Every φ in the swept range is a null on the crew arm, and near one on the
passenger arm.*

| φ | postings | crew-only | pax AR % | crew AR % | A5 (inf) | vs φ = 0: Δ pax pp (se) | Δ crew pp (se) | flips off/on, sign p |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| −1 | 208 (13.54 %) | 8 | 5.928 | 2.543 | 2.33 | −0.285 (0.079) | −0.107 (0.049) | 42/29, 0.15 |
| 0 | 221 (14.39 %) | 8 | 6.213 | 2.651 | 2.34 | — | — | — |
| 0.5 | 215 (14.00 %) | 10 | 6.280 | 2.719 | 2.31 | +0.067 (0.080) | +0.068 (0.055) | 39/33, 0.56 |
| 1 | 217 (14.13 %) | 13 | 6.196 | 2.581 | 2.40 | −0.017 (0.077) | −0.070 (0.052) | 39/35, 0.73 |
| 2 | 219 (14.26 %) | 12 | 6.209 | 2.627 | 2.36 | −0.004 (0.076) | −0.024 (0.052) | 42/40, 0.91 |

Between 769 and 794 of 1,536 voyages are bit-identical to the control in each
arm (a pool holding one class draws the same partners at any φ, and the extra
multinomial only fires in a mixed pool). Across the whole range A5 sits in
2.31–2.40 against 4.3, postings in 13.5–14.4 % against 0.6–1.6 %. The one arm
that resolves anything is φ = −1, where the classes present share a draw
*equally* regardless of size, so a passenger's contacts are pulled toward the
smaller crew class: passenger infection falls 0.29 pp (3.6 se) and crew falls,
not rises, by 0.11 pp (2.2 se) — the direction is against the naive reading
that giving crew a larger share of passenger contacts should raise crew
infection, and at 2 se it is not resolved on this sample. At φ ≥ 0.5, where a
crew member's contacts are concentrated onto the larger passenger class and a
passenger's onto other passengers, nothing moves in either arm beyond 1.3 se.

Read: on this hull, *which class* a host's fixed 13.4 contacts land on is not
where the crew excess lives, over this design. The same verdict every
reallocation of partners has returned since BERTH-01 — the cabin, the crew
mess, the sitting, the table party, and now the class — and for the same reason
stated at the head of this entry: the aggregate draw is frequency-dependent by
measurement, so no reallocation of it changes how many contacts a host has, and
the model's direct-contact dose is evidently insensitive to whom they are with.
Whether that insensitivity is itself a defect (a shedding distribution too flat
across hosts for the identity of the partner to matter) is a separate question
this sweep does not answer.

No `φ` is adopted; the default stays 0. Finite-sample statements only: over
these 256 points and 6 seeds, no arm in the stated sub-range resolved a crew
effect. This says nothing about the continuous box, about other hull classes
(the mixed pools on a 1,900- or 2,100-passenger hull are larger and more
frequent), or about a `φ` that differs by pool type, which Shirreff's
pair-specific exponents would license and this sweep did not vary.

**`AERO-NEAR-01` gives the air route a sub-room compartment, and gives this arm
nothing.** The short-range inhalation route now has a near field over the
co-located unit — the cabin at night, the table party at a meal, adjacent tables
as the second ring — added to the unchanged zone-well-mixed far field:
`κ · w · m · (1/V_unit − 1/V_zone)` per near partner, where `m` is the aerosol
mass that partner already emits into the same pool. No emission is created (the
zone pool keeps the whole mass, the near field being nested inside the far field
and draining into it), the term vanishes when the declared unit is not smaller
than the room, and `retained_fraction = 0` or an absent block is the pre-change
route on the same code path. Geometry is **declared** (a per-berth and a per-seat
volume the run must state when it turns the near field on; a run that turns it
on without them is a load error) and both magnitudes — `κ` and the neighbouring
table's ratio `ρ`, whose ordering envelope is Li 2021's CFD column — are
**declared swept axes with no adopted value**, because tranche 36 returned ∅ on
the near-field volume and exchange rate for a table or a bedroom. Adjacency is a
declaration, not a distance kernel: tables are dealt in consecutive slices of a
sitting and consecutive indices are the neighbour pair, so there is no third
ring. The cabin's four convergent ×3–4.5 estimates stay the post-repair check
they were, not a multiplier.

**Nothing in §2 or §3 of this file moves.** The near field admits only arms with
*continuous* airborne emission, and `norwalk_gi` is `emesis_conditioned` because
the record supports no continuous respiratory norovirus emission (§4 item 16).
So a norovirus sweep over `κ` is a **null by construction** — not a measurement
— and this change is measurable on the `sars_cov2_resp` arm, whose restaurant
record is the out-of-sample structural check. The norovirus half of the defect
is the **emesis** pool's near field, which is still outstanding.

**`CONTACT-ARCH-01`: the contact draw is derived from the schedule and the
architecture, and POLYMOD 13.4 becomes the reference and the control, not the
generator.** The uniform draw is a citation-only adoption with no register row:
Mossong et al. 2008 (PLoS Med 5:e74; 7,290 one-day diaries in 8 countries,
97,904 contacts) counts *distinct persons per day* met by skin-to-skin contact
**or** a two-way conversation of ≥ 3 words — only ~⅓ physical outside the home,
country means 7.95–19.77, weekdays 30–40% above Sundays, professional contacts
excluded in four countries, pulled up by 10–19-year-olds and falling after 50 —
in a general population that goes home at night. As the generator of a
faecal-oral hand-transfer route on a confined ship it is **Grade C**: wrong
contact definition, wrong population, wrong setting, and role- and
activity-blind by construction, so a waiter on a ten-hour shift and a passenger
asleep drew the same count, nine `Sleep` hours carried 37.5% of the day's draw
against a measured ~6% of institutional contacts at night (Vanhems 2013), and
no zone could change *how many* partners a host met, only *who*. That last
point is why every reallocation since `BERTH-01` returned a null on the crew
arm. The 13.4 is **kept** — at its definition, in this ledger, and in
`density_contact_spec.md` — as the general-population whole-day reference and
the paired control arm of any campaign.

The repair is a generator, not a number. `transmission.activity_contacts`
(off by default; absent or `enabled: false` is the uniform draw on its old code
path and RNG) resolves each susceptible, per mixing unit, per epoch, into one of
eight activities from state the engine already holds — the unit the
architecture placed it in (cabin compartment, hallway residual), the zone type
(`Dining`), the schedule token (`Sleep`, `Work`, `Free`, `Meal:*`), the duty
state (`_on_service_duty`) and the seating (`dining_party_ids`): `cabin`,
`corridor`, `work_service`, `work_other`, `dining_table`, `dining_venue`,
`leisure`, `other`. The run declares each activity's rate in distinct partners
per hour, a number or a `{passenger, crew}` mapping; the clock converts it, the
voyage multiplier applies, the Poisson draw is capped by the unit's eligible
pool, and the unchanged sampler (table party, cabin, class exponent `φ`) picks
the partners. Role therefore enters **through the schedule and the duty
assignment** — crew `Work` hours are passengers' `Free` hours, `work_service`
is crew by construction — and through a per-role rate only where a setting's
evidence distinguishes the roles. Occupancy does not enter the rate (Shirreff
2024's aggregate is frequency-dependent); it enters through the pool and `φ`.

**No rate is adopted, and none can be defaulted.** Enabling the block requires
all eight activities declared; a missing activity, an unknown one, a rate
outside the refusal band `[0, 30]`/h (Duval 2018's individual maximum is
47.3/day), a role mapping missing a role, or any `contact_mode` other than
`per_partner_contact` is refused at load with the key named. The sourcing is
[tranche 37](../literature/consensus_tranche_37_contact_architecture.md) and
the intervals to declare are in
[`contact_architecture_spec.md` §4](../contact_architecture_spec.md): Pung et
al. 2022 (*Nat Commun* 13:1956; the only cruise proximity-sensor record, four
3-day sailings at 50% capacity under COVID-era controls, so a **floor**, not a
rate) — passengers median **20** and crew **10** unique close contacts/day,
F&B visits plateauing at **3** (IQR 2–5) after ≥ 1 h, **71%** of
passenger–passenger episodes in F&B locations, cabins explicitly not measured;
Jiang 2017 and Duval 2018 for working roles (Grade B analogues); Vanhems 2013
for the night share; Mossong's location split (home 23%, work 21%, leisure
16%, travel 3%) as the reference decomposition. A first campaign should hold
every role split at 1 so that any crew:passenger difference is *produced* by
the schedule and the architecture, which is the point; the §6 checks (per-role
daily totals against 20/10 and 13.4, night share against 5.9%, dining share
against 71%) are out-of-sample reports, never targets, and tranche 37's finding
that instrumented crew made half the passengers' contacts means this change is
expected, if anything, to move A5 *away* from 4.3 — which the first matched
campaign then did, 2.34 → 2.02 across the interval bracket, with the box's
upper corners refused by the §6 totals (§4 item 17). Invariants held by `tests/test_contact_architecture.py`: absent
and disabled run-identical; the control still draws the POLYMOD mean; every §2
resolution rule; every refusal; a rising rate raises the draw in its own
activity and nowhere else; `n_contacts ≤ r0_draw ≤` pool; partners distinct and
present; doses finite.

**Every screen and gate result to date belongs to no ship class, before
`COMPLEMENT-01` (history §9m).** They ran `mega_cruise_5000` — a hull declaring
5,000 passengers and 2,000 crew — with `num_agents = 450`, i.e. 316 passengers
and 134 crew: the expedition class's complement in the mega class's spatial
graph. Complement and platform were independent fields with independent
defaults in two places (the campaign's own table, and the observation model's
`Design` plus both design CLIs), so B3 (#29), which repaired the capacity
*constants*, left the execution path free to pair any complement with any hull.
Two consequences bite the anchors directly: VSP posts at 3% of a complement, so
every posting frequency was scored where the trigger is 5 crew cases out of 134
against observed postings' median 830 crew (only ~4% at 200 or fewer), and zone
occupancy was ~1/15 of nominal against the density kernel's reference occupancy
of 50. The repair derives the complement from the hull's declared
`nominal_complement` with one reader, refuses a stated complement that is not
the hull's, and moves the default hull to `classic_cruise_1900`, the modal
observed class (66.1% of postings carry 600-2,200 passengers; 3.6% carry more
than 3,600). No constant moves. The class-weighted A9 re-scoring this enables
still requires a class-stratified voyage denominator; posted-outbreak class
shares are outcome-conditioned and cannot serve as fleet weights.

**Every arrival prevalence, and every posting rate measured under one, is void
before `ARRIVE-01` (history §9l).** Epoch 0's port call was offered to the
engine twice — once by initialization, once when the epoch loop reached epoch 0
— so a boarding spec's per-person probability was realized as two independent
Binomials over the same eligible population, and epoch-0 explicit seeds were
applied twice. Measured over 40 voyages of the quiet-region point, passengers
arrived infected at 5.09% against a declared 3.25% and crew at 3.32% against a
declared 1.85%. This is not a small perturbation of the anchors that failed: at
3.32%, arrival alone delivers about 4.4 of the 5 cases VSP's 3%-of-134 crew
trigger needs, so a voyage could post before any transmission occurred. Every
campaign since boarding landed at #54/#440 — the `bounded_design_v2` screen, the
#37 v2 ten-factor gate, the 1,440-seed quiet corner and the matched
duty-exclusion pair — was computed in that regime and must be re-run before its
posting frequencies are read as the declared model's. Their conditional outbreak
magnitudes and factor rankings are affected too, in an unmeasured direction.
Nothing in the repair moves a constant: the spec's declared prevalence is what
now obtains.

**Every dose figure in this repository is void.**
`environmental_faecal_release_log10_g_per_epoch` (the old `dose_adjustment`,
still accepted as a legacy alias) was last fitted against a contact layer that no
longer exists: #351 rebuilt the fomite chain, #352 added emesis, and #353
raised the direct-contact kernel about 10x and the shared-surface touch rates
4-10x. A dose fitted before those is not transferable, and no refit has been
run since.

Also withdrawn and not yet replaced:

**Every figure computed inside a container before `PKG-02` is not comparable
with a figure computed in a checkout.** The campaign, design and analysis images
never copied `presidio/data/`, and the decision runtime treated an absent
class-interaction matrix, information-diffusion configuration or global-health
timeline as a licence to use empty defaults. A container therefore scored a
ship whose social layer was off while reporting the same run spec. The
divergence is not small in the places it reaches: on one Morris design point the
merged AWS screen and the local screen differ in 55 raw effect entries, and
deleting `presidio/` from a local checkout reproduces the container trace
md5-identically. The 20-shard `bounded_design_v1` screen
(`6ca5b363-f1d2-4e94-9719-e903a1605288`, all 20 children SUCCEEDED) is
operationally complete and **scientifically superseded**: it must be re-run on
the repaired image before any μ\* from it is read, and it is in any case only
sensitivity information, never a value or an interval. `PKG-02` ships the data
in all three images and makes an absent runtime input an error.

`bounded-design-v3` closes the equivalence check the repair was made for. The
four-child seed-sharding smoke re-run on the repaired image
(`7e542e5f-1b8c-4b2c-af27-c44bdf1b3b7d`, 2 trajectories x 4 seeds, 2 seed
blocks, `--design-seed 17`) produces shard artifacts whose raw effects are
**identical** to a local run of the same four shards, factor by factor and
trajectory by trajectory, where the pre-repair image differed in 55 entries.
Against a local *unsharded* screen the merged result agrees to 8e-15 relative
in the 25 pooled per-trajectory effects that move at all, which is the floating
point associativity of a seed-weighted mean over two blocks versus one mean
over four seeds, not a model difference. Both merge refusals still fire
(a missing shard; a duplicated seed block). The re-run 200-shard screen is
`bounded_design_v2` (`77d99c06-485d-4bed-8e87-8bcb6663fad2`); the
`bounded_design_v1` reports stay in S3 as the record of what the degraded image
produced.

**The re-run screen has landed and its verdict is one Grade D factor
(history §9k).** `bounded_design_v2` (200/200 children, merged in
`telemetry_buffer/observation_model/bounded_screen_v2_merged.json`) ranks
`environmental_faecal_release_log10_g_per_epoch` first on all six outputs by
13x over the next factor on attack rate; the four food/faecal-chain axes rank
third to sixth, 35-151x below it. The degraded-image `v1` merge is kept beside
it (`bounded_screen_v1_merged.json`, labelled) and differs by at most a factor
1.2 on any mu\* except the smallest. This is a ranking: it selects no value,
narrows no interval, and the admissible-region question from #37 is untouched
by it.

**Hand recontamination became an event, not a per-epoch relaxation
(`SYMP-EFF-01`, §4 item 0).** A norovirus host's hand load is now returned to
the measured Liu ceiling at a Poisson defecation event and decays between
events, instead of relaxing toward the ceiling every epoch. Any route share,
surface-reservoir mass or fomite/food dose measurement taken before this change
is **not transferable across it**: the same probe's total surface mass moves
about five orders (5.87e6 -> 53.0) at an unchanged epidemic size. Two
surface-lineage-recovery test expectations moved and are attributed to this
change rather than rebaselined silently. No shedding curve, hand target,
wastewater path, grade or interval changes here.

**Leisure-venue assignment and exterior-zone AHU membership changed.** The
`Free`-zone leisure draw is now capacity-weighted over passenger-accessible
venues instead of uniform over every `Free` zone, and exterior zones — open-air,
semi-open and open-aft decks — are no longer members of recirculating AHU
networks on any cruise platform. Both change zone occupancy and zone-to-zone
airborne coupling, so any attack-rate, route-share or dose measurement taken
before this commit is not transferable across it. No constant, grade or interval
changes here.

- **The v4 campaign** and every campaign before it. Each was invalidated by a
  defect found after it ran (§12 of the history).
- **The C1 reported-case bracket (2,880 runs, 2026-09-05).** Withdrawn as a
  bracket, not as runs. Its nine `dose_adjustment` rungs 12.0-14.0 produced
  bit-identical output at every seed across all 47 recorded outputs — resolved
  fraction 1/9 — so the ladder sat entirely inside the region where the
  environmental-release term has already gone to zero, and no dose interval,
  empty or non-empty, may be quoted from it. Measured in
  [`c1_reported_case_bracket_result.md`](c1_reported_case_bracket_result.md).
  Its syndromic arm is separately unscored: the runs recorded no sick-call
  hazard, and the scorer will not assume one.
- **Any host-level attack rate taken from a co-seeded bundle run, for any one
  pathogen.** Every agent-level infection and illness field is a projection
  across all of a host's lineages
  (`natural_history.project_legacy_illness`), and the summary counters, the
  reported-case ladder and the VSP threshold all read that projection, so a run
  of `active_profiles` — which seeds norovirus, influenza A and SARS-CoV-2 with
  one index case each — reports the union and attributes it to nothing. Measured
  at the Morris box centre over seeds 500-502: attack rate 0.4348 co-seeded
  against 0.0052 with norovirus alone, `vsp_posted` 1.0 against 0.0, peak epoch
  166 against 8. The influenza arm was activated at `f95677c` (2026-09-04),
  after the 2026-09-01 Morris pass, so the contamination is post-dated to that
  measurement rather than an explanation of it; it is nonetheless why the #36
  re-run isolates the screened pathogen (`--co-seeded isolated`, the default in
  `bounded_screen.py`). A composite run is a legitimate scenario, but it is a
  different scenario, and its ranking may not be compared with an isolated one.
- **The #36 Morris ranking (350 runs, 2026-09-05), as a statement about the
  current model.** Withdrawn on its initial condition, not on its arithmetic.
  Every one of its design points started from one fiat norovirus index case;
  #54/#440 landed the day after those runs and moved arrival into each
  pathogen's profile as a boarding prevalence draw (`norwalk_gi`: 3.25% of
  passengers, 1.85% of crew), which the initiation engine now owns outright.
  The regime is different, not merely re-plumbed: at the same box centre, same
  hull, agents, horizon and seed, the boarding arm reports a passenger
  infection attack rate of **0.0759 against ≈0.005** under one index case, and
  a peak at epoch 61 rather than 8. The screen's own §3 reading — that five of
  six factors sat below the floor because the isolated epidemic was near
  extinction — is exactly what a ~15× denser arrival changes, so the ranking
  may not be carried into #37 as a restriction on which factors it searches.
  The measurement stands as a measurement of the retired condition; a
  replacement pass needs its own floor, because the floor was taken under the
  same retired condition.
- **Every food-route dose, route share and posting rate measured before the
  FOOD-ARCH-01 deposition repair.** The route's deposit was a fixed share of
  every zone shedder's whole faecal emission; it is now contacts × per-contact
  transfer × hand load with the hand depleted. The shipped contact rate was set
  so the *expected* deposit at the shipped hand load and release adjustment is
  unchanged, and the orchestrator smoke did not move, so this withdrawal is
  narrower than DIM-01's: the level is preserved in expectation. What is not
  preserved is the route's *response* — it now varies with hand load, hygiene,
  role and the swept contact rate, and no longer with the release adjustment —
  so any statement of the form "the food route carries X% of dose" or "factor Y
  moves the food route" predates its mechanism and must be re-measured. This
  compounds the withdrawal below rather than replacing it. The replacement
  measurement is
  `telemetry_buffer/observation_model/route_weight_measurement_findings.md` §8:
  under boarding, on the shipped grid, the food route delivers **2e-7 of
  pre-weight norovirus dose**, against the withdrawn 93-99.9%. The per-shedder
  deposit is preserved in expectation, so the collapse is the loss of the
  whole-emission coupling (a hand load saturates where an emission does not),
  not a chosen magnitude. **Correction, FOOD-PERHEAD-01:** that entry also
  attributed the collapse in part to "the per-head division of the pool", and
  the attribution was wrong. The divisor is scale-neutral in both currencies —
  mass delivered is exactly independent of how many diners share the pool, and
  per-head dose is zone-size invariant at steady state, because deposits scale
  with the shedders present while consumption is a fraction of the pool (§9 of
  the findings). It is also the *generous* choice on establishment rather than
  the conservative one: expected infections rise with the number sharing a
  fixed mass, since concentrating it wastes supra-saturating dose. The model
  now sits far below Mouchtouri 2024's 7.3-32% food-involved outbreak share,
  having sat far above it; that is a recorded discrepancy, not a target, and
  the candidate cause that survives the probes is a deposition channel with no
  term in the route at all — emesis into or near food, and product contaminated
  before it meets a hand — not the allocation rule.
- **Every food-route dose and route share measured on the hourly grid before
  the pool fractions were unit-declared (Edison DIM-01).** `FOOD_INGESTION_FRACTION`
  0.05 and `ENV_DELIVERY_FRACTION` 0.01 were applied once per *epoch* with no
  clock conversion, so on the shipped 1 h grid a food pool was eaten down at
  24 days' worth of ingestion per day — about 14× the daily-grid delivery
  over 24 physical hours. They are now `FOOD_INGESTION_FRACTION_PER_DAY`
  (compounding, `decay_per_epoch`) and `ENV_DELIVERY_FRACTION_PER_DAY`
  (dividing, `amount_per_epoch`); the two deposition shares are shares of an
  already per-epoch emission and were not converted. No value changed. This
  sits under #37's empty region and the "every voyage posts" rate measured
  after it (food was 93-99.9% of delivered dose in the last route
  measurement), so neither may be read as a property of the model until
  re-run. Which of the six factors' magnitudes it moves is not yet measured.
- **Any claim that the model reproduces VSP attack rates.** Withdrawn at #346
  and not re-established. Expedition's earlier agreement was a cancellation of
  an inflated infection rate against a deflated illness ratio.
- **Route shares.** The often-quoted "droplet carries 94-96% of establishing
  dose" dates from the post-#338 measurement and remains withdrawn: it predates
  #351/#352/#353, all three of which change route magnitudes directly. The
  current measurement is
  [`route_weight_measurement_findings.md`](../../telemetry_buffer/observation_model/route_weight_measurement_findings.md),
  taken at `e8b2b95`, which finds droplet no longer dominant and reports mass
  share and establishment share as distinct objects. It adopts nothing and
  changes no constant.
- **The passenger/crew ratio.** Same reason.

**The removed-fraction non-secretor mechanism is withdrawn and replaced
(Wave 1, task #21).** `norwalk_gi` no longer carries
`innate_nonsusceptible_fraction`. It carries
`secretor_negative_fraction` 0.20 (FUT2 se428 nonsense-homozygote prevalence in
European/North American populations, Grade B) with
`secretor_negative_relative_susceptibility` 0.20 (Teunis 2020 GII rows,
0.015 / 0.076 = 0.197, Grade B), applied multiplicatively to the host's
susceptibility multiplier instead of assigning zero. The removed-equivalent
fraction this implies is 0.20 × (1 − 0.20) = **0.16**, the ceiling published in
#367, so the arm no longer asserts sterile immunity that Teunis 2020 and
Rouphael's 4-of-8 GII.2 challenge refute. `innate_nonsusceptible_fraction`
survives only as a deprecated alias (relative susceptibility 0.0) so the other
bundles in `data/pathogens/` keep their present behaviour. The history below is
retained because the sequence of reversals is the reason the mechanism changed.

**The mega-cruise campaign still runs the withdrawn mechanism.**
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py:988` writes
`innate_nonsusceptible_fraction` into its per-run overrides, so every campaign
run rides the deprecated alias at relative susceptibility 0.0 — sterile immunity
— while `data/pathogens/active_profiles.json` runs partial susceptibility. The
behaviour is deliberately unchanged: the campaign sweeps the removed fraction,
and converting that swept axis into a relative susceptibility is a design
decision rather than a rename. Any campaign result must therefore be read as
having been produced under the withdrawn mechanism until that decision is
taken.

**The emesis titre × volume parameterisation is withdrawn and replaced by the
quantity Kirby identifies (Wave 2, task #38).** `EMESIS_TITRE_GEC_PER_ML` is no
longer an input: no profile key resolves to a titre, and the emesis record
carries titre only as a derived diagnostic (`episode_load / volume_ml`). The
emitted load now comes from `EMESIS_TOTAL_SHED_GEC_RANGE` = (1e5, 1e8) genome
copies, log-uniform, drawn **once per symptomatic illness** and partitioned
equally over the episodes drawn with it. Provenance: Kirby et al. 2016 Table 3,
per-subject **cumulative** emesis shed — GII.2 Snow Mountain 1.8e7 GEC
(SEM 1.8e7), GI.1 2.3e8, per-subject values spanning ≈1e5–1e8; Grade B on a
surrogate genotype, because no GII.4 emesis measurement exists (tranche 4 §3).
The endpoints are set by an arithmetic check and not by tuning: the arithmetic
mean of a log-uniform on [1e5, 1e8] is (1e8 − 1e5)/ln(1e3) = **1.45e7**, within
1.25× of the measured 1.8e7. The reason this is a reparameterisation rather than
a value swap is that the three former inputs are not independent — the measured
GII.2 titre mean 1.6e5 GEC/mL times the measured mean total volume 845 mL is
1.35e8, **7.5× above** the same paper's measured cumulative 1.8e7, because the
titre mean is taken over positive samples on a heavy right tail. Volume stays
drawn over 50–800 mL as the physical deposit volume only, and
`EMESIS_EPISODES_RANGE` is corrected to the measured (1, 7): with the total
identified, the episode count only partitions and times that same total.
**Every emesis-derived numeric expectation and every RNG-dependent emesis golden
is invalidated by this change**, since both the magnitude and the emesis draw
sequence move.

**Surface decay is now in the units it is sourced in, everywhere (Wave 2 task
#41, completed by R1/#59).** `surface_decay_log10_per_day` is the **only** key:
the deprecated fraction-valued alias `surface_decay_per_day` is deleted from the
engine, the schema and every profile, and a profile that still spells it that way
falls through to the default rather than being honoured. `norwalk_gi` carries
**0.124939 log10/day**. The conversion f = 1 − 10⁻ᵏ happens in exactly one
function, `transmission_core.surface_fraction_per_day`, instead of living in a
comment in `bounded_screen.py`. **No measurement recorded here is invalidated:**
0.124939 = −log10(1 − 0.25) reproduces the previous per-day fraction exactly, so
no shipped behaviour and no golden moved — this is a unit migration, not a
refit. The divergence #41 recorded is therefore closed rather than carried: the
sourced key is now the only key, and it is exercised by everything that runs.
The screen box is expressed unconverted, [0.067, 0.79] log10/day, and remains
adopted **for the screen box only** — the shipped 0.124939 is still an unsourced
value that happens to lie inside it near the slow end.

**Hand↔surface transfer is split by direction, and a drying axis is added at
neutral (Wave 2, task #42 item 3).** `SURFACE_TO_HAND_LOGNORMAL` keeps the pickup
direction; `HAND_TO_SURFACE_LOGNORMAL` — identical numbers — carries the deposit
direction, because they are two different measured quantities carrying very different
drying levers: ~100× on the deposit direction, where hand→surface falls
13% → 0.1% with 10 minutes of drying (Tuladhar 2013) and 59% → <1%
(Sharps 2012), against only ~5× on pickup, where surface→hand dries to
2–11% (Sharps) / 2.0 ± 2.0% on steel (Tuladhar). The shipped distribution is therefore a
**wet-contact** parameterisation, defensible against Tuladhar's and Bidawid's
immediate 13% and about 100× too high for a dried donor hand. The new
`hand_to_surface_drying_multiplier` multiplies the deposit side only, defaults to
1.0, is set by no profile and consumes no RNG, so it reproduces the shipped
arithmetic exactly; it is screened over [0.008, 1.0] (log10) because **which
drying state applies to a hand continuously recontaminated by its own shedding
is not measured**. That is why it enters as an axis and not as a value.

**The Morris ranking in
[`bounded_screen_results.md`](bounded_screen_results.md) is invalidated a second
time, and by this change.** The screen's seventh factor was
`innate_nonsusceptible_fraction` over [0.00, 0.16]; it is now
`secretor_negative_relative_susceptibility`, now over [0.04, 0.83] (widened in
tranche 6, below) — a different factor over a different interval, so every
elementary effect in that document is stale. The re-run on the recut `surface_decay_per_day` box was **killed part-way
and never completed**: only the 20-seed noise floor at the new box centre exists,
and there is no completed screen on either the recut box or the substituted
factor. Nothing may be ranked from that document until a screen is run on the
current box.

**That screen has now been run, isolated, and it is
[`bounded_screen_isolated_36.md`](bounded_screen_isolated_36.md) (#36,
2026-09-05).** 350 runs, 10 trajectories over the current six factors, 5 matched
seeds per point, `--co-seeded isolated`, against a 20-seed floor at the same
centre. It resolves **one** factor above that floor —
`environmental_faecal_release_log10_g_per_epoch`, monotone, ratio 1.6–2.0 on the
whole-ship and both passenger channels — and places the other five below it,
including every factor on the crew reported-case channel. `peak_epoch` carries no
ranking and `vsp_posted` cannot be thresholded from a centre that never posts. It
is a ranking and nothing else: no interval moves, no admissible region follows,
and #37 is a separate measurement. Two things it changes here: the resolved
factor is the box's only grade-D one, so the scored outputs are dominated over
this box by the quantity with the least right to its interval; and five
unresolved factors is a statement about the design, since at 450 agents with one
index case the isolated epidemic sits near extinction (centre attack rate ≈0.005)
and the seed budget, not the trajectory count, is what binds.

**The “≈3.7× GI-vs-GII infectivity per genome copy” comparison is withdrawn as a
unit error (tranche 6 §3).** It was published in tranche 3 and repeated when
Wave 3 was proposed. Reproducing Teunis et al. 2020's single-copy GII risk of
0.076 inside the shipped beta-Poisson family requires α = 2.85, which implies an
ID50 of ≈10 genome copies — five orders of magnitude below every challenge
measurement. Those fits model *aggregation* and report risk per aggregate, not
per disaggregated qPCR copy, so the two figures were never in the same unit and
no genogroup infectivity ratio can be read off them.

**The norovirus dose-response is no longer blocked by mechanism: it is declared
and swept (tranche 6 §2; register §3.1).** The shipped α = 0.111 / β = 32.81 is
the disaggregated GI.1 challenge arm of Teunis et al. 2008, and it is declared as
that rather than refitted. Mapped onto α at fixed β = 32.81, the human GII
evidence gives α ∈ [0.072, 0.161] — Rouphael 2022 GII.2 challenge ID50 5.1×10⁵
→ 0.072; Guix 2020 GII outbreak illness ID50 2,934 → 0.154, a lower bound on
infection α; Ramesh 2020 gnotobiotic-pig GII.4 → 0.149–0.161 as Grade C
corroboration — and 0.111 lies inside it, within 3% of its geometric centre
(0.108). No profile value changed, and β does not become an independent factor:
family, aggregation assumption and dose unit are one categorical choice (Liu et
al. 2026).

**#43's norovirus half is closed on the unit, and the ≈925 copies-per-aggregate
bridge is withdrawn (tranche 23).** The dose axis of the shipped row is
**administered genome copies (gEq/GEC)** — the unit both challenge inocula were
quantified in, and the unit in which Kirby, Teunis & Moe and Atmar's reply agree
that the two studies' no-aggregation models give similar estimates. On our side
the live per-agent confluent-hypergeometric beta-Poisson path has an N50 of
**16,644 copies** and the closed-form helper an approximate **16,871 copies**;
both give **P ≈ 0.047** at `D = 18`, so pairing "ID50 = 18" with this row stays
arithmetically impossible whatever unit the 18 is in.

The 925 figure was `16,643.78 / 18 = 924.65` — the N50 it was derived from — and
is **withdrawn as circular**. Its published replacement is **µ_c = 517**, the
aggregate-size parameter in Kirby's Figure 1 caption, which belongs to the
*pooled aggregation-corrected* fit (α = .024, β = .017) rather than to our
no-aggregation row — that row has no aggregation parameter, which is what "no
aggregation" means. **The ~100× aggregation fork is retracted, and the arithmetic
is why:** that pooled fit's exact N50 is 1.85 aggregates, and 1.85 × 517 = 954
copies, within 6% of Teunis's aggregated ID50 of 1,015 gEq. An aggregate-unit
axis re-expresses the same dose; it does not move it by two orders of magnitude.

What is **not** settled is Teunis's own wording, and it is contested in print
rather than merely unread: Kirby's letter reports the disaggregated HID50 as
**18.2 GEC, 95% CI 1.03–4,350 GEC**; Atmar's reply calls the 18 "genomic
equivalents ... determined using assumptions about differing amounts of virus
aggregation" and argues Teunis's own 0/9 at 324 gEq and 0/8 at 32.4 gEq make it
untenable; the collaborator bundle reads the Results sentence as 18 *single
virions* under a hypothetical fully disaggregated inoculum, and is cited as
**Sec** for that. Teunis 2008's body text and Table III are **?nr** — paywalled,
no body from Europe PMC, two chunk queries returned the abstract only — so the
row-structure claims rest on secondary analysis. Nothing above depends on the
wording. **#43 was still filed against a question our own review had already
posed**, and it is withdrawn rather than sent. Atmar's measured HID50 of
1,320–2,800 gEq remains an open **5.9–12.6×** gap below the live 16,644 under the
same no-aggregation framing, and **is now declared as a span on the dose axis**,
[1.32×10³, 1.69×10⁴] gEq, `logU`, **declared and not applied** so the #36 screen
and #37 admissible-region test expose it rather than absorb it. No dose figure
changed — every dose figure in this repository remains void pending refit.

**The proposal to close that 5.9–12.6× gap by retargeting α/β onto Atmar's
HID50 is rejected on genogroup, and the gap is reclassified as a
genogroup-declaration item rather than a residual error.** The narrative review
of the exchange adds three things the ledger did not have, and the third
disqualifies the refit. First, **Atmar 2014 fits a logistic model**, not a
beta-Poisson: its 1,320 gEq (secretor-positive blood group O/A) and 2,800 gEq
(all secretor-positive, blood group B/AB being wholly resistant in that study)
are logistic ID50s, with no infection observed below 324 gEq. Importing either
would change the dose-response *family* as well as its value, and β = 32.81
would keep no provenance at all once the Teunis fit it was lifted from is
abandoned — moving α while holding β is retaining half of a rejected fit.
**Corrected by tranche 23: the family is not what produces the gap.** Kirby's
Figure 1 caption reports an *exact beta-Poisson* refit of Atmar's own data with
no aggregation — the same family and assumption as our row — at α = .28,
β = .58, whose exact N50 recomputed in-repo is 4.16 dose units, ≈**1,660 gEq**
at Atmar's ≈400 gEq per RT-PCR unit (the caption does not state its unit; that
conversion is an inference, grade C). Family and value move together and the
~10× distance from 16,644 survives, so the refusal to retarget α/β rests on the
genogroup argument below and on the after-the-gate boundary, not on family.
Second, **the two figures are not interchangeable, and the tree picks 2,800**:
susceptibility here is gated on secretor status and **not** on ABO, so a
secretor-positive agent stands for Atmar's whole secretor-positive cohort across
blood groups, which is the 2,800 arm; the 1,320 arm conditions on O/A hosts this
model cannot separate, and adopting it without an ABO nonsusceptibility gate
would overstate susceptibility by exactly the resistant B/AB share. Third, and
decisively, **Atmar 2014 challenged GI.1 Norwalk while this arm is GII**: the
`norwalk_gi` id says GI, but the profile's name, its declared genotype mixture
GII.4/GII.17/GII.2 and its pooled-GII incubation row all say GII, and against
GII challenge evidence the shipped 16,644 is roughly **30× too sensitive**
(Rouphael 2022 GII.2 ID50 5.1e5), not 6–13× too insensitive. The two claims sit
on opposite sides of the shipped value and cannot both be about this arm, so the
6–13× figure is a GI-vs-GII comparison and not a demonstrated model error. What
this item now needs is the genogroup declaration, not a fit: declared GII, the
existing α ∈ [0.072, 0.161] interval stands and Atmar 2014 is out of scope;
declared GI.1, the target is 2,800 and α/β must be refitted **jointly** to
Atmar's data and graded as a logistic-to-beta-Poisson transfer. No value moved
and the withdrawal is unchanged.
[`proposals/pathogen_class_structure_decision.md`](../proposals/pathogen_class_structure_decision.md)
then settles how the ~2.6 logs of spread across these measurements is
*structured* — as GII.4-versus-non-GII.4 classes, with the shares declared from
external typing rather than fitted, since the VSP series carries no genotype in
any of its 428 postings — and adopts no dose value either.

**The exact and approximate dose-response forms are also an open implementation
item, not a repair in this change.** Production reaches
`_dose_response_hazard` at `engines/transmission_core.py:2082`, through the
persistent Beta draw in `_dose_response_susceptibility`; the closed helper
`_dose_response` at `engines/transmission_core.py:1649` is exercised only by
`tests/test_dose_pathway_invariants.py:473`. The tree therefore carries two
spellings of one mechanism — an exact per-agent frailty path in production and
an approximate population closed form covered by a test — matching the
duplicate-mechanism archetype in the provenance guidance. Neither function nor
the test is changed here.

**The secretor screen interval widens to [0.04, 0.83], which invalidates the
pending Morris design again (tranche 6 §4).** Kambhampati 2015's pooled
secretor:non-secretor odds ratios are genotype-specific — 9.9 (3.9–24.8) for
GII.4 and 2.2 (1.2–4.2) for GII non-4, implying non-secretor relative
susceptibility 0.10 (0.04–0.26) and 0.45 (0.24–0.83) — and the declared genotype
mixture GII.4/GII.17/GII.2 straddles both rows, so the width is genotype
composition rather than measurement error. The adopted 0.20 stays inside the
interval and is not refuted, and no profile value changed. The screen box moves,
so the screen re-run that was already outstanding is invalidated a further time;
task #36 carries it.

**`innate_nonsusceptible_fraction` (history): the sourced interval is 0.00 – 0.16, and
both the shipped 0.0 and Edison's 0.2 sit outside it.** This entry has been
rewritten twice; the sequence matters, because the second reversal was caused by
reading a paper more carefully than the profile.

- #367 withdrew the queued 0.0 → 0.2 correction, using the **GII** row of
  Teunis et al. 2020, *Epidemics* 32:100401 — Se+ 0.076 against Se− 0.015 per
  genomic copy, a ~5× reduction rather than an exclusion — corroborated by
  Rouphael et al. 2022 (*JID*, GII.2: 4 of 8 Se− ill at top dose) and Frenck et
  al. 2012 (*JID*, GII.4: 1 of 17 Se− ill against 13 of 23 Se+). Non-secretors
  are partially susceptible to GII, so a fully-removed fraction is the wrong
  mechanism and its ceiling is ≈0.16.
- #371 reversed that, on the grounds that the same paper's **GI** row is Se+
  0.28 against Se− **0.00007** (a factor of ~4,000), with Lindesmith et al.
  2003, *Nature Medicine* reporting the FUT2 null allele as fully penetrant in
  GI.1 challenge — no nonsecretor infected **at any dose**. That is correct for
  GI.1, and #371 asserted `norwalk_gi` is a GI.1 arm.
- **That assertion was false, and the profile says so.** `norwalk_gi` carries
  `name: "Norwalk Virus (Norovirus GII.4)"`; its `strain_evolution.genotypes`
  are `GII.4 / GII.17 / GII.2` at equal prior weight; and its incubation note
  states outright that the distribution is "GII rather than the GI the
  pathogen_id implies, because this profile's genotypes are GII.4/GII.17/GII.2."
  The arm simulates GII. **The GII interval therefore governs, #367's
  conclusion stands, and Edison's 0.2 is not defensible for this arm.**

**The chimera is real but runs the other way round.** What is mis-genogrouped is
the *dose-response*, not the susceptibility term: `alpha` 0.111 / `beta` 32.81
are inherited from `Person.java` and were, per
[`norovirus_model_history.md`](norovirus_model_history.md) §9c, fitted to
administered oral **Norwalk (GI.1)** inoculum — while name, genotypes,
incubation and validation targets are all GII. GI is 3.7× more infectious per
genome copy in Se+ hosts than GII (0.28 vs 0.076), so the arm is running a GI
infectivity curve against a GII strain set, and correcting it would move
infectivity and susceptibility in opposite directions, partially cancelling in
the aggregate attack rate. Prevalence is population-specific in any case (~20%
European-ancestry, 29% of the Lindesmith 2003 sample, 19% in the Rwandan cohort
of Munyemana et al. 2025), so a removed fraction — if the mechanism were right —
would remain an interval rather than a value. Evidence:
[`../literature/consensus_tranche_2.md`](../literature/consensus_tranche_2.md)
§1–§2 and
[`../literature/consensus_tranche_3.md`](../literature/consensus_tranche_3.md)
§1; derivation:
[`bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md)
§3.3. No profile JSON is changed by this entry.

**Withdrawn (2026-09-03): the claim that the chronic immunocompromised shedder
is the norovirus importation channel.** Stated in PR #383 and in the #45 notes.
The mechanism stands — a chronic host boards already shedding and never clears
on a 7–14 day voyage — but the prevalence was never computed. Tranche 10
computes it two ways, which disagree by 2.5 orders (1.4e-5 to 4.2e-3 of a
boarding population), and both ends sit one to three orders below the ordinary
asymptomatic adult channel at 2.5–4%. No chronic-shedder boarding point
prevalence is licensed; the importation channel is mostly immunocompetent.

**Withdrawn (2026-09-05): the reading that any structural arm since `BERTH-01`
was measured against the anchors at all.** Every one of those campaigns swept
the `expedition_sensitivity` box, and that box contains
`environmental_faecal_release_log10_g_per_epoch` — the void dose normaliser —
on a *linear* interval [4, 24]. The quantity enters as an exponent:
emission is `10^(curve[idx] − adj)`
(`engines/infection_dynamics_bridge.py`, `shedding_amount`), the shipped
faecal curve peaks near 11 log10, so the interval sweeps released material over
**twenty orders of magnitude**, from 10⁷ down to 10⁻¹³ of a curve unit. A
Grade D axis twenty logs wide is not a sensitivity range; it is the whole
model, switched on and off.

Where the switch sits, measured (scratch diagnostic, expedition_cruise_450,
168 epochs, `norwalk_gi`, every other factor at its box midpoint, two seeds per
point — acquired-aboard infections per voyage, separated from boarding imports
by `boarding_state`):

| `adj` | acquired/voyage | imported/voyage | pax AR | crew AR | posted |
|---:|---:|---:|---:|---:|---:|
| 4 | 150.5 | 9.0 | 0.424 | 0.190 | 1.00 |
| 5 | 113.5 | 9.5 | 0.342 | 0.112 | 1.00 |
| 6 | 17.5 | 10.5 | 0.081 | 0.019 | 0.50 |
| 7 | 1.0 | 10.5 | 0.030 | 0.015 | 0.00 |
| 8–12 | 0.0 | 10.5 | 0.027 | 0.015 | 0.00 |

The transition is complete inside the bottom three units of a twenty-unit
interval. Above `adj ≈ 7` — 85% of the swept box — the continuous faecal chain
delivers no transmissible dose at all, and a voyage's infections *are* its
boarding imports. At the midpoint over twelve seeds, 12 voyages produced 2
acquired infections between them, none posted, and their dose was fomite from
emesis deposition: the emesis channel draws an absolute load
(`EMESIS_TOTAL_SHED_GEC_RANGE`) that the normaliser never touches, so the two
shedding channels are on incommensurate scales and only one of them is swept.

Three consequences, none of which is a new measurement:

1. **The posting rate the campaigns report is the fraction of the box below the
   switch.** A uniform design over [4, 24] puts roughly 15% of its points under
   `adj ≈ 7`, those points post on essentially every voyage, and the rest post
   almost never — against the 13.5–18.6% postings reported across the φ,
   `CONTACT-ARCH-01` and `CONTACT-ARCH-02` arms. The model has not been
   producing 10× too many outbreaks; it has been producing a near-certain
   outbreak in one corner and a dead ship everywhere else, and the campaign
   reported the mixture.
2. **A5 has been measuring boarding prevalence, not transmission.** In the
   import-only regime the passenger:crew infection ratio is 0.0269/0.0149 =
   1.81, which is the ratio of the two boarding-prevalence intervals and
   nothing else; the explosive corner gives 2.2. The 2.02–2.37 that nine arms
   reproduced is that mixture, and no partner-topology or contact-count change
   could have moved it, because in 85% of the box no contact transmits.
3. **Every null since `BERTH-01` is uninterpretable as a mechanism result.**
   Cabin, crew mess, sitting, table, class exponent, activity-derived contacts
   and dwell saturation were each averaged over a box in which most points
   have no transmission to reallocate. The mechanisms are not refuted; they
   were not tested.

Nothing is adopted or refitted here, and the interval is not narrowed: the
refit that would license a value is the one the whole ledger is waiting on.
What this entry withdraws is the *interpretation* of the campaign readouts, and
what it adds is a precondition — no mechanism arm on this box can be read
against an anchor until the dose scale is resolved, or until the design
conditions on it (stratify the readout by `adj`, or sweep the mechanism at a
declared scale rather than marginalising over twenty logs of it). The
diagnostics behind this entry are scratch, not repository functionality, and
are recorded here rather than committed.

## 2. Anchors

Targets, from `telemetry_buffer/observation_model/anchor_measurement_spec.md`:

| | quantity | target |
|---|---|---|
| A1 | ever-ill attack rate, passengers (Wikswo whole-ship cohort) | ~0.154 |
| A2 | ever-ill / infected | 0.68-0.81 (0.59-0.81 GII.4-weighted) |
| A3 | reported / ever-ill (infirmary capture) | 0.60 ± 0.05 |
| A4 | reported passenger attack rate | inside the hull-class IQR |
| A5 | passenger / crew reported attack rate | ~2.9-3.5 |

A5's two figures come from different sources and are both live: the anchor spec
says ~3.5 (7% vs 2%); the VSP 424-outbreak series gives ~2.9 (passenger
5.7-6.9% against crew 2.0-2.4%). Treat the target as a range, not a point.

**"Stable on both sides of the COVID break" was wrong, and is withdrawn.** It
was inferred from A5 rather than measured, and the per-outbreak series
contradicts it: across the break the median crew rate rises by 1.37x
(1.004-1.677, p=0.007) while the passenger median does not move detectably,
so the passenger/crew ratio falls by about a third (A7c = 0.668, 0.532-0.907).
A5 must therefore be quoted per era, not as one era-independent number, and any
fit that reproduces A5 pooled across both arms is reproducing an average of two
different ratios. Measured at `e167e32`; see A7 in
`telemetry_buffer/observation_model/anchor_measurement_spec.md`.

**Last measured values, and this is the part that matters: they are stale.**
All of the following were taken at `d557f39`, immediately after #346 and
*before* #348, #351, #352 and #353 landed. Every one of those changed
transmission. Do not quote these as current model behaviour; they are recorded
so the next measurement has something to compare against.

| | expedition | classic | measured at |
|---|---:|---:|---|
| infection attack rate | 0.407 | 0.465 | `d557f39`, 120 runs, dose 2.0 |
| ill / infected (A2) | 0.341 | 0.364 | `d557f39` |
| reported passenger AR (A4) | 3.48% | 3.89% | `d557f39` |
| A5, ever-ill ratio | 0.94-1.15 across hulls | | pre-#351 |
| A5, reported ratio | 0.85-0.97 across hulls | | pre-#351 |

Status at that measurement: **A4 failed on both hulls** (expedition below the
4.51% floor). **A2 missed by ~1.8x.** **A5 missed by ~3x, in a model that
returns roughly parity.** A1 and A3 were not jointly satisfiable with A2 under
homogeneous exposure — infection attack rate and ill/infected are welded to the
same dose, so they cannot be separated by refitting.

**The four hard-coded VSP class targets are withdrawn.** The triples
`score_anchors.py` carried (expedition 8.56%, 4.51-13.60%; classic 5.59%,
4.46-7.76%; spirit 5.64%, 4.44-7.90%; mega 5.61%, 3.40-7.45%) had no
derivation script and no source note, and do not reproduce from
`telemetry_buffer/observation_model/vsp_outbreak_series.csv` under capacity
bands or under any alternative band edge tried; the expedition class misses by
the widest margin. They are replaced by values recomputed from the series at
runtime, per hull class **and per era**, by
`telemetry_buffer/observation_model/vsp_class_era_scoring.py`, which
`score_anchors.py` now calls (`--vsp-era`, default `pre`). Derivation and
sources: `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md`.

VSP passenger attack-rate targets, for A4, as now derived (333 of 428 postings
carry a passenger denominator; the 87 `legacy_pre2004` rows carry none, and the
5 `shutdown` postings are never pooled into either arm):

Binned on **passenger** complements as of B3 (#29); the earlier cut of this
table binned passenger denominators against passenger-plus-crew totals and is
superseded:

| hull | era | n | q1 | median | q3 |
|---|---|---:|---:|---:|---:|
| expedition | pre | 21 | 4.00% | 5.32% | 10.45% |
| expedition | post | 12 | 3.22% | 7.42% | 13.74% |
| classic | pre | 95 | 4.15% | 5.52% | 7.82% |
| classic | post | 8 | — | — | — |
| spirit | pre | 130 | 4.18% | 5.26% | 7.24% |
| spirit | post | 43 | 3.72% | 4.95% | 6.95% |
| mega | pre | 16 | 3.55% | 6.00% | 7.49% |
| mega | post | 3 | — | — | — |

Against the floor of ten postings, the recut moves anchors in both directions:
**`mega_cruise_5000` gains a pre-2020 A4 anchor** (16 postings, where the
total-agent bins gave it four) and **`classic_cruise_1900` loses its post-2020
one** (8 postings, where they gave it 32). `score_anchors.py` reports a
withheld cell as `n/a (insufficient VSP postings)` rather than scoring it, so
no post-2020 classic result and no post-2020 mega result may be described as
passing or failing A4.

**A8/A9 are now implemented model-side, but the post-COVID arm has no
unconditional incidence observation at all.** The model-side channels are in
`telemetry_buffer/observation_model/score_anchors.py`; their MIDRS constants,
interval targets and fixed hull-to-GRT mapping are in
`telemetry_buffer/observation_model/midrs_incidence_targets.py`, sourced from
`telemetry_buffer/observation_model/midrs_observed_targets.md`. A8 aggregates
reported cases and travel-days over every run, including non-take-off runs. A9
applies the VSP 3% passenger-or-crew rule to eligible voyages and reports
ineligible runs separately. A truth-only arm emits an explicit no-reporting
sentinel rather than a false zero.

The only published MIDRS incidence analysis is MMWR Surveill Summ 2021;70(6),
covering 2006-2019; a search of CDC's VSP data pages, MMWR and the
peer-reviewed literature found nothing after it. So the post-2020
health-practice configuration changes exactly the channel we have no post-2020
observation for. A pre-arm A8 match plus a post-arm A4 match is the most that
can honestly be claimed until a post-2020 MIDRS analysis exists.

The MIDRS source record carries three conflicts that must remain attached to
the implementation. First, the MMWR Results prose labels 26.7 and 29.2 as
mega and super-mega **crew** rates, but Table 2 identifies those as passenger
rates; the crew values are 14.7 and 16.0, with the crew maximum 19.8 on
extra-large ships. Second, the reported "80.6% of the 252 ships were extra
large" is actually 30,039/37,258 voyage reports; the per-ship size distribution
is unpublished. Third, MMWR counts 156 investigated passenger outbreaks,
whereas `telemetry_buffer/observation_model/vsp_outbreak_series.csv` contains
208 posted outbreaks over the same period. A9 therefore reports an interval
spanning those definitions rather than silently mixing them.

**Resolved in B3 (#29): `HULL_CAPACITY` was a total-agent complement, not a
passenger complement.** The role split used by the model is authoritative in
`orchestrator_init.py::role_group_for_agent`: on the expedition reprobe
summary `..._dose12_..._s503`, `cumulative_ever_infected_passenger = 107` and
`infection_attack_rate_passenger = 0.338608`, giving
`round(107 / 0.338608) = 316`; the corresponding crew values are 40 and
0.298507, giving 134. Thus 316 passengers plus 134 crew equals the
`num_agents = 450` total. `HULL_CAPACITY["expedition_cruise_450"] = 450`
therefore denotes the total complement, not the passenger denominator.
`BAND_EDGES` in `telemetry_buffer/observation_model/vsp_class_era_scoring.py`
are geometric means of those total complements while binning observed
passenger counts (`pax_total`), so the A4 class bins inherited this offset.
**Repaired in B3 (#29):** each hull's `spatial_layout.json` now declares
`nominal_complement` as a passengers/crew split, `HULL_PASSENGER_CAPACITY`
reads the passenger half, and `BAND_EDGES` are geometric means of those
passenger complements (636 / 1,684 / 3,240). The A4 targets merged in #360 are
superseded by the recut table above. Still unrepaired: the hull-to-GRT
mapping behind A8/A9 picked representative ships for the classic and spirit
hulls against the same total-agent figures, so their GRT band is one band too
high pending two re-sourced representative ships. A8's passenger and crew denominators instead
come from the role-derived complements emitted in each run summary and do
not use `HULL_CAPACITY`, so A8/A9 are unaffected.

### The #37 feasibility gate: empty, and two of six anchors never became evidence

**Run, 2026-09-06:**
[`admissible_region_37.md`](admissible_region_37.md). 128 Sobol' points over the
full six-factor box, 5 matched seeds each, `mega_cruise_5000`, pre-2020,
norovirus isolated at the boarding channel. **0 of 128 points admissible**; the
best passes two of the five scoreable anchors, and every anchor pair passes
jointly zero times except A5+A4 (twice).

What binds, and this is what stops the result being read as structural
infeasibility:

- **A8 and A9 are unusable as currently mapped, not failed.** A4 is conditional
  on a posted outbreak and A8 is unconditional over all travel-days, on the same
  numerator: converted to A8's units at these runs' 5.19-day voyage, A4's target
  is 683-1,442 per 100,000 travel-days against A8's 16.9-29.2 — 23x apart, so no
  parameter value satisfies both in a cell of identically distributed voyages.
  A9's target likewise cannot be represented by 5 runs (it needs >=180 eligible
  voyages for one posting to land inside 0.00419-0.00558) and is reported
  design-limited rather than waived.
- **A1 against A2 is the one genuinely structural tension.** Both are inside the
  box's reach separately (8 and 2 passes) and never together: ill/infected is
  dose-dependent, so A2 reaches 0.59 only at an ever-ill attack rate of
  0.30-0.32, against A1's ceiling of 0.22; inside A1's band it tops out at 0.544,
  short of A2's floor by 1.08x. A5 sits the same way: over the 24 points where
  the ratio is in band, A1 never exceeds 0.073.
- **A1 against A4 binds in the observation model.** A4's reported band lies
  entirely below A1's ever-ill band, so both can hold only if reported/ever-ill
  is ~0.16-0.75 — roughly what A3 asserts. The shipped observation model's
  capture instead **rises with epidemic size and saturates at 1.0**, and A3 lands
  out of its 0.35-0.45 construction band at 123 of 128 points. That capture
  saturation is a defect of the observation model (§4.7), not grounds to widen
  either anchor.

No interval was widened, no endpoint selected, no anchor dropped and no constant
refitted after this gate ran. Unlike #36 this design is not near extinction: the
take-off fraction is 1.0 at all 128 points.

### The #37 re-run on the repaired structure: still empty, and now nothing is design-limited

**Run, 2026-09-07:**
[`admissible_region_37_v2.md`](admissible_region_37_v2.md). 256 Sobol' points over
the **full ten-factor box** (the six above plus the two stool-event and two
food-route axes), **180 matched seeds each** — 46,080 voyages, 256/256 AWS Batch
children succeeded. **0 of 256 points admissible, 0 pending, 0 unscored**, and
**every** pairwise joint pass count is zero, including A5+A4.

What this adds to the row above:

- **A9 scores for the first time, and fails high across the whole box.** 180
  seeds is the smallest cell in which one posting can land inside 0.00419-0.00558,
  so `design_limited_anchors` is now empty. The *quietest* point in the box posts
  on 0.0333 of eligible voyages (6 of 180) — **6.0x above A9's ceiling** — and
  A8 fails high at every point in both channels (quietest passenger cell 40.2 per
  100,000 travel-days against 29.2). The take-off fraction is 1.0 at all 256
  points: not one of 46,080 voyages went extinct. The emptiness is therefore no
  longer attributable to anchors that never became evidence.
- **A1-vs-A2 reproduces with four more swept axes and 36x the seeds.** Inside
  A1's band ill/infected spans 0.436-0.562, short of A2's floor by 1.05x (1.08x
  before). Those same 13 points post on 0.994-1.0 of voyages.
- **A5 no longer reaches its floor at all** (0.427-1.805 against 2.5-4.5), and is
  undefined at 211 of 256 points.
- **The A4/A8 conflict is now computed in-run**: at 7.075-day voyages A4's band
  implies 501-1,059 per 100,000 travel-days against A8's 16.9-29.2, separation
  factor 17.2, no overlap.
- **A3 is out of its construction band at 134 of 135 defined points**, so the
  capture-saturation defect (§4.7) is unchanged.

This strengthens the tranche-31 diagnosis into the binding gap: with no
symptom-conditioned spreading-efficiency term, every voyage takes off, so the
quiet/outbreak mixture A8 and A9 measure is unreachable from any point of the
sourced box. No interval widened, no anchor dropped, no constant moved.

**Read-out, 2026-09-08** (§3.6 of the same report, harness
`telemetry_buffer/observation_model/gate37_quiet_voyages.py`): take-off at 1.0 is
*not* every voyage posting, and conflating the two overstated the failure.
**36,087 of 46,080 voyages (78.3%) stayed below the 0.03 posting threshold**, and
the median point posts on 20 of 180 (11.1%) — 23x A9's target rather than
uniformly loud. What the box lacks is the middle: quiet voyages sit almost
entirely at points with an ever-ill attack rate under 0.01 (89% quiet over 217
points), while inside A1's band 2,338 of 2,340 voyages post. At the 222 points
posting on under half their voyages, 176 have a median voyage that reports
**nothing** while carrying a 5.1-5.7% *infection* attack rate, and the cell mean
bounds the posting voyages' reported rate at <=5.5-6.8% — inside A4's posted-
outbreak IQR of 3.55-7.49%. So the outbreaks are the right size and ~23x too
frequent, and the voyages between them are symptomless infection rather than
small outbreaks. That is a symptom-conversion statement, which points at the
absent spreading-efficiency term rather than at seeding heterogeneity or a wider
dose ladder. The bound is a ceiling read off A8's cell mean and the posting
count; the shard streams keep cells, not per-run rows, so the within-point
distribution itself is not recoverable from the artifact.

**Re-run of the quiet corner at 1,440 seeds, 2026-09-05:**
[`lowposting_region_37.md`](lowposting_region_37.md), harness
`telemetry_buffer/observation_model/gate37_lowposting.py`. 16 of the same grid
indices, 1,440 matched seeds each with every voyage's row retained — 23,040
voyages, 384/384 Batch children succeeded. The ceiling above is now a
measurement, and four things change:

- **The posting floor is real, not a resolution artifact.** The quietest point
  posts 46 of 1,440 = **3.194% [2.348%, 4.238%]**, and none of the sixteen exact
  intervals reaches A9's 0.42-0.56%; the 1,440-seed frequencies reproduce the
  180-seed counts point for point.
- **Extinction exists at 0.26%** (45 of 17,280 quiet-region voyages fail
  take-off with peak prevalence 9 against 10), so "take-off 1.0" above was a
  180-seed resolution statement, not a structural one.
- **Conditional on posting, the reported passenger attack rate is median 4.11%,
  IQR 3.48-5.06%** — measured, replacing the <=6.0% ceiling, and still inside
  A4's IQR. Quiet-region mass is 55.1% infected-but-no-illness, 10.8% ill with
  nothing reported, 29.5% reported below threshold.
- **51.5% of the quiet region's postings are crew-only.** The crew complement is
  134, so five reported crew cases (3.73%) post a voyage; the passenger channel
  alone posts on 2.228%, still 4.0x A9's ceiling. The in-sim `vsp_trigger_epoch`
  fires only on the passenger channel while A9 scores both — a definitional gap
  in the trigger, not a parameter, recorded as outstanding.

**A9's numerator is passenger-channel, measured, 2026-09-05:** the reporting
rule is 3% of passengers *or* 3% of crew, so both of A9's numerators are sets of
channels and had to say which. Classifying the 208 postings of the 2006-2019
window on rates recomputed from their published counts gives 182 passenger-only,
22 both, **1 crew-only**, 3 at neither; the 3 include the two rows whose hosted
`pax_ill` dropped a leading digit (2013 Celebrity Millennium, 2011 Sea Princess,
already triaged in the extraction log), so on the printed percentages the
passenger channel carries 206 of 208. MMWR's investigated counts bound the same
quantity loosely and in the same direction — 16 crew outbreaks against 156
passenger — so the observed crew contribution sits in **0.5-9.3%** against the
quiet region's 51.5% crew-only and 66% crew-at-threshold. The rule stays
passengers-or-crew; `score_anchors` now reports
`A9_posting_probability_passenger_channel` beside the or-rule so a crew arm
firing on a different scale is visible rather than pooled away. No threshold
moved and no floor was introduced: the observed crew-only rows include one-case
postings on small complements, so no universal minimum-case publication rule is
sourceable from the series. Recorded in `midrs_observed_targets.md` section 4.

**The regulated crew duty exclusion is implemented and measured, and it is not
the A9 defect, 2026-09-05:** VSP's 2018 Operations Manual 4.4.1.1.1 *requires*
symptomatic crew off duty — food employees 48 h symptom-free with documented
medical clearance, other crew 24 h — where 4.4.2.1 only advises isolation of
passengers, and the model had the crew exposure multipliers with no counterpart
exclusion. `SOP-VSP-CREW-01` adds it as a standing operational rule, off by
default, and it is numerically inert when off (in the campaign image, current
`main` reproduces #467's 17,280 archived rows exactly). Run as a matched arm over
the same twelve quiet points, factor vectors, 1,440 seeds and seed order —
common random numbers, one difference — with `compliance_fraction` at **1.0**,
the declared enforced-regulation upper bound rather than an estimate, since
maritime compliance is null in the literature: postings fall **793 → 780 of
17,280**, crew-only 408 → 391, and paired that is 51 voyages stopping and 38
starting, McNemar's exact **p = 0.20**. The exclusion arm posts on 4.514%
[4.209%, 4.834%] against A9's 0.42-0.56%. So the mechanism is **neither
sufficient nor necessary** for A9: 7.5× above the ceiling with it on, and its
effect on the scored quantity is not resolvable at 17,280 matched voyages. The
reason is structural rather than parametric — VSP's numerator is cumulative
reported cases and the rule cannot fire before the first crew case is
*identified* (first admission at epoch 59-93 of 168), so it prunes the tail of a
chain whose first five cases are already counted. What stays implicated is
upstream: crew infection rate, crew-versus-passenger reporting, and the
3%-of-134 five-case trigger. Measurement:
[`dutyexcl_matched_37.md`](dutyexcl_matched_37.md). No constant moved, and no
compliance value was chosen to move an anchor.

## 3. Out-of-sample checks

**Park et al. (2015)** — surface swabs during a shipboard outbreak; nothing was
ever fitted to it. Observed 80-31,217 copies/swab in sick passengers' cabins,
16-113 in public spaces, a gradient of roughly 100-300x.

| | #351 (hand chain) | #352 (+ emesis) | #353 (+ measured contact) | #355 (+ cleaning) |
|---|---:|---:|---:|---:|
| cabin, confined | 1,434 | 1,434 | 5,571 | 4,120 |
| public, 60 shedder-h/day | 356.9 | 356.9 | 384.9 | 368.0 |
| cabin/public gradient | 4.02x | 4.02x | 14.5x | 11.2x |
| shedder-hour asymmetry needed for 100x | 75x | 75x | 29.3x | 29.3x |

Levels sit inside the observed ranges across 1.5 orders of magnitude, from
independently sourced constants. The **gradient still fails**. A single emesis
episode reaches Park's level (1,047-31,400 copies/swab at Park's stated
recovery) but carries no intrinsic cabin/public gradient — the touchable-area
factor and the per-area concentration cancel exactly. The residual is *where*
people vomit, and reaching 100x needs 98.5-99.7% of episodes in the host's own
cabin. That fraction is unmeasured, is not a model parameter, and reading it off
Park's gradient would be fitting. Refused. Harness:
`telemetry_buffer/observation_model/park_surface_check.py`.

Routine cleaning (#355) moves the gradient the **wrong way**, from 14.5x to
11.2x, and the reason is instructive: a daily pass over 37% of objects competes
with continuous removal by hand pickup, so it multiplies the time-averaged pool
by 0.74 in a quiet cabin (loss 0.029/h) but only 0.96 in a busy public zone
(loss 0.33/h), where pickup already clears surfaces faster than housekeeping
can. Real ships clean cabins and public spaces on different schedules with
different products; the model does not, because nothing measured says how. The
gradient shortfall is therefore not a cleaning gap — it remains §4's sick-host
movement problem. Measured at the #355 head with
`ROUTINE_CLEANING_COVERAGE=0.37`, 1.29 log10/pass, one pass/day.

**The COVID discontinuity** is the better instrument, is now measured, and is
not yet scored. It is a *difference*, so errors common to both arms cancel —
which is what this effort needs, having spent its length finding errors that
cancel in levels. #355 supplies the NPI lever it needs (routine coverage and
per-event log10 are separately configurable, and outbreak response is a
distinct mechanism), but one schedule still applies to every zone class, so the
passenger-facing asymmetry cannot yet be expressed.

Two limits on the instrument, from
`telemetry_buffer/observation_model/post_covid_configuration_sources.md`. Every
A7 statistic is conditional on VSP posting, so an intervention that stops an
introduction from taking off is *invisible* to all of them — it prevents the
posting rather than shrinking it, and pre-boarding screening and denial of
boarding are exactly that kind. A7c is therefore a lower bound on NPI effect,
and a flat A7a is not evidence that NPIs did nothing. Second, the post-2020 arm
carries two changes with opposite signs: the NPI change, and a susceptibility
rise from two years of interrupted exposure (O'Reilly 2021, Lappe 2023, the
latter projecting >2-fold community incidence at full contact resumption).
Prior immunity must be set from those sources, or the NPI configuration
silently absorbs the immunity effect. Also note the industry's own hand-hygiene
push was alcohol-rub-centric, and alcohol rub is measurably weaker than soap
against norovirus (Tuladhar 2015), so it is expected to be near-null here.

The two caveats that blocked it are now handled by construction rather than by
correction, per `telemetry_buffer/observation_model/vsp_covid_discontinuity_design.md`: score only statistics
conditional on posting, so the missing voyage denominator never enters; and run
VSP's own posting rule over simulated voyages, so both arms are truncated
identically. The reporting-intensity confound is cancelled by taking the
passenger shift over the crew shift.

**The "~15-20% drop, p=0.032" figure is withdrawn.** It was read off
`docs/norovirus/vsp_covid_discontinuity.png`, whose per-outbreak table was never in the
repository. Rebuilt from CDC-hosted pages (`telemetry_buffer/observation_model/vsp_outbreak_series.csv`, 428
postings, `e167e32`), the passenger median moves 5.39% → 4.91%, a ratio of
0.912 (0.788-1.182, p=0.26) — no detectable level drop. The discontinuity is
real but it is not that: the crew median rises, the passenger/crew ratio falls
by a third (A7c = 0.668, p<0.001, and 0.736 with fleet composition held), and
what disappears from the passenger distribution is its upper tail — on ships
carrying 1000+ passengers, 11 of 226 pre-2020 postings exceeded 15% of
passengers ill and 0 of 48 post-2020 do, the maximum falling 25.2% → 13.5%.
About half the crew rise is composition, not behaviour: small expedition
vessels, several below VSP's own 100-passenger criterion, are posted post-2020.
Detecting an effect of this size needs hundreds of posted simulated voyages per
configuration; the design fixes 1,000.

**Mouchtouri et al. (2024) route-mode counts — a new out-of-sample check, and
the model currently fails it.** The systematic review of 45 norovirus outbreaks
on 26 cruise ships, 1990-2020, reports source and mode for 41. From its Table 3
(read from the Europe PMC JATS full text, PMC10986668): person-to-person 14,
person-to-person plus environmental 11, multiple modes 10, **food-borne 3**,
waterborne 3, unknown 4. So food as the **sole** mode is 3/41 = **7.3%**, and
counting every mixed-mode outbreak as food-involved bounds food involvement
above at 13/41 = **32%**.

The last route measurement puts the **food route at 93-99.9% of delivered
dose**. That is inconsistent with the setting's own outbreak record by an order
of magnitude, and it is the first external constraint this repository has on
route *shares* rather than on levels. It is admissible precisely because a
mode-attribution count is a different observable from A1/A2/A4/A8; the paper's
attack-rate columns are deliberately not used, and no constant may be moved to
bring the share into 7-32% ([tranche 29](../literature/consensus_tranche_29_food_and_environmental_deposition.md) §5). What the check does not do is say which
route should carry the dose instead: person-to-person and
person-to-person-plus-environmental together are 25/41, and the model's
contact, droplet and fomite routes are not separated in the review's
categories.

**The symptomatic-to-asymptomatic reproduction-number ratio** is the second
external constraint on something other than a level, and the model has not been
measured against it. Sukhrie 2012 (DOI 10.1093/cid/cir971, five GII.4
healthcare-facility outbreaks, all patients and staff sampled with and without
symptoms) puts R at **1.64 (95% CI 1.56-1.70)** with diarrhoea against **0.85
(0.55-1.05)** without: a ratio of **0.52**, CI corners **[0.32, 0.67]**. It is
non-circular against A1/A2/A4/A8 because it is a within-outbreak ratio of
reproduction numbers in hospitals rather than a cruise attack rate or posting
rate, and it is an **upper bound** on the ratio applying to a
`never_symptomatic` host, because Sukhrie's exposed arm is "without diarrhoea"
and so contains vomiting-only cases while ours has no symptoms at all.

The model's realised ratio is expected to sit near 1.0, because symptom status
reaches `transmission_core` through the **emesis path and nowhere else** -
faecal deposition, hand load, food deposition and direct contact are per-copy
identical for a carrier and an ill case. That is the check's point: it measures
a structural gap rather than a mis-set constant, and **no constant may be moved
to reproduce 0.52** ([tranche 31](../literature/consensus_tranche_31_symptom_conditioned_spreading.md)
§3.2, §4.2). Adopting 0.52 as a per-copy multiplier is separately refused:
R is net of every route including the emesis path already in tree, so it would
double-count by exactly the amount emesis already supplies.

## 4. Outstanding

Roughly in dependency order.

00. **The dose scale governs the box, and every mechanism arm is downstream of
   it.** `environmental_faecal_release_log10_g_per_epoch` is swept linearly
   over [4, 24] as an exponent, the switch between a runaway epidemic and no
   onboard transmission at all sits at `adj ≈ 6–7`, and §1's entry records the
   measurement. Until the refit resolves the scale, a campaign on this box
   measures which side of the switch its design points fell on. Two ways
   forward that adopt nothing: **stratify** every readout by `adj` so the
   mechanism is read within a regime instead of marginalised across the
   switch, and **declare** the emesis channel's absolute load and the
   continuous channel's normaliser on one scale, since only the second is
   currently swept. Neither is implemented.

   **What the release term should be instead, sourced but not adopted.**
   [Tranche 38](../literature/consensus_tranche_38_environmental_release.md)
   assembles the factors that would replace the scalar: titre (existing curve)
   × stool mass per event (Rose 2015, **128 g/cap/day over 1.20
   defecations/day**, Grade A, and the review states its data are highly
   skewed) × deposition fraction per 100 cm² per flush (Goforth 2023 and Sassi
   2018 seeded MS2, **10^−3.7 to 10^−8.8** on seat surfaces, Grade B-minus
   surrogate) × event rate (tranche 32). Composed, that envelope is **about
   five orders of magnitude wide against the box's twenty**, and it
   **straddles** the `adj ≈ 6–7` switch rather than sitting on one side of it.
   The third mode — the **background deposition onto ordinary surfaces** — is
   a **literature null**: crAssphage is quantified only in water
   (copies/100 mL), and every built-environment chair study is 16S relative
   abundance, including the classroom-chair source-contribution work (Meadow
   2014, gut-associated indicator taxa on chair seats, no absolute load). The
   one quantified built-environment result is a **turnover timescale** — a
   desk's community recovers within **2–5 days** of a ~50% removal (Kwan
   2018) — not a level. **Nothing is adopted and [4, 24] is not narrowed**:
   the surrogate deposition fraction is PFU on a 100 cm² swab, the model's
   pool has its own declared area, and that denominator must be reconciled
   before any of this becomes a parameter.

   **The reconciliation, and the correction it forces.**
   [The denominator reconciliation](fomite_pool_denominator_reconciliation.md)
   settles the area question and overturns the paragraph above it. **The
   release scalar never reaches the surface pool**: in the profiled path the
   pool is fed only by the hand (Liu's measured 3.86 log10 gc/hand ceiling,
   through `get_pathogen_hand_target`) and by emesis (an absolute per-event
   load), and the food route deposits from the same hand — `adj` scales only
   direct contact, aerosol, HVAC, the environmental reservoir and wastewater.
   A seeded-flush deposition measurement therefore **cannot** set, narrow or
   justify `adj`, and the `adj ≈ 6–7` switch is a switch in the contact and
   air routes, with the fully sourced faecal chain left running above it.
   On the common denominator the two sides **do** reconcile — the pool enters
   a pickup only as `mass / HIGH_TOUCH_AREA_M2`, an areal density, which is
   Goforth's unit, and the PFU→gc conversion is not needed because the
   deposition fraction is a ratio of two PFU readings (carried across on an
   unmeasured MS2/norovirus partition assumption, Grade C). The comparison at
   the curve peak: the model's cabin surfaces reach at most **1.68–2.43 log10
   gc/100 cm² per day** (a ceiling — no decay, no cleaning, no depletion),
   against **4.24–9.38 log10 gc/100 cm² for one flush**, so the model's
   surfaces are **1.8 to 7.7 logs low, per day against per event**. The hand
   is simply the wrong-sized reservoir for a faecal channel: 10^3.86 copies
   against a bowl's 10^13. Still **nothing adopted**, and the flush is **not**
   entered as a pool gain, because the toilet's touchable area is unsourced
   and the pool has no within-zone structure — a seat hotspot would be smeared
   over the cabin's declared 1.5 m² on arrival, which is the recurring defect
   archetype reproduced by the repair.

0. **`SYMP-EFF-01`: the missing term now exists as a rate, and the shared
   quantity is narrowed rather than separated.** Norovirus boards at
   a prevalence of **asymptomatic faecal RNA carriage** (Grade B on its own
   denominator: Kobayashi 2021, Qi 2018, Jeong 2021), which is exactly the
   quantity **wastewater surveillance detects** - and the same emission is what
   the fomite route delivers dose from, because the sentinel samples the
   greywater fraction of the same zone pools that `ENV_DELIVERY_FRACTION_PER_DAY`
   draws on. So there is no admissible change to asymptomatic detectability
   that does not move asymptomatic infectiousness by the same factor, and the
   #37 posting-rate diagnosis cannot be resolved by adjusting either the
   prevalence or the asymptomatic shedding offset - **neither is a free
   parameter, because there is no free parameter**. The adult literature
   declines to shrink either: Teunis 2014 finds asymptomatic shedding markedly
   similar to symptomatic across peak, time-to-peak, duration and AUC, and
   states that the greater contribution of symptomatic cases must therefore be
   caused by higher **spreading efficiency**. That term is measured (§3's
   check) and absent here. Of the two candidate shapes recorded, **the first
   landed and the second was refused**: hand contamination now scales with
   defecation events per day, which is what the Sukhrie and Teunis authors' own
   hygiene attribution points at, rather than a per-copy symptom multiplier. A
   GC:PFU conversion is **refused**: 1.4-4.3 log10 wide and matrix-dependent,
   and exactly absorbed by the dose-response intercept, whose axis is
   administered genome copies
   ([tranche 31](../literature/consensus_tranche_31_symptom_conditioned_spreading.md) §4.1).

   **What the mechanism is, and what it is not.** A profile declaring
   `stool_events_per_day` recontaminates a shedding host's hand at a defecation
   *event* drawn as a Poisson thinning on the epoch grid, and between events the
   hand only decays; the event rate has two independently sourced arms,
   non-diarrhoeal **[0.43, 3.0]/day** (Grade B) and diarrhoeal **[3.0, 8.5]/day**
   (Grade C, swept), and the diarrhoeal arm applies only to a host that is
   symptomatic, drew the diarrhoea axis, and is in a phase declaring the
   diarrhoeal feature
   ([tranche 32](../literature/consensus_tranche_32_stool_event_frequency.md)).
   **Continuous RNA emission is untouched**: the shedding curves, hand target,
   zone pools and the greywater sentinel read the same numbers they read before,
   so a never-symptomatic carrier still appears in wastewater. What it no longer
   does is have its hand held at the Liu ceiling every epoch.

   **Still open, and not claimed closed.** The sentinel and the fomite route
   still consume one emission, because the sentinel samples the greywater
   fraction of the same zone pools; the mechanism reduces how much a carrier
   injects into those pools without separating the two readings. The
   whole-gut-transit and diarrhoeal-liquid gaps at the deposition constants
   (#447) remain open: the event *rate* is now symptom-conditioned, the
   per-event hand load is still the single Liu ceiling on both arms.

   **Measured consequence, withdrawn as a result and recorded as a magnitude.**
   Over a 48-epoch 10-seed probe with lineage tracking on, total surface mass
   fell from **5.87e6 to 53.0** while infected hosts moved 12 -> 13, so the
   continuous path was maintaining a faecal injection of one ceiling hand-load
   per shedding host per **epoch** - 24/day on the hourly grid - that the dose
   pathway barely consumed. Every dose figure remains void per §1; this is a
   before/after of one structural change, not a fit.

1. **`FOOD-ARCH-01`: repaired in form, and half of it remains open.** The
   deposition side is closed: the food route now composes its deposit the way
   the fomite route does — contacts × per-contact transfer × hand load,
   subtracted from the hand — so `FOOD_DEPOSITION_FRACTION_OF_EMISSION` is
   retired, the hygiene levers reach the route through the hand it deposits
   from, and the crew food-handler channel exists as its own (inferred)
   multiplier. The shipped contact rate, 0.6/day, is the corridor arithmetic
   below read backwards, so the repair did **not** choose a new magnitude at
   the shipped point; it is a declared sweep axis, and a physically plausible
   rate of a few contacts per meal is 5–17× higher, which the box must measure
   rather than the default assert. Two consequences are recorded, not repaired:
   the deposit no longer scales with
   `environmental_faecal_release_log10_g_per_epoch` at all (hand load is
   measured against the curve peak instead), which retires the coupling through
   which #36's one resolved factor reached this route; and
   **`FOOD_INGESTION_FRACTION_PER_DAY` = 0.05 against a 0.1/day decay is
   untouched**, so the 85.5%/day carry-over identified below as the actual
   mechanism behind the route's dose share is still standing. The paragraphs
   below are the statement of the original defect.

   **`FOOD-PERHEAD-01`, the allocation follow-up: one defect closed, and the
   allocation rule exonerated.** The pool was depleted by the susceptible
   shares only, so an immune or already-infected diner's food stayed standing
   and every remaining susceptible's dose rose with the immune fraction —
   bounded by `(decay + f)/decay` = 1.5× at the shipped rates, and of the wrong
   sign, since prevalence already raises deposition. Every diner present now
   eats an equal share off the pool and only a susceptible one takes a dose
   from it. What the probes did **not** find is any dependence of the route's
   size on the per-head divisor (§9 of the findings). Two things stay open, and
   neither is a value: eating is not a representable event — `f` is a declared
   pool turnover, so a zone of 3,000 diners consumes the same mass per day as a
   zone of 2, and "dose per meal" has no referent, which is where whole-gut
   transit and the diarrhoeal-liquid objection below attach; and the deposition
   channel that could carry Mouchtouri's mass — emesis into or near food,
   product contaminated before it meets a hand, and a food handler working
   while shedding — has no term in the route at all. VSP's own inspection and
   remediation records are a candidate non-circular source for the last of
   those, at the same provenance standing as B4's inspection census.

   **The deposition-channel sourcing pass has now been run
   ([tranche 30](../literature/consensus_tranche_30_food_deposition_channels.md)),
   over the general food-service literature and not only the cruise literature,
   and it separates the three channels rather than filling them.** Nothing
   below moved a constant, and no channel was implemented.

   - **Source-contaminated product is the best-sourced of the three, and the
     only one that deposits with no occupant involved.** Oysters at the point a
     ship provisions them are measured at Grade A for the EU supply: **10.8%**
     of 2,129 dispatch-centre samples positive at a mean **168 copies/g**,
     against **34.5%** of 2,180 production-area samples at **337 copies/g**,
     Class A areas 3.7% against Class B 20.0% (EFSA/Aerts 2019); retail leafy
     greens and berries at **2.2–5.3%** and **<2–3.6%** (Cook 2019, Torok
     2019). It stays unimplemented for a stated reason: the measurement is per
     **gram of a named commodity** and the pool is per **zone** with no
     commodity, so adopting it is a structure change gated on **servings per
     voyage** and **grams per serving**, and neither quantity exists. Sourcing
     it does not license adding it.
   - **Emesis into food is refused, not merely unsourced.** No study measures
     what fraction of emesis mass reaches food; and the model already carries
     emesis as a discrete event feeding the **airborne** reservoir, which is
     the mechanism the one detailed dining-room emesis outbreak actually
     supports — food could not be implicated, attack rate fell with distance
     from the vomiter (Marks 2000). A food-pool term sized by the same event
     would double-count it absent a measured destination split. This is the
     channel that would most easily have closed the Mouchtouri gap, which is
     why it is written down as refused.
   - **The food-handler channel is bounded on the wrong denominator.**
     Work-while-ill is measured in the analogous setting — 11.9% of 491 workers
     worked ≥2 shifts while vomiting or with diarrhoea in the previous year
     (Sumner 2011), ~20% ≥1 shift (Carpenter 2013), ~70% of 426 restaurant
     managers ever, with a third of restaurant policies silent on exclusion
     (Norton 2015) — but every figure is **12-month worker-level recall**,
     where a per-shift probability is what is needed, and the model has no
     food-handler shift to attach one to.

   Two by-products bear on the box rather than on the food route.
   `FOOD_HAND_CONTACTS_PER_DAY` = 0.6/day is now flagged **plausibly low by an
   order of magnitude** against the nearest measured analogues (hand-to-mouth
   6–7/h during eating, Wilson 2020; ~3.1 hand-hygiene occasions per
   handler-hour, Mohamed 2024) — neither is a hand→food contact, so the value
   is unchanged and the flag is a reason to sweep it, and it is the
   first-ranked candidate explanation for the route's 2e-7 dose share. And
   **the VSP ship-year score panel is closed as a parameter source and as a
   between-ship spread proxy**: the join has been run and is null (1,197
   inspections, mean 95.7, pre-outbreak 96.4 vs 95.1, p = 0.42 — Taylor 2018),
   and the score does not track the mechanism, being uncorrelated with the one
   objective hygiene audit that does discriminate pre-outbreak ships (r² =
   0.002, p = 0.75 — Carling 2009). Violation **content** — what a 95 has that
   a 100 does not — remains a live mechanism observable; the score does not.

   The fomite path replenishes a
   per-hand load from a measured target, counts contacts, draws a transfer
   efficiency per event, applies the drying multiplier and **subtracts the
   deposit from the hand**. The food path multiplies the whole faecal emission
   by one constant, for every shedder in the zone, with no hand, no contact
   count, no depletion and no hygiene lever — so the NPI interface (#9/#10),
   whose buffet-prompt arms act on hand-mediated routes, has almost nothing to
   act on in the route that carries the dose.

   The sourcing pass ([tranche 29](../literature/consensus_tranche_29_food_and_environmental_deposition.md)) establishes that the parts for a decomposed food
   route are already in hand — hand load Grade B in tree (Liu 2013), hand to
   **food** transfer Grade B at 0.3-46% per contact (Bidawid 2004, Tuladhar
   2013, Rönnqvist 2014, Grove 2015), contact rate ∅ null and therefore
   sweepable — and that the shipped `FOOD_DEPOSITION_FRACTION_OF_EMISSION` =
   1e-4 is **equivalent to 0.3-46 bare-hand food-contact events per shedder per
   day**, i.e. inside an admissible corridor. So the food route's dominance is
   not that constant's magnitude. It is
   `FOOD_INGESTION_FRACTION_PER_DAY` = 0.05 against a 0.1/day decay, which
   leaves **85.5% of the pool standing each day**: the pool integrates every
   shedder's deposits across the voyage and delivers to every occupant every
   day. That carry-over is food-service logistics declared as a rate, and no
   literature search can raise its grade. Of those two, the deposition form is
   now repaired and the ingestion carry-over is not.

2. **Zone-differentiated cleaning schedules — swept, bounds sourced, no cell
   adopted.** #355 closed the "nothing cleans surfaces" gap — routine
   housekeeping is a discrete pass over the measured 37% of objects it reaches,
   and outbreak-response hypochlorite is a separate, stronger, SOP-triggered
   mechanism. A search found no measured cleaning-frequency schedule
   differentiated by zone class in an accommodation or passenger-vessel
   setting. The opt-in schedule is therefore swept inside the bounds documented
   in
   [`cleaning_schedule_sweep_spec.md`](../../telemetry_buffer/observation_model/cleaning_schedule_sweep_spec.md):
   cabin frequency 0.33–1.0/day, public 1.0–12.0/day, dining/galley/crew_mess
   1.0–6.0/day; cabin coverage 0.336–0.600, public 0.292–0.454, and
   dining/galley/crew_mess 0.292–0.600. No sweep cell may be adopted as a
   parameter value or default.

   Carling et al.'s Grade A 37% measurement is specifically from public
   restrooms on cruise ships, not cabins. Applying it to cabins is an
   unsourced extension, not evidence of a cabin schedule. The shipped model
   retains its uniform default; the schedule sweep exposes this uncertainty
   without fitting it to an anchor. Its hand-only gradient envelope is
   8.6635–18.5054x, against 11.1977x for the shipped default: that is a
   bound on schedule leverage (at most 1.6526x upward), not a test of Park
   reachability, because the hand-transfer channel was already shown
   unreachable at any occupancy. The Park comparison is instead made with
   the emesis-inclusive calculation, swept over the separate, unmeasured
   fraction of a host's emesis episodes occurring in its own cabin; at 0.99,
   78 of 81 schedule cells reach Park's 100–300x range, and at 1.00 all 81 do.
   That fraction is not a schedule parameter and no value is selected. It was
   spelled "cabin-localization fraction f" until #12 and is now
   `EMESIS_IN_OWN_CABIN_SWEEP`: it counts episode locations, not transmission
   events, so the register's `f ≤ 0.5`-scale ceiling never applied to it.
   Note that the premise has changed:
   crew rates did *not* hold still across the break, they rose (A7b), so a
   configuration that leaves the crew arm untouched now contradicts the data
   rather than matching it.
3. **Refit the common dose** against VSP class targets. The contact layer
   (#353) and cleaning (#355) are now in place, so this is next. One common
   dose-response across all four hull classes; no hull-specific pathogen
   biology, ever. The first attempt (C1, 2,880 runs) is withdrawn by §1: its
   ladder was degenerate, and a replacement must be sited where the axis
   resolves — checked with `picard_framework/analysis/sweep_degeneracy.py` on a
   short probe *before* submission — and must hold the surveillance response
   fixed while the dose moves, since the two arms differ 6-80x in infection
   attack rate at the same dose and seed.
4. **Re-measure route shares and the passenger/crew ratio** on the refitted
   model. Expect #353 to push A5 *further* from 2.9 — crew work the highest
   touch-rate zones and their berthing is already ~3x denser than passengers'.
   If it does, that is a finding about what is still missing.
5. **Score the v4-successor campaign** against VSP class targets, per era,
   and never on a withheld A4 cell (post-2020 classic, post-2020 mega).
6. **A8/A9 need a fleet-scale cell before they can score anything.** #37 showed
   the two anchors as mapped cannot be satisfied by a cell of replicate runs of
   one configuration at all: A4 is outbreak-conditional and A8 unconditional on
   the same numerator (23x apart in A8's units), and A9's target needs >=180
   eligible voyages to be attainable. Either the gate's cell becomes a fleet
   spanning outbreak and quiet voyages, or both anchors are withdrawn from the
   verdict until it does. Model-side aggregation and the sourced
   MIDRS target tables are implemented in
   `telemetry_buffer/observation_model/score_anchors.py` and
   `telemetry_buffer/observation_model/midrs_incidence_targets.py`. The
   post-arm observation remains unavailable, and A10 duration trajectories are
   still Proposed.
7. **The observation model's capture saturates at 1.0, and A3 says it should
   not.** Measured across #37's 128 points: reported/ever-ill rises with epidemic
   size and reaches 1.0 in exactly the region where A1 is in band, so A3 is out
   of its 0.35-0.45 construction band at 123 of 128 points and A4 inherits A1's
   value. This is the fifteen declared, unsourced observation numbers of B2/#27
   showing up as a scored consequence; it must be repaired in the observation
   model, and A4 re-read afterwards, before an A1/A4 incompatibility means
   anything about transmission.
8. **Cabin-level environmental compartments — landed as `BERTH-01` (#475),
   measured in §1.** Before it the finest mixing compartment was
   `Cabin_Corridor`: ~37 people in 800 m³ where reality is 2 people in ~40 m³
   (crew 3); `cabin_size` and `cabin_mate_ids` existed but only exempted a mate
   from confinement attenuation. Now each stateroom is a direct-contact unit at
   full strength and its own surface pool, the corridor is a hallway residual
   at the unchanged 0.15, and each hull declares its berthing per class
   (expedition 2/2, crew_galley 3; classic 2/3, galley 4, medical and
   engineering 2; spirit 2/3, medical and engineering 2; mega 2/2) from the
   tranche-35 envelopes. **`DINE-SEG-01`** then drew the daytime half of the
   line: before it every agent's fixed dining venue was drawn uniformly across
   all Dining zones, so on expedition three quarters of crew took every meal in
   the passenger dining rooms and a quarter of passengers ate in the CrewMess
   or Galley. Now crew are seated in the hull's `crew_mess` venues and
   passengers in its `mdr`/`buffet`/`specialty` venues, each by declared
   capacity, and the per-meal rotation (off in every campaign) respects the
   same line; crew *working* a passenger venue still do so through their work
   zone. No constant moves; the matched expedition reprise is in §1 (crew
   infection unchanged, passenger infection up a third of a point). Still
   open: crew leisure is drawn from the passenger leisure
   catalogue because no hull declares a crew recreation space (crew bar, crew
   deck) — that is a zone declaration to source, not an assignment defect.
   **Sourced in
   [tranche 35](../literature/consensus_tranche_35_crew_berthing.md):** MLC
   2006 caps passenger-ship crew rooms at four; the documented norm is two
   (all Icon-class crew staterooms), two to four on 1990s hulls, two to three
   on expedition ships, one for officers; roommates are drawn by department
   and shift; and the cabin is where the record puts the risk (ill cabin-mate
   RR 3.0 in passengers, aOR 3.27 in crew; NoV on the crew cabin toilet, not
   the crew galley). The engine's crew corridor ward (37–40, `cabin_size: 3`)
   is larger than its passenger ward (25, `cabin_size: 2`), so the *model's*
   crew mix more at night than its passengers — the same sign as every other
   crew defect. The earlier note here that building the cabin "would raise
   crew rates" was a guess for 3- vs 2-berth cabins under corridor mixing and
   is withdrawn as a prediction: the direction is to be measured on AWS, not
   assumed. The corridor factors (0.15 direct, 0.25 zone) remain undeclared.
9. **Aerosol portal efficiency.** #352 computes and records the emesis aerosol
   load but does not route it into the airborne reservoir. The direction is
   settled (norovirus establishes enterically; inhalation is delivery-to-gut via
   swallowing, so the respiratory clearance proxy is the wrong quantity) but the
   magnitude is not: the 10-30% figure is deposition in mouth/nose/trachea and
   is explicitly **not** an intestinal-delivery fraction.
10. **Sick-host movement and a bathroom destination.** The Park gradient needs
   it; see §3.
11. **AWS daughter session: CONTAM vs native accumulation comparison.** Deferred.
12. **Provenance queue, re-ordered by the bounded screen.** Measured in
    [`bounded_screen_results.md`](bounded_screen_results.md) §7.
    `innate_nonsusceptible_fraction` moves to the front on consequence: it is
    the top-ranked factor while carrying the mechanism §1 withdraws.
    `contact_transfer_fraction` drops down it — across its whole sourced
    interval it moves no scored output above the measured noise floor, so the
    shipped value is still wrong but it is not an exposure. **That screen row is
    withdrawn and the item is closed by retirement (#22):** the field stood in
    the same position of the same product as
    `route_efficiency_multipliers["direct_contact"]`, so the design ranged half
    of a product and its μ\* is not a sensitivity of contact transfer at all. The
    field is deleted from the engine, the schema and the box, and refused at
    load; the route keeps one owner
    ([`../literature/consensus_tranche_12_contact_transfer.md`](../literature/consensus_tranche_12_contact_transfer.md)
    §10). No other row in that screen is affected. Emesis titre
    becomes a first-order provenance target, which it was not before.
13. **`EMESIS_TITRE_GEC_PER_ML` = 3.9e4 is the wrong figure from the right
    paper, and its two companions are also off the measurement.** Traced in
    [`../literature/consensus_tranche_4.md`](../literature/consensus_tranche_4.md)
    §1c. 3.9 × 10⁴ is Kirby et al. 2016's **abstract** value for "GII viruses",
    which pools GII.2 Snow Mountain with a 2-subject GII.1 Hawaii pilot at
    5.0 × 10³ that the paper's own Results excludes from every genogroup
    comparison; Table 3 gives GII.2 as **1.6 × 10⁵ GEC/mL** and reports no
    significant GI/GII difference (p = 0.36 against the abstract's p = 0.02).
    For a GII.4/GII.17/GII.2 arm the applicable measured value is 4.1× what is
    shipped. Alongside it, `EMESIS_EPISODES_RANGE` = (1, 3) against a measured
    1–7 events (mode 1, 32% single), and per-episode volume 50–800 mL log-uniform
    implying ≈200–600 mL per subject against measured means of 658.7 mL (GI) and
    845.0 mL (GII.2). Compounded, the pathway sits about an order of magnitude
    below the measured per-subject cumulative shed — on the screen's
    second-ranked factor. Not repaired here: the measured object is a
    heavy-tailed distribution (Kirby's GI mean 8.0 × 10⁵ against Atmar 2008's
    median 4.1 × 10⁴ for the same genogroup, 20×), so the repair is a
    distribution plus a corrected episode count, not a swapped point value, and
    it must go through `model-parameter-provenance` with the goldens moved
    deliberately. **Repaired in Wave 2 as a reparameterisation, not a value
    swap** — see §1: the pathway is now driven by the measured per-subject
    cumulative shed, drawn log-uniform once per illness, with titre retired as
    an input and the episode count corrected to 1–7. Three inputs collapse to
    one, so the item is closed as a degrees-of-freedom reduction rather than as
    a re-valued titre.
14. **Resolved: the infectious period was incorrectly tied to illness duration,
    and two thirds of the authored shedding curve was never emitted.** Measured,
    not argued:
    `telemetry_buffer/observation_model/shedding_clock_check.py` drives the real
    progression seam. The tranche 7 baseline was a norovirus host reaching only
    curve indices
    **0–2 of the authored 15**, clearing on day 3–6 (median 4), with
    **30.9% symptomatic and 75.0% asymptomatic integral emitted** — equivalently,
    69.1% and 25.0% unreachable. After tranche 8, the host reaches indices
    **0–14**, clears on day 15–18 (median 16), and emits **100.0%** of both
    integrals. The COVID control is unchanged: indices **0–6**, last shedding
    day median **12** (range 8–22), and **99.8%** of both integrals.
    The repair separates `recovery_day` as illness duration from
    `shedding_duration_days` as infectious/shedding duration. Illness and its
    emesis records clear at onset + 3 days, while infection, hand load and
    faecal shedding remain active through onset + 15 days. Atmar 2008 measures
    both quantities in the same subjects: symptoms 1–2 days, faecal shedding
    median **28 days** (13–56); Kirby 2014 finds shedding up to three weeks past
    symptom resolution in both genogroups; Cheng 2021 sees GII shedding cease
    around day 15. The shipped value is **15**, screen interval **[12, 30]**,
    Grade B, not fitted to any scored anchor. The legacy
    no-per-pathogen-record path in `engines/infection_dynamics_bridge.py` still
    uses `ONSET_DAY + RECOVERY_DAY` as a one-clock fallback; that known
    limitation is unchanged. See
    [`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md).

15. **Resolved: immunocompromise acted on acquisition, the one quantity nothing
    measures, and not on duration, which is measured directly.** #45 deleted
    `immunocompromised_multiplier` = 2.0 from the tree — no source measures the
    relative risk of *acquiring* norovirus while immunocompromised, and Green
    2014 states the persistence mechanisms are unknown — and put the measured
    quantities where they were measured, as pathogen-profile keys on
    `norwalk_gi` only: `chronic_shedder_fraction` **0.228** (van Beek 2017,
    *Clin Microbiol Infect* 23(4):265 — 23 of 101 infected solid-organ
    recipients) and `chronic_shedding_duration_days` with median **218 days**,
    range **32–1,164** and a declared σ_log of **1.09**. The σ is a
    distributional assumption of ours, not van Beek's: treating the reported
    range as an approximate 90% interval, ln(1164/218) = 1.674 and
    ln(218/32) = 1.919, mean 1.797, ÷1.645 → 1.09. Davis 2020 confirms
    *infectious* virus (HIE) rather than RNA alone in 20 chronic paediatric
    cases (37 to >418 days), and van Beek 2017 (*J Infect Dis* 216(9):1132)
    supports at mean 352 days (76–716). The fraction is conditional on being
    both immunocompromised and infected; the duration is drawn once per host per
    profile at initialization on a derived RNG stream, truncated to
    [32, 1164], and preferred over the profile's `shedding_duration_days`
    through the infection record by the tranche 8 clearance seam, so a chronic
    host's illness still clears at onset + `recovery_day` while it keeps
    shedding past any voyage length. Deliberately **not** done here: no chronic
    *magnitude* multiplier (Chaimongkol 2024's 10⁴–10¹¹ copies/g is 7 logs wide
    and already spanned by the `shedding_variance_log10` per-host draw, with no
    point value to adopt), no severity multiplier (reported but unquantified),
    and no boarding-prevalence importation channel — that is the
    quantitatively interesting half, and no chronic-shedder point prevalence is
    licensed yet
    ([`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md)
    §6). **This move is downward on every arm**: 5% of hosts lose a 2×
    susceptibility multiplier, and the chronic duration only lengthens shedding
    in the small immunocompromised-and-infected subset.

16. **`AERO-NEAR-01`: the short-range inhalation route has no sub-room unit.**
    `_pathway_droplet` divides every shedder's aerosol emission by the whole
    zone's declared `volume_m3` and doses every occupant identically, so a
    cabin mate breathes the corridor's 450–600 m³ rather than a cabin's
    ~20–30 m³ and a table party the dining room's 1,050 m³. `BERTH-01` gave
    the cabin its contact unit and fomite pool but not its air; `DINE-PARTY-01`
    gave the table its contact pool but not its air. For norovirus the route
    is fed only by emesis episodes, so the exposure that matters is whoever
    shares air with the vomiting host — the table (Marks 2000's
    distance-from-table gradient) or the cabin — and whether it carries
    material dose is a measurement to make; for the SARS-CoV-2 arm the
    restaurant record is a table/adjacent-table record that a well-mixed room
    cannot produce. The requirement is filed pathogen-general, with the
    seating declarations (`meal_seatings`, occupancy bound,
    `dining_table_size`, table adjacency) as operator levers:
    [`../near_field_air_spec.md`](../near_field_air_spec.md).
    Off by default and bit-identical when off; sourcing precedes any value; no
    constant here is chosen against a scored quantity.

    **Sourced, [tranche 36](../literature/consensus_tranche_36_near_field_air.md)**
    (Consensus exhausted for the period; retrieved by the approved open-full-text
    fallback). The structure is licensed and the magnitude is not. Licensed: the
    two-compartment near/far form, time-dependent (a breath tracer at a seated
    0.76 m runs **~36–44%** above other distances in the first 20 min and only
    **~18%** above the volume average by 60 min in a 27 m³ chamber at ~3 ACH,
    Parhizkar 2022); **two rings and no third** at a meal, bounded by Li 2021's
    Guangzhou restaurant — **31.25%** attack rate at the immediate neighbouring
    tables against **0%** remote, **45.45%** inside the recirculating
    air-conditioning zone against **0%** outside, with per-table exposure ratios
    (index = 1) of **0.76–1.04** same air stream, **0.40–0.47** same HVAC zone,
    **0.04–0.23** remote — those ratios being **CFD predictions in a room at
    0.9 L/s/person**, an envelope for the ordering test and not a dose; and the
    cabin as an air compartment, with four convergent infection estimates for
    sharing a sleeping compartment (**aOR 2.99**, Brown 2023; **≈×4.5**,
    Sun 2023; **RR 3.0** / **aOR 3.27** in the cruise cohorts of tranche 35)
    reserved as the **post-repair check**, since three routes already share the
    cabin and adopting ×3 as an aerosol multiplier would double-count them.
    **∅ null on search:** the near-field effective volume / exchange rate for a
    table or a cabin (nobody measures it — it ships as declared geometry plus a
    swept axis), and any influenza bedroom-sharing magnitude. **Null that
    narrows the norovirus arm, and is a finding:** the record supports no
    continuous respiratory norovirus emission — airborne material is
    emesis-conditioned (Alsved 2020: 21/86 samples, **OR 8.1** within 3 h of
    vomiting, 5–215 copies/m³) — so the norovirus near-field unit is whoever
    shares air with a vomiting host, and the out-of-sample check for this change
    is Marks 2000's attack rate by table around one vomiting diner,
    **91 / 71 / 56 / 50 / 40 / 25%** (trend P ≈ 0.0007). Two channels the 2024
    review lists as unresolved remain **absent and unlicensed**: toilet-flush
    aerosol (which would attach to the cabin toilet `BERTH-01` already
    compartmented) and diarrhoea-associated aerosolisation.

    **Implemented, off by default, and a null for this arm by construction.**
    `transmission.near_field_air` landed (§1 of this file; the spec's §10 is
    what shipped): the cabin and the table are near-field units, adjacent
    tables are the second ring, geometry is declared and the retained fraction
    is a swept axis with no adopted value. It admits only *continuously*
    emitting arms, so `norwalk_gi` — `emesis_conditioned` on the strength of
    the null above — takes no near field, and no norovirus figure in this file
    moves. **What remains outstanding for this arm is the emesis pool's own
    near field**: the episodic term over whoever shares air with a vomiting
    host, with Marks 2000's by-table gradient as its out-of-sample check. Until
    that lands, the norovirus inhalation route is still zone-well-mixed.

17. **`CONTACT-ARCH-01`: implemented, off by default, first campaign read;
    the interval box is refused above its low corner by its own §6 check.**
    The activity-derived contact generator (§1) is a design arm of the
    bounded gate (`--activity-contacts`, one complete eight-rate scalar
    declaration; absent is the uniform control on its old RNG path; Batch
    parameter `activity_contacts`, `off` for the control —
    `contact_architecture_spec.md` §4a). Done: (a) the arm; (b) the matched
    expedition campaign (image v19, 4 arms × 1,536 voyages, uniform 13.4 as
    paired control, role splits 1 by construction, tranche-37 interval lows /
    midpoints / highs), read in `contact_architecture_spec.md` §8; (c) the §6
    checks, §8a. Finite-sample findings: the control is bit-identical to the
    φ=0 arm of `CONTACT-SCALE-01` in 1,536/1,536; the low corner is a null on
    passengers (−0.13 pp, se 0.10) and +0.17 pp (se 0.07) on crew; the
    midpoint and high corners raise **both** roles (pax +1.44 / +2.21 pp, crew
    +1.08 / +1.52 pp), so A5 falls 2.34 → 2.02 (away from 4.3, as tranche 37
    predicted) and postings rise 14.4% → 17.8% against 0.6–1.6%. The §6
    per-role totals are 13.7/20.0 (low), 36.7/42.0 (mid), 56.8/62.0 (high)
    passenger/crew per day: the high corner and the midpoint's crew are
    outside the pre-registered 5–40 band, i.e. a **declaration error** —
    per-hour rates measured over short dwells applied to every resolved hour
    without saturation — not a magnitude to lower until a total matches.
    Crew:passenger is 1.1–1.5 against Pung's 0.5 (reported, not adjusted; the
    expedition schedule puts crew ~4.5 h/day in `Dining` zones); night share
    8.0/11.9% against 5.9%; passenger dining share 28.6% against 71%. Two
    resolver consequences were recorded on this campaign, for a resolver change
    and not a rate change, and both are repaired by item 18: `Meal`-token hosts
    awaiting a sitting resolved to `other`; crew scheduled `Work` in a `Dining`
    zone off food-handler duty resolved as diners.
    Outstanding: (d) `CONTACT-ARCH-02`, a dwell-tracking saturating form, now
    the prerequisite for reading the upper corners of the box at all; (e) a
    per-role `dining_venue` mapping only after (d). No rate is adopted. Every
    readout from `BERTH-01` through `CONTACT-SCALE-01` is conditional on the
    uniform draw and stands as recorded; none is re-run by this item.

18. **`CONTACT-ARCH-01b`: the schedule token a reader gets is the one that
    placed the agent, and the two resolver consequences of item 17 are
    repaired. This one moves the shipped model.** Three changes, no rate,
    interval or kernel among them. (a) The engine records the token it placed
    an agent by (`KorkinAgent.current_activity`) beside `current_location`, and
    `TransmissionCore` reads that record instead of re-deriving the hour from
    its own epoch counter. Those counters differ: measured, the core's epoch
    runs exactly one behind the engine's (48/48 calls on a 48-epoch expedition
    point), so the reader was matching the *previous* hour's token to this
    hour's location. On a 168-epoch point that wrong token changed **46% of the
    fomite eating verdicts** (9,790 of 21,119 calls) and **25% of the true
    food-handler duty verdicts** (116 of 459), and both of those predicates are
    live in the default configuration — the hand-to-mouth eating channel
    (`FOOD-ARCH-01`) and the food-handler deposition and surface class
    (`FOOD-ROLE-01`). (b) Scheduled `Work` is now resolved before the room, so
    a crew member at work in a `Dining` zone off food-handler duty is
    `work_other`, not a diner. (c) A `Meal` token resolves as a meal wherever
    the host stands, so no meal falls to `other`; a host whose sitting is
    inactive carries the `Free` the seating rewrite gave it. On a representative
    expedition point the resolver now emits no `other` at all, and no
    off-duty-`Work`-as-diner. **Consequence for the record: the uniform control
    is no longer bit-identical to the stored arms, so every readout that depends
    on the eating check or the duty state — the `FOOD-*` items, `SURF-KO-01`,
    and the control arms of `CONTACT-SCALE-01` and item 17 — was computed with
    the off-by-one token and needs a matched reprise before its numbers are
    quoted against post-repair runs. Nothing was re-run to make a number come
    out; nothing is retuned here.**

19. **`CONTACT-ARCH-02`: a visit's contacts saturate with dwell, when a run
    declares so; the matched reprise is item 20.** Item 17 (d) is implemented, off
    unless declared, and reads `contact_architecture_spec.md` §3a. The engine
    counts, per agent, the consecutive epochs it has been placed by the same
    token in the same room (`KorkinAgent.dwell_epochs`; any change of token,
    room or override starts a visit at zero), and an optional
    `activity_contacts.saturation_hours` map declares a time-scale `tau` per
    activity: cumulative contacts over a visit of `t` hours are
    `rate * tau * (1 - exp(-t / tau))`, so the declared per-hour rate is the
    initial slope and `rate * tau` the plateau. An activity with no `tau`
    keeps the constant-rate CONTACT-ARCH-01 arithmetic and RNG exactly; absent
    or disabled `activity_contacts` keeps the uniform 13.4 control. Provenance:
    Pung licenses the *form* (F&B plateau after about an hour; sports still
    rising at two hours) and no magnitude; `tau` is a declared swept axis with
    a `(0, 24]` h refusal band, and the spec forbids choosing it by the §6
    total, Pung's 20/10, A5 or a posting rate. Consequence for the record: the
    item 17 readout stands as a constant-rate result and is not reinterpreted;
    the upper-corner declaration error it recorded is now *readable* under a
    declared `tau` sweep, which is the matched reprise item 18 already
    requires. No rate, `tau` or kernel adopted.

20. **The matched reprise under the resolver repair and dwell saturation:
    saturation returns the upper corners to the control, the ordering of item
    17 reproduces, no arm nears an anchor, and no `tau` or rate is adopted.**
    Nine expedition arms on image `bounded-design-v20` (job definition rev 20,
    built from the item 18 tree), each 256 Sobol' points × 6 seeds over the
    13-factor `expedition_sensitivity` box (design seed 37, seed base 500),
    1,536 voyages per arm, 16/16 shards, no failed child: the uniform control,
    the tranche-37 lows / midpoints / highs unsaturated, and a declared `tau`
    sweep on the two upper corners (midpoint × {1, 2} h; high × {0.5, 1, 2} h;
    the same `tau` on all eight activities). Full tables in
    `contact_architecture_spec.md` §9–9a. Finite-sample over that design only.
    (a) **The item 18 repair moved the control within error**: against the
    item 17 (v19) control on the same points and seeds, Δ pax +0.05 pp (se
    0.08), Δ crew −0.00 pp (se 0.05), 36 off / 35 on, p = 1.0, 804/1,536
    bit-identical — half the voyages changed and the aggregate did not, so the
    item 18 reprise requirement for the `FOOD-*`, `SURF-KO-01` and
    `CONTACT-SCALE-01` readouts is discharged for the expedition control
    aggregate and remains open for each of those arms individually.
    (b) **Unsaturated, item 17's ordering reproduces**: pax 6.26 → 6.54 →
    7.83 → 8.57%, crew 2.65 → 2.95 → 3.81 → 4.25%; A5 2.37 → 2.02, away from
    4.3; postings 14.3% → 18.6% against 0.6–1.6%. The low corner is now a small
    positive on both roles (+0.28 / +0.31 pp, se 0.09 / 0.08) rather than a
    null, attributable to the repair moving waiting diners from `other` into
    `leisure`. (c) **Saturation lowers every upper corner, monotonically in
    `tau`**: high → τ = 0.5 / 1 / 2 h is −2.75 / −2.04 / −1.31 pp pax and
    −1.57 / −1.09 / −0.67 pp crew, all p < 10⁻⁴; midpoint → τ = 1 / 2 h is
    −1.84 / −1.26 pp pax and −1.00 / −0.72 pp crew. At τ ≤ 1 h both corners
    sit within ~0.5 pp of the uniform control on both roles. (d) **§6 checks
    after the repair**: crew:passenger 0.61–0.65 on every arm (was 1.1–1.5
    inverted in item 17), on Pung's side of unity; unsaturated high (63 / 41
    per day) and the midpoint's passengers (42) remain declaration errors
    outside the 5–40 band, the low corner (21 / 13) and every saturated arm
    (15–35 / 10–23) lie inside it; passenger dining share 48–61% saturated
    against 34–40% unsaturated and Pung's 71%. (e) **Reported, not tuned**: a
    single `tau` saturates a ten-hour `work_service` shift like a one-hour
    meal (0.7–2.2 on-duty contacts/day under the sweep), which is the wrong
    shape for a role whose partners turn over; the map allows `work_service`
    its own `tau` or none, and no arm here declared one. That is an open
    declaration question, not a magnitude. **Consequence for the record: A5
    lies in 2.02–2.37 and postings in 13.8–18.6% across all nine arms; no
    activity rate, `tau` or kernel is adopted, and no arm was chosen or read
    for its distance from Pung's 20/10, A5, VSP or a posting rate.** Every dose
    figure remains void pending refit.

21. **The retained arrays re-read within a dose regime: the contact arms were
    diluted, not null; A5 is deficient in every regime; and the posting anchor
    is unreachable by any reduction in transmission.** Item 00 closed with a
    precondition — stratify the readout by `adj` or sweep at a declared scale.
    The first half needs no new voyages: each retained point carries its own
    `adj`, so the four expedition campaigns (`SURF-KO-01`, `CONTACT-SCALE-01`,
    `CONTACT-ARCH-01`, `CONTACT-ARCH-02`, fifteen arms) were re-cut at item
    00's switch into live (`adj` < 5.5, 19 points), transition (5.5–6.5, 13)
    and import-only (≥ 6.5, 224) strata and the paired contrasts re-read
    inside each. Readout `telemetry_buffer/observation_model/`
    `adj_stratified_readout.py`; tables in `adj_stratified_readout.md`.
    Finite-sample, and a stratum is a seventh of the design, so every
    stratified bound is ~8× wider than the marginal one it replaces.
    (a) **Item 00's second consequence is corrected.** A5 was recorded there as
    a mixture of an import-only 1.81 and an explosive-corner 2.2. On the
    reported channel the anchor scores, the ratio is flat across all three
    regimes — 2.56 / 2.75 / 2.61 against ≈ 3.5 — so the crew deficit is
    reproduced identically on a dead ship, a transitional ship and a burning
    one. It is a missing-structure result, not a resolution artefact, and
    resolving the dose scale will not produce it.
    (b) **The large contact arms were diluted by roughly the live fraction of
    the box.** `CONTACT-ARCH-01` high reads +15.19 ± 0.70 pp pax (live) and
    +12.95 ± 0.89 (transition) against +2.21 marginal; the low corner is
    −2.56 ± 0.79 (live) against −0.13 ± 0.10 marginal, i.e. signed and
    negative where the marginal readout called it a null. Dwell saturation is
    likewise a signed mechanism rather than a return to the control: against
    the control, `high` at τ = 0.5 h is −4.65 ± 0.75 pp pax in the live
    stratum, overshooting the uniform rate rather than restoring it. Item 17's
    and item 20's *marginal* magnitudes therefore understate these arms by
    about 8×; their orderings stand.
    (c) **The small arms stay small, and become bounds.** `SURF-KO-01`
    +0.12 ± 0.49 pp (live), −1.46 ± 0.69 (transition); the φ arms within
    ±2.5 pp, only φ = −1 signed in both strata and in the direction of *less*
    infection. Item 00 withdrew these as uninterpretable; they are reinstated
    as bounds inside a transmitting regime, not as nulls over the box.
    (d) **The posting anchor is out of reach from below.** The import-only
    stratum posts 4.5% of voyages against A9's 0.42–0.56% with essentially no
    onboard transmission, and splitting it by the swept boarding prevalence
    gives 2.38 / 4.46 / 3.27 / 7.74% by quartile — the lowest sourced quartile
    is still above the band. No transmission-side change of any size reaches
    A9. This is `#467`'s posting floor, measured on the stratified arrays.
    Two corrections to this sub-item, both in item 22: the binding term is
    **not** the boarding interval or the observation model, and the band is
    0.42–0.56% (`a9_targets("pre")["fleet"]`, i.e. 4.187–5.583 per 1,000
    eligible voyages), not the 0.6–1.6% quoted here and in items 19 and 20.
    (e) **The import-only stratum is not transmission-free**, and stratifying
    by `adj` cannot test a fomite arm. Passenger infection attack rate exceeds
    passenger boarding prevalence in every quartile (3.00% against 2.69%;
    4.61% against 3.81%). That residue is the hand/surface/food chain, which
    `adj` does not scale at all (item 00a, `fomite_pool_denominator_`
    `reconciliation.md`), so for a fomite-side arm the strata differ only in
    the routes the arm does not touch. **Nothing is adopted and no stratum is
    declared**: the transmitting corner is where arithmetic permits
    transmission, not where the ship has been shown to sit, and standing there
    because the anchors improve would fit `adj` to an anchor indirectly. The
    interval stays [4, 24] pending the refit.

22. **A9's floor is the hand route's own release normaliser, not an import,
    an ascertainment rule or the boarding interval — and the band A9 has been
    scored against in the last three items was wrong.** Item 21(d) attributed
    the 4.5% posting floor to boarding prevalence and the observation model.
    Splitting the same retained rows by dose band (`floor_probe` in
    `adj_stratified_readout.py`; tables in `adj_stratified_readout.md` §3)
    refutes both attributions.
    (a) **The cut at `adj` ≥ 6.5 was not an import-only stratum.** Posting
    falls 20.5 → 7.7 → 1.8% across 6.5–7.5, 7.5–8.5 and 8.5–10, so item 21's
    top stratum averaged a still-transmitting decade into the floor. The floor
    proper is `adj` ≥ 10 (n = 1,074), where a host's profiled emission is
    below 10⁻⁶ of one copy per epoch.
    (b) **That band still transmits.** 696 of 1,074 voyages took off, mean
    passenger infection attack rate 3.40% against a mean boarding prevalence
    of 3.25%, 35 voyages (3.3%) exceeded 8% passenger infection attack rate,
    and 2.51% posted on the passenger channel — A9's own numerator (item 11) —
    against 0.42–0.56%. Crew-only postings are 15% of the or-rule total, so
    the crew channel is not the excess either.
    (c) **What separates those 35 voyages is one-sided and it is the hand
    chain.** Relative to their band: `food_ingestion_fraction_per_day` 1.53×,
    `hand_to_surface_drying_multiplier` 1.28×,
    `secretor_negative_relative_susceptibility` 1.17×,
    `food_hand_contacts_per_day` 1.12×, passenger boarding prevalence 1.07×,
    `adj` 1.00×. Descriptive only — a space-filling box and 35 rows — and no
    factor here is adopted, narrowed or fitted.
    (d) **The mechanism is a second, unswept release normaliser.**
    `engines/infection_dynamics_bridge.py` reads `HAND_LOAD_LOG10_GEC` = 3.86
    (Liu 2013 hand rinses, Grade B, origin Ab) against
    `HAND_LOAD_REFERENCE_PEAK_LOG10` = 11.0, so the hand route carries an
    implicit **−7.14 log10 g of stool per hand** — a Class X convention, as
    its own comment declares, that no study has measured. `adj` never touches
    it (item 00a). Every voyage therefore keeps one transmitting channel at an
    `adj`-equivalent of 7.14, at the top of item 00's 6–7 switch, whatever the
    design does to the profiled channel; every arm run since BERTH-01 swept
    the dead channel and held the live one fixed at an unsourced value.
    (e) **Correction to the scored band.** A9's fleet target is 4.187–5.583
    postings per 1,000 eligible voyages — 0.42–0.56%, as
    `admissible_region.py` and items 11–13 have it. Items 19, 20 and 21(d)
    quote 0.6–1.6%, which is in no source and no code path; the campaign
    readouts under it understate the over-posting (item 21(d) is 8–10× over,
    not 3–7×). The orderings and contrasts in those items are unaffected.
    (f) **Open, and not closed by this item.** The bridge is not sourced here
    and is not moved here: what is required is the mass of faecal material on
    a contaminated hand, read independently of A9, so the hand and
    environmental channels sit on one measured scale. Sourcing it by which
    value lowers the posting rate is forbidden by `AGENTS.md` and would
    destroy the only test available afterwards.

23. **The hand bridge is a literature null, and the indicator arithmetic that
    stands in for it puts the shipped convention at the bottom of its band —
    so the A9 floor may not be read as "the constant is too high".**
    [Tranche 39](../literature/consensus_tranche_39_hand_release_bridge.md)
    answers item 22(f) as far as the record allows. Nothing is adopted,
    narrowed or moved.
    (a) **The direct quantity does not exist.** No study weighs faecal
    material on a hand; none measures stool titre and hand load in the same
    subjects (tranche 26, unchanged). The closest published quantity is
    derived, not measured: Mattioli 2015 (*Environ Sci Technol*) models
    **0.93 mg of faeces ingested per day** by hand-to-mouth in Tanzanian
    children under five, an integrated daily dose over many contacts whose own
    indicator→mass conversion factor is `?nr`.
    (b) **The indicator bridge, composed from independently retrieved halves.**
    Numerator: E. coli **2.1–2.2 log10 CFU per two hands** on mothers'
    hands (Mattioli 2015, *Am J Trop Med Hyg*, Results table), with
    2.25–1.55 × 10⁵ CFU/pair across SaniPath's 287 rinses and > 2 log10
    CFU/pair in EXCAM. Denominator: total E. coli **undetectable to 8.75 log10
    CFU/g faeces** in 41 healthy adults (McOrist 2005) and **6.86 ± 1.56
    log10 CFU/g** in infants (Islam 2019). The quotient is
    **10⁻⁶·⁹ … 10⁻⁴·¹ g of stool per hand** for a *routine* contaminated hand
    in a heavily contaminated household setting.
    (c) **The shipped convention sits at or below the bottom of that band.**
    `10^(3.86 − 11.0)` = 10⁻⁷·¹⁴ g/hand. It is therefore **not** shown to be
    too high, and item 22(d) must not be read as claiming it is: an
    independently sourced replacement drawn from this envelope would *raise*
    the hand load and *raise* the posting floor. The envelope and the anchor
    point in opposite directions, and `AGENTS.md` forbids resolving that by
    following the anchor.
    (d) **It is an envelope, not a measurement.** Two stacked surrogates
    (E. coli for norovirus, culturable CFU for genome copies); E. coli is not
    conserved on skin; the denominator is left-censored at *undetectable*; the
    setting is low/lower-middle-income households, where Cantrell 2022 puts
    hand E. coli prevalence at 49% against **6% [1–12%]** in upper-middle/high
    -income settings — the cruise analogue is mostly non-detects; and hand
    rinse recovery efficiency is unmeasured, so every numerator is a lower
    bound.
    (e) **The event arm is unconvertible.** Oie 2021's **39,499 ± 77,768
    CFU/glove** after defecation is the only retrieved measurement at the
    event the engine actually models (`_replenish_hand` re-attains the target
    at a stool event), but it counts total culturable microbes and the
    matching per-gram denominator is **`?nr`**. Dividing it by an E. coli
    per-gram figure would be a unit error and is not done. As an ordering only
    it puts a post-defecation hand 2–3 logs above the routine band.
    (f) **Still open.** The row closes on one of: norovirus copies per hand
    *and* stool titre in the same subjects; a gravimetric or tracer study of
    faecal residue transferred at defecation; or Oie's per-gram denominator.
    None was found. `HAND_LOAD_LOG10_GEC`, `HAND_LOAD_REFERENCE_PEAK_LOG10`,
    `environmental_faecal_release_log10_g_per_epoch`, the dose-response rows
    and `POSTING_THRESHOLD` are all unchanged by this item.
24. **The hand load is intermittent, its reference pair is cross-population,
    and the defecation trigger has the wrong sign — three corrections from one
    full text, none of them adopted.**
    [Tranche 40](../literature/consensus_tranche_40_hand_event_amplitude.md)
    opened Liu 2013 (`10.1128/AEM.02576-13`) at PMC3837815 after three
    Consensus phrasings returned the abstract only. Items 22–23 and the
    tranche 26/39 rows are corrected as follows; **no constant moves**.
    (a) **Item 23(a) is partly withdrawn, and tranche 26's null 2 with it.**
    "No study measures stool titre and hand load in the same subjects" was a
    **retrieval failure, not a null**. Liu's Table 3 pairs each subject's
    *maximum* stool titre — **8.3, 8.1, 7.4, 7.5, 7.4, 8.2 log10/g** — with
    that subject's *mean positive* hand load. Max-versus-mean and not
    simultaneous, so it bounds rather than measures.
    (b) **The shipped pair is cross-population.** The engine reads Liu's
    3.86 against a curve peak of 11.0 taken from a different population.
    Against Liu's own subjects the same arithmetic gives
    **−3.5 … −4.4 log10 g/hand**, 2.7–3.6 logs above the shipped `−7.14` and
    at the **top** of item 23(b)'s independent indicator envelope. Two
    independent routes now bracket the bridge from above. Neither is adopted,
    and neither licenses raising the load on its own — see (c), which acts the
    other way.
    (c) **3.86 is a mean over a quarter.** Only **18/71 (25.4%)** of rinses
    from symptomatic, stool-positive hosts were positive at a limit of
    **2.15 log10 GEC per rinse**; **two of six** infected subjects never had a
    positive hand; per-subject positivity ran 0% to 54.5%, per-subject means
    3.30–4.45. `_replenish_hand`'s **non-event mode — which holds every
    shedding host at the ceiling every epoch — is refuted** for this pathogen
    in this setting, independently of any magnitude.
    (d) **The event mode's trigger has the wrong sign.** Liu measured the
    contrast the engine asserts: rinses taken **immediately after bathroom
    use** were *lower* and *less often positive* (**11/89 = 12.4%**, mean
    **2.30 log10**) than rinses at routine vital-sign checks (**6/16 =
    37.5%**, mean **3.32 log10**), **P < 0.05** on both. The engine returns
    the hand to the ceiling *at* a stool event. Why the field reverses is
    `?nr` — the paper records sample context, not behaviour.
    (e) **What the dispersion evidence licenses.** Ram 2011 (serial rinses,
    same mothers hours apart): mean absolute difference **3.5 log10, SD 1.4**,
    and **no correlation** between random and critical-time counts
    (R = 0.13). Pickering 2011: activity-conditioned geometric-mean increments
    from **50 to 6,310 CFU per two hands**, bathing negative. Oie: SD ≈ 2× the
    mean. Together these support **intermittency plus lognormal-scale
    dispersion with measured suppression terms**; a **fitted power-law or
    Pareto tail index is `?nr-term`** — no retrieved source reports one, and
    adopting one would be a declaration.
    (f) **Rare-release mode.** Chalmers 2021 puts the probability that one
    bather contaminates a pool at **1 in 10³ to worse than 1 in 10⁴** per
    person-visit; Gerba 2000 estimates **0.14 g** of faecal material per
    bather from indicator wash-off; Petterson 2020's **0.06 / 0.6 / 6 g**
    triangular is another model's declared reference distribution and is
    **not** evidence. Wrong setting for all three.
    (g) **Nothing changed.** `HAND_LOAD_LOG10_GEC`,
    `HAND_LOAD_REFERENCE_PEAK_LOG10`, `stool_events_per_day`,
    `environmental_faecal_release_log10_g_per_epoch`, the dose-response rows
    and `POSTING_THRESHOLD` are untouched. Corrections (b) and (c) act in
    opposite directions on the time-averaged hand load and must be resolved
    together; (d) is a structural result and may not be retimed by what moves
    A9.

25. **The shipped hand process measured against the measurement that sources
    it: the baseline arm passes, the diarrhoeal arm is 2–3× over-occupied, and
    every arm is 0.6–0.8 log10 short on amplitude — and the repair raises the
    load.** Liu 2013 reports two stationary moments of exactly the process
    `_replenish_hand` implements, and neither had ever been computed for the
    engine.
    [`hand_occupancy_readout.py`](../../telemetry_buffer/observation_model/hand_occupancy_readout.py)
    reproduces the recurrence on the shipped values — ceiling **3.86**,
    `stool_events_per_day` **1.0 / 5.63**, `hand_inactivation_rate_per_hour`
    **[0.61, 1.7]**, hygiene at its shipped **0.0**/h — and reports occupancy
    above Liu's **2.15 log10 GEC/rinse** limit and the mean over those epochs.
    No anchor is read anywhere in it.
    (a) **The baseline arm passes an out-of-sample check, unaimed.** Occupancy
    **0.116 (k = 1.7) to 0.249 (k = 0.61)** brackets Liu's **0.254**. That is
    `λ/k` falling out of tranche 32's event rate and an independently sourced
    die-off, and it is the first such check the hand route has passed.
    (b) **The diarrhoeal arm fails high, and it is the arm that carries the
    dose.** Occupancy **0.503–0.805**, i.e. **1.98–3.17×** Liu, whose subjects
    were themselves symptomatic challenge cases.
    (c) **Every arm fails low on amplitude.** `E[log10 L | L > LOD]` is
    **3.11–3.30** against Liu's **3.86**, a shortfall of **0.56–0.75 log10**.
    This is item 24(c) made quantitative: a load decaying from the conditional
    mean spends its supra-limit time below it, so a conditional mean used as a
    ceiling cannot reproduce itself.
    (d) **The two failures have opposite signs and the joint solve is
    infeasible.** Searching (per-event peak × post-toilet wash probability)
    over wash efficacies **1.06** and **1.89 log10** and `σ ∈ {0, 0.5, 1.0}`
    returns **no cell** reproducing both moments: the best reach the
    conditional mean only at occupancies **0.29–0.86**, with a per-event peak
    of **4.0–6.2 log10** in place of 3.86 and a time-averaged hand mass
    **+0.8 to +1.7 log10** above shipped. Tranche 32's diarrhoeal event rate,
    the inactivation interval and Liu's two moments are **jointly infeasible
    under decay-plus-reset with the sourced removals** — a structural
    refutation, not a parameter error.
    (e) **The direction is against the anchor, and is recorded before any
    implementation.** The amplitude repair raises the hand mass by 0.8–1.7
    log10; the occupancy repair lowers it by at most
    `log10(5.63/1.5) ≈ 0.57`. The residual is positive, all three hand
    consumers are linear in `L`, and A9 is already **4.5–6× above** target, so
    a hand route reconciled with Liu is expected to make A9 **worse**. Per the
    provenance rule that is a result; it may not be used to prefer a different
    structure. (f) **Also measured, as a negative control:** replacing
    `max(decayed, target)` with additive arrivals moves the mass by
    **< 0.1 log10** at these rates, so the structural idiom in
    [HAND-EVENT-01](../proposals/hand_event_release_spec.md) §3.1 is not what
    moves this channel. (g) **Nothing changed.** No constant, interval,
    profile field or default moved; the readout imports no engine module.

## 5. Held fixed by assumption

Live Grade C liabilities. Any of these could move the reported rate; the system
is over-determined only *given* them. Full list in §10 of the history document.

- Route weights (contact 0.35, fomite 0.30, food 0.20, droplet 0.10, HVAC 0.05)
  — assumed, not traced to a source. **The largest single unsourced input.**
- `shedding_duration_days` = **15 days**, screened over **[12, 30]**, Grade B
  (Atmar 2008, Kirby 2014, Cheng 2021). The shipped value is a declared
  operational point, not fitted to a scored anchor; the field keeps the
  illness duration (`recovery_day`) separate from the infectious/shedding
  duration.
- `HIGH_TOUCH_AREA_M2` — per-room high-touch area in m² has never been measured
  by anybody. Permanent Grade C; the gap is the field's, not ours.
- Fraction of emesis episodes occurring in the host's own cabin — swept, never
  asserted.
- `EMESIS_AEROSOL_FRACTION_RANGE` (7.2e-7 – 2.67e-4, Tung-Thompson surrogate)
  **has now been checked** against a measured airborne concentration: Alsved et
  al. 2019, *CID* — 5–215 copies/m³ beside 26 hospital norovirus patients,
  positivity associated with vomiting in the previous 3 h. The check is
  `scripts/alsved_airborne_check.py` and it **decides nothing about the value**:
  the interval's ceiling reaches 5.0–6.7 copies/m³ in a 900–1200 m³ zone, at the
  measurement's floor, and the 6.4-decade interval constrains
  fraction × total shed ÷ volume jointly — inverting the comparison admits
  receiving volumes across five decades. So there is no over-emission to
  correct, and the fraction remains an interval with no point selected;
  choosing it to match the measurement would be fitting. See
  [`../literature/consensus_tranche_4.md`](../literature/consensus_tranche_4.md)
  §1d and
  [tranche 28](../literature/consensus_tranche_28_airborne_norovirus_out_of_sample.md).
- Confinement attenuation factor 0.05.
- `immunocompromised_fraction` = 0.05, defaulted in the multi-pathogen config
  block rather than in a profile, is now **bounded by measurement**:
  **[0.02, 0.074]**, Grade B (Lopez-Gigosos 2020's 2.0% of 1,196 travel-clinic
  travellers; NHIS 2.7% in 2013 rising to 7.4% in 2022), a width that is era and
  population rather than uncertainty. The shipped 0.05 is unchanged and lies
  inside the interval, the sources sit at the definition, and a value outside
  the interval draws an advisory sanity-checker warning. The companion key
  `immunocompromised_multiplier` = 2.0 is **withdrawn and deleted from the
  tree** (#45): a config still setting it is warned about rather than silently
  ignored, and the measured quantities enter as duration on the profile — see
  §4 item 15.
  Remaining Grade C liability: `chronic_shedding_duration_days.sigma_log` =
  1.09 is our declared lognormal shape over van Beek's measured median and
  range, not a measured dispersion. See
  [`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md)
  §4–§5.
- The **seeded index case's acquisition dose** is a construction constant, in
  two different values: the legacy engine path seeds `10^(9.0 − 4.0)` = 1e5
  from the symptomatic curve's day-1 entry, and the pathogen-aware boarding,
  mid-cruise and shore paths hard-code `1e4`. `acquired_particles` is the
  argument of `illness_probability`, so these numbers set the index case's
  probability of ever presenting — 0.643 and 0.555 at this profile's η/γ,
  against 0.577 at its own beta-Poisson N50 — and neither tracks
  `environmental_faecal_release_log10_g_per_epoch`, so under the campaign's
  dose sweep every transmission-acquired dose rescales and the index case's
  does not. Grade C, no source, no comment at the definition. See
  [`../proposals/initiation_engine_spec.md`](../proposals/initiation_engine_spec.md)
  §1 and §3, which replaces it with an explicit config value or with no dose
  at all. **Both values are now removed from the boarding and the seed
  paths**, which closes that liability where initiation owns the host: a
  boarded host carries dose 0.0 and an explicitly seeded one carries the dose
  its config states, or 0.0 when it states none, and whether the host presents
  is set by the boarding state axis or by the seed rather than by a
  construction dose read through `illness_probability`. The two constants
  survive only on the legacy paths a run without an `initiation` block still
  takes, which is every run shipped today.
- Secretor-status non-susceptibility. Not a held-fixed 20% ceiling: the profile
  the campaign runs ships 0.0, no attack-rate ceiling is observed (0.013–0.326
  across the override arms), and §1 withdraws 0.2 as the correction target. The
  live liability is that the mechanism is a removed fraction at all, where the
  evidence is partial susceptibility.
- `airborne_half_life_hours` = 1.1 is cited to van Doremalen et al. 2020, which
  measured **SARS-CoV-2**, and is the identical value carried by the COVID
  profile. A search for a norovirus airborne decay measurement returned a null
  result (see
  [`../literature/parameter_sourcing_bundle.md`](../literature/parameter_sourcing_bundle.md)
  §2.3), so this is a cross-pathogen borrow presented as a citation, not a
  sourced value. Treat as Grade C until it is declared or bounded by deposition
  physics.
- The shipped rate, **0.124939 log10/day** (spelled `surface_decay_per_day` =
  0.25 until R1 migrated it), has no source. It implies 0.125 log10/day,
  slower than the MNV-1-on-stainless-steel surrogate measurement (≥0.29
  log10/day, Leblanc et al. 2019), and the gap inflates the fomite reservoir.
  No human-norovirus dry-surface infectivity decay measurement exists; any
  adopted interval is Grade B at best and must state its medium.
- The decay interval is now carried in the units it is measured in,
  **[0.067, 0.79] log10/day** on `surface_decay_log10_per_day`, recut in
  `../literature/consensus_tranche_5.md` §1 from five surrogate studies; the
  earlier [0.14, 0.84] is the identical interval converted through
  f = 1 − 10⁻ᵏ (0.067 ↔ 0.143, 0.79 ↔ 0.838). It is an order of magnitude wide in rate, and the
  shipped 0.25 lies inside it near the slow end — Edison's proposed
  [0.49, 0.84] is the top of the literature, not its span, and the fast-end
  citation does not check against the paper it names. Every Morris result in
  `bounded_screen_results.md` was produced on the old [0.10, 0.60] box and
  must be re-run before the admissible-region search. The re-run was launched
  and then killed part-way; the factor substitution in §1 invalidates that
  document again, independently.
- The former `surface_deposition_fraction` / `airborne_emission_fraction`
  continuous-shedding definition is deleted from the active norovirus profiles:
  shedding is measured in copies/g of stool or vomitus while airborne virus is
  measured in copies/m³ of room air, never in the same subjects. Norovirus now
  declares `airborne_emission_mode = emesis_conditioned` and
  `emesis_aerosol_fraction_range = [7.2e-7, 2.67e-4]`; `TransmissionCore` draws
  log-uniformly per emesis event and drains that mass into the zone airborne
  reservoir once. Tung-Thompson 2015's table is in percent
  (7.2e-5%–2.67e-2%), so the declared fractions are the two-decades-smaller
  conversion. The deleted 1e-4 fell inside the interval only by coincidence
  across incompatible denominators, not corroboration.
- Uniform `immune_ratio` across a resident crew and a weekly-turnover passenger
  cohort — an assumption that bears directly on A5. Tranche 34
  (`docs/literature/consensus_tranche_34_crew_immunity.md`) sourced the crew
  side: the crew deficit is measured (passenger:crew AR **4.3** pooled, **10.1**
  person-to-person, Mouchtouri 2024 Tables 2–3) and the cruise literature
  attributes it to **segregated crew sleeping, dining and boarding areas**, not
  to host biology. Crew-specific prior immunity, comorbidity effects on
  norovirus *susceptibility*, and a voyage-to-voyage carried immune state are
  all **∅ null**; the last is also a **structural gap** — the engine resets
  every agent to one role-blind `immune_fraction` at each voyage start, so a
  carried crew state has no field to live in. A role-stratified prior-immune
  share is at most a declared sensitivity axis; no value for it, and no move in
  `immune_fraction` or the susceptibility draw, may be read off A5 or A9.
- Crew presenteeism and mandatory occupational reporting: absent in both
  directions, and the regulated direction is now sourced. VSP's 2018 Operations
  Manual §4.4.1.1.1 **requires** isolation of a crew member meeting the AGE case
  definition — food employees until 48 h symptom-free with documented medical
  clearance before return to work, nonfood employees 24 h — where §4.4.2.1 only
  *advises* it of passengers. The model has no such rule: symptom-triggered
  removal exists only as SOP-008 gated at escalation status ALERT, which never
  fires in the quiet region, so a symptomatic crew member works the voyage under
  `crew_contact_multiplier` 2.0, `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR` 545.4
  and `FOOD_HANDLER_CONTACT_MULTIPLIER` 12.7. The exclusion's trigger and
  duration are stated by the regulation, so the structure carries no free
  magnitude; the **compliance share is ∅ null** for the maritime arm, and the
  land-based presenteeism bound (tranche 30 §1) is on the wrong denominator and
  the wrong regime. The rule is now **implemented as a declared operational
  arm** (`crew_duty_exclusion` in `crusher_labs/config.yaml`,
  `engines/crew_duty_exclusion.py`), `enabled: false` by default so every prior
  run and campaign keeps meaning what it meant. It fires from the first
  identified crew case rather than at ALERT, holds a food employee 48 h and
  other crew 24 h symptom-free through the existing quarantine machinery, and
  leaves passengers untouched. It introduces no epidemiological constant and no
  second ascertainment probability — it reuses `ever_reported_ids` — and
  `compliance_fraction` defaults to 1.0 as the *enforced upper bound on what
  the structure can remove*, not an estimate, the maritime share being ∅ null.
  Neither the rule nor a compliance value may be read off A9 — see
  `docs/literature/consensus_tranche_33_crew_duty_exclusion.md`. The same probe
  removed each crew exposure multiplier in turn at the quietest gate point and
  found **no** order-of-magnitude effect on either channel (36 seeds, weak
  power); no multiplier moved.
- `OUTBREAK_CLEANING_COVERAGE` 0.58 — no shipboard measurement exists. Carried
  over from a 34%→53% supervision-and-feedback effect in two hospitals
  (Murphy 2011) applied to Carling's 37%. Sweep it; never assert it.
- Log10 additivity of the two-step outbreak procedure (detergent preclean then
  hypochlorite, 1.29 + 3.0 = 4.29). The field reports two-step efficacy that
  way; nobody measured the composition.
- Uniform routine cleaning remains the shipped default. One pass per day is the
  denominator of Carling's "cleaned on a daily basis", not a measured
  per-zone-class schedule. The optional per-zone-class schedule is swept inside
  sourced bounds; no sweep cell may be adopted as a parameter value.
- Newly deposited surface mass is split into cleaned and missed shares in
  proportion to coverage, i.e. shedders touch reached and missed objects alike.
  Untested; if soiling concentrates on the objects housekeeping skips, the
  missed reservoir is larger than modelled.

## 6. Maintaining this file

Update it in the same PR as any change that invalidates something here. The
failure mode this file exists to prevent is a future session reading a stale
dose figure from a doc and building on it in good faith — so a ledger that is
quietly out of date is worse than no ledger. Date-stamp every measurement with
the commit it was taken at.
