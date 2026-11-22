# COVID voyage-stage contact evidence — memo for SEED-RING-02

**Status:** Draft. Evidence pass commissioned 2026-11-21 after
COVID-EARLY-GROWTH-01 showed the record-timed overshoot sits in early
growth, not the tail, and that θ is confounded between founder yield and
post-founder growth. Framing per Edison's two linked propositions: (1) does
representing the actual early exposure opportunities establish the outbreak
at the appropriate time? (2) does representing subsequent routine contacts
prevent early-established outbreaks from growing too rapidly? A surge that
expires back to the unchanged current routine is not enough — the routine
itself is under examination.

## 1. What the model declares today

In the boxed_s1s2 replay (`diamond_princess_2020`, and every DP design so
far): `contact_mode = per_partner_contact` with **no `activity_contacts`
block**, so every host on every zone visit draws partners
`Poisson(POLYMOD_CONTACTS_PER_DAY=13.4 × voyage_contact_multiplier=1.0)`
scaled per epoch (`engines/transmission_core.py:6894-6902`, `8250`).
Consequences:

- **Flat across voyage days.** The turnaround-day crush draws partners at the
  same rate as a quiet sea-day afternoon. `voyage_contact_multiplier` is the
  only stage handle and it is a single flat scalar.
- **Maximal partner novelty.** Partners are sampled fresh from zone
  occupants every epoch; no repeat-partner structure below the cabin/table
  ring.
- **No measured per-activity rates.** CONTACT-ARCH-01
  (`transmission.activity_contacts`, 8 activities × 2 roles) exists but has
  no engine defaults because none is measured on a cruise ship under
  ordinary operations (tranche-37 note in the code).

## 2. Evidence — settled-voyage routine (days 6+)

| Number | Definition | Source | Where read |
|---|---|---|---|
| 20 (IQR 10–36) | unique close contacts/day, passengers | Pung et al. 2022, Nat Commun 13:29522 | Abstract + Fig. 1 |
| 10 | unique close contacts/day, crew | same | Abstract |
| ~3 (IQR 2–5) | close contacts per ≥1 h F&B visit, saturating | same | Fig. 2 |
| 79% | close-contact episodes intra-cohort (travelling groups) | same | Results |
| >60% | close-contact episodes in dining or sports areas (mask-off) | same | Abstract |
| 86% | of contact pairs on cruises occur on a single day only | Pung et al. 2024, J R Soc Interface | Results/fig. 4a |
| 20–70% | overestimate of unique contacts when assuming day-independence | same | Abstract |

Grade A for setting on Pung 2022 — a real cruise — attenuated: 50%
capacity, COVID-era work bubbles, masking off-ship. So ~20/10 close
contacts/day is a *floor* for ordinary operations. Pung 2024's 86%
single-day-pair figure says cruise partner novelty is intrinsically high —
the fresh-draw structure is *less* wrong on a ship than it would be on land;
do not lean on repeat-partner structure to justify the routine stage.

**Definition gap (recorded, not resolved):** the model's partner draw is
Polymod-semantics (≥3-word conversation or physical contact/day); Pung's
"close contact" is a cumulative-duration proximity episode, reported
across several duration thresholds (their Fig. 1c). 20/day is not
directly comparable to 13.4/day — comparing them is a units error until
the Pung episode threshold is mapped onto Polymod-class contacts. The
bounded-question deliverable is the mapping, not a re-fit.

## 3. Evidence — embarkation window (days 0–5)

**Operational record (non-journal class — agency/industry, no literature
index covers it).** Voyage day 0 (2020-01-20) was a Yokohama *turnaround*:
arrive 06:00, depart 17:00 (Yokohama port calendar; crew-center itinerary).
A ~2,700-passenger turnaround packs terminal processing queues, the
SOLAS-required muster drill before departure, and the boarding-day buffet
crush into one afternoon — a dense crowd of *strangers*, i.e. maximum
novelty partner mixing. The index boarded at Yokohama on day 0 and departed
Hong Kong on day 5: his entire aboard window overlapped the post-turnaround
mixing phase.

**Measured in our own campaign (SEED-RING-01 / IGNITION-01):**

- Founder routes aboard-window are droplet + caregiver only; the founder
  lottery discriminates early ignition with zero overlap (≥10 founders →
  ign ≤9).
- Surge venues exist in the declared schedule but drawn itineraries hit
  them ~15–20% of the time — placement at the surge buffet did not lift the
  founder pool (NULL-PLACEMENT), so the under-declared structure is the
  crowd participation itself, not the venue assignment.
- Day-0 droplet bursts of 25/11/6 on the fastest cells prove the machinery
  reaches record-implied yield when the drawn index does hit a broad
  embarkation-day footprint.

**Literature: no cruise embarkation sensor record exists** — recorded as
absence of evidence, not a null result on the mechanism. Bounding
measurements from mass-gathering settings: Cattuto et al. 2010 (RFID,
conference crowds up to 575 participants, ~1 m/20 s face-to-face
proximity granularity, super-linear connector behaviour); transient
contacts at dense events are mostly 1–30 s proximities (Thota et al. 2024,
UWB indoor location). A boarding-window uplift is therefore a **declared
assumption bounded by mass-gathering measurements**, not a sourced
constant.

## 4. What the record implies the two stages must produce

- Founder pool ~10 within the index's 5-day aboard window (IGNITION-01).
- Pre-quarantine infections ≲800 implied by the [712,960] band and the
  day-16 arrest; 34 recorded onsets before day 17.
- Record-implied early growth ~1.3–1.4×/day; the model's record-timed cells
  run ~1.45–1.5×/day sustained through day 15 and reach d15 median 1,292 —
  the overshoot compounds a modest daily-rate excess with a founder-count
  excess (EARLY-GROWTH-01).

## 5. Declaration candidates (for the SEED-RING-02 design)

Two propositions, two declarations:

- **P1 — embarkation window.** A voyage-day-windowed contact schedule: the
  day-0/1 window (muster, terminal, boarding buffet) carries an uplift α on
  the partner draw for *everyone* (the crowd mixes, not just the index),
  relaxing to the routine draw after the window. Mechanism already in
  tree: the voyage itinerary layer (`engines/voyage_itinerary.py`)
  resolves a per-day `contact_rate_multiplier` into
  `voyage_contact_multiplier` when `voyage.effects_enabled` — the DP
  config ships the flag off with an empty itinerary, so the declaration
  is config-level (embarkation day type + α), not an engine change.
  α is a declared assumption bounded by mass-gathering measurements
  (no embarkation sensor record); the design declares it, not fits it.
- **P2 — settled routine.** The routine stage gets its own independently
  justified draw — the honest candidates are the flat POLYMOD draw (current)
  vs a Pung-anchored activity schedule (`activity_contacts` armed, all 8
  rates declared). Which one runs is part of the frozen prediction, not a
  fit: if the Pung floor (~20/10 close contacts/day) maps above the current
  13.4 draw, the routine stage is *under*-dense on count and the growth
  correction must come from dose/partner structure — recorded here as an
  open mapping question, not picked.

**Frozen two-leg prediction shape:** (a) founder median ≥10 with ignition
≤9 on window-uplifted arms (early establishment); (b) on record-timed
cells, post-window growth lands the record-implied slope and d15 infections
≤960 (routine prevents over-rapid growth). Both legs declared before any
cell runs; θ and every dose constant unchanged.

## 6. What remains open (owner/design calls)

- Window length: turnaround afternoon (day 0) vs the index's whole aboard
  window (days 0–5). The founder bursts that produce record timing are
  concentrated day 0–1 on the fastest cells — lean day 0–1, sweep the
  alternative.
- α bounds: pick from mass-gathering contact rates; needs one more
  retrieval pass on queue/muster-density contact measurements if a number
  is required pre-freeze, else declare the assumption band.
- The Polymod-vs-Pung definition mapping (§2) decides whether the routine
  stage is under- or over-dense — resolved by reading Pung's close-contact
  episode threshold before the design freezes.
