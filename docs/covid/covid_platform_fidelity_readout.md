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

## PLATFORM-FIDELITY-01b — corrected DP contrast (2026-11-08)

The DP row above is confounded (see the caveat) and is superseded for
hull-fidelity inference by the 01b corrective rerun
(`docs/covid/covid_platform_fidelity_01b_addendum.md`,
`campaigns/covid/platform_fidelity_01b/`, ledger
`docs/ledger/PLATFORM-FIDELITY-01B.md`). The 01b design reran ONLY the 20
dedicated cells with the function-matched union `exempt_work_zones`
(Θ 7.9e6, seeds 20200205–20200224, frozen); the 20 PF-01 proxy cells are
reused as the baseline on proven behavioral equivalence (addendum §3:
union list inert on the proxy per-seed, and one full local proxy cell
bit-identical in every epidemiological field to its PF-01 payload).
20/20 cells, 0 technical failures; witness audit clean on every cell
(working crew 98–135 at activation, posted zones ⊆ the 7 hull-native
essential IDs, boxed service active, `SOP-017-MESSBOX` fired, no
`close_zones`). Input-hash contract vs PF-01 dedicated cells: platform,
scenario, pathogen, and agent-profile hashes identical; only the design,
protocols, and run-spec hashes differ.

| Row | P(takeoff) proxy | P(takeoff) dedicated | n both-takeoff | paired Δ median [q05, q95] | CRN ρ | unpaired? | asym share proxy | asym share dedicated | onsets med proxy (all seeds) | onsets med dedicated (all seeds) | onsets total proxy | onsets total dedicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DP @ 7.9e6 (01b corrected) | 0.50 | 0.30 | 5 | +114 [−66.6, +358.6] | −0.137 | yes | 0.367 | 0.427 | 12.5 | 2.0 | 1103 | 1457 |

Reading, per the addendum §6 corrections: the q05–q95 is a SEEDWISE SPREAD
across the 5 both-takeoff pairs, not a confidence interval, and it includes
zero — no platform-equivalence conclusion is drawn from that. The
unconditional onset burden (all 20 seeds regardless of the takeoff gate)
shows the dedicated hull's outbreaks are LARGER when they take off (total
1457 vs 1103 onsets; conditional medians on the 6 dedicated takeoff seeds
run to 441) despite a LOWER takeoff probability (0.30 vs 0.50) and a lower
unconditional median (2.0 vs 12.5). This is the same directional pattern
the confounded PF-01 DP row hinted at (dedicated conditional median 243 vs
64), now measured with the same effective quarantine policy on both hulls.
At 20 seeds/arm the frozen criteria resolve nothing; no platform is
selected, no Θ refit, the train/test split untouched.

## What this settles and what it does not

Settles (measured): the platform-fidelity machinery is proven end-to-end on
both event pairs (override reaches the engine, echoes complete, no
`close_zones` firing, 0/200 technical failures); at the frozen operating
points the hull choice moves the COVID replays by amounts small relative to
seed noise, with no row meeting a frozen significance criterion.

Does not settle (per prereg §7): no platform is selected or crowned, no Θ
is refit, the train/test split is untouched, and the descriptive GM layers
carry no criterion. For DP, the corrected 01b contrast (above) replaces
the confounded PF-01 row: takeoff probability favors the proxy (0.50 vs
0.30) while outbreak size conditional on takeoff favors the dedicated hull
(unconditional totals 1103 vs 1457), and the paired endpoint rests on 5
both-takeoff seeds with a seedwise spread that includes zero — unresolved
at 20 seeds/arm. The GM 7.9e6 rare-takeoff regime remains the other
observation a follow-up design would need more seeds or a different gate
to resolve; neither is asserted here.

## Provenance

- Cells: `campaigns/covid/platform_fidelity_01/{dp,gm}_t*_*/cell_<seed>.json` in S3 (200 payloads, each with `platform_fidelity` block).
- Readout: `python3 campaigns/covid/platform_fidelity_01/readout.py --prefix s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/`
- Batch jobs: canary `6a7e6185-…`/`4e914d4d-…` (DP), `533758d0-…`/`84caa2e3-…` (GM 7.9e6); full array `d8d4cbb7-…`, `411dc224-…`, `a1aecf18-…`, `8bcc7cc2-…`, `7ce2d5d3-…`, `41308e2f-…` (jobdef revs :1–:10, all digest-pinned).
- Bring-up repairs (declared, no epidemiological constant touched): prereg §8.
- 01b cells: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/cell_<seed>.json` (20 payloads); proxy baseline reused from the PF-01 `dp_t7e6_proxy` block. Batch job `5bd3f49c-3483-4a33-94fb-772f18f5c807` (jobdef rev :1, digest `sha256:ed4700c6…`, image built at `7d79b7d0`).
- 01b readout: `python3 campaigns/covid/platform_fidelity_01b/readout.py --proxy-prefix s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/dp_t7e6_proxy/ --dedicated-prefix s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/`
