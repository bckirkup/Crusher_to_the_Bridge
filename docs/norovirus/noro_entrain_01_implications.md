# NORO-ENTRAIN-01 implications — where the anchor gap actually lives

> **Status:** Measured — the §2 decomposition is computed from the 27,048
> landed `summary.json` members plus a 311-voyage full-census pass over every
> posted voyage, all at engine `dbbd5395` under
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_entrain_01/`.
> Companion to [noro_entrain_01_readout.md](noro_entrain_01_readout.md); the
> readout scores the design's §6 clauses, this document orders what they imply
> for the next design. Not a design freeze.

## 1. The gap is three different failures, not one

The anchor target has three independent legs and the campaign separated them:

| anchor leg | result | where it sits |
|---|---|---|
| Posting rate 0.4–0.9% (cls/spr) | Reachable — but only via import mass (bc80 in-band on spr; cls bc40 in-band) | denominator, not mechanism |
| Burst signature on postings | Not reachable — posted burst48 at rest level on every object arm (0.375–0.43 vs 0.400 rest); only `ind` postings burst (0.521) | propagation timing |
| Posted-conditional pax AR 0.04–0.10 | Not reachable on any arm including `ind` (med 0.003–0.035) | resolved below — **not** upstream of cs in the transmission sense |

## 2. Measured step-1 reads (from the landed zips, zero new voyages)

### 2.1 Acquired-vs-reported AR — the AR gap is not transmission

`infection_attack_rate_passenger` (true infections, all courses) vs
`reported_case_attack_rate_passenger` (what the wire emits), medians on the
full 27,048-cell fleet:

| hull | infected pax AR (all cells) | infected pax AR (posted cells) | reported pax AR (posted cells) |
|---|---|---|---|
| exp | 0.073 | 0.082–0.119 | 0.011–0.035 |
| cls | 0.093 | 0.032–0.124 | 0.003–0.034 |
| spr | 0.094 | 0.070–0.109 | 0.008–0.022 |

Acquired infection is **in or above the 0.04–0.10 band on essentially every
voyage of every arm** — posted or not, `off` included. Transmission is not
the constraint on the AR leg.

### 2.2 The reporting-wire funnel — where infections die out

Per-cell medians of the summary-level funnel fields (all 27,048 cells):

| stage | exp | cls | spr | ratio |
|---|---|---|---|---|
| ever infected pax | 23 | 124 | 198 | — |
| ever ill pax (presentation ≥ mild) | 3 | 20 | 33 | **ill/infected ≈ 0.13–0.17** |
| reported cases pax | 2 | 14 | 22 | **reported/ill ≈ 0.65–0.70** |

On posted cells the wire is nearly perfect: reported/ill ≈ 0.78–1.00. The
observation chain loses the cases **before** the wire — ~85% of infections
never reach a symptomatic presentation (the `ever_ill` axis: presentation ∈
{mild, symptomatic, severe}), and of the ~15% that do, the wire already
captures most.

This is consistent with the profile as declared, not obviously a defect:
`illness_probability` is the dose-conditional Teunis Hill (η 0.508, γ 0.095)
and `severity_model.base_probabilities` puts 80% of courses on
asymptomatic/subclinical rungs where `syndrome_case_eligibility` is 0/0.55.
But it creates a measured tension worth naming: the profile's own notes cite
adult challenge-cohort symptomatic shares ~0.71 (children ~0.365), while the
fleet realizes ~0.15. The two are reconcilable only if delivered doses sit
low on the Hill — which is itself the discriminating measurement (§3.2).

### 2.3 Source-magnitude signature on posted voyages (311-voyage census)

Early objects (seeded ≤48h) on posted voyages, by `source_kind`:

- **Composition:** `ind` postings are provisioned-lot-dominated (early
  objects 89% lot on exp, 53% cls, 43% spr). Every object arm — `ship`,
  `a_ext`, `a_thin`, `bc*`, `bi*`, `bmix` — posts on an ill-handler-dominated
  mix (~60–77% handler, ~20–35% diner) with **1–2 provisioned_lot objects
  per posted voyage at most**. The lot channel that drives `ind` postings is
  nearly absent under the object grammar.
- **Per-object reach:** `ill_diner` objects carry the largest taking (median
  47 servings, p90 622); `provisioned_lot` median 19, p90 57; `ill_handler`
  median 0 (most handler objects never serve). The `ind`-vs-object
  difference is **channel composition**, not per-object magnitude — lots are
  not uniquely big; they are uniquely present under v1.
- **Voyage max early takers** on posted bc* cells reaches 576–1,128 on
  cls/spr — import-sourced diner/handler objects *do* mint huge exposure
  events; they still don't convert to bursts. Exposure size is not the
  binding term for propagation either.

## 3. Revised implication tree

### 3.1 Branch 1 — excursion → posting (the posting mechanism leg)

Early events exist on ~every voyage (P(early) 90–100% cls/spr); conversion
to posting stays at `ship` rates (~0.2%) on every object arm. The two facts
that order the remaining tests:

1. `a_thin` cut per-window mass ~3× and conversion moved **in neither
   direction** — per-window dose is not binding within ±3×.
2. Posted `ind` voyages ride `provisioned_lot` objects that the object arms
   barely mint; posted object-arm voyages ride import-sourced people.

The declared **`cs_extent` redraw arm** remains the discriminating test —
iso-dose, concentrated into `ind`-like cadence — but §2.3 reframes what it
discriminates: if the redraw recovers `ind`-like posting, the axis is
**cadence-with-lot-minting** (the v1 spike's coupling to the lot channel),
not cadence alone. A cheap pre-check: census the unposted cells for
`provisioned_lot` mint rates per arm — if object arms mint lots at `ind`
rates but they never drive postings, the channel-presence story dies.

### 3.2 Branch 2 — infection → reported case (the AR leg, resolved to the wire's input)

Resolved to first order: the binding term is **infection → symptomatic
presentation** (~0.15 measured; Hill + severity prior as declared), then
ill → reported (~0.7 fleet, ~0.9 posted). Sub-branches left:

1. **Dose-position audit (readout-side, no engine).** Join acquired
   infections to their credited doses (census `dose`/`patch` rows — a new
   parse pass; the scan tool reads `hosts[]` + the common_source tail only)
   and compute expected presentation under the declared Hill vs the realized
   ~0.15. If realized ≈ Hill expectation, subclinical dominance is a
   faithful consequence of delivered-dose magnitude and the question moves
   to why doses are low; if realized ≪ expectation, the presentation draw
   has a defect or a different denominator.
2. **Anchor-semantics check.** The 0.04–0.10 band is *reported ill people*
   per head in real VSP outbreaks. If real outbreaks carry higher
   symptomatic share at higher delivered doses (challenge cohorts use large
   doses), the model may be honest about infection and under-dosed, not
   under-reported — same conclusion as (1) from the anchor side.
3. **Emitted-complement wiring.** Rule out that AR is scored against a
   different denominator than the band intends (complement vs at-risk
   susceptibles) — cheap definitional check.

### 3.3 Branch 3 — posting semantics

bc* bought posting rate via ~95% import-sourced objects — import shadows,
not outbreaks. Any next lever should be scored on posted-with-burst or
posted-with-acquired-source, not raw posting. Unchanged from the readout.

## 4. Ordered next steps

| # | step | cost | resolves |
|---|---|---|---|
| 1 | Dose-position audit: per-acquisition credited dose × Hill expectation vs realized presentation (~0.15) | census re-parse of landed zips, no AWS | Branch 2: dose-realism vs presentation defect |
| 2 | Unposted-cell `provisioned_lot` mint-rate census | census re-parse of landed zips, no AWS | kills or sharpens the channel-presence story under Branch 1 |
| 3 | `cs_extent` redraw arm (declared contract; small engine change + focused sweep) | moderate AWS | Branch 1: cadence-with-lot vs extent |
| 4 | Emitted-complement denominator check | definitional review | Branch 2 residual |
| 5 | Next campaign design freeze | — | only after 1–3 |

## 5. Reproduction

- Summary scan: `tools/noro_diag/entrain_01_scan.py --no-census` over
  `campaign/noro_entrain_01/` → per-cell posting flag, reported and
  infection ARs, complements (27,048 rows, 0 errors).
- Posted census: same tool with `--full-keys` on the 311 posted keys →
  early-object rows (`source_kind`, servings taken, per-window max, pans,
  import/acq source) and `max_early_takers`.
- Funnel fields (`cumulative_ever_infected_*`, `cumulative_ever_ill_*`,
  `cumulative_reported_cases_*`, `sick_call_count`, `campaign_specimens`,
  `campaign_confirmed`) read from `summary.json.summary` by
  `tools/noro_diag/entrain_01_funnel_scan.py` — same ranged member fetch.
- `ever_ill` axis definition: presentation ∈ {mild, symptomatic, severe}
  (`telemetry_buffer/agent_axes.py`); illness vs infection is the
  dose-conditional `illness_probability` Hill plus the severity prior in
  `data/pathogens/active_profiles.json`.
