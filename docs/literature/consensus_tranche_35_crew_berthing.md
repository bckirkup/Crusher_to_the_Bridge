# Tranche 35 — crew berth two or three to a cabin behind a shared toilet, not thirty-seven to a corridor, and the cabin is where the record puts the risk

**Register rows fed / supersession.** Feeds the berthing topology declared in
each cruise hull's `spatial_layout.json` (`cabin_size` on `PC_*` / `CC_*`
`Cabin_Corridor` zones) and the two undeclared corridor constants
`DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR` (0.15) and the density-spec
`Cabin_Corridor: 0.25` zone factor. It **supersedes nothing** and **withdraws
no measurement**. It moves no constant. It records, for each hull class, what
crew accommodation is documented to be, so the berthing repair the open ledger
carries as item 8 can be built against evidence rather than assumption.

**Status:** Evidence assembled and interpreted. Nothing implemented in this
tranche.

**Source discipline.** This tranche is documentary, not a Consensus retrieval.
The peer-reviewed rows (Wikswo 2011; Kordsmeyer 2022; Huttunen 2023; Crisp
2023) are read from full text and marked **Tr**. Regulatory text (MLC 2006) is
**Tr** from the convention. Trade and crew-account sources (CruiseMapper's
Icon-class crew stateroom sheet, operator recruitment notices, crew cabin tours
reported by trade press) are marked **Doc** — first-person or operator
documentation of how people are berthed, admissible as topology declarations,
not as constants. Nothing here is a rate.

**Scope:** the user's question after the FOOD-ROLE-01 reprise moved nothing —
whether the engine's picture of crew housing is right, given that shared
berthing is the exposure the passenger literature names and crew are
sometimes seen in single cabins.

**Result in one line.** Crew sleep **two to a cabin** as the modern norm, **two
to four** on older ships and for the most junior hotel ranks, **single** for
officers and 2.5-stripe-and-above staff — never more than four (MLC 2006
A3.1 caps passenger-ship non-officer rooms at four); passengers sleep two
(three or four with sofa-beds); cabin-sharing with a case **triples** an
individual's risk in the one passenger cohort and the one crew cohort that
measured it; and the engine mixes both roles across a **25–40 person corridor
ward** at night with the cabin inert, which is the wrong compartment for
everyone and wrong in the direction that over-infects crew.

---

## 1. What the regulation permits

Maritime Labour Convention 2006, Standard A3.1 ¶9 (**Tr**, ILO text as
transposed at lovdata.no and imorules.com):

- (d) a separate berth for each seafarer in all circumstances; (e) berth
  ≥ 198 × 80 cm;
- (f) single-berth rooms: floor ≥ 7 m² on ships ≥ 10,000 GT;
- (i) **on passenger ships**, rooms for seafarers *not* performing officers'
  duties: **7.5 m² for two, 11.5 m² for three, 14.5 m² for four** — four is
  the ceiling for a passenger ship; (j) more than four only on special-purpose
  ships;
- (a) individual rooms are the default on *non*-passenger ships; passenger
  ships are the carve-out under which shared rooms are lawful.

So the regulatory envelope for cruise crew is 1–4 per cabin, with the model's
declared `cabin_size: 3` inside it and the corridor ward of 37–40 far outside
it. Every ship in the observed VSP record sails under this or a flag
equivalent.

## 2. What is documented, by hull class

| class (model hull) | berths per crew cabin | bathroom | source, origin |
|---|---|---|---|
| **mega** (`mega_cruise_5000`) — Icon class | **2** in all 1,175 crew staterooms; 2,350 crew across a four-deck "Crew Neighborhood" (decks 1–4); fixed upper/lower berths, privacy curtains | en-suite per cabin; the newer *single* crew cabins share a "Jack-and-Jill" bathroom **between two cabins** | CruiseMapper Icon of the Seas crew-cabin sheet; RC Blog 2026; AOL/TheStreet 2025 (**Doc**) |
| **mega** — Oasis class (Utopia, 2024) | musicians in **single** cabins ~100 ft²; entry hotel ranks 2 | single cabins pair on a shared bathroom | Cruise Hive 2024-06-25 (**Doc**) |
| **classic** (`classic_cruise_1900`) — 1990s hulls, e.g. Fantasy class 70k GT / 920 crew | **2 to 4** per cabin, "9 × 9 ft" (~7.5 m²), "85% of crew below the waterline"; cooks, waiters, bar, laundry in the 3–4 berth rooms | one wet-bath per cabin, or shared with the neighbouring cabin on the oldest ships; communal facilities "down the hall" for some entry ranks | workingoncruiseships.com 2019; Remitly 2026; Cruise Hive 2024 (Fantasy-class shared bathrooms) (**Doc**) |
| **spirit** (`spirit_cruise_3000`) — 2000s hulls | no class-specific count found; general accounts (2 standard, 3–4 junior, officers single) apply | en-suite | Adventour Begins 2021; TRAVELLING STEWDIO 2017 ("single, double, triple or sometimes quad occupancy… most crew will have a shared cabin") (**Doc**) |
| **expedition** (`expedition_cruise_450`) — 100–200 pax, 100–150 crew | Lindblad steward posting: "you will bunk with **one or two** roommates"; expedition-staff assistant postings: "shared cabin"; MS *Roald Amundsen* (HX, 530 pax / ~160 crew): cabin-sharing was a measured exposure among crew | en-suite | Lindblad Expeditions recruitment (lever.co); allcruisejobs.com; Kordsmeyer 2022 (**Doc**, **Tr**) |
| all classes — officers and 2.5-stripe+ staff | **1**; larger, with porthole, decks 1–2 or near the bridge | en-suite | Adventour Begins 2021; Remitly 2026 (**Doc**) |

Two structural facts recur in every account and are absent from the engine:

1. **Roommates are drawn by department, gender and shift** ("two housekeepers
   working similar shifts", "from the same or a similar department", cabins
   "located near each other and close to their workplace" — restaurant and bar
   staff on deck 0 by the crew elevators). Crew berthing is *correlated with
   work zone*; the engine draws `home_zone` for crew uniformly over the `CC_*`
   corridors, independent of `work_zone`.
2. **The toilet is the shared compartment.** Every 2–4-berth cabin has one
   wet-bath; single cabins on Oasis/Icon share one between two. The engine has
   no cabin toilet — the faecal chain deposits into the corridor pool.

The "single small room" seen in crew videos is real and is the officer /
senior-staff / Icon-solo case — a minority of the complement, and even there
the bathroom is shared by two.

## 3. What the outbreak record says about the cabin

| finding | population | value | source |
|---|---|---|---|
| ill cabin-mate | passengers, GII.4 outbreak, n = 1,532 | **RR 3.0**, p < 0.01 (vs. witnessed vomiting at boarding RR 2.8) | Wikswo et al. 2011, *Clin Infect Dis* 52:1116, doi:10.1093/cid/cir144 (**Tr**) |
| infected cabin-mate | crew, SARS-CoV-2, MS *Roald Amundsen*, n = 114 (71% of crew) | **aOR 3.27** [0.97–11.07], p = 0.057; workplace clusters aOR 9.2 (mechanical), 6.1 (catering) | Kordsmeyer et al. 2022, *Int J Infect Dis* 118:10, doi:10.1016/j.ijid.2022.02.025 (**Tr**) |
| NoV GII on surfaces | Baltic ferry outbreak 2016, >230 cases | **crew cabin toilet 2/2 positive** (tap handle, seat, GII.2[P16]); crew galley 0/3; crew mess toilet 0/1 | Huttunen et al. 2023, SELL 3/2023 (Univ. Helsinki) (**Tr**) |
| crew-first, cruise-to-cruise chain | 410 cases over 5 voyages, 356 pax / 54 crew | index = food-and-beverage crew on a **crew-only** voyage 1 → crew-to-crew on voyage 2 → passengers on 3–5; ~70% of ill crew were passenger-facing | Crisp et al. 2023, *MMWR* 72(30):833 (**Tr**) |
| modelling precedent | 121-case NoV outbreak, Mediterranean, 7 d | force of infection carries an explicit **night-time cabin-sharing term** separate from ship-wide mixing | *J Travel Med* 2025, doi:10.1093/jtm/taaf059 (**Tr**) |

The same magnitude — about ×3 — appears for the cabin in a passenger norovirus
cohort and a crew SARS-CoV-2 cohort, which is the cabin as a *compartment*
speaking rather than either pathogen. The Baltic surface survey puts the
virus on the crew cabin toilet and not in the crew galley or crew mess, which
is the opposite of where the engine's crew fomite exposure sits (service
zones). Crisp 2023 is the carried-state gap of tranche 34 seen from the other
side: infection, not immunity, persisted in the crew across voyages.

## 4. What the engine does instead

- Berthing *is* segregated by role (`CC_*` vs `PC_*`) — that part is right.
- Within a corridor, `per_partner_contact` samples a susceptible's partners
  uniformly from **all occupants of the corridor** (25 passengers; 37–40
  crew), for the 8–9 sleep hours, scaled by the undeclared 0.25 zone factor;
  `cabin_mate_ids` is consulted **only** under quarantine confinement
  (`_cabin_pair_contact_factor`, `_cabin_mate_droplet_addback`).
- The fomite pool is per corridor: a corridor of 37 shares one surface pool
  where reality is 12–19 toilets.
- Crew corridors declare `cabin_size: 3` (the model default for `CC_*`) and a
  larger ward than the passenger corridors, so the *engine's* crew mix more
  at night than its passengers — the same sign as every other crew defect
  found so far, and opposite to the record's two-berth modern norm.
- Crew `home_zone` is independent of `work_zone`; the department clustering
  that the accounts describe (and that Kordsmeyer measured as the strongest
  cluster) does not exist.

## 5. What this licenses, and what it does not

**Licensed (topology declarations, no magnitude):**

- The night mixing unit is the **cabin**, not the corridor: partners at
  `Sleep` are cabin-mates; corridor encounters are a residual.
- Crew cabin size by class: **2** (mega/new-build), **2–4** (classic/older,
  junior hotel ranks at 3–4), **2–3** (expedition), **1** for an
  officer/senior fraction; passenger cabins 2, with a declared 3–4 minority.
  These are envelopes for the `cabin_size` declaration per hull, to be carried
  as ranges where the class evidence is a range.
- A **cabin toilet** as the finest fomite compartment, shared by one cabin (or
  two single cabins).
- Crew roommates and cabin location **correlated with department / work zone**.

**Not licensed:**

- Any value for the corridor residual (`DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR`
  0.15 and the 0.25 zone factor remain undeclared assumptions; this tranche
  found nothing that measures hallway contact).
- Reading the ×3 cabin-mate risk as a transmission constant — it is a
  *check* the repaired structure must reproduce, in the same class as A5, and
  must not be fitted.
- Any expectation of direction: the ledger's item 8 says building the cabin
  "would raise crew rates"; that was written for a 3-berth crew cabin against a
  2-berth passenger cabin and is not obviously true once corridor-ward mixing
  is removed for both roles. Measure it on AWS; do not assume it.

## 6. Open

- No class-specific crew-cabin count for 2000s mid-size hulls (spirit) beyond
  the general 2-standard / 3–4-junior pattern.
- Officer/senior single-cabin **fraction** of the complement is not sourced
  (rank structure is documented; its headcount share is not).
- Passenger 3–4-berth **share** by class is not sourced here (deck plans carry
  it; not retrieved).
