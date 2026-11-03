# Consensus tranche 54 — the COVID exhaled-emission level (`environmental_release_log10_per_day`, #30)

> **Status:** Reference.

Evidence retrieved 2026-11-02 for item #30 (Edison task 2): a sourced
exhaled-rate level for the `sars_cov2_resp` arm, comparable to influenza's
Yan 2018 derivation, replacing `dose_adjustment = 3.0` as the emission
fallback. Retrieval: targeted Consensus `search` passes with
`include_full_text_chunks: true`, each query naming the quantity **and**
unit ("exhaled SARS-CoV-2 RNA copies per hour / per minute"). Origins are
marked per row (`R` Results, `Tn` Table n, `Ab` Abstract only, `Me`
Methods, `F` Figure, `?nr` queried, not returned).

## 1. What is measured — exhaled RNA rate in COVID-19 patients

| Source | n | Measured exhaled rate | Origin | Grade |
|---|---|---|---|---|
| Alsved et al. 2022, *Clin Infect Dis* (DOI 10.1080/23744235.2022.2140822) | 38 | median **70 / 110 / 80 copies min⁻¹** breathing / talking / singing; higher nearer onset | Ab (per tranche 9; not re-queried this pass) | B |
| Coleman et al. 2021, *Clin Infect Dis* ciab691 (DOI 10.1093/cid/ciab691) | 59 | **63–5,821 N-gene copies per 30–60-min activity**; 85.4% of the load in the ≤5 µm fine fraction | R (Results chunk) | B |
| Ma et al. 2021, *Clin Infect Dis* ciaa1283 (DOI 10.1093/cid/ciaa1283) | 86 | up to **10⁵ viruses min⁻¹** in earlier-stage patients; exhaled concentrations 10⁵–10⁷ copies m⁻³ | R (Discussion) | B |
| Li et al. 2021, *Front Med* (DOI 10.3389/fmed.2021.604392) | — | **1,710–4,600 copies min⁻¹** | R | B |
| Malik et al. 2023, *Infect Prev Pract* (DOI 10.1016/j.infpip.2023.100299) | 2 | **8.6 × 10³ – 2 × 10⁵ copies h⁻¹** | Ab | C (n=2) |
| Zheng et al. 2022 (MQL ref 82) | 25 | 11 of 25 Omicron patients at **4.4–5.8 × 10⁷ copies h⁻¹** | Ab + R (Discussion, per tranche 9) | B |
| Lane et al. 2023 (medRxiv) | — | ~80 copies min⁻¹ | ?nr this pass | C (preprint) |
| Zhou et al. 2023 (DOI 10.1016/S2666-5247(23)00101-5) | 18 | correlates emission with nasal load, publishes **no emission/specimen-titre ratio** | Ab | — |

Two notes on pointers. Edison's "Coleman 2022" resolves to **Coleman
2021** (CID ciab691): the repository's own `droplet_field_split_spec.md`
cites that DOI under both years, and no 2022 Coleman exhaled-aerosol
paper exists in the index. Zheng 2022 has no DOI in the repository; it
enters through the MQL reference list at tranche 9.

## 2. The bracket and the selected level

The arm's declared measured bracket is **[4.2 × 10³, 5.8 × 10⁷]
copies per epoch** (tranche 9 §1: Alsved breathing floor to Zheng top),
4.1 orders wide. Per the sourcing rule for a wide measured interval —
*a stated central value or the midpoint, and say which* — the shipped
point is the **geometric midpoint**, 4.94 × 10⁵ copies h⁻¹ ≈
1.19 × 10⁷ copies day⁻¹, giving

```
environmental_release_log10_per_day = 9.0 − log10(1.19e7) ≈ 1.93
```

where 9.0 is the `shedding_curve_log10` peak the level normalises.
Alsved, Coleman, Ma, Li and Malik all sit inside the span; no single
study is the level, and the 4.1-log span remains the declared sweep
axis, not a fit.

## 3. The measured finding: the level and the shipped fraction are an inconsistent pair

Code truth (verified in `orchestrator_epoch._deposit_agent_emission`):
per-shedder-epoch airborne deposit = `sv × airborne_emission_fraction`,
`sv = SimClock.amount_per_epoch(10^(curve − level) × host × strain)`.

- At the shipped level (peak sv = 4.94 × 10⁵ copies/epoch), deposit =
  **24.7 copies/epoch**, ~170× below the bracket floor; even at the
  bracket's top level (level = −0.14) it reaches only 2.9 × 10³.
- The in-bracket fraction at the shipped level is **[8.5 × 10⁻³, ~1.2]** —
  i.e. a fine-share-scale factor. The measured share **0.85** (Coleman
  2021, inside the [0.76, 0.92] interval tranche 27 §6 licenses **exactly
  once this level fix lands**) satisfies it at every measured level.
- Shipped 5e-5 was always a unit-bearing titre→emission conversion on a
  nasal level, not a share (tranche 9 §1, register §392). It stays
  untouched: adopting the measured share is the follow-on Edison decision
  this inconsistency hands off, outside #30's non-goals.

Also corrected in the record: tranche 9 §1's "5 × 10⁴ copies per epoch"
and the register's "7.6× above Alsved's talking median" omit both the
release normaliser and the per-day→epoch division; the shipped arm's
actual peak deposit was ~2.1 copies/epoch.

## 4. What this licenses

- `sars_cov2_resp.environmental_release_log10_per_day` = **1.93**,
  Grade B (direct measurements, clinical not maritime setting; midpoint
  of a declared interval, selected against no anchor).
- `dose_adjustment` removed as the COVID emission fallback; it stays on
  `norovirus_gii4` and `sars_cov2_ba5` and dormant consumers, and the
  Theta-fit and Presidio-workspace overrides that relied on it were
  migrated to pin `environmental_release_log10_per_day` explicitly so
  their run semantics are bit-identical.
- Nothing about `airborne_emission_fraction`: value unchanged, the
  inconsistency recorded, the fine-share adoption left as the open
  follow-on.
