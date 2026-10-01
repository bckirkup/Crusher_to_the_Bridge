# Tranche 51 — washing is a stochastic practice with a compliance gate, a per-act efficacy family, and a drying tail; routine hand re-loading is activity-tick driven

**Register rows fed.** Binds the constants declared for `NORO-HAND-PRACTICE-01`
(`docs/ledger/NORO-HAND-PRACTICE-01.md`): post-visit wash compliance, routine
(non-bathroom) wash frequency, per-act wash efficacy split by soap use, the
wet-window transfer factor, and the routine self-contact re-loading term. It
**moves no existing constant** — `HAND_HYGIENE_EFFICACY_LOG10` stays as the
authored distribution consumed by the `wash_reuptake`/`spike_decay` baselines
and the profile lever `hand_hygiene_rate_per_hour`; the new arm draws from the
sourced families below.

**Status:** Evidence assembled for the mechanism revision. Implemented in the
PRACTICE-01 change.

**Scope.** RESERVOIR-01's verdict (`still_starved`, occupancy R = 0.132,
ordering unflipped) says delivery works and retention fails: every stool event
ends in a deterministic wash, non-challengeable pickup mass cannot rebuild the
load, and routine rows underflow. What the literature says about the four
gaps: (a) whether every bathroom visit really ends in a wash (compliance),
(b) how much a wash removes (per-act efficacy, soap vs water), (c) how often
hands are washed away from the toilet (routine frequency), (d) what a wet
hand does to a transfer (drying), and (e) what rebuilds the load between
visits (routine self-contact / activity increments).

---

## 1. E0 triage

| Question | Unit that settles it | Retrieved? |
|---|---|---|
| What fraction of toilet visits actually end in a wash? | observed post-restroom wash fraction | **Yes** — §2 (Drankiewicz 2003, Lawson 2019) |
| What does one wash remove? | log10 reduction per act, soap vs water-only | **Yes** — §3 (Hilton 2025) |
| How often are hands washed outside bathroom visits? | events/day, general population | **Yes** — §4 (Machida 2020/2021, Głąbska 2020) |
| Does residual moisture move transfer? | translocated CFU, wet vs dried | **Yes** — §5 (Patrick 1997) |
| What rebuilds hand load between washes? | per-activity log10 increment | **Yes** — tranche 40 §4 (Ram 2011, Pickering 2011), re-read here |
| Field (not lab) wash effectiveness | in-situ LRV | **Yes, and it is much lower** — §3 |

## 2. Compliance — a toilet visit is a *coin-flip* wash, not a wash

**Drankiewicz & Dundes 2003**, *Am J Infect Control* 31:67, restroom
observation of female college students: **63%** washed hands at all after the
toilet, **38%** used soap, only **~2%** washed ≥10 s. Origin: **Ab**.

**Lawson et al. 2019**, *IJERPH* 16:5036,
[10.3390/ijerph16245036](https://doi.org/10.3390/ijerph16245036): 60-day
indirect observation of university public restrooms, pre-intervention:
**51.1%** practiced *basic* compliance (water + soap + dried afterwards);
**7.9%** *adequate* (≥20 s wash and ≥20 s dry). Origin: **Ab**.

**Read:** observed post-toilet wash fractions cluster at **0.5–0.65**, soap
use at **0.4** of washers, and full-duration compliance under 0.1. A
per-host `wash_compliance` drawn U(**0.35, 0.75**) brackets both studies
across settings; a per-act `soap_share` of **0.4** follows Drankiewicz's soap
row. Grade B (observed restroom behaviour, non-cruise population). This is
also the mechanism Liu's post-bathroom column implies: 12.4% positive *after*
bathroom use is the signature of a compliance-gated wash — under a
deterministic wash (RESERVOIR-01) post-visit positivity underflows toward
zero; under no wash it would track routine levels.

## 3. Efficacy — one wash is ~2 log10 with soap, ~1.5 with water; field is far below lab

**Hilton et al. 2025**, *BMJ Global Health*
[10.1136/bmjgh-2025-018925](https://doi.org/10.1136/bmjgh-2025-018925):
systematic review (177 studies) underpinning the WHO community hand-hygiene
guidelines; log10 reductions on hands, community settings. Origins **Ab** /
**R** / **T2** as marked:

| Quantity | Value | Origin |
|---|---|---|
| Viruses, soap + water, summary LRV | **2.03 (95% CI 1.45–2.62)** | Ab |
| Viruses, *plain* soap + water only | 2.42 (0.78–4.05) | R/T2 |
| Viruses, **water only** | **1.55 (0.74–2.35)**, 5 studies | R/T2 |
| Bacteria, water only | 1.54 (0.83–2.24), 8 studies | R/T2 |
| Bacteria, soap + water | 2.19 (1.5–2.87) | Ab |
| Viruses, alcohol-based sanitiser | 1.86 (1.37–2.35) | Ab |
| **Field** studies, soap + water, bacteria | **0.45–0.55** | R/T4 |

Only 4% of the evidence is enveloped-virus; most lab arms seeded MS2/Phi6
bacteriophage — the norovirus-analogue arm is thin by construction, which is
why the per-act draw keeps a wide spread rather than a fitted point.

**Read:** a per-act draw of N(**2.03, 0.5**) clip[0.5, 3.5] for soap washes
and N(**1.55, 0.6**) clip[0.2, 3.0] for water-only washes covers the summary
LRVs and their intervals (sd values are declared spread, not fitted — the
meta-analytic CI is uncertainty over a mean, and the per-act spread is wider
by construction). Grade B (meta-analysis, lab-seeded surrogates). The field
LRV of ~0.5 is the standing liability recorded against this constant — lab
efficacy overstates what a distracted 8-second rinse does.

## 4. Frequency — hands are washed ~5–10×/day total, so most washes are *not* post-toilet

- **Machida et al. 2020**, *IJID*
  [10.1016/j.ijid.2020.04.014](https://doi.org/10.1016/j.ijid.2020.04.014):
  n = 2400 Japanese adults, Feb 2020 — median **5** hand-hygiene events/day
  (IQR 3–8). Origin: **Ab**.
- **Machida et al. 2021**, *Jpn J Infect Dis*
  [10.7883/yoken.jjid.2020.631](https://doi.org/10.7883/yoken.jjid.2020.631):
  n = 2149 — mean **10.2** events/day; per-moment prevalence 30.2–76.4%;
  only 21.1% washed at all five recommended moments. Origin: **Ab**.
- **Głąbska et al. 2020**, *Sustainability* 12:4930 (PLACE-19, n = 2323):
  declared washes/day **3–10** pre-pandemic (68.1%), 6–15 during. Origin: **Ab**.
- Xun et al. 2021 (meta-analysis, *Ann Transl Med* 10.21037/atm-20-6005)
  buckets frequency as ≤4 / 5–10 / >10 per day — the same band. Origin: **Ab**.

**Read:** a norovirus host defecates 1.0–5.63×/day (rows 346/347); total
hygiene ~5–10×/day → **non-bathroom routine washes ~2–8/day**, drawn per host
U(2, 8). Grade C (declared residual of measured totals; pandemic-era
self-reports run high, and cruise-embarked elderly skew is unmeasured).

## 5. Drying — a wet hand transfers ~50–500× more; dry hands barely deposit

**Patrick et al. 1997**, *Epidemiol Infect*
[10.1017/s0950268897008261](https://doi.org/10.1017/s0950268897008261):
hands washed then touched to skin / food / utensils while **wet and undried**
translocated **68 000 / 31 000 / 1 900** CFU; a 10 s cloth + 20 s air dry cut
that to **140 / 655 / 28** — 99.8%, 94%, 99% reductions, i.e. wet:dry ratios
≈ **486× / 47× / 68×**. Origin: **Ab**. (Patrick 2010, *Healthcare
Infection* 10.1071/hi09025 — childcare replication, dual-dry vs usual: 82–96%
reduction — same direction. Origin: **Ab**.)

**Read, with the existing register note:** the shipped
`HAND_TO_SURFACE_LOGNORMAL` is documented at its definition as a
*wet-contact* parameterisation (Tuladhar immediate 13%, Bidawid 13%) — every
contact today behaves as if the hand were wet. Under a drying model, a hand
is wet for a short window after a wash (declared U(**20, 90**) s — Patrick's
residual moisture, no duration series retrieved; Grade C) and dry otherwise,
where hand→surface transfer falls to ~0.5–8% of the wet value (Tuladhar
13%→0.1% in 10 min; Sharps 59%→<1%): dry-state multiplier U(**0.005, 0.08**),
Grade B. The epoch-level deposit multiplier is the wet-share-weighted blend
`wet_share·1 + (1−wet_share)·dry_mult` — no new per-contact draws. The same
blend applies to hand→food and hand→hand deposits (Patrick's food row is a
deposit). The pickup (surface→hand) direction is unchanged: the donor
surface's dryness is already what the pickup distribution was measured on,
and a wet *recipient* hand's uptake gain is plausible but not retrieved —
declared as out of scope.

## 6. Re-loading — routine activity ticks, not one reservoir spike

Tranche 40 §4's increments carry the emission half of this repair:

- **Ram 2011** (mother–infant pairs): within-person hand-rinse titres swing
  **2.0–3.5 log10** over hours on ordinary activity — the load is a state,
  not a host attribute.
- **Pickering 2011** (Dar es Salaam, fecal-indicator bacteria): per-activity
  increments of **~50–6300 CFU** per contact episode (hand-to-mouth,
  food, latrine-adjacent contacts).

**Read:** between bathroom visits a shedding host re-loads its own hands
through continuous self/fomite contact — modelled as a Poisson tick stream
U(**1, 4**)/h, each tick adding `propensity × U(50, 6300)` GEC capped at the
visit ceiling. The propensity coupling is a declared structural choice
(Grade C): a host who does not contaminate hands at the toilet also seeds
its own environment less, so its ticks deliver less — this is what produces
Liu's never-positive tail without a separate "clean subject" flag. The tick
rate band is declared, not measured — Grade C.

## 7. What this predicts on the frozen census (declared before building)

On the RESERVOIR-01 cells (occupancy R criterion, ordering sign, never-
positive share, positive-mean window — criteria frozen in
`docs/ledger/NORO-HAND-PRACTICE-01.md`):

- Ordering **flips**: event rows = contaminate(0.21 mean propensity) ×
  comply(~0.55) × suppress(~1.5–2 log10) → ~10–15% positive; routine rows
  ride the tick equilibrium ~10³–10³·⁵ GEC for high-propensity hosts →
  post-bathroom *below* routine, as Liu measures.
- Occupancy lands between the 0.026 spike-decay floor and a routine-driven
  ceiling — the measured number decides the verdict, not the design.
- SARS-CoV-2's continuous arm gains routine washes (previously zero) — its
  hand reservoir sits below the relaxation ceiling for the first time.

## Sourcing ledger

| # | Query (abridged) | Kept |
|---|---|---|
| 1 | observed post-toilet wash compliance restroom | Drankiewicz 2003, Lawson 2019, Khalish 2025 |
| 2 | handwashing virus log10 reduction soap water systematic review | Hilton 2025 (+preprint twin, same numbers) |
| 3 | water-only handwashing viral LRV (Hilton full text) | Hilton T2 water-only rows |
| 4 | Patrick 1997 residual moisture transfer | Patrick 1997, Patrick 2010 |
| 5 | daily hand-hygiene frequency events/day | Machida 2020, Machida 2021, Głąbska 2020, Xun 2021 |

No query was run to make an anchor come out right; the occupancy criteria
were frozen before these numbers were bound.
