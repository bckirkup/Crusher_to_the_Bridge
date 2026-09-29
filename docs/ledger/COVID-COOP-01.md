# COVID-COOP-01
**Date:** 2026-09-29
**Commit:** ada0f4a1
**Pathogens:** sars_cov2_resp
**Status:** open

Sourced bounds for a packet-resolved cooperative dose law on
`sars_cov2_resp` — the mechanism under which the far-field pool carries
PCR-detectable load but cannot initiate infection because no carrier
particle delivers the multi-virion packet a non-independent-action law
requires. Literature pass via Consensus (2026-09-29); no sim numbers in
this entry. **Bias flag (declared):** 2020–22 airborne-risk conclusions
rest on an independent-action inference layer (RNA copies → infectious
dose → risk); instrument *measurements* are used as evidence, *risk
conclusions* drawn under one-virion-one-chance are treated as
non-evidence for mechanism.

**Granularity statement (the design input):** the quantity the mechanism
needs is the *packet distribution* — complete, viable virions per carrier
particle at deposition — not the accrued host-level dose field, which
cannot express the mechanism. Carrier occupancy is set at emission and
modified by viability decay in flight; at deposition each carrier lands
as one packet on a microscopic mucosal patch, so local per-cell
multiplicity ≈ packet occupancy, not zone-average density.

## Bound 1 — genome copies per infectious unit (deflator)

**Declared widest interval: 10³–10⁶ copies per infectious unit. Graded
interior: 3×10³–3×10⁴.**

Zapata-Cardona et al. 2022 (Iranian J Microbiol; Results/Discussion):
PFU:RNA 1:29 800 (D614G), 1:11 700 (Alpha), 1:8 930 (Gamma), 1:12 500
(Delta), 1:2 950 (Mu); cites prior range 10³–10⁶:1. Grade B — in-vitro
isolates, Vero endpoint assay, variant-dependent. Despres et al. 2022
(PNAS; Results): genome:PFU 10³:1–10⁶:1 on 162 clinical swabs; SARS-1
~360:1; Delta/Epsilon higher FFU:RNA than Alpha. Grade B.

*Structure caveat (recorded, not a bound):* PFU/TCID50 is an
endpoint-dilution *event* presupposing independent action — under a
cooperative law the "infectious unit" may itself be a collective packet,
so this divisor bounds copies→infection-event, not copies→viable-virion.

## Bound 2 — genomically-complete fraction of emitted virions

**Unbounded — declared assumption pending.** DVGs ubiquitous in vitro and
in autopsy lung (Zhou et al. 2023, mBio); DI particles selected at high
MOI (Girgis et al. 2022, Comm Biol); symptomatic > asymptomatic DVG
abundance (Zhou cohort reanalysis). No retrieved paper measures the
complete-genome fraction in *emitted aerosol* virions — two phrasings
returned DVG biology, not emission fractions: `?nr-term`. If
cooperativity requires n *complete* virions, packet occupancy divides
further by this fraction — strengthening far-field starvation,
unquantified.

## Bound 3 — emitted packet field (carrier rates × RNA loading)

**Derived packet loading ~0.004–0.1 RNA copies per emitted carrier
across median-to-p95 emitters — the RNA-bearing class is ~1 virion per
carrier; multi-virion packets live in the >30 µm class.**

Archer et al. 2022 (Interface Focus; Results + Table 2): breathing 3–20,
speaking 40–100, singing 70–200 particles/s (25–75% ranges); ventilation
5–26 L/min. Grade B. Coleman et al. 2021 (CID; Table 3): 63–5 821
N-copies/activity, 85% of load ≤5 µm, 2/13 participants = 52% of total;
cultures negative. Grade B. Alsved et al. 2022 (single case): 90% of
exhaled RNA <4.5 µm, peak 0.94–2.8 µm. Grade C (n=1). Li et al. 2024
(Building & Environment): multi-virion aerosols via discrete compound
(stuttering) Poisson in a generalized Wells–Riley — the >30 µm class
carries the multi-virion packets; Anand et al. 2022 (Sci Rep):
double-Poisson carriers×occupants. Grade C as constants — the functional
form is the asset.

Arithmetic: median singing ~714 copies/15 min against ~10⁵ emitted
particles → ≲0.01 copies/carrier; supershedder class ≲0.1 on the <5 µm
class. The uniform soup of isolated virions is the measured loading —
PCR-visible RNA mass in few carriers among many empty.

## Bound 4 — cooperativity at the cellular scale

**Graded envelope: n\* ≈ 2–5 complete virions per target cell, anchored
on the measured VSV cellular-Allee optimum ~3. Widest envelope: any
n ≥ 2 (declared; the challenge-law exponential is the n = 1 limit).**

Andreu-Moreno et al. 2018 (Curr Biol; Results incl. Fig 2 text): VSV
aggregates — per-capita first-cycle progeny peaks at cMOI ≈ 3, every
cMOI>1 beats cMOI=1, a cellular-level Allee effect, cell-type and
innate-immune dependent. Grade B — other virus, direct mechanism
measurement, the n* anchor. Peterson et al. 2025 (bioRxiv **preprint**):
HCMV infected-cell frequency grows faster than linear with inoculum;
same signature HIV, vaccinia; absent TMV-on-leaf. Grade C — preprint;
supplies the test statistic (faster-than-linear infectivity vs per-cell
dose). Sanjuán 2017 (Trends Microbiol), 2018 (Curr Opin Virol):
collective-infectious-unit reviews. Grade C (secondary).

**SARS-CoV-2 per-cell MOI curve: not found** after two phrasings →
`?nr-term` on coronavirus. Baggen et al. 2023 (Cell, TMEM106B) is
*receptor-level* cooperation — recorded so it is not misread as
virion–virion cooperativity. The row terminates at family-level
stand-ins, same convention as VULN-01's α bound (229E challenge fits).
Bottleneck literature measures *genetically distinct founders*, not
particle-level collectives — a droplet of n same-genome virions reads
founder = 1; the mechanism is invisible to it, not excluded by it.

## Bound 5 — viability decay (the window a packet has to reach a cell)

**Graded interior: ~50–60% infectivity lost <5 min; ~90% by 10–20 min;
near-instant loss at RH < 50%. Widest: half-life seconds–minutes to
~1 h (matrix/RH dependent).**

Oswin et al. 2022 (PNAS; Results): levitated 5–10 µm droplets, ~1
virion/droplet; →~10% by 20 min, most loss <5 min; RH < 50% near-instant
50–60% loss; four variants similar. Grade B. Pan et al. 2026 (EST Lett):
direct-to-cell deposition ~100× more PFU than settle-into-medium — ~2
log10 loss <10 min without fast cell contact; regrades all air-sampling
culture-negatives ~2 log conservative. Grade B.

The disagreement, measured: PCR+ air common at 10²–10⁴ copies/m³ (Ong et
al. 2021: 179–2 738/m³, all cultures negative despite
viability-preserving sampling; Birgand et al. 2020 JAMA Netw Open
review: pooled ~10³–10⁴/m³, 7/81 cultures+, all close-environment) vs
the outlier positive (Lednicky et al. 2020: viable 2–4.8 m out, 6–74
TCID50/L, gentle VIVAS) and early-infection positives (Kitagawa 2022).
Cooperative reading: ~10³ copies/m³ → ~500 copies/h inhaled →
~0.05–0.5 infectious units/h of sub-cooperative singles — PCR-visible,
uniform, sub-threshold; near-field wet droplets deliver packets inside
the seconds-long viability window. Both literatures right: PCR+ is the
soup, culture+ is the packets.

## Bound 6 — deposition geometry (secondary)

Extrathoracic capture of the 1–3 µm RNA class is small and disputed:
CFPD nasal efficiency 0.2–1% (1 µm) / 1–6% (2.4 µm) / 6–12% (5.5 µm) vs
ICRP HRTM 2.5–5.5% / 13–25% / 47–68% (Dey et al. 2025, Sci Rep; Results).
~10× disagreement on ET capture >0.5 µm; the small class largely transits
to bronchial/pulmonary. Grade B for the spread's existence, C for either
bound's value. For the mechanism the consequential geometry is upstream:
per-cell MOI at the patch = packet occupancy, not the receiving region.

## What this buys the model

1. The mechanism is expressible **without cellular-resolution state** —
   as carrier-packet loading: emission draws per-packet complete-virion
   count (stuttering-Poisson by droplet class; occupancy = droplet
   volume × matrix titre), Bound 5 decay applies to packet contents in
   flight, the cooperative law acts on per-packet per-cell MOI at
   deposition — not on the accrued field.
2. Declared uncertainty divides into: copies→infectious-unit
   (10³–10⁶, interior 3×10³–3×10⁴), complete-genome fraction
   (unbounded), cooperative order n\* (2–5, wider ≥2), decay window
   (measured), packet loading (derived; instrument target).
3. The instrument task stands, now justified: emit per-epoch × route
   packet-size structure — whether any far-field packet ever exceeds
   ~1 complete virion — before any dose-law A/B spends an array.

## Gaps recorded

- SARS-CoV-2 per-cell MOI curve: `?nr-term` (two phrasings;
  receptor-level cooperativity excluded as different sense).
- Complete-genome fraction of emitted virions: unbounded (`?nr-term`).
- Lednicky 2020 TCID50/L back-calculation unresolved on chunks —
  flagged, not taken as a bound.
