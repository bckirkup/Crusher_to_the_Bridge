# Register fragment — `covid-dose-denominator` (unit for task #30, tranche 15)

**Additive only.** Proposed replacement for the `dose_response.alpha` / `beta`
row of `docs/parameter_provenance_register.md` §3.2 (SARS-CoV-2,
`sars_cov2_resp`), plus one new row for the conversion factor, which the register
does not currently carry as a quantity. The lead merges; nothing here is adopted,
and no shipped value changes.

**State: evidence recorded — the denominator itself stays ∅ null in copies, and
the conversion that would rescue Killingley is recorded as a Grade B interval
~2.7 logs wide.** Source:
[tranche 15](consensus_tranche_15_covid_dose_denominator.md).

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `dose_response.alpha` / `beta` | 0.18 / 58.0 | C (attribution withdrawn twice, independently) | **No SARS-CoV-2 ID50 in genome copies exists**, from any design — tranche 15's eight unfiltered Consensus queries found none, including a query written specifically to find a characterisation of the Killingley inoculum in copies. Independent dose measurements are all in infectious units: Killingley 2022 (*Nat Med*, DOI 10.1038/s41591-022-01780-9) **10 TCID50 → 18/34 (~53%)** naive adults, the only naive human dose point; Jackson 2024 (*Lancet Microbe*, DOI 10.1016/s2666-5247(24)00025-9) escalates **10¹ → 10⁵ TCID50** in 36 **seropositive** adults and induces **no sustained infection at any dose** (5/36 transient), so the slope is not a virus property once hosts are immune; hamster ID50/MID figures span ~5 logs in infectious units (Rosenke 2020 ID50 5 infectious particles, DOI 10.1080/22221751.2020.1858177; Lin 2022 MID ≤14 PFU, DOI 10.1038/s41598-022-09218-5; Blaurock 2022 MID 10⁻³ TCID50 orotracheal, DOI 10.1038/s41598-022-19222-4). Prentiss and Riediker stay **rejected as attack-rate-fitted**, and tranche 15 rejects three further fitted candidates on the same ground: Marc 2021 (*eLife* 10.7554/elife.69302, load→transmission fitted to transmission pairs), Iyaniwura 2024 (*PNAS* 10.1073/pnas.2406303121) and Xu 2025 (*Epidemics* 10.1016/j.epidem.2025.100843), both within-host models fitted to the Killingley data | ⊘ joint, **and ∅ null in copies** — the existing sweep and "adopt neither endpoint, no attack-rate-fitted value" stand unchanged. **Provenance note:** the row's parenthetical "≈ 10³–10⁴ copies" for 10 TCID50 implies ~10²–10³ copies per TCID50, which is **1–3 logs below every measured ratio** in the new row below; that conversion is unsourced, not measured | #30 |
| **Copies per infectious unit** (new row — the unit bridge between the emission side, in copies, and every independent dose measurement, in infectious units) | not a profile key; used implicitly wherever a TCID50 dose is quoted in copies | **B as an interval, by setting** | **Clinical respiratory/environmental specimens: 10⁴·² – 10⁶·² N-gene copies per PFU** (Gaussian fit on log10, mean **10⁵·² ± 1.0 SD** = 160,000; 151 infectious specimens of 459, 75 patients; Lin 2022, *Sci Rep*, DOI 10.1038/s41598-022-09218-5, Results/Fig. 8a). **Propagated culture supernatant: 2.95 × 10³ – 2.98 × 10⁴ E-gene copies per PFU** across five isolates — D614G 29,800, Alpha 11,700, Gamma 8,930, Delta 12,500, Mu 2,950 (Zapata-Cardona 2022, *Iran J Microbiol*, DOI 10.18502/ijm.v14i3.9758), corroborated by Lin's own ~10⁴:1 for culture-harvested virus. **PFU↔TCID50 is itself an offset of 0.59–0.96 log10**, variant-dependent (same paper). **Combined honest bound ≈ 3 × 10³ – 1.6 × 10⁶, ~2.7 logs.** Three studies designed to test whether a fixed ratio exists say it does not: Puhach 2022 (*Nat Med* 10.1038/s41591-022-01816-0) copies-vs-FFU **R² = 0.15–0.40** in 565 NPS; Despres 2022 (*PNAS* 10.1073/pnas.2116518119) infectious units per E-gene copy **5.9× / 3.0×** higher for Delta / Epsilon than Alpha (14.3× / 6.9× on subgenomic E), n = 162; Porter 2025 (*Access Microbiol* 10.1099/acmi.0.000732.v3) the ratio moves **> 5 logs across one infection course** | ✓ **evidence recorded, interval only — no central value licensed.** Grade B for each setting; the ~1–1.5-log specimen-vs-supernatant split, the 3–14× variant spread and the >5-log within-host swing are **not** measurement error and must not be collapsed to a point. **Composition with Killingley is left to the lead and is not performed**: it would chain a TCID50→PFU step (0.59–0.96 log10 measured, and published conversions of this exact inoculum disagree ~8×: ~7 PFU vs Xu 2025's "≈ 55 PFU"), this ~2.7-log ratio, and a single-dose 53% point that cannot identify a two-parameter dose-response — **> 3 logs composed**, wider than the sweep already carried | #30 |

**Definition problems** (full statement in tranche 15 §7): the model needs one
constant and the field measures a distribution; "infectious unit" is three
different assays; every ratio is measured in a swab or supernatant, never in
aerosolised room-aged virus, which is what the airborne path delivers; and the
naive-host dose-response may not be the shipboard quantity, since a ship
population is mostly not naive.

**Nulls to record** (tranche 15 §8): no ID50 in genome copies; **no measurement
of copies per TCID50 in a respiratory specimen** (the specimen-side ratio is per
PFU; the TCID50-side work is on culture stocks); no characterisation of the
Killingley inoculum in copies; and no fixed clinical conversion factor — the last
being a positive finding, not a gap.
