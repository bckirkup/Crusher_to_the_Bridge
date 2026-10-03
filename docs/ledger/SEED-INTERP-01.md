# SEED-INTERP-01
**Date:** 2026-10-03
**Commit:** 1e158d47
**Pathogens:** all
**Status:** measured
**Measured at:** 1e158d47

The two runtimes compared: the campaign image (digest
sha256:017a0db8…, python 3.11.17 / numpy 2.4.6) and a local venv
(python 3.12.13 / numpy 2.5.0).

## What this entry records

A run seed pins a trajectory **only within one interpreter×numpy
toolchain**. The same engine code (`ENGINE_GIT_SHA=1e158d47`,
`transmission_core` source sha-identical), same run_id
`fl_norovirus_expedition_cruise_450_…_s8016`, same manifest cell:

- Batch / image runtime (python 3.11.17, numpy 2.4.6): 25 infected, peak 14
- Local venv (python 3.12.13, numpy 2.5.0): 26 infected, peak 15

Running the image itself on the local box reproduces the Batch dump
exactly, so the divergence is the dependency set, not the hardware or
the job harness. Ruled out empirically: `PYTHONHASHSEED` 0 vs 42
(bit-identical), `NPY_DISABLE_CPU_FEATURES` with AVX2/AVX-512 off
(identical). All sim RNG is `np.random.default_rng(seed)` — PCG64 is
platform-stable; the drift enters through float-level computation in
the dependency versions, and `uv.lock` itself selects numpy by
interpreter: 2.4.6 on `python_full_version < '3.12'`, 2.5.0 on
`>= '3.12'`. The campaign Dockerfile is `python:3.11-slim` while CI and
dev venvs run 3.12+.

## Consequences

- **Batch campaign dumps cannot be reproduced locally.** A batch seed's
  voyage is a different draw stream under py≥3.12/np2.5 — local replays
  of "the same seed" measure a different realization. Cell-level
  pooled ratios stay meaningful (each is a within-image distribution);
  per-seed counter forensics must run in-image.
- **Bit-sensitive pins are toolchain-pins.** Authored-window goldens
  (e.g. `tests/test_covid_hull_change_detector.py` hull tuples) are
  valid only for the interpreter×numpy they were read on. Repin per
  convention: read the tuple from the CI job on the same shard, record
  the job id in the pin comment.
- The Diamond Princess `(3,12)` hull-pin discrepancy investigated on
  2026-10-03 (off-arm `(2278,245,3063,999,663)` vs pin
  `(2575,2131,2617,688,618)` on a py3.12/np2.5 box while CI at pre-#859
  main passed) resolves here: env-sensitivity, not a CAREGIVER-V1 leak.
  No code change; the DP pin under the post-#860 stack is repinned from
  the next CI nightly read per convention.
