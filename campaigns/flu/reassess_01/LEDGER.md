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
