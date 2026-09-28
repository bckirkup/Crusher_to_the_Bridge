# CABIN-FLOOR-03
**Date:** 2026-09-28
**Commit:** 27efdbd4
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 27efdbd4

Recomputation over the FLU-RHYTHM-01 campaign artifacts (cells run at
`07d9856c`).

Recalibration of the confined-attack floor, filed as the resolution of
FLU-RHYTHM-01 §4's floor-spec finding. Corrected spec:
`docs/confined_attack_floor_spec.md`.

## The defect in the old band

The 15–25% "sourced floor" bounded a different quantity than documented.
Its numbers trace to the norovirus shipboard cabinmate pair (Wikswo 2011
15.4%, Chimonas 2008 24.1%), transplanted into the generic CABIN-FLOOR
check; on the flu row it was documented as "Lau 3–38%", and Lau's PCR-SIR
spread does not contain a 15–25% band. On flu it was effectively drawn
around FLU-DELIVERY-01's realized n=34 point estimate (7/34 = 20.6%), i.e.
it bounded the noisy observed attack, not the declared-k expectation.

No recomputation from the declared `k` produces 15–25%: evaluated at the
declared sourced interval `k ∈ [2e-4, 1e-3]` on the measured confined-slot
dose distribution, the expected confined-mate SAR spans **[3.7%, 12.1%]**
pooled off-arm (n=9047), per-class edges [3.1–4.8%, 10.4–15.7%]. Even the
n=34 upper-tail dose draw (classic s8105/8106) reaches only 18.5% at k_hi.

## Corrected quantity and band

The band bounds the **expected confined-mate SAR**,
`E[1 − exp(−k · delivered_p_dose)]` over confined slots — not the realized
pooled attack as a hard edge. Band = `[E(k_lo), E(k_hi)]` on the slot dose
distribution the cabin-mate geometry produces under declared conditioning;
declared k lands inside by construction (monotone in k). Realized attack is
compared n-aware via Wilson overlap. Full derivation and per-class table in
`docs/confined_attack_floor_spec.md`.

At declared k=6e-4 the expected SAR is 7.4–11.3% per class per arm
(pooled 8.7% off); observed pooled attack 10.5–14.6% sits inside or
marginally above each cell's band through its Wilson interval — consistent
with the ~2–4 pp conversion-truncation residual named in the spec. The flu
arm is therefore internally consistent at declared k: the earlier
"below floor" readings were a miscalibrated band, not a delivery or rhythm
defect.

## Consequences

- `tools/flu_rhythm_ab_readout.py` replaces `FLOOR = (0.15, 0.25)` with the
  derived band computed per (class, arm) from pooled `slot_rows`
  `delivered_p_dose` at `K_SOURCED_INTERVAL = (2e-4, 1e-3)`;
  `in_floor_band` becomes a Wilson-overlap check.
- The scored anchor is unchanged: audit F1 keeps Lau 2012 [0.03, 0.38]; the
  floor band is an internal-consistency check, not an anchor and never a
  fitting target.
- Ledgers whose verdict tables carried "Sourced floor: 15–25%"
  (`CABIN-FLOOR-01`, `CABIN-FLOOR-02`, `FLU-DELIVERY-01`, `FLU-RHYTHM-01`,
  `FLU-DOSE-01`) are measurement records and are not rewritten; each carries
  a pointer to this entry. For norovirus the Wikswo/Chimonas pair remains
  that pathogen's own sourced floor — the withdrawal applies to its reuse as
  a generic band, and specifically to the flu arm.
