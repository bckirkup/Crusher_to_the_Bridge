# NORO-CHANNEL-04
**Date:** 2026-10-03
**Commit:** #856
**Pathogens:** norwalk_gi
**Status:** declared

## Question

NORO-CAREGIVER-01 (merged `a78c942e`, default-ON) ships the
party-mediated caregiver mechanism aimed at both broken funnel links
measured by NORO-CHANNEL-03 (`d6c51c14`): infected -> symptomatic-course
0.170-0.413 vs 0.6, eligible -> reported 0.168-0.321 vs 0.4. Does the
CHANNEL-03 rung chain move on the identical 9 cells x 20 seeds, and is
any lift channel-attributed (discovery stamp vs cleanup dose)?

## Instrument

`tools/noro_diag/observation_channel_funnel.py` extended read-only:
`caregiver_report_ids`/`caregiver_report_due_epoch` capture, the
reported rung's `via_caregiver` split, per-infection dominant route for
the caregiver share of aboard transmissions, and the engine's
`caregiver_telemetry` counters. `tools/noro_diag/channel_03_readout.py`
adds `viaCG`/`CGtx` columns and evaluates the frozen triggers.
Identical spec source (`noro_outbreak_01_manifest.json`), cells and
seeds as CHANNEL-03; fresh prefix `campaign/noro_channel_04/` pairs
each new dump against the `campaign/noro_channel_03/` baseline at the
same spec+seed. Design: `docs/norovirus/noro_channel_04_design.md`.

## Admissibility (frozen)

- caregiver share of aboard transmissions > 10% on any pooled cell ->
  over-delivery, report immediately;
- any caregiver report on a non-emetic course -> stamp-integrity
  defect, report immediately;
- vomiting-course voyages with zero caregiver+steward responses ->
  report the count per cell;
- rep/elig > ~0.6 anywhere -> over-reporting (carried);
- infected -> symptomatic-course near zero at takeoff -> contradicts
  the shipped never_symptomatic reading (carried).

## Scope

- Reads the shipped mechanism; fits nothing. No mode:off arm — the
  d6c51c14 dumps are the labelled baseline.
- The funnel-vs-map `took_off` join is reported as a mechanism-effect
  witness (divergence = takeoff change), no longer a void condition.
- Anchor re-score (OUTBREAK-01-scale) is the following decision, not
  this campaign.

## Canary readout — 2026-10-03, `fl_exp_12d_scr` x `rung-shipped,bp32p5c18p5`, 20 seeds

Array `8f6dbe53` on `picard-campaign-queue`, image
`picard-campaign:campaign-1e158d47` (digest sha256:017a0db8…, CAREGIVER-V1
`f8a8f362` + PROPENSITY-V1 `1e158d47` composed). 17/20 seeds took off.

| rung | canary | ch_03 baseline | declared ~ |
|---|---|---|---|
| infected → symptomatic-course | 0.389 | 0.413 | 0.6 |
| symptomatic → eligible | 1.000 | 1.000 | — |
| eligible → reported | 0.224 | 0.172 | 0.4 |
| reported → confirmed | 0.302 | 0.371 | — |
| reports via_caregiver | 0.512 | dead channel | — |
| caregiver-dominant aboard tx | 0.022 | — | — |
| dated / confirmed | 0.692 | — | — |

Verdict: the discovery stamp is live in the data — 51.2% of all reports
now arrive via `via_caregiver`, converting stamped hosts to reports ~1:1 —
and eligible→reported rose 0.172→0.224. The first rung did not move
(0.389 vs 0.413): the A2 symptom-course draw still carries the gap, as
the design predicted — neither mechanism touches the illness draw.
Cleanup-dose transmission is real but thin (2.2% of aboard infections
carry the caregiver as dominant route).

### Trigger evaluation

- *vomiting-course voyages, zero caregiver+steward responses*: 3 of 15
  vomiting voyages (seeds 8002, 8004, 8016). Decomposed by instrumenting
  `_emit_emesis`/`_caregiver_response` on the pinned image runtime:
  - 8002: exactly one viral-positive emit (agent 28, `ObsLounge`) → one
    steward draw, lost (~0.22 miss/emit). Honest tail.
  - 8004, 8016: `_caregiver_response` never invoked — the declared
    vomiting courses produced zero due emesis episodes in-window (late
    infection / unopened emetic phase). `vomiting_course_hosts` counts
    the illness *course*, not realized emesis; a course with no fired
    episode cannot draw a response. Funnel-accounting artifact, not a
    dead channel: the other 12 vomiting voyages all recorded ≥1
    response.
- *caregiver report on a non-emetic course*: 1 — the tending-arm stamp
  working as designed (R2 stamps non-emetic hosts by construction).
- Remaining frozen triggers not fired.

## Runtime caveat — 2026-10-03

Seed trajectories are interpreter×numpy-pinned (SEED-INTERP-01): the
batch image (python 3.11.17 / numpy 2.4.6 per `uv.lock`'s
`python_full_version < '3.12'` pin on `python:3.11-slim`) and a
python ≥3.12 venv (numpy 2.5.0) realize different voyages for the same
seed — measured identical on run_id `…s8016` (batch/image 25 infected,
venv 26; image-on-local reproduces batch exactly). Cell-level ratios are
self-consistent within the image; do not re-derive a batch seed's
counters locally.

## Campaign readout — 2026-10-03, all 9 cells, 180 runs

8 remaining arrays submitted (20-child arrays on
`picard-campaign-queue`, same digest-pinned image `campaign-1e158d47`):
exp scr-hi `c0942c77`, exp ren `531acccf`, cls scr-mid `61d8627b`,
cls scr-hi `57e4a538`, cls ren `cd9748f3`, spr scr-mid `817c0941`,
spr scr-hi `aebb3997`, spr ren `6b3197a5`. 160/160 children SUCCEEDED,
zero failures; 180 dumps under `campaign/noro_channel_04/`. Full
measured readout: `docs/norovirus/noro_channel_04_readout.md`.

| cell | n (tk) | symp/inf | rep/elig | viaCG | CGtx |
|---|---|---|---|---|---|
| cls ren | 20 (17) | 0.206 (0.222) | 0.390 (0.321) | 0.512 | 0.019 |
| cls scr-mid | 20 (20) | 0.345 (0.363) | 0.345 (0.242) | 0.516 | 0.034 |
| cls scr-hi | 20 (20) | 0.359 (0.371) | 0.315 (0.239) | 0.545 | 0.037 |
| exp ren | 20 (2) | 0.333 (0.280) | 0.286 (0.429) | 0.250 | 0.000 |
| exp scr-mid | 20 (17) | 0.389 (0.413) | 0.224 (0.172) | 0.512 | 0.022 |
| exp scr-hi | 20 (19) | 0.393 (0.390) | 0.249 (0.168) | 0.476 | 0.025 |
| spr ren | 20 (19) | 0.217 (0.170) | 0.451 (0.316) | 0.598 | 0.025 |
| spr scr-mid | 20 (20) | 0.333 (0.333) | 0.331 (0.238) | 0.571 | 0.031 |
| spr scr-hi | 20 (20) | 0.365 (0.368) | 0.318 (0.267) | 0.614 | 0.040 |

(parenthetical = CHANNEL-03 baseline at the same cell)

- **A2 link untouched on all 9 cells** — Δsymp/inf −0.024..+0.053;
  the illness draw is outside the mechanism's reach by construction.
- **rep/elig systematically lifted** — +0.051..+0.135 on 8/9 cells;
  paired-seed attribution 14-18/20 up per cell (18/18 spr ren).
  exp_ren's −0.143 is a 2-takeoff cell (thin).
- **viaCG 0.476-0.614; stamped→reported 100%** on every cell
  (stamped_not_reported = 0 in all 180 voyages).
- **CGtx ≤ 0.040 everywhere** — 10% amplifier trigger not fired.
  Steward responses dominate party ~10:1 (public emesis ≫ in-cabin).
- **Join witness**: 13/180 takeoff disagreements vs the OUTBREAK-01
  map (7 funnel-ON, 6 funnel-OFF, ren-cell concentrated) — treatment
  effect per the design, not a void.
- **Triggers**: non-emetic stamped reports on 7/9 cells (38 voyages,
  tending-arm working as designed); zero-response vomiting voyages 4
  (3 canary seeds decomposed + 1 cls_ren) — same accounting quirk:
  `vomiting_course_hosts` counts declared courses, not fired episodes.
- **Residual**: rep/elig still <0.4 on shipped cells except spr_ren
  (0.451); residual decomposes to `course_not_symptomatic_onboard`
  (599-1182/cell censored presence) over `visible_whole_course_draw_missed`
  (154-313). The mechanism stamps what surfaces; the censoring pool is
  outside its reach.

Readout tooling fixed en route: `_trigger_lines` KeyError on
`zero_response_voyages` (absent key when no voyage hits the condition),
and the OUTBREAK-01 map join now does targeted `<tier>/<run_id>.zip`
ranged reads instead of scanning all ~16k map zips; `--join-witness`
renders disagreements per the channel_04 semantics.
