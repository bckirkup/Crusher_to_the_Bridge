> **Status:** Handoff record (2026-11-16), authored against `main` = `2271f2c1`
> after #1256 merged. Reports **no new numbers**: every figure is quoted from the
> ledger entry, campaign readout, or committed ranking artifact that measured
> it, with that entry's `Measured at` SHA where it has one. Read
> `docs/norovirus/norovirus_open_ledger.md` §1 before quoting any dose figure —
> every dose figure in the repository remains withdrawn pending the refit.

# Food-supply expedition screen handoff — 2026-11-16

## 1. The question

Does **contaminated food-supply boarding burden** — the per-seed supply census
from `noro_supply_seed_scan_01` — correlate with **posted outbreak attack rate
and timing** on the expedition hull, and does the supply provenance arm
(`station_lots` vs `single_line_receipt` vs `declared_receipts`) change that
relation?

The proposed screen is expedition-first: `expedition_cruise_450` on the pinned
SENSITIVITY-01 p06 passenger-venue cell (`fl_exp_12d_sens_p06_paxv`), using the
same p06 contract as the seed scan and worst-case readouts unless the successor
design freezes a different cell. The endpoint is posted-conditional, not
voyage-averaged: `posted` means `vsp_trigger_epoch is not None` (either-channel
reported-case counter crossed the 3% VSP rule), **not** `outbreak_occurred`.
Primary observables are passenger reported-case AR and VSP epoch/day; secondary
observables are crew reported-case AR, passenger/crew infection AR, overall AR,
and route/channel witnesses. Quiet controls and near-post seeds are required so
the screen does not condition on posting by construction.

Success is a predeclared, uncertainty-qualified association between supply-burden
rank and posted-conditional AR/timing on expedition, with the provenance arms
compared on the same seed rule. Failure is an uninformative screen: too few
contaminated seeds convert to posts, no association resolves, or the design
cannot separate supply burden from hull scale, venue realization, or the
observation funnel. This is a measurement screen, not a fit: no constant may be
chosen to make an anchor come out right.

## 2. Current hypothesis

The seed census can enrich contaminated boarding events cheaply, but supply
burden is not sufficient for posted-AR scale by itself. The four-hull worst-case
probe found the highest passenger reported AR on the **expedition** receipt seed
(18.67%) while the mega receipt seed was lower (4.55%), so expedition is the
right hull to test whether burden rank predicts posted AR/timing rather than the
mega crew-heavy posting mix. The working hypothesis is that burden rank will
predict ignition/timing more cleanly than final passenger reported AR, because
the observation funnel and secondary/fomite dynamics dominate conversion; the
screen exists to measure that split, not to assume it.

## 3. Evidence for

- **`FOOD-SUPPLY-01-SEED-SCAN`** (`docs/ledger/FOOD-SUPPLY-01-SEED-SCAN.md`,
  measured at `357dfac06103ed6b496e2428099d13b8d5117ddc`; PRs #1246/#1249):
  378,600 one-epoch seed scans, 0 errors. On expedition (`exp`, 56,000 seeds per
  arm), `station_lots` boards a contaminated lot on 5,354 seeds (9.561%),
  `single_line_receipt` serves a contaminated lot on 1,051 seeds (1.877%), and
  `declared_receipts` serves one on 1,065 seeds (1.902%). Lot size/titre
  distributions are similar across arms; receipt arms contaminate only
  shellfish/salad_leaf/fresh_produce, and `declared_receipts` spends half its
  contaminated receipts on venue-empty indices under the single pinned Dining
  zone. These JSONL seed lists are reusable for stratified full-fidelity runs.
- **`FOOD-SUPPLY-01-WORST-CASES`** (`docs/ledger/FOOD-SUPPLY-01-WORST-CASES.md`,
  measured at `b310ac70d111475c4a53a7a1e0eb5bc3c5f6ebd4`; PR #1251): the four
  highest-burden contaminated seeds all posted. The expedition selected seed
  (`declared_receipts` 917326, burden_est 6.448e8 exact receipt mass) posted at
  VSP epoch 63 / day 3 with passenger reported-case AR 18.67%, passenger
  infection AR 37.34%, overall AR 28.67%, and final status `LOCKDOWN`. Across
  hulls, burden did not map monotonically to passenger reported AR: expedition
  had the highest passenger reported AR and mega the lowest (4.55%).
- **`FOOD-SUPPLY-01-REDEPOSIT-WORST`** (`docs/ledger/FOOD-SUPPLY-01-REDEPOSIT-WORST.md`,
  measured at `7a3d3d7828dd34f96c58b10a75fe040b19ffde5a`; PRs #1253/#1255/#1256):
  on the four mega worst seeds, `shedders_only` posted 4/4 while `carriers`
  posted 1/4 and lowered passenger reported-case AR on every pair. Post-readout
  witness extraction showed the carrier path fired but the same arm collapsed
  the non-shedder stool/hygiene stream and reduced quarantine person-epochs, so
  `carriers` is a bundled/confounded arm, not a clean amplification test.
- **Committed ranking artifacts**: `campaigns/noro/supply_worst_cases_01/ranking.md`
  and `ranking.json` freeze the burden rule used for the worst-case selection:
  receipt lots use exact `quantity_g * lot_titre_gec_per_g`; `station_lots` use
  `lot_servings * lot_titre_gec_per_g * 150 g` because serving mass is drawn
  later. The expedition screen should reuse or explicitly amend this rule before
  any cell runs.

## 4. Evidence against / unexplained

- The seed scan measures **boarding prevalence only**. It does not measure
  posting, attack rate, roles, or timing; a contaminated lot is a primer, not a
  posted voyage.
- The worst-case examples are **top-burden single seeds**, not rates. The
  expedition result is an existence proof that a high-burden receipt seed can
  produce a large passenger-reported excursion on a small hull; it does not
  establish that burden rank explains variance across seeds.
- Receipt arms have much lower served-lot yield than `station_lots` on every
  hull, and `declared_receipts` loses half of its contaminated receipts to
  venue-empty indices under the pinned single-Dining-zone cells. A receipt-first
  expedition screen would be compute-poor unless the design accepts a small
  contaminated sample.
- The `carriers` hand-redeposit arm is confounded: it adds non-shedder carrier
  deposits but also suppresses the non-shedder stool/hygiene/self-contact stream
  and is not stream-neutral. Do not use it as an amplification arm for the
  expedition screen; keep `shedders_only` unless a stream-preserving carriers
  witness exists.
- `docs/norovirus/norovirus_open_ledger.md` §1 still governs: every dose figure
  in the repository is void pending a refit. Posted AR/roles/timing are the
  current scoreable surface for this screen, but dose-level mechanism claims
  remain withdrawn.

## 5. PRs landed this session

Food-supply stage, in dependency order:

1. #1232 — `FOOD-SUPPLY-01` provisioning receipt/lot layer design.
2. #1235 — default-off receipt/lot layer implementation.
3. #1238 — receipt-arm smoke ledger.
4. #1239 — carry `station_zone_pin` through receipt lots.
5. #1240 — pinned re-smoke ledger.
6. #1243 — pinned canary ledger.
7. #1246 — `noro_supply_seed_scan_01` scanner + campaign.
8. #1249 — seed-scan readout ledger.
9. #1251 — worst-case example campaign, ranking, and readout.
10. #1253 — mega worst-seed redeposit contrast campaign.
11. #1255 — redeposit readout ledger.
12. #1256 — carrier redeposit witness attribution ledger amendment.

Earlier NORO-HAND-CASCADE probes (#1207–#1230) also landed in this session as
background for the hand-redeposit attribution; they are not inputs to the
expedition screen except for the carriers-confound caution in §4/§9.

## 6. Running jobs

None from this session. The supply seed scan, worst-case examples, and mega
redeposit contrast arrays all SUCCEEDED; job IDs and image digests are in the
campaign ledgers. No expedition screen has been submitted.

Durable artifact prefixes:

- Seed census: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_seed_scan_01/`
- Worst-case examples: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_01/`
- Mega redeposit contrast: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_worst_cases_redeposit_01/`

## 7. What is now void

No committed measurement is withdrawn by this handoff. The standing withdrawals
in `docs/norovirus/norovirus_open_ledger.md` §1 still apply, including every
dose figure pending refit. The four-seed redeposit panel is directional evidence
for a confounded arm, not an effect size; it must not be quoted as a carriers
effect or used to flip defaults.

## 8. The single open decision

**Freeze the expedition screen contract before any full runs.** The next
session must choose exactly one primary design and write it as a frozen design
file before cells run:

- Primary arm: `station_lots` only, receipt served-lots only, or paired
  `station_lots` vs receipt served-lots on the same seed rule. The seed scan
  yields argue for `station_lots` first on expedition (5,354 contaminated seeds
  vs ~1.06k served receipt lots per arm), while the worst-case probe argues the
  receipt layer can still produce the largest passenger-reported excursion.
- Stratification: burden rank/deciles plus item-line, lot-count, venue, and a
  quiet-control stratum; endpoints and stop rule frozen before submission.
- Budget/gate: campaign-preflight smoke + canary (≥20 seeds at one cell) before
  any array, per the campaign rules.

The evidence that would settle the arm choice is already committed: expedition
seed yields and lot-size/titre similarity from `FOOD-SUPPLY-01-SEED-SCAN`, and
the single-seed expedition receipt result from `FOOD-SUPPLY-01-WORST-CASES`.

## 9. Do not reopen

- Do not fit any constant to VSP/Park/attack-rate anchors, and do not flip
  `food_supply`, `provisioned_source`, or hand-redeposit defaults from this
  screen.
- Do not treat the seed census as a posted-AR measurement; it is a boarding
  witness only.
- Do not use `transmission.hand_redeposit_mode="carriers"` as an amplification
  arm unless a stream-preserving carriers witness/null contrast exists.
- Do not submit an array before the campaign-preflight gate: geometry/seed gate
  validated, local smoke passed, dry-run count matches the design, image digest
  pinned, manifest in S3, and a canary read out.
- Do not read `outbreak_occurred` as the posting flag; posted means
  `vsp_trigger_epoch is not None`.
- Do not quote dose figures from this thread; `norovirus_open_ledger.md` §1
  keeps every dose figure void pending refit.
