# NORO-OUTBREAK-04
**Date:** 2026-10-04
**Commit:** 1e158d47539ab2b8de9ca46ed13db1da028d3238
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1e158d47539ab2b8de9ca46ed13db1da028d3238

Paired posting-rate re-measurement of the four NORO-OUTBREAK-01 spirit
cells on the post-caregiver image `picard-campaign:campaign-1e158d47`
(digest `sha256:017a0db816da…`; CAREGIVER-V1 + PROPENSITY-V1 default-ON).
Identical voyage draws to OUTBREAK-01 — spirit_cruise_3000,
`fl_spr_12d_scr` split at bp25c7 / bp32.5c18.5 / bp40c30 and
`fl_spr_12d_ren`, nsf 0.29, dose 7.57, epochs 288, seeds 8105–9104 — so
the posting contrast is voyage-for-voyage, not two independent rates.
Manifest
`picard_framework/runs/mega_cruise_campaign/noro_outbreak_04_manifest.json`
(design-of-record; the image serves tier specs via the byte-identical
in-image 01 manifest). 4 arrays × 1000 children on
`picard-campaign-queue`, jobdef `picard-noro-outbreak-04:1` (image
pinned to the campaign-1e158d47 digest), S3 prefix
`campaign/noro_outbreak_04/`; 4000/4000 SUCCEEDED, ~2.3 h fleet time at
~8.8 min/child. Canary `38459575` (20 seeds, fl_spr_12d_scr bp32.5c18.5)
verified `vsp_trigger_epoch`/posted fields, caregiver route counters and
`engine_git_sha: 1e158d47` before the fleet ran. Canonical tables:
`docs/norovirus/noro_outbreak_04_readout.md`.

Instrument overlay note (provenance): the pinned image predates
`d71b301a`, so its `tools/diag/instrument_common.py` carries the stale
6-arg `wrap_emit_emesis` and `growth_chain_census` cannot run unpatched.
Every child appended the merged `d71b301a` wrapper to its writable
container layer before the entrypoint (see
`deploy/aws/submit_outbreak_04.py`). Instrumentation-only — the wrap is
observational and does not affect voyage dynamics; engine SHA is
unchanged.

Baseline-access note: the `campaign/noro_outbreak_01/` zip payloads are
lifecycle-archived in S3 Deep Archive, so the `--import-root` per-seed
join cannot read them directly. A Standard-tier restore of the two
`fl_spr_*` tiers was requested 2026-10-04 (~12 h); the full
established/takeoff seed-pairing can be backfilled once objects are hot.
The posting pairing is unaffected and exact — the baseline posted count
is committed zero for all four cells
(`docs/norovirus/noro_outbreak_01_readout.md`), so every 04 posting is a
gain and none can be lost.

## Measured — frequency (noro_outbreak_04 vs noro_outbreak_01)

- **Spirit posts for the first time**: scr-bp40c30 0%→0.30% [0.10,0.88]
  (3/1000); all other cells stay 0/1000.
- All three postings are crew-channel crossings — reported crew cases
  27–28 vs the ≥27 wire; reported passenger cases 33–39 on the same
  voyages stay well short of ≥63. Posted pax AR med 0.017.
- Posted voyages: seeds 8511, 8721, 8887 — all takeoff voyages (acquired
  218–239, peak prevalence 240–265), vsp flag epochs 277–281.
- Takeoff within noise everywhere (Δ −0.1…0.0 pp); ren takeoff 91.3%
  [89.39,92.89].
- Median acquired up +1…+7; peak prevalence med +3…+8 — the caregiver
  mechanism deepens the high end slightly, consistent with expedition.

## Measured — paired gained/lost postings (same seeds, n=1000/cell)

- scr-bp40c30 **3 gained / 0 lost**; all other cells 0/0. Net +3
  postings on the spirit map (baseline total 0).

## Measured — reports/voyage vs the posting cutoffs

- Spirit wires: ≥63 passenger reports or ≥27 crew reports (3% of
  2100/900).
- Crew channel is the binding one post-caregiver: median crew reports
  8 [6-11] on bp40c30 (baseline crew incidence 46.8→81.6 ratio), max 28
  crossing; passenger reports run med ~24 [20-28], max 58 — ~92% of the
  way to the pax wire without crossing.
- On ren, both channels are far from their wires (pax med 6.1, max 29;
  crew med 1.0, max 9).

## Measured — anchor deltas (new − old)

- A3 rep/ill rises +0.15…+0.18 on every cell (0.53–0.70 vs 0.38–0.52) —
  the caregiver reporting lift, same shape as expedition.
- A8 incidence ratios run hotter: ΔA8 pax +6.9…+23.2, crew +4.9…+34.9.
- A5 pax/crew falls −0.66…+0.19 as crew reports outpace passenger
  reports.
- A1/A2 flat (|Δ| ≤ 0.01).
- Verdict changes: ren **A8 pax PASS→FAIL** (17.91→24.79, over the
  band's top); scr-bp25c7 **A5 pax/crew PASS→FAIL** (2.70→2.04, under
  the band's floor). No new passes; A9 fires 0.30% on one cell but stays
  a FAIL verdict.
- `detection_epoch` is null on every ren takeoff voyage (baseline
  282 [282-282]); scr detection unchanged (~ep 273). Recorded here as an
  observed change, not yet attributed.

## Interpretation

- The posting mechanism is the same one measured on expedition
  (OUTBREAK-02), operating at spirit's deeper tail: reporting lift
  raises reported incidence ~25–75% (A8), and on the most saturated
  cell the crew channel crosses its 3% wire on the upper tail.
- The pax channel remains the harder wire — even on bp40c30 the largest
  voyage reported 58 passenger cases vs 63 needed — because A1/A2 still
  cap symptomatic flow (illness-expression deficit unchanged).
- The cost of the lift is visible in the anchors: the two marginal
  spirit passes from OUTBREAK-01 (A5 bp25c7, A8 ren) move out of band
  from opposite directions — reported incidence is now uniformly
  higher, pulling pax/crew ratios down and incidence ratios up.
- Rate remains rare: 3 postings in 4000 voyages (0.08% pooled), all on
  the single near-saturated cell — the same saturated-cell signature
  expedition showed at 0.7–0.8%.
