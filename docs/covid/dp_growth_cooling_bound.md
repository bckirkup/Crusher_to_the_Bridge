# DP record growth bound — how much cooling the conditioned arrays must deliver

**Status:** measured (record-side cited; model-side measured at `1dfac0e4`)
**Purpose:** convert "the model is too hot and fast" into a quantified target for the
SUSCEPT-V1 / HEAT-V1 conditioned arrays, and name the discriminating observables
that decide between the two remaining mechanism classes (susceptibility ceiling
vs suppression truncation).

## 1. Record side — the real Diamond Princess growth

| Quantity | Value | Source |
|---|---|---|
| First confirmed onset aboard | 22 Jan 2020 (day 2) | Kakimoto, Eurosurveillance 2020 (PMC7403638) |
| Pre-quarantine shape | low for ~2 weeks, acceleration late Jan | same |
| First crew onset | 1 Feb (day 12) — crew lag ~10 d, dominates confined tail | same |
| Infection-incidence peak | **2–4 Feb (model days 13–15)** — i.e. AT confinement | Mizumoto, J Clin Med 2020 (backcalculation, 199 dated cases) |
| Confined-phase transmission | cabin-sharer + working crew only; ~0 cross-cabin | PMC8046742 |
| Onboard R₀ estimates | **2.28** (Rocklöv, J Travel Med); **3.27–4.73** (Emery, PLOS One, serial interval 5–6 d, incl. crew-mediated quarantine arm); 14.8 (Zhang SEIR fit, high outlier — itself predicted only 79% attack) | as cited |
| Implied daily multiplier | **~1.15–1.27×/day** at serial interval 5–6 d | derived from above |
| Yokohama outdoor RH during quarantine | median 73% hi / 40% lo; marine-HVAC indoor est. ~30–45% | Yamagishi, EID 2020 (PMC7454703) |

The real epidemic was **mid-growth when confinement fired**: incidence peaked
within ±2 days of the Feb 5 order, then declined into a subcritical
cabin/crew tail.

## 2. Model side — measured ramp (D0 baseline arms, θ = 2.37e11, SHA 1dfac0e4)

| Seed | ramp multiplier/day | onset peak day | infections | recorded |
|---|---|---|---|---|
| 20200205 | 1.61 | 8 | 3,577 | 1,981 |
| 20200206 | 2.20 | 11 | 3,589 | 3,539 |
| 20200208 | 1.80 | 9 | 3,586 | 2,316 |
| 20200209 | 1.87 | 20 | 2,877 | 2,757 |
| 20200212 | 1.94 | 19 | 3,095 | 3,008 |
| 20200213 | 1.73 | 16 | 3,558 | 3,544 |
| 20200214 | 1.63 | 19 | 3,309 | 3,237 |

**Median ramp: ×1.80/day (r ≈ 0.59 d⁻¹)**; onset-curve slope ≈ infection-
incidence slope under a stationary incubation delay. SOP-017 (day 16) lands
on the decaying shoulder: `infections_before_quarantine` ~3,570 vs `during` ~7
— suppression is post-burn, never load-bearing.

## 3. The gap

- **Rate:** model ~1.8×/day vs record ~1.2×/day — ~1.5× too hot per day,
  i.e. effective reproduction ~4–6× the mid-range record estimates (2.3–4.7).
  The model sits in the regime of the single high literature fit (14.8),
  which itself predicted 79% attack — less than the model's ~96%.
- **Size math that rules out rate alone:** homogeneous-mixing final size at
  R 2–4 is 80–98%. **No slowdown-only arm can land [712,960] ≈ 19–26% of
  3,710.** The record requires either:
  - **A. susceptibility ceiling** — effective susceptible share ≈
    **0.24 ± 0.07** → `ship_graph.immune_fraction` ≈ **0.70–0.80**
    (or the equivalent reach ceiling from structured mixing);
  - **B. truncation** — per-day growth cooled to ~1.15–1.25 (combined
    pooled-route force cut roughly **×0.12–0.25**), so that day-16
    confinement lands pre-peak and the confined cabin/crew chains produce
    the observed tail;
  - **C. a mix** (partial ceiling + partial cooling).

## 4. Discriminating observables (all already in the cell payload)

| Signature | Pool-ceiling winner | Truncation winner |
|---|---|---|
| `infections_during_quarantine` / `during_quarantine_by_*` | ~0 — pool exhausts fast, confined stratum stays starved | dominant stratum — long subcritical tail |
| `during_quarantine_by_zone_class` | same mix as pre-quarantine | cabin + crew-mess/galley concentrated |
| `crew_onsets_after` vs passengers | flat role mix | crew-skewed tail (record: crew onset lag ~10 d) |
| `onset_curve` at day 16 | smooth decay | visible kink at confinement |
| before_share | stays ~0.6+ (fast burn among susceptibles) | moves toward 0.173 |

A SUSCEPT-V1 immune-depth arm that lands the truth band but keeps
before_share ≈ 0.6 and ~0 confined infections is the ceiling signature —
and it would mean the timing leg still needs a second mechanism
(cooled growth or retimed suppression). A HEAT-V1 route-cooling arm that
lands the band will necessarily carry the truncation signature.

## 5. Reading note

- Anchors unchanged: 197 recorded onsets, before_share 0.173 ± 0.10,
  infections band [712,960]. The R₀ literature is a *range*, not a bound:
  the mid-range estimates (2.3–4.7) are the honest target; the 14.8 fit is
  recorded as the outlier regime the model currently reproduces.
- RH is not the missing coolant on the record: outdoor median 40–73% and
  inferred indoor ~30–45% RH make the shipped `airborne_half_life_hours`
  1.1 (~40% RH lab value) plausibly honest; it survives as a sensitivity
  corner only.
