# NORO supply solver screen handoff (2026-11-17)

> **Status:** Handoff record. Reports no new numbers; every figure is quoted from `docs/norovirus/supply_solver_screen_01_readout.md` and `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-01.md`, measured at `6742f1a456e5717cf813c57bc9b3e34bb532fda5`.

## 1. The question

Does replacing the legacy ordered intra-epoch hand-contact updates with the shipped `transmission.contamination_solver: continuous` RK4 hand↔surface↔food flow change expedition p06 supply-contamination outcomes enough to matter? The screen paired `discrete` (labelled baseline) vs `continuous` on the same 44 stratified supply seeds (`station_lots` contaminated + quiet controls, `single_line_receipt`, `declared_receipts`) on `fl_exp_12d_sens_p06_paxv` / `expedition_cruise_450`. Success was an uncertainty-qualified paired association in posted-conditional passenger reported-case AR, VSP trigger epoch/day, or passenger/crew role partition; failure was an uninformative screen with overlapping ranges.

## 2. Current hypothesis

On these supply seeds the solver arm is not the first-order driver of posted AR, VSP timing, or role partition: all contaminated strata posted on both arms, quiet controls did not post, and paired differences were small with sign-test p ≥ 0.180 and overlapping ranges. The continuous default should stand unless a targeted mechanism witness shows a specific flux/dose consequence that this screen could not resolve.

## 3. Evidence for

- `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-01.md` (`Measured at` `6742f1a4`): 88/88 cells SUCCEEDED; contaminated posting 16/16, 10/10, 10/10 on both arms; quiet 0/8 both arms; paired pax reported-AR diffs −0.2% / −0.3% / +0.8% with sign p 0.791 / 1.000 / 0.508; VSP-epoch diffs −3.5 / +2.0 / −1.5 epochs with p 0.454 / 0.344 / 1.000; all role-partition sign tests p ≥ 0.180.
- `docs/norovirus/supply_solver_screen_01_readout.md` (`Measured at` `6742f1a4`): posted-conditional pax reported-AR ranges overlap in every contaminated stratum (e.g. `station_lots` discrete 2.9–19.6% vs continuous 3.5–17.7%).
- `docs/ledger/NORO-HAND-CASCADE-01-CONTINUOUS-FLOW.md`: the continuous solver was shipped as default with discrete retained as the labelled baseline; this screen is the paired-seed/campaign witness that entry said was still open.

## 4. Evidence against / unexplained

- The screen is a screen, not a mechanism proof: it measures posted outcomes, not hand↔food/surface flux or per-host dose. A solver effect that only appears below posting resolution, or only on non-supply transmission, would not show here.
- `station_lots` VSP-epoch range compressed on continuous (discrete 50–283 vs continuous 40–112) while the paired median/sign test stayed unresolved; treat that as a tail observation to explain, not as a result.
- `continuous_path_calls` is not a clean solver-arm witness (`tools/noro_diag/hand_occupancy.py` increments it on a stool-outcome condition); arm identity comes from `parameters.tier_id` / the frozen manifest.

## 5. PRs landed this session

- #1275 — `transmission.contamination_solver: continuous` default RK4 intra-epoch hand contamination flow; discrete remains the labelled baseline; ledger `NORO-HAND-CASCADE-01-CONTINUOUS-FLOW`.
- #1280 — expedition p06 supply solver screen campaign spec, frozen design/seeds, digest-pinned image, S3 manifest/seed upload; ledger/campaign `noro_supply_solver_screen_01`.
- This change — screen readout, ledger entry `NORO-SUPPLY-SOLVER-SCREEN-01`, and this handoff; no engine or constant change.

## 6. Running jobs

None. All eight array parents completed with 88/88 children SUCCEEDED; parent job IDs and jobdef revisions are recorded in `campaigns/noro/supply_solver_screen_01/LEDGER.md`. Results prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/` (local mirror `out/noro_supply_solver_screen_01/`, not committed).

## 7. What is now void

Nothing. No committed measurement is withdrawn by this stage; `docs/norovirus/norovirus_open_ledger.md` §1 is unchanged. The continuous-vs-discrete screen does not invalidate the continuous default or any FOOD-SUPPLY measurement.

## 8. The single open decision

Decide whether the next bounded session should (a) accept this solver screen as a null for supply-contamination outcomes and return to the expedition supply contamination-rank vs posted AR/timing question, or (b) first run one targeted mechanism witness (hand↔food/surface flux or per-host dose challenge) on the largest paired AR/VSP-diff seeds to see whether the unresolved differences are real below posting resolution. Evidence that would settle it: a paired-seed mechanism witness showing a monotone flux/dose consequence on the same seeds, or a second independent seed stratum reproducing the same sign pattern.

## 9. Do not reopen

- Do not fit any constant to VSP/Park/attack-rate/passenger-crew anchors; this screen is not anchor fitting.
- Do not flip `transmission.contamination_solver` back to `discrete` on the basis of this screen; continuous remains the default and discrete the labelled baseline.
- Do not use `transmission.hand_redeposit_mode="carriers"` as an amplification arm without a stream-preserving carriers witness/null contrast.
- Do not treat the FOOD-SUPPLY seed census as a posted-AR measurement; it is a boarding/prevalence witness only.
- Do not read `outbreak_occurred` as posting; posted means `vsp_trigger_epoch is not None`.
