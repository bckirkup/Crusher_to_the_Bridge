# COVID platform-fidelity study — PLATFORM-FIDELITY-02 pre-registration

Status: pre-registered, frozen before any PLATFORM-FIDELITY-02 cell runs —
2026-11-08. This is the criterion of record for the larger-seed Diamond
Princess follow-up commissioned in
`docs/covid/covid_platform_fidelity_handoff_2026_11_08.md` §8. Nothing below is
altered after the first PF-02 cell's surface is seen. Campaign registration:
`campaigns/covid/platform_fidelity_02/`; design:
`picard_framework/runs/covid_platform_fidelity_02_dp_design.json`; power
calculation: `campaigns/covid/platform_fidelity_02/power_analysis.py` +
`power_analysis.json`.

## 1. Question

Does the Diamond Princess COVID replay still show the 01b hull-fidelity
contrast — proxy `mega_cruise_5000` vs event-faithful `diamond_princess` —
when the paired-seed count is raised from 20 to the seed count fixed by the
pre-registered power calculation? This remains a **pre-registered
sensitivity measurement**: it selects no Theta, crowns no canonical platform,
reopens no train/test split, touches no GM cells, and does not retune the
frozen union `exempt_work_zones`.

## 2. Power calculation (analysis-only, frozen seed count)

The calculation runs on the committed PF-01 proxy and PF-01b dedicated cell
payloads already in S3; it needs no new simulation cells. It estimates, from
the 20 paired seeds, the power of the two primary endpoints as a function of
seeds/arm:

- **P(takeoff)**: exact two-sided McNemar on discordant pairs, plugging in
  the observed discordant rate (6/20) and proxy-only split (5/6 of
  discordants).
- **Both-takeoff outbreak size**: one-sample t on the both-takeoff paired
  `dedicated - proxy` `recorded_onsets` deltas (n=5, mean +109.0, SD 193.6),
  with the both-takeoff rate (5/20) bootstrapped over the empirical pair-type
  distribution of the 20 seeds.

Selection rule, frozen here and implemented in `power_analysis.py`: smallest
grid n with **≥0.90 power on both endpoints at the observed plug-in rates**
and **≥0.80 power on both under halved event rates** (both-takeoff 0.25 →
0.125; discordant 0.30 → 0.15). Reproduce:

```bash
AWS_PROFILE=picard python3 campaigns/covid/platform_fidelity_02/power_analysis.py \
  --out campaigns/covid/platform_fidelity_02/power_analysis.json
```

Result (`power_analysis.json`): **200 seeds/arm = 400 cells** is the smallest
grid point satisfying the rule. At n=200: P(takeoff) power 0.9999 observed /
0.9600 halved; both-takeoff size power 0.9978 observed / 0.8862 halved. The
next lower grid point, n=160, fails the halved-rate size criterion
(0.7803 < 0.80). Unconditional onset burden is reported for context only; it
is not powered or selected on (Welch/paired-t power remains ≈0.19/0.21 at
n=100 and only ≈0.89/0.93 at n=800), so the primary endpoints are the
takeoff indicator and the both-takeoff paired size.

## 3. Frozen design

- Scenario `diamond_princess_2020`, voyage declared; Θ = 7.9e6,
  `infection_age_days` 6.8, imports 1, `sanitary_visit_mode`
  `dwell_weighted`; boxed `sect_mess_boxed` crew-mess overrides verbatim from
  PF-01/01b.
- Protocols `data/config/protocols_covid_pf_dp_01b.json` (SOP-017-MESSBOX,
  union `exempt_work_zones`, frozen).
- Arms: `proxy_mega_cruise` (baseline, empty overrides) and
  `dedicated_diamond_princess` (`platform_id: diamond_princess`).
- Seeds 20200205–20200404 (200/arm; `seed_base + i`), the contiguous extension
  of the frozen 01b series; same seed list on both arms for CRN pairing.
- Both arms are rerun over the full series so PF-02 is self-contained: 400
  cells. The first 20 dedicated seeds (20200205–20200224) are the
  canary/replication row against PLATFORM-FIDELITY-01b.
- No stopping rule beyond the fixed n: no interim significance looks, no
  extension, no re-analysis with a transformed endpoint. Technical-failure
  rate >10% of cells, any `close_zones` firing, or any witness/hash-contract
  audit failure stops the array for diagnosis.

## 4. Metrics and statistics (frozen)

Primary endpoints (the only quantities the power calculation selected on):

1. **P(takeoff)** per arm = fraction of all 200 seeds with
   `recorded_onsets >= 10`; exact two-sided McNemar on the discordant pairs
   (`proxy_only` vs `dedicated_only`), α = 0.05.
2. **Both-takeoff outbreak size**: per-seed `dedicated − proxy`
   `recorded_onsets` on seeds where BOTH arms record ≥10 onsets; one-sample
   t on those deltas, two-sided α = 0.05, mean delta with 95% t CI.

Reported, never selected:

- Median paired delta with q05–q95 on both-takeoff seeds — a **seedwise
  spread, NOT a confidence interval**.
- Unconditional onset burden per arm (median, total, mean over all 200
  seeds) with Welch t as context only.
- Takeoff-conditional asymptomatic share of `lab_confirmed` per hull.
- CRN Pearson ρ on both-takeoff seeds.
- `proxy_only` / `dedicated_only` takeoff counts and all audit fields.

Binding corrections carried from the 01b addendum §6 and Edison's audit
(`platform-fidelity-01-statistical-audit-v47d`): q05–q95 are seedwise spreads,
not CIs; report unconditional onset burden + takeoff probabilities alongside
any conditional endpoint; never conclude platform equivalence from an
interval crossing zero; no "small relative to seed noise" claims. A
non-rejection at n=200 is "unresolved at this n", never equivalence.

## 5. Audits and stop rules (frozen)

- **Failed comparison**: any cell whose protocol engine fired a
  `close_zones` protocol is a FAILED COMPARISON — reported, never deleted.
- **Technical failures**: missing payloads or errored cells are counted; a
  rate above 10% of a submitted block stops the array.
- **Witness/hash contract**: every cell echoes the `platform_fidelity` block
  (resolved `platform_id`, protocols path, per-input SHA-256, fired protocol
  ids, `close_zones_fired_flag`); the readout audits the proxy echo
  (`mega_cruise_5000`) and the dedicated witness/hash contract. Any mismatch
  stops the array.
- **Report immediately**: any `close_zones` firing; technical-failure rate
  >10%; any witness/hash audit failure; any primary endpoint rejecting at
  α = 0.05 (reported as a measured platform-fidelity effect, not a platform
  selection).
- Campaign gate (bounded-research-sessions rule): geometry/seed gate
  validated, local smoke passed, dry-run count == design, image pinned by
  digest, canary `dp_t7e6_dedicated_canary` (20 seeds, 20200205–20200224)
  read out — then **stop and report**; the owner decides whether the
  remaining 380 cells run.

## 6. Execution order

1. `scripts/campaign describe campaigns/covid/platform_fidelity_02/campaign.json`
   — count must equal the design's 400 cells.
2. Local smoke of the worker proving the `platform_id` override reaches the
   engine and the payload contract is unchanged.
3. Build and push the campaign image; pin `image_tag` by digest in
   `campaigns/covid/platform_fidelity_02/campaign.json`.
4. Canary `dp_t7e6_dedicated_canary` (20 cells) → read out → STOP.
5. Owner decision → `dp_t7e6_proxy` (200) + `dp_t7e6_dedicated_rest` (180).
6. Readout `campaigns/covid/platform_fidelity_02/readout.py`; ledger/handoff
   update; interpretation and next decision.

## 7. Non-goals

No Batch submission beyond the campaign-gate canary in this package; no Θ
refit or adaptation; no platform selected or crowned; no GM cells; no GM
redesign; no retuning of the union `exempt_work_zones`; no hull zone renames;
USS Theodore Roosevelt is out of bounds as a comparator.
