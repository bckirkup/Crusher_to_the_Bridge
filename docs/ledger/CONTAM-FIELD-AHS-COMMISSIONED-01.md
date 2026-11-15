# CONTAM-FIELD-AHS-COMMISSIONED-01
**Date:** 2026-11-15
**Commit:** 7cef1125
**Pathogens:** all
**Status:** open
**Measured at:** 7cef1125

Stage 4 of the class-(f) adjudication fix
([`../proposals/contam_field_adjudication_audit_and_fix_plan.md`](../proposals/contam_field_adjudication_audit_and_fix_plan.md);
evidence in `CONTAM-FIELD-ADJUDICATION-01`). Committed authored Contam bundles
were `ahs_terminal_mode="design"` historical annotations; this entry brings all
77 committed bundles to the declaration-faithful `ahs_terminal_mode="commissioned"`
encoding. No hull declaration, schema, engine, or exporter-semantics change is
included, and no frozen campaign artifact is touched.

## Change

- Re-exported every committed `data/platforms/*/contam/platform.prj` +
  `path_map.json` pair with
  `PYTHONPATH=. .venv/bin/python scripts/generate_platform_contam_prj.py --ahs-terminal-mode commissioned --platform <id> ...`
  for all 77 bundle ids. Commissioned emission is per-room `ach·V·duty` Fahs on
  constant schedule 0; exhaust-only `hvac_duty <= 0` branches emit supply 0 and
  return `ach·V`; `path_map.json` records `declared_flow_m3h` on AHS terminal
  entries.
- `tools/contam_commissioned_check.py` now keys declared terminal flows by
  `(ahs_nr, room)` instead of room alone, because a room may be served by more
  than one HVAC group (measured case: `montana_acr13/SIGNAL_Bridge` is in
  `ahs1` at 180 m³/h and `ahs6` at 1350 m³/h). Added
  `tests/test_contam_commissioned_check.py` and updated
  `tests/test_contamw34_commissioned.py` so the byte-stability change-detector
  pins the commissioned bundles while design mode is asserted to carry no
  `declared_flow_m3h`.

## Byte-pinned reproduction

- Fresh `ahs_terminal_mode="commissioned"` exports byte-match all 77 committed
  `platform.prj` / `path_map.json` pairs: checked 77, mismatch 0, errors 0.
- Path-map entry counts are unchanged: 77 platforms, 58,180 path_map entries
  before and after. Schema validation against
  `schemas/contam_path_map.schema.json`: 77/77 pass.

## Measurements

- Paired exact-integral diagnostic (`tools/diag/contam_paired_diagnostic.py`,
  filter 0.3, decay 0.1/h, horizon 12 h; before = committed design bundles,
  after = committed commissioned bundles). After this change the authored lane
  equals the commissioned lane exactly for both supported hulls (max abs diff
  0.0 over 42 cells). Headline `pulse_t0` whole-hull material-time:

  | Hull | Source | Authored before h | Authored after h | Commissioned h |
  |---|---|---:|---:|---:|
  | `expedition_cruise_450` | `HD_5P_M` | 0.23101756975413998 | 0.051756484614901455 | 0.051756484614901455 |
  | `destroyer_baseline` | `HD_MAIN_M` | 0.23071363020057828 | 0.05168714306011469 | 0.05168714306011469 |
  | `destroyer_baseline` | `Mess_Hall` | 0.6699371412982886 | 0.3252110940500446 | 0.3252110940500446 |
  | `destroyer_baseline` | `Bridge` | 0.6432333355298602 | 0.4165951917194409 | 0.4165951917194409 |
  | `expedition_cruise_450` | `MainDining` | 0.1886143807252093 | 0.1912604906581144 | 0.1912604906581144 |
  | `expedition_cruise_450` | `MainGalley` | 0.10355204832358522 | 0.1068440991137111 | 0.1068440991137111 |
  | `expedition_cruise_450` | `PoolDeck` | 0.7492617109298074 | 0.7740977157007225 | 0.7740977157007225 |

- Forced-exhaust audit re-run:
  `PYTHONPATH=. .venv/bin/python tools/diag/forced_exhaust_audit.py audit --out telemetry_buffer/contam_field_audit_after`
  → platforms=82, links=1018, recount=82/1018, reconciled=True.
- Commissioning check: `--emit-only` passes for all 77 re-synced bundles. The
  ContamX solve pass completed 76/77 hulls with every solved AHS terminal inside
  the default 5% tolerance (0 out-of-tolerance rows). `olympia_c6` did not return
  within the stock 300 s ContamX timeout; an extended 1200 s commissioned run
  also timed out, and the same hull in the pre-change design encoding also times
  out at 300 s. This is a pre-existing ContamX solver-performance outlier for
  that hull, not a commissioned-encoding regression; `olympia_c6` still passes
  emission, byte-pinned reproduction, path-map schema, and path-map counts.

## Frozen artifacts and campaign lanes

- Phase-2 `contam_phase2_cruise_contrasts_01/02` lane P is explicitly a
  historical design-mode lane: it solved the committed
  `contam/platform.prj` + `path_map.json` as-run for
  `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, and
  `mega_cruise_5000` (baseline arm). Its caches/readouts stay valid as-run. No
  frozen campaign directory, S3 prefix, `_v1`/`_v2` cache, committed readout, or
  prior ledger is modified, and no `_v2` cache/design is produced here. Any
  future P-lane re-measurement must use the `_v2` field-cache/design-id
  convention (#1217/#1236) rather than overwriting the frozen P lane.
- No pathogen open-ledger note is added: no recorded measurement is invalidated;
  the frozen P-lane readout remains an as-run design-mode result.

## Validation

- `PYTHONPATH=. .venv/bin/python -m pytest tests/ -m 'not slow' -n auto --tb=short`:
  8521 passed, 9 skipped.
- `ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311`
  on changed sources: pass; `python3 scripts/sonar_guard.py` on changed sources:
  pass; pre-commit on changed files: pass;
  `python3 tools/sanity_checker.py --from-config`: pass (2 pre-existing TAT
  warnings).
