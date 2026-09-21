# COVID Θ handoff — 2026-09-21 (THETA-SCREEN-V10 canary closed)

> **Status:** Handoff record. Reports **no new numbers**: every figure is quoted
> from the ledger entry or readout that measured it, with that entry's
> `Measured at` SHA. Successor to
> `docs/covid/covid_theta_handoff_2026_09_19.md`, which stays valid for
> everything before the v10 canary. Read `docs/covid/covid_open_ledger.md` §1
> before quoting any COVID figure.

## 1. The question

What mean per-host susceptibility Θ, on `diamond_princess_2020` with one
declared import and a declared index `onset_day = -1.0`, reproduces the
Diamond Princess observables — primarily `covid.T1` (197 recorded onsets by
20 Feb 2020) with `covid.T3` (634 cumulative PCR positives on 3,063 specimens)
and the index-geometry invariant — on the engine as repaired by QUAR-EXEMPT-01
(#633, `861a0b9`) and REINFECT-01 (#636, `d62f10d`)? Success is an admissible
Θ whose seeds put onset mass *near* the target, not an interval that spans it
by mixing extinct with saturated seeds. A pass produced by that span is a
known failure mode, not a fit (`docs/covid/covid_theta_screen_v9_readout.md`
§3; open ledger §2, last bullet).

## 2. Current hypothesis

The Θ surface measured by THETA-SCREEN-V9 at `0fb186b` is structurally intact
on the repaired engine, and Θ is not the parameter that will produce onset mass
near 197: it moves the probability of takeoff, leaving an extinction-or-burn
dichotomy at every decade (v9 readout, `0fb186b`). The v10 canary supports this
at Θ 1e9 and nowhere else. If it holds across the other nine decades, the
criterion question — trajectory under T1 with import geometry as the next axis,
versus takeoff probability scored against covid.H3 with onsets conditional on
takeoff — is the real blocker, and it must be declared in a design file before
its cells run.

## 3. Evidence for

- **THETA-SCREEN-V10 canary** (`docs/ledger/THETA-SCREEN-V10.md`, measured at
  `a9b4f1f`, canary only; readout
  `docs/covid/covid_theta_screen_v10_readout.md`): Θ 1e9 × 20 seeds, 20/20
  children succeeded, takeoff 0.60 on the *same twelve seeds* as v9,
  conditional median attack rate 0.865 in both, `infections_total` within 2.1%
  on every takeoff seed and identical on all eight extinct seeds. The shared
  seed 20200205 reproduces the QUAR-ATTR-V2 `A0_declared` cell of record
  exactly (3458 / 0.9318).
- **THETA-SCREEN-V9** (`docs/ledger/THETA-SCREEN-V9.md`, measured at
  `0fb186b`): Θ moves takeoff probability 0 at ≤ 1e3 → 0.85 at 1e10, not
  conditional outbreak size (median onsets given takeoff 1,582–3,391 from 1e6
  up); no near-critical band in [1e1, 1e10] for one declared import; the sole
  T1 pass is an interval span with `onset_mass_near_target` 0.00.
- **QUAR-ATTR-V2** (`docs/ledger/QUAR-ATTR-V2.md`,
  `docs/covid/covid_quarantine_attribution_v2_readout.md`, measured at
  `d62f10d`): the reinfection inflation lived in the quarantine-window counts
  (973 → 43 during quarantine at the saturated seed), while distinct-host
  totals barely moved. The screen payload never carried window counts, which is
  why the canary's row is stable.

## 4. Evidence against / unexplained

- **Nine of ten decades are unmeasured on the repaired engine.** Θ 1e1–1e8 and
  1e10 still rest on `0fb186b`. Stability at one Θ — the most saturated one,
  where nearly every host is infected and small trajectory differences have
  nowhere to go — is the weakest possible place to test it. A move near the
  takeoff threshold (1e4–1e6) would be invisible here.
- **`covid.T3` flips fail → pass at Θ 1e9** purely because the p90 of campaign
  positives moves 628.5 → 646.9 across the 634 target with p10 still 0 (v10
  readout §3). Two anchors now "pass" on the same bimodal span. Nothing was
  selected on this, and it is a warning about the criterion, not evidence.
- **The episode-count gate could not be read.** The screen payload has no
  episode field, so "no cell reports an episode ≥ 2" — a pre-committed gate
  check — is unverifiable from these cells (it was verified on the
  QUAR-ATTR-V2 payload at `d62f10d`). Likewise the 3414–43–1 window split.
- **Per-seed onsets move up to −224** on saturated seeds with totals nearly
  unchanged, i.e. the recorded-onset channel is more sensitive than the truth
  channel at saturation. Not attributed; expected from any RNG-stream
  disruption (`.agents/skills/stochastic-attribution/SKILL.md`) and not treated
  as a finding.

## 5. PRs landed this session

- **(this PR)** THETA-SCREEN-V10 canary readout + surface/pairs CSVs, ledger
  entry `declared` → `measured` (canary only), open-ledger entry, this handoff,
  `tools/covid_theta_screen_csv.py` (surface JSON → v9-shaped CSV and paired
  v9/v10 seed table), and `--index-offset` on
  `deploy/aws/covid_boarding_screen_entrypoint.py`. Ledger entry:
  `THETA-SCREEN-V10`.

The v10 design declaration itself landed before this session (#639/#641,
`docs/ledger/THETA-SCREEN-V10.md` at `1da4211`).

## 6. Running jobs

**None.** Both canary jobs are terminal:

| what | job | detail |
|---|---|---|
| shared-seed child (index 160) | `6555b89d-f44f-420e-b607-41ebd239c1b9` | SUCCEEDED |
| canary array (indices 161–179) | `cf4865ef-2a4b-48ef-bf31-6830d062fd0c` | size 19, all SUCCEEDED |

- Queue `picard-campaign-queue`, job definition
  `picard-covid-boarding-screen:12`, account 994254241749, `us-east-1`,
  `AWS_PROFILE=picard`.
- Image `picard-campaign:theta-v10-a9b4f1f`,
  digest `sha256:325dde73ac57039dee318f451700fd1886fa3c35d60f880d060ea93146b4d3b1`
  (campaign base at `a9b4f1f` layered with `deploy/aws/Dockerfile.covid_hull`;
  the bare base image lacks `deploy/aws/`, which is why revision 11 — registered
  against it and never used — is dead. The role cannot deregister job
  definitions).
- Results: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v10/a9b4f1f/cells/`
  (20 cells). Nothing of value remains on the session VM.
- To run the rest: same job definition and prefix, 160 children at offsets
  0–159 and 20 at 180–199, via the new `--index-offset` (Batch overwrites a
  user-supplied `AWS_BATCH_JOB_ARRAY_INDEX`, so the offset must be a job
  parameter, not an env var). Expect ≤ 1 h wall clock on Spot, from
  QUAR-ATTR-V2's 240 children in ~30 min.

## 7. What is now void

Nothing new is void. The canary **confirms** rather than withdraws: the v9
Θ 1e9 row's takeoff fraction, conditional attack median and extinct-seed cells
hold on the repaired engine (open ledger §2, v10 bullet). The v9 rows at other
Θ keep their `0fb186b` status — valid at their own SHA, not re-measured —
exactly as the QUAR-EXEMPT-01 paragraph of open ledger §1 already states. The
one correction is bookkeeping: the v10 design file's gate text quotes v9's
Θ 1e9 takeoff as 0.85; the v9 surface CSV gives 0.60 at 1e9 and 0.85 at 1e10.

## 8. The single open decision

**Do the remaining 180 v10 cells run?**

- **Yes** (~1 h Spot, ~$ tens): converts §2's hypothesis into a measurement,
  lets each v9 verdict be formally superseded or confirmed per Θ, and covers
  the 1e4–1e6 takeoff-threshold region where the canary is blind. Recommended:
  the canary gives no reason to expect surprises, so this buys completeness of
  the record cheaply — and the record is what the criterion decision will be
  argued from.
- **No**: accept the v9 surface as the Θ locator on the strength of the 1e9 row
  and move straight to the criterion declaration, or to the QUAR-ATTR-V2
  follow-up (a crew-confinement SOP variant: the attribution showed confinement
  scope, not Θ, carries the quarantine-era counts).

Either way the *next* design file after that is the criterion declaration, and
it must exist before its cells run.

## 9. Do not reopen

- **Do not re-run QUAR-ATTR-V2.** Its attribution is settled at `d62f10d`.
- **Do not fit Θ, or any epidemiological constant, to T1/T3.** Θ 1e9 is not a
  fitted or selected value and may not be quoted as one
  (`.agents/skills/model-parameter-provenance/SKILL.md`).
- **Do not loosen or rewrite the frozen v9 admissibility block inside a running
  design.** A criterion change is a new design file, declared before cells run
  (`.agents/skills/campaign-preflight/SKILL.md`).
- **Do not re-add the infection-age axis** under a declared `onset_day`: the
  age cancels exactly in `engines/initiation.py::_apply_one_seed`, measured
  byte-identical over 200 triples (THETA-SCREEN-V9, `0fb186b`).
- **Do not treat the canary as a v10 surface**, and do not compare S3 cells
  against host runs: reproduction is byte-exact only inside the campaign image.
- The v9 `stage_1b_refinement` plan stays withdrawn.
