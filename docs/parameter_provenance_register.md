# Parameter provenance register: every quantity, its class, and what blocks its adoption

Status: **register, 2026-09-02. This is the central record.** It is the document
to read before changing any epidemiological constant in any arm, and the document
to update in the same change.

It exists because the answer to "how many parameters are sourced now" was, until
today, only recoverable by reading five tranche documents in publication order
and applying two corrections issued mid-series. That is not a state a
defensibility claim can rest on.

## 0. What this replaces, and what it does not

| Document | Relationship |
|---|---|
| [`norovirus/norovirus_open_ledger.md`](norovirus/norovirus_open_ledger.md) | **Still authoritative** for what is *withdrawn*. Every dose figure is void pending refit; that record stays there. This register does not restate it |
| [`covid/covid_parameter_provenance_audit.md`](covid/covid_parameter_provenance_audit.md) | Absorbed as the SARS-CoV-2 rows of §3. Its §2–§5 arguments are not restated here. Extended by [tranche 9](literature/mql_tranche_9_sars_cov2.md), which cross-checks the arm against the DHS Master Question List. |
| [`norovirus/norovirus_parameter_freedom_audit.md`](norovirus/norovirus_parameter_freedom_audit.md) | Absorbed as §5. Its measurements (the inert dose knob, the 15 observation-model numbers) stand |
| [`literature/`](literature/) tranches 1–19 and the Edison reviews | The evidence behind the Evidence column. Contextual: this register is the index into them, and where the two disagree, the tranche document holds the citation and this one holds the status |
| `formal_spec_v2.md` Appendix A | Superseded as a provenance record. Its source column was the baseline this register was built against |

## 1. Five axes, because each hides what the others cannot say

Provenance class alone was the wrong instrument. Six quantities in §3 have a
citation and *still cannot be adopted*, because the field they would go into
cannot express what the paper measured. The count was seven after tranche 7
measured two quantities the model could not express: norovirus shedding
duration, which had no field at all, and the shedding curve's peak magnitude,
which is mis-genogrouped and not separately identifiable. Tranche 8 removes
the first blocker: `shedding_duration_days` exists, the shedding clock is
separate from the illness clock, and the measured interval is adopted at 15
days (#46). Classifying the remaining blocked quantities as "sourced" would be
the most dangerous entry in the table: it would look like provenance and encode
something the evidence rejects.

**Axis 1 — provenance class.**

| Class | Meaning |
|---|---|
| **M** measured | Direct measurement in the target setting, quantity and units check |
| **B** analogous | Direct measurement in an analogous setting (surrogate virus, different material, different host) |
| **I** inherited | Carried from the upstream Korkin Java model or another pathogen, with no measurement behind the transfer |
| **A** adapted | Derived from a measurement of something else by an unquantified adjustment |
| **C** assumed | No source; a plausible number |
| **P** placeholder | No source and not intended as one |
| **F** free | Available for fitting, by construction |
| **X** construction | Not a measurable quantity — a unit, a convention, a truncation bound |
| **S** scored output | Not an input. Listed only where a value has been mistaken for one |

**Axis 2 — adoption state.** The column that matters operationally.

| State | Meaning |
|---|---|
| **✓ adoptable** | Evidence exists, the field can express it, nothing blocks the change but the work |
| **⊘ field** | Evidence exists; the field's units or shape cannot represent it. Needs a schema or engine change first |
| **⊘ mech** | Evidence exists; the mechanism the field drives is the wrong mechanism. Needs a model change first |
| **⊘ joint** | Evidence exists but the quantity is not separately identifiable — it must be adopted together with another, or swept |
| **∅ null** | Searched, and no measurement of this quantity exists. Must be declared or bounded by argument, not sourced |
| **— in tree** | Already carries a citation in the tree |
| **closed** | Interval + shape + origin + grade recorded; reopened only by new evidence that moves the interval or changes the supported shape |
| **∅def** | Unmeasurable by definition — the denominator is one no assay uses; reopened only by a model change to the quantity's definition |
| **∅comm** | Commensurability null — the two sides are never measured in the same subjects; reopened only by a study measuring both |
| **∅lit** | Searched; no measurement of this quantity exists; reopened only by a new publication |
| **?nr-term** | Ladder exhausted through E3 without retrieval; reopened by a new route or a new paper, never a new phrasing |
| **Tr-class** | Not a journal article at all — VSP posting archive, DHS/industry report; nothing reopens it because it is already at its best available origin |
| **L0** | No leverage on any scored output across the whole interval; reopened by a model change that gives it leverage |

The existing `∅ null` cells currently do the work of three distinct states:
`∅def`, `∅comm`, and `∅lit`. They will be refined by the first pass under
the [sourcing protocol](sourcing_protocol.md), but no existing `∅ null` cell is
re-classified here without evidence for that row. `?nr-term` is reopened by a
new route or a new paper, never by a new phrasing.

**Axis 3 — section of origin.** Where in the paper the number was actually read.
Neither axis above can express it, and the failure mode it catches is the one the
sourcing audit kept finding by hand: a Grade A or class M constant whose only
support is an abstract headline. Two of this register's own corrections were
exactly that defect — the withdrawn emesis titre (Kirby's abstract pools a pilot
its Results exclude) and the withdrawn 3.7× genogroup ratio.

| Code | Meaning |
|---|---|
| **R** | Results (Results prose) |
| **Tn** | Table n |
| **Fn·dig** | Figure n, digitized — state by whom |
| **Me** | Methods (definitions, units, assay, denominators) |
| **Ab** | Abstract only — no body text seen for this number |
| **Sec** | Secondary: a review, or another paper's citation of it |
| **Tr** | Transcribed from a PDF or a non-journal document |
| **?nr** | **not retrieved** — queried by quantity *and* unit and the full-text chunks returned nothing. A retrieval state, never an origin, and never a null result: chunk retrieval is query-relevant rather than exhaustive, so absence here is not evidence of absence |

Three rules, because the column is worthless if they are not held:

- **Only governing citations carry an origin** — the ones that set the shipped
  value, an interval endpoint, or the definition of the quantity. Corroborating
  citations may be summarised (`corroborators: Ab×3`). Format `Author year: code`,
  comma-separated.
- **The weakest governing origin is printed first.** A row governed by an
  abstract reads `Ab` in first position whatever its class and grade.
- **Origin is orthogonal to class and to grade**, and may not be used to move
  either without a separate, stated decision.

Fragments carry the same column, plus the ledger the column is a summary of —
one row per governing citation, with the query that retrieved it, so the reading
is reproducible rather than remembered:

`| Citation | Quantity + unit, as queried | Query string | Retrieval | Section of origin | Verbatim locator |`

where `Retrieval ∈ {chunks, full text opened, transcribed, not retrieved}` and
the locator is the sentence or table row the number was read from, quoted.

The ledger for the current population of this column is
[tranche 21](literature/consensus_tranche_21_full_text_reverification.md) §1,
and the findings the population produced — including the ones this register does
not act on — are its §2. Finding references in Origin cells (`F1`…`F11`) are
that document's numbering.

**Axis 4 — bounds and shape.** The §3.1/§3.2/§3.3 tables add `Interval` and
`Shape`. `Interval` records bounds plus their basis: measured range, pooled CI,
across-study spread, or declared bound. `Shape` records the distributional form
the evidence supports over those bounds. The governing S2 rule is: **never
record an interval narrower than the evidence supports; manufactured precision
is what makes the feasible box go empty, and an empty box from over-narrowing
cannot be told apart from an empty box caused by a wrong mechanism.**

| Code | Meaning |
|---|---|
| `pt` | A single measured value; no spread reported |
| `U` | Uniform over the bounds — the evidence supports the range but not any interior preference |
| `logU` | Log-uniform over the bounds; the quantity spans orders of magnitude |
| `c±s` | Central value with a reported spread (mean ± SD/SEM, median + IQR); state which |
| `skew` | Heavy-tailed or strongly skewed, with the tail side named |
| `set` | A small ordered set of measured values, not a continuum |
| `—` | Not established yet |

**Axis 5 — leverage.** The §3.1/§3.2/§3.3 tables add `Lev`. The leverage
ranking is front-loaded before query spend.

| Code | Meaning |
|---|---|
| `L2` | Moving the parameter across its interval changes whether an anchor verdict passes |
| `L1` | Moves an anchor measurably but does not flip a verdict |
| `L0` | No detectable movement in any scored output across the whole interval |
| `L?` | Not yet ranked |

`L0` is a declaration that requires the perturbation that established it to be
recorded. The new `Interval`, `Shape`, and `Lev` columns are unpopulated:
populating them is the first pass under the sourcing protocol, and no such pass
has run.

## 2. Where the count actually stands

Against the #366/#369 baseline (SARS-CoV-2 8 sourced of 25, norovirus 6 of 35,
influenza 2 of ~25):

| | Count |
|---|---|
| Quantities that had no usable literature basis and now have one recorded | **57** |
| — of those, adoptable as they stand (✓) | 24 |
| — blocked by a field, mechanism or identifiability defect (⊘) | **20** |
| — adopted in the tree | **5** (the FUT2 pair from Wave 1, the influenza `symptomatic_fraction` from R3, the norovirus `emesis_conditioned` airborne mode and interval from R4, and the SARS-CoV-2 `shedding_duration_days` interval from A2) |
| — provenance recovered but mis-genogrouped | **1** (η/γ; the dose-response pair left this row in tranche 6, declared as the GI.1 arm and swept over the GII interval it lies inside) |
| — refuted, or shown to be unmeasurable (∅) | **7** |
| Nulls and rejections recorded as results (§3.4) | 16 |
| Profile scalars carrying a citation **in the tree** | 9 / 7 / 3 |

**These figures are recounted from §3, not incremented**, so they are not
comparable line-for-line with the 33 / 9 / 6 published before sourcing wave 1,
which was maintained by increment. The rule, so anyone can re-derive them: count
the quantity rows of §3.1–§3.3 (75 rows), and exclude 18 — six rows whose
in-tree citation predates the sourcing campaign and was not re-searched
(`incubation` and `presymptomatic_shedding_days` in all three arms), five that
are not quantities at all (the superseded `innate_nonsusceptible_fraction` and
emesis titre rows, the campaign-versus-profile divergence, the curve-selection
defect, the emesis degrees-of-freedom reduction), three declared or
construction inputs (`base_susceptibility` in both arms, secretor/innate
nonsusceptibility), two still unsourced (`airborne_emission_fraction` on the
SARS-CoV-2 arm, `presymptomatic_share_of_presenting`, which is derived from three profile
fields rather than measured), and Edison's proposed influenza
`surface_decay_per_day` key, which is not in the tree — that proposal predates
R1 and is quoted in the fraction spelling it was written in, which no longer
exists anywhere; the tree's influenza field is `surface_decay_log10_per_day`.
That leaves **57**
recorded. Blocked counts a row when its adoption state is a ⊘ state or says
"blocked by", and does not count a row whose state records the defect as
resolved (the former norovirus `airborne_emission_fraction` row and
`surface_deposition_fraction`). Refuted-or-unmeasurable counts a row whose own
adoption state carries ∅ or the word refuted.

R3 moves the influenza presentation quantity from the refuted bucket into the
adopted tree as `symptomatic_fraction`, deleting the dose-conditional mechanism
rather than re-sourcing it; R4 then moves the norovirus airborne quantity into
the adopted tree by redefining it as the event-conditioned interval and plumbing
it per emesis event without selecting a point. A2 then moves the SARS-CoV-2
`shedding_duration_days` row out of the blocked bucket: tranche 8 had built the
field and tranche 9 recorded the evidence, so the only thing missing was the
value on this arm.

Sourcing wave 1 (tranches 11–18) is the largest single move in the table and
it adopts nothing. It adds five §3.1 rows (GII time-to-peak, GII decline shape,
the GII-specific asymptomatic offset, the GII shedding-duration confirmation,
the external voyage denominator), one §3.2 row (copies per infectious unit),
rewrites eight existing rows with measured evidence, and records 16 nulls and
rejections in the new §3.4. It moves `never_symptomatic_fraction`,
`contact_transfer_fraction`, the cabin-localization fraction `f` and the
influenza η/γ pair from unsearched or assumed to searched-and-blocked, and it
found one defect in this register itself: the unsourced "≈ 10³–10⁴ copies"
conversion in the SARS-CoV-2 `dose_response` row, now withdrawn in place. The
in-tree headline is unchanged at 8 / 6 / 2.

Tranche 9 adds three SARS-CoV-2 quantities that now have a basis — the aerosol half-life as an interval, the emission-rate bracket, and the severity ladder — and one new blocked row, `shedding_duration_days`, which exists as a field after tranche 8 but was absent on this arm. Nothing was adopted in tranche 9 itself; the shedding-duration row was adopted later, by A2 (#51), on the RNA-positivity meta-analyses recorded in §3.2.

Tranche 10 adds the norovirus boarding prevalence (⊘ mech: the interval
exists, the importation channel does not) and the paediatric
asymptomatic-offset comparison (⊘ setting), and records the
chronic-shedder boarding prevalence as a bounded ∅. In-tree adoption is
again unchanged.

The last row is the honest headline, and it has moved four times. Wave 1 adopted the
FUT2 pair — `secretor_negative_fraction` 0.20 with
`secretor_negative_relative_susceptibility` 0.20 — by replacing the mechanism
that blocked them, and resolved the naming defect on the two renamed fields
(`route_efficiency_multipliers`, `airborne_emission_fraction`) without sourcing
either. Wave 2 then adopted the identified emesis total and moved surface decay
into its sourced unit. R3 then adopted influenza `symptomatic_fraction` by
deleting the dose-conditional presentation mechanism. R4 then adopted the
norovirus airborne definition and plumbing while retaining the measured
per-event interval rather than selecting a point. The other in-tree changes
from the sourcing campaign remain three screening intervals
(`surface_decay_log10_per_day`, the recut
interval in sourced units, [0.067, 0.79]; `hand_to_surface_drying_multiplier`,
[0.008, 1.0] at a neutral shipped value;
`secretor_negative_relative_susceptibility`, [0.05, 0.50] → [0.04, 0.83],
tranche 6). The remaining gap
is deliberate — adoption is queued behind the mechanism fixes in §4 — but it must
not be reported as progress on sourcing when it is progress on evidence.

## 3. The register

Shipped values verified against `data/pathogens/active_profiles.json` and
`data/pathogens/edison_10pathogen_profiles.json` on 2026-09-02.

### 3.1 Norovirus (`norwalk_gi`) — active

| Quantity | Shipped | Class | Evidence / interval | Origin | Interval | Shape | Lev | State | Task |
|---|---|---|---|---|---|---|---|---|---|
| `incubation` (3 fields) | — | M | Lee 2013, **GII** | Wei 2021: **?nr** — the GSD 1.57 was not retrieved in 2 attempts, and the 5.8 d median matched only in a same-topic COVID incubation meta-analysis whose identity with the cited paper is unconfirmed. Finding **F10** | — | — | L? | — in tree | |
| `presymptomatic_shedding_days` | 0.5 | M | Atmar 2008 | Ip 2017: **Ab** (2 attempts, zero chunks) | — | — | L? | — in tree | |
| `dose_response.alpha` / `beta` | 0.111 / 32.81 | I → **M (form and value)** | The shipped pair is the **disaggregated GI.1 challenge arm** of Teunis 2008, traced by Edison's bundle. Mapped onto α at fixed β = 32.81, the human GII evidence gives **α ∈ [0.072, 0.161]**: Rouphael 2022 GII.2 challenge ID50 5.1e5 → 0.072; Guix 2020 GII outbreak illness ID50 2,934 → 0.154, a *lower* bound on infection α; Ramesh 2020 gnotobiotic-pig GII.4 → 0.149–0.161, Grade C corroboration ([tranche 6](literature/consensus_tranche_6.md) §2). The **aggregation half** of that categorical choice is resolved for this row: the shipped pair is the non-aggregation genome-copy fit, and the live per-agent path has an exact confluent-hypergeometric N50 of **16,644 copies**; the closed-form helper has an approximate N50 of **16,871 copies**, a ≈1.3% gap between the live mechanism and a test-only helper. Both forms return **P ≈ 0.047** at *D* = 18 to three significant figures. The 16,644 live figure is unit-consistent with Teunis 2008 Table III's ID50 of 18 aggregates at ≈925 copies per aggregate, but that bridge is circular: the bundle review posed it as **16,644 / 18**, so 16,643.78 / 18 = 924.65 and 18 × 925 agrees to ≈0.04%; the aggregate reading is **unverified**, not corroborated, and not read off Table III. What would settle it is Teunis et al. 2008's own aggregation parameter or aggregate-size distribution from Table III or the paper's text, independently of any ID50 held here. Atmar et al.'s reply (DOI 10.1093/infdis/jiu382) instead calls the 18 “genomic equivalents … determined using assumptions about differing amounts of virus aggregation,” and Atmar 2014's measured HID50 of 3.3 RT-PCR units (≈1,320 gEq) secretor-positive O/A and 7.0 (≈2,800 gEq) across secretor-positives sits **5.9–12.6× below 16,644** in the same unit, under the framing Kirby, Teunis & Moe (*J Infect Dis* 2015;211(1):166–7, DOI 10.1093/infdis/jiu385) show is statistically rather than biologically distinguishable between the two datasets. Retargeting the pair onto that HID50 is **not adopted, on genogroup**: Atmar 2014 challenged **GI.1**, while this profile's genotypes are GII.4/GII.17/GII.2 and its incubation row is pooled GII, so the GII evidence that brackets α puts Rouphael's GII.2 ID50 5.1e5 **≈30× above** 16,644 while Atmar's GI.1 figure sits 5.9–12.6× below it — opposite directions, and not both about this arm. Were the arm declared GI.1, the matching figure is **2,800, not 1,320**: the tree gates secretor status and **not** ABO, so its secretor-positive agents stand for Atmar's whole secretor-positive cohort across blood groups, whereas 1,320 conditions on O/A hosts this tree cannot separate. Atmar 2014 fits a **logistic** model, so either figure would change family as well as value, and β = 32.81 retains no provenance once the Teunis fit it was taken from is abandoned. **Nothing is adopted and no value changes** | Lin 2022: **R** partial (PFU quantification in body chunks), Xu 2023: **R**; Blaurock / Iyaniwura / Jackson / Killingley / Marc / Rosenke: not re-queried this pass | — | — | L? | ✓ **declared and swept** — 0.111 lies inside that interval and within 3% of its geometric centre (0.108), so it is declared as the GI.1 arm rather than refitted; α is queued into the screen box over [0.072, 0.161] with β held fixed, because family + aggregation assumption + dose unit are one categorical choice. **No profile value changes** | #21 note |
| `illness_probability.eta` / `gamma` | 0.508 / 0.095 | I → **M** | Teunis 2008, same table. The genogroup contrast **cannot be quantified** for this pair either: Teunis 2020's per-copy genogroup figures are aggregate-unit, not disaggregated qPCR-copy ([tranche 6](literature/consensus_tranche_6.md) §3), and Guix's illness ID50 bounds the infection∘illness composite, not η/γ alone | Carrat 2008: **Ab** — 66.9% symptomatic present in the abstract and absent from the three body chunks returned, including the paper's own "Clinical illness" section. Finding **F11**; Teunis: not re-queried this pass | — | — | L? | ⊘ mech — same genogroup mismatch, and no GII-specific η/γ measurement exists to replace it | |
| `secretor_negative_fraction` | 0.20 | B | FUT2 se428 nonsense-homozygote prevalence, European/North American populations ~20% (population genetics, not this setting) | — | — | — | L? | ✓ **adopted** (#21) — demographic input, deliberately outside the screen box | #21 done |
| `secretor_negative_relative_susceptibility` | 0.20 | B | **Genotype-specific**: Kambhampati 2015 pooled secretor:non-secretor odds ratios 9.9 (3.9–24.8) for GII.4 and 2.2 (1.2–4.2) for GII non-4, implying non-secretor relative susceptibility **0.10 (0.04–0.26)** and **0.45 (0.24–0.83)**; the declared genotype mixture GII.4/GII.17/GII.2 straddles both rows ([tranche 6](literature/consensus_tranche_6.md) §4) | Kambhampati 2015: **Sec** (systematic review / meta-analysis, so the pooled OR is by construction secondary) + **R** — both 9.9 and 2.2 retrieved from body chunks | — | — | L? | ✓ **adopted** (#21); screened over **[0.04, 0.83]**, widened from [0.05, 0.50] — the width is **genotype composition**, not measurement error, and the adopted 0.20 sits inside it and is not refuted. Implies a removed-equivalent fraction of 0.20 × 0.80 = **0.16**, the #367 ceiling | #21 done |
| `innate_nonsusceptible_fraction` | withdrawn from `norwalk_gi`; deprecated alias | — | The removed-fraction mechanism is refuted for GII and is no longer the norovirus mechanism. Alias retained (rr = 0.0) so the other bundles in `data/pathogens/` keep loading | — | — | — | L? | — superseded | #21 done |
| **Divergence: campaign vs shipped profile** | campaigns write `innate_nonsusceptible_fraction` | — | `picard_framework/runs/mega_cruise_campaign/campaign_runner.py:988` still writes `innate_nonsusceptible_fraction` into its per-run overrides, so **every campaign run models sterile immunity in a removed fraction** while `data/pathogens/active_profiles.json` models FUT2 partial susceptibility. Behaviour deliberately left unchanged: the campaign *sweeps* the removed fraction, and converting the swept axis to a relative susceptibility is a design decision, not a rename | — | — | — | L? | recorded, unresolved | |
| `shedding_variance_log10` | 1.0 | C | Teunis 2014, 102 subjects, peaks 10⁵–10⁹/g | Schijven 2020: **Ab** + **R** partial (per-hour emission in a body chunk; the emission-rate value itself absent from the chunks returned) | — | — | L? | ✓ | |
| `recovery_day` | 3 | I → **M as an illness duration** | Atmar 2008 measures both in the same 16 subjects: symptomatic illness **1–2 days**, faecal RT-PCR shedding **median 28 days** (13–56). Two independent sources on illness duration (tranche 3 §5) put 3 days inside the illness range | — | — | — | L? | ✓ **implemented as an illness duration only.** The second job moved to `shedding_duration_days` in tranche 8: `illness_clearance_day = onset_day + recovery_day` now ends the *illness* (and the emesis schedule with it), while the infection and its shedding run to the shedding clock. The value is unchanged | #46 done |
| `shedding_duration_days` | **15** | **B** as an interval | Cheng 2021 (77 children, GII): rise days 2–9, decline after day 9, most shedding ceased by **day 15**. Atmar 2008 (GI.1 challenge): median **28 days** (13–56). Kirby 2014 (GI.1 and GII.2 challenge, stools to day 35): both genogroups shed **up to 3 weeks past symptom resolution**. Shipped value **15**, the authored curve's own length and Cheng's cessation day; interval **[12, 30]** ([tranche 7](literature/consensus_tranche_7.md) §3, §6). Not fitted to any scored anchor | Keske 2023: **R** (median culture-positive duration in body chunks) | — | — | L? | ✓ **implemented** (tranche 8). The field is optional and absent means the shedding period equals `recovery_day`, so the COVID arm is unchanged; the norovirus host now reaches all 15 authored curve indices and emits **100.0%** of both authored integrals, against 30.9% symptomatic / 75.0% asymptomatic before. Unblocks #45 | #46 done |
| Curve selection by *current* illness status | symptomatic vs asymptomatic curve re-chosen every epoch | — | — | — | — | — | L? | ✓ **defect, fixed in tranche 8.** Once illness can clear while shedding continues, selecting the curve from `illness == SYMPTOMATIC` silently moved a convalescent host onto the *asymptomatic* curve mid-course. All three selection sites (`get_pathogen_shedding`, `get_pathogen_hand_target`, `strain_shedding_shares`) now select on whether the host ever presented, so the tail read is the tail of the curve the host started on | #46 done |
| `shedding_curve_log10` peak magnitude | 11.0 log10 copies/g | I → **M, mis-genogrouped; GII interval now measured, figure-digitized** | 11.0 remains Atmar 2008's **GI.1** median peak (95×10⁹ = 10^10.98). Tranche 16 sources the **GII** quantity in its own units. Per-subject symptomatic GII peaks, unambiguous **copies (or genome equivalents) per gram of wet stool**: interval **[7.0, 9.1] log10**, which is **figure-digitized from the public `shedding-hub` dataset and reported by no paper** (the publishers' Results sections were unreachable) — Kirby 2014 GII.2 challenge, n=9, median 7.06 (3.63–8.92, digitized from the paper's figures, §2.1); Tu 2008 GII aged-care outbreak, observed maximum 9.14 (digitized); Teunis 2015's 161 observed GII.4 samples top out at 8.94. Acute-phase single-specimen GII medians fall inside it: Lee 2007 GII.4 n=40 median **8.93 log10 copies cDNA/g stool** (IQR 8.22–10.24); He 2017 GII n=201 geometric mean **9.03 ± 1.71 log10 copies/g stool (w/w)**; Barreira 2009 GII children symptomatic **8.39**; Ozawa 2007 GII/4 mean 7.96×10⁹ /g (9.90). Immunocompromised/chronic hosts run to 10.4–11 (He 2017 severe stratum; Chaimongkol 2024, 10⁴–10¹¹ /g) — a different population from a passenger. **Grade B is the ceiling**: no GII faecal titre has ever been measured in the target setting, and no GII.4 challenge study quantifies a stool time course at all | Kirby 2014: **F·dig** (shedding-hub digitisation) + **?nr** for the paper body (2 attempts), Teunis 2015: **?nr** (body chunks returned; 5.79/5.91 absent from them), Lee 2007: **?nr** (2 attempts, paper not surfaced), Ozawa 2007 / He 2017 / Barreira 2009: **Ab**, Tu 2008: **F·dig** + Ab, Chaimongkol 2024: **R**, Atmar 2008: **R** + Ab (GI.1 anchor) | — | — | L? | ⊘ **joint, unchanged** — emission scale and dose-response enter as a **product** (#366) and every dose figure is void pending refit, so the measured GII interval is *recorded, not applied*. **No GI→GII correction factor is proposed** (a Kirby-derived offset applied to an Atmar-derived peak crosses two assays whose own GI.1 medians differ by ~2.3 logs). Shipped 11.0 lies above every GII central estimate and above every observed GII maximum in an immunocompetent host — declared, not acted on | #47 evidence recorded |
| `shedding_curve_log10` **time to peak** (GII) | curve index of the authored maximum | **B as an interval** | **Days 2–4 post inoculation**, and the day-of-peak median of 4 is **figure-digitized, not paper-reported** in the only GII challenge with serial quantification (Kirby 2014 GII.2, digitized day-of-peak median 4, range 2–6, n=9); **day 3 post onset** with the rise continuing to day 9 in paediatric GII cohorts (Lee 2021; Cheng 2021, rise days 2–9, decline after day 9). Ge 2023's 1.5–2.3 d is a **fitted** GI.1 quantity (grade C) and is not used | Kirby 2014: **F·dig** + **?nr**, Lee 2021: **?nr** (zero chunks), Cheng 2021: **R**, Ge 2023: **R** (1.5–2.3 d in a body chunk) + Ab | — | — | L? | evidence recorded, not adopted | #47 |
| `shedding_curve_log10` **decline shape** (GII) | authored tail over 15 indices | **B for the shape, ⊘ unit for the rate** | Log-linear decline after peak; the only decline rate with unambiguous units is Sabrià 2016's ≈**0.11 log10/day** (symptomatic 7.51 ± 1.80 → 5.28 ± 0.76 log10 GC/g over 19 d; asymptomatic 6.49 ± 1.93 → 4.52 ± 1.45, mixed genogroup). Tu 2008 (0.76/day, half-life 2.5 d) and Lai 2013 (0.66/day, half-life 1.7 d) are **not self-consistent** under either a natural-log or a log10 reading and neither states the rate's units, so they cannot be adopted as published | Sabrià 2016: **Ab** (zero chunks; 7.51 → 5.28 log10 GC/g read from the abstract), Tu 2008: **Ab**, Lai 2013: **Ab**. The only decline rate with unambiguous units is therefore abstract-only — finding **F3** | — | — | L? | ⊘ **blocked by unit ambiguity** in the published rates | #47 |
| `asymptomatic_shedding_log10` (offset), **GII-specific evidence** | peak 0.5 log10 below symptomatic | C, **direction contested for GII** | Tranche 16 adds the contradiction the existing row does not carry: for GII the offset is **either absent or ≈1 log**. Absent: Ozawa 2007 (GII means similar in symptomatic and asymptomatic food handlers); Teunis 2015 observations (symptomatic median 5.79 vs asymptomatic 5.91 log10 gc/wet g, n=115 / 46); Costantini 2015 (cases and exposed controls shed similar amounts); Huynen 2013 (higher in symptomatic for **GI**, P = 0.03, but **not for GII**). Present, 0.8–1.2 log10: Barreira 2009 (1.24, GII, P = 0.011); Dábilla 2017 (0.79, mixed); Sabrià 2016 (≈1.0 at first sample, mixed). The GII challenge literature supplies **no asymptomatic peak at all**. This row and the paediatric community row below measure the same key in **different populations** (GII-specific here; paediatric community there) and are deliberately kept separate: they are **not to be pooled**, and which one governs is an open adoption decision under #47 | Ozawa 2007: **Ab**, Teunis 2015: **?nr**, Huynen 2013: **?nr** (2 attempts, paper not surfaced), Barreira 2009: **Ab**, Dábilla 2017: **?nr** for the 0.79 offset (2 attempts), Sabrià 2016: **Ab**, Costantini 2015: **R** + Ab | — | — | L? | ⊘ **not identifiable** as a single ratio; keep 0.5 as an authored placeholder, now with its interval [0, 1.2] and its contradiction recorded | #47 |
| `shedding_duration_days` — GII confirmation | 15 | B (already adopted, interval [12, 30]) | Tranche 16 adds GII-specific support and does **not** move the interval: Kirby 2014 GII.2 first-to-last positive median **5 d** (a minimum estimate; last sample still positive in two subjects) with shedding to **3 weeks past symptom resolution**; Tu 2008 GII outbreak mean **28.7 d**; Aoki 2010 mean **14.3 d** (9–32); Costantini 2015 **47% of GII.4 cases shed ≥21 d**; Cheng 2021 cessation by day 15; Lee 2021 decline days 10–15. Shedding far outlasting the 1–3 day illness is confirmed for GII | Kirby 2014: **F·dig** + **?nr**, Tu 2008: **Ab**, Aoki 2010: **Ab** (zero chunks), Lee 2021: **?nr**, Cheng 2021: **R**, Costantini 2015: **R** (47% ≥21 d in a body chunk) + Ab | — | — | L? | ✓ interval unchanged, GII support added | #46 done / #47 |
| `immunocompromised_fraction` (config) | 0.05 | **A → B as an era-aware interval** | Harpaz 2016 (NHIS, 2.7% of US adults, 2013), Martinson 2024 (6.6% in 2021, 7.4% in 2022), Lopez-Gigosos 2020 (24 of 1,196 travel-clinic travellers, **2.0%**) → **[0.02, 0.074]**; the width is population and era, not uncertainty ([tranche 7](literature/consensus_tranche_7.md) §5) | Martinson 2024: **?nr** (2 attempts, zero chunks), Lopez-Gigosos 2020: **?nr** (2 attempts, paper not surfaced), Harpaz 2016: **R** (2.7% in a Discussion chunk). Both interval endpoints above Harpaz are unretrieved — finding **F4** | — | — | L? | ✓ **adopted as an interval, not a point** (#45): the shipped 0.05 is unchanged and lies inside [0.02, 0.074], the interval and its three sources are recorded at the definition in `crusher_labs/config.yaml`, and `tools/sanity_checker.py` warns (advisory, not an error) when a config sets a value outside it | #45 done |
| `immunocompromised_multiplier` (config) | **removed from the tree** | **F → ∅ refuted as a quantity** | No source measures the relative risk of *acquiring* norovirus while immunocompromised; Green 2014 states the persistence mechanisms are unknown. What is measured is duration and infectiousness: van Beek 2017 (2,182 SOT recipients, 4.6% infected, 22.8% chronic, median **218 days**, 32–1,164), Davis 2020 (20 chronic paediatric cases 37 to >418 days, **infectious** virus shed continuously, HIE-confirmed), Chaimongkol 2024 (chronic shedding **10⁴–10¹¹** copies/g) | Green 2014: **Ab** ("mechanisms unknown" read in the abstract), van Beek 2017: **R** (218 d, 32–1,164 in a Results chunk) + Ab, Davis 2020: **R** (>418 d in a body chunk), Chaimongkol 2024: **R** | — | — | L? | ∅ **withdrawn and removed from the tree** (#45) — an assumption sitting on the one quantity the literature does not measure, and Wave 1 made it bite harder by composing multiplicatively instead of overwriting. The key is deleted from `config.yaml`, no longer read in `init_multi_pathogen`, and no longer printed; a config that still sets it gets a sanity-checker warning saying it is refuted and ignored rather than being silently dropped. The `immunocompromised` flag survives and now selects the hosts eligible for chronic shedding below | #45 done |
| `chronic_shedder_fraction` (`norwalk_gi`) | **0.228** | **B** | Probability that a host who is both immunocompromised *and* infected becomes a chronic shedder. van Beek 2017 (*Clin Microbiol Infect* 23(4):265): 2,182 solid-organ recipients tested, 101 (4.6%) infected, **23 of 101 = 22.8%** chronic. Davis 2020 confirms *infectious* virus (HIE) rather than RNA alone in 20 chronic paediatric cases | van Beek 2017: **Ab** — 4.6% and 22.8% present in the abstract only; the Results chunks returned other denominators. Davis 2020: **R**. Finding **F5** | — | — | L? | ✓ **adopted** (#45) as a pathogen-profile key on `norwalk_gi` only; `sars_cov2_resp` and the influenza bundle carry nothing, because no sourced chronic duration exists for them, and a profile without the key has no chronic mechanism at all. Conditional on immunocompromise and infection, so it is not a population fraction. Not fitted to any scored anchor | #45 done |
| `chronic_shedding_duration_days` (`norwalk_gi`) | median **218**, range **32–1,164**, `sigma_log` **1.09** | **B** for median/range; `sigma_log` is a **declared assumption** | van Beek 2017 (*Clin Microbiol Infect* 23(4):265) measures median shedding **218 days**, range **32–1,164**, in the 23 chronic cases; van Beek 2017 (*J Infect Dis* 216(9):1132) is a supporting cohort at mean 352 days, range 76–716; Davis 2020 reports 37 to >418 days of infectious virus. The lognormal *shape* is not van Beek's: treating the reported range as an approximate 90% interval, ln(1164/218) = 1.674 and ln(218/32) = 1.919, mean 1.797, ÷1.645 → **σ = 1.09** | van Beek 2017: **R** (median 218 d, range 32–1,164 in a Results chunk), Davis 2020: **R** | — | — | L? | ✓ **adopted** (#45). Drawn once per immunocompromised host per profile at initialization on a derived RNG stream, truncated to [32, 1164] by rejection (clipped only if the 32-draw budget is exhausted), stamped into the infection record at infection and preferred over the profile's `shedding_duration_days` by `_clearance_days`. A chronic host's duration exceeds any voyage, so on board it never clears; the boarding-prevalence importation channel is deliberately **not** implemented here. No chronic *magnitude* knob is added: Chaimongkol 2024 spans 10⁴–10¹¹ copies/g, which the existing `shedding_variance_log10` per-host draw already covers, and no point value exists to adopt | #45 done |
| `surface_decay_log10_per_day` | **0.124939**, set by the profile; the fraction alias no longer exists | C → **B in sourced units** | Five surrogate studies → **[0.067, 0.79] log10/day**, Grade B, which is the unit every source measures in; the former [0.14, 0.84] was that same interval converted through f = 1 − 10⁻ᵏ. Shipped 0.25 fractional ↔ −log10(0.75) = **0.125 log10/day**, which lies **inside [0.067, 0.79] near its slow end** (tranche 5 §1) | Thompson 2017: **Ab** (2 attempts, zero chunks), Perry 2016: **Ab** (2 attempts), Greatorex 2011: **R** (hours and percentages in body chunks), Qian 2023: **R** (half-life in body chunks); Bean 1982 / Oxford: not re-queried this pass | — | — | L? | ✓ interval **adopted in the screen box in sourced units** (#41), and as of R1 the shipped value is expressed in that unit too: `norwalk_gi` carries 0.124939 log10/day, `surface_decay_per_day` is deleted from the engine, the schema and every profile, and the conversion is a single function, `transmission_core.surface_fraction_per_day`. **The divergence #41 recorded is closed** — the sourced key is now the only key and is exercised by everything that runs. This changes no value: 0.124939 = −log10(1 − 0.25) reproduces the previous per-day fraction, no golden moved, and the interval is still **adopted for the screen box only**, not as a point estimate | #41, #59 done |
| `airborne_emission_mode = emesis_conditioned`; `emesis_aerosol_fraction_range` | **[7.2e-7, 2.67e-4]**, declared interval | **B** | The continuous-shedding definition remains **∅ null-confirmed-by-search**: no study reports emission to air as a fraction of a host's shedding, for norovirus or, in six unfiltered Consensus queries, for any pathogen. Shedding is measured in copies/g of stool or vomitus and airborne virus in copies/m³ of room air, never in the same subjects, so that fraction has no commensurable numerator and denominator ([tranche 13](literature/consensus_tranche_13_airborne_fraction.md) §3.1). Conditioned on one emesis event, Tung-Thompson 2015 measured MS2 in simulated vomiting, **n = 3 per condition**, a **41 L chamber**, corrected for **8.5% sampler efficiency**; the denominator is the virus in **one expelled bolus**. Its table is in **percent**, **7.2e-5%–2.67e-2%**, which converts to the declared fraction interval **[7.2e-7, 2.67e-4]**; reading the percentages as fractions would overstate the interval by two decades. The deleted 1e-4 fell inside the converted interval only by coincidence across incompatible denominators and is not corroboration | Tung-Thompson 2015: **R** (Results prose: "ranged from a low of 7.2 x 10−5 ± 0.00006 to a high of 2.67 x 10−2 ± 0.03 (Table 2)"), re-queried 2026-09-04 and **corrected from ?nr** in [tranche 21](literature/consensus_tranche_21_full_text_reverification.md) §1; the Table 2 row itself is **?nr** | — | — | L? | ✓ **definition and plumbing adopted (R4)**: the norovirus arm emits to air only per emesis event, drawing log-uniformly over the entire declared interval into the zone reservoir exactly once. The value remains an interval; **no point inside it was selected**, and no value was selected to match an anchor or golden | R4 |
| `airborne_half_life_hours` | 1.1 | **I, cross-pathogen** — **∅ null for human norovirus, reconfirmed** | **No measurement of airborne human norovirus decay exists**; human NoV is not routinely culturable, so airborne NoV work reports RNA persistence, not infectivity decay. The shipped 1.1 remains van Doremalen's SARS-CoV-2 figure, mis-cited there too (van Doremalen measures 2.7 h). Nearest measurement, **Grade B, named calicivirus surrogate**: Zargar 2025 (*J Virol Methods* 335:115144) feline calicivirus in a 25 m³ room-sized aerobiology chamber, six-jet Collison nebuliser, soil load, gelatin slit sampler, PFU assay, **22 ± 2 °C and 50 ± 10% RH** → biological decay **0.0081 ± 0.0031 log10 PFU/m³/min**, which as a unit transformation is t½ = **0.62 h (0.45–1.00 h on ±1 SD)**. **Abstract-verified only** — full text paywalled, so "biological decay" (i.e. corrected for physical loss), the fit form and the run count are unverified; Reckitt-funded air-purifier study. Supporting bounds, no rates: Purhonen 2024 (MNV infectious to 90 min), Alsved 2020 (drying drives infectivity loss), Rupprom 2024 (GII RNA to 120–240 min), Sanka 2026 (MS2/ΦX174 infectious in air at 2 h, absent at 24 h), Donaldson 1976 (FCV RH-sensitive across 30–70%, no rate). Rejected: Dubuis 2020 (ozone), Buonanno 2024 (far-UVC), thermal/surface/water persistence, all SARS-CoV-2 aerosol work ([tranche 13](literature/consensus_tranche_13_airborne_fraction.md) §4–§5) | Kormuth 2018: **Ab** + **R** for the infectivity prose; the half-life figure itself **?nr** | — | — | L? | ∅ **null stands for norovirus.** Either declare the field unsourced, or adopt the FCV surrogate interval **[0.45, 1.00] h** as an explicitly cross-species Grade B stand-in — an adoption decision this tranche does not take. Note the shipped 1.1 sits **outside** that interval; recorded as a fact about the surrogate measurement, not as an argument for any replacement value | #39 |
| `route_efficiency_multipliers` (6) | 0.35/0.1/0.05/0.3/0.2/0.0 (renamed from `transmission_route_weights`, values unchanged) | C | None. Independent per-route multipliers, not shares — the schema now says so | — | — | — | L? | ⊘ **joint** — the field defect is resolved (#25); these multipliers are not separately identifiable from Edison's pre-establishment clearance layer, which parameterises the same object, so no per-route efficiency can be adopted into one of the two alone | #25 |
| `environmental_faecal_release_log10_g_per_epoch` | 4.0 (`dose_adjustment`) | F → **measured inert** | Ge 2023 measures *total shed genome copies*, which retires the key rather than sourcing it | Ge 2023: **R** + Ab | — | — | L? | ⊘ field | #38 |
| `emesis_total_shed_gec_range` (engine) | (1e5, 1e8), log-uniform, drawn **once per symptomatic illness** | **B**, surrogate genotype | Kirby 2016 Table 3, per-subject **cumulative** emesis shed: GII.2 Snow Mountain 1.8e7 GEC (SEM 1.8e7), GI.1 2.3e8, per-subject values spanning ≈1e5–1e8. No GII.4 emesis measurement exists (tranche 4 §3). The interval reproduces the measurement rather than being fitted: the arithmetic mean of a log-uniform on [1e5, 1e8] is (1e8 − 1e5)/ln(1e3) = **1.45e7**, within 1.25× of the measured 1.8e7 | Kirby 2016: **R** (Results prose, chunk-verified 2026-09-04) + **T3** (study-3 row read from the open-access full text, Europe PMC PMC4845978, 2026-09-04: cumulative shed 1.8×10⁷ GEC, SEM 1.8×10⁷ — the register value confirmed, finding **F1 withdrawn**); **Me** for the unit (sample weight used as the volume proxy, 1 g = 1 ml) | — | — | L? | ✓ **adopted** (#38); screened over [3.6e7, 3.1e8] on the high endpoint (GII.2 mean + 1 SEM → largest per-subject cumulative mean in the paper) | #38 done |
| **Degrees-of-freedom reduction (emesis)** | three inputs → **one** | — | The former titre × volume × episode-count parameterisation carried **three** free inputs for a quantity the source identifies **once**, and it was not merely mis-valued: the measured GII.2 titre mean (1.6e5 GEC/mL) times the measured mean total volume (845 mL) is 1.35e8, **7.5× above** the same paper's measured per-subject cumulative 1.8e7, because the titre mean is taken over positive samples on a heavy right tail. Setting all three independently therefore overstated emission by an order of magnitude *while looking like provenance on each*. Adopting the cumulative total removes two degrees of freedom outright | — | — | — | L? | ✓ recorded and implemented | #38 done |
| Emesis titre (engine) | **withdrawn and deleted**; 3.9e4 no longer appears in the engine, and the withdrawn figure is recorded here and in the ledger | B, **from the abstract** | Kirby 2016 Table 3: GII.2 = 1.6e5. The abstract pools a 2-subject GII.1 pilot the Results exclude. No profile key resolves to a titre any more; the emesis record carries titre as a **derived** diagnostic (`episode_load / volume_ml`), so the abstract-versus-Results defect cannot return through a config | Kirby 2016: **R** (Results prose, chunk-verified 2026-09-04: GII.2 emesis titre 1.6×10⁵ GEC/ml) + **T3** (study-3 row, open-access full text, Europe PMC PMC4845978: 1.6×10⁵ GEC/ml, SEM 4.5×10⁴); **Me** for the unit (sample weight as the volume proxy, 1 g = 1 ml). Finding **F1** withdrawn in tranche 21 §2 | — | — | L? | — superseded by the cumulative total | #38 done |
| Emesis volume (engine) | 50–800 mL/episode, still drawn | B | Tung-Thompson 2015, Booth & Frost 2019. It no longer multiplies a titre: with the total identified, volume is only the physical deposit volume, used for the deposition record and any concentration-based check | Booth & Frost 2019: **?nr** for a volume in ml (2 attempts), Tung-Thompson 2015: **R** for the vomiting-episode prose + **?nr** for a stated volume | — | — | L? | ✓ role narrowed | #38 done |
| Emesis episode count (engine) | **1–7** (was 1–3) | **B**, measured | Kirby Tables 2–3: 1–7 events per subject, mode 1. With the total identified, the count only **partitions and times** that same total; it no longer scales emission, which is what makes correcting the range safe | — | — | — | L? | ✓ **adopted** (#38) | #38 done |
| `contact_transfer_fraction` (engine) | **1.0, by omission** — neither active profile sets it | **C** | **Blocked by definition.** The field multiplies dose from *contacted partners* (`_direct_contact_dose`, `_per_partner_contact_dose`), and the schema defines it as the fraction of a partner's **emission** reaching the target. No transfer assay in this literature uses emission as its denominator — all use a pipetted donor inoculum recovered at contact time ([T12](literature/consensus_tranche_12_contact_transfer.md) §6.4). Nearest measured analogue is **hand → hand: 0.7–6.6 %** (rotavirus 6.6 % at 20 min / 2.8 % at 60 min, Ansari 1988 DOI 10.1128/jcm.26.8.1513-1518.1988; rhinovirus 14 0.7–0.9 %, HPIV-3 undetectable, Ansari 1991 DOI 10.1128/jcm.29.10.2115-2119.1991), Grade B, and **no norovirus or norovirus-surrogate measurement of that direction exists** (§6.3). The **~0.25** anchor in `norovirus/norovirus_model_history.md` §10 **does not trace to a primary measurement**: it is numerically indistinguishable from Anderson 2021's direction-free MS2 pooled mean 0.26 (DOI 10.1128/aem.01215-21), Julian 2010's direction-free 0.23 ± 0.22 on glass (DOI 10.1111/j.1365-2672.2010.04814.x) and Grove 2015's single-direction 24 % surface → hand (DOI 10.1016/j.ijfoodmicro.2014.12.023), and the repository does not say which. As a **direction-free** transfer fraction it is **refuted** — the two directions differ by up to two orders of magnitude under drying, so no single number represents both (§1). Arithmetic only, no recommendation: 0.25 is inside the shipped screen interval 0.06–0.50, at the top edge of the surface → hand norovirus-surrogate range 2.0–24 %, **above** the dried hand → surface range 0.1–1.8 % by ~14–250×, and **above** the hand → hand range by ~4–36×. **Measured to clear no noise floor anywhere** in the PR #368 screen — which is not evidence that any value is correct | Anderson 2021: **?nr**, Julian 2010 / Ansari 1988 / Grove 2015: **Ab** (zero chunks each). The row is blocked by definition, not by retrieval | — | — | L? | **blocked by field** (definition unmeasurable) + **~0.25 anchor refuted as a direction-free quantity** | #22 |
| surface → hand transfer fraction, non-porous (`SURFACE_TO_HAND_LOGNORMAL`) | lognormal `(-2.1, 1.4)` | **B** | **2.0–24 %** for norovirus + norovirus surrogates on non-porous donors by **infectivity**: MNV-1 stainless steel → finger pad **2.0 ± 2.0 %** and Trespa® → finger pad **4.0 ± 5.0 %**, dried 40 min, 0.8–1.9 kg/cm² for ~2 s (Tuladhar 2013, DOI 10.1016/j.ijfoodmicro.2013.09.018); FCV steel disk → finger pad **7 ± 1.9 %**, air-dried, 0.2–0.4 kg/cm² for 10 s (Bidawid 2004, DOI 10.4315/0362-028x-67.1.103); MNV-1 steel spigot → bare hand **24 %** (1.4-log transfer %), ≥ 9 replicates, **moisture state not stated** (Grove 2015, DOI 10.1016/j.ijfoodmicro.2014.12.023). Human NoV GI/GII bound it from above in **genome copies**: **2–11 %** dry, **1–50 %** wet (Sharps 2012, DOI 10.4315/0362-028x.jfp-12-052). Widened to all analogous viruses and tracers on non-porous donors: **~0.5–80 %**, with humidity and time-since-deposition each worth ~1 order of magnitude (Lopez 2013 up to 57 % at RH 15–32 % and 79.5 % at RH 40–65 %, DOI 10.1128/aem.01030-13; Ansari 1988 rotavirus 16.8 % at 20 min → 1.6 % at 60 min; Behzadinasab 2021 SARS-CoV-2 13–16 % wet / 3–9 % dried, DOI 10.1038/s41598-021-00843-0) | Tuladhar 2013: **Ab** (2 attempts, zero chunks), Sharps 2012: **Ab** (2 attempts, zero chunks), Bidawid 2004: **Ab**, Ansari 1988 / Grove 2015: **Ab**, Lopez 2013: **R** (transfer percentages in Results chunks); Behzadinasab: not re-queried this pass | — | — | L? | **evidence recorded** | #22 |
| hand → surface transfer fraction, non-porous (`HAND_TO_SURFACE_LOGNORMAL`) | lognormal `(-2.1, 1.4)` | **B** | **Splits by moisture; do not state as one interval.** **Wet/immediate 9.2–60 %**: MNV-1 hand → stainless steel **9.19 %** (Dallner 2021, DOI 10.3390/v13071352), MNV-1 finger pad → stainless steel **13 ± 16 %** immediate (Tuladhar 2013), human NoV GII fingertip → stainless steel **58–60 %** in genome copies (Sharps 2012). **Dried 0.1–1.8 %**: MNV-1 **0.1 ± 0.2 %** after 10 min drying (Tuladhar 2013), MNV-1 hand → spigot **0.6 %** (Grove 2015), HuNoV GII **< 1 %** dry (Sharps 2012), rotavirus **1.8 %** at 60 min (Ansari 1988). Disagreement retained: FCV finger pad → steel **13 ± 3.6 %** air-dried but transferred immediately after drying (Bidawid 2004) lands with the wet group, so the dried interval is not tight. Direction asymmetry independently confirmed: significant for MS2 (Anderson 2021) and for influenza A RNA (Zhang 2026, DOI 10.1016/j.ijheh.2026.114766); the ~130× drying penalty falls on **this** direction, matching the PR #378 axis | Sharps 2012: **Ab**, Tuladhar 2013: **Ab**, Zhang 2026: **?nr**, Anderson 2021: **?nr**, Lopez 2013: **R**; Dallner 2021 / Bidawid 2004 / Grove 2015 / Ansari 1988: Ab or not re-queried | — | — | L? | **evidence recorded** | #22 |
| `hand_to_surface_drying_multiplier` | key added, **1.0 (neutral) by default, no profile sets it** | **B** as an interval | The drying lever is ~100× on the deposit direction and only ~5× on pickup: hand→surface falls 13% → 0.1% after 10 min drying (Tuladhar 2013) and 59% → <1% (Sharps 2012). Interval **[0.008, 1.0]**, log10 — 0.008 is Tuladhar's dried/immediate ratio (0.1%/13% = 0.0077), 1.0 is fully wet | Tuladhar 2013: **Ab**, Sharps 2012: **Ab** — the whole ~100× drying lever is abstract-only after 2 attempts per paper. Finding **F6** | — | — | L? | ✓ interval **adopted in the screen box**; the value is *not* adopted, because **which drying state applies to a hand continuously recontaminated by its own shedding is not measured**. It enters as a swept axis, at neutral, changing no shipped arithmetic | #42 |
| Cabin-localization fraction `f` | swept | **C, bounded above** | **Headline bound: `f ≤ 0.5`, and it is structural rather than epidemiological** — at double occupancy at most one occupant of every affected cabin can have been infected elsewhere, so the ceiling is occupancy combinatorics and holds whatever the attack rates are (tranche 17 §5.2). **Still no measurement of `f`**: no study on any ship reports the share of norovirus transmission occurring between cabinmates, and none reports the cabin-level case distribution that would give it without a model ([tranche 17](literature/consensus_tranche_17_cabin_localization.md) §3, §6). A tighter **empirical** ceiling of `f ≤ 0.18–0.45` is derivable from cruise outbreak attack rates and cabinmate association measures — `≤ 0.18` (Wikswo 2011, RR 3.0, AR 15.4%, DOI 10.1093/cid/cir144), `≤ 0.26` (Chimonas 2008, OR 3.40, 95% CI 1.80–6.44, AR 24.1%, DOI 10.1111/j.1708-8305.2008.00200.x), `≤ 0.37`, CI 0.25–0.45 (Mouchtouri 2024 pooled, OR 38.70, 95% CI 13.51–110.86, DOI 10.2807/1560-7917.ES.2024.29.10.2300345) — but that derivation is Grade C and, more importantly, **is derived from the same attack-rate data the model is scored against, so it is not usable to constrain the swept range while A4/A8/A9 remain scored anchors**: it is the A3 circularity of item **A3 (#23)** in [`proposals/defect_resolution_plan.md`](proposals/defect_resolution_plan.md) arriving by a new route. It also over-attributes to the cabin, because cabinmates share dining, excursions and travelling party. Household SAR is the **Grade B** analogue at **13.8–23%** per contact — Matsuyama 2018 **13.8%** (DOI 10.1177/0300060518776451), Quee 2020 **15%** (DOI 10.1016/S1473-3099(20)30058-X), Balachandran 2023 **23%** (*Open Forum Infect Dis*, DOI 10.1093/ofid/ofad619: “The overall secondary attack rate was 23%”, 570 primary cases, 1,479 household contacts, 338 secondary cases, an integrated US health care network 2014–2016). Two caveats ride with Balachandran, both from its own abstract: its 23% is **viral AGE across all enteric pathogens, not norovirus-specific** — norovirus-positive primary cases carried an adjusted OR of **2.7** for onward transmission, so a norovirus-only figure would be **higher** than the pooled one — and households of ≥3 members carried aOR **2.1**, so the figure is **household-size-conditioned**. The interval remains a **per-contact secondary attack rate, not a fraction of transmission**, and therefore is **not a bound on `f`**. **No lower bound is supported: `f = 0` is not excluded.** Fitted route splits (Towers 2017, Tsang 2018, De Bellis 2025, Lei 2018, Xiao) are excluded as circular against the attack-rate anchors — explicitly including **Tsang 2018's Bayesian model-fit household SARs of 84% (urban, size-2 households) and 13–29% elsewhere**, which are **seen and rejected** on that ground and must not enter the household interval above | Chimonas 2008: **Ab** (2 attempts, paper not surfaced with chunks), Matsuyama 2018: **?nr** (2 attempts), Wikswo 2011: **R** partial (transmission-mode sections retrieved; the household/cabin split absent from them), Tsang 2018: **R** + Ab; Balachandran / De Bellis / Lei / Mouchtouri / Quee / Towers: not re-queried this pass | — | — | L? | **evidence recorded — upper bound only: `f ≤ 0.5` structural and admissible; the empirical `f ≤ 0.18–0.45` is anchor-derived and **not** admissible as a constraint on the sweep; ∅ null on any central value** | #12, #23 |
| Observation model (~15 numbers) | — | C / F | One empirical aggregate constrains them jointly, and that aggregate is anchor A3 | — | — | — | L? | ⊘ **A3 is not a test** | #23, #27 |
| External voyage denominator for VSP posting rates (qualifying voyages per year under VSP jurisdiction, ≥100 pax, 3–21 d) | **absent** — the series holds posted outbreaks only; anchors A4/A8/A9 use class-level MIDRS aggregates | **M, transcription unverified, for 2008–2014; ∅ null for 2004–2007, 2015–2019, 2022–2026** | Freeland 2016 (MMWR 65(1), DOI 10.15585/mmwr.mm6501a1, Table): VSP-report voyages per year **4,404–4,808** (2008–2014; Σ 32,084), of which 3–21 d and >100 pax **3,964–4,387** per year (Σ 29,107); 73.6 M passengers and 28.3 M crew over the seven years; travel-days recoverable only by back-calculation from the published per-10⁷-travel-day rates. Jenkins 2021 (MMWR SS 70(6), DOI 10.15585/mmwr.ss7006a1): **37,258** unduplicated voyage reports and ~127 M passengers, 2006–2019, as a single total — **not year-resolved**, and not reconcilable with Freeland's annual counts in the same unit (29,107 of 37,258 would fall in 7 of the 14 years). Koo 1996 (JAMA, DOI 10.1001/jama.1996.03530310051032) documents the construction (passengers × cruise length from routine 24-h reports) for 1989–1993 only. MARAD/BTS US-departure cruises 2004–2011 (4,126–4,498/yr) and BREA/CLIA embarkations (9.7–13.8 M, 2010–2019) are **measured / estimated in a different population** (US departures incl. domestic; no ≥13-pax or foreign-itinerary filter) and are excluded as denominators; CLIA global volumes are part projection. **Grade M, transcription unverified** for 2008–2014, and **no Grade A is claimed**: the counts are a transcription of a table the sourcing unit could not re-open, and the paper's own published per-1,000-voyage rates are not reproducible from them for 5 of 7 years, so how well we know these numbers is currently **not at all**. **None** elsewhere | Koo 1996: **?nr** (2 attempts), Freeland 2016: **R** — the voyage counts (Σ 32,084; 4,404–4,808/yr; 29,107 of 3–21 d and >100 pax) came back in MMWR body chunks, not from transcription, Jenkins 2021: **R** + Ab. Finding **F7** (reopened: this row was a transcription) | — | — | L? | ⊘ **blocked by field** — the numerator is *posted* outbreaks (91 rows 2008–2014; 208 rows 2006–2019) while every CDC denominator pairs with *investigated* outbreaks (132; 156), and CDC's two voyage units disagree; a posting rate is computable for 2008–2014 only after declaring the voyage unit, and for no other year without an annual MIDRS extract from CDC VSP. **Freeland's counts are unverified**: the table above was transcribed by the sourcing unit from a source it could not re-open (cdc.gov returned 403, no PMC copy), the paper's published per-1,000-voyage rates are reportedly not reproducible from those transcribed counts for 5 of 7 years, and the paper's text says 133 where its table says 132. **No posting rate may be computed from them until the primary is re-read** — which blocks nothing further, because this row adopts nothing | #13 |
| Boarding / importation prevalence | **absent** — the index case is seeded by fiat | **C → B as an interval** | Asymptomatic norovirus RNA in stool, non-outbreak populations: 2.5% of 4,536 healthy asymptomatic adults, mean age 58.0 (Kobayashi 2021, *Clin Microbiol Infect*, DOI 10.1016/j.cmi.2021.06.004); pooled adult 4%, Europe/North America 4%, food handlers 3% across 81 studies (Qi 2018, *EClinicalMedicine*, DOI 10.1016/j.eclinm.2018.09.001); 5 of 707 asymptomatic food handlers = 0.71% (Jeong 2021, *J Food Prot*, DOI 10.4315/jfp-21-136). **Passengers [0.025, 0.040], crew [0.007, 0.030]**, Grade B. Outbreak-population figures (Qi's 18%, Wang 2023's 21.8%) are **excluded as circular** — measured during the event the model is scored on | Jeong 2021: **?nr**, Kobayashi 2021: **Ab** (abstract chunk only), Qi 2018: **Ab** (highlights/abstract), Wang 2023: **R** + Ab | — | — | L? | ⊘ **mech** — no importation channel exists; a host cannot board infected. Sweep the interval once one does ([tranche 10](literature/consensus_tranche_10.md) §3) | #45 |
| Chronic-shedder boarding prevalence | absent | ∅ **null, bounded** | Derived two ways, disagreeing by 2.5 orders: van Beek's cohort denominator gives **1.4e-5–5.2e-5** of a boarding population (0.117% per patient-year chronic incidence × 218-day median × immunocompromised [0.02, 0.074]); Bok's positivity denominator gives **1.1e-3–4.2e-3** as an **upper bound** (13% positive × 44% persistent, denominator = patients tested while under investigation). Both are **1–3 orders below** the general asymptomatic channel above, and are mostly inside it rather than additive | — | — | — | L? | ∅ **no point value licensed** — chronic shedding enters as a swept **duration** axis on an imported host, not as its own prevalence ([tranche 10](literature/consensus_tranche_10.md) §4) | #45 |
| `asymptomatic_shedding_log10` (offset) | peak 0.5 log10 below the symptomatic curve | C, **direction confirmed, magnitude open** | Measured symptomatic-versus-asymptomatic stool loads: 8.39 vs 7.15 log10 copies/g, a 1.24-log10 offset (p = 0.011, Vitória cohort, children) and 2.69 × 10⁸ vs 4.32 × 10⁷ GC/g, 0.79 log10 (Dábilla 2017, DOI 10.1016/j.jcv.2016.12.009, children). Both paediatric, so the shipped 0.5 is about half the measured offset, in the conservative direction. This row and the GII-specific row above measure the same key in **different populations** and are deliberately kept separate: they are **not to be pooled**, and which one governs is an open adoption decision under #47 | Dábilla 2017: **?nr** for the 0.79 offset (2 attempts), Barreira 2009: **Ab** — and the 1.24 log10 offset is **arithmetic on two abstract medians**, stated nowhere. Finding **F8** | — | — | L? | ⊘ setting — not adoptable from paediatric data alone; an adult measurement would settle it ([tranche 10](literature/consensus_tranche_10.md) §6) | |
| `never_symptomatic_fraction` — share of imported infections that never present, in a boarding population | **none shipped** | **B as two intervals; C for the model's own population** | **Searched** ([tranche 11](literature/consensus_tranche_11_never_symptomatic.md)). Two admissible designs disagree and are **not pooled**. **Challenge studies, infected adults, illness = diarrhoea and/or vomiting: [0.22, 0.36]** — GI.1 5/14 (Gray 1994, *J Clin Microbiol*, DOI 10.1128/jcm.32.12.3059-3063.1994) and 7/26 (Newman 2016, *Clin Exp Immunol*, DOI 10.1111/cei.12772), GI.1 33% of 21 infected (Atmar 2014, *J Infect Dis*, DOI 10.1093/infdis/jit620), **GII.4** 4/16 infected secretors (Frenck 2012, *J Infect Dis*, DOI 10.1093/infdis/jis514), **GII.2** ≈6/24 infected (Rouphael 2022, *J Infect Dis*, DOI 10.1093/infdis/jiac045, Table 1: 44 adults, infection in 90% and illness in 70% at the highest dose, ID50 5.1×10⁵ GEC, illness defined as diarrhoea and/or vomiting in infected subjects) — at inocula far above natural exposure. **Community birth cohorts, weekly sampling: [0.59, 0.68]** — Baker 2026 PREVAIL (*Clin Infect Dis*, DOI 10.1093/cid/ciag033) reports **72 GI and 330 GII norovirus infections among 156 children** and states that **about one-third of infections were symptomatic**, including half of infections with cycle threshold values <25; El-Heneidy 2022 (*Pediatr Infect Dis J*, DOI 10.1097/inf.0000000000003667) 127/209 infections, 183/221 of them GII. The interval therefore rests on a **rounded verbal statement rather than count-level data**, so its precision is lower than two decimal places implies. Corroborated but **not independently**: Cannon 2026 (*Pediatrics*, DOI 10.1542/peds.2025-072461), the **same PREVAIL cohort**, 245 children and 13,944 stools — "approximately two-thirds of enteric viral infections were asymptomatic", symptomatic infections infrequent before age 6 months; **Grade B**, and **pooled across five enteric viruses rather than norovirus alone**. **The definition moves the value more than the population does:** the same GII.2 trial reads ≈25% never-symptomatic under "diarrhoea and/or vomiting" (Rouphael 2022) against 64% under "AGE presentation" — but that 64% is the **secondary-inoculum arm alone, 16/25**; the primary arm is 2/9 and the pooled figure is ≈53% (Qu 2025, *J Med Virol*, DOI 10.1002/jmv.70546). Outbreak-conditioned figures — Miura 2018's 32.1% (also a fitted MLE), Wang 2023's 21.8%, Wang 2024's 17.6%, Qi 2018's 18% — are **excluded as circular**, measured in populations conditioned on the outcome the model is scored on; Lopman 2014 (*Am J Epidemiol*, DOI 10.1093/aje/kwt287) and Teunis 2020 are **model outputs, not measurements** | Gray 1994: **Ab** (2 attempts, zero chunks), Rouphael 2022: **Ab** — including the register's "Table 1" attribution, which was **?nr** in 2 attempts (finding **F9**), Baker 2026: **Ab** (zero chunks), Qi 2018: **Ab**, Atmar 2014: **R**, Frenck 2012: **R** (Discussion + susceptibility chunks), Wang 2023: **R**; Cannon / El-Heneidy / Lopman / Miura / Newman / Qu / Teunis: not re-queried this pass | — | — | L? | ⊘ **no value licensed, and the obstacle is a design mismatch rather than a width**: the challenge interval is measured in **adults, but at inocula far above natural exposure**; the community interval is measured **under natural exposure, but in children under 3, in whom the fraction demonstrably falls with age** (71.1% in year 1 → 61.2% in year 2, none symptomatic before 4 months); and the model's population is **adult passengers of measured mean age 72.6** (Pavli). **No admissible design measures this quantity in the model's target population**, so the two intervals are swept separately and **never pooled into a central value**, the illness definition the `never_symptomatic` state means is declared before either is adopted, and **enabling boarding without the coordinate remains a load error** | #45, #53 |
| `presymptomatic_share_of_presenting` — share of presenting imported infections caught before onset | 0.04 as a derived default, swept | C, **derived, not measured** | Arithmetic on three fields of this profile, not an independent measurement: `presymptomatic_shedding_days` = 0.5, `recovery_day` = 3 and `shedding_duration_days` = 15, so a presenting episode's non-symptomatic shedding course is 0.5 before onset plus 15 − 3 = 12 after illness clears, and the pre-symptomatic part of it is **0.5 / (0.5 + 15 − 3) = 0.5 / 12.5 = 0.04**. Re-derivable from the profile alone; move any of the three fields and this default moves with them ([spec](proposals/initiation_engine_spec.md) §4) | — | — | — | L? | Default shipped in the config block only; swept, never adopted as a measured value | #45 |

### 3.2 SARS-CoV-2 (`sars_cov2_resp`) — active, not scoreable

| Quantity | Shipped | Class | Evidence / interval | Origin | Interval | Shape | Lev | State | Task |
|---|---|---|---|---|---|---|---|---|---|
| `incubation` (3 fields) | lognormal, 5.8 d, GSD 1.57 | M | Wei 2021, ancestral | Wei 2021: **?nr** — the GSD 1.57 was not retrieved in 2 attempts, and the 5.8 d median matched only in a same-topic COVID incubation meta-analysis whose identity with the cited paper is unconfirmed. Finding **F10** | — | — | L? | — in tree (wrong for Omicron) | |
| `presymptomatic_shedding_days` | 2.0 | M | He 2020 | He 2020: **R** (presymptomatic transmission prose in Summary/Discussion chunks); the 44% figure itself **?nr** | — | — | L? | — in tree | |
| `airborne_half_life_hours` | 1.1 | ~~M~~ → **I** | **Mis-cited**: the row cited van Doremalen 2020, whose measurement *is* 2.7 h. Measured dark aerosol half-lives are 1.43 h (Schuit 2020, simulated saliva) and 2.7 h (van Doremalen 2020); Fears reports retained infectivity to 16 h. Interval **[1.43, 2.7] h**, Grade B — the shipped 1.1 is outside it, clearing the pool faster than the fastest measurement. The same inherited 1.1 sits on `norwalk_gi`, where tranche 5 recorded a null | van Doremalen 2020: **Ab** (2 attempts, zero chunks — the mis-citation the row already records could not be checked against body text), Schuit 2020: **R** (half-life in body chunks) | — | — | L? | ✓ adoptable as an interval ([tranche 9](literature/mql_tranche_9_sars_cov2.md) §4) | #31 |
| `surface_decay_log10_per_day` | **1.301030** (was `surface_decay_per_day` = 0.95) | C → **B** | **Corroborated under both readings of the field**: 0.95 as a per-day fraction = 5.55 h half-life, 0.95 as log10/day = 7.6 h (the label on this branch previously read "1.30 log10/day", which is the *same* quantity as the fraction reading — 1.301030 log10/day is 5.55 h — so the two readings were mislabelled, not miscounted), both inside Xu 2023's reviewed 5–9 h on stainless steel / plastic / glass at 22 °C. Material and condition dependence is large and is not carried by a single constant (porous 1–5 h; 28 days at 20 °C in darkness with a protein-rich matrix, Riddell; 90% loss every 6.8–12.8 min under simulated UVB, Ratnesar-Shumate) | Xu 2023: **R** (half-life in hours in body chunks) + Ab | — | — | L? | — in tree; the **first inherited SARS-CoV-2 constant a search confirms** ([tranche 9](literature/mql_tranche_9_sars_cov2.md) §4). **R1 resolved the two readings, and not on evidence:** migrating to the sourced unit forced a choice between them, and the value-preserving one was taken, so 0.95-as-fraction became 1.301030 log10/day and the 5.55 h half-life is what the tree now means. Both readings sit inside Xu 2023's 5–9 h, so nothing is adopted or excluded by the choice, but it was made to keep behaviour identical rather than because 5.55 h is better attested than 7.6 h | |
| `recovery_day` | 7 | C → **B** | #366 §3 | — | — | — | L? | — in tree | |
| `shedding_duration_days` | **15** | **B** as an interval | The field's clock ends the infection, and the curve it runs over is a **nasal RNA concentration**, so the quantity sourced is the **upper-respiratory RNA-positivity duration**, not the infectious one: Cevik 2020 (*Lancet Microbe*, DOI 10.1016/S2666-5247(20)30172-5; meta-analysis, 43 studies / 3,229 individuals) pooled mean **17.0 d** (95% CI 15.5–18.6) in the URT; Fontana 2020 (*Infect Control Hosp Epidemiol*, DOI 10.1017/ice.2020.1273; 28 studies) pooled median **18.4 d** (15.5–21.3, I² = 98.9%); Wu 2023 (*Int J Infect Dis*, DOI 10.1016/j.ijid.2023.02.011; Omicron meta-analysis) mean PCR positivity **10.82 d** (10.23–11.42). Interval **[10.8, 18.4]** — the width is variant and era, not uncertainty. Shipped **15**, the authored curve's own length, 0.4 d from the interval midpoint (14.6) and not fitted to Diamond Princess or any other scored anchor. **The two clocks stay distinct in the evidence and the tail is the shorter one**: no culture positivity past day 9 of illness in Cevik's review, 5.16 d (4.18–6.14) viable-virus duration for Omicron (Wu 2023), Keske 2023 culture positivity 83/52/13.5/8% at days 5/7/10/14 with 19% infectious after symptoms stop | Cevik 2020: **R** (pooled mean in a Results chunk), Fontana 2020: **R** (pooled median in a Results chunk), Wu 2023: **R** (both durations in a Results chunk), Keske 2023: **R** (median culture-positive duration in body chunks) | [10.8, 18.4] | — | L? | ✓ **implemented** (#51). Illness still clears at `recovery_day` = 7 and only the infection/shedding clock is extended, so the host now reaches all 15 authored curve indices and emits **100.0%** of both authored integrals, against 99.979% symptomatic / 99.9725% asymptomatic before — the point of the change is **detectability over a repeat-testing series**, not dose. The cost of serving both clocks from one field is stated rather than hidden: days 8–14 emit at 2.0–5.5 log10 as if infectious when the culture evidence says most hosts are not, worth 0.021% of the curve integral. Unblocks #33 | #51 done |
| `shedding_curve_log10` (shape) | peak at index 4 | C → **B** | #366 §3 | — | — | — | L? | — in tree | |
| `shedding_curve_log10` (magnitude) | peak 10⁹ | C, **mis-dimensioned, path-dependently** | Lane 2023 ~80 copies/min breathing; Coleman 2021 63–5,821 copies/activity; Alsved 2023 4–127 TCID50/s singing; **Alsved 2022 (n=38) 70/110/80 copies min⁻¹ breathing/talking/singing and Zheng 2022 4.4–5.8 × 10⁷ copies h⁻¹ in 11 of 25 Omicron patients — 4.1 logs apart, with the shipped arm inside them**. The shipped term is a nasal concentration used as a rate: the droplet and direct-contact paths consume it raw (2–4 orders high), while the airborne path divides by `airborne_emission_fraction` first and lands 7.6× above Alsved's talking median | Coleman 2021: **R** (Results chunk) + **?nr** for a per-minute rate, Zheng 2022: **Ab** for the per-hour rate + **R** (Discussion); Alsved / Lane: not re-queried this pass | — | — | L? | ⊘ joint with β — but the emission side is now **bounded by measurement**, so β is identifiable given the bracket ([tranche 9](literature/mql_tranche_9_sars_cov2.md) §1) | #30 |
| `dose_response.alpha` / `beta` | 0.18 / 58.0 | C (attribution withdrawn twice, independently) | **No SARS-CoV-2 ID50 in genome copies exists**, from any design — tranche 15's eight unfiltered Consensus queries found none, including a query written specifically to find a characterisation of the Killingley inoculum in copies. Independent dose measurements are all in infectious units: Killingley 2022 (*Nat Med*, DOI 10.1038/s41591-022-01780-9) **10 TCID50 → 18/34 (~53%)** naive adults, the only naive human dose point; Jackson 2024 (*Lancet Microbe*, DOI 10.1016/s2666-5247(24)00025-9) escalates **10¹ → 10⁵ TCID50** in 36 **seropositive** adults and induces **no sustained infection at any dose** (5/36 transient), so the slope is not a virus property once hosts are immune; hamster ID50/MID figures span ~5 logs in infectious units (Rosenke 2020 ID50 5 infectious particles, DOI 10.1080/22221751.2020.1858177; Lin 2022 MID ≤14 PFU, DOI 10.1038/s41598-022-09218-5; Blaurock 2022 MID 10⁻³ TCID50 orotracheal, DOI 10.1038/s41598-022-19222-4). Prentiss and Riediker stay **rejected as attack-rate-fitted**, and tranche 15 rejects three further fitted candidates on the same ground: Marc 2021 (*eLife* 10.7554/elife.69302, load→transmission fitted to transmission pairs), Iyaniwura 2024 (*PNAS* 10.1073/pnas.2406303121) and Xu 2025 (*Epidemics* 10.1016/j.epidem.2025.100843), both within-host models fitted to the Killingley data | Lin 2022: **R** partial (PFU quantification in body chunks), Xu 2023: **R**; Blaurock / Iyaniwura / Jackson / Killingley / Marc / Rosenke: not re-queried this pass | — | — | L? | ⊘ joint, **and ∅ null in copies** — the existing sweep and "adopt neither endpoint, no attack-rate-fitted value" stand unchanged. **Withdrawn, and it was this register's own defect:** the previous version of this row converted Killingley's 10 TCID50 to "≈ 10³–10⁴ copies". That parenthetical is **withdrawn as an unsourced conversion** — it implies ~10²–10³ copies per TCID50, which is **1–3 logs below every measured ratio** (see the row below), and it is **not replaced by a composed number**: composing Killingley through the measured conversion would stack a 0.59–0.96 log10 TCID50→PFU step, a ~2.7-log copies-per-PFU interval and a single-dose 53% point that cannot identify a two-parameter dose-response — over 3 logs composed, wider than the sweep already carried | #30 |
| **Copies per infectious unit** (new row — the unit bridge between the emission side, in copies, and every independent dose measurement, in infectious units) | not a profile key; used implicitly wherever a TCID50 dose is quoted in copies | **B as an interval, by setting** | **Clinical respiratory/environmental specimens: 10⁴·² – 10⁶·² N-gene copies per PFU** (Gaussian fit on log10, mean **10⁵·² ± 1.0 SD** = 160,000; 151 infectious specimens of 459, 75 patients; Lin 2022, *Sci Rep*, DOI 10.1038/s41598-022-09218-5, Results/Fig. 8a). **Propagated culture supernatant: 2.95 × 10³ – 2.98 × 10⁴ E-gene copies per PFU** across five isolates — D614G 29,800, Alpha 11,700, Gamma 8,930, Delta 12,500, Mu 2,950 (Zapata-Cardona 2022, *Iran J Microbiol*, DOI 10.18502/ijm.v14i3.9758), corroborated by Lin's own ~10⁴:1 for culture-harvested virus. **PFU↔TCID50 is itself an offset of 0.59–0.96 log10**, variant-dependent (same paper). **Combined honest bound ≈ 3 × 10³ – 1.6 × 10⁶, ~2.7 logs.** Three studies designed to test whether a fixed ratio exists say it does not: Puhach 2022 (*Nat Med* 10.1038/s41591-022-01816-0) copies-vs-FFU **R² = 0.15–0.40** in 565 NPS; Despres 2022 (*PNAS* 10.1073/pnas.2116518119) infectious units per E-gene copy **5.9× / 3.0×** higher for Delta / Epsilon than Alpha (14.3× / 6.9× on subgenomic E), n = 162; Porter 2025 (*Access Microbiol* 10.1099/acmi.0.000732.v3) the ratio moves **> 5 logs across one infection course** | Puhach 2022: **Ab** + **R** for the term itself, Despres 2022: **R** for the PFU assay + **?nr** for a copies-per-PFU ratio, Lin 2022: **R** partial; Porter / Zapata-Cardona: not re-queried this pass | — | — | L? | ✓ **evidence recorded, interval only — no central value licensed.** Grade B for each setting; the ~1–1.5-log specimen-vs-supernatant split, the 3–14× variant spread and the >5-log within-host swing are **not** measurement error and must not be collapsed to a point. **Composition with Killingley is left to the lead and is not performed**: it would chain a TCID50→PFU step (0.59–0.96 log10 measured, and published conversions of this exact inoculum disagree ~8×: ~7 PFU vs Xu 2025's "≈ 55 PFU"), this ~2.7-log ratio, and a single-dose 53% point that cannot identify a two-parameter dose-response — **> 3 logs composed**, wider than the sweep already carried | #30 |
| `asymptomatic_shedding_log10` | peak 10⁷·⁵ | C | **Refuted**: measured URT loads are similar between symptomatic and asymptomatic in week 1. The 1.5-log10 offset has no basis | — | — | — | L? | ✓ remove the offset | #31 |
| `shedding_variance_log10` | 1.2 | C | Schijven 2020: between-person SD 1.3–1.7 log10 | Schijven 2020: **Ab** + **R** partial (per-hour emission in a body chunk; the emission-rate value itself absent from the chunks returned) | — | — | L? | ✓ | #31 |
| Severity / asymptomatic fraction | absent | — | Buitrago-García 2020 (~31% screened), Sah 2021 (35.1%). **Tabata/Diamond Princess is barred — it is the training set.** Tranche 9 adds the ladder: 81% of symptomatic cases mild (Wiersinga 2020), 29–34% ICU and 12.6–13.6% death among hospitalised (Mody 2021, Nguyen 2021), Levin 2020 age-specific IFR 0.004% (0–34) → 0.75% (55–64) → 2.5% (65–74) → 28.3% (85+), Ulloa 2022 Omicron 59% lower hospitalisation or death than Delta. The ladder spans four orders across the age range and cruise passengers are not a general population (Pavli mean age 72.6), so severity should **read the agent's age** rather than be one fitted vector | Buitrago-García 2020: **R** + Ab; Levin / Mody / Nguyen / Sah / Ulloa / Wiersinga: not re-queried this pass | — | — | L? | ✓ with the screened denominator, **as a function of age** | #31 |
| PCR sensitivity vs time since exposure | absent | — | Tranche 3 §3; tranche 9 adds the infectiousness side — Keske 2023 viral-culture positivity 83/52/13.5/8% at days 5/7/10/14 after the first positive, 19% shedding infectious virus after symptoms stop, against a median 7-day RNA shedding and RNA to 21 days in samples with no viable virus | Keske 2023: **R** | — | — | L? | ✓ — required by the observation layer; **RNA positivity and infectiousness are two clocks** | #33 |
| `illness_probability.eta` / `gamma` | 0.4 / 0.12 | C | Unattributed near-neighbours of norovirus's Korkin values. Yields 0.56 at the profile N50 — a dose-conditional value, not a population fraction | — | — | — | L? | ⊘ field | #31 |
| `route_efficiency_multipliers` (6) | 0.25/0.3/0.3/0.1/0/0.05 (renamed, values unchanged) | C | None | — | — | — | L? | ⊘ **joint** — field defect resolved (#25); not separately identifiable from the clearance layer, as norovirus | #25 |
| `airborne_emission_fraction` | 5e-5 (renamed, value unchanged) | **C** unsourced-assumed | Norovirus's 1e-4, halved, with no stated reason. **Derivable rather than assumed on this arm**: measured emission rate (Alsved 2022, Zheng 2022) ÷ modelled specimen titre, both in copies ([tranche 9](literature/mql_tranche_9_sars_cov2.md) §1) | Zheng 2022: **R** (Discussion); Alsved: not re-queried this pass | — | — | L? | — not blocked: field defect **resolved** (#42); derivable, pending the units fix on the curve | #30 |
| Secretor / innate nonsusceptibility | absent (key removed from neither — never set) | C, **defensible** | No known innate-resistance locus; correct by argument for a naive 2020 population | — | — | — | L? | declared | |
| `base_susceptibility` | 1.0 | X | The unit modifiers act against | — | — | — | L? | construction | |
| `immunocompromised_fraction` (shared, `config.yaml`) | 0.05 | C → **B as an interval** | Self-reported immunosuppression in US adults: 2.7% (Harpaz 2016, JAMA, DOI 10.1001/jama.2016.16477), 6.6% in 2021 (Martinson 2024, JAMA, DOI 10.1001/jama.2023.28019), 7.4% in 2022 (Li 2024, OFID, DOI 10.1093/ofid/ofae415). Nearest measurement in our setting: 24 of 1,196 international travellers = 2.0% (Lopez-Gigosos 2020, AJTMH, DOI 10.4269/ajtmh.19-0702). Interval ≈ **[0.02, 0.074]**, Grade B — the width is population and era, not uncertainty | Martinson 2024: **?nr** (2 attempts), Lopez-Gigosos 2020: **?nr** (2 attempts), Harpaz 2016: **R**; Li: not re-queried this pass. Same defect as §3.1 — finding **F4** | — | — | L? | ✓ **adopted as an interval** (#45); shipped value unchanged at 0.05, inside the interval, with the sources at the definition and an advisory warning outside it | #45 done |
| `immunocompromised_multiplier` (shared, `config.yaml`) | **removed from the tree** | C → ∅ refuted | No study measures immunocompromised *acquisition* risk for norovirus; Green 2014 (DOI 10.1111/1469-0691.12761) states the persistence mechanisms are unknown. What is measured is **duration**: van Beek 2017 (DOI 10.1016/j.cmi.2016.12.010), 2,182 solid-organ recipients, 4.6% infected, 22.8% of those chronic, median shedding 218 days (range 32–1,164); Bok 2016 (DOI 10.1093/ofid/ofw169), persistent infection ≥6 months in 8 of 18 genotyped | Green 2014: **Ab**, van Beek 2017: **R**; Bok: not re-queried this pass | — | — | L? | ∅ **withdrawn, and the mechanism defect is resolved** (#45): the multiplier is gone from the tree and the measured quantity now enters where it was measured, as a shedding duration on the pathogen profile. See the note below | #45 done |

**The immunocompromised evidence measures duration, not susceptibility — and
that is now where it enters.** #45 deleted the susceptibility multiplier and put
the measured quantities on the `norwalk_gi` profile as
`chronic_shedder_fraction` 0.228 and `chronic_shedding_duration_days`
(median 218, range 32–1,164, declared σ_log 1.09), drawn per host at
initialization on a derived RNG stream and consumed through the infection
record by the tranche 8 clearance seam. Against a 7–14 day voyage a 218-day
duration means a chronic host never clears on board, so the quantitatively
interesting half remains the host who **boards already shedding** — an
importation channel, quantifiable as boarding prevalence × chronic fraction.
That channel is deliberately **not** implemented yet, and
[tranche 10](literature/consensus_tranche_10.md) settles why: no
chronic-shedder point prevalence is licensed — two derivations disagree by
2.5 orders — and the channel that matters is not this one. Ordinary
asymptomatic adults board shedding at 2.5–4%, one to three orders above
the chronic estimate, so importation is real, measured, and mostly
immunocompetent. What chronic hosts retain is duration, not prevalence:
218 days against a 7–14 day voyage means a shedder present for the whole
cruise.

### 3.3 Influenza A (`influenza_a`) — **active** in `active_profiles.json`

The pooled arm is loaded by a run today: one `influenza_a` profile with no
subtype-specific biology, scored on **MAARI and NAT-confirmed infection as
separate observation rungs**, and its Edison bundle counterpart is *not* the
profile that loads (§3.3's `surface_decay` row still refuses the Edison value).
§4.4 remains open, and the fields it concerns are declared and swept rather
than fitted — `base_susceptibility` stays a scenario input, and the
vaccination and antiviral coverage that every shipboard anchor was measured
under is a manifest axis (§3.3.2), not a pathogen constant.

What activation required, in what order, is sequenced in
[`proposals/influenza_arm_activation_plan.md`](proposals/influenza_arm_activation_plan.md);
the shipboard evidence it would be scored against is assembled in
[tranche 20](literature/consensus_tranche_20_shipboard_influenza_anchors.md).
Neither re-grades a row here. The arm has **no anchor in VSP**: VSP's reporting
rule is gastrointestinal, so the 428-posting series is not an influenza anchor
by construction, and the candidate anchors are the five published shipboard
outbreak reports in §3.3.1 — declared as a *likelihood*, never as a prior.

| Quantity | Shipped | Class | Evidence / interval | Origin | Interval | Shape | Lev | State | Task |
|---|---|---|---|---|---|---|---|---|---|
| Incubation | — | M | Lessler 2009, median 1.4 d | Lessler 2009: **Ab** for the 1.4 d figure + **R** (incubation-distribution body chunks) | — | — | L? | — in tree | |
| `presymptomatic_shedding_days` | 1.0 | M | Ip 2017, ~1 d | Ip 2017: **Ab** (2 attempts, zero chunks) | — | — | L? | — in tree | |
| `symptomatic_fraction` — presentation given infection, dose-independent (**replaces** the deleted `illness_probability.eta` / `gamma` = 0.67 / 0.1) | **0.669**, 95% CI **[0.583, 0.745]** | **B** | **Refuted at the cited source, verified in Carrat's Results** — graded **B, not A**: Carrat 2008 is a **pooled meta-regression** across 56 volunteer challenge studies in clinical facilities, which is a measurement in an analogous setting and a cross-study regression rather than a direct measurement in the target setting, so B is the ceiling under this register's own class definitions (*Am J Epidemiol* 2008;167:775–785, DOI 10.1093/aje/kwm375): "The proportion of symptomatic infection (any symptoms) was 66.9 percent (95 percent CI: 58.3, 74.5). No significant difference was noted according to the virus type … or the initial infectious dose (p = 0.12)." Denominator **522 infected individuals in 38 subgroups**, from 56 studies / 1,280 challenged, inoculum **3–7.2 log10 TCID50** (4.2 orders). Lower-respiratory symptoms 21.0% (14.0–30.3) likewise dose-independent. The one clinical dose association runs the **wrong way**: fever OR **0.56 per log10 TCID50** (0.42–0.73, p<0.001), which the authors call striking and unexplained. The only contrary claim found is Teunis 2010 (DOI 10.1016/j.epidem.2010.10.001), whose "slightly higher illness risk due to the higher doses involved" is an output of a **fitted** hierarchical dose-response model, class C, and therefore circular for an attack-rate-scored model — recorded and rejected in §3.4 | Carrat 2008: **Ab** confirmed verbatim; the same sentence was **?nr** in every body chunk returned by three queries, including the paper's own "Clinical illness" section, so the row's "verified in Carrat's Results" reading is **not reproducible by chunk retrieval** and rests on the opened PDF — [tranche 21](literature/consensus_tranche_21_full_text_reverification.md) §2 finding **F11** | — | — | L? | ✓ **adopted by deleting the mechanism (R3)**: the Hill field `1 − (1 + η·dose)^−γ` is strictly increasing in dose while the measured endpoint is flat over 4.2 orders, so the η/γ pair is **deleted on this arm rather than re-sourced** and presentation reads the measured proportion directly from `symptomatic_fraction`. The shipped 0.67 was this same pooled population fraction standing in an η slot, where it meant a dose-curve parameter; the repair moves it to a field where it means what Carrat measured, at the reported 0.669. The 95% CI is the screening interval and **no point inside it was selected against any anchor**. The influenza arm loses a dose-conditional degree of freedom, which is the intended direction | #44 |
| `dose_response.k` | 0.18 (exponential) | C | Alford 1966 **aerosol** ID50 0.6–3 TCID50; Memoli 2015 **intranasal** — and Edison's two bundles disagree on it by 1–2 orders (α/β → 902 TCID50 vs a quoted 10⁴–10⁵) | Alford 1966: **Ab** (2 attempts, zero chunks), Memoli 2015: **R** (TCID50 in Discussion + validation chunks) | — | — | L? | ⊘ joint + unresolved citation | #44 |
| Route efficiency (aerosol vs intranasal) | absent | — | The ratio is a **measurable physical quantity spanning at least two orders**. Multiplier withdrawn pending Memoli's primary text; the order-of-magnitude conclusion stands | — | — | — | L? | ⊘ field — needs #25 first | #25 |
| Emission | — | C | Yan 2017/2018 (EMIT): GM 3.8e4 copies/30 min fine aerosol, 1.2e4 coarse, culturable in 39% of fine. **Uncorrelated with NP swab load** — direct proof that a nasal-indexed curve cannot be an emission rate | Yan 2017: **R** (fine-aerosol infectious-virus chunks) + **?nr** for the copies-per-30-min figure | — | — | L? | ✓ once the shedding path takes a rate | #30 pattern |
| `surface_decay_log10_per_day` | **1.221849** (was `surface_decay_per_day` = 0.94) | C | **∅ null as defined**: no study measures a surviving fraction, or a single per-day rate, spanning material/matrix/RH. What is measured, all infectious-virus assays: **half-life 4.5–5.9 h** on steel/ABS/PS/glass in **human airway surface liquid**, 23% RH, 22–24 °C (Qian 2023, *Appl Environ Microbiol*, DOI 10.1128/aem.00633-23; steel 4.52 h, 95% CrI 2.41–8.56; **donor-culture spread 3.2–8.1 h is wider than the between-material spread**); **t½ ≈ 1.5 h** in BSA/DMEM at 17–21 °C, 23–24% RH, steel undetectable by 24 h (Greatorex 2011, DOI 10.1371/journal.pone.0027932); **99% reduction at 174.9 h** on steel in 0.3% BSA, viable to 2 weeks (Thompson 2017, DOI 10.1016/j.jhin.2016.12.003); **<2 log10 over 7 days** on steel in mucin/FBS/medium at 18–25 °C, 20–55% RH, AH significant p<0.0001, strain not p=0.45 (Perry 2016, DOI 10.1128/aem.04046-15); 24–48 h recoverable on steel/plastic (Bean 1982, DOI 10.1093/infdis/146.1.47; Oxford 2014, DOI 10.1016/j.ajic.2013.10.016). Decay on steel is **non-monotone in RH** (fastest mid-range, Qian 2023). RNA persists 1–3 orders longer than infectivity on the same coupons (Greatorex: 0.06 log10 RNA loss vs >4.2 log10 infectivity at 24 h on steel; Thompson: 7 weeks PCR vs 2 weeks viable). **Two-regime rates, sourced and not adopted** ([tranche 19](literature/consensus_tranche_19_influenza_biphasic_surface.md) §2, from full text rather than abstracts): Rockey 2024 (DOI 10.1128/aem.02010-23) measures H1N1pdm09 in 1 µL **human saliva** droplets at 50% RH decaying at **0.010 ± 0.012 log10/min before drying** (indistinguishable from zero) and **0.036 ± 0.020 log10/min after**, with drying time itself measured at **0.26 / 0.54 / 1.29 h** for 20 / 50 / 80% RH — while **airway surface liquid shows a single rate, 0.010 ± 0.0030 log10/min, with no detectable phase split** and inactivation associated with neither protein, salt nor drying time; French 2023 (DOI 10.1128/mbio.03452-22) reports both phase rates for H1N1pdm09 across nine volume × RH conditions in cell-culture medium, with the wet/dry ordering **inconsistent** (0.52 ± 0.16 wet vs 0.17 ± 0.06 dry at 5 µL/40% RH, reversing to 0.06 ± 0.13 vs 0.19 ± 0.03 at 50 µL/40% RH) | Thompson 2017: **Ab** (2 attempts, zero chunks), Perry 2016: **Ab** (2 attempts), Greatorex 2011: **R** (hours and percentages in body chunks), Qian 2023: **R** (half-life in body chunks); Bean 1982 / Oxford: not re-queried this pass | — | — | L? | ⊘ **field** — confirmed by search, not argument: the scalar has no measured referent, and the sourced quantity is a matrix- and RH-conditioned **interval of half-lives**, not a point. Evidence recorded; **still not adoptable, and R1 narrowed why.** The unit defect is fixed — the field is now a log10 rate like norovirus's, at the 0.94-preserving 1.221849 — so what remains is dimensionality alone: one number cannot carry an interval indexed on matrix, donor, RH and assay endpoint, and Qian 2023's donor spread is wider than its between-material spread. Converting the units does not endorse the value, which stays refuted pending R2 — whose shape question is re-read in [`proposals/surface_decay_biphasic_spec.md`](proposals/surface_decay_biphasic_spec.md) as biphasic in time since deposition rather than indexed on the environmental covariates, which it argues largely collapse on an HVAC-pinned ship. That proposal sources and adopts nothing, so this row's ⊘ state, grade, interval and evidence are unchanged by it. **R2's assay-endpoint question is resolved on this row: the decay endpoint is infectivity, not RNA**, inheriting tranche 5 §1's norovirus resolution — the pools are denominated in genome copies and the dose-response consumes copies, so an RNA rate is dimensionally consistent and wrong by up to four orders, and the copies→infectivity availability conversion is itself an open item rather than a licence to substitute the RNA rate. **R2's rate question is now a selection problem, not an absence**: tranche 19 §2 supplies two sourced triplets and neither is adopted, because they disagree on which phase is faster, they are single-droplet experiments over 1–8 h rather than a per-day pool law, and the respiratory matrix the ship setting favours shows no phase split at all. No value, grade or interval on this row moves. **What the shipped scalar means, stated in the unit the sources measure in** (the tranche 5 §1 / #41 move, applied here without adopting the value): 1.221849 log10/day is a **5.9 h half-life**, which sits at the *slow edge* of Qian 2023's measured 4.5–5.9 h respiratory-matrix range and well inside its 2.41–8.56 h steel credible interval; the five studies above bracket roughly **[0.27, 4.8] log10/day** (Thompson's 174.9 h to Greatorex's 1.5 h), and the spread is *matrix*, not strain (Perry p = 0.45). So the row is not an absence of a referent — it is one point inside a wide sourced bracket, and the discriminating test is empirical rather than bibliographic: sweep the field across the bracket and see whether any scored observable moves. Recorded as the screening bracket; **no grade change and no adoption**, and it does not block activation (plan §4) | #44 |
| Same key in Edison's *proposed* bundle (not in `data/`) | **4.8**, range [2.0, 16.0] | P | Unchanged by this tranche: nothing found measures influenza surface persistence in any unit in which 4.8/day is a coherent value | — | — | — | L? | **must not be loaded** | #44 |
| `airborne_half_life_hours` | 1.5 | C | Kormuth 2018: <0.5 log10 loss across 20–98% RH **in respiratory mucus** vs minutes in saline. Interval width is *matrix*, not RH | Kormuth 2018: **Ab** + **R** for the infectivity prose; the half-life figure itself **?nr** | — | — | L? | ✓ as an interval | |
| `base_susceptibility` | 0.65 | **F, and it is prior immunity** | Not a constant: a per-season, per-route seroprevalence/vaccination input. This is the one place a flu arm could quietly overfit. **Now measured to be irreducible to a scalar** ([tranche 20](literature/consensus_tranche_20_shipboard_influenza_anchors.md) §3.2): on Ward 2010's single voyage pandemic H1N1 ran at **RR 17.4 (10.5–29.1)** in children 3–6 with **zero cases** over 65, while H3N2 was flat across every age band — so the quantity is subtype- **and** age-conditioned. Vaccination does not convert into it either: Millman's crew were 90% / 95.5% covered with 93.9% / 100% of crew cases vaccinated, Brotherton 2003 found no significant protection, and Ortiz 2023 found HAI ≥40 does not separate infected from uninfected (OR 0.81 per two-fold, p = 0.126) | — | — | — | L? | reclassify as a scenario input — **declared and swept, never fitted** | |
| `surface_deposition_fraction` | 1e-3 | I | 10× the norovirus value, no stated reason. The bundle still uses the deprecated key name; the engine reads it through the alias — i.e. it is an **airborne emission fraction**, feeding the airborne zone reservoir. The Emission row above is the reason a *fraction* is the wrong form: Yan's emission is uncorrelated with NP load, so it cannot be a share of a nasal-swab-indexed curve. Same defect class R4 resolved for norovirus by redefining the field | — | — | — | L? | ∅ null; ⊘ field resolved in the active bundle only (#42) | #42 |
| `dose_adjustment` | 1.5 | **I — no referent on this arm** | The key is now spelled `environmental_faecal_release_log10_g_per_epoch` and means −log10 of the **grams of stool** released to the environment per epoch. On a respiratory pathogen it denotes nothing, and it multiplies into dose. Not a sourcing question | not re-verified this pass — row added by R5, after the origin sweep | — | — | L? | **must not be loaded**: remove or replace at activation (plan §1) | |
| `transmission_route_weights` | 0.2 / 0.35 / 0.3 / 0.15 (**sums to 1.0**) | **I — unit mismatch** | Authored as a mixture of shares; the engine reads the key as the deprecated alias of `route_efficiency_multipliers`, which are **independent per-route dose multipliers, not shares**. Renaming without re-deriving would reinterpret a mixture as five efficiencies | not re-verified this pass — row added by R5, after the origin sweep | — | — | L? | **must not be loaded** as-is (plan §1) | |
| `observation_model`, `severity_model` | **absent** | — | Both active profiles carry them; this arm has neither, so an activated arm would emit *infections* against anchors that are all reported *illness*. The capture fraction is not transferable: norovirus anchor A3 is **0.60 ± 0.05**, while Ward 2010 measures 0.7% presenting to the infirmary against 8.9% NAT-confirmed infection on one voyage — **≈0.08**, ~7× lower ([tranche 20](literature/consensus_tranche_20_shipboard_influenza_anchors.md) §2). MAARI also over-counts influenza **2–5×** (22–57% of tested cases confirmed), and HAI-only serology under-counts infection by ~a third (31% of SHIVERS seroconversions were NAI-only) | not re-verified this pass — row added by R5, after the origin sweep | — | — | L? | ✓ **both now present on the active profile**, and the two endpoints are emitted as **separate rungs** rather than one capture fraction: a MAARI reporting model (severity-conditioned, pre- and post-recognition) and an independent molecular/NAT model (passive sampling of presenting cases plus optional active screening, with its own assay sensitivity), so a scenario can miss one rung and hit the other. Norovirus's A3 = 0.60 is **not** reused here, and no capture probability on this arm was chosen to reproduce Ward's ≈0.08 or Millman's 3.1–6.2% | |
| `recovery_day` vs `shedding_curve_log10` | 5 against a 15-day curve, no `shedding_duration_days` | — | The two clocks coincide, as they did on the norovirus arm before #43 — but the consequence here is small: the curve peaks at day 3, so ~99.7% of the linear-scale integral falls inside the window. Separate the clocks at activation rather than relying on that | not re-verified this pass — row added by R5, after the origin sweep | — | — | L? | minor; plan §1 | |

#### 3.3.1 Candidate anchors — declared, not adopted

From [tranche 20](literature/consensus_tranche_20_shipboard_influenza_anchors.md) §1.
Rung matters more than ship: the reviews' much-quoted "3.8%–37%" is this ladder
read as one quantity. **No influenza parameter may be sourced by which value
reproduces one of these.**

| Candidate | Endpoint as measured | Value | Role |
|---|---|---|---|
| Ward 2010 (DOI 10.3201/eid1611.100477, PMC3294517) | NAT-confirmed infection, passengers, n = 1,970 | 3.9% pdm09 + 5.0% H3N2 + 0.1% both = **8.9%** | candidate primary |
| Ward 2010, same voyage | ILI presenting on board | pax **0.7%**; crew self-reported ILI 2.7% (crew on oseltamivir prophylaxis — intervention-confounded) | candidate primary; the capture pair |
| Millman 2015 Ship A (DOI 10.1111/jtm.12215, PMC4869710) | MAARI | pax **97/2,595 = 3.7%**; crew **33/1,057 = 3.1%** | candidate primary; the pax/crew contrast |
| Millman 2015 Ship B | MAARI | pax **187/2,987 = 6.2%**; crew **54/1,157 = 4.7%** | candidate primary |
| Brotherton 2003 (DOI 10.1017/s0950268802008166) | self-reported ILI, postal questionnaire | **310/836 = 37%** of respondents | validation only |
| Miller 2000 (DOI 10.1086/313974) | self-reported ARI | **215/1,284 = 17%** | validation only |
| Fernandes 2014 (DOI 10.1111/jtm.12132) | ARI case count | 104 cases, **no denominator in the abstract**, no open full text | ⊘ blocked read — not a rate |

Two structural findings in that set constrain the ship and crew models rather
than the pathogen: the influenza passenger/crew ratio is **1.19–1.32** against
norovirus anchor A5's **~2.9–3.5** on the same kind of hull (so A5 must not be
a pathogen-independent crew term), and importation is **pre-embarkation and
plural** — two or three co-circulating viruses per voyage, onsets before Day 0,
low influenza activity at every port of call.

An influenza **fleet count cannot be a likelihood at all**: seasonal-influenza
reporting to CDC is voluntary, and the maritime threshold is **1.38 ILI cases
per 1,000 traveler-days** — a different functional form from VSP's
passenger-fraction rule. Where #13 blocks norovirus's posting rate on the
denominator, influenza's numerator is self-selected as well.

#### 3.3.2 Vaccination and oseltamivir — manifest axes, not pathogen constants

Every candidate anchor in §3.3.1 was measured **under intervention**: Ward's
voyage treated cases and gave the crew prophylaxis, and both Millman ships ran
empiric treatment plus chemoprophylaxis of contacts. So 8.9% / 3.7% / 6.2% are
post-intervention observations, and an arm with no pharmacology cannot be
scored against them at all. The knobs live in the run manifest
(`pharmaceutical_interventions.<pathogen_id>`), keyed by role, and none of them
was chosen to reproduce an anchor.

Two axes, kept apart because the evidence splits that way and a single
"protection" scalar would hide it: **acquisition** (does the host get infected)
and **illness given infection** (does an infected host become a case). Neither
is folded into `base_susceptibility`, which stays pathogen biology.

| Quantity | Default | Class | Evidence / interval | State |
|---|---|---|---|---|
| `vaccination.efficacy_against_illness` | **0.4848**, 95% CI [0.419, 0.5429] | **B** | Ge 2025 (*Clin Microbiol Infect*, DOI 10.1016/j.cmi.2025.09.005): pooled VE against **laboratory-confirmed** influenza across 26 RCTs / 104,931 participants. A pooled RCT meta-analysis in the general population, not a measurement in the target setting, so B is the ceiling | ✓ adopted as the illness-axis default; overridable per run |
| `vaccination.efficacy_against_acquisition` | **0.0** | **B — an explicit zero** | Not an unsourced default. Presa 2025 titles the finding "morbidity benefits amid low infection prevention"; on the ships themselves Millman's crew were 90% / 95.5% covered with 93.9% / 100% of crew MAARI cases vaccinated, Brotherton 2003 found no significant protection, and Ortiz 2023 found HAI ≥40 does not separate infected from uninfected (OR 0.81 per two-fold, p = 0.126) | ✓ adopted as zero and **exposed as a sweep**; it is the field where a flu arm would otherwise absorb transmission error |
| `antiviral.prophylaxis.efficacy_against_illness` | **0.60** (RR 0.40, 95% CI 0.26–0.62) | **B** | Zhao 2024 (*Lancet* 404:1841, WHO guideline network meta-analysis, DOI 10.1016/S0140-6736(24)01357-6): oseltamivir post-exposure prophylaxis against **symptomatic** influenza, moderate certainty | ✓ adopted |
| `antiviral.prophylaxis.efficacy_against_acquisition` | **0.0** | **B — an explicit zero** | Same review: neuraminidase inhibitors "probably ha[ve] little or no effect on prevention of **asymptomatic** influenza virus infection" | ✓ adopted as zero |
| `antiviral.treatment.illness_reduction_days` / `shedding_reduction_days` | **1.0 day** | **B** | Fry 2014 (*Lancet Infect Dis* 14:109, RCT, n = 1,190): median symptom duration 3 vs 4 days; virus isolation cut 15.2% / 30.2% / 47.5% at days 2 / 4 / 7 | ✓ adopted; applied to the treated host's own natural history at onset, not to the profile |
| `antiviral.treatment.transmission_multiplier` | **1.0 (no effect)** | **C — interval spans no effect** | Ng 2010: household secondary infection odds **0.54 (0.11–2.57)** with treatment within 24 h. Whether treating an index case reduces onward transmission is not established | ✓ adopted as no effect; the field exists so the question can be **swept rather than assumed** |
| `antiviral.treatment.window_hours` | **48.0** | **declared operational cutoff, not a constant** | Fry 2014 still measured a shedding effect past 48 h, so this is a policy boundary rather than a measured biological limit | declared; a dose arriving after the window is no dose |
| `coverage_by_role` (vaccination, treatment, prophylaxis) | **{} — nobody covered** | scenario input | Millman's *measured* crew coverage (90% Ship A, 95.5% Ship B) appears only as a worked example in `crusher_labs/config.yaml`, commented out — it is not a default. A role absent from the map is uncovered, so a partially-specified manifest cannot quietly cover everybody | declared and swept, never fitted |

### 3.4 Nulls and rejections recorded by sourcing wave 1

Recorded so the same searches are not repeated and the same attractive papers
are not re-found and read as an oversight. None of these is a gap in the
search; each is a result.

| Quantity | Finding | State |
|---|---|---|
| GII.4 faecal shedding time course | **No GII.4 human challenge study reports a quantitative stool titre time course.** Frenck 2012, Bernstein 2014 and Rouphael 2022 report detection, proportions positive or ID50 only. The sole GII challenge with serial quantification is GII.2 Snow Mountain — a genotype, not the pandemic GII.4 ([tranche 16](literature/consensus_tranche_16_gii_shedding_peak.md)) | null result, recorded |
| GII faecal titre in the target setting | **No measurement exists on a ship.** Grade A is unattainable for this quantity; B is the ceiling | blocked by setting |
| Prospective community cohort, serial GII quantification in copies/g | **None found.** The community designs recovered (IID2, LoewenKIDS, Kobayashi's matched adult cohorts, Cannon 2026) report detection, genotype or Ct, not per-subject quantified peaks | null result, recorded |
| SARS-CoV-2 ID50 in genome copies | **None exists, from any design** — eight unfiltered queries, including one written to find a characterisation of the Killingley inoculum in copies ([tranche 15](literature/consensus_tranche_15_covid_dose_denominator.md)) | ∅ null |
| Copies per TCID50 in a respiratory specimen | **Not measured.** The specimen-side ratio is per PFU; the TCID50-side work is on culture stocks | ∅ null |
| A fixed clinical copies-per-infectious-unit conversion | **Three studies designed to test whether one exists conclude it does not** (Puhach 2022 R² = 0.15–0.40; Despres 2022 3–14× variant spread; Porter 2025 >5 logs across one infection course). A positive finding about the field, not a gap in ours | ∅ null, and it is a result |
| Norovirus emission to air as a fraction of shedding | **No study reports it**, for norovirus or for any pathogen in six unfiltered queries: shedding is measured per gram of stool or vomitus and airborne virus per m³ of room air, never in the same subjects ([tranche 13](literature/consensus_tranche_13_airborne_fraction.md)) | ∅ null, confirmed by search |
| Airborne human norovirus decay | **No measurement exists**; human NoV is not routinely culturable, so airborne work reports RNA persistence, not infectivity decay. Rejected on mechanism: Dubuis 2020 (ozone), Buonanno 2024 (far-UVC), all SARS-CoV-2 aerosol work | ∅ null, reconfirmed |
| Norovirus contact transfer, human-norovirus **infectivity**, either direction | **None exists**; every HuNoV figure is RT-qPCR copies and every infectious figure is a surrogate, so **Grade B is the ceiling, not a provisional grade** ([tranche 12](literature/consensus_tranche_12_contact_transfer.md) §6.2) | ∅ null |
| Hand→surface transfer under cruise-ship soiling, humidity or touch pressure | **None exists.** Every value in the interval rows is a food-contact or laboratory assay | ∅ null |
| Cabin-localization `f` — QMRA and fitted route splits | **Rejected as circular**, not missed: Towers 2017, Tsang 2018, De Bellis 2025, Lei 2018 and Xiao fit a cabin or route share to the same attack-rate data anchors A4/A8/A9 score against. Tsang 2018's fitted household SARs (**84%** urban size-2; 13–29% elsewhere) are recorded here as seen-and-rejected so they are not mistaken for unseen evidence, and they do not enter the household-SAR interval in §3.1 ([tranche 17](literature/consensus_tranche_17_cabin_localization.md) §5) | rejected, recorded |
| Contact transfer — QMRA and model-derived transfer fractions | **Rejected as model outputs**: Wilson, Canales, Kraay, Pérez-Rodríguez, Iulietto, Jin, Chang, Zhang 2021. Porous and food-material values (Rönnqvist, Verhaelen, Stals, Wang, Escudero, Derrick and the food legs of Tuladhar/Bidawid/Dallner/Grove) are excluded on material | rejected, recorded |
| SARS-CoV-2 dose-response — attack-rate-fitted candidates | **Rejected**: Prentiss and Riediker stay out, and tranche 15 adds Marc 2021, Iyaniwura 2024 and Xu 2025 on the same ground — adopting one and then scoring on Diamond Princess would fit a physical constant to a scored anchor | rejected, recorded |
| Influenza illness-given-infection, dose dependence | The only contrary claim to Carrat's dose-independence is Teunis 2010, whose higher illness risk at higher dose is an output of a **fitted** hierarchical dose-response model — class C, and circular for an attack-rate-scored model | rejected, recorded; mechanism deleted by R3 |
| VSP posting-rate denominator outside CDC | MARAD/BTS US-departure cruises and BREA/CLIA embarkations are **measured or estimated in a different population** (US departures including domestic, no ≥13-pax or foreign-itinerary filter) and are excluded as denominators; CLIA global volumes are part projection ([tranche 18](literature/consensus_tranche_18_voyage_denominator.md)) | rejected, recorded |

## 4. The five blocked and one resolved, and the change each needs

This is the actionable core of the register. In every case the paper exists and
the field cannot take it, so the next move is a model change, not a search.

**The order in which these are taken is not free**, and it is set out in
[`proposals/defect_resolution_plan.md`](proposals/defect_resolution_plan.md)
rather than here: items 1–3 are structural prerequisites of the rest, items 4
and 6 are the same identifiability constraint in two arms and must be adopted
jointly or not at all, and item 5 is circular with anchor A3 until A3 is
demoted. Read that plan before starting any single item.

How these blocked rows are re-read before any inference runs is set out in
[`proposals/bayesian_inference_design.md`](proposals/bayesian_inference_design.md),
which **re-grades no row and adopts no value**.

The immunocompromise item left this list in #45 and is recorded in its §3.1 and
§3.2 rows instead: the mechanism defect was that the only field available was a
susceptibility multiplier, and the evidence measures duration. The duration
field now exists (`chronic_shedding_duration_days`, on the profile), so the
quantity enters where it was measured and the multiplier is deleted rather than
repurposed. The enumerated count below is unchanged at six because this item was
carried as a §3.2 ⊘ mech row rather than as one of the six.

Two items left this list in Wave 2 and are recorded in their §3.1 rows instead.
The norovirus half of the surface-decay defect is resolved: the field is now
`surface_decay_log10_per_day`, the unit every source measures in, and the
conversion happens in one place (#41 done). R1 finished what #41 left half-done —
the fraction alias is deleted rather than deprecated, and every profile in both
bundles is on the sourced unit, so the migration reaches what runs (#59 done).
The influenza half survives as item 3 below, now on dimensionality alone. And the drying-state axis **now exists**, as
`hand_to_surface_drying_multiplier` over [0.008, 1.0], shipping neutral and
swept; what remains there is that no value is adopted, which is a missing source
rather than a missing mechanism (#42).

Norovirus dose-response left this list in tranche 6: the shipped α/β is declared
as the disaggregated GI.1 arm and swept over the human GII interval it lies
inside (§3.1), so no model change is owed. Its conditional-illness partner η/γ
remains blocked, and its blocker is now carried in its §3.1 row rather than as an
item here, because the genogroup contrast cannot be quantified for it at all.

1. **Route efficiency, both active arms** — the naming and schema defect is
   resolved (they are declared independent per-route multipliers, not shares, and
   the six numbers were left exactly as shipped). What remains blocked is that
   they duplicate the object Edison's clearance layer parameterises, so the two
   are not separately identifiable: influenza supplies the measured version of the
   same quantity (per-portal efficiency, ≥2 orders) and it cannot be adopted into
   two parameterisations at once (#25).
2. **Influenza `illness_probability`** — **resolved by R3, by deletion.** The
   value was a population fraction and the field a dose-conditional Hill form
   whose monotonicity Carrat's dose-independence rejects, so sourcing 0.67 into
   η would have encoded a dose effect the evidence denies. The η/γ pair is now
   deleted on this arm and presentation reads a dose-independent
   `symptomatic_fraction` of 0.669 (95% CI 0.583–0.745, Grade B, Carrat 2008).
   The Hill form stays on the two active arms, where it is blocked for its own
   reasons (§3.1, §3.2) (#44).
3. **Influenza `surface_decay_log10_per_day`** — R1 moved the influenza bundle
   onto the sourced unit along with everything else, so this item is no longer
   about units: what survives is that a **scalar** cannot express humidity-,
   matrix- and drying-dependent non-exponential survival, and that the value
   itself converts to a half-life slower than both its citations. The remedy is
   no longer read as a covariate-indexed rate:
   [`proposals/surface_decay_biphasic_spec.md`](proposals/surface_decay_biphasic_spec.md)
   argues that the environmental covariates largely collapse on an HVAC-pinned
   ship and that the axis the field cannot express is **time since
   deposition** — decay is biphasic and the boundary is drying — which makes
   this item and #60's shape question one question. Nothing is sourced or
   adopted there, so this row's status, grade and interval are unchanged
   (#44). That spec's §7.1 **refuses** the biphasic form on evidence — the
   wet/dry split appears in saliva and not in the airway surface liquid a ship
   deposit resembles, and the phase ordering reverses between conditions — so
   the remedy is deferred behind #36 rather than pending, and Track A item A4
   is closed on that basis: what is left here is a shape question for the
   screen, not a field that cannot hold its measurement.
4. **SARS-CoV-2 emission × β** — not separately identifiable: dose and
   susceptibility enter the beta-frailty law strictly as a product. Must be
   adopted jointly against a copies-denominated measurement, with β swept over
   the Killingley-to-Zhang & Wang span (#30).
5. **The observation model's ~15 numbers** — jointly constrained by a single
   empirical aggregate which *is* anchor A3, so A3 cannot also be a test of them
   (#23, #27). Track A3 (#48) changed what those numbers are read against and
   adopted nothing: the onset draw is now the *peak* of the course, and
   `severity_model.trajectory_ladder_offsets_by_day` — rungs below that peak,
   one entry per illness day on the same onset axis as the shedding curve —
   says what an observer sees on each day of it. **No profile declares a
   path**, which holds the peak for the whole illness and reproduces the
   previous behaviour exactly, so this row's status, grade and interval are
   unchanged and this register gains no quantity. A declared path is a sourcing
   question owned by this item and by the SARS-CoV-2 severity row in §3.2
   (#31), and it inherits that row's constraint: the ladder reads on age, and
   Tabata/Diamond Princess remains barred.
6. **Norovirus shedding-curve peak magnitude** — 11.0 log10 copies/g is Atmar's
   GI.1 median peak to two decimals, and Kirby measures GII.2 about two logs
   below GI.1 in the same challenge design. Unlike the dose axis, where the GII
   interval contained the shipped GI.1 value, this discrepancy is directional and
   large — and it is the same blocker as item 4 in a different arm: emission
   scale and dose-response enter as a product, so a −2 log emission correction
   applied alone would be absorbed into a quantity we have not identified.
   Declared, not applied, and it has to be adopted jointly with the dose axis if
   at all (#47).

7. **Norovirus airborne emission** — **resolved by R4, by redefinition.** The
   continuous-shedding fraction had no commensurable numerator and denominator:
   shedding is copies/g of stool or vomitus while airborne virus is copies/m³ of
   room air, never measured in the same subjects. The profile now declares
   `airborne_emission_mode = emesis_conditioned` and the Tung-Thompson Grade B
   interval `[7.2e-7, 2.67e-4]`, whose denominator is the virus in one expelled
   bolus. The engine draws log-uniformly per event and drains that mass into the
   zone reservoir once; no point inside the interval was selected. The percent
   table was converted from `7.2e-5%–2.67e-2%`, and the deleted `1e-4` was inside
   the interval only by coincidence across incompatible denominators, not
   corroboration.

## 5. Degrees of freedom, by provenance

Named quantities still free to move, after identifiability collapses some of
them:

| Arm | Free quantities | Notes |
|---|---|---|
| Norovirus | 6 route efficiency multipliers, cabin-localization `f`, one reporting-probability scale | The airborne quantity is a measured interval consumed per emesis event, not a free continuous airborne fraction. The reporting scale is the only one constrained by an anchor, and that anchor is A3. The former single dose knob is **measured inert** above release 8 — the fomite pool dominates so completely that a 14-log10 change is byte-identical |
| SARS-CoV-2 | 1 identifiable composite `(emission × route × transfer)/β`, 6 route efficiency multipliers, a 5-state severity vector, the testing-campaign replica, `airborne_emission_fraction` | The composite is *one* degree of freedom wearing four parameters' clothing. Fitting it while the background is unsourced would absorb their error, which is the failure the whole audit road exists to avoid |
| Influenza | `base_susceptibility` (prior immunity), plus everything in §3.3 | Not active. The susceptibility term must come from seroprevalence or vaccination coverage for the specific season and route, or the arm has a free knob on its most consequential input. R3 removed the dose-conditional presentation pathway (η/γ deleted), so the arm has one fewer free quantity: `symptomatic_fraction` is measured with a CI and is not a knob. |

Two of these were *removed* by measurement rather than by sourcing, which is
worth recording as the register's own precedent: the norovirus dose knob (inert),
and `contact_transfer_fraction` (clears no noise floor anywhere across its whole
sourced interval — correct it, but do not prioritise it).

How many of these the **data** can separate is a different question from how many
are free, and it is the smaller number. Counting the informative cells in the
fleet observable — posted outbreaks by hull class and era against a traffic
background, two of whose eight class-era cells (mega) are unusable — gives an
expectation of order **five** identifiable composites on the norovirus arm
against the nine named above, with the rest pinned by prior or frozen:
[`proposals/fleet_emergence_decision.md`](proposals/fleet_emergence_decision.md)
§4.3. That is a prediction for #36 and #37 to measure, not a count this register
adopts, and it moves no row here.

## 6. Rules this register is held to

Unchanged from `.agents/skills/model-parameter-provenance/SKILL.md`, restated
because this table is where they would first be broken:

- No value in this register may be selected because it improves a scored target.
  Intervals are literature spans, not favourable ends.
- A citation is not adoption. The Evidence column may be full while the State
  column says ⊘; that is the normal case, not an oversight.
- Genome persistence is not infectious-virus persistence, and an RNA-denominated
  pool decayed at an RNA rate preserves non-infectious material as dose. Both
  conversions must be stated wherever they are used.
- A source calibrated on a held-out target is barred, however attractive: Emery
  2020 and Tabata's Diamond Princess severity vector are both excluded on this
  ground.
- Recording a null (∅) is a result. **Nine quantities in §3 are known to be
  unmeasurable as specified**, counted under the same rule stated in §2 (a row
  whose own adoption state carries ∅ or the word refuted); they are to be
  declared, not searched again. The nulls and rejections recorded by sourcing
  wave 1 are itemised in §3.4.

## 7. Keeping it current

Update this register in the same change as any constant, interval, mechanism or
schema change that moves a row. When a tranche document and this register
disagree, the tranche holds the citation and this holds the status — fix the
status here. When the tree and this register disagree, the tree wins: correct the
register and say so in the change.
