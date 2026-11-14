# CONTAM Phase 2 readout addendum: exact integral and pre-D1 caveat

**Status:** Measured transport-correctness addendum. No epidemiology claims. The committed [`READOUT.md`](READOUT.md) and [`phase2_readout.json`](phase2_readout.json) are unchanged.

Machine-readable addendum: [`phase2_exact_integral_addendum.json`](phase2_exact_integral_addendum.json).

## What this adds

- Recomputed `b_v_h` exactly for every frozen hull×arm×lane×source-zone×timing-pattern cell (1200 records) from the same linear operator: N from the native `ContamTransportEngine` tree at `baseline_sha` `71dd32ec5fd79803adf1b07fffb59cd2a481544a` with the frozen arm op list applied in memory, E/P from the frozen field cache SHA256 `e8d61dd4703ee6c2a7e5624db35d8c80f3f034c6f76ac533e91a5bfdd74fc6c6`. P remains baseline-arm only.
- `endpoint_sampled_b_v_h` reproduces the campaign's hourly right-endpoint rule; `exact_b_v_h` is the matrix-exponential integral of total retained mass fraction over the 12 h horizon; `exact_over_endpoint` is their ratio. For `t0_t1_split`, the exact value is `0.5 * integral_0^12h + 0.5 * integral_0^11h` for the half pulse injected at t = 1 h.
- Spot checks reconcile with the audit: §4.1 sanitary-source means reproduce within `5e-4` h for the four-cruise panel, and the eta0.3/decay0.1 JSON reproduces to about `1e-13` h for the named expedition/destroyer sources.

## Caveat

Per `docs/proposals/forced_exhaust_audit_and_fix_plan.md` §4.2 and `docs/ledger/CONTAM-SANITARY-DIR-01.md`: N-lane cells carry reverse sanitary paths as authored pre-D1; every `sanitary_branch` source cell's `b_v_h` is dominated by the endpoint-sampling artefact; N-vs-E contrasts are partly reverse-paths plus sampling, not field generation alone. The readouts remain valid as-run at their `baseline_sha`; D1 does not change E-lane caches; X1/X2 exporter fixes would require field-cache v2 plus new `design_id`s, and the frozen v1 caches stay unchanged.
