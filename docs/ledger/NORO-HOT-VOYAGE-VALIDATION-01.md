# NORO-HOT-VOYAGE-VALIDATION-01
**Date:** 2026-11-24
**Commit:** #1415
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** e14f5bf3

Validation synthesis, no new cells: the user reframed the target as
"~99.5% of voyages cold is correct; what matters is that the ~0.5%
hot cruises transmit through the right routes at the right final AR."
This entry scores the model's hot-voyage structure on the three
checkable numbers that reframing implies. Inputs: the 60 artifacts of
noro_external_sequester_01 + noro_carrier_distribute_01 (post-hoc), the
NORO-DOSE-REFIT-01 measured ignition chain (spirit/mega, 120 voyages),
tranche-42's prevalence cross-check, and the 162-posting surveillance
record in `docs/norovirus/cross_hull_outbreak_evidence.csv`.

## 1. The ignition chain, decomposed (measured)

Per-voyage ignition is a product of independent gates:

| gate | value | source |
|---|---|---|
| import census per voyage | classic ~0.24% of complement (1–7 per 1910); spirit 6.97/voy; mega 16.35/voy — same ~0.23–0.24% rate on all hulls | measured, artifact `imports` |
| P(vomiting axis \| import) | 0.111–0.124 | NORO-DOSE-REFIT-01, 60+60 voyages |
| P(emits in window \| axis) | ~0.54 | same |
| **P(emits \| import)** | **0.062–0.067** | same |
| P(≥1 emesis event \| voyage) | ~26% at classic census; measured 10/20 (incl. hot) on the 8000–8019 cohort | composed + measured |

The low per-import figure is structural, not a defect: in a stationary
prevalent sample only ~4% of illness-destined infections board inside
the presymptomatic window (`presymptomatic_share_of_presenting` 0.04 —
the ~1–2 day window over Atmar's 28-day detectable duration), the other
96% board convalescent with their vomiting already done on land, and
29% never symptomatic at all. Per-import on-board vomiting probability
≈ 0.71 × 0.04 × 0.72 ≈ 2% at the axis gate, before the in-window emit
and schedule-count draws. **Cold is the correct default state** — the
measured emesis timing is not "too late": when events occur they land
at epoch 5–16 of 288 (day 1–2). 10 of 18 cold cohort cells simply have
zero emesis events all voyage.

## 2. Frequency: what the composite implies

- Harness prevalence (~0.24%) sits inside the renewal-consistent
  literature range (0.14–1.64%, tranche-42 finding C) — but an order
  below the adopted boarding-axis interval [2.5%, 4.0%], which
  tranche-42 showed inconsistent with community incidence. **The
  frequency answer is entirely hostage to which prevalence is real**;
  the question is documented open, not resolved here.
- Events are common, establishment is rare: on the classic cohort,
  ~half of cold cells see ≥1 emesis event, but small chains die
  (crossing cells reach σ 1.4–13, most chains <10 secondaries).
  NORO-DOSE-REFIT-01 measured the same wall on spirit/mega: 22/60 and
  42/60 voyages ignite, **0/120 post** — growth never compounds past
  ~13 concurrent there. Yet the classic cohort's two hot cells *do*
  compound (136–193 secondaries). The difference is ignition strength,
  measured in section 3.
- The cohort's hot rate (2/20) is not a frequency estimator — seeds
  are fixed challenge cells, not a prevalence-stratified voyage sample,
  and the strong ignitions are seed-level lotteries. No valid model
  posting-rate estimate exists yet; deriving one requires the
  prevalence resolution plus a supply-event probability, both open.

## 3. The hot cells: AR and routes vs the posting record

Final AR, carrier-R+D arm (n=1910):

| cell | AR | ever infected | secondaries | dominant route tally |
|---|---|---|---|---|
| 8000 | 2.4% | 50 | 45 | common_source_food 29, caregiver 12, fomite 9 |
| 8006 | 10.1% | 196 | 193 | common_source_food 119, fomite 42, caregiver 27 |

Posted record, classic-capacity hulls, norovirus-only postings (n=46):
passenger AR median **5.8%**, IQR [4.5, 8.8]; crew median 1.4%.
Postings are ≥3%-threshold events by construction.

- 8006 (10.1%) lands just above the passenger IQR top — plausible-hot,
  moderately heavy.
- **8000 (2.4%) would not post at all** — it is a sub-threshold hot
  cell: transmission sustained, AR below the surveillance floor.
  Sub-threshold propagation is real-world consistent (CDC publishes
  sub-threshold events of significance), but it means the cohort's
  "hot" label straddles the posting definition.
- **Both hot cells are food-dominated** in route tally — including
  8006, which is emesis-patch-driven in mass terms (1.24e9 GEC patch)
  yet still attributes most infections to common_source_food. The
  user's "leaning too hard on one kind of supply" is confirmed in the
  route ledger: person-to-person amplification (fomite/caregiver/
  direct) is present but secondary in count. The investigated-record
  comparison (Rispens 2020: supply origin with onboard propagation;
  duration evidence against single-exposure-only) says real postings
  are mixed supply+propagation — the model's food dominance share has
  never been scored against the propagation share evidence.

## 4. Verdict against the reframed target

| question | answer | confidence |
|---|---|---|
| 99.5% cold correct? | Structurally yes — the per-import vomiting chain makes cold the correct default; but the actual hot frequency is unmeasurable until the prevalence inconsistency (tranche-42) is resolved | measured structure, open magnitude |
| hot cruises transmit how? | Food-dominated in both hot cells, with real but secondary fomite/caregiver propagation; emesis amplifies mass but food attributes the infections | measured on 2 cells — small n |
| final AR right? | In range: 10.1% vs posted IQR [4.5, 8.8]; one hot cell sub-threshold at 2.4% | measured, n=2, seed-lottery |

## 5. What this does not settle (open inputs to the next decision)

1. **Prevalence resolution** — tranche-42's three-way inconsistency is
   the single largest lever on hot frequency; until it resolves, no
   posting-rate comparison is meaningful.
2. **Supply-event probability** — common_source_food dominates hot-cell
   transmission, but the per-voyage probability of a contaminated lot
   is a seed lottery never validated against supply-chain evidence
   (the `supply_seed_scan_01` / `supply_solver_screen` line is the
   measured start of this).
3. **Propagation-share scoring** — food-vs-propagation split has no
   frozen criterion; the posting/investigation record could supply one.
4. Held seeds 8105/8106 remain unused; the classic cohort's
   168-vs-288-epoch manifest asymmetry is not relevant here (this
   cohort ran 288 throughout).
