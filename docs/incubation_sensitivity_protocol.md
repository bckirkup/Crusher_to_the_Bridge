# Do the published conclusions survive the incubation refinement?

Companion to [`incubation_reconciliation_plan.md`](incubation_reconciliation_plan.md),
which says *what* has to be reconciled. This document says how to test whether
already-published conclusions hold under the refined infection mechanism, in the
order the author set: paper 3 merges, then paper 2 sensitivity, then paper 1.

The design principle throughout: **paired arms, same seeds, one switch.** The
switch is the presence of the `incubation` block on the pathogen profile
(representation A vs the fixed 1-day fallback C). Everything else — platform,
seeds, `dose_adjustment`, surveillance configuration — is held. A conclusion
"holds" if its *sign and ordering* survive; a conclusion whose absolute number
moves but whose ranking does not is a re-statement, not a retraction.

## 0. The campaign already in flight is an asset, not a casualty

The paper 2 campaign now running was submitted from a container image built
before the merge, so it is generating line lists under the fixed-onset model.
Do not stop it: those runs are the control arm of every test below, at zero
extra compute. The sensitivity work is a *paired re-run* of a subset, not a
re-run of the campaign.

(Anything submitted after the merge from a freshly built image will be on the
new mechanism, so campaign submissions from here on must record which arm they
belong to. That is one field in the manifest, and it is cheaper to add now than
to infer later from timestamps.)

## 1. Paper 2 — port-of-call sentinel attribution

Paper 2 infers port hazards λ_p from ship-side onsets. Its exposure is direct:
the simulator generates the onsets, and the Stan likelihood convolves candidate
infection epochs with a *fixed pathogen-level* incubation kernel. The refinement
changed the data-generating process; the estimator did not change.

Three conclusions to test, in decreasing order of exposure.

**C2.1 — port separability / MDHR.** The claimed minimum detectable hazard ratio
rests on the incubation IQR being small relative to the inter-port interval. The
refinement *narrows* the realized IQR at calibration-regime doses (19 h in the
catalog vs 12 h at `dose_adjustment=3`, 5 h at the dose floor). The prediction is
therefore that paper 2's MDHR is **conservative** — attribution should get easier,
not harder. Test: re-run the port-recovery fit on paired arms and compare
posterior λ_p intervals and the recovered-vs-true hazard ratio at fixed power.
This is the one conclusion that could move in the paper's *favour*, and it is the
one worth reporting either way.

**C2.2 — bias from kernel mis-specification.** Under the old model the DGP was a
fixed 24 h spike fitted with a 33 h lognormal; under the new one it is a
28.8 h-median lognormal, dose-shifted. The mis-specification is smaller but no
longer of a form the kernel can represent. Test: on both arms, compare the
posterior mean λ_p against the ledger's ground-truth introductions
(`LineListRecord`/`IntroductionRecord` already carry both), and report bias, not
just interval width. A bias that shrinks confirms the refinement; a bias that
changes *sign* by port would mean the fixed kernel is now the binding error and
R1/R2 become prerequisites for the paper's numbers rather than tidy-up.

**C2.3 — the wastewater channel's marginal value.** Currently off in the fitted
model (clinical-only, pending reads on line lists), so unexposed. Note and skip.

Compute: the paired subset is the 72 hazard × fleet × `R_onboard` cells at
reduced seeds, not the full 3360. One session plus a modest re-run.

## 2. Paper 1 — VSP degradation, detection timing, and the economics

Paper 1's conclusions split cleanly by what they depend on, and the split is
what makes this cheap.

**Unexposed (attack rate and epidemic size).** Ever-infected was unchanged
within noise across the paired arms. Any conclusion phrased over final attack
rate, cumulative infections, or transmission-route attribution needs no re-run —
it needs a stated model version.

**Exposed (anything with a clock).** Time-to-detection, VSP threshold crossing
epoch, symptomatic person-time (5–12% lower at fixed `dose_adjustment`),
quarantine-bed occupancy, and every wearable / cascade lead-time result read the
onset distribution. The paired-arm test is the same as above with detection
epoch and OIS/cost ledger as the outcomes.

**Exposed and calibration-coupled.** The VSP degradation campaign pins
`dose_adjustment=10.6`. Under the refinement that pin no longer corresponds to
the AGE rate it was chosen to match, so the degradation *curve* is being read at
a shifted operating point. This is the one paper 1 result that needs R6 (the
tier re-fit) before its numbers can be restated; the qualitative claim — that
degradation is monotone in the swept dial — should survive, and that is what the
paired arms establish.

**Insurance / wearable ROI.** ROI is a difference between arms that both contain
the same incubation mechanism, so it is far less exposed than either arm alone —
the same argument the shore-side benefit model rests on. Expect the ratio to
survive and the absolute dollar figures to move.

## 3. Acceptance rule

For each conclusion, record one of three verdicts, with the paired-arm evidence
attached:

- **holds** — sign and ordering unchanged; restate with a model-version note.
- **holds, magnitude restated** — ordering unchanged, numbers move; publish the
  updated figure and the delta.
- **requires re-fit** — the conclusion is stated at a calibrated operating point
  that the refinement moved. Blocked on R6.

The failure mode to avoid is the one already hit once in this work: concluding
from unchanged golden fixtures that nothing moved. Goldens are change detectors
at destroyer doses; they say nothing about the calibration regime, which is
where all three papers live.

## 4. Order of work

1. Merge paper 3 (this PR).
2. R1 + R5 — make the sentinel catalog a projection of the profiles with a drift
   test. Cheap, and paper 2's tests are more interpretable once the two kernels
   cannot silently disagree.
3. Paper 2 paired-arm runs → C2.1, C2.2.
4. R3 — incubation for the remaining 13 profiles, since multi-pathogen results
   in either paper currently quote a 1-day incubation for measles.
5. R4 + R6 — dose anchoring, then the VSP tier re-fit.
6. Paper 1 paired-arm runs, restating what R6 moved.
