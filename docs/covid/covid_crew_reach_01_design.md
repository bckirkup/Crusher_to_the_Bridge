# CREW-REACH-01 design — serial-testing + crew-reach observation structure

Status: **frozen, pre-run**. Companion to
`picard_framework/runs/covid_crew_reach_01_design.json` (the frozen scoring
grammar) and `campaigns/covid/crew_reach_01/`.

## Question

The boxed Diamond Princess configuration (`sect_mess_boxed`) landed crew share
of lab_confirmed at 0.293 on DP-scale cells vs the record's 0.29 — but under an
ascertainment structure that shades crew (the published ladder reaches crew
last, and capacity binds every day). The honesty test: if the record's actual
observation structure — serial re-testing and the late crew mass-test wave —
is armed, does the crew share hold at ~0.29–0.4 (the landing was physics) or
rise materially past ~0.5 (crew infections are genuinely hot and the landing
was ascertainment artifact)? Both outcomes are reportable; neither is a fail.

## Mechanisms (S1, S2 — the ASYM-CONF-01 seam spec)

- **S1 retest-negative sweeps.** Each campaign day may declare
  `retest_tiers` — tiers whose published volume includes re-swabs of hosts
  already holding a negative specimen. Declared on 15–20 Feb (mass re-screen +
  exit swabs) and the 23 Feb crew wave, per Yamahata & Shibata 2020 Table 1
  (cumulative 3,894 tests vs 3,711 aboard; footnote b documents retests). A
  retest is a NEW specimen; the specimen-bar invariant is preserved: a
  confirmed host is never re-swabbed, and no host is swabbed twice on the same
  simulated day. Armed per-arm via `observation_overrides.
  retest_negative_sweeps` → `syndromic.retest_negatives_on_sweep` (default
  off; the no-retest behaviour is the labelled baseline arm).
- **S2 crew reach.** The 23 Feb 2020 day — 831 tests / 57 positives, the
  ladder's step 6 ("all crew members") realized after passenger
  disembarkation — is declared in the campaign record as `wave: "crew_wave"`,
  tiers `[crew]` (Grade A volume, Grade C crew-only composition). Wave-tagged
  days exist only while the scenario arms the wave name, via
  `observation_overrides.campaign_waves` →
  `syndromic.testing_campaigns.waves`.
- **Voyage extension.** The crew wave is sim day 34, past the old 32-day
  window; `duration_days` extends 32 → 35 with provenance (the documented
  campaign runs to 23 Feb). Shared by every arm — cross-arm deltas stay
  single-mechanism.

## Arms (4 × 20 seeds, θ7.9e6, seeds 20200205–20200224)

| arm | overrides | tests |
|---|---|---|
| `boxed_declared` | {} | labelled baseline; bit-identity vs landed cells on the day≤31 slice |
| `boxed_s1` | `retest_negative_sweeps` | retest-negative sweeps only |
| `boxed_s2` | `campaign_waves: [crew_wave]` | crew wave only (S2 isolated — cheap, un-entangles S2 from S1) |
| `boxed_s1s2` | both | the record's full observation structure |

## Witness echoes

`funnel_echo` design flag emits per cell: `specimen_channel` (resolved flags,
armed waves, realized campaign tallies incl. retest and wave splits),
`campaign_specimen_log` (ship's testing-log rows with `retest`/`wave` marks),
`funnel_hosts` (per-host infection/presented/specimen/confirmed days — the
drain table reconstructable at readout without a rerun).

## Execution

80 cells, one Fargate array on `picard-analysis-fargate-queue`, image tag
`covid-crew-reach-01`, s3 `campaign/covid_crew_reach_01/`. Canary = the whole
design; read out, then STOP.
