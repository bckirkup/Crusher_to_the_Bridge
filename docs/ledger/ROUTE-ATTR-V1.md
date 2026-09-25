# ROUTE-ATTR-V1
**Date:** 2026-09-25
**Commit:** be121a0
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** be121a0

Whole-voyage route attribution and observation-channel ascertainment
audit on the declared Diamond Princess replay (arm `D0_declared` of
`covid_plume_dose_assay_v1`, seeds 20200205 / 20200217 / 20200222, full
768 epochs) via the new `tools/covid_route_attribution.py`. Run locally
under CPython 3.12 — structural reads only; not cross-comparable with
the Batch (3.11) campaign counts. Readout:
`docs/covid/covid_route_attribution_v1_readout.md`.

## Measured

**Routes.** On the saturating seed (20200205) 99.8% of 3,531 infections
fire before quarantine day 16 — 90% droplet-dominant, zone-class `other`
2,490 / crew_mess 515 / cabin 499. On the two slow seeds the burn
re-centres into the during-quarantine window with cabin zones carrying
1,318/1,517 of the during mass — the confinement channel.

**Ring-vs-pool dose split.** Droplet dose reaching infected agents is
~98% ring-side (dose-weighted): near-field plume 60–69% + cabin-mate
addback 30–40%; the far-field pool carries ~2%. Per-agent the share is
bimodal (median 0.28–0.65, q05 0, q95 ≈0.999; 44–56% majority-ring).
Both channels exceed the infection threshold for most hosts — the
mechanism behind PARTNER-RATE-V1 / PLUME-DOSE-V1 flatness: cutting a
ring arm takes a host's dose from huge to still-sufficient, so recorded
mass does not move. The cabin-mate addback alone carries 30–40% of
droplet dose weight — the largest fixed-ring channel the arm grammar
cannot express.

**Observation channel.** The channel confirms ~76% of all infected
(2,055–2,639) and dates 93–100% of confirmed datable-course cases at
the true onset day — vs the record's 197 dated of ~712 confirmed
(0.28). 85–89% of dated onsets are mild severity — the stratum a
shipboard investigation loses to recall and non-presentation. The
channel does include — and date — cases the published investigation
missed; dating ascertainment is a ~3.4× multiplier inside the ~18×
conditional gap (case ascertainment ~3.0–3.7× more).

## Open threads named by this measurement

- The arm grammar still cannot express "no cabin-mate addback" or a
  changed index day-0 exposure geometry — the two remaining
  transmission-side suspects.
- An onset-dating ascertainment arm (record-consistent dating
  probability on confirmed cases) would split the ~18× gap into
  channel vs transmission shares — the funnel puts roughly one third
  on the channel.
- Severity bookkeeping anomaly: on seed 20200205 zero infected agents
  carry `none`/`asymptomatic` severity despite the profile's 0.31
  asymptomatic base probability; the slow seeds do show ~20% — flagged,
  unresolved.
