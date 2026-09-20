# NORO-REINFECT-IMPACT-01
**Date:** 2026-09-19
**Commit:** d62f10d
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** e83aa06

`REINFECT-01` (PR #636, merged at `d62f10d`) repaired a generic natural-history
defect: a host whose infection cleared with no strain registry configured wrote
no immune memory and returned to the fully susceptible pool. This entry asks
one question and stops: **does that repair change any norovirus conclusion, and
is `NORO-EMESIS-SIZE-01` still current?** It changes no constant, profile,
engine path or test, and runs no new cell — every number below is read from the
committed pre-repair dumps of `NORO-EMESIS-SIZE-01`.

## Why norovirus is in scope at all

`variant_surveillance` is off for these runs, so before the repair
`TransmissionCore.strain_configs` was populated only when a strain registry
existed, and `_challenge_protection` reduced to the legacy `agent.immune` flag.
The repair changes both sides:

1. `TransmissionCore.__init__` now builds a `StrainEvolutionConfig` for **every
   profile that declares one**, registry or not.
2. `_challenge_protection` now takes the maximum of the legacy flag and the new
   `_unlabeled_resolution_protection`, which reads `immune_waning` for each
   infection-origin `ImmuneRecord`.
3. `advance_infections` writes that record — `record_unlabeled_clearance_immunity`
   — when the last resident lineage clears with nothing tracked.

`norwalk_gi` declares `strain_evolution.immune_waning` with
`refractory_days = 56.0` and `refractory_protection = 1.0`, against a 288-epoch
(12-day) voyage. So a norovirus host that clears **aboard** is now fully
protected for the remainder of any voyage of this length: the change is live for
this pathogen, not dormant.

## Measured size, from the committed pre-repair dumps

Read from `docs/norovirus/noro_emesis_size_01/classic_cruise_1900/`, the 20
cells measured at `e83aa06`, using the instrument's per-host `exit_reasons`:

| quantity | value |
| --- | --- |
| hosts ever resident with `norwalk_gi` (87 imports + 3 secondaries) | 90 |
| of those, hosts with non-resident challenge epochs | 46 |
| of those, hosts that carried dose while non-resident | 22 |
| Σ evaluated hazard on those 22 hosts' non-resident epochs | **1.2527e-5** |
| Σ evaluated hazard over the block | 3.0046 |
| share of the block's hazard newly blocked by the repair | **4.2e-6** |

The 22 hosts are imports, so their dose-bearing non-resident epochs follow
clearance; the 3 secondaries are excluded because for them the evaluated epochs
precede acquisition, not follow it. That exclusion is the only ordering
assumption in the table, and it is safe: all three acquisitions are witnessed at
epochs 5, 6 and 31, far short of the 15-day `shedding_duration_days` at which
any of them could have cleared, so **no observed secondary is a reinfection.**

## What this means for the standing conclusions

- **Nothing is withdrawn.** The repair removes 4.2e-6 of the block's hazard —
  six orders of magnitude below the effect `NORO-EMESIS-SIZE-01` reports, and
  far below the between-seed spread of 45 decades in credited dose.
  `NORO-EMESIS-SIZE-01`'s 3 secondaries against Σ hazard 3.0046, its 6/20
  emesis incidence and its 1.16 log10 bolus→hands loss all stand.
- **`NORO-DOSE-01` and `NORO-SUSCEPT-03` are unaffected** beyond the withdrawal
  `NORO-EMESIS-SIZE-01` already recorded. Their voyages are the same length and
  their hosts clear no earlier.
- **α is untouched.** The repair moves no `dose_response` term.

## The one consequence that does bite: the block is not bit-comparable

`_resolve_pathogen_challenge` returns at `protection >= 1.0` **before**
`self.rng.random()`. Every challenge the repair now blocks is a draw the engine
no longer consumes, so the shared stream shifts for any seed containing a
cleared, dose-bearing host — 22 hosts across 10 of the 20 seeds. This is the
`RNG-FRAILTY-STREAM-01` failure mode arriving from a different direction: the
diff is not in the dose-response terms, but it still reorders draws.

Consequently **re-running seeds 8000–8019 on current `main` will not reproduce
the committed per-seed values**, and a difference from the table in
`NORO-EMESIS-SIZE-01` is not evidence of anything. Those numbers are pinned to
pre-repair `main` at `e83aa06`. Any future paired contrast on this hull must be
re-baselined at a commit at or after `d62f10d`, with both arms on the same side
of the repair.

## Where the repair *would* matter to norovirus

Not on this hull at this length, but three cases are live and unmeasured:

1. Voyages longer than the 15-day `shedding_duration_days`, where clearance and
   re-exposure both fall inside the run.
2. Multi-voyage or fleet-level runs where a host carries immune history across
   cruises.
3. Any arm that shortens `shedding_duration_days` inside its screened [12, 30]
   band, which moves clearance inside a 12-day voyage.

None of them is opened here.

## Non-goals

No new cell was run, no constant or engine path changed, and neither α nor β was
touched. The re-measurement of the 8105/8106-based claims, `NORO-EMESIS-SHARE-01`,
`NORO-PATCH-SATURATION-01`, `NORO-HAND-STATIONARY-01`, `NORO-SURFACE-CONSUME-01`,
`NORO-CARRIER-REDEPOSIT-01` and `NORO-TRANSFER-PRODUCT-01` all remain filed and
unstarted. A post-repair replay of the 20-seed block is **not** required to keep
`NORO-EMESIS-SIZE-01` current; it is only required if a bit-level comparison
against current `main` is ever wanted.
