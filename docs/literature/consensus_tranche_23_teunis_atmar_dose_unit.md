# Tranche 23 — the norovirus dose unit: what Teunis's 18 is, why the ~100× aggregation fork costs nothing, and the span the two challenge studies actually leave open

**Register rows fed / supersession.** This tranche feeds the norovirus
`dose_response.alpha` / `beta` row of §3.1 of
[`docs/parameter_provenance_register.md`](../parameter_provenance_register.md)
and the `#43`-norovirus paragraphs of
[`../norovirus/norovirus_open_ledger.md`](../norovirus/norovirus_open_ledger.md).
It supersedes three things recorded there:

1. the **≈925 genome copies per infectious aggregate** bridge, which was posed as
   `16,644 / 18` and was therefore circular. It is **withdrawn** and replaced by
   a number read from a published figure caption: Kirby et al.'s pooled
   aggregation-corrected fit reports **µ_c = 517**;
2. the **~100× aggregation fork** — the possibility that reading the 18 as
   aggregates rather than copies moves this arm's dose axis by two orders of
   magnitude. **Retracted** (the retraction is the user's; §4 shows the
   arithmetic behind it rather than asserting it);
3. the reading that Atmar's **logistic family** is what separates 1,320–2,800 gEq
   from 16,644. §5 removes it: an *exact beta-Poisson* refit of Atmar's own data,
   published by the authors of the model this arm uses, lands at ≈1,660 gEq.
   The gap survives the change of family, so the genogroup argument in the
   ledger — not the family argument — is what holds the refusal to refit.

**Status:** evidence assembled, **one interval declared and nothing applied**.
No profile value changes; `alpha` stays 0.111 and `beta` stays 32.81. The one
in-tree edit is a **unit correction to a profile note**, which called Teunis's 18
"RT-PCR units" — it is not one — and asserted `acquired_particles` is "in model
units" without qualification; the corrected note keeps the model unit and records
that its commensurability with genome copies is not established. Neither edit is
a value. Every dose figure in this repository remains void pending a
refit, and the refit is after the gate (plan §9), not here.

**Scope:** task #43, item C6 of
[`../proposals/defect_resolution_plan.md`](../proposals/defect_resolution_plan.md).
C6 was filed as a question to send to a collaborator: *is the Teunis Table III
ID50 of 18 stated in genome copies or in aggregates?* It is answered here from
the published exchange instead, and the question is withdrawn rather than sent.

---

## 1. The quantity, and why the unit is the whole question

The shipped pair `alpha = 0.111`, `beta = 32.81` is a beta-Poisson (beta-frailty
hit) dose-response whose argument is a **dose**, and the engine feeds it
`acquired_particles`. Nothing in the pair says what one unit of that dose is.
Three candidate units appear in this literature and they differ by ~3 logs:

| Unit | Where it comes from |
|---|---|
| RT-qPCR **genome copies** / genomic equivalents (gEq, GEC) | how both challenge inocula were quantified |
| **RT-PCR units** | Atmar's dosing unit; **1 unit ≈ 400 gEq** (Atmar 2014, Results) |
| **aggregates** (clumps of virions) | Teunis's aggregation-aware branch, which reports infectivity *per single infectious particle* |

If the axis is copies and the shipped N50 is ~16.6k copies, the arm is one thing.
If the axis were aggregates, the same N50 would be a ~500–900× larger dose in
copies, and every route-efficiency figure downstream of it would be off by that
factor. That is the unit trap that produced the withdrawn 3.7× genogroup ratio,
which is why it was filed as an external question.

## 2. Method, and what was not retrieved

Consensus MCP, unfiltered, full-text chunks requested on every query. Queries as
issued, with negative results recorded so they are not repeated:

| # | Query | Outcome |
|---|---|---|
| 1 | *Norwalk virus dose response beta-Poisson alpha beta aggregation ID50 genome copies Teunis 2008 secretor positive* | Teunis 2008 surfaced, **abstract only, no body or table chunks**. Kirby 2014 letter returned with body chunks and its Figure 1 caption. Schmidt 2015 and Messner 2014 returned as the reanalysis literature |
| 2 | *aggregated Norwalk virus inoculum Se+ subjects 50% infectious dose 1015 genome copies 2.6 aggregated particles completely disaggregated virus ID50 18 viruses* | Teunis 2008 again **abstract only**; Atmar 2014 body chunks including the Discussion paragraph that characterises Teunis's 18–1,015; Ramesh 2020 secondary restatement |
| 3 | *Reply to Kirby Teunis Norwalk virus infectious dose Atmar letter genomic equivalents assumptions differing amounts of virus aggregation* | Atmar et al.'s **Reply to Kirby et al.** retrieved (DOI 10.1093/infdis/jiu382) — the whole letter, which is shorter than most abstracts |

Route switch for Atmar 2014: Europe PMC's `fullTextXML` endpoint returned no
body, and the PMC HTML at `PMC3952671` did. Its Methods, Results, Table 2 and
Discussion were read from that HTML.

**`?nr` — Teunis et al. 2008 Table III and Results were not retrieved.** Two
Consensus queries by quantity *and* unit returned the abstract only, and the
article is paywalled (*J Med Virol* 80:1468–76, DOI 10.1002/jmv.21237); Europe PMC
holds no body for it. Per the sourcing protocol this is a **retrieval state, not
a null**: the numbers are in the paper, we have not read them there. Everything
below that depends on Table III's row structure is therefore carried at **Sec**,
and §7 states what a primary read would settle.

## 3. What each number is, where it was read, and its grade

| Quantity | Value | Source | Origin | Grade |
|---|---|---|---|---|
| Table III has three 8fIIa fits — (a) no aggregation `α=0.111, β=32.81`; (b) aggregation-aware `α=5.35e-3, β=2.51e-3` + aggregation parameters; (c) 8fIIa+8fIIb pooled `α=0.040, β=0.055` + aggregation parameters — and the shipped pair is **row (a)** | — | Edison bundle (collaborator analysis of the Teunis/Atmar exchange), relayed 2026-09-05 | **Sec** | secondary analysis |
| The 18 belongs to Teunis's **Results prose**, not to row (a): the aggregated inoculum in Se+ subjects gives ID50 **1,015 genome copies ≈ 2.6 aggregated particles**, and completely disaggregated virus gives **ID50 = 18 viruses** | 1,015 gEq / 18 | Edison bundle, quoting Teunis 2008 Results | **Sec** (Teunis body itself **?nr**) | secondary analysis |
| HID50 for **disaggregated** virus from Teunis's data = **18.2 GEC, 95% CI 1.03–4,350 GEC**; Atmar's "ranged from 18 to 1015 gEq" is an oversimplification | 18.2 GEC | Kirby, Teunis & Moe, *J Infect Dis* 2014 (DOI 10.1093/infdis/jiu385), letter body | **R** (letter) | B — reported by the model's own authors, about their own data, in a letter rather than a fitted paper |
| Exact beta-Poisson refit of **Atmar's** data, no aggregation: **α = .28, β = .58**, residual deviance 1.63. The caption **does not state the dose unit** of that fit | — | Kirby 2014, **Figure 1 caption** | **F1** (caption text, not digitized) | B for the pair; the unit is **inferred** here, see §5 |
| **Pooled** Atmar+Teunis exact beta-Poisson with aggregation correction: **α = .024, β = .017, µ_c = 517**, deviance 15.71 | µ_c = 517 | Kirby 2014, **Figure 1 caption** | **F1** | B |
| Teunis's 8fIIa dose groups: **3/9 infected at 3,240 gEq, 0/9 at 324, 0/8 at 32.4** | — | Atmar et al., **Reply to Kirby et al.**, *J Infect Dis* 2014 (DOI 10.1093/infdis/jiu382), letter body | **Sec** (Atmar restating Teunis's data) | B |
| Atmar's own characterisation of the 18: "**18 genomic equivalents (gEq), determined using assumptions about differing amounts of virus aggregation between their 2 challenge pools**", which Atmar contends the data do not support; and "models without aggregation assumptions are the most reasonable ones to use and report" | — | Reply to Kirby et al., letter body | **R** (letter) | contested claim, recorded as contested |
| HID50 **3.3 RT-PCR units ≈ 1,320 gEq** (secretor-positive blood group O/A), **7.0 ≈ 2,800 gEq** (all secretor-positive); 95% CIs **1.1–9.4** and **1.4–62.5** units by Fieller's theorem, i.e. ≈**440–3,760** and ≈**290–25,000** gEq; **1 RT-PCR unit ≈ 400 gEq**; B/AB secretor-positives wholly uninfected | 1,320 / 2,800 gEq | Atmar et al. 2014, *J Infect Dis* 209:1016–22 (DOI 10.1093/infdis/jit620), **Results** "Infection status" + **Methods** "Statistical analysis" (logistic regression, Fieller CIs) | **R**, **Me** | B — GI.1 challenge in healthy adults; this arm is GII |
| Challenge doses administered: **4,800, 48, 4.8, 0.48, 0 RT-PCR units** | — | Atmar 2014, **Table 2** | **T2** | B |
| Teunis "reported an HID50 estimate that ranged from 18 to 1015 gEq depending on their modeling assumptions"; no person given ≤324 gEq was infected | — | Atmar 2014, **Discussion** | **R** | B, and superseded on the 18 by Kirby's letter |

The two letters are **letters**: peer-reviewed correspondence in *JID*,
reporting fits their authors do not report anywhere else. They are graded B and
carry an `R`/`F1` origin for numbers read in their own text, and `Sec` where they
restate another paper's data.

## 4. Arithmetic, recomputed here, and the ~100× fork

All of the following was computed in-repo against the shipped pair, not taken
from any source. The exact form solves `1 − ₁F₁(α; α+β; −D) = 0.5`; the closed
form is `β·(2^(1/α) − 1)`.

| Quantity | Value |
|---|---|
| Exact (confluent hypergeometric) N50 at α=0.111, β=32.81 | **16,643.78** dose units |
| Closed-form N50 at the same pair | **16,871.14** dose units (+1.4%) |
| P(infection) at D = 18, exact / closed form | **0.0475 / 0.0474** |
| P(infection) at D = 324 / 1,320 / 2,800, exact | 0.234 / 0.339 / 0.391 |
| `10^dose_reference_log10` = `10^4.23` | 16,982 — the profile's own N50, to 2% |

`D = 18` therefore sits at **P ≈ 0.047** on the shipped curve, nowhere near 0.5.
Pairing "ID50 = 18" with row (a) is arithmetically impossible, whatever unit the
18 is in; the two belong to different rows of the same table.

**Why the aggregation fork costs nothing at our parameters.** Take Kirby's
pooled aggregation-corrected fit, whose three parameters are published in the
Figure 1 caption: α = .024, β = .017, µ_c = 517. Its exact N50 is **1.85
aggregates**, and 1.85 × 517 = **954 genome copies** — within **6%** of the
1,015 gEq Teunis reports for the aggregated inoculum. So the aggregation branch
and the copy branch are the *same dose in two units*, and µ_c is the bridge
between them. The ~100× fork is retracted, and this is the arithmetic behind the
retraction: an aggregate-unit axis does not move the dose by two orders of
magnitude, it re-expresses it. (`β·(2^(1/α)−1)` for that pair is ~5.9×10¹⁰ and
is meaningless — the closed form is not valid at α ≪ 1, which is a second reason
the live path uses the exact form.)

**The 925 is withdrawn.** It was `16,643.78 / 18 = 924.65`, which reproduces the
N50 it was derived from and confirms nothing. The published aggregate-size
parameter is **517**, from a caption, and it is not a copies-per-aggregate figure
for *our* row: it belongs to the pooled fit (c-like) with its own α and β, not to
row (a). Row (a) has no aggregation parameter — that is what "no aggregation"
means.

**What stays unverified.** Whether Teunis's Results sentence says "18 viruses"
(single virions under a hypothetical fully disaggregated inoculum) or 18 gEq is
carried at **Sec** only: Edison's bundle reads it the first way, Atmar's reply
reads it the second, Kirby's letter writes it as 18.2 **GEC**, and we have not
read the sentence. It is recorded as **contested in print and unread here**, not
as settled. Nothing in this document depends on which reading is right: row (a)
is the shipped row, it has no aggregation parameter, and its N50 is 16.6k in the
unit its own inoculum was quantified in.

## 5. The unit question is closed; the gap is not, and it is not a family artefact

**Closed:** the dose axis of row (a) is **genome copies (gEq/GEC)**. Both
inocula were quantified by RT-qPCR in copies; Kirby's letter states plainly that
Atmar's data "can be readily fitted to the published dose response model,
assuming there is no inoculum aggregation", which is the same assumption as row
(a) and the same unit; and Atmar's reply agrees that the two studies give "very
similar estimates … using dose-response models that do not make assumptions
about virus aggregation". No aggregate-unit reading of row (a) survives that.

**Not closed, and now harder:** the ledger previously explained away the
5.9–12.6× distance between Atmar's 1,320–2,800 gEq and row (a)'s 16,644 partly
by noting that Atmar fits a **logistic** model, so importing its ID50 would
change the dose-response family. That explanation is removed by Kirby's Figure 1
caption. Refitting Atmar's data in the *exact beta-Poisson* family — same family
as row (a), same no-aggregation assumption, fit by the model's own authors —
gives α = .28, β = .58, whose exact N50 recomputed here is **4.16 dose units**.

The caption does not name that fit's dose unit, so the conversion is an
**inference, graded C, and labelled as one**: Atmar dosed in RT-PCR units at
≈400 gEq per unit, and 4.16 **RT-PCR units** is ≈**1,660 gEq**, which reproduces
Atmar's own logistic HID50 pair (1,320 / 2,800) to well inside its CI, whereas
4.16 **gEq** would be an N50 below every dose Atmar administered and below the
doses at which Atmar observed zero infections. The unit check is what identifies
the unit; a primary read of Kirby's methods would replace the inference. Either
way family and value move together and the answer does not change: **on Atmar's
GI.1 data the beta-Poisson N50 is ~10× below row (a)'s.**

What remains as the reason not to retarget α/β is therefore the **genogroup**
argument, which is unchanged and is stated in the ledger: Atmar 2014 challenged
**GI.1**, this profile's declared genotypes are GII.4/GII.17/GII.2, and the GII
challenge evidence runs the *other* way (Rouphael 2022 GII.2 ID50 5.1×10⁵ GEC,
≈30× **above** 16,644). Two GI.1-versus-GII comparisons pointing in opposite
directions do not identify a value; they bracket one. Plus the standing boundary:
the refit is after the gate.

## 6. What is declared

**The dose axis span, no-aggregation branch, in administered genome copies:**

| | Value | Basis |
|---|---|---|
| Lower bound | **1.32×10³ gEq** | Atmar 2014 logistic HID50, secretor-positive blood group O/A, Results (Fieller 95% CI ≈440–3,760 gEq) |
| Interior points | 1.66×10³ gEq; 2.80×10³ gEq | Kirby's exact beta-Poisson refit of Atmar's data (caption fit, N50 recomputed here, unit inferred per §5); Atmar's all-secretor-positive HID50 (CI ≈290–25,000 gEq) |
| Upper bound | **1.69×10⁴ gEq** | row (a)'s own closed-form N50, 16,871 (exact form 16,644) |
| Shape | `logU` | 1.1 logs wide, four estimates inside it, no interior preference the evidence supports |
| Grade | **B** | every endpoint is a human challenge measurement, none of it in this arm's genogroup and none of it shipboard |
| State | **declared, not applied** | it is a *span between two studies*, not a measurement of one quantity; it exists so the #36 screen and the #37 admissible-region test see the 6–13× disagreement instead of absorbing it |

**Recorded, not swept — the aggregation branch.** Teunis's aggregated ID50
1,015 gEq ≈ 2.6 aggregated particles; disaggregated 18.2 GEC (95% CI 1.03–4,350
GEC, Kirby); pooled aggregation-corrected fit α = .024, β = .017, µ_c = 517.
These are commensurable with the branch above only through µ_c, which belongs to
a different fit than the shipped row, and the disaggregated figure is contested
in print by Atmar's reply on the strength of Teunis's own 0/9 at 324 gEq and 0/8
at 32.4 gEq. Recorded so it is not re-derived; **not** an interval endpoint.

**Not declared:** any single dose figure, any change to α or β, any conversion
of the span into a point, and any use of the span to move an anchor. The 18 is
not an endpoint of anything here.

## 7. What would move this

- A **primary read of Teunis 2008 Table III and its Results paragraph** — which
  would replace every `Sec` in §3, settle the "18 viruses" versus "18 gEq"
  wording, and say whether row (a) is the row we think it is. Route: the
  publisher PDF or an institutional copy; chunk retrieval has been exhausted at
  two queries and is a `?nr`, not a null.
- Any **GII.4 challenge dose-response**, which would end the genogroup bracket
  by measuring this arm's genogroup instead of interpolating between GI.1 and
  GII.2.
- The **refit itself**, after the gate, at which point the span in §6 becomes the
  prior box rather than a declaration.

## 8. What C6 was, and what it is now

C6 was "ask Edison whether the Teunis Table III ID50 of 18 is in aggregates" and
was flagged as the item with external latency. It is **withdrawn rather than
sent**: the published exchange between the two teams answers the part that
matters (the axis is copies; the 18 is not row (a)'s ID50; the aggregation
branch re-expresses the dose rather than moving it), and the part it does not
answer — Teunis's exact wording — is a paywall problem, not a question for a
collaborator. The collaborator analysis that prompted this is cited above as
**Sec**. Its *modelling recommendation* — abandon 0.111/32.81 and refit to an
ID50 of ~2,800 gEq — is **advice, not adopted**: it is a refit, it is before the
gate, and it selects a point inside exactly the span this program exists to keep
open.
