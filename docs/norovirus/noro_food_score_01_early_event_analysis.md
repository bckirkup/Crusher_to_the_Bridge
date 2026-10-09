# Early shared-dose event analysis — how big does the seed need to be to reach the wire?

> **Status:** Measured — analysis of landed SCORE-01 + MEGA-IMPACT-01 data; no new simulation cells

> **Status note (2026-10-09):** numbers below are measurements over the
> landed campaign zips; nothing was re-simulated. All sizes are *taker
> counts* (heads served one shared pan/lot serving) — `dose_credited`
> values exist per object/event but are withheld from the tables pending
> the withdrawn dose-ledger refit.

Question (verbatim intent): *"how big does the 'early multi-host event'
need to be for each class"* — the size of the synchronized shared-dose
seed required to reach the VSP reported-case wire (3% of role
population), so routes and frequencies to initiating events become
legible.

**Answer in one paragraph (measured):** there is no single "how big" —
the required seed grows with hull size until it outruns the mechanism.
On exp the wire is reachable with no early shared-dose event at all
(39/117 postings had none; the smallest that ever preceded a posting is
**3 takers**). On cls and spr every `ind` posting sat behind an early
event of >=**26** / >=**34** takers respectively, with conversion
ramping monotonically ~13–58% inside the observed range — a ramp, not
a cliff. On mega the mechanism's own ceiling (80 takers per pan) is
hit routinely and still buys at most 0.86 of the wire. On the object
arms everywhere, events several-fold to ~10× larger than the `ind`
sizes convert at ~0.1–0.2% vs `ind`'s 1.4–19.5% — **size is not the
discriminating variable; the seeded-draw shape is**. The route that
matters is the provisioned lot: ~4–11% of early events but the
voyage-max driver on most posted voyages.

## Definitions

- **Early shared-dose event.** On object arms (`ol1`–`ol3`, `ship`): one
  contamination *object* with `seeded_epoch <= 48` (provisioned lots
  surface days 1–3 by construction; handler/diner objects can seed any
  time — the <=48 h conditioning is per object). On `ind`/mega arms: one
  pan-window serving *event* with `start_epoch <= 48`. Conditioning is
  per event, not per voyage.
- **Size.** Takers served across the event's windows:
  `servings_served` on objects, `servings_taken` on v1 pan-window rows.
  Per-window serving size (`pw`) is reported alongside object totals
  where the window view matters.
- **Posted.** `reported_case_attack_rate_{pax,crew} >= 0.03` — the same
  A9 wire as the SCORE-01/MEGA-IMPACT-01 readouts.
- **Reach.** `max(rep_pax_ar, rep_crew_ar) / 0.03` — fraction of the
  wire a voyage attained.

Data: `campaign/noro_food_score_01/` (18 cells x 1,000 seeds, engine
`40862b8c`) and `campaign/noro_mega_impact_01/` + `campaign/noro_mega_01/fl_mega_12d_scr`
(A0 baseline). Tooling: `tools/noro_diag/early_event_scan.py` (streams
`summary.json` by ranged reads + tail-decodes `growth_census.json.gz`),
`tools/noro_diag/early_event_report.py` (the tables below).

## §0 Wires and complements (measured from emitted complements)

| hull | pax comp | crew comp | wire (3% -> min reported cases) | posted n |
|---|---|---|---|---|
| exp (expedition_cruise_450) | 316 | 134 | >=10 pax / >=5 crew | TBD |
| cls (classic_cruise_1900) | 1,338 | 572 | >=41 pax / >=18 crew | 46/6,000 |
| spr (spirit_cruise_3000) | 2,100 | 900 | >=63 pax / >=27 crew | 21/6,000 |
| mega (mega_cruise_5000) | 4,900 | 2,100 | >=147 pax / >=63 crew | 0/926 |

Emitted complements are trusted over nominal passenger counts: spr
emits 2,100/900 (wire **>=63/>=27**, not the ~90/38 nominal); cls emits
1,338/572 (wire **>=41/>=18**). Per-cell postings (measured,
`early_event_scan` summary side): exp `off` 10 (other exp cells below);
cls — `ind` 41, `ol1` 1, `ol2` 1, `ol3` 1, `ship` 2, `off` 0; spr —
`ind` 14, `off` 1, `ol1` 1, `ol2` 1, `ol3` 2, `ship` 2. Posted-cell
counts on the object arms are thin (1–2/cell) — treated as thin cells
throughout (reported, not smoothed).

## §1 Frequencies leg — P(>=1 early shared-dose event per voyage) vs posting rate

Two-factor decomposition per cell: `P(post) = P(early event) x
P(post | early event)`, with the posterior read off the censused
subpopulation (unbiased: posted voyages were censused at 100%, unposted
at a stride sample, so rates are estimated on the unposted sample and
posted voyages added back explicitly — no sample bias).

| cell | P(>=1 early) | posted n | posted w/ early | P(post \| early) | P(post \| no early) |
|---|---|---|---|---|---|
| exp `ind` | 29.3% | 68 | 57 | 19.5% | 1.6% |
| exp `ol1` | 39.1% | 10 | 3 | 0.8% | 1.2% |
| exp `ol2` | 39.1% | 11 | 4 | 1.0% | 1.2% |
| exp `ol3` | 39.1% | 13 | 6 | 1.5% | 1.2% |
| exp `ship` | 39.3% | 15 | 8 | 2.0% | 1.2% |
| exp `off` | — (no census; 0-witness by construction) | 10 | — | — | ~1.0% |
| cls `ind` | 89.5% | 41 | 41 | 4.6% | 0.0% |
| cls `ol1`–`ol3` | 91.0% | 1 each | 1 | ~0.1% | 0.0% |
| cls `ship` | 88.0% | 2 | 2 | 0.2% | 0.0% |
| cls `off` | 0.0% (n=30 spot) | 0 | — | — | — |
| spr `ind` | 97.0% | 14 | 14 | 1.4% | 0.0% |
| spr `ol1`–`ol2` | 97.0% | 1 each | 1 | ~0.1% | 0.0% |
| spr `ol3`/`ship` | 97.0% | 2 each | 2 | ~0.2% | 0.0% |
| spr `off` | 0.0% (n=31 spot) | 1 | 0 | — | ~0.1% |

Measured readings:

- **On big hulls, early shared-dose events are nearly universal** (cls
  ~90%, spr ~97% of voyages have >=1). Frequency is not the bottleneck —
  *conversion* is: identical giant objects convert at ~0.1–0.2% while
  the much smaller v1 events on `ind` convert at 4.6% (cls) / 1.4%
  (spr).
- **On exp, frequency is scarce but conversion is high**: only ~29% of
  `ind` voyages see an early event, yet each converts at 19.5% — and
  postings also arrive without one (1.2–1.6% baseline, ~1%/voyage on
  `off`). On a 450-passenger hull the wire is low enough (10 pax / 5
  crew reported cases) that diffuse seeding alone reaches it.
- Every `ind` posting on cls and spr had an early event (41/41, 14/14);
  on exp 11/68 `ind` postings had none.

## §2 Size join — early-event size on posted vs unposted voyages

Size = voyage-max early event in takers (`servings_served` objects /
`servings_taken` events). Per posted voyage the largest early event is
what "preceded" the posting.

| cell | posted n | max-early med \[p90\] on posted | unposted n | max-early med \[p90\] unposted |
|---|---|---|---|---|
| exp `ind` | 68 | 18 \[29\] | 932 | 0 \[14\] |
| exp `ol1`–`ship` | 49 | 0 \[~75–110\] | 3,951 | 0 \[~78–82\] |
| cls `ind` | 41 | 52 \[70\] | 100 | 35.5 \[56\] |
| cls object cells | 5 | 317–376 range | 405 | ~384 \[~1005\] |
| spr `ind` | 14 | 61 \[76\] | 100 | 42.5 \[68\] |
| spr object cells | 6 | 260–959 range | 404 | ~586 \[~1186\] |

Posted-voyage max-early sizes, listed in full (thin cells included):

- exp `ind`: min **3**, median ~18, max 39 — `0`s on 11 voyages with no
  early event; values `3,4,6,10–29,31,34,34,34,39` on the rest.
- exp object cells (pooled 49 posted): 28 with no early object; the 21
  with one carried 32–260 takers (values recurring 32 / 63–65 / 73–75 /
  110 / 260 across `ol1`→`ship` — the same seeded objects on the
  shared-seed grid).
- cls `ind` (all 41): `26–72`, median ~51.
- cls objects (5 posted): `317, 317, 376, 376, 376`; unposted med
  ~384 — **the posted voyages' objects sit inside the unposted size
  distribution; size does not discriminate on object arms.**
- spr `ind` (all 14): `34–77`, median ~61.
- spr objects (6 posted): `260, 260, 882, 959, 959, 959`; unposted med
  ~586 — same non-separation.

## §3 Threshold — does a minimum-size floor exist?

Conversion of the voyage-max early event by size cut, `ind` cells only
(object cells pooled at hull level show the giant-object ~0.1% flat
conversion regardless of cut):

| max-early >= | exp `ind` conv | cls `ind` conv | spr `ind` conv |
|---|---|---|---|
| 3 takers | 57/282 = 20.2% | 41/129 = 31.8% | 14/111 = 12.6% |
| 10 | 54/198 = 27.3% | 41/127 = 32.3% | 14/110 = 12.7% |
| 15 | 43/130 = 33.1% | 41/125 = 32.8% | 14/106 = 13.2% |
| 20 | 28/71 = 39.4% | 41/122 = 33.6% | 14/105 = 13.3% |
| 26 | 14/29 = 48.3% | 41/113 = 36.3% | 14/96 = 14.6% |
| 34 | 4/7 = 57.1% | 36/94 = 38.3% | 14/82 = 17.1% |
| 50 | — (none exist) | 25/43 = 58.1% | 13/49 = 26.5% |

Smallest early event that ever preceded a posting, per hull:

- **exp: 3 takers** (and 39/117 postings had no early shared-dose event
  at all). There is no minimum on exp — "~10–25 takers suffice" is
  answered *yes, and smaller*: even 3–10-taker events convert at ~20%.
- **cls: 26 takers** — 41/41 `ind` postings had >=26; 0/28 unposted
  voyages below 26 posted (sample too thin to call it a hard floor, but
  nothing below 26 ever converted).
- **spr: 34 takers** — 14/14 `ind` postings had >=34; 0/32 unposted
  below 34 converted.
- **mega: no posting exists** — see §5.

The pattern is a **monotone ramp, not a cliff**: each hull's conversion
climbs smoothly with voyage-max size on `ind`; on the object arms the
distribution is shifted ~10× larger but conversion collapses ~50× —
size alone does not buy conversion on big hulls, the shared-dose
mechanism *shape* does.

## §4 Route decomposition — which route produced the early events that preceded postings

Source arms are `provisioned_lot` (lot rows materialized days 1–3 by
construction), `ill_handler`, `ill_diner` — the same `source_kind` on
object rows (`ol`/`ship`) and v1 pan-window events (`ind`). Coverage:
censused voyages only (`off` cells contribute no events; exp `off`'s
10 postings are therefore absent from the "posted" rows).

| hull | early events on posted voyages (lot/handler/diner) | early events on all censused voyages | voyage-max early event's arm on posted voyages |
|---|---|---|---|
| exp | 255 / 63 / 24 (**74.6%** / 18.4% / 7.0%) | 407 / 2,568 / 865 (10.6% / 66.9% / 22.5%) | lot 55, handler 19, diner 4, none 39 |
| cls | 172 / 82 / 115 (46.6% / 22.2% / 31.2%) | 193 / 1,280 / 901 (8.1% / 53.9% / 38.0%) | lot 25, handler 3, diner 18, none 0 |
| spr | 72 / 106 / 89 (27.0% / 39.7% / 33.3%) | 143 / 2,235 / 1,326 (3.9% / 60.3% / 35.8%) | lot 8, handler 1, diner 11, none 1 |

Measured readings:

- **Provisioned lots are the dominant route to a posting.** On every
  hull, posted-voyage early events are lot-dominated far beyond their
  baseline share (exp 74.6% vs 10.6%; cls 46.6% vs 8.1%; spr 27.0% vs
  3.9%). Handler and diner objects outnumber lots ~6–15× in the general
  population but contribute a minority of the events that precede
  postings.
- The voyage-max early event on a posted voyage is a provisioned lot on
  55/78 exp (with events), 25/46 cls, 8/20 spr — and an `ill_diner`
  event is second (18 on cls, 11 on spr). Ill-handler objects, the most
  common early source, almost never drive the voyage-max on posted
  voyages (3 on cls, 1 on spr).
- "Routes to initiating events" therefore reads as: *lots produce few
  events but most of the ones that matter; handler/diner routes produce
  frequency without conversion.*

## §5 Mega — the "doesn't cross" half

MEGA-IMPACT-01 ran the v1 pan-window mechanism (`common_source.mode:
"on"`, independent draws — no contamination objects). Census coverage:
a3 (cg off / food on) n=150, a1_bp40c30 n=50, a1 (cg on / food on)
n=60 stride sample, a0id n=10 (food off — 0 events, canary-clean).

| arm | n | >=1 early event | early events/voy (med) | max-early med \[p90\] | biggest early | reach med \[max\] |
|---|---|---|---|---|---|---|
| a1 (cg on/food on) | 60 | 55 (92%) | ~95 (all epochs) | 61 \[75\] | **80** | 0.39 \[0.68\] |
| a1_bp40c30 | 50 | 50 (100%) | ~146 | 71 \[79\] | **80** | 0.44 \[0.86\] |
| a3 (cg off/food on) | 150 | 145 (97%) | ~97 | 67 \[79\] | **80** | 0.29 \[0.76\] |
| a0id (food off) | 10 | 0 | 0 | 0 | — | 0.42 \[0.47\] |
| A0 baseline (`noro_mega_01`) | 308 | — | — | — | — | — \[0.75\] |

Measured: on mega, the biggest observed early event is **80 takers —
exactly the declared `COMMON_SOURCE_PAN_SERVINGS_RANGE = (20, 80)`
ceiling**; a substantial mass of voyages saturates it. The saturated
seed buys reach ≈0.68–0.86 of the wire (best: 0.857, a1_bp40c30) —
i.e. the largest early event the v1 mechanism can emit falls ~14%
short of posting on its best draw, and the typical voyage sits at
~0.3–0.4. There is no size axis left inside the v1 mechanism: the
distributions at max-early=80 span reach 0.24–0.68 with no
size-to-reach ordering within the cap.

What this does *not* measure: whether a 300–1,000-taker contamination
object would cross on mega — object mode was never armed there (the
mega tiers run `"on"`, not `"object"`). The nearest evidence is the
big-hull object cells (cls/spr), where objects of exactly that size
convert at ~0.1–0.2% — nothing in the landed data suggests mega's
larger denominator would rescue conversion, but that is inference, not
measurement.

## §6 Instrument gaps and caveats

- **Mega carries v1 events only, never objects** — all food-on arms
  (`a1`, `a1_bp40c30`, `a3`) emit per-event pan-window rows (verified on
  the landed zips: a1 55/60 with early events), so per-event size
  conditioning *is* available on mega; the gap is that the object-mode
  mechanism — the only route to >80-taker shared seeds — was never
  armed on this hull. Whether giant objects would cross at mega scale is
  not measurable from landed data.
- **Early emesis-in-shared-venue is not measurable from the census:**
  host rows carry per-host emesis tallies (`emesis_emitted`,
  `emesis_surface_gec`, ...) but no per-episode epoch/venue rows — the
  "very public emesis" synchronized seed cannot be conditioned on
  <=48 h or on venue from the landed artifacts. Instrument gap.
  The coarse proxy that *is* measurable — voyage-total emesis emitters —
  is strongly associated with posting (posted vs unposted medians:
  exp 9 vs 2, cls 38.5 vs 17, spr 52 vs 26), consistent with emesis as
  the other synchronized-seed channel, but it cannot be conditioned
  early/public from this payload.
- **`off` cells are zero-witness by construction** (mechanism off); the
  316-voyage spot check from the SCORE-01 readout stands, re-verified on
  a fresh sample here.
- Posted-cell counts on cls/spr object arms are thin (1–2 postings per
  cell) — per-cell conversion CIs are wide; hull-pooled reads are
  reported alongside.

## §7 Measured vs inferred vs hypothesis

- **Measured:** all census numbers (n and cell sets on every table);
  posting/reach from `summary.json`.
- **Inferred:** any statement that a specific early object *drove* a
  posting — we measure co-occurrence (early event present + posting) and
  excursion flags, not counterfactual causality.
- **Hypothesis:** threshold readings (e.g. "events below N takers never
  precede a posting") are observational over landed seeds, not declared
  engine behaviour.
