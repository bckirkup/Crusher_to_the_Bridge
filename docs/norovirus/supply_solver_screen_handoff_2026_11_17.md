# NORO supply solver screen handoff (2026-11-17)

> **Status:** Handoff record. Reports no new numbers; every figure is quoted from `docs/norovirus/supply_solver_screen_01_readout.md` / `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-01.md` (`Measured at` `6742f1a456e5717cf813c57bc9b3e34bb532fda5`), `docs/norovirus/supply_solver_screen_02_readout.md` / `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-02.md` (`Measured at` `455f9ff788e85580a8253438fb4137ff69e22146`), and `docs/norovirus/supply_solver_screen_03_readout.md` / `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-03.md` (`Measured at` `c6c3c25fbabefa7ed918cba55311ceec231dbba3`).

## 1. The question

Does replacing the legacy ordered intra-epoch hand-contact updates with the shipped `transmission.contamination_solver: continuous` RK4 hand↔surface↔food flow change supply-contamination outcomes across the expedition, classic, spirit, and mega p06 passenger-venue cells? The screens paired `discrete` (labelled baseline) vs `continuous` on the same stratified supply seeds per hull (`station_lots` contaminated + quiet controls, `single_line_receipt`, `declared_receipts`). Success was an uncertainty-qualified paired association in posting frequency, posted-conditional passenger reported-case AR, VSP trigger epoch/day, or passenger/crew role partition; failure was an uninformative screen with overlapping ranges or too few posted pairs.

## 2. Current hypothesis

Across these four hulls the solver arm is not the first-order driver at posting resolution. On expedition the contaminated strata posted on every cell in both arms; on classic/spirit the contaminated strata had posting headroom but quiet controls never posted and paired differences stayed sign-test unresolved; on mega the frozen stratified supply seeds almost never reach the 3% VSP wire, leaving only one both-posted pair and no solver separation. The continuous default should stand unless a targeted mechanism witness shows a specific flux/dose consequence below posting resolution, or a posting-frequency screen on a hull with headroom shows the solver moves `vsp_trigger_epoch is not None` itself.

## 3. Evidence for

- `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-01.md` (`Measured at` `6742f1a4`): expedition 88/88 cells SUCCEEDED; contaminated posting 16/16, 10/10, 10/10 on both arms; quiet 0/8 both arms; paired pax reported-AR diffs −0.2% / −0.3% / +0.8% with sign p 0.791 / 1.000 / 0.508; VSP-epoch diffs −3.5 / +2.0 / −1.5 epochs with p 0.454 / 0.344 / 1.000; all role-partition sign tests p ≥ 0.180.
- `docs/norovirus/supply_solver_screen_01_readout.md` (`Measured at` `6742f1a4`): posted-conditional pax reported-AR ranges overlap in every expedition contaminated stratum (e.g. `station_lots` discrete 2.9–19.6% vs continuous 3.5–17.7%).
- `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-02.md` (`Measured at` `455f9ff7`): classic+spirit 176/176 cells SUCCEEDED; `station_lots` posted 9/16 discrete vs 10/16 continuous on cls and 7/16 vs 8/16 on spr; receipt strata posted 2–6/10; quiet controls posted 0/8 on both hulls and both solvers; paired pax AR sign p ≥ 0.1797 and VSP-epoch p ≥ 0.5.
- `docs/norovirus/supply_solver_screen_02_readout.md` (`Measured at` `455f9ff7`): posted-conditional pax reported-AR medians are ~3.5–6.1% on cls/spr contaminated strata with overlapping ranges; role partition shows no solver separation.
- `docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-03.md` (`Measured at` `c6c3c25f`): mega 88/88 cells SUCCEEDED; `station_lots` posted 1/16 on each solver arm (the same seed on both), `single_line_receipt` and `declared_receipts` posted 0/10, quiet controls 0/8; the single posted pair had pax reported AR 0.0455 discrete vs 0.0445 continuous and VSP epoch 56 vs 75; paired sign tests uninformative (`posted_both=1`).
- `docs/ledger/NORO-HAND-CASCADE-01-CONTINUOUS-FLOW.md`: the continuous solver was shipped as default with discrete retained as the labelled baseline; these screens are the paired-seed/campaign witness that entry said was still open.

## 4. Evidence against / unexplained

- The screens measure posted outcomes, not hand↔food/surface flux or per-host dose. A solver effect that only appears below posting resolution, or only on non-supply transmission, would not show here.
- `continuous_path_calls` is not a clean solver-arm witness (`tools/noro_diag/hand_occupancy.py` increments it on a stool-outcome condition); arm identity comes from `parameters.tier_id` / the frozen manifest.
- On cls/spr `station_lots`, continuous VSP-epoch upper ranges are wider than discrete (cls 52–212 vs 52–69; spr 36–174 vs 35–88) while paired sign tests remain unresolved; treat that as a tail observation to explain, not as a result.
- Expedition posting was saturated on contaminated strata, so it could not test posting frequency; cls/spr had posting headroom but still showed no paired solver separation; mega had almost no posting headroom realized by the frozen supply seeds, so it could not test the solver at all.
- Mega receipt strata posted 0/10, which gives only an upper bound on posting frequency, not evidence that receipts are safe or that the solver arms agree.

## 5. PRs this session

- #1275 — `transmission.contamination_solver: continuous` default RK4 intra-epoch hand contamination flow; discrete remains the labelled baseline; ledger `NORO-HAND-CASCADE-01-CONTINUOUS-FLOW`.
- #1280 — expedition p06 supply solver screen campaign spec, frozen design/seeds, digest-pinned image, S3 manifest/seed upload; campaign `noro_supply_solver_screen_01`.
- #1281 — expedition screen readout, ledger entry `NORO-SUPPLY-SOLVER-SCREEN-01`, and the first handoff revision; no engine or constant change.
- #1282 — classic+spirit supply solver screen campaign spec, frozen design/seeds, digest-pinned image, S3 manifest/seed upload; campaign `noro_supply_solver_screen_02`.
- #1283 — classic+spirit screen readout, ledger entry `NORO-SUPPLY-SOLVER-SCREEN-02`, and the handoff update through screen 02; no engine or constant change.
- #1292 — mega supply solver screen campaign spec, frozen design/seeds, digest-pinned image, S3 manifest/seed upload; campaign `noro_supply_solver_screen_03`.
- #1293 — mega screen array approval and Batch parent job IDs in the campaign ledger.
- This change — mega screen03 readout, ledger entry `NORO-SUPPLY-SOLVER-SCREEN-03`, campaign-ledger measurements, and this updated handoff; no engine or constant change.

## 6. Running jobs

None. Screen 01 finished 88/88 cells SUCCEEDED, screen 02 finished 176/176 cells SUCCEEDED, and screen 03 finished 88/88 cells SUCCEEDED; parent job IDs and jobdef revisions are recorded in `campaigns/noro/supply_solver_screen_01/LEDGER.md`, `campaigns/noro/supply_solver_screen_02/LEDGER.md`, and `campaigns/noro/supply_solver_screen_03/LEDGER.md`. Results prefixes: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/`, `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_02/`, and `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/` (local mirrors `out/noro_supply_solver_screen_01/`, `out/noro_supply_solver_screen_02/`, and `out/noro_supply_solver_screen_03/` are not committed).

## 7. What is now void

Nothing. No committed measurement is withdrawn by these stages; `docs/norovirus/norovirus_open_ledger.md` §1 is unchanged. The continuous-vs-discrete screens do not invalidate the continuous default or any FOOD-SUPPLY measurement.

## 8. The single open decision

Decide whether the next bounded session (a) designs a mega-appropriate seed/burden stratum or a posting-frequency-targeted solver screen so the solver arms can be separated where posting headroom exists, or (b) treats mega supply contamination at these burdens as a weak posting driver and returns to the supply contamination-rank vs posted AR/timing question on hulls where posting is not saturated. Evidence that would settle it: a paired posting-frequency screen on mega (or another hull with headroom) showing solver-arm separation in posting rate/timing, or a contamination-rank screen showing rank predicts posted AR/timing better than the solver arm.

## 9. Do not reopen

- Do not fit any constant to VSP/Park/attack-rate/passenger-crew anchors; these screens are not anchor fitting.
- Do not flip `transmission.contamination_solver` back to `discrete` on the basis of these screens; continuous remains the default and discrete the labelled baseline.
- Do not use `transmission.hand_redeposit_mode="carriers"` as an amplification arm without a stream-preserving carriers witness/null contrast.
- Do not treat the FOOD-SUPPLY seed census as a posted-AR measurement; it is a boarding/prevalence witness only.
- Do not read `outbreak_occurred` as posting; posted means `vsp_trigger_epoch is not None`.
- Do not treat quiet-control zero postings as evidence about contaminated strata.
- Do not treat the single posted mega `station_lots` pair as solver separation; the paired screen is uninformative at `posted_both=1`.
