# FLU-REASSESS-01 ledger

> Status: **spec** — not yet measured. Design and frozen predictions in
> `DESIGN.md` beside this file. Baselines of record: FLU-OPEN-01
> `7f4702ef`, FLU-VIS-01 `ca775a0b`.

## Intent

Re-measure the flu open-voyage surface on the post-enhancement engine
(`service.contact_factor` U[0.05,0.3] + `defiant_escalation_hours` 24,
both default-ON since the baselines ran): 8 blocks {exp, spr, cls, mega}
× {r100_dec census, r200_dec sign-reversal arm} × seeds 8105–8204 = 800
cells. Approved scope (2026-10-07): census + r200_dec; shipped
`responder`/`uniform` service defaults; no `direction:"both"` arm.

## Execution log

| date | step | detail |
|------|------|--------|
| 2026-10-07 | spec authored | `campaign.json` (8 blocks), `cell.py` (VIS-01 contract + mechanism echo + compliance witnesses), `readout.py` (committed-baseline deltas + same-campaign r200−r100 pairing), `DESIGN.md` frozen predictions P1–P6. |
| 2026-10-07 | merged | PR #949 @ `a7593ddc` |
| 2026-10-07 | image | `picard-campaign:flu-reassess01` @ `a7593ddc`, pushed digest `sha256:dc88bb52…d786d`; in-container `--local` exp s8106 verified |
| 2026-10-07 | jobdef | `picard-flu-reassess-01:1` registered digest-pinned (no bare-tag revs) |
| 2026-10-07 | canary | array `144d61ba-ba21-4dd5-8a53-7916cfbc4c37` — `flu_exp_12d_r100_dec` seeds 8105–8124 (20) on `picard-analysis-queue` |
| 2026-10-07 | drought | EC2 CE parked queue-wide ~40 min (0 RUNNING across all queued arrays); `picard-flu-reassess-01-fargate:1` registered, parallel canary `31bf588c-99a9-46ef-b863-9c1f530c78e5` on `picard-analysis-fargate-queue` (dedup via skip-if-uploaded) |
| 2026-10-07 | canary read out | 20/20 cells landed via Fargate in ~4 min, all audits pass (echo `["uniform",0.05,0.3]`/24/responder/uniform on every cell, `to_host` 0.0, enforced 18 ≤ refusals 50 on 12 cells). exp r100_dec: infected 7.70/cell (base 7.55), onboard 2.55/cell (base 2.82), presenting attack 0.93% (≈Ward), rep/inf 54.5%, outbreak 75%, confined 20/20, acquired-route split caregiver 16 vs droplet 35 of 51. |
