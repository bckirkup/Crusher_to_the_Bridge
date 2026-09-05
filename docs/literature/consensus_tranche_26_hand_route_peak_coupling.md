# Tranche 26 — the shedding-curve peak is also the hand route's denominator (#47, item C3)

Status: **evidence record, 2026-09-05.** Track C item C3 of
[`../proposals/defect_resolution_plan.md`](../proposals/defect_resolution_plan.md) §5.
No constant moves. The register row this tranche updates is
[`../parameter_provenance_register.md`](../parameter_provenance_register.md) §3,
`shedding_curve_log10` peak magnitude, plus one new row for the hand-route
reference pair.

Tranche 16 sourced the GII faecal peak in its own units — **[7.0, 9.1] log10
copies (or genome equivalents) per gram of wet stool**, figure-digitized from
the public `shedding-hub` dataset — against a shipped 11.0 that is Atmar 2008's
**GI.1** median. It recorded the value as *declared, not applied*, on the
grounds that emission scale and dose-response enter the hazard as a product
(#366) and every dose figure is void pending refit.

This tranche does not revisit that interval, and does not propose a
GI→GII correction factor. It asks the narrower question C3 was opened for —
**can the peak be applied?** — and returns a mechanism finding: the peak has a
**third** consumer that tranche 16 did not name, and that consumer is the only
place in the enteric chain carrying a *measured absolute load*.

## 1. The coupling, read off the engine

`KorkinAgent.get_pathogen_hand_target` — the fixed point the hand pool
relaxes toward in `TransmissionCore._replenish_hand` — is

```
hand target (GEC per hand) = 10^3.86 × 10^(curve[idx] − 11.0) × host multiplier
```

and `KorkinAgent.get_pathogen_shedding` is

```
environmental emission = 10^(curve[idx] − release offset) × host × strain
```

Both read the **same** curve index. So a peak replacement is a single
multiplicative rescale of magnitude `10^(peak − 11.0)` applied simultaneously
to the environmental pool *and* to the hand pool's fixed point. Measured at the
shipped GII candidates on a symptomatic host at one epoch, release offset 4.0:

| Curve peak | Emission (per epoch) | Hand target (GEC/hand) | Ratio to shipped |
|---|---|---|---|
| 11.0 (shipped, GI.1) | 4.167 × 10⁵ | 7.244 × 10³ | 1 |
| 9.1 (GII interval top) | 5.246 × 10³ | 9.120 × 10¹ | 1.259 × 10⁻² |
| 7.0 (GII interval floor) | 4.167 × 10¹ | 7.244 × 10⁻¹ | 1.0 × 10⁻⁴ |

The two constants in that expression were bare literals at the call site before
this change; they are now `HAND_LOAD_LOG10_GEC` and
`HAND_LOAD_REFERENCE_PEAK_LOG10` in `engines/infection_dynamics_bridge.py`,
carrying their source, grade and origin at the definition, and two tests hold
the coupling — one change-detector that the hand target equals Liu's measured
load when the curve sits at the reference peak, and one graded test over four
peaks that both routes move by the same factor.

**Why this blocks adoption rather than merely accompanying it.** The faecal
peak is an *assay reading on stool*; the hand load is an *assay reading on a
hand*. `3.86 − 11.0 = −7.14` is therefore an implicit bridge — approximately
**7.2 × 10⁻⁸ g of stool per hand** — and it is a derived quantity no study in
this tranche or the previous ones measures. Applying the GII interval to the
curve alone would leave that bridge fixed and so move the hand load to
**10^1.96–10^(−0.14) GEC per hand**, i.e. below one copy at the interval floor,
purely as a side effect of a faecal-titre change. That is not a defensible
consequence of a stool measurement, and it is exactly the class of silent
rescale the register exists to catch.

## 2. Liu 2013, the number the hand route is pinned to

**Liu, Escudero-Abarca, Jaykus et al. 2013**, "Laboratory Evidence of Norwalk
Virus Contamination on the Hands of Infected Individuals", *Appl Environ
Microbiol* 79:7875, DOI `10.1128/aem.02576-13`. 159 hand-rinse samples from six
experimentally infected and six uninfected subjects; **18/71 (25.4%)** of
infected-subject samples presumptively positive by RT-qPCR, mean
**3.86 log10 genome-equivalent copies per hand** among positives.

- Genogroup: **GI.1 (Norwalk, 8fIIa lineage)** — the same challenge lineage the
  shipped 11.0 peak comes from, and the same lineage as the shipped
  α = 0.111 / β = 32.81 row (tranche 23).
- Grade **B**: direct measurement, analogous setting — an experimental
  challenge ward, not a cruise ship.
- Origin **Ab**: the mean and the positive fraction were read from the abstract
  as returned by Consensus. The paper body was not retrieved, so the
  distribution behind the mean (spread, per-subject variation, whether 3.86 is
  arithmetic on logs or a log of a mean) is **?nr**.

The genogroup agreement is the operative point. The shipped pairing
(GI.1 peak, GI.1 hand load, GI.1 dose-response) is internally consistent in
lineage. Replacing one member with a GII value breaks that consistency, and
nothing retrieved here supplies the GII members needed to replace the set.

## 3. What was searched, and what is not there

Eleven Consensus queries. Recorded so the same ground is not re-covered.

| # | Query | Result |
|---|---|---|
| 1 | norovirus genome copies per hand fingertip contamination challenge study | Transfer and decontamination studies only; **no** GII stool peak |
| 2 | norovirus GII.4 hand contamination quantitative fingerpad virus recovery | Sharps 2012, Tuladhar 2013 — transfer efficiencies, not loads |
| 3 | norovirus GII stool peak viral load copies per gram cruise ship outbreak passengers | Outbreak/review literature (Mouchtouri 2024, Bert 2013, Isakbaeva 2005, Wikswo 2011); **no** quantified stool titre in a cruise population |
| 4 | norovirus hand contamination naturally infected patients quantitative RT-PCR copies per hand | **Rate limit exceeded** — retried as #5/#6 |
| 5 | norovirus hand contamination naturally infected patients quantitative copies per hand rinse | Liu 2013 (challenge, not natural); nothing in naturally infected hosts with a per-hand concentration |
| 6 | norovirus GII infected patients hand swab viral load outbreak hospital quantification | Environmental-swab prevalence, no per-hand concentration |
| 7 | faecal mass residue on hands after defecation micrograms indicator | Indicator-organism and hygiene-behaviour literature; **no** measurement of the stool mass the −7.14 bridge asserts |
| 8 | Mattioli norovirus GII hands mothers Bagamoyo Tanzania concentration genome copies hand rinse | Mattioli 2015: GII detected on ≈**5%** of maternal hand rinses in both seasons; **no** concentration exposed |
| 9 | norovirus GII hand rinse concentration log10 genome copies caregivers households | Prevalence/detection framing only |
| 10 | norovirus GII concentration on mothers hands Bagamoyo Tanzania hand rinse genome copies per hand | As #8; concentration remains **?nr** |
| 11 | Liu Norwalk virus hand rinse log10 genomic equivalent copies per hand infected volunteers | Liu 2013, the §2 numbers, at abstract level |

Three nulls worth stating as nulls rather than as gaps in the reading:

1. **No quantitative hand load in a GII-infected host.** Mattioli 2015 is the
   closest naturally-exposed design and reports detection frequency, not
   concentration. So the hand route has **one** measured absolute level, and it
   is GI.1.
2. **No study measures stool titre and hand load in the same subjects.** That
   pairing is the measurement that would license the −7.14 bridge (or replace
   it), and it is what would make the peak adoptable independently of the hand
   route. Its absence is structural: hand studies dose or enrol for hand
   sampling, faecal time-course studies quantify stool.
3. **No stool peak in a cruise population.** Grade A remains unreachable for
   the peak from the demand side as well as the supply side.

Two families returned repeatedly and are recorded as **not** answering the
question, so they are not re-retrieved:

- **Transfer efficiencies.** Sharps 2012 (`10.4315/0362-028x.jfp-12-052`): GII
  fingertip → stainless steel and small fruits ≈58–60% wet, far lower dry,
  recipient contamination often >4–5 log genomic copies. Tuladhar 2013:
  MNV-1/GI.4/GII.4 finger pad ↔ surface ↔ food in PCR units, wet/dry and
  sequential dependence. These constrain the transfer *fractions* already
  sourced in tranche 12, not a load or a titre.
- **Hand decontamination.** Liu 2009 (`10.1128/aem.01729-09`): finger-pad
  Norwalk reductions, soap/water 0.67–1.20 log10, water rinse 0.58–1.58,
  sanitizer 0.14–0.34. Tuladhar 2015: soap/water removes more GI.4/GII.4
  genomic copies than alcohol. These constrain hand hygiene, not the peak.

## 4. Decision

**C3 closes as declared-not-applied, with the coupling recorded.** The GII
interval [7.0, 9.1] log10 copies/g stands as sourced, figure-digitized,
Grade B, `logU` on the log axis — and stays out of
`data/pathogens/active_profiles.json`.

The reason is now stronger and more specific than tranche 16's: the peak is not
merely non-identifiable against emission scale and dose-response (#366), it is
the **reference denominator of the hand route**, so no assignment to it is a
statement about faecal titre alone. Adopting the interval requires the dose axis
(#43, tranche 23, span [1.32 × 10³, 1.69 × 10⁴] gEq, unresolved) **and** either
a GII hand-load measurement or a measured stool-mass-per-hand bridge to replace
the −7.14 implicit in the code. Neither exists.

No refit is performed, and no point inside the interval is selected. The three
GI.1 members of the shipped set (peak, hand load, dose-response row) move
together or not at all, and #36/#37 should carry the peak as one factor of the
enteric exposure scale rather than as an independent axis.
