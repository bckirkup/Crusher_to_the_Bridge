# NORO-PROVISIONED-SOURCE-01 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Mechanism
contract: `docs/provisioned_source_01_design.md`. Frozen eval design:
`docs/norovirus/noro_provisioned_source_01_sweep_design.md`. Ledger
entry: `docs/ledger/PROVISIONED-SOURCE-01.md`. Mega spec:
`campaigns/noro/provisioned_source_01_mega/` (same manifest, elevated
memory — AGE-FOOD split precedent).

**Grid:** 3 small hulls × 12 arms + mega × 10 arms × 1,000 seeds =
46,000 cells + ~128 canary. Seeds exp 8000–8999, cls/spr/mega
8105–9104 (SCORE-01 lists). Fixed coordinates: shipped bp
0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65, dose 7.57,
embarkation 2026-01-10.

**Submit gate:** NO cells submit until the implementation leg lands
the `provisioned_source` mechanism + witness fields
(`common_source.provisioned_source` voyage block,
`provisioned_source_id` on object rows, `reported_cases_by_dominant_route`
summary) and the image pins a SHA containing them. Canary (~128
cells) then STOP — user gates wave 1.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 6 exp + 1 meg | 128 | done 2026-10-16 — all gates pass |
| 1 | exp ×12 arms | 12,000 | submitted 2026-10-16 |
| 2 | cls + spr ×12 arms | 24,000 | not submitted |
| 3 | mega ×10 arms | 10,000 | not submitted |

## Readout log

### canary — submitted 2026-10-16, awaiting cells

Image `picard-campaign:noro-provisioned-source01@sha256:97d99be4c1abf362af1f9914f476740bd1086e7b73491b371f8741bfb1ac95de`
(pinned in campaign.json `image_tag`; ENGINE_GIT_SHA=a9f4a517).
Manifest mirrored to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_source_01/manifest.json`.

| block | jobdef | cells | job id |
|---|---|---|---|
| canary_exp_mint | picard-noro-provisioned-source-01:1 | 48 | 970ef763-ef33-4d65-830e-9451eb8860f3 |
| canary_exp_q30 | :2 | 24 | 69cbe84b-2bf5-4126-8f25-5289aba99ee2 |
| canary_exp_q03 | :3 | 24 | f270b39b-0e83-45f0-86b6-5b3fafdd0775 |
| canary_exp_ps_ship | :4 | 8 | 157f3d0a-a38e-45c8-8579-e6368c9640ab |
| canary_exp_ind | :5 | 8 | 84c16c5c-e3ed-49f1-a300-d9dd61a2638d |
| canary_exp_off | :6 | 4 | 9c70c1d1-45c4-4505-abe9-4f39fc7200f7 |
| canary_meg_q30 | picard-noro-provisioned-source-01-mega:1 | 12 | bf212817-ce81-4323-b269-421996164788 |

Canary gates (design §5.3-2 as amended A1): q-source echo present in
run provenance; provisioned_source witness blocks (stations/objects)
written; minted-set parity vs landed mint cells per shared seed;
objects-bind-stations consistency; mega cells RSS within 8192 MB.

### canary readout — exp cells (116/116 SUCCEEDED, measured 2026-10-16)

- Echo: `lot_mint_model` echoed per arm (`provisioned_source` on
  q03/q30/ps_ship, `fiat` on mint, absent on ind/off);
  `provisioned_source: {source_id, q_source}` in run provenance.
- Witness: `common_source.provisioned_source` written per voyage —
  `n_stations: 21` (exp census), `n_contaminated`, `q_source_drawn`
  on every provisioned cell; objects carry
  `provisioned_source_id: generic_cruise_port`.
- Draw statistics (measured): q30 2/24 voyages minted exactly 1
  object (E = 21·0.003 ≈ 0.063 ⇒ ~1.5 expected); q03 0/24
  (E ≈ 0.006); ps_ship per-ship q resolved [2e-4, 5e-4], 0/8;
  ind/off 0 objects, 0 events. Consistent with Binomial(21, q).
- objects-bind-stations: `n_contaminated` == `provisioned_lot`
  objects on every provisioned cell, no exceptions.
- Attribution blocks live: `reported_cases_by_dominant_route` +
  `reported_cases_by_channel` (`supply_chain` populated on minted
  voyages).
- RSS: peak 516 MB across all exp cells (limit 4096).
- Minted-set parity vs MINT-RATE-01 `fl_exp_12d_scr_mint` (seeds
  8000–8047 paired): **45/48 bit-identical** object sets + event
  counts. Seeds 8026/8032/8046 diverge — attribution: landed cells
  ran image SHA `49e1993b` (81 commits older than canary `a9f4a517`),
  including the ndarray rate-vector truthiness fix (#1013) and
  phylodynamics founder draws (#1025) which perturb the shared RNG
  stream; seed 8026 shows the signature (identical minted set,
  divergent downstream acquired) — upstream stream shift, not a
  mint-mechanism change. Gate read: PASS-with-note (parity axis)
  pending user call.

### canary readout — mega cells (12/12 SUCCEEDED, measured 2026-10-16)

- Witness: `n_stations: 70` on every cell; `n_contaminated` 10×0 +
  2×1 (seeds 8115, 8116 — the latter produced 4 provisioned_lot
  events, `supply_chain: 7` passenger cases in
  `reported_cases_by_channel`). E = 70·0.003 = 0.21 ⇒ ~2.5
  contaminated voyages expected in 12; 2 measured —
  Binomial-consistent.
- RSS: peak 6431–6588 MB (limit 8192).
- objects-bind-stations: exact on the 2 minted cells.

### canary verdict

All canary gates pass; the single note is the 45/48 minted-set
parity (attributed to the 81-commit SHA gap — upstream stream
perturbation, not the mechanism). Wave 1 decision is the user's.

### wave 1 — submitted 2026-10-16, awaiting cells

User approved after the canary readout ("merge 1058, launch wave
1"). 12 exp arrays × 1,000 seeds, digest-pinned jobdef revs.

| block | jobdef rev | job id |
|---|---|---|
| fl_exp_12d_scr_off | picard-noro-provisioned-source-01:7 | cc4af336-485a-4d5e-99b3-d109ad77c5c1 |
| fl_exp_12d_scr_ind | :8 | 1756adfc-2681-4196-962f-73ae67f6cea0 |
| fl_exp_12d_scr_ship | :9 | 42d478cf-9805-4fcc-9a61-f9f3562bd6c4 |
| fl_exp_12d_scr_mint | :10 | 74793cb0-e711-4fec-8228-352081a14967 |
| fl_exp_12d_scr_ps_ship | :11 | 29e2e349-304b-4913-9498-06177a024645 |
| fl_exp_12d_scr_q01 | :12 | 4ccc47b7-ad07-420d-8017-b22f83b93e44 |
| fl_exp_12d_scr_q02 | :13 | a8af78b8-fbfc-495d-9973-2a46e663c6d4 |
| fl_exp_12d_scr_q03 | :14 | f688db70-16c0-4859-91ec-7719a348d468 |
| fl_exp_12d_scr_q05 | :15 | d0329bf5-fbda-4fac-998f-964f43ce534f |
| fl_exp_12d_scr_q08 | :16 | 6eec0fa0-b7b4-4539-a53a-19ef87c5b6f4 |
| fl_exp_12d_scr_q15 | :17 | dbfbaedb-b2ba-4991-af19-da27ac0b852b |
| fl_exp_12d_scr_q30 | :18 | 1de736ce-fa69-47b6-9d21-0c9805ac917d |
