# NORO-GROWTH-01
**Date:** 2026-09-27
**Commit:** ce8e3020
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** ce8e3020

Why ignited `fl_spr_12d` voyages never compound: a link-by-link census of the
"secondary case → sheds → deposits → picked up → tertiary infection" chain,
measured end-to-end on every ignited voyage in the refit set.

## Cohort

All 60 refit seeds (8105–8164) were screened; the 22 carrying an emesis
witness (`emesis_events > 0` in `refit.json`, NORO-DOSE-REFIT-01 `4a619493`)
were re-run locally under `tools/noro_diag/growth_chain_census.py` with the
verbatim `fl_spr_12d` spec (spirit_cruise_3000, n=3000, 288 epochs,
`syndromic_comp65`, `dwell_weighted`, `cabin_compartment`, pool `airflow`,
dose_adjustment 7.57). All 22 confirmed ignited in the census (a gen-0 host
filed patch mass). No AWS array was needed: the ignited set was small enough
to run on-box (~2 h, 2 workers).

**Instrument caveat (measured, affects prior counts):** `_emit_emesis`
creates `agent.emesis_deposition_records_by_pathogen[pathogen_id]` via
`setdefault` *inside* the emit call. A probe that snapshots the list with
`.get(pathogen_id)` before the call never sees the host's **first** emit —
the patch still files (`pool_gain` is returned), but no deposition record is
visible to the probe. `emesis_witness.emesis_events` (refit) and this
census's emit rows read the same store, so emit-record counts are a lower
bound. Ignition in this entry is keyed on filed patch mass
(`emesis_patch_gec > 0` or patch depositor tag), which is complete. The
first emit per host is also the most likely to land mobile/venue-side, so
emit-row landing tables systematically undercount venue landings — the
landing census below is rebuilt from patch sweeps, which are complete.

## L1 — Secondary shedding: alive

Pooled over the 18 challenge-acquired hosts on the 22 ignited voyages:
449k GEC shed, 41 scheduled emesis draws, 18 recorded emits, 221M GEC filed
to patches, 341k GEC of surface deposits, 101 stool events. Per symptomatic
epoch the acquired deposit 355 GEC vs the index's 2,492 — ~7x lower (an
order within range, not a dead link; confinement timing and post-detection
hygiene account for part of it). 42% of acquired infected epochs are spent
confined (1,753/4,217). Only **9 of 18** acquired hosts ever filed patch
mass — the vomiting-axis draw gates the other half out of the bolus channel
entirely (they still shed/deposit).

## L2 — Deposit landing: lands, mostly in shared zones

Acquired-sourced surface deposits by unit class: `other_zone` 272k GEC,
`cabin_fittings` 68k GEC, `shared_head` 29 GEC — 80% of deposited mass
reaches shared space (index split is the reverse: 5.10M cabin / 114k other /
8.7k head — index cabins carry its bulk because index shedding precedes
detection and its cabin-mates are still susceptible then).

Patch-sweep census (every sweep of a unit holding patches, by depositor
class — the "mass sat with nobody to touch it" half of pickup):

| depositor | sweep-epochs | mass swept (GEC) | zero-susceptible sweeps | mass unseen (GEC) |
|---|---|---|---|---|
| import | 6,938 | 1.03e10 | 5,540 (80%) | 8.69e9 (84%) |
| acquired | 1,611 | 1.58e9 | 1,472 (91%) | 1.42e9 (89%) |

Removal accounting on patch mass — for acquired-sourced patches, pickup
delivered 3.46M GEC while routine cleaning + outbreak disinfection +
survival decay removed 217.6M GEC (~98.4% removed, 1.6% delivered). For
import patches: 72.6M delivered vs 850.6M removed (~8% delivered). The
cleanup dominance is the same declared mechanism on both sides; it bites
the secondary harder because its patches sit in cleaned cabins.

## L3 — Pickup into susceptible hands: the named link

Three partition facts, all measured:

1. **Cabin channelling.** Acquired emesis landed in 12 distinct units: 8
   cabins, 4 venues. At first sweep the 8 cabin units held 1–2 occupants
   with **0 susceptibles in 6 and 1 in the other 2** — the co-occupant is
   the source (already infected); a secondary confined to its own cabin
   vomits into a room whose only reachable hands are immune. The 4 venue
   landings (MainGalley ×2, MainDining_U, MainTheater) each found 114–257
   susceptibles.
2. **Footprint lottery.** Even when the bolus lands in a full venue, the
   per-occupant footprint share (~1.4% for MainGalley-class rooms) yields
   only 1–4 pickup requests per sweep — s8159's 6.1e7-GEC MainDining_U
   patch drew exactly 1 requester out of 116 susceptibles.
3. **Zone-pool dilution.** The non-emesis channel does reach hands — 5,433
   acquired-sourced zone-pool pickups pooled — but at median dose
   4.4e-4 GEC (p90 0.29), ~5+ orders below a convertible dose. Co-presence
   census: of 2,846 unit-epochs containing acquired-sourced pool mass, only
   902 (32%) had a susceptible present.

The pickup gate is exonerated again: 6.5M `pickup_gate_open` evaluations
closed on pools holding a total of 5,000 GEC — noise, not a blocker
(NORO-REBASE-01 `a872367c` stands).

## L4 — Conversion: at naive rate, gated by the frailty draw

Pooled dose-response hazard over all challenges: 17.7 expected vs 18
observed acquisitions. On challenges whose delivered mass was ≥50%
acquired-sourced: expected 1.32 vs **4 observed** — conversion runs at (or
above) naive rate. The terminal link is not under-powered; it is
starved of *jointly* (dose, viable-frailty target) arrivals. Example:
s8159's dining-hall patch delivered 2.38e5 GEC to the single footprint
winner, hand-to-mouth dose 1.28e3 GEC — but that host's susceptibility
frailty drew 1.3e-10 → hazard 5e-8. A lottery won by the wrong host.

## L5 — The named link: L3 presence/partitioning

No link carries hard zero, and no gate or route annihilates mass it
shouldn't touch. The link carrying ~zero throughput is **pickup
partitioning**: where the secondary's mass lands versus where susceptibles
are. It decomposes into three declared mechanisms acting jointly —
confinement channelling emission into the self-consuming cabin (the
secondary's only cabin-mate is typically its source), the emesis footprint
share (NORO-EMESIS-FOOTPRINT-01 / the #604 verdict — stands), and
cleanup/decay dominance (~98% of secondary patch mass removed before
pickup). All by-design; **no defect found**.

Per-run named link:

| seed | acq | acq-src | link |
|---|---|---|---|
| 8105 | 1 | 0 | L3 (mass present, no susceptible pickup) |
| 8107 | 0 | 0 | L0 (ignition produced no secondary) |
| 8110 | 0 | 0 | L0 |
| 8112 | 0 | 0 | L0 |
| 8113 | 0 | 0 | L0 |
| 8114 | 2 | 0 | L4 (expected 3.1e-4 tertiaries, got 0) |
| 8115 | 0 | 0 | L0 |
| 8117 | 0 | 0 | L0 |
| 8121 | 0 | 0 | L0 |
| 8123 | 0 | 0 | L0 |
| 8124 | 1 | 0 | L4 (exp 1.1e-5, got 0) |
| 8129 | 3 | 2 | intact end-to-end |
| 8132 | 1 | 0 | L4 (exp 5.1e-5, got 0) |
| 8135 | 1 | 0 | L3 |
| 8137 | 3 | 2 | intact end-to-end |
| 8148 | 1 | 0 | L4 (exp 2.4e-5, got 0) |
| 8149 | 0 | 0 | L0 |
| 8156 | 1 | 0 | L4 (exp 7.1e-5, got 0) |
| 8158 | 3 | 0 | L4 (exp 0.015, got 0) |
| 8159 | 1 | 0 | L4 (exp 0.14, got 0 — incl. the 1.3e-10-frailty draw) |
| 8162 | 0 | 0 | L0 |
| 8163 | 0 | 0 | L0 |

L0 on 10/22: the index patch itself produces no secondary — ignition is a
rare event *and* conversion of it is another lottery.

## Arithmetic summary

Per-generation yield on this cell: ~14 secondaries across 22 ignited
voyages (~0.64/ignited voyage, matching the refit's ~0.9 within noise),
then expected tertiary yield 1.32 pooled across the 15 voyages that had a
secondary (~0.09/secondary-voyage; 4 observed — above the naive expectation
because two venue landings hit). The chain is subcritical at ~0.1 per
generation; ~13-concurrent peaks and 0/120 VSP postings are the arithmetic
consequence, not a dead link.

Consequence for the next session: not a mechanism repair. Any honest
recovery is on the **source side** — how much mass a confined symptomatic
case can shed into shared space before/without confinement, how often the
first emit lands mobile, and whether the frailty draw that annihilates
1e3-GEC doses is the intended susceptibility spread (DOSE-FRAIL-01).
All constants named above remain as declared; nothing here authorizes
retuning them.

## Instruments

`tools/noro_diag/growth_chain_census.py` (per-host generation census:
emits, deposits, patch sweeps, pickups, doses, hazards, acquisitions with
delivered-mass provenance; read-only wrappers, no RNG draws) and
`tools/noro_diag/growth_chain_readout.py` (folds run zips into the link
table; ignited = emitting import under the corrected patch-filing
definition). Run zips are local `growth_runs/` scratch — the tables above
are the durable record.
