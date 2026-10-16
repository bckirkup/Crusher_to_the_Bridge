# CONTAM-COMMISSION-01
**Date:** 2026-10-16
**Commit:** 0a2e025a
**Pathogens:** all
**Status:** measured
**Measured at:** 0a2e025a

Commissioned-terminal `.prj` emission mode + the hull→solver measurement it
enables, and a correction to the mechanism claimed in `CONTAM-DIVERGENCE-01`.

## Mechanism correction (measured, ContamX 3.4.0.3 native Linux)

The prior write-up asserted `.prj` AHS terminal `Fahs` is a design annotation
the pressure solve redistributes, citing "ahs2 shunts 878 m³/h through
MedBay" on `tests/fixtures/contam/destroyer_baseline.sim`. **That shunt never
happened — it is a mislabeled readout.** The fixture `.sim` carries the
July-2026-era 44-path numbering; reading it through the September 69-path
`path_map.json` maps fixture path 42 (ahs3's Berthing return, ~878 m³/h)
onto the label "ahs2 MedBay supply". Re-solving the actual July `.prj` with
the real solver reproduces the fixture's flows exactly — a clean balanced
solve.

Measured on flagged simple-AHS terminals (flag 8, `a#` = AHS group): ContamX
enforces **per-terminal `Fahs × schedule`** — it is not a pressure-solved
free link. Proof: patching ahs2 terminals to distinct Fahs
(0.1/0.2/0.4 kg/s) returns exactly `Fahs × sched` per terminal; assigning
`fan_cvf` elements to terminal paths changes nothing (the AHS model, not the
path element, drives them).

What the emitted `.prj` actually got wrong — the residual divergence:

- terminal Fahs was the group's **uniform** `ach·ΣV/n` split, ignoring the
  per-room `V·duty` weighting native applies (e.g. ahs2: 300/300/300 vs
  declared 180/480/240);
- the hobbyist `DutyW` week schedule multiplied terminals by 0.5 **on top of**
  the already-duty-weighted declared field — the exact-halving fingerprint on
  the current `platform.prj` solve.

`CONTAM-DIVERGENCE-01`'s ground-truth divergence numbers (native 42% vs
ContamX 98% retained, HD-sink artefact) stand; the *mechanism* paragraph is
withdrawn and replaced by this entry. The §5 bracketed-surrogate result is
re-read as bounding a scenario correctly-authored `.prj` cannot produce.

## Commissioned emission mode

`ahs_terminal_mode="commissioned"` (export kwarg /
`hobbyist_overrides.json` key / `--ahs-terminal-mode` on
`scripts/generate_platform_contam_prj.py`; default `"design"` unchanged):

- each terminal's `Fahs` = per-room declared `ach · V_room · duty` [kg/s]
  on a **constant** schedule (`sched_nr = 0`);
- exhaust-only branches (`hvac_duty ≤ 0` — the `AHU_HD_*` head-deck AHUs)
  emit supply `Fahs = 0` and return `Fahs = ach · V_room` (the declared
  exhaust design rate);
- recirc design annotation becomes `(1 − oa_fraction) · Σ declared supply`;
- each `ahs_supply`/`ahs_return` path_map entry records
  `declared_flow_m3h` for the check harness;
- `engines/contamx_ahs_bridge.synthesize_ahs_recirculation_paths` now emits
  room→plenum return legs for supply-less (exhaust-only) groups — the head
  drains overboard in the synthesized star.

## Hull → solver commissioning proof (measured)

`tools/contam_commissioned_check.py` exports each platform in commissioned
mode, solves with `third_party/contamx/contamx3` (NIST ContamX 3.4.0.3
Linux-64, SHA256 `3612798d…` matching NIST's published hash), and compares
each terminal's solved `Flow0` against the declared field recomputed
independently from the platform JSON. Tolerance 5% relative; observed
residual ≈ 0.1–0.2% (the `.sim` reader's mean-density conversion vs the
1.2041 kg/m³ authoring constant).

- **destroyer_baseline** (69 paths, 9 declared rooms, 18 terminal legs):
  non-FATAL; every leg ratio 1.002 — Bridge 240.6/240, MedBay 180.4/180,
  Mess_Hall 481.2/480, Galley 240.6/240, Engine_Room 1002.5/1000,
  Berthing 751.8/750; HD supplies exactly 0, HD returns
  358.6/357.7, 239.1/238.5, 119.5/119.2.
- **expedition_cruise_450** (343 paths, 46 declared rooms, 92 terminal
  legs across 22 AHS): non-FATAL; every leg ratio 1.001; 14 exhaust-only
  heads at supply 0 / declared return.

The authored `.prj` solves back onto the declared per-branch flows — the
hull→solver validation the divergence work called the "defensible
construction". No bespoke fan model was needed: the `Fahs` on a flagged
simple-AHS terminal **is** ContamX's constant-flow terminal.

## What changes downstream

- `docs/contam_engine_divergence.md` §2/§4/§7 amended: the twins still
  bracket commissioned-vs-artefact, but the artefact is authoring error
  (uniform split + schedule double-count), not solver redistribution.
- ContamX is no longer Windows-only in this repo — the NIST Linux build
  drops into gitignored `third_party/contamx/` (README there documents the
  drop; `find_contamx` already resolves it).

## Open

- Fleet-wide `.prj` regeneration in commissioned mode is a separate
  decision — committed `contam/platform.prj` artifacts remain design-mode
  until then (a labelled change-detector test pins them).
- The `.sim` reader's mean-density conversion contributes the ~0.1–0.2%
  residual; pinning per-path densities would tighten it further.
