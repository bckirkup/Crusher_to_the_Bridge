# PLATFORM-FIDELITY-01b campaign ledger

Diamond Princess dedicated-arm corrective rerun under the addendum
`docs/covid/covid_platform_fidelity_01b_addendum.md` (merged in #1182).
Proxy baseline = the 20 reused PLATFORM-FIDELITY-01 `dp_t7e6_proxy` cells
(proven behaviorally equivalent under the union list, addendum §3).
GM untouched.

## 1. Design (frozen, from the addendum)

- Scenario `diamond_princess_2020`, voyage declared; Θ = 7.9e6,
  infection_age_days 6.8, imports 1, sanitary_visit_mode dwell_weighted.
- Seeds 20200205–20200224 (20), CRN pairing with the PF-01 proxy cells.
- Protocols `data/config/protocols_covid_pf_dp_01b.json` (SOP-017-MESSBOX,
  union `exempt_work_zones`); design
  `picard_framework/runs/covid_platform_fidelity_01b_dp_design.json`.
- Execution count: 20 new Batch executions (dedicated block only).

## 2. Preflight evidence (addendum §3, gathered before submission)

- Zone resolution: proxy resolves all 11 PF-01 IDs, none of the 6 DP-native
  IDs; dedicated resolves `Bridge` + the 6 DP-native IDs, none of the other
  10 PF-01 IDs (verified against both `spatial_layout.json` files).
- Proxy equivalence: original-11 vs union exempt counts identical on all 20
  seeds at init; one full local proxy cell (seed 20200205) diffed against
  its PF-01 payload — 436 leaf fields, 19 differences all metadata echoes
  (design id, protocols path/hash, declaration list), every epidemiological
  field bit-identical.
- Dedicated under the union (init probes, 20 seeds): exempt crew 98–135 per
  seed (mean 114.3), all posting to the 7 hull-native essential zones.

## 3. Local smoke (2026-11-08, dev venv)

- Proxy equivalence full cell (seed 20200205, Θ 7.9e6, full voyage): PASS —
  see §2 (bit-identical epidemiology vs PF-01).
- Dedicated `dedicated_diamond_princess` seed 20200205, full voyage: PASS —
  resolved `diamond_princess` vs declared `mega_cruise_5000`;
  `SOP-017-MESSBOX` fired, no `close_zones`; working crew 120/1045 at
  activation, posted zones exactly {Bridge, MainGalley, Engine_Room, Stores,
  Laundry, CrewMess, CrewMessOff}; boxed `crew_meal_service` active_epochs
  360; 8 input hashes echoed, `protocols_sha256` matches the 01b file.
- Dry-run: array size 20, block/seeds/queue as designed.

## 4. Image

| Field | Value |
|---|---|
| Tag | `covid-platform-fidelity-01b` |
| Digest | `sha256:ed4700c6ce9a8b47b66fbba4e7a2f54b36e12a218504259fa3c614511e52bdfc` |
| Built from | `7d79b7d0` (root `Dockerfile` base + `deploy/aws/Dockerfile.campaign` overlay, both stamped `ENGINE_GIT_SHA=7d79b7d0`) |
| Preflight | ENTRYPOINT `["python3"]`; all 01b files present in-container (worker, entry hook, campaign.json, 01b protocols, 01b design, `campaign_entrypoint.py`); 17-ID union list verified in-image |

## 5. Runs

| Date | Block | Seeds | Cells | Job | SHA | Digest | Jobdef rev | Wall | Result |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-08 | `dp_t7e6_dedicated` | 20200205–224 | 20 | `5bd3f49c-3483-4a33-94fb-772f18f5c807` | `7d79b7d0` | `sha256:ed4700c6…` | `:1` | ~25 min | SUCCEEDED 20/20 |

The whole 01b campaign IS the canary-sized block (20 seeds at one arm-row),
submitted per the owner-approved addendum after local smoke + dry-run.
Campaign COMPLETE: 20/20 cells, 0 technical failures.

## 6. Readout (2026-11-08)

Readout: `python3 campaigns/covid/platform_fidelity_01b/readout.py` pairing
the reused PF-01 proxy cells with the 01b dedicated cells on seed. Result
(full record in `docs/covid/covid_platform_fidelity_readout.md` §01b and
`docs/ledger/PLATFORM-FIDELITY-01B.md`):

- P(takeoff): proxy 0.50 vs dedicated 0.30 (n = 20 each).
- Takeoff-conditional paired Δ (n = 5 both-takeoff seeds): median +114
  onsets, q05–q95 [−66.6, +358.6] — a SEEDWISE SPREAD, not a confidence
  interval; it includes zero and no equivalence conclusion is drawn from
  that.
- CRN ρ = −0.137 → unpaired analysis declared.
- Unconditional onset burden (all 20 seeds): median 12.5 (proxy) vs 2.0
  (dedicated); totals 1103 vs 1457 — the dedicated hull's outbreaks are
  larger when they take off, despite the lower takeoff probability.
- Takeoff-conditional asymptomatic share: 0.367 (proxy) vs 0.427 (dedicated).
- Audit clean: 0 witness failures (working crew 98–135 at activation, posted
  zones ⊆ the 7 DP-native essential IDs on every cell), 0 `close_zones`
  firings, 0 missing platform echoes, 0 missing cells, technical failure
  rate 0.0.
- Input-hash contract vs PF-01 dedicated cells: platform, scenario,
  pathogen, and agent-profile hashes identical; only `design_sha256`,
  `protocols_sha256`, and `run_spec_canonical_sha256` differ (the two
  declared changes).
