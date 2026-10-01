# Tranche 50 — SARS-CoV-2 partial immunity, 2020 window: cross-reactive *recognition* is licensed, *protection* is not — verdict `recognition_only_no_protection`


**Register rows fed.** This tranche feeds §3.2's `Secretor / innate
nonsusceptibility` row (the non-susceptible fraction, updated from
"correct by argument" to "correct by argument + measured null under the
2020 window") and adds two rows to §3.2: a **pre-existing cross-reactive
recognition fraction** (licensed as an interval, recognition only) and an
**age-dependent susceptibility multiplier** (licensed shape: continuous,
peaking in the elder bands). No shipped constant changes; nothing in this
tranche is a value the engine consumes today.

**Status:** Retrieval-only session. Evidence assembled and interpreted
against the surviving declared suspect class ("frailty tail × partial
protection") after all seven conditioned axes measured-retired and
SUPPRESS-V1 returned `suppression_incapable` at 630/630 cells (axis floor
~1,121–1,197 infections at the deepest corner, ~160 over the band top 960;
before_share floor 0.51 vs the record's 0.173). **No engine change, no
array, no anchor fitting, no COMBINED-V1 decision.**

**Declared evidence window (declared before searching, per the prompt):**
primary window = **2020-season** — papers published 2020-01-01 through
2020-12-31 (`year_min=2020, year_max=2020`). Probe of the **strictly
pre-DP window** (literature published before the Diamond Princess
quarantine era, `year_max=2020, month_max=2`) is recorded at §1. For the
DP replay only *pre-existing* immunity is in scope: within-voyage immunity
development is ~2 weeks of a ~5-week record and the question is what
fraction of the boarding pool was already non-susceptible.

**No candidate was selected, ranked or rejected by what its value would
do to the Diamond Princess band, before_share, or any scored anchor.** The
~15% bound check in §7 is arithmetic *on* the retrieval result, not a
selection criterion.

## 1. The strict window returns ∅ a priori — and that is the honest answer

**Strictly pre-DP** (published before ~1 Feb 2020) the SARS-CoV-2
immunity literature does not exist, and could not: the virus was
sequenced in mid-January 2020, Grifoni's T-cell megapool paper was
*received* by Cell in April, Braun's in April (published 29 July), the
first observational acquisition studies (Sagar, Gombar, Anderson) in the
autumn. A month-filtered query (`year_max=2020, month_max=2`) returns
exactly what that window contains: in-silico epitope *predictions* (Ahmed
2020, *Viruses*, DOI 10.3390/v12020254 — SARS-CoV-immunology-derived
vaccine targets, not a measurement of immunity in humans) and pre-2020
SARS-CoV-1 memory literature (e.g. Liu 2016). Every item the strict query
surfaces that *measures* SARS-CoV-2 immunity is a mid-2020 paper the
date filter passed loosely — the corpus confirms there is nothing
earlier to find.

So under a strictly pre-DP window the answer to every question in this
tranche is ∅. **The 2020-season window is therefore the operative one**,
and everything below is read inside it. This is itself a finding about
the surviving mechanism class: a "2020 population was partially immune"
hypothesis has to be licensed by what 2020 measured, and §4 is what it
measured.

## 2. Queries, verbatim

Run against `mcp_tool(server="consensus", tool_name="search")`,
`include_full_text_chunks: true` on every call, `page_size` 5–6.

1. `SARS-CoV-2 cross-reactive CD4 T cells unexposed healthy blood donors percentage common cold coronaviruses` — window 2020.
2. `pre-existing cross-reactive T cells protection against SARS-CoV-2 infection acquisition exposed household contacts remain uninfected` — window 2020. Returned the recognition corpus (Le Bert, Mateus, Lipsitch, Schulien, Ogbe, Tan): the corpus's answer to "protection" in 2020 *is* the recognition literature.
3. `age-dependent susceptibility SARS-CoV-2 children adolescents lower odds infection contact tracing estimated susceptibility by age` — window 2020.
4. `SARS-CoV-2 rechallenge rhesus macaque after primary infection protection reinfection dose neutralizing antibody` — window 2020.
5. `SARS-CoV-2 immunity cross-reactive T cell protection susceptibility` — strict-window probe (`year_max=2020, month_max=2`); §1.
6. `Davies age-dependent effects transmission control COVID-19 epidemics susceptibility children lower than adults model estimate` — window 2020; identity-targeted, the "Davies class" reference in the prompt.
7. `cross-reactive SARS-CoV-2 antibodies unexposed healthy donors binding antibodies spike endemic coronavirus no neutralization pre-pandemic sera` — window 2020; the B-cell half of Q1.
8. `prior endemic common cold coronavirus infection associated with protection SARS-CoV-2 susceptibility disease severity observational evidence` — window 2020; the direct acquisition-protection test.
9. `exposed seronegative individuals resist SARS-CoV-2 infection abortive transient infection pre-existing memory T cells high-risk contacts` — window 2020; second phrasing of the protection question, per the ≥2-attempt rule before recording a null.

## 3. Recognition — licensed, as an interval

A substantial fraction of never-exposed adults carries SARS-CoV-2-reactive
adaptive immunity. That is measured, repeatedly, in the target population:

| Layer | Fraction of unexposed | Source |
|---|---|---|
| T-cell (CD4+, peptide pools) | **~0.20–0.60** | Grifoni 2020 (*Cell* 10.1016/j.cell.2020.05.015) ~40–60%; Braun 2020 (*Nature* 10.1038/s41586-020-2598-9) 34–35% spike-reactive; Le Bert 2020 (*Nature* 10.1038/s41586-020-2550-z) ~30–50% N/NSP; Weiskopf ~30%; Mateus 2020 (*Science* 10.1126/science.abd3871) memory-CD4+ cross-reactive, reports the 20–50% class; synthesis "20–50%" (Sette & Crotty 2020, *Nat Rev Immunol* 10.1038/s41577-020-0389-z), "20–81%" across assays incl. low-avidity and naive-phenotype cells (Bacher 2020, *Immunity* 10.1016/j.immuni.2020.11.016); counterweight Woldemeskel 2020 (*JCI* 10.1172/jci143120) 1/21 seronegative donors |
| Antibody (S-reactive IgG) | **~0.05–0.23** | Ng 2020 (*Science* 10.1126/science.abe1107) **5.29% (16/302)** uninfected adults, S2-targeting, neutralizing-capable in those few; Anderson 2020 (medRxiv 10.1101/2020.11.06.20227215) ~23% non-neutralizing cross-reactive binding; Song 2020 (bioRxiv 10.1101/2020.09.22.308965) minimal/no S-reactive sera in 36 pre-pandemic donors and **zero neutralizing cross-reactive mAbs** (one S2 exception); Sekine 2020 (*Cell* 10.1016/j.cell.2020.08.017) pandemic-era healthy donors carried ~2× more memory-T-cell than antibody responses |

Source attribution is established 2020 work: the cross-reactivity derives
from endemic HCoV memory (OC43/HKU1/NL63/229E — Mateus's epitope-level
demonstration), with Le Bert's NSP7/NSP13 arm pointing partly at
non-endemic betacoronavirus conservation. Bacher adds the honest caveat:
a share of the "reactive" cells in unexposed donors are naive-phenotype,
not memory — the recognition interval is heterogeneous in quality, not
just in magnitude.

**What is licensed: a recognition interval, ~[0.20, 0.60] T-cell and
~[0.05, 0.23] antibody, in unexposed adults.** Grade B — measured in the
right population for the wrong quantity (recognition, not protection).

## 4. Protection — ∅lit, and it is a measured null, not an unretrieved one

Two differently-phrased protection queries (2 and 9) plus the direct
acquisition query (8) converge on the same answer: **no 2020 publication
shows pre-existing cross-reactive immunity blocking or reducing
SARS-CoV-2 acquisition in humans.** The window did not fail to look —
the papers that *measured acquisition* exist inside it, and they read
null:

- **Sagar 2020** (*JCI* 10.1172/jci143380): documented prior endemic-CoV
  infection → **similar rate of SARS-CoV-2 acquisition** (explicit), with
  less-severe COVID-19 among those infected. Disease mitigation, not a
  non-susceptible fraction.
- **Gombar 2021** (*Diagn Microbiol Infect Dis* 10.1016/j.diagmicrobio.2021.115338,
  2020 work): documented seasonal-CoV history → **similar infection rate
  AND similar severity** — "does not provide immunity to subsequent
  infection", the strongest single-sentence negative in the window.
- **Anderson 2020** (medRxiv): the ~23% carrying cross-reactive
  antibodies were **not** protected from infection or hospitalization —
  a direct A/B on 252 PCR-confirmed cases vs controls.
- **Bacher 2020** (*Immunity*): "argue against a protective role for
  CCCoV-reactive T cells" — the one 2020 experiment designed on the
  protective hypothesis reports against it.
- **Meyerholz 2020** (*JCI* 10.1172/jci144807, commentary on Sagar):
  "No differences … in terms of susceptibility to SARS-CoV-2 infection."
- Review-level state, same window: Sette & Crotty — the implication for
  protection "still await[s] … actual data"; Lipsitch 2020 (*Nat Rev
  Immunol* 10.1038/s41577-020-00460-4) treats herd-level effects as
  unresolved.

**The sole positive acquisition association anywhere in the window is
Aran 2020** (*J Infect* 10.1016/j.jinf.2020.10.023; 869,236 insured):
recent common-cold diagnostic codes → OR **0.76** (0.75–0.77) for a
positive SARS-CoV-2 PCR — a claims-data proxy the paper itself says
"cannot attribute … to cross-immunity", absent in under-18s, and a *leaky
relative-risk* rather than a non-susceptible fraction even if credited.

The abortive-infection literature does not rescue this. Gallais 2020
(*EID* 10.3201/eid2701.203611) seronegative intrafamilial contacts with
cellular responses, and Sekine's seronegative exposed family members, are
**post-exposure** observations — they cannot distinguish immunity that
prevented infection from immunity the exposure generated. The studies
that do answer the protection question prospectively (Swadling's HCW
abortive-infection cohort, Kundu's household-contact readout) are
2021–2022 publications: **outside the declared window, and their absence
from 2020 is the finding.**

**Verdict on the fraction: ∅lit.** A pre-existing *non-susceptible*
fraction has no licensed value — not "not retrieved": retrieved,
measured, and read null. If a frailty-tail × partial-protection
structure proceeds, its immunity half is a **declaration**, and that is
now on the record rather than assumed.

## 5. Age-dependent susceptibility — licensed shape is a continuous multiplier, and it is adverse on this hull

The "Davies et al. 2020 class" question has a clean answer: the 2020
literature supports a **continuous susceptibility-by-age multiplier, not
a binary non-susceptible fraction**:

- **Davies 2020** (*Nat Med* 10.1038/s41591-020-0962-9): fitted
  age-structured model over six countries; susceptibility under 20 ≈
  **half** that of over-20s.
- **Ayoub 2020** (*Global Epidemiology* 10.1016/j.gloepi.2020.100042):
  decade ladder relative to 60–69y — 0.06 (≤19), 0.34 (20s), 0.57 (30s),
  0.69 (40s), 0.79 (50s), **1.00 (60–69)**, 0.94 (70–79), 0.88 (≥80).
- **Viner 2020** (*JAMA Pediatr* 10.1001/jamapediatrics.2020.4573;
  32 studies, contact-tracing subset): pooled OR **0.56** (0.37–0.85)
  for a child vs adult to be an infected contact.
- Goldstein 2020 (*JID* 10.1093/infdis/jiaa691): consistent direction.

Two consequences for the DP replay, recorded rather than softened. First,
every estimate is a **relative multiplier on a susceptible host** — none
of them implies anyone is unsusceptible; the literature's mechanism is
graded susceptibility (likely immune-maturation/ACE2-class arguments), so
what it licenses is a *multiplier surface*, the opposite functional form
from a protected fraction. Second, on an **elder-skewed pool** the
licensed multiplier runs the wrong way to help: susceptibility *rises*
through the bands DP's population concentrates in (Ayoub's peak is
exactly 60–69y). An age axis applied to this hull raises effective
susceptibility against a young reference, not a partial-immune floor.

## 6. Sterilizing vs leaky — undefined for pre-existing immunity; graded where protection exists at all

For **pre-existing cross-reactive** immunity the question is moot under
this window: with no acquisition protection measured (§4), there is no
protection whose functional form to classify. What the window does say
about the *form* of coronavirus protection:

- Post-infection macaque rechallenge reads **near-sterilizing at matched
  high dose, early after primary infection**: Deng 2020 (*Science*
  10.1126/science.abc5343), Chandrashekar 2020 (*Science*
  10.1126/science.abc4776), Bao 2020 — no detectable dissemination on
  day-28 rechallenge with the same strain.
- McMahan 2020 (*Nature* 10.1038/s41586-020-03041-6) makes that
  protection **level-graded**: antibody-threshold-dependent, CD8
  depletion partially abrogates it — i.e., protection where it exists is
  dose-of-immunity-dependent (leaky at low titer), not all-or-none.
- Huang 2020 (*Nat Commun* 10.1038/s41467-020-18450-4), systematic
  review of coronavirus challenge data: neutralizing-titer-stratified
  protection and higher inoculum → more disease — the same graded shape
  in the homologous-CoV challenge setting.

So the licensed *shape* for any partial-immunity arm is **leaky/graded**,
not a binary non-susceptible switch — which is itself in tension with the
~15%-non-susceptible form the bound needs (§7).

## 7. Bound check — the ~15% and before_share arithmetic, recorded without softening

- **Count bound.** Pulling the deepest corner (~1,121–1,197) under the
  band top (960) needs roughly a 15% reduction in effective susceptibles.
  The retrieval licenses **no** non-susceptible fraction (§4 ∅lit), so the
  required value is unsourceable — and even the window's most generous
  protective *association* (Aran OR 0.76, leaky-form, non-attributable)
  is a ~24% relative-risk reduction, not a 15% binary floor. A binary
  15% non-susceptible pool cannot be licensed; a leaky ~20%-off-risk
  proxy is neither licensed-for-mechanism nor the right functional form.
- **Timing bound (before_share 0.51 vs 0.173).** A *time-constant*
  susceptibility floor rescales the pool uniformly — it cannot move
  *when* in the voyage the recorded mass sits. Recorded as a bound:
  no constant-susceptibility structure, licensed or declared, addresses
  before_share at all; only a mechanism with time dependence (suppression
  dynamics, exposure geometry, observational channel) can.

## 8. What this tranche licenses

1. A **recognition interval** in unexposed adults — T-cell ~[0.20, 0.60],
   antibody ~[0.05, 0.23] — Grade B (right population, wrong quantity).
   Registered as a measured fraction of *recognition*, never of
   *non-susceptibility*.
2. A **measured null for protective (non-susceptible) fraction**, ∅lit:
   the 2020 window searched, measured, and read null. Any
   partial-protection arm constant is thereby *declared*, which the
   register now says explicitly.
3. A **continuous age-susceptibility multiplier** — licensed shape,
   adverse direction on an elder-skewed hull; supports a multiplier
   surface, not a non-susceptible fraction.
4. A **graded (leaky) protection form** as the only form protection
   takes anywhere in the window — no all-or-none pre-existing
   fraction anywhere.

**Not licensed, and deliberately not done:** no fraction adopted into any
field; no engine surface implied; no use of Aran's proxy association as a
constant (non-attributable by its own statement); no verdict on whether
COMBINED-V1 proceeds — that decision is the lead's, now with the
immunity half's provenance settled.

## 9. The nulls, stated plainly

- **No 2020 evidence that pre-existing cross-reactive immunity prevents
  or attenuates SARS-CoV-2 acquisition in humans** — measured null across
  three independent observational designs (Sagar, Gombar, Anderson), not
  a retrieval miss.
- **No binary non-susceptible fraction anywhere in the window** — every
  quantitative statement is a multiplier or a leaky relative risk.
- **No measurement linking the ~15% class to any licensed quantity** —
  the recognition interval overlaps the bound only if recognition equaled
  protection, which the window's own studies measured and rejected.
- **Strict pre-DP window: ∅ a priori** — no SARS-CoV-2 immunity
  measurement could exist before ~Feb 2020; the corpus's earliest real
  items are April–May 2020.

**Verdict: `recognition_only_no_protection`.** The immunity half of the
surviving combined-structure class is a declaration, not a mechanism;
and the timing bound stands — a time-constant susceptibility floor
cannot move before_share regardless.
