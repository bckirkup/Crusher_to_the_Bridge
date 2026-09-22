> **Status:** Living — literature record for ledger NORO-HIGH-TOUCH-DEFINITION-01; adopts nothing

# Tranche 46 — what observation says is a "high-touch" surface

**Read first.** Tranche 45 asked how large the fomite areal denominator `A`
is, and answered with an envelope between two *readings* of the phrase "high
touch": `hardware` (hand-contact hardware only) and `broad` (hardware plus
touched planes). That split was a convenience of enumeration, not a finding —
neither reading was argued from anything anybody observed. The shipped
`HIGH_TOUCH_AREA_M2` table sat between the two, differently per zone class,
which is exactly the symptom of a table with no single definition behind it.

This tranche asks the prior question: **when an observational study counts
touches, which surfaces does it count?** That is a question the literature
does answer, repeatedly, in video-coded studies with five-figure touch
counts. The answer is the definition; the area arithmetic then follows from
it rather than from a choice between two enumerations.

Nothing here changes a constant.

**Retrieval.** Consensus MCP, full-text chunks on, queries phrased at the
measured quantity (touch counts, surface classifications, touch networks) and
the setting (restaurant, office, dormitory, hotel lobby, airport, aircraft
cabin, hospital room, cruise restroom). Each number below records the section
it was read in.

---

## 1. Every touch-observation study partitions surfaces the same way

The partition is not into hardware and planes. It is into **surfaces one
person touches** and **surfaces several people touch**, and the studies draw
it explicitly because it is the partition that matters for transmission.

**Jin et al. 2022**, *Int J Infect Dis*, DOI `10.1016/j.ijid.2022.05.047` —
the one norovirus surface-transmission study built on observed touches.
Guangzhou restaurant, CCTV, 89 diners in 17 family groups and 18 staff,
**41,042 touches**. *Results:* "a total of 87 subsurfaces in the restaurant
were identified as being involved. We divided them into seven groups: mucous
membranes (M), hand (H), body (B …), personal private objects (PP), personal
object provided by the restaurant for each table's use (PT, personal table's
objects), table's object for public use (T, table's public objects), and
object for public use for all individuals in the restaurant (R, restaurant's
public and common objects)."

The operative fact for this repository: **T and R are the shared classes, and
PT — the per-diner place setting — is not.** A place setting is provided by
the restaurant but is personal to one diner; Jin codes it separately from the
table's public objects for that reason. The diner shared-surface rate the
hull already ships (42.8/h) is T + R = 38.5 + 4.3; the staff rate (545.4/h)
is 245.8 + 299.6 over the same two classes. *Results, touch-frequency table.*

**Zhang et al. 2018**, graduate-student office. More than **120,000 touches**
over 60 h on **1,490 coded surfaces**; 5.02 touches/minute/student, mean
touch duration 21.72 s, 94.6% of observed time in contact with some surface.
*Results:* the surface-touch network is scale-free — **76.9% of surfaces have
degree 1** and 12.8% degree 2; the highest-degree public surface is a
water-dispenser button at degree 14. Public surfaces are rarer than private
surfaces but carry the network's connectivity.

This is the definition, measured: degree in the touch network is a property
of a surface that observation reports directly, and it is bimodal. The
overwhelming majority of touched surfaces are touched by exactly one person
and cannot mediate transmission between two.

**Zhang et al. 2021**, *Building and Environment*, DOI
`10.1016/j.buildenv.2020.107578`. Same office, **98,000+ touch actions** over
14 h, with a fomite transmission model on top. *Abstract/Results:* "Public
surfaces are responsible for 53% of virus transmission due to surface touch
to susceptible students"; door handles and mobile phones transferred the most
viral load to susceptible hands; "if we never touch other's personal
surfaces, we would reduce our exposure to the virus by 80%."

A minority of surfaces by count carries a majority of the transmission, and
the discriminating property is multi-user access.

## 2. The same partition in the settings the hull's zone classes stand in for

**Ackerley et al. 2025**, *Perspect Public Health*, DOI
`10.1177/17579139251371964` — the hotel lobby behind the hull's `public`
touch rate. *Methods:* 30 h of observation. *Results:* "A total of 324
individuals performed 627 touches over **13 different fomites**"; the
elevator button and front-desk counter took **32% and 22% of all touches**;
55% of individuals touched the elevator button; 56% touched two or more
surfaces; 314 surface-to-surface interactions. A seeded tracer reached 13
surfaces in 4 h, the most contaminated being tables, counter tops and door
handles.

Thirteen fomites is the whole shared inventory of a working lobby, and two of
them take over half the touches. The set is small and multi-user; the touch
distribution over it is heavy-tailed.

**Zhang et al. 2024**, *PLOS Comput Biol*, DOI `10.1371/journal.pcbi.1012561`
— norovirus in airports. *Methods/Results:* 21.3 h of video over nine
functional areas, **25,925 touches** from 1,760 passengers, "a total of 108
surfaces touched across all areas, categorized into four primary categories:
facial mucous …, body …, **private surfaces** (e.g., phones, boarding
passes), and **public surfaces** (e.g., check-in counters, restaurant
tables)." Public-surface disinfection every 2 h cuts norovirus infection risk
83.2%; handwashing every 2 h cuts it 2.0%.

Note what is filed as a public surface here: a restaurant *table* is public,
alongside a check-in counter. The partition is not hardware-vs-planes.

**Zhuang et al. 2023** — airport public-surface touch, same measurement
family. Touch on shared surfaces concentrates on self-service screens and
escalator handrails; self-service check-in screens were touched at 371.7/h
in the detailed excerpt and self-service areas carried 473.5 public-surface
touches/h in the abstract. Another heavy-tailed distribution over a small
fixed shared inventory.

**Lei et al. 2017**, DOI `10.1038/s41598-017-13840-z` — 21-row Boeing 737
economy cabin, **422 enumerated touchable surfaces** over 126 seats: 42 aisle
seatbacks, 84 non-aisle seatbacks, 126 tray tables, 168 armrests, 2 toilets.
Every one of the five item types is multi-user across a flight cycle, and the
enumeration is **3.3 shared surfaces per seat** — the count scales with
seats, not with the room.

**Carling et al. 2009**, DOI `10.1086/606058` — **8,344 objects in 273 public
restrooms on 56 cruise ships**, i.e. 30.6 evaluated objects per shipboard
public restroom, all of them multi-user by construction. The only shipboard
object enumeration in the retrieved literature.

**Huslage et al. 2010**, DOI `10.1086/655016` — five high-touch surfaces
identified from 50 observed HCW–patient interactions: bed rails, bed surface,
supply cart, over-bed table, IV pump. **Cheng et al. 2015** — 6,144 contact
episodes over 66 h in a six-bed cubicle; bedside rails 13.6 touches/h, tables
12.3 touches/h. Both lists mix hardware (rails, IV pump) with planes (bed
surface, over-bed table) without hesitation: what puts an item on the list is
that staff and patient both touch it, not what kind of object it is.

**Yuan et al. 2024**, *Building and Environment*, DOI
`10.1016/j.buildenv.2024.111976` — university dormitories, video-coded.
*Abstract/Results:* "Primary surfaces being touched included **desks,
cellphones, keyboards and computer mice**, with averaged touch frequencies
ranging from **10.4 h⁻¹ to 25.4 h⁻¹**."

Recorded here because the hull cites this study for its `cabin` touch rate of
17.9/h under the heading "primary shared surfaces". Three of the four named
surfaces — cellphone, keyboard, mouse — are personal-use objects in a
dormitory, and the fourth is a personal desk. This is an *all-surface* rate
for a residential occupant, not a shared-surface rate. Flagged as a
numerator-side provenance defect for `SURFACE_CONTACTS_PER_HOUR["cabin"]`;
it is out of scope for NORO-HIGH-TOUCH-DEFINITION-01, which changes nothing,
and is not repaired here.

## 3. What the tranche establishes

1. **A surface's degree in the touch network is the measured discriminant.**
   Observation partitions surfaces by how many people touch them (Zhang 2018,
   Zhang 2021, Zhang 2024, Jin 2022), and the single-user majority — 76.9% of
   coded surfaces at degree 1 — carries no person-to-person transfer.
2. **Object kind is not a discriminant.** Every enumerated shared set mixes
   hardware and planes: tray tables with armrests (Lei), bed surface with
   rails (Huslage), restaurant tables with check-in counters (Zhang 2024),
   counter tops with door handles (Ackerley). The tranche 45
   hardware-vs-broad axis has no counterpart in any observational protocol.
3. **The shared set scales with occupancy where the occupancy is seated.**
   Lei's 422 surfaces are 3.3 per seat; Jin's T class is per table, populated
   per diner. Ackerley's 13 lobby fomites are fixed. Both patterns are
   measured, and a denominator that is flat in occupancy matches neither for a
   seated zone.
4. **Touch is heavy-tailed over the shared set** (32%/22% of lobby touches on
   two of 13 fomites; a degree-14 hub in a 1,490-surface office). This does
   *not* by itself license shrinking `A` — see ledger §3 for why the engine's
   own uniform-deposition assumption forces the unweighted sum — but it is the
   quantity that would matter if deposition were hand-mediated.

## 4. Null register — unchanged

Tranche 45 registered `∅nr` (no retrieved source reports it) and `∅lit` for
the cruise zone classes on **summed high-touch area per room**. The further
queries in this tranche, phrased at surface inventories, touch networks,
coded-surface counts and per-area touch rates across six settings, retrieved
**no source reporting a summed high-touch area for any room of any kind**.
Counts of surfaces, touch rates per surface, and total room surface remain
available; their product remains underived in the literature and derived only
here. **The null stands.**

## 5. Queries run (Consensus MCP, full-text chunks on)

1. Zhang 2018 graduate student office 1490 coded surfaces scale-free surface
   touch network proportion of touches on few surfaces power law degree
   distribution
2. Jin 2022 restaurant surface classification table public use objects
   tablecloth chairs personal private surfaces list of coded surfaces
   norovirus
3. Yuan 2024 dormitory surface touch frequency shared surfaces per hour video
   observation list of shared surfaces door handle desk bed university
   dormitory
4. Zhuang 2023 airport public surface touch frequency self-service check-in
   screen escalator handrail touches per hour
5. Zhang 2021 office fomite route touch actions public versus personal
   surface virus transfer door handle mobile phone
6. — plus the tranche 45 ladder (high-touch surface area per room; enumerated
   high-touch object inventories; hospital high-touch surface lists; cruise
   ship restroom object counts; aircraft cabin touchable surface enumeration;
   surface-to-volume ratio of furnished rooms), re-run against the
   touch-behaviour framing.

Sources first retrieved in tranche 45 and re-read here for their surface
classification rather than their counts: Huslage 2010, Cheng 2015, Lei 2017,
Carling 2009. Sources new in this tranche: Zhang 2018, Zhang 2021, Zhang
2024, Yuan 2024 (full-text surface list), Ackerley 2025 (full-text fomite
count and touch shares), Jin 2022 (full-text seven-class coding scheme).
