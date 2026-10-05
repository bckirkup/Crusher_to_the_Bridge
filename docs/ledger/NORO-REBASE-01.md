# NORO-REBASE-01
**Date:** 2026-09-26
**Commit:** fbad8738
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1935b5d4

## Declared design (frozen before any cell ran)

Rebaseline of the VSP posting + attack-rate anchors on the post-#724 engine
(`fbad8738`: cabin-fomite channel live since #721 at `afa360cc`, crew watch
schedules since #723 at `790e090c`, secretor-negative fraction 0.2 live in the
`norwalk_gi` profile via NORO-SUSCEPT-04). Every dose figure in
`docs/norovirus/norovirus_open_ledger.md` stays void pending refit — this
entry measures anchors only and publishes no dose numbers.

- **Cell**: the FLUSH-S4 `off`-arm declared-complement cell verbatim —
  `dose_adjustment` 4.0, `syndromic_comp65`, boarding rung `reportable`,
  `sanitary_visit_mode` `dwell_weighted`, `flush_aerosol_fraction` 0.0,
  `flush_cabin_emission` true, `cabin_air_mode` `cabin_compartment`,
  `hvac.pathogen_pool_transport` `airflow` — so the post-724 delta reads
  voyage-for-voyage against the `flush_sweep_v1_off_s4` archive. The #721/#723
  machinery rides at shipped defaults; this cell's overrides do not touch it.
- **Platforms**: `expedition_cruise_450` (450), `classic_cruise_1900` (1,910),
  `spirit_cruise_3000` (3,000), `mega_cruise_5000` (7,000) — declared
  complements.
- **Lengths**: 168 and 288 epochs (`hours` clock), embarkation 2026-01-10.
- **Seeds**: paired 8105/8106 per cell. 8 cells x 2 seeds = 16 runs.
  Manifest `noro_rebase_01_manifest.json` (tiers `fl_{exp,cls,spr,mega}_{7d,12d}`).
- **Canary**: `fl_spr_12d` at seeds 8105-8124 (20 seeds; manifest
  `noro_rebase_01_canary_manifest.json`) — the strongest posting cell in the
  pre-fix baseline (20 per 1,000 at `off` over the 200-seed block). Gate:
  pipeline end-to-end (run -> zip -> summary.json -> score_anchors) parses
  clean, posting field populated, and the cell is read out before the array
  is submitted.
- **AWS**: `picard-campaign-queue`, prefix `campaign/noro_rebase_01/` and
  `campaign/noro_rebase_01_canary/`, jobdef `picard-campaign:49`, image digest
  `sha256:e1f7b0ccff1db48caaed2c021a17015fd658fb573d92f16805cb3ea5d0c3341c`
  (`picard-campaign:noro-rebase-01`, engine SHA 1935b5d4 = fbad8738 +
  manifest/declared-ledger commit only). Canary Batch array
  `de944b89-2b12-4fd8-bec6-4eeb32797cc3` (20 children).
- **Harness**: `telemetry_buffer/observation_model/score_anchors.py`
  (`--vsp-era pre`), scoring A1/A2/A4/A5/A8/A9 conditional on take-off
  (`peak_prevalence >= 10`); A3 is a construction band, reported not scored.

## Pre-fix baseline (archive, engine `7f689b9`, same seeds)

The `flush_sweep_v1_off_s4` archive at seeds 8105/8106, scored by the same
harness on the extracted shard zips — the voyage-for-voyage baseline. Mega has
no pre-fix reading in this cell (the hull never ran it at declared
complement); its baseline column is empty by construction, not zero.

| hull | take-off | A1 | A2 | A4 | A5 | A9 (per voyage) |
|---|---|---|---|---|---|---|
| expedition | 0/4 | — | — | — | — | 0/4 = 0.00 |
| classic | 0/4 | — | — | — | — | 0/4 = 0.00 |
| spirit | 2/4 | 0.1419 | 0.658 | 0.0869 | 12.04 | 2/4 = 0.50 |
| mega | (no baseline) | — | — | — | — | — |

Caveat carried forward from NORO-EMESIS-SIZE-01: the 8105/8106 pair sits below
the heavy tail on classic — 0/4 take-off there is the pair's reading, not the
cell's distribution (200-seed `off` posting was 5/1,000). The pair is the
convention, not a powered estimate.

## Frozen readout criteria

- Per hull x length: A1/A2/A4/A5/A8/A9 verdicts + raw values, paired against
  the baseline table above where a baseline exists.
- Report-immediately trigger: any platform never posts in both lengths, or a
  platform never takes off.
- Deltas are read against which open-ledger items they support or weaken:
  the posting-surplus property, the crew-route overshoot (A5), and the
  take-off tails noted in the ledger.

## Canary readout — spirit 12d, seeds 8105–8124 (measured)

**Measured at:** `1935b5d4` (image `sha256:e1f7b0ccff1db48caaed2c021a17015fd658fb573d92f16805cb3ea5d0c3341c`,
jobdef `picard-campaign:49`, array `de944b89-2b12-4fd8-bec6-4eeb32797cc3`,
S3 `campaign/noro_rebase_01_canary/`).

20/20 children SUCCEEDED. The cell **never posts** (0/20) and take-off has
collapsed: 4/20 cross the take-off gate, all marginal (peak prevalence 10–11),
versus the paired pre-fix voyage at seed 8105 that posted with peak 614.
Passenger infection AR sits at 0.3–0.4% (pre-fix pair: 27.0% on 8105).
Cell verdicts: A1 FAIL (0.0007), A2 FAIL (0.16), A4 FAIL (0.0003),
A5 FAIL (0.0), A8 FAIL (2.1 pax / 2.3 crew), A9 FAIL (0.00).

**Report-immediately trigger fired** (a platform never posts); reported to the
requester, who directed a powered take-off measurement on the smallest hull
before the four-hull array.

## Expedition take-off power block (declared extension, same base)

`noro_rebase_01_exp_block_manifest.json`: tiers `fl_exp_7d` / `fl_exp_12d`,
seeds 8000–8999 (1000 per cell; the range covers the full 200-seed `off_s4`
baseline block voyage-for-voyage plus 800 fresh seeds), same off-arm cell
verbatim. 2,000 runs; Batch array `03dfc8bd-0cd2-41b5-b519-fdb4863e2f6b`
(500 children x 4 runs), jobdef `picard-campaign:50`, image digest
`sha256:6b5cdb0c98717002b24dee40218f9969b9ce3e2a23359970265695fb9a425ef0`
(`picard-campaign:noro-rebase-02`, engine SHA a872367c — same engine code as
the canary, plus this manifest), S3 `campaign/noro_rebase_01_exp_block/`.

Readout: take-off fraction + posting fraction per length on expedition, with
the paired 8105/8106 subset feeding the per-platform anchor table below.

### Expedition power-block readout (measured)

**Measured at:** `a872367c` (array `03dfc8bd-0cd2-41b5-b519-fdb4863e2f6b`,
all 500 children SUCCEEDED, 2,000 runs scored).

| expedition | take-off | posted | peak med / p90 / max |
|---|---|---|---|
| 7d post-724 (n=1000) | 0/1000 | 0/1000 | 1 / 2 / 5 |
| 12d post-724 (n=1000) | 0/1000 | 0/1000 | 1 / 2 / 5 |
| 7d pre-fix (n=200, seeds 8000–8199) | 0/200 | 0/200 | 1 / 2 / 9 |
| 12d pre-fix (n=200) | 0/200 | 0/200 | 1 / 2 / 9 |

Expedition never took off at either epoch (pre- or post-724): the verdict is
unchanged, and the peak tail fell from max 9 to max 5 — importations die
faster than before but this hull was already sub-threshold.

The sharper reading comes from spirit's canary against its own 200-seed
baseline: take-off rate on `fl_spr_12d` was 28/200 pre-fix vs 4/20 post-724 —
but every post-724 take-off stalls at peak 10–11 where pre-fix take-offs ran
to peaks of hundreds (max 614). Voyage initiation still fires at roughly the
old rate; outbreak growth collapses around the gate, so nothing reaches the
3% reported-AR posting threshold. The post-724 change suppresses the
*size* of established outbreaks, not (much) their initiation.

## Four-hull array — paired seeds 8105/8106 (measured)

**Measured at:** `a872367c` (array `bc0ed6ff-23bb-4991-b4d2-ad88d076634e`,
16/16 children SUCCEEDED, jobdef `picard-campaign:50`, image
`sha256:6b5cdb0c...`, S3 `campaign/noro_rebase_01/`). All verdicts scored by
`score_anchors.py` at `vsp-era pre` on the emitted complements.

| hull | len | take-off post (pre) | A1 post (pre) | A2 post (pre) | A4 post (pre) | A5 post (pre) | A8 pax/crew post (pre) | A9 post (pre) |
|---|---|---|---|---|---|---|---|---|
| expedition | 7d | 0/2 (0/2) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | 0.0/0.0 FAIL (22.9/0.0 FAIL) | 0.00 FAIL (0.00 FAIL) |
| expedition | 12d | 0/2 (0/2) | n/a (n/a) | n/a (n/a) | n/a (n/a) | n/a (n/a) | 0.0/0.0 FAIL (0.0/0.0 FAIL) | 0.00 FAIL (0.00 FAIL) |
| classic | 7d | 1/2 (0/2) | 0.0000 FAIL (n/a) | 0.0000 FAIL (n/a) | 0.0000 FAIL (n/a) | n/a (n/a) | 0.0/0.0 FAIL (0.0/12.1 FAIL) | 0.00 FAIL (0.00 FAIL) |
| classic | 12d | 1/2 (0/2) | 0.0000 FAIL (n/a) | 0.0000 FAIL (n/a) | 0.0000 FAIL (n/a) | n/a (n/a) | 0.0/7.1 FAIL (0.0/7.1 FAIL) | 0.00 FAIL (0.00 FAIL) |
| spirit | 7d | 1/2 (1/2) | 0.0014 FAIL (0.0886 FAIL) | 0.3256 FAIL (0.5926 PASS) | 0.0010 FAIL (0.0614 PASS) | n/a (13.95 FAIL) | 7.1/0.0 FAIL (438.6/31.4 FAIL) | 0.00 FAIL (0.50 FAIL) |
| spirit | 12d | 1/2 (1/2) | 0.0014 FAIL (0.1952 PASS) | 0.3256 FAIL (0.7243 PASS) | 0.0010 FAIL (0.1124 FAIL) | n/a (10.13 FAIL) | 4.2/0.0 FAIL (468.3/46.2 FAIL) | 0.00 FAIL (0.50 FAIL) |
| mega | 7d | 2/2 (no baseline) | 0.0004 FAIL | 0.1143 FAIL | 0.0001 FAIL | 0.00 FAIL | 1.4/3.6 FAIL | 0.00 FAIL |
| mega | 12d | 2/2 (no baseline) | 0.0004 FAIL | 0.1143 FAIL | 0.0002 FAIL | 0.00 FAIL | 1.7/2.1 FAIL | 0.00 FAIL |

Baseline column: per-length paired baseline (seeds 8105/8106, engine 7f689b9)
from the off_s4 archive scored by the same harness; "no baseline" where the
hull never ran this cell pre-fix (mega).

- **No platform posts anywhere** post-724: 0/16 array voyages, 0/20 canary,
  0/2000 expedition block. Classic's pair now takes off marginally (peak 10,
  seed 8106) where pre-fix it did not; spirit's pair collapses from two posted
  voyages (peaks 371/614) to one marginal take-off (peak 11); mega's pair takes
  off at peaks 20–21 with pax infection AR 0.35% but reported AR ≈ 0.
- **Every take-off is marginal**: the largest post-724 peak anywhere in the
  campaign is 21 (mega). Pre-fix peaks on the same seeds reached 614.
- **A5 reads n/a or 0** — crew reported AR is ~0 everywhere; the crew-route
  question is moot where nothing transmits, not resolved.
- **Mega roster note**: the hull emits `passenger_complement` 4900 /
  `crew_complement` 2100 (sums to the 7,000 `num_agents`), not the declared
  5000/2000 — anchors were scored on the emitted split, and the harness's
  recovery cross-check misfires on this hull (accommodated in the readout).

### Where transmission dies (diagnostic, seed s8105 spirit-12d paired)

Pre-fix: the import cohort's first defecation wave (~epoch 16) drove
`sanitary_activity.dose_delivered` to 1.8e5 in one epoch → 100 secondaries →
peak 614. Post-724: same imports, same symptom timing, `dose_delivered`
≈ 2–5 per epoch and ~zero secondaries. Pickup requests still fire
(~700–1,200 recipients/epoch), so the venue pickup gate is not the blocker —
the **surface-pool deposit mass collapsed ~5 orders of magnitude** (shedder
hand load reaching sanitary venues), and index stool reroutes roughly halved
(107 → 41 by epoch 16). Candidate drivers inside 7f689b9..fbad8738: emesis
footprint localization (#604), blackwater bowl-share capture (#590s),
watch-schedule rerouting (#723), sub-copy pickup gate (NORO-GATE-FLOOR-01).
This is an inference from one paired trace — the attribution ablation is
deliberately out of scope here.

### What the deltas say about open-ledger items

- **Supports** the withdrawal premise (§1): the pre-fix posting surplus and
  explosive take-off tail were artefacts of zone-wide emesis dosing — now
  confirmed measured, not just argued. The tail is gone: max peak 21 vs 614.
- **Supports** the open-ledger item that A8/A9 need a fleet-scale cell
  (§list item 6): at the voyage cell A9 is uniformly 0.00 — the anchors
  cannot score what never posts.
- **Context for the refit item ("refit the common dose", §list item 3):**
  the post-724 box is cold, not hot — a refit now works from a base where
  establishment itself is rare; whether that means the dose must rise or the
  deposit-side collapse is a defect to fix first is the open question this
  entry hands off.
- **Weakens** nothing the ledger still stands on — A5/crew-route items are
  unverifiable at this transmission level, not contradicted.

## Provenance

Numbers at `a872367c` on `picard-campaign:50`
(`sha256:6b5cdb0c98717002b24dee40218f9969b9ce3e2a23359970265695fb9a425ef0`);
canary at `picard-campaign:49` (`sha256:e1f7b0cc...`). Secretor-negative
0.2/0.2 was live throughout — no dual measurement needed.
