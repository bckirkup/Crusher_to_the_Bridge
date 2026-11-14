# CONTAM Phase 1 readout addendum: exact integral and pre-D1 caveat

**Status:** Measured transport-correctness addendum. No epidemiology claims. The committed [`READOUT.md`](READOUT.md) and [`readout/phase1_readout.json`](readout/phase1_readout.json) are unchanged.

Machine-readable addendum: [`readout/phase1_exact_integral_addendum.json`](readout/phase1_exact_integral_addendum.json).

## What this adds

- Recomputed `b_v_h` exactly for every frozen hull×lane×source-zone×timing-pattern cell (322 records) from the same linear operator: N from the native `ContamTransportEngine` tree at `baseline_sha` `a3dab46fcf50ee4c51b5962d9139c27a3f76e0f3`, E/P from the frozen field cache SHA256 `b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5`.
- `endpoint_sampled_b_v_h` reproduces the campaign's hourly right-endpoint rule; `exact_b_v_h` is the matrix-exponential integral of total retained mass fraction over the 12 h horizon; `exact_over_endpoint` is their ratio. For `t0_t1_split`, the exact value is `0.5 * integral_0^12h + 0.5 * integral_0^11h` for the half pulse injected at t = 1 h.
- Spot checks reconcile with the audit: Phase 1-condition `Mess_Hall` gives N exact/endpoint `0.312922 / 0.040083` and E `0.285604 / 0.024018` (audit §3.3: `0.313 / 0.040` and `0.286 / 0.024`); §4.1 sanitary-source means reproduce within `5e-4` h; the eta0.3/decay0.1 JSON reproduces to about `1e-13` h.

## Caveat

Per `docs/proposals/forced_exhaust_audit_and_fix_plan.md` §4.2 and `docs/ledger/CONTAM-SANITARY-DIR-01.md`: N-lane cells carry reverse sanitary paths as authored pre-D1; every `sanitary_branch` source cell's `b_v_h` is dominated by the endpoint-sampling artefact; N-vs-E contrasts are partly reverse-paths plus sampling, not field generation alone. The readouts remain valid as-run at their `baseline_sha`; D1 does not change E-lane caches; X1/X2 exporter fixes would require field-cache v2 plus new `design_id`s, and the frozen v1 caches stay unchanged.
