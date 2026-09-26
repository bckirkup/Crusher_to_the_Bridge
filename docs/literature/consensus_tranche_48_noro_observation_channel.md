# Consensus tranche 48 — norovirus observation-funnel literature checks

**Register rows fed / supersession.** None. Every quantity retrieved here is
a *check* read against ratios the shipped observation channel emits in
`NORO-CHANNEL-01` (`docs/ledger/NORO-CHANNEL-01.md`); per AGENTS.md none of
them may enter `fitted_against` and no constant is tuned to them.

**Method:** Consensus MCP (`search`, `include_full_text_chunks: true`,
`page_size` 3–5), five queries, 2026-09-25/26. Quantities are graded with
the repo's convention — **[E]** a number the paper estimates from data,
**[M]** a modelled/derived quantity, **[?nr]** needed but not retrieved —
and quoted with the locus where the figure was read.

## 1. Asymptomatic fraction of norovirus infections

Direct readings, share of *infected* that stays asymptomatic:

- **Challenge studies (Kirby 2016, PLoS ONE; Table 1 + Results text):**
  GI.1 Norwalk — 20 ill of 25 infected (ill share **0.80**); GII.2 Snow
  Mountain — 9 ill of 15 infected (**0.60**); GII.1 Hawaii pilot 2/2 ill
  (**1.00**, n=2 descriptive only). Illness share of infected across
  challenge studies ≈ **0.60–1.00 [E]**; equivalently asymptomatic share
  **≈0–0.40 [E]**, consistent with the v2 priors' "67–100% [E]".
- **Natural outbreaks with universal testing (Miura 2018, J Epidemiol;
  abstract + Results):** asymptomatic ratio **0.321 [E]** (95% CI
  0.277–0.367) across 55 foodborne outbreaks, all involved individuals
  PCR-tested; GII.4 stratum **0.407 [E]** (0.328–0.490). This is the right
  denominator (share of *infections*, not share of tested contacts).
- Context only, different denominator: outbreak *prevalence among tested
  asymptomatic contacts* — Wang 2024 (China meta) 17.6% [14.1–21.3],
  Wang 2023 (global meta) 21.8% [17.4–27.3] [E]. Do not compare these
  against a per-infection fraction.

**Check band:** asymptomatic share of infections **0.20–0.40 [E]**
(challenge ∪ natural-outbreak union, favoring Miura's denominator).

## 2. Share of the ill who report to the ship infirmary

- **Passengers (Wikswo 2011, CID; abstract + Results):** one high-morbidity
  cruise norovirus outbreak with a passenger questionnaire — 236 met the
  AGE case definition, **95 (40%) had not reported to the infirmary**;
  capture **≈0.60 [E]** among case-definition-ill passengers. This is the
  same elicitation the v2 priors cite; it bounds the *AGE-eligible,
  symptomatic-aboard* rung, not all symptomatic infections and not all
  infections.
- **Crew capture fraction [?nr]:** no retrieved paper quantifies the share
  of ill crew who present. Two indirect constraints: Dahl 2005 (Int Marit
  Health) documents crew sick *presenteeism* — crew consultations high,
  sick leave low, presenteeism promoted aboard — i.e. crew under-reporting
  pressure is real but unquantified; Freeland 2016 (MMWR) + Jenkins 2021
  (MMWR MIDRS) count *reported* cases only and show crew AGE rates
  comparable to passenger rates (crew 21.6 vs passenger 22.3 per 100k
  travel-days, 2014) — a reported-rate comparison, not a capture fraction.
  **Treat any crew-vs-passenger reporting ratio the model emits as
  unidentifiable from this literature.**
- VSP case-definition context (Crisp 2023 MMWR; Jenkins 2021): reportable
  AGE = ≥3 loose stools/24h or vomiting plus one other symptom, and the
  counts are *reports to medical staff* — MIDRS counts the channel's
  output, never the infection denominator.

**Check band:** infirmary capture among syndrome-eligible symptomatic
passengers ≈ **0.4–0.8 [E]** (single point estimate 0.60 widened for
single-outbreak uncertainty); crew [?nr].

## 3. Onset-dating practice in VSP GI records

- VSP outbreak investigations do carry a per-case **illness onset date**:
  Crisp 2023 (MMWR, January 2023 GII outbreak) reports its epi curve
  "Cases of acute gastroenteritis (N = 410), by illness onset date" across
  five consecutive voyages — onset is recorded per reported case and spans
  pre-arrival dates, i.e. onset can precede the report and even the voyage
  boundary. Jenkins 2021 confirms the denominator structure: all MIDRS
  counts derive from cases *reported to ship medical staff*.
- **Onset dates exist only for cases that reported.** No retrieved source
  describes imputation or back-dating of onset for unreported cases; the
  dated-onset population is by construction a subset of reported cases.
  Precision of the recorded onset (same-day vs recalled) is not quantified
  in retrieved text — mark **[?nr]** for any finer claim than "per-case
  onset date is recorded for reported cases, including pre-boarding
  onsets".

## What this tranche does not do

It supplies comparison bands only. `NORO-CHANNEL-01` reads the shipped
funnel against §§1–3; a measured ratio outside a band diagnoses the
channel, never re-tunes a constant to land inside it.

## Retrieval log

| # | Query focus | Papers used |
|---|---|---|
| 1 | asymptomatic share of infections, challenge studies | Kirby 2016 |
| 2 | asymptomatic ratio, natural outbreaks | Miura 2018; Wang 2023, 2024 (context) |
| 3 | ill→infirmary capture, cruise | Wikswo 2011; Mouchtouri 2024 |
| 4 | crew reporting behaviour | Dahl 2005 (qualitative); Freeland 2016 |
| 5 | VSP/MIDRS practice incl. onset dating | Jenkins 2021; Crisp 2023 |
