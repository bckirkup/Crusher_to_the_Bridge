# The retained arrays, re-read within a dose regime

**Status: finite-sample readout of arrays already on disk. No campaign was
re-run, no constant was changed, no interval was narrowed, and nothing here
selects a value.** Produced by
`telemetry_buffer/observation_model/adj_stratified_readout.py`.

## Why stratify

`environmental_faecal_release_log10_g_per_epoch` (`adj`) sits in the exponent
of a host's emission, and the bounded-gate box sweeps it linearly over
[4, 24] — twenty orders of magnitude of release. Ledger §4 item 00 measured a
switch near `adj ≈ 6–7`: below it a voyage transmits, above it a voyage's
infections are close to its boarding imports. Every campaign since `BERTH-01`
averaged its mechanism contrast across that switch, so a mechanism was
credited with whatever it did on ships that could not transmit at all.

Each retained point carries its own `adj`, so the contrasts can be re-cut
without re-running anything. The strata are cut at the ledger's switch, not at
a quantile of the design:

| stratum | `adj` | points, of 256 |
|---|---|---|
| live | < 5.5 | 19 |
| transition | 5.5–6.5 | 13 |
| import-only | ≥ 6.5 | 224 |

Six seeds a point, so 114 / 78 / 1,344 voyages per arm. **A stratified contrast
is a seventh of the design**: a difference bounded at ±0.06–0.10 pp over the
whole box is bounded at ±0.6–1.0 pp inside the transmitting strata, so this
re-read can only rule out large effects, and its "nulls" are correspondingly
weaker statements than the marginal ones it replaces.

## 1. The strata are three different ships

Control arm (`CONTACT-ARCH-02` reprise; the three-arm control agrees to within
0.3 pp):

| stratum | pax inf AR | crew inf AR | posted | reported-channel A5 |
|---|---|---|---|---|
| live | 31.56% | 13.09% | 97.4% | 2.56 |
| transition | 14.48% | 5.46% | 62.8% | 2.75 |
| import-only | 3.64% | 1.60% | 4.5% | 2.61 |

The marginal readouts every campaign has reported (pax ≈ 3.6%, postings
13.5–18.6%) are a mixture of a ship that always posts and a ship that almost
never does, in the proportions the box happens to supply. That much confirms
ledger item 00.

## 2. What the re-read changes

**A5 is not a mixture artefact, and item 00's second consequence is corrected.**
The ledger recorded A5 ≈ 2.0–2.4 as a blend of an import-only ratio of 1.81 and
an explosive-corner ratio of 2.2. On the reported channel the anchor actually
scores, the ratio is **flat across all three regimes** — 2.56 / 2.75 / 2.61 —
against a target of ≈ 3.5. So the crew excess is not hidden by the mixture: the
model reproduces the same deficient ratio on a dead ship, a transitional ship
and a burning ship, which makes it a missing-structure result rather than a
resolution one, and removes the hope that it would appear once the dose scale
was fixed.

**The large contact arms were not null, they were diluted.** Read inside the
transmitting strata (arm − control, paired on point and seed):

| arm | live Δpax | transition Δpax | marginal Δpax (as reported) |
|---|---|---|---|
| `CONTACT-ARCH-01` low | −2.56 ± 0.79 | −1.52 ± 0.94 | −0.13 ± 0.10 |
| `CONTACT-ARCH-01` mid | +11.11 ± 0.62 | +7.18 ± 0.90 | +1.44 |
| `CONTACT-ARCH-01` high | +15.19 ± 0.70 | +12.95 ± 0.89 | +2.21 |
| `CONTACT-ARCH-02` high, τ=0.5 h | −4.65 ± 0.75 | −2.51 ± 0.83 | ≈ control |

The marginal numbers were roughly an eighth of the effect, which is the live
fraction of the box. Dwell saturation likewise turns out to be a real,
signed mechanism inside a transmitting regime rather than a return to the
control: against the control, `mid_tau1` is −3.01 ± 0.69 pp and `high_tau05`
−4.65 ± 0.75 pp on passengers in the live stratum, i.e. τ overshoots past the
uniform contact rate rather than restoring it.

**The small arms stay small, and are now bounded rather than unmeasured.**
`SURF-KO-01` is +0.12 ± 0.49 pp (live) and −1.46 ± 0.69 pp (transition); the
φ arms are within ±2.5 pp everywhere and only φ = −1 is signed in both strata
(−2.38 ± 0.58 live, −2.46 ± 0.77 transition, and it lowers infection). These
were reported as nulls and remain small, but the honest statement is now a
bound inside a regime, not a null over a box most of which was inert.

**The import-only stratum is still above the posting anchor.** It posts 4.5%
of voyages against A9's 0.6–1.6%, so the model over-posts by ~3–7× *with
essentially no onboard transmission*. Splitting it by the swept boarding
prevalence:

| passenger boarding prevalence | pax inf AR | posted |
|---|---|---|
| 2.69% | 3.00% | 2.38% |
| 3.06% | 3.36% | 4.46% |
| 3.44% | 3.59% | 3.27% |
| 3.81% | 4.61% | 7.74% |

Even the lowest sourced quartile posts 2.4%. **No reduction in transmission of
any size reaches A9 from here**; the binding terms are the boarding-prevalence
interval and the observation model, which is where `#467`'s posting floor came
from and where item 00 did not look. Two further readings: the infection attack
rate exceeds the boarding prevalence in every quartile (3.00% against 2.69%,
4.61% against 3.81%), so the "import-only" stratum is not transmission-free —
that residue is the hand/surface/food chain, which
`fomite_pool_denominator_reconciliation.md` shows `adj` never scales; and
because of that, stratifying by `adj` can never test a fomite-side arm, whose
strata differ only in routes it does not touch.

## 3. What this does not license

The transmitting strata are not a regime the model has been shown to belong
in; they are the corner of an unsourced interval where arithmetic permits
transmission. Reading a mechanism there is a conditional statement ("given a
ship that transmits, this arm moves passengers by X"), and choosing to stand
there because the anchors come out better would be fitting `adj` to an anchor
through the back door. Nothing is adopted, no stratum is declared, and the
interval stays [4, 24] until the refit the ledger is waiting on.
