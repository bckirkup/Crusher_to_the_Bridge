# Register fragment — norovirus airborne route (task #42, tranche 13)

> **Merged.** This fragment was merged into [`../../parameter_provenance_register.md`](../../parameter_provenance_register.md) by the sourcing-wave-1 integration pass, with the lead's corrections applied at merge time. It is kept as the audit trail of what the sourcing unit proposed; it is **not** a live proposal, and where it and the register differ the register holds the status.

**Status:** Merged into the register; kept as the audit trail. Proposed §3.1 (`norwalk_gi`)
replacement rows for two quantities, recorded in
[`../../parameter_provenance_register.md`](../../parameter_provenance_register.md).
Evidence and rejections behind them:
[`../consensus_tranche_13_airborne_fraction.md`](../consensus_tranche_13_airborne_fraction.md).
**No shipped value changes, and no value is recommended for adoption.**

Column order as in register §3.1: Quantity | Shipped | Class | Evidence / interval | Origin | State | Task.

**Superseded in the tree.** R4 replaced the `airborne_emission_fraction` row
this fragment proposed: the quantity is now `airborne_emission_mode =
emesis_conditioned` with the Tung-Thompson per-event interval, so the null
recorded below holds only for the *continuous-shedding* definition it was
searched under. The register carries the current row.

| Quantity | Shipped | Class | Evidence / interval | Origin | State | Task |
|---|---|---|---|---|---|---|
| `airborne_emission_fraction` | 1e-4 (renamed from `surface_deposition_fraction`, value unchanged) | **C** unsourced-assumed — **∅ null confirmed by search** | **No study reports emission to air as a fraction of a host's shedding**, for norovirus or, in six unfiltered Consensus queries, for any pathogen: shedding is measured in copies/g of stool or vomitus and airborne virus in copies/m³ of room air, never in the same subjects, so the fraction has no commensurable numerator and denominator ([tranche 13](literature/consensus_tranche_13_airborne_fraction.md) §3.1). What is measured instead is **air concentration** — Alsved 2019 5–215 copies/m³ (86 samples, 26 patients), Bonifait 2015 1.35 × 10¹–2.35 × 10³ genomes/m³ (48 samples, 8 facilities), Rupprom 2024 GII 3.4 × 10¹–5.0 × 10³ copies/m³ (60 samples), Kittigul 2025 GII 1.5 × 10²–5.5 × 10³ copies/m³ (WWTP aerosols), Boles 2021 383–684 MNV copies/m³ after a seeded toilet flush — all **Grade B concentrations, not emission rates** (§3.2). **The SARS-CoV-2 row's "derivable" note has no norovirus counterpart**: there is no measured norovirus emission rate to be the numerator (§2, query 5, which returns no norovirus paper at all). The one measured aerosolised fraction, Tung-Thompson 2015 (MS2, simulated vomiting, n = 3/condition, 41 L chamber, corrected for 8.5% sampler efficiency), is **7.2 × 10⁻⁵ % – 2.67 × 10⁻² %**, i.e. a fraction of **7.2 × 10⁻⁷ – 2.67 × 10⁻⁴** — **percent, and misreading the table as fractions overstates it by two decades** — and its denominator is the virus in one expelled bolus, not the host's shedding (§3.3) | not recorded — proposed before axis 3 existed; see [tranche 20](../consensus_tranche_20_full_text_reverification.md) §1 | — **not blocked, and still unsourced.** The ⊘ field defect stays resolved; the suspicion that the field has no measurable referent is now **searched and confirmed**, not assumed. Adoption is possible only by **redefining the field** as an emesis-event-conditioned aerosolisation fraction, for which Tung-Thompson 2015 would be a Grade B source; as a fraction of continuous shedding, nothing measures it. The shipped 1e-4 falls inside Tung-Thompson's fraction range near its top, which is **coincidence across incompatible denominators and is not provenance** | #42 done (search); redefinition open |
| `airborne_half_life_hours` | 1.1 | **I, cross-pathogen** — **∅ null for human norovirus, reconfirmed** | **No measurement of airborne human norovirus decay exists**; human NoV is not routinely culturable, so airborne NoV work reports RNA persistence, not infectivity decay. The shipped 1.1 remains van Doremalen's SARS-CoV-2 figure, mis-cited there too (van Doremalen measures 2.7 h). Nearest measurement, **Grade B, named calicivirus surrogate**: Zargar 2025 (*J Virol Methods* 335:115144) feline calicivirus in a 25 m³ room-sized aerobiology chamber, six-jet Collison nebuliser, soil load, gelatin slit sampler, PFU assay, **22 ± 2 °C and 50 ± 10% RH** → biological decay **0.0081 ± 0.0031 log10 PFU/m³/min**, which as a unit transformation is t½ = **0.62 h (0.45–1.00 h on ±1 SD)**. **Abstract-verified only** — full text paywalled, so "biological decay" (i.e. corrected for physical loss), the fit form and the run count are unverified; Reckitt-funded air-purifier study. Supporting bounds, no rates: Purhonen 2024 (MNV infectious to 90 min), Alsved 2020 (drying drives infectivity loss), Rupprom 2024 (GII RNA to 120–240 min), Sanka 2026 (MS2/ΦX174 infectious in air at 2 h, absent at 24 h), Donaldson 1976 (FCV RH-sensitive across 30–70%, no rate). Rejected: Dubuis 2020 (ozone), Buonanno 2024 (far-UVC), thermal/surface/water persistence, all SARS-CoV-2 aerosol work ([tranche 13](literature/consensus_tranche_13_airborne_fraction.md) §4–§5) | not recorded — proposed before axis 3 existed; see [tranche 20](../consensus_tranche_20_full_text_reverification.md) §1 | ∅ **null stands for norovirus.** Either declare the field unsourced, or adopt the FCV surrogate interval **[0.45, 1.00] h** as an explicitly cross-species Grade B stand-in — an adoption decision this tranche does not take. Note the shipped 1.1 sits **outside** that interval; recorded as a fact about the surrogate measurement, not as an argument for any replacement value | #39 |

Relative links above are written as they would appear **in the register** (i.e.
from `docs/`), not from this fragment's own directory.

## Section-of-origin ledger

Not recorded: this fragment predates the register's section-of-origin axis. The
retrieval ledger covering its citations is
[tranche 20](../consensus_tranche_20_full_text_reverification.md) §1.
