> **Status:** Handoff record (2026-11-22). Reports no new numbers — every
> figure is quoted from the ledger entry or readout that measured it,
> with that entry's `Measured at` SHA.

# Noro hand/fomite mechanism stage — handoff

Session `devin-d2314b841ac24a6a92da365571c2c9ee` retiring at a campaign-stage
close per `.agents/skills/session-handoff-ledger`.

## 1. The question

Norovirus takes off far too slowly on the hulls: onboard records show
interpersonal propagation beyond a food burst, but the model produces
substantial food-associated acquisition while typical non-food
propagation stays small. Edison's framing: distinguish (a) attenuation
along the hand pathway (deposit → pickup → retention → loss → transfer
→ delivered dose), (b) spatial averaging of fomite contamination across
large high-touch regions, and (c) missing activity/event structure that
makes contact and contamination patchy and dense. Success = a measured
verdict naming the binding stage; failure = another magnitude lever
that cannot ignite cold cells.

## 2. Current hypothesis

The deficit is **upstream of delivery entirely — in encounter/activity
structure**. The zone pool holds mass and every delivery mechanism that
exists works when asked, but ordinary high-touch encounters *request*
almost nothing. Ignition today happens only where an emesis event lands
a concentrated patch in an occupied unit. The next design lives in who
touches what, how often, and whether contact and contamination are
co-located — likely a patch-style mechanism for ordinary fomite plus
event scheduling that creates genuinely dense encounters (bearing in
mind §4's sign reversal).

## 3. Evidence for

- **NORO-DOSE-LEDGER-01** (`docs/ledger/NORO-DOSE-LEDGER-01.md`,
  measured, PR [#1394](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1394)):
  22 frozen `classic_cruise_1900` cells, 288 epochs, joined per-epoch
  mass ledger. Zone pool is a write-only reservoir under `continuous`
  (~0.3% of delivered mass); 99.7% of delivered is emesis-patch; ~4% of
  delivered reaches a mouth; hand→hand negligible. Hot cells ignite on
  `common_source_food` bursts; secondaries ≈ Σhazard.
- **NORO-POOL-PICKUP-01** (`docs/ledger/NORO-POOL-PICKUP-01.md`,
  measured, all 22 cells at `5a1bb0cd`): discrete solver arm —
  requested 79.85M GEC, offered 2.15B, delivered 79.66M (~100% fill of
  requests), still ~99.9% emesis-patch. B ≈ A on cold cells → per the
  frozen rule, deficit is upstream of pickup.
- **Mechanism review + optimistic upper bound** (this session, memo
  `noro_hand_fomite_mechanism_review_2026_11_22.md` — NOT committed;
  its content is superseded by the ledger entries above): magnitude
  levers top out ~3–5×; structural ignition is the only route to the
  ~35× AR gap vs the Explorer target.
- **NORO-HAND-RESERVOIR-01** (prior ledger): occupancy `partial`,
  18.9% vs Liu's 25.4% — emission gated on a mostly-empty reservoir.

## 4. Evidence against / unexplained

- **D3′ rhythm re-read** (`docs/ledger/NORO-RHYTHM-REREAD-01.md`,
  commit `5007b3a4`, PR
  [#1398](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1398)): on the 8-day mega reconstruction the 4 seeds
  igniting in both arms show rhythm-on *reducing* onboard acquisitions
  148.0 → 113.5 (−23.3%, sign-test p = 0.125). Scheduling may damp
  rather than amplify — the encounter-density explanation is unverified;
  confirmatory A/B recommended, not yet funded.
- **D1′ carrier-hop comparison blocked** (`docs/ledger/` blocker
  record, PR [#1395](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1395)):
  carrier-redeposition arm bypasses the recorder's discrete deposit
  path under the freeze; a real comparison needs an engine change to
  donor eligibility. Whether that change is worth it is the user's call.
- **RNG-stream divergence caveat**: seed 8105 realized its emesis
  patch under `continuous` (del 1.17M, haz 1.098) but not `discrete`
  (del 51k, haz 0.01). Solver choice perturbs the RNG stream, so
  per-seed arm contrasts are not paired realizations — pooled readouts
  are the unit of evidence.
- Unresolved from the review: `sanitary_visit_mode: none` means the
  shared-head venue carries zero fomite exposure; `per_surface`
  representation silently flips the solver to `discrete` (arm C was
  declined on that coupling plus a weak prior).

## 5. PRs landed this session

- [#1392](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1392)
  — joined per-epoch mass-ledger witness in
  `tools/noro_diag/per_host_dose_challenge.py` + `noro_dose_ledger_01`
  campaign spec. Merged.
- [#1394](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1394)
  — D0′ readout: `docs/ledger/NORO-DOSE-LEDGER-01.md` measured on 22
  cells + D2′ design. Merged.
- [#1395](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1395)
  — D1′ blocker record (child session
  `454b9750b8624ea78ba9daaa526db9a9`). Merged.
- [#1397](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1397)
  — `--contamination-solver` worker knob, `noro_pool_pickup_01`
  campaign spec, D2′ measured readout, this handoff. Open at handoff.
- [#1398](https://github.com/bckirkup/Crusher_to_the_Bridge/pull/1398)
  — D3′ ledger `NORO-RHYTHM-REREAD-01` at `5007b3a4` (child
  `3ec803fb0fde432f813df15087e20802`). Open at handoff.

## 6. Running jobs

None. All Batch work terminal: `noro_dose_ledger_01` array (22 cells)
SUCCEEDED; `noro_pool_pickup_01` discrete canary (20) + remainder
array `e2d63e9e-2963-4345-9384-2274afd8d376` (2 cells) SUCCEEDED.
Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_ledger_01/classic_cruise_1900/`
and `.../noro_pool_pickup_01/classic_cruise_1900_discrete/`; local
copies `/home/ubuntu/noro_dose_ledger_01_canary/` and
`/home/ubuntu/noro_pool_pickup_01_canary/discrete/` (ephemeral with the
VM — S3 is canonical). Arm-C block `classic_cruise_1900_per_surface`
was never submitted.

## 7. What is now void

- The 12-day mega archive's `ignited` flag: can be true at zero onboard
  acquisitions — its published 126/127 flag counts cannot establish
  propagation (recorded in NORO-RHYTHM-REREAD-01; rescored on
  acquisition counts).
- The earlier "≤2-case schedule on/off" mega comparison: it used mean
  cumulative *reported* cases over all seeds and is superseded by the
  conditioned re-read.
- The `high_touch_area_scale` sweep framing of D2′ is dead by
  measurement: pool delivery is ~0 under `continuous`, and per-touch
  pickup under `discrete` does not move it — no area or solver
  representation corner was worth sweeping.
- Open-ledger §1: no new withdrawals from this session beyond the
  above; every pre-existing dose figure remains void pending refit as
  already recorded there.

## 8. The single open decision

**Commission the encounter/activity-layer diagnostic or not.** Options,
ranked: (a) design a patch-style co-location mechanism for ordinary
fomite + touch encounters (the stage D0′+D2′ converged on); (b) fund
the D3′ confirmatory rhythm A/B first, since a −23% scheduling-damper
result would change what the activity layer must do; (c) fund the D1′
engine change (carrier donor eligibility) to test multi-hop hand
transfer. Settling evidence: for (a), a declared design with frozen
criteria on the same 22 cells showing cold-cell encounters can be made
dense enough to request/deliver ignition mass without touching
constants; for (b), a paired A/B on the 8-day reconstruction with a
pre-registered take-off gate.

## 9. Do not reopen

- No epidemiological constant may be tuned to an anchor
  (`model-parameter-provenance`); the hand-transfer factors were
  already measured at literature magnitude (NORO-TRANSFER-PRODUCT-01).
- No pool-side delivery repair under `continuous` or representation
  change to `per_surface`: measured not-binding (NORO-POOL-PICKUP-01).
- No Explorer schedule on/off comparisons without an attached event
  programme (vacuous on `explorer_seas_06`).
- Per-seed arm contrasts under different solvers are not paired
  realizations (RNG divergence) — report pooled.
- Campaign images must build from `deploy/aws/Dockerfile.campaign`
  (ENTRYPOINT `python3`); the root Dockerfile's `campaign_runner`
  ENTRYPOINT eats jobdef argv.
