# Tranche 19 — influenza surface decay: two studies do report a wet rate, a dry rate and a drying boundary in infectivity units, and the reason not to adopt them is no longer that they are missing

**Status:** Evidence assembled. **No profile constant, engine constant, schema,
grade, interval or adoption state changes in this document.** In particular it
does not adopt `k_wet`, `k_dry` or `t_dry`, and it does not implement the
biphasic form; the refusal in
[`../proposals/surface_decay_biphasic_spec.md`](../proposals/surface_decay_biphasic_spec.md)
§7.1 stands. Nothing here is authoritative about the model; the authoritative
per-quantity status is
[`../parameter_provenance_register.md`](../parameter_provenance_register.md).

**Scope:** R2 of [`../proposals/field_repair_sequence.md`](../proposals/field_repair_sequence.md)
(task #44, influenza surface decay). R2's environmental-covariate scope is
superseded by the biphasic spec; what remained live and is discharged here is
(a) the search for a source that supplies the two regime rates and the drying
boundary, and (b) the **assay-endpoint** resolution (§4).

**Interfaces used, per result.** §1 is the Consensus MCP peer-reviewed-paper
search endpoint, which returns metadata and abstracts. §2 is **full text**,
retrieved as JATS XML from the Europe PMC REST API
(`/{PMCID}/fullTextXML`); all three papers are open access, so no paywall
escalation was needed. **This distinction is the tranche's methodological
finding: every quantity in §2 is in a Results table or regression sentence that
the abstract does not contain, so the abstract-level search result was a false
null.** Where a value below is quoted, the interface that produced it is named.

**Search run:** 2026-09-04. Consensus queries were unfiltered unless a filter is
shown explicitly. The target was one influenza surface experiment reporting
infectious virus at enough time points to identify a wet-phase rate, a dry-phase
rate and the drying boundary, preferably in a respiratory matrix.

## 1. Query log

| # | Exact query and filters | Returned | Relevant result and disposition |
|---|---|---:|---|
| Q1 | `influenza A virus survival on surfaces infectivity time course` — no filters | 20 | Returned the known surface series: Thompson 2017 (plaque assay and qRT-PCR at 1 h, 24 h and weekly), Bean 1982, Oxford 2014 (seven time points), Greatorex 2011, Perry 2016, Qian 2023 and Rockey 2024. It establishes time-resolved infectivity measurements, but no returned abstract reports all three biphasic quantities in one experiment. |
| Q2 | `influenza virus persistence fomites TCID50 multiple sampling timepoints` — no filters | 19 | Returned Irwin 2010's systematic review, Mukherjee 2012 (natural respiratory secretions; immediate, 5, 10 and 30 min sampling), Perry 2016, Thompson 2017, Greatorex 2011 and Qian 2023. This is a positive hit for infectious-virus, multi-timepoint surface data and a null for a jointly measured wet rate, dry rate and drying boundary. |
| Q3 | `biphasic inactivation influenza virus droplet drying surface` — no filters | 20 | Returned Longest 2024's review, Rockey 2024 and Schaub 2024. Rockey reports distinct wet- and dry-phase infectivity kinetics in saliva droplets; Schaub reports rapid salt-driven inactivation before efflorescence and slower first-order inactivation after equilibrium. Neither returned abstract supplies a measured `t_dry` with dispersion together with both rates in the ship's surface-pool setting. |
| Q4 | `influenza virus inactivation respiratory mucus surface infectious titre humidity` — no filters | 20 | Returned Rockey 2024, Pan 2025, Kormuth 2018 and respiratory-matrix studies. It confirms respiratory matrix is available as a selection criterion and infectivity is measured, but the returned results do not identify all three constants. |
| Q5 | `influenza virus surface decay infectivity compared with RNA qPCR same coupons` — no filters | 20 | Returned Thompson 2017 first: plaque assay and qRT-PCR on the same coupons, viable virus to two weeks on steel while PCR remained positive for seven weeks. It also returned Pan 2025. This corroborates the assay-endpoint separation; it does not identify all three biphasic constants. |
| Q6 | `virus survival wet dry phase droplet evaporation inactivation kinetics fomite` — no filters | 20 | Returned general mechanism evidence: Kong 2022, Huang 2021, Longest 2024, French 2023 and Lin 2019. French includes influenza and reports distinct wet- and dry-phase decay rates, but uses cell-culture medium rather than respiratory matrix; the returned abstract does not provide a jointly measured drying boundary and both numeric rates. |
| Q7 | `biphasic inactivation influenza virus droplet drying surface` — `exclude_preprints=true` | 20 | Peer-reviewed-only repeat. Returned Schaub 2024, David 2023 and the Weber 2008 review. It removes preprint ambiguity but does not change the result: biphasic/two-stage mechanisms exist, while a complete adoptable triplet is absent from the returned evidence. |
| Q8 | `influenza A half-life stainless steel human airway surface liquid infectious virus` — no filters | 20 | Returned Qian 2023 first (primary-human-bronchial-epithelial culture matrix, infectious virus, 4.5–5.9 h half-lives on non-copper surfaces at 23% RH), followed by Rockey 2024, Thompson 2017, Perry 2016 and Kormuth 2018. Strong respiratory-matrix infectivity evidence; no complete biphasic triplet. |
| Q9 | `wet phase dry phase first-order inactivation rate constants influenza virus deposited droplet` — no filters | 20 | Returned Rockey 2024 first, Wei 2026 second, and Schaub 2024. Wei reports evaporation-phase rate constants two orders above suspension-phase constants, but it is an airborne aerosol system, not a deposited surface pool. Rockey is deposited respiratory fluid but the abstract does not supply all three numeric quantities. |
| Q10 | `drying time droplet surface virus inactivation two-phase model rate constant before and after drying` — no filters | 20 | Returned French 2023 and Schaub 2024. French directly reports distinct wet/dry rates and experimentally tracks quasi-equilibrium drying, but the matrix is cell-culture medium; no complete respiratory-matrix triplet is reported in the returned abstract. |
| Q11 | `influenza virus surface decay infectivity time-resolved respiratory matrix` — `year_min=2015`, `exclude_preprints=true` | 20 | Explicitly filtered modern peer-reviewed search. Returned Pan 2025 and Rockey 2024 first, then surface-decay studies. Pan measures infectivity in mucin-containing deposited droplets through 4 h; Rockey reports wet/dry phase differences in saliva and respiratory mucus. The filtered search still returned no source reporting an adoptable `k_wet`, `k_dry`, `t_dry` triplet. |

No query returned zero papers. **The abstract-level conclusion drawn from this
table — that no study reports all three quantities — did not survive full-text
retrieval, and is withdrawn.** The dispositions in the fourth column are
therefore recorded as what each abstract supported at the time, not as findings;
§2 supersedes them for Rockey 2024 and French 2023. What the query log is still
good for is the search coverage and the recorded fact that the shape is
widely corroborated.

## 2. Full text: the sourced values, reported and not adopted

The brief for this unit says that if all three quantities are found, they are to
be reported and the unit stops, because adopting them is a different decision.
That is the situation. **Two studies supply the triplet on an infectivity
endpoint, and one of them is in a respiratory matrix.** No value below is
adopted, no value enters a profile, an engine, a schema or a screen box, and
nothing here is a recommendation of a rate.

### 2.1 Rockey et al. 2024 — respiratory matrix, all three quantities (Europe PMC full text, PMC10880610)

*Appl Environ Microbiol*, DOI `10.1128/aem.02010-23`. H1N1pdm09 in **1 µL
deposited droplets of pooled human saliva or airway surface liquid**, infectious
virus, five independent replicates × three technical replicates, 50% RH.
First-order fit `log10(Nt/N0) = k·t`, so **k is in log10 per minute**.

| Quantity | Saliva | Airway surface liquid |
|---|---|---|
| Wet-phase rate | **0.010 ± 0.012 min⁻¹** (95% CI; **not significantly different from zero**) | — |
| Dry-phase rate | **0.036 ± 0.020 min⁻¹** | — |
| Single rate, both phases | — | **0.010 ± 0.0030 min⁻¹**, significantly greater than zero; **no detectable wet/dry difference** |
| Drying boundary, 20% RH | **0.26 h** (0.25–0.27) | 0.25 h (0.23–0.27) |
| Drying boundary, 50% RH | **0.54 h** (0.49–0.59) | 0.47 h (0.43–0.51) |
| Drying boundary, 80% RH | **1.29 h** (1.26–1.31) | 1.26 h (1.23–1.28) |

Drying times are the mean of two independent replicates with the replicate range
in parentheses; the boundary was set by droplet mass plateau and agreed with
visual inspection except at 80% RH, where droplets did not dry within the 2-hour
exposure. Total decay over 2 h reached ~1 log10 at 20% RH and never exceeded
1.1 log10 in airway surface liquid.

Three properties of this result matter more than the numbers, and all three cut
against the biphasic form as the spec proposes it:

1. **The phase split is real in saliva and absent in respiratory mucus.** Airway
   surface liquid — the matrix the selection criterion prefers, and the matrix a
   coughed or sneezed deposit on a ship is closer to — is adequately described
   by *one* rate. Adopting a two-rate form for the influenza arm would import a
   structure this source does not support for that matrix.
2. **Rockey's own conclusion is that inactivation is not a function of drying.**
   Drying times differ by at most 4.2 min between the two matrices while decay
   rates differ severalfold, and inactivation tracked neither bulk protein, salt
   content, nor drying time; the authors attribute the dry-phase rate to residue
   morphology. `t_dry` as a *causal* phase boundary is therefore weaker than
   §7.1 of the spec assumes, even though `t_dry` as a *measured time* now exists.
3. **The observation window is one to two hours, not a voyage.** These constants
   describe a 1 µL droplet drying, not a fomite pool persisting over days.
   `surface_decay_log10_per_day` is a per-day pool rate; 0.036 log10/min is
   ~52 log10/day, which is not a per-day pool law and must not be read as a
   candidate for that field. **This unit computes no such conversion for
   adoption; the arithmetic is shown only to demonstrate the scale mismatch.**

### 2.2 French et al. 2023 — all three quantities, wrong matrix (Europe PMC full text, PMC10128059)

*mBio*, DOI `10.1128/mbio.03452-22`. H1N1pdm09 and Phi6 on polystyrene in
1 × 50 µL, 5 × 5 µL and 10 × 1 µL droplets at 40%, 65% and 85% RH; infectious
virus; quasi-equilibrium (drying) time measured gravimetrically per condition
(Table S2) and used as the phase breakpoint. Table 1 reports **both phase rate
constants for H1N1pdm09 in all nine conditions**, in h⁻¹, e.g. 5 × 5 µL at 40%
RH: evaporation phase **0.52 ± 0.16**, dry phase **0.17 ± 0.06** (the one
H1N1 condition where the two phases differ significantly); 10 × 1 µL at 65% RH:
**0.80 ± 0.43** wet against **0.17 ± 0.08** dry; 1 × 50 µL at 40% RH:
**0.06 ± 0.13** wet against **0.19 ± 0.03** dry — i.e. the ordering reverses.

So the triplet is present and the *sign of the effect is not stable*: French's
own text records that for H1N1pdm09 "differences in decay rates between the two
phases were not consistent", and across the 12 comparable virus × condition
cells the wet phase was faster in 7 and significantly faster in 3. The matrix is
cell-culture medium, which the spec's own selection criterion excludes.

### 2.3 Why this is a stop and not an adoption

The two sources that supply a triplet disagree about which phase is faster, in
matrices that differ, over windows of one to eight hours, in units that are not
the pool's units. Adopting either set would mean choosing a matrix, a droplet
volume, an RH and a time window — four selections this unit is not authorised to
make and which are exactly the freedoms §7.1 of the spec warns that a
three-constant form buys. **Reported, therefore, and stopped.**

## 3. Sources that answer part of the question (Consensus MCP, abstract level)

- **Greatorex et al. 2011**, *PLoS ONE*, DOI
  `10.1371/journal.pone.0027932`: infectivity and RNA on the same coupons at
  multiple times. The same-coupon contrast is 0.06 log10 RNA loss versus
  >4.2 log10 infectivity loss at 24 h. Its incidental observation that a 10 µL
  deposit was dry by 7 h is not a measured drying-time distribution, and rates
  read from the project's chosen time windows would be fitted values rather
  than reported constants.
- **French et al. 2023** and **Rockey et al. 2024**: see §2, where the full text
  supplies what the abstracts did not.
- **Schaub et al. 2024**, *Environmental Science & Technology*, DOI
  `10.1021/acs.est.4c04734`: influenza infectivity in drying 1 µL saline droplets;
  resolves rapid supersaturation-associated inactivation before efflorescence
  and slower first-order loss after equilibrium. It is mechanistically useful,
  not a respiratory-matrix surface parameter set.
- **Qian et al. 2023**, *Applied and Environmental Microbiology*, DOI
  `10.1128/aem.00633-23`: infectious H1N1pdm09 grown in primary human bronchial
  epithelial cultures on nonporous surfaces. It supplies respiratory-matrix
  half-lives and donor variability, not separately identified wet/dry rates and
  a drying boundary.
- **Thompson et al. 2017**, *Journal of Hospital Infection*, DOI
  `10.1016/j.jhin.2016.12.003`: plaque assay and qRT-PCR on the same coupons at
  1 h, 24 h and weekly. Viable virus persisted for up to two weeks on steel;
  PCR persisted for seven weeks. It reinforces that genomic detection is not an
  infectivity decay law.

## 4. Assay endpoint resolution

The model's environmental pools and dose input are denominated in genome copies,
which makes an RNA-rate update dimensionally neat but does not make RNA persistence
a proxy for infection hazard. Greatorex's same-coupon divergence — 0.06 log10 RNA
loss against >4.2 log10 infectivity loss at 24 h — shows that using the RNA rate
can preserve epidemiological availability by roughly four orders after infectious
virus is gone. Thompson's plaque/PCR divergence points in the same direction over
weeks.

The influenza row therefore inherits tranche 5 §1's norovirus resolution:
**the epidemiological decay endpoint is infectivity, not RNA.** Genome-copy pools
must ultimately carry an infectivity-equivalent availability state or conversion;
the mismatch is not repaired by applying a genome-decay rate to the pool.

## 5. Decision

**The assay endpoint is resolved: infectivity, inheriting tranche 5 §1.** That is
this unit's one durable output.

**`k_wet`, `k_dry` and `t_dry` are still not adopted, and the reason has
changed.** They are no longer unsourced — §2 reports two sourced sets in
infectivity units, one of them in a respiratory matrix — so the earlier "nobody
measures this" framing is withdrawn. They are refused now because the sourced
sets are *incommensurable with the field they would fill*: they disagree on which
phase is faster, they are measured over one to eight hours on single droplets
rather than as a per-day pool law, the matrix that the ship setting favours shows
**no** phase split at all, and the study that measures the drying boundary most
carefully concludes that drying does not drive inactivation. Adoption would
require choosing matrix, volume, RH and window — four new freedoms in place of
one scalar, which is the exact trade §7.1 refuses.

No value is adopted, no point is selected from an interval, no golden is touched
and no biphasic engine is implemented. The next decision on this quantity — which
is not this unit's — should start from Rockey's Table 2 and Fig. 5 and French's
Table 1 as reported above, and must not infer a per-day pool rate from a
one-hour droplet experiment.
