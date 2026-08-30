# Post-#346 anchor pilot: what the dose-accumulation fix moved, measured

Runs: 120 (expedition_cruise_450, classic_cruise_1900 x dose 2.0/2.5/3.0 x
none_response/syndromic_comp85 x seeds 940-949), 0 failures, executed at
`d557f39` — merged `main` with #346 (persistent host susceptibility, cumulative
dose) in and **nothing else changed** relative to the pre-fix pilot at
`7a9b439`. Same hulls, same doses, same strategies, same seeds, same scorer,
same take-off conditioning (peak prevalence >= 10). Table:
`anchor_report_hull_resolved.md`. Pre-fix table:
`../postmerge_anchor_pilot_7a9b439/anchor_report_hull_resolved.md`.

This is a matched-seed before/after of one code change. It is not a fit and no
parameter was tuned between the two runs.

## Prediction registered before the run

Stated to the PI before the pilot executed: infection AR falls hard,
ill/infected rises to roughly 0.34-0.45, A1 and A2 both still miss, and if
ill/infected landed much above 0.45 at a realistic attack rate something else
was wrong. Recording it here because the alternative — reading the direction
off the result — is unfalsifiable.

## Matched pairs, natural-history arm (`none_response`)

| Hull | Dose | Take-off | A1 ever-ill (pax) | inf AR (pax) | A2 ill/inf | A4 reported AR |
|---|---:|---:|---:|---:|---:|---:|
| expedition | 2.0 | 10/10 -> 8/10 | 0.2152 -> **0.1487** | 0.7974 -> **0.4067** | 0.264 -> **0.341** | 6.02% -> **3.48%** |
| expedition | 2.5 | 10/10 -> 9/10 | 0.1202 -> 0.0759 | 0.7358 -> 0.3196 | 0.187 -> 0.237 | 3.80% -> 1.90% |
| expedition | 3.0 | 8/10 -> 6/10 | 0.0649 -> 0.0379 | 0.4889 -> 0.1946 | 0.131 -> 0.196 | 1.90% -> 1.74% |
| classic | 2.0 | 10/10 -> 9/10 | 0.1783 -> **0.1622** | 0.7941 -> **0.4649** | 0.224 -> **0.364** | 3.88% -> **3.89%** |
| classic | 2.5 | 10/10 -> 9/10 | 0.0571 -> 0.0516 | 0.6977 -> 0.3303 | 0.101 -> 0.186 | 1.31% -> 1.35% |
| classic | 3.0 | 8/10 -> 9/10 | 0.0482 -> 0.0187 | 0.5982 -> 0.2048 | 0.090 -> 0.179 | 1.04% -> 0.45% |

Direction is uniform across all six natural-history cells: infection attack
rate falls by 1.8-2.9x, ill/infected rises by 1.3-2.0x. Both are the signature
of removing the 24x-per-day Bernoulli inflation, and neither anchor was used to
choose anything.

## Anchor verdicts after the fix

| Anchor | Target | Measured (no response, dose 2.0) | Verdict |
|---|---|---|---|
| A1 ever-ill (pax) | 0.10-0.22 | expedition 0.149, classic 0.162 | PASS at dose 2.0, both hulls |
| A2 ill/infected | 0.59-0.81 | 0.341 / 0.364 | **FAIL, ~1.8x low** (was ~2.5-3x low) |
| A3 reported/symptomatic | 0.35-0.45 | 0.259 / 0.216 | FAIL low pre-recognition; 0.51-0.98 under response |
| A4 reported AR vs VSP IQR | exp 4.51-13.60%, classic 4.46-7.76% | exp 3.48% FAIL, classic 3.89% FAIL | **both below floor** |
| A5 reported pax:crew | 2.5-4.5 | 0.97 / 0.85 | **FAIL, structural, unchanged** |

## The result that matters most is A4, and it is a loss

Before the fix, expedition's reported attack rate sat inside the VSP IQR at
6.02%. That was the one endpoint agreement the model had, and it was already
labelled a cancellation rather than a fit: infection AR was ~3.6x too high and
ill/infected ~3x too low, and the reported endpoint is (roughly) their product.

#346 corrects the inflated factor and leaves the deflated one where it was. The
cancellation therefore breaks, and expedition falls to 3.48% — below the 4.51%
IQR floor. **Correcting a defect moved the model from passing A4 to failing
it.** That is the expected consequence of removing one of two compensating
errors, and it is the strongest available evidence that the earlier pass was
not a fit. Any earlier statement that the model reproduced expedition's VSP
attack rate is withdrawn.

Classic is the instructive contrast: its reported AR is unchanged to three
decimals (3.88% -> 3.89%) while infection AR halved and ill/infected rose 1.6x.
The two moves cancelled almost exactly. Same defect, same fix, opposite visible
effect on the endpoint — which is what an endpoint built from a product of two
wrong factors does. Endpoint agreement in this model carries very little
information about whether the mechanism is right.

## Honest limits of this measurement

- **Fixed dose is not fixed epidemic size.** Take-off fell in five of six
  natural-history cells (e.g. expedition 2.0: 10/10 -> 8/10), because the same
  nominal dose now establishes fewer infections. The comparison is therefore
  "same input" rather than "same outbreak", and the conditioning set changed
  slightly between the pairs. The direction of every move is far larger than
  this effect, but the exact magnitudes carry it.
- **Ten seeds per cell**, take-off-conditioned, so cells with 4-6 take-offs
  (the syndromic arms at dose 2.5-3.0) are noise-dominated and should not be
  read as trends.
- **A2 is still the discriminating failure.** At 0.34-0.36 against 0.59-0.81 it
  is closer but not close, and the corrected model welds it to infection AR
  through the same dose: at AR ~0.22 the homogeneous form cannot exceed
  ill/infected ~0.41. A1 and A2 remain jointly unsatisfiable without exposure
  structure. The fix was necessary and is not sufficient, exactly as stated in
  advance.
- **A5 did not move and cannot** be moved by dose or severity; it needs a real
  passenger/crew reporting asymmetry.

## What this withdraws

Every hourly-epoch infection attack rate and ill/infected ratio quoted before
`d557f39` — the v4 campaign, the pre-fix anchor pilot, and the figures given to
the PI in conversation. They were inflated (infection) and deflated (illness)
by the per-epoch dose-response defect. The pre-fix table is retained in
`../postmerge_anchor_pilot_7a9b439/` as the record of what was wrong, not as a
result.
