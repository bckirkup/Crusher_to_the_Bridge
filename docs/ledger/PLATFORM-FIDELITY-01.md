# PLATFORM-FIDELITY-01
**Date:** 2026-11-08
**Commit:** e2eb7163
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** e2eb7163

Cells ran on image
`picard-campaign:covid-platform-fidelity-01@sha256:cd59519ab17135252fe13519fac37ad465c5dbb825a80a25c55bcbe0882dd346`,
built at `bba29d19` (engine/data tree identical to `e2eb7163`).

PLATFORM-FIDELITY-01 measured how much hull fidelity moves the two frozen
2020 COVID event replays — Diamond Princess (training) and Greg Mortimer
(held-out) — replayed on their event-faithful platforms versus the generic
proxy platforms they rode, everything else held fixed. Pre-registration:
`docs/covid/covid_platform_fidelity_prereg_v1.md`; readout:
`docs/covid/covid_platform_fidelity_readout.md`; campaign:
`campaigns/covid/platform_fidelity_01/` (200/200 cells, 20 seeds per row,
0 technical failures, no `close_zones` firing anywhere).

Measured result: at the frozen operating points the hull choice moves the
replays by amounts small relative to seed noise. DP @ 7.9e6: P(takeoff)
0.50 proxy vs 0.35 dedicated, paired Δ median +130 onsets [−44.75,
+297.5] over 6 both-takeoff seeds, CRN ρ 0.012 (unpaired declared). GM
@ 7.9e6: rare takeoff on both hulls (0.20 / 0.30, reported as-is, no Θ
change), paired Δ −6 [−8.7, −0.6] over 3 seeds with ρ −0.5 (unpaired
declared; interval-excludes-zero flag is hypothesis-grade at n=3). GM
descriptive layers @ 1e11 / 2.37e11 / 1e12 (P(takeoff) = 1.0, n = 20 pairs):
paired Δ medians +4.5 / +3.5 / +8.0 onsets on ~50-onset medians, all
intervals include zero; CRN ρ 0.26 / 0.52 / 0.66 (unpaired declared only
at 1e11). No frozen criterion is met or failed on any row; no platform is
selected, no Θ refit, the train/test split untouched.

Machinery delivered with the campaign: the `platform_id` arm key in
`picard_framework/covid_boarding_screen.py` (rewrites `catalog.platform_id`),
the frozen per-event-pair protocols files
(`data/config/protocols_covid_pf_{dp,gm}.json`), and the cell-worker
`platform_fidelity` echo block (resolved platform, fired protocol ids,
`close_zones` flag, per-input SHA-256 hashes) — the payload did not echo
`platform_id` before this campaign.

Bring-up repairs, declared in prereg §8 (data consistency, no epidemiological
constant touched): `data/platforms/diamond_princess/voyage_config.json`
disabled worked-example blocks repointed (`hazard_sources` penetration zones
to real hull zones) and emptied (`ship_functions.functions` staffed classes
the DP scenario does not declare); both blocks were `enabled: false` and
behaviorally inert either way.
