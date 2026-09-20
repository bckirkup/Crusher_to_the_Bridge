# QUAR-EXEMPT-01
**Date:** 2026-09-19
**Commit:** 008c8c8
**Pathogens:** all
**Status:** measured
**Measured at:** 008c8c8

## Defect

`exempt_classes` is a qualifier of one protocol's own confinement order, but
the protocol merge (`ProtocolEngine._merge_modifier_value`) unions list
modifiers across every active protocol, and `step_quarantine_confinement`
read that single merged list for every confinement path. A later, stricter
order could therefore never tighten confinement: `SOP-011` (symptomatic
confinement, all four crew classes exempt) shares its trigger with `SOP-008`
(no exemptions), so symptomatic crew were never confined by `SOP-008`; and
`SOP-017-ALLHANDS` (`exempt_classes: []`) inherited `SOP-011`'s four crew
exemptions and confined exactly what `SOP-017` confines. Arms
`A1_crew_confined` / `A4_crew_confined_and_pool_off` of
`covid_quarantine_attribution_v1` were byte-identical to `A0` / `A2`.

## Fix

`step_quarantine_confinement` now receives the per-protocol `active_mods`
and applies each whole-body and each symptomatic order under that order's own
`exempt_classes` (enforced whole-body orders first). An agent is confined when
any active order confines it; exemptions never cross protocol boundaries. The
escalation-status paths (ALERT+/LOCKDOWN) have no owning protocol and keep the
merged set. Legacy callers without `active_mods` keep the union behaviour.
The merge itself is unchanged.

## Measurement

All figures are the v9 cell theta 1e5, infection age 3.3 d, imports 1, seed
`20200205`, full voyage, run inside the campaign image (`python:3.11-slim`,
numpy 2.4.6 from `uv.lock`). The local host stack (CPython 3.12, numpy 2.5.0)
follows a different trajectory from the same commit and seed (1,346 vs 1,110
infections at `0fb186b`), so local payloads are never compared with S3 cells.

| Commit | infections_total | attack_rate | recorded_onsets | vs S3 v9 cell |
|---|---:|---:|---:|---|
| `0fb186b` (v9 measured) | 1,110 | 0.2991 | 775 | byte-identical |
| `204ba42` (branch base) | 1,110 | 0.2991 | 775 | byte-identical |
| `1a25c24` (arm wiring, before this fix) | 1,110 | 0.2991 | 775 | trajectory identical; payload adds `cell.arm_id: null` |
| `5b5a1e9` (this fix) | 1,171 | 0.3155 | 931 | moved |
| `008c8c8` (HEAD) | 1,171 | 0.3155 | 931 | identical to `5b5a1e9` |

Attribution of the move (paired trace of `1a25c24` vs `5b5a1e9`, same image,
same seed): infected-id sets, per-agent dose sums, quarantined sets and
compliance logs are identical through epoch 238. `SOP-010`/`SOP-016` are
active from epochs 182/153, `SOP-008` and `SOP-011` from 186 and 234. The
first divergence is at epoch 239–248: `5b5a1e9` confines a symptomatic
`crew_general` agent (3408) under a no-exemption symptomatic order while
`SOP-011` is active; the old union never confined crew. The first infected-id
difference follows at epoch 240. The recorded `onset_curve` differs from day 5
because the record dates an onset to first presentation but only writes it
once the host is laboratory-confirmed, so later confirmation differences move
early days of the curve retrospectively; the truth channel is identical before
epoch 239.

Consequence: every THETA-SCREEN-V9 figure remains valid at `0fb186b`; the same
cell run at HEAD is a different trajectory, attributed entirely to this fix.
`SOP-017-ALLHANDS` now confines 3,711 agents at activation (was 2,742 as
`SOP-017`), so A1/A4 differ from A0/A2.

Artifacts (host, not durable): `/home/ubuntu/attr_repro/bisect/`,
`/home/ubuntu/attr_repro/docker/`.
