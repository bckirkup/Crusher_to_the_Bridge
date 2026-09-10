# Tranche 37 — a person's contacts are a property of where the schedule puts them and what they are doing there, not of the day; the cruise record measures passengers at twice the crew's count, and the night at one-twentieth of the day's

**Register rows fed / supersession.** Feeds `CONTACT-ARCH-01`
([`../contact_architecture_spec.md`](../contact_architecture_spec.md))
and the open ledger's §4 item 17. It **supersedes nothing** and **withdraws no
measurement**: `POLYMOD_CONTACTS_PER_DAY = 13.4` (Mossong 2008) stays in the
tree as the whole-day general-population **reference** and as the paired
control of every campaign that has run under it. It moves no constant and it
adopts none — every per-setting rate below ships as a declared interval on a
swept axis, and the per-role daily totals that the cruise sensor study measured
are the **out-of-sample check** on what the architecture produces, never an
input to it.

**Status:** Evidence assembled and interpreted. Nothing implemented in this
tranche.

**Source discipline.** Consensus full-text excerpts were used for the
hospital-ward rows (Vanhems, Jiang 2017a/b, Shirreff; origin marked). The two load-bearing papers —
Pung 2022 (cruise) and Duval 2018 (long-term care) — were read from the Europe
PMC `fullTextXML` (PMC9005731, PMC5786108) and Pung's Springer supplementary
PDF, under the open-full-text fallback of `docs/sourcing_protocol.md`. Mossong
2008 was re-read from its open full text for its location split. Origins: **R**
(Results prose), **T** (table), **F** (figure), **S** (supplement), **A**
(abstract only). Contact **definitions differ between every study below** and
are stated in each row; nothing here equates a ≥15 min proximity episode with a
diary conversation.

**Scope.** Four questions. (1) Is a day's contact count the same for everyone
aboard a cruise ship, or does it depend on role? (2) How do contacts accrue
within a setting — per hour, per visit, saturating? (3) How are contacts
distributed over the day and over settings, and in particular over the sleeping
hours the model currently gives a third of them to? (4) What do occupational
analogues measure for a working role against a resident one?

**Result in one line.** On the only cruise ships ever instrumented, passengers
made a median **20** distinct close contacts a day and crew **10** (Pung 2022,
Grade A for setting, attenuated by 50% capacity and work bubbles); contacts
**accrue per visit and saturate** — about **3** close contacts per food-and-
beverage visit of an hour or more, **2 → 4** in a sports venue from 30–60 min to
≥2 h — so a venue's contribution is set by how long the schedule keeps a person
there, not by the clock; **94.1%** of a hospital unit's contacts fall in the
daytime (Vanhems 2013), against the **37.5%** the uniform 13.4/24 draw places
in the model's nine sleeping hours; and where roles are not bubbled, the mobile
working roles make **1.3–2.2×** a resident's distinct daily contacts (Duval
2018) and **~3×** a community adult's work-related contacts (Jiang 2017a) —
while the per-hour work-block rate is **2.9–5.0 contact episodes/h** (Jiang
2017b). None of this supports one whole-day count applied to a sleeping
passenger and a waiter alike; all of it supports contacts derived from the
activity and the unit the schedule puts a host in. It does **not** supply a
cruise contact rate for a hand-transfer route: every count is a proximity or
conversation count, and the model's `direct_contact` partner is neither.

---

## 1. The cruise record: role, setting and accrual (questions 1–3)

**Pung R, Firth JA, Spurgin LG, Singapore CruiseSafe working group, CMMID
COVID-19 working group, Lee VJ, Kucharski AJ (2022).** *Using high-resolution
contact networks to evaluate SARS-CoV-2 transmission and control in large-scale
multi-day events.* Nat Commun 13:1956. DOI 10.1038/s41467-022-29522-y,
PMC9005731. Grade **A for the setting** (it is a cruise ship) and **B for the
operating state** (four three-day sailings from Singapore at **50% passenger
capacity**, masks, distancing, and crew in **work bubbles** — a floor on
pre-2020 contact counts, not a central estimate). Origins **R**, **F2**, **S**.

- Sample: four sailings, mean **1,304 passengers** (range 1,142–1,682, median
  age 54) and **1,050 crew** (1,003–1,083, eight departments) per sailing;
  **5,216 passengers and 4,197 crew** in all; **37-h** data-collection periods
  per three-day sailing. **3,963,256** contact episodes, **1,846,312** unique
  pairs. The authors state that in a cabin a device "may not necessarily be
  placed in a 2 m proximity" so cabin interactions "would not be recorded
  accurately" — the cabin is **∅ unmeasured** by this study. **R/Methods.**
- Definitions: a contact is a device-to-device proximity within **~2 m**; pairs
  are **close** at ≥15 min cumulative per day, **casual** at 5–15 min,
  **transient** at <5 min. **R/Methods.**
- **Role.** Passengers: median **20** unique close contacts per day (IQR
  **10–36**); crew: median **10** (IQR **6–18**). Duration-weighted degree
  13.9 (5.6–23.7) against 8.3 (4.4–13.5). **R.** Crew contacts cluster by
  department; housekeeping and galley staff are the exceptions whose contacts
  are dispersed across the network. **R/S.** So on the instrumented ships the
  crew made **half** the passengers' close contacts — the role dependence is
  real and, under bubbling, points the crew arm **down**.
- **Setting.** **~71%** of passenger–passenger close-contact episodes fall in
  food-and-beverage locations (buffet **~23%**, inclusive restaurants **~38%**
  of the location breakdown), entertainment **~16%**, sports **~8%**. **R/F.**
- **Accrual within a setting saturates.** After ≥1 h in an F&B location a
  passenger's close contacts there plateau at median **3** (IQR 2–5); in a
  sports venue **~2** at 30–60 min rising to **~4** at ≥2 h. **F2/R.** This is
  the form the architecture needs: a visit's contacts are a saturating
  function of dwell time in the unit, so a two-hour sitting and a one-hour
  sitting do **not** yield the same count, and the seating declarations
  (`meal_seatings`) change contacts by construction.
- **What it is not.** Not a hand-transfer or physical-contact count; not a
  pre-pandemic operating state; not the cabin. Its per-role daily totals are
  the natural **out-of-sample check** on what a schedule-derived model produces
  for each class on each hull — and because A5 (the passenger:crew ratio) is a
  scored anchor, **no per-setting rate may be chosen to move the model's
  crew:passenger contact ratio toward or away from Pung's 1:2**.

## 2. The reference: Mossong 2008, kept and re-read (question 3)

**Mossong J, Hens N, Jit M, et al. (2008).** *Social contacts and mixing
patterns relevant to the spread of infectious diseases.* PLoS Med 5(3):e74. DOI
10.1371/journal.pmed.0050074. Grade **C for this setting** (general
European population, paper diary, one day; a conversation of ≥3 words counts;
right-censored at 29; four countries excluded professional contacts). Origins
**R**, **T2**, **F**.

- Pooled mean **13.4** distinct persons per day (7,290 diaries, 97,904
  contacts); country means **7.95 (DE) – 19.77 (IT)**; weekdays **30–40%**
  above Sundays; the age profile peaks at 10–19 and falls after 50. **R/T.**
- **Location split** of contacts: home **23%**, work **21%**, school **14%**,
  leisure **16%**, travel **3%**, multiple/other the remainder. Physical share
  **~75%** at home, **~50%** at school and leisure, **~⅓** elsewhere. **R/F.**
- Reading against the model: 13.4 is retained as the **whole-day, whole-
  population reference** and the control arm. Its own location split says the
  count is a *sum over settings of very different intensity*, which is the
  argument for deriving it rather than declaring it; its "travel 3%" is the
  only measured figure for the corridor/transit block.

## 3. Day and night (question 3)

**Vanhems P, Barrat A, Cattuto C, et al. (2013).** *Estimating potential
infection transmission routes in hospital wards using wearable proximity
sensors.* PLoS ONE 8(9):e73970. DOI 10.1371/journal.pone.0073970. Grade **B**
(geriatric ward, wearable proximity sensors, 46 HCWs and 29 patients over 4
days and 4 nights). Origins **R**, **T**.

- **14,037** contacts, **94.1% in the daytime**; contact number and duration
  differ between morning, afternoon and night; patterns stable across days;
  six HCWs account for **42%** of contacts involving a patient. **R.**
- Reading: the uniform draw gives the nine `Sleep` hours **9/24 = 37.5%** of a
  host's contacts (partly dropped by the cabin's 1–3 eligible partners), against
  a measured **~6%** at night in the closest instrumented residential setting.
  This is the single largest misallocation of the whole-day draw and it is
  architecture, not magnitude: the night unit is the cabin.

## 4. Occupational analogues: working roles against resident ones (question 4)

**Duval A, Obadia T, Martinet L, et al. (2018).** *Measuring dynamic social
contacts in a rehabilitation hospital: effect of wards, patient and staff
characteristics.* Sci Rep 8:1686. DOI 10.1038/s41598-018-20008-w, PMC5786108.
Grade **B** (200-bed long-term care facility, RFID close-proximity interactions
≤1.5 m, four months). Origins **R**, **T2**.

- Median **11.6** distinct daily contacts per person (range **1.6–47.3**);
  median cumulative contact **17.1 min/day** (1.1–174.1). By role: hospital
  porters **24.6**, physicians **21.3**, other HCWs **14.3**, patients **11.2**
  distinct contacts per day. Patients hold the longest cumulative contact
  (~32 min/day). **T2/R.**
- Reading: the roles whose work moves them through the building make
  **1.3–2.2×** a resident's distinct contacts — the analogue for housekeeping,
  galley and service crew against a passenger, in a setting **without** work
  bubbles. Frequency and duration are **not interchangeable**: the residents
  have fewer, longer contacts.

**Jiang L, Ng IHL, Hou Y, et al. (2017a).** *Infectious disease transmission:
survey of contacts between hospital-based healthcare workers and working
adults from the general population.* J Hosp Infect. Grade **B/C** (Singapore,
diary, contact = conversation or touch). Origin **R** (Consensus full text).

- HCWs: median **13** work-related contacts per work day (range 2–69) against
  **4** (1–24) for community working adults; household 2 vs 3; other 1 vs 0.
- Reading: the *work block* of a working role carries **~3×** the contacts of a
  general adult's work block — the multiplier attaches to the activity, not the
  person, since household contacts are the same in both groups.

**Jiang L, Lee VJM, Lim WY, et al. (2017b).** *Contact patterns between
healthcare workers and patients in general wards.* Epidemiol Infect. Grade
**B/C** (Singapore general wards; diary, direct observation and interview).
Origin **R** (Consensus full text).

- Per shift, distinct persons contacted: nurses **14**, doctors **18**,
  assorted HCWs **15**. Observed within one hour: **3.5 / 2.9 / 5.0** contact
  episodes, cumulative **25.6 / 22.1 / 44.3** min. Patients over 24 h: **14**
  persons, **23** episodes, **314.5** min; patient–patient episodes rare
  (maximum five for one participant).
- Reading: the only **per-hour** rate for a working role in a confined
  institution, **2.9–5.0 episodes/h**, in a setting where the worker's task is
  contact. For a waiter or steward it is an upper analogue; for an engineer on
  watch it is not an analogue at all — hence a `work_service` and a
  `work_other` axis rather than one work rate.

**Shirreff G, Huynh B-T, Duval A, et al. (2024).** *Assessing respiratory
epidemic potential in French hospitals through collection of close contact data
(April–June 2020).* Epidemics 46:100807. Already recorded for
`CONTACT-SCALE-01`; re-read here for one finding: aggregate contact rate
**0.15 contact-minutes per person-minute** (ward range 0.08–0.26) is
frequency-dependent in aggregate. Reading: a per-setting rate need not scale
with the room's occupancy; occupancy enters through the eligible pool and
through φ, both already in tree. **R.**

## 5. What is null

- **A cruise per-setting contact rate under pre-2020 operations.** ∅. Pung is
  the only cruise sensor study and it is a COVID-era floor.
- **Cabin contacts.** ∅ on the cruise ship (devices left in cabins). The cabin
  block is bounded only by its pool (1–3 mates) and by Vanhems's night share.
- **A hand-transfer contact count in any of these settings.** ∅. Every count is
  proximity or conversation; the direct-contact partner semantics stay as the
  register already grades them.
- **A corridor/transit rate.** Only Mossong's 3% "travel" share; ∅ per hour.
- **Covers per server, or any operational contact rate for a waiter.** ∅ in the
  literature; documentary only (crew accounts), not sourced in this tranche.

## 6. What the tranche licenses, and what it forbids

Licenses: an **activity- and unit-derived** contact draw — the rate a host
draws at is set by the mixing unit the architecture places it in (cabin, table,
venue, corridor, service floor, work space, leisure space) and the schedule
token that put it there, each as a **declared per-hour interval** with the
provenance above; a **saturating** per-visit form where the dwell time is
known; role entering **through** the schedule and the duty state, with an
explicit role split only where a setting measures one.

Forbids: choosing any rate so the model's per-role totals land on Pung's 20/10
or Mossong's 13.4 — those are the **checks**; choosing any rate for its effect
on A5, A9 or the posting rate; presenting a proximity count as a hand-transfer
rate; retiring 13.4 from the documentation or from the control arm.
