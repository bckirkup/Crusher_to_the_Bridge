# PLATFORM-FIDELITY-01 readout

Status: measured (findings) — 2026-11-08. Pre-registration (criterion of
record, frozen before any cell ran):
`docs/covid/covid_platform_fidelity_prereg_v1.md`. Ledger entry:
`docs/ledger/PLATFORM-FIDELITY-01.md`. Campaign ledger:
`campaigns/covid/platform_fidelity_01/LEDGER.md`.

- source: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/`
- designs: `picard_framework/runs/covid_platform_fidelity_{dp,gm}_design.json`
- image: `picard-campaign:covid-platform-fidelity-01@sha256:cd59519ab17135252fe13519fac37ad465c5dbb825a80a25c55bcbe0882dd346` (built at `bba29d19`; engine/data tree identical to `e2eb7163`)
- coverage: 200/200 cells (DP 40 + GM 160), 20 seeds per row (20200205–20200224), audit clean — 0 failed comparisons (no `close_zones` fired anywhere), 0 missing platform echoes, 0 missing/unexpected cells, technical failure rate 0.0
- measured at: `e2eb7163`

> **Caveat (2026-11-08): the DP row below is confounded and superseded for
> hull-fidelity inference.** The frozen DP protocols file declared 11
> `exempt_work_zones`, all `mega_cruise_5000` IDs; the `diamond_princess`
> hull carries only `Bridge` of them, so the dedicated arm quarantined ~318
> more crew than the proxy arm (working crew at activation 10–21 vs
> 295–368 of 1045). The DP contrast mixed hull geometry with a different
> effective intervention. The cells are preserved (not deleted, not
> re-scored) and remain evidence of a zone-name-dependent intervention
> defect. The corrective DP-only rerun is pre-registered in
> `docs/covid/covid_platform_fidelity_01b_addendum.md`; the revised DP
> readout will follow it. GM rows are unaffected by this defect (the GM
> protocols file declares no `exempt_work_zones`), though their statistical
> wording is subject to the same corrections listed in the addendum §6.

## Frozen metrics per row

Paired hull delta = dedicated − proxy `recorded_onsets`, takeoff-conditional
(both arms ≥ 10 onsets), median with q05–q95. CRN ρ < 0.3 declares the
unpaired analysis (prereg §4). Takeoff gate: `recorded_onsets ≥ 10`.
**The q05–q95 ranges below are seedwise spreads across the paired seeds,
not confidence intervals**, and no platform-equivalence conclusion may be
drawn from an interval crossing zero (see the 01b addendum §6).

| Row | P(takeoff) proxy | P(takeoff) dedicated | n both-takeoff | paired Δ median [q05, q95] | CRN ρ | unpaired? | asym share proxy | asym share dedicated | onsets med proxy | onsets med dedicated |
|---|---|---|---|---|---|---|---|---|---|---|
| DP @ 7.9e6 | 0.50 | 0.35 | 6 | +130 [−44.75, +297.5] | 0.012 | yes | 0.367 | 0.452 | 64 | 243 |
| GM @ 7.9e6 | 0.20 | 0.30 | 3 | −6 [−8.7, −0.6] | −0.500 | yes | 0.412 | 0.509 | 18 | 14.5 |
| GM @ 1e11 | 1.00 | 1.00 | 20 | +4.5 [−23.4, +20.15] | 0.258 | yes | 0.261 | 0.305 | 52.5 | 53.0 |
| GM @ 2.37e11 | 1.00 | 1.00 | 20 | +3.5 [−12.65, +29.2] | 0.521 | no | 0.248 | 0.278 | 53.5 | 57.0 |
| GM @ 1e12 | 1.00 | 1.00 | 20 | +8.0 [−2.3, +32.25] | 0.657 | no | 0.238 | 0.263 | 48.5 | 60.0 |

Proxy = the platform each event currently rides (`mega_cruise_5000` DP,
`expedition_cruise_450` GM); dedicated = the event-faithful hull
(`diamond_princess`, `greg_mortimer`). Every cell echoes its resolved
`platform_id`, fired protocol ids, and input hashes; pairing is self-audited
against those echoes.

## Reading against the frozen criteria

- **DP @ 7.9e6 (primary, training hull).** The paired interval includes
  zero and rests on 6 both-takeoff seeds; CRN ρ ≈ 0.01 declares the unpaired
  analysis. Unpaired, the dedicated hull shows a higher takeoff-conditional
  onset median (243 vs 64) and asymptomatic share (0.452 vs 0.367) but a
  LOWER takeoff probability (0.35 vs 0.50). Direction is mixed; no frozen
  criterion is met or failed — the platform effect on DP is not resolved at
  20 seeds/arm.
- **GM @ 7.9e6 (primary, held-out hull).** Takeoff is rare on both hulls
  (0.20 / 0.30) — the "fizzle" regime the prereg said to report as-is; no Θ
  was changed. The paired delta's q05–q95 [−8.7, −0.6] excludes zero, which
  literally trips the prereg §5 report-immediately flag, but it rests on 3
  both-takeoff seeds with CRN ρ = −0.5 (unpaired declared), so it is
  hypothesis-grade, not a landed contrast. Unpaired medians (18 vs 14.5
  onsets) and takeoff probabilities (0.20 vs 0.30) show no decisive hull
  effect.
- **GM descriptive layers (1e11, 2.37e11, 1e12; none selectable, none
  fitted).** At the two higher thetas takeoff is certain on both hulls
  (P = 1.0, n = 20 pairs) and the paired deltas are small (+3.5 to +8.0
  onsets on ~50-onset medians) with intervals including zero; CRN pairing
  is moderate (ρ 0.52–0.66) and the unpaired analysis is NOT declared on
  those two rows. At 1e11 ρ = 0.258 declares unpaired. No descriptive row
  shows a platform effect that survives its interval.

## What this settles and what it does not

Settles (measured): the platform-fidelity machinery is proven end-to-end on
both event pairs (override reaches the engine, echoes complete, no
`close_zones` firing, 0/200 technical failures); at the frozen operating
points the hull choice moves the COVID replays by amounts small relative to
seed noise, with no row meeting a frozen significance criterion.

Does not settle (per prereg §7): no platform is selected or crowned, no Θ
is refit, the train/test split is untouched, and the descriptive GM layers
carry no criterion. The DP takeoff-probability gap (0.50 vs 0.35) and the
GM 7.9e6 rare-takeoff regime are the two observations a follow-up design
would need more seeds or a different gate to resolve; neither is asserted
here.

## Provenance

- Cells: `campaigns/covid/platform_fidelity_01/{dp,gm}_t*_*/cell_<seed>.json` in S3 (200 payloads, each with `platform_fidelity` block).
- Readout: `python3 campaigns/covid/platform_fidelity_01/readout.py --prefix s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/`
- Batch jobs: canary `6a7e6185-…`/`4e914d4d-…` (DP), `533758d0-…`/`84caa2e3-…` (GM 7.9e6); full array `d8d4cbb7-…`, `411dc224-…`, `a1aecf18-…`, `8bcc7cc2-…`, `7ce2d5d3-…`, `41308e2f-…` (jobdef revs :1–:10, all digest-pinned).
- Bring-up repairs (declared, no epidemiological constant touched): prereg §8.
