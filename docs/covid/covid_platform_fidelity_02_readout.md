# PLATFORM-FIDELITY-02 readout

Status: measured (findings) — 2026-11-08. Pre-registration (criterion of record,
frozen before any PF-02 cell ran):
`docs/covid/covid_platform_fidelity_02_prereg.md`. Ledger entry:
`docs/ledger/PLATFORM-FIDELITY-02.md`. Campaign ledger:
`campaigns/covid/platform_fidelity_02/LEDGER.md`.

- source: proxy `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_02/dp_t7e6_proxy/`; dedicated `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_02/dp_t7e6_dedicated_{canary,rest}/`
- design: `picard_framework/runs/covid_platform_fidelity_02_dp_design.json`
- image: `picard-campaign:covid-platform-fidelity-02@sha256:d641a0d69e54b4e054b2f59b9237ddb7d689d75413aaba2760c8f9cf8f0060c6705` (built at `db95a4f2`)
- coverage: 400/400 cells — 200 proxy + 200 dedicated (20 canary + 180 rest), seeds 20200205–20200404, 0 Batch failures, technical-failure rate 0.0
- measured at: `db95a4f2`
- machine-readable summary: `campaigns/covid/platform_fidelity_02/readout.json` from `python3 campaigns/covid/platform_fidelity_02/readout.py`

## Frozen metrics

Paired hull delta = dedicated − proxy `recorded_onsets`, takeoff gate
`recorded_onsets >= 10`. q05–q95 are seedwise spreads, NOT confidence
intervals; unconditional onset burden is reported alongside the
takeoff-conditional endpoint; no platform-equivalence conclusion is drawn
from an interval crossing zero.

### Primary endpoints

| Endpoint | Result |
|---|---|
| P(takeoff) | proxy 0.535 (107/200) vs dedicated 0.510 (102/200); discordant proxy-only 49 vs dedicated-only 44; exact two-sided McNemar **p = 0.678532** — not rejected |
| Both-takeoff outbreak size | n = 58 both-takeoff seeds; dedicated − proxy mean **+92.672** onsets, 95% t CI **[+15.033, +170.311]**, two-sided **p = 0.020167** — rejects α = 0.05; median paired Δ +27.5 with seedwise q05–q95 [−371.1, +619.45]; CRN ρ = 0.441203 |

### Reported, never selected

| Quantity | proxy | dedicated |
|---|---:|---:|
| unconditional onset median | 15.5 | 12.5 |
| unconditional onset mean | 85.615 | 112.670 |
| unconditional onset total | 17,123 | 22,534 |
| Welch p (context only) | — | 0.168304 |
| takeoff-conditional asymptomatic share | 0.395225 | 0.497643 |

## Reading

The 20-seed takeoff-probability gap (01b: proxy 0.50 vs dedicated 0.30) does
not survive at n = 200: proxy 0.535 vs dedicated 0.510, McNemar p = 0.679.
The both-takeoff outbreak-size endpoint does reject: on the 58 seeds where
both arms take off, dedicated-hull outbreaks are larger by mean +92.7 onsets
(median +27.5; seedwise q05–q95 [−371.1, +619.45] is a spread, not a CI; the
inferential statement is the one-sample t CI/p above). Per the pre-registration
this is a measured platform-fidelity effect, not a platform selection: no
Theta refit, no canonical-platform crowning, train/test split untouched, GM
still closed.

Unconditional burden is mixed and context-only: dedicated total and mean
onsets are higher (22,534 vs 17,123; 112.67 vs 85.615) while the unconditional
median is lower (12.5 vs 15.5), Welch p = 0.168. Dedicated takeoff-conditional
asymptomatic share is higher (0.498 vs 0.395). CRN ρ = 0.441 on both-takeoff
seeds.

## Audit

Clean: 0 missing cells, 0 missing platform echoes, 0 `close_zones` failed
comparisons, technical-failure rate 0.0. Proxy echo audits clean
(`mega_cruise_5000`); dedicated input-hash/protocols/posting/meal-service
witnesses are clean.

One inherited diagnostic needs explicit classification: `readout.py` reuses
the PLATFORM-FIDELITY-01b `_witness_audit`, whose working-crew band
(95–140) was calibrated on the 01b 20-seed canary (observed 98–135). At n =
200 that band flags 16 dedicated rest seeds — 20200230, 20200254, 20200258,
20200271, 20200275, 20200293, 20200309, 20200339, 20200348, 20200360,
20200365, 20200384, 20200394, 20200399, 20200400, 20200401 — with
at-activation `working_crew_count` 71–144 (15 below, 1 above; 0/20 canary
seeds flagged). Inspection shows these cells still fire `SOP-017-MESSBOX` at
epoch 384, keep the same union `exempt_work_zones`, post only to the 7
DP-native essential zone IDs, keep boxed crew-meal service active, and
satisfy working + confined = 1045. The variation is seed-level pre-activation
confinement over the extended seed series, not an exempt-policy or hash
breach; the PF-02 design/prereg froze the echo/hash/posted-zone contract, not
a new numeric crew band. The machine-readable audit still lists the 16 seeds
for transparency.

Next decision: accept this band-calibration diagnosis and close
PLATFORM-FIDELITY-02, or rule the inherited 01b band binding for PF-02 and
reopen the witness audit before closing. Either way the both-takeoff size
rejection above is the measured PF-02 result.

## Provenance

- Cells: S3 prefixes above; 400 payloads with `platform_fidelity` echoes.
- Readout: `AWS_PROFILE=picard python3 campaigns/covid/platform_fidelity_02/readout.py --out campaigns/covid/platform_fidelity_02/readout.json`.
- Batch: canary child `015a87fb-faf2-4bd1-9008-164ae1765816` + array `a63d7a13-408b-45cf-b8f1-539b462fbacd` (jobdef `:1`/`:2`); full arrays `982768ff-930c-4c80-a45e-da8dab93a115` (`:3`, 180 cells) and `0f3e898f-35ba-490d-ab89-fe04a6f98201` (`:4`, 200 cells), all digest-pinned.
- Power/design freeze: `campaigns/covid/platform_fidelity_02/power_analysis.json`, `docs/covid/covid_platform_fidelity_02_prereg.md`.
