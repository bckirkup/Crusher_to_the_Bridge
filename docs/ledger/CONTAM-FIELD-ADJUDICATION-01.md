# CONTAM-FIELD-ADJUDICATION-01
**Date:** 2026-11-15
**Commit:** 78a023b6
**Pathogens:** all
**Status:** open
**Measured at:** 78a023b6

## Scope

Doc-only adjudication of Edison's preserved native-vs-ContamX field differences
after #1241/#1242. Proposal of record:
[`../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../proposals/contam_field_adjudication_audit_and_fix_plan.md).
No code, data, schema, campaign, S3, or frozen artifact is changed by this entry.

The committed paired diagnostic was rerun locally and wrote 42 cells; the
post-fix commissioned `pulse_t0` whole-hull values reproduce
`CONTAM-PAIRED-RECOMPARE-01` (for example Expedition `MainDining`
0.1912604906581144, `HD_5P_M` 0.051756484614901455, `PoolDeck`
0.7740977157007225, `MainGalley` 0.1068440991137111; destroyer `Mess_Hall`
0.3252110940500446, `HD_MAIN_M` 0.05168714306011469, `Bridge`
0.4165951917194409). Flow/ΔP numbers below are local measured diagnostics at the
same SHA, not committed readouts.

## Verdicts

| # | Difference class | Verdict |
|---|---|---|
| a | Service-hatch reverse flow (Expedition `MainGalley -> MainDining` ≈ 2120 m³/h field vs native fixed 8 m³/h) | Legitimate representation difference; magnitude rides on (d) |
| b | Pool-deck openings (≈ 2127 m³/h `PoolDeck -> CasualDining` + ≈ 1891 m³/h `ObsLounge -> PoolDeck` field vs native ≈ 400 m³/h declaration) | Authoring gap |
| c | Galley release remote material-time ≈ 12× in the field lane | Legitimate representation difference downstream of (a)/(b) |
| d | Extreme solved pressure drops after the #1241 laminar probe | Authoring gap |
| e | Destroyer authored outward envelope leaks 0.5403 m³/h ignored as contaminant paths | Needs owner decision |
| f | Authored vs commissioned sanitary terminal (`HD_5P_M` whole-hull 0.231018 vs 0.0517565 h) | Authoring gap |

No class was proven to be a defect in the transport kernel, the ContamX bridge,
or the paired diagnostic.

## Key measurements

- Paired diagnostic (`pulse_t0`, filter 0.3, decay 0.1/h, horizon 12 h),
  Expedition `MainGalley` remote material-time: native 0.0016680483135042468 h,
  commissioned 0.024046017210102237 h, authored 0.01838404161683253 h.
- Expedition `HD_5P_M` whole-hull material-time: native 0.05181347150259067 h,
  commissioned 0.051756484614901455 h, authored 0.23101756975413998 h.
- Authored Expedition flow field: `p057 service_hatch` +2120 m³/h at +446.5 Pa;
  `p048 open_deck` +1891 m³/h; `p050 doorway` and `p133 CasualDining_Open_Doorway`
  together −2126.9 m³/h in path-map orientation, i.e. `PoolDeck -> CasualDining`.
- Pressure plausibility: authored Expedition envelope leak `dP ≈ −7.157e5 Pa`,
  commissioned Expedition envelope leaks `dP ≈ −9.82e5 Pa`, commissioned
  destroyer envelope leaks `dP ≈ −8.156e4 Pa`.
- Destroyer authored envelope leaks `p004 Engine_Room -> ambient` +0.2701 m³/h
  and `p006 Berthing -> ambient` +0.2702 m³/h are `kind: envelope_leak`,
  `crusher_transfer: false`, and skipped by the ContamX→Crusher contaminant
  filter.

## Follow-ups

Versioned stages are in the proposal: pressure/balance diagnostic, PoolDeck
opening authoring review, service-hatch mechanism decision, AHS terminal-mode
decision for committed authored bundles, envelope-boundary semantics decision,
and envelope/make-up authoring fixes. Each landed stage gets its own ledger entry.
