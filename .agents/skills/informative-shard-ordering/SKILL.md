---
name: informative-shard-ordering
description: Order mega-cruise campaign runs by expected informativeness before sharding (--order informative) and stop a shard cleanly when its completed runs support a pre-declared unexpected trend (--stop-rule). Use when planning a campaign whose wall clock may be cut short, when a shard should abort on an out-of-band outbreak frequency, or when editing informative_ordering.py / stop_rule.py.
---

# Informative shard ordering and in-loop stopping

Companion to `.agents/skills/mega-cruise-campaign-local/SKILL.md` (how to run
the campaign) and `.agents/skills/campaign-results-analysis/SKILL.md` (what to
do with the shard zips afterwards). Code lives in
`picard_framework/runs/mega_cruise_campaign/informative_ordering.py` and
`picard_framework/runs/mega_cruise_campaign/stop_rule.py`; both are wired into
`campaign_execution.py` and reached through `campaign_runner.py`.

Both features are **opt-in**. With neither flag the runner behaves exactly as
before: manifest order, no stopping rule.

## Why

The manifest order walks each tier's cartesian product one axis at a time. A
shard that is killed at 30% of its budget has therefore finished 30% of the
*tiers* finely and the rest not at all. And a shard has no way to notice that
the campaign is producing something the design did not anticipate (every
norovirus rung ignites; no influenza rung ignites) until the analyst opens the
zips. This skill addresses both.

## 1. Informative ordering (`--order informative`)

```bash
RUNNER=picard_framework/runs/mega_cruise_campaign/campaign_runner.py

# See the order without running anything
python3 "$RUNNER" --tier t1 --dry-run --order informative

# Shard 2 of 7, informative order
python3 "$RUNNER" --tier t1 --order informative --shard-count 7 --shard-index 2
```

`order_runs_informative(all_runs)` is applied to the **complete flattened run
list** in `main()` before `shard_total` and the positional partition
`global_index % shard_count == shard_index` are computed. The rule:

1. Group runs into design points (every `campaign_parameters` coordinate
   except `seed` / `run_id`).
2. Emit in **waves**: wave 0 is one seed of every design point, wave 1 the
   second seed, ... No design point gets a replicate until all have a first.
3. Within a wave, visit design points in **van der Corput (bit-reversal)**
   order of their manifest index, so any prefix samples the whole grid
   coarsely rather than one end of one axis.

Nothing reads a result. The order is fixed by the run list alone.

### The invariant: ordering is shard-independent

The reordering must be a **pure function of the run list**. It must not look
at `--shard-index`, `--shard-count`, the clock, the resume log, or S3. Every
shard then computes the same global order, and the modulo partition over that
order stays complete and disjoint — the property
`tests/test_mega_cruise_campaign.py::test_shard_partitions_are_complete_and_disjoint`
and `test_dry_run_shard_counts_sum_to_total` guard. If you change the ordering
key, keep it a function of `(tier_id, run_id, spec)` triples only, and keep
`tests/test_informative_shard_ordering.py` green.

### Interaction with `--shard-count` / `--shard-index` / `--resume`

- **Every shard of a campaign must use the same `--order`.** Mixing
  `manifest` and `informative` across shards of the same `--shard-count`
  breaks completeness: two shards may both run a run_id and another run_id is
  run by none. Bake the flag into the Batch job definition, not per-child.
- `--resume` keys on `run_id`, not position, so resuming an `informative`
  campaign with `--order informative` skips exactly the completed runs. Resuming
  with a *different* `--order` is also safe for completeness (the union of
  done + remaining is still the full list) but the shard-level "same order"
  rule above still applies within one launch.
- `--limit N` now means "the N most informative assigned runs" rather than
  "the first N in manifest order", which is the point.

## 2. In-loop stopping rule (`--stop-rule EVENT:LOW:HIGH:MIN_N`)

```bash
# Stop this shard if the outbreak frequency leaves the expected 20-60% band,
# once at least 12 runs have been scored.
python3 "$RUNNER" --tier t1 --order informative \
  --shard-count 7 --shard-index 2 \
  --stop-rule outbreak_occurred:0.2:0.6:12

# Event with a threshold on a derived metric
python3 "$RUNNER" --tier t2 --stop-rule 'attack_rate>=0.3:0.05:0.4:20'
```

### Statistics

The rule is the Beta-Binomial posterior from
`telemetry_buffer/observation_model/staged_posting_readout.py`, applied to
completed runs instead of postings. `stop_rule.py` **imports** `JEFFREYS`,
`STOP_MASS`, `band_mass` and `decision` from that module rather than restating
them:

- prior Beta(1/2, 1/2) (Jeffreys);
- after `k` events in `n` scored runs, posterior mass below / inside / above
  `[LOW, HIGH]`;
- `stop_above` if mass above >= 0.95, `stop_below` if mass below >= 0.95,
  else `continue`;
- the rule cannot fire before `MIN_N` scored runs.

`EVENT` is a key of the run's `derived` block (see `compute_derived_metrics`
in `campaign_execution.py`): bare (`outbreak_occurred` — truthy is the event)
or with a comparator (`attack_rate>=0.3`, `peak_epoch<40`, `detection_epoch>200`).
Runs whose `derived` block lacks the metric are counted as *unscored* and do
not advance `n`.

### Pre-declaration discipline

The band and `MIN_N` are the **expected** frequency, written down before the
first run. A `stop_above` / `stop_below` means the shard's own data say the
event frequency is outside what the campaign was designed around with 95%
posterior mass — an *unexpected trend*. Per
`docs/proposals/defect_resolution_plan.md`: report the finding and the binding
metric; do **not** widen the band and relaunch. Any change to the spec is a new
campaign with its own register entry. Never derive the band from the shards
that are already running.

### What happens on a stop

`_campaign_gate` returns `stop` on the first assigned run after the rule fires,
`_execute_assigned_runs` breaks, and the normal end-of-shard path runs:

1. the completed-runs log is uploaded (`completed_runs.<shard>.txt`);
2. `ShardBundle.flush()` packs and uploads the shard zip + manifest;
3. `<shard>.stop_rule.json` is written to the output root and uploaded — the
   full verdict (spec, prior, `k/n`, posterior masses, decision, scored
   run_ids);
4. the process exits **0** unless a run actually failed.

The shard is fully resumable: `--resume` reads the same completed-runs log, and
the rule is **re-armed from the bundle's existing entries** on start, so a
resumed shard whose rule already fired stops again immediately (exit 0) rather
than running past the verdict. To continue past a fired rule deliberately,
relaunch without `--stop-rule` (and record why).

Each shard evaluates only **its own** completed runs. A stop on shard 2 does not
stop shard 3; read every `*.stop_rule.json` when aggregating.

### Interpreting `<shard>.stop_rule.json`

```json
{
  "spec": "outbreak_occurred:0.2:0.6:12",
  "band": [0.2, 0.6], "min_n": 12, "stop_mass": 0.95,
  "prior": {"family": "beta", "a": 0.5, "b": 0.5},
  "scored_runs": 14, "events": 13, "unscored_runs": 0,
  "posterior": {"below": 0.0001, "inside": 0.0140, "above": 0.9859, "mean": 0.9},
  "decision": "stop_above",
  "scored_run_ids": ["t1_norovirus_s42", "..."]
}
```

`decision: continue` with `scored_runs >= min_n` means the shard ran to
completion (or hit `--limit`) with the frequency inside the band. `posterior:
null` means nothing was scorable — check that `EVENT` names a real derived key.

## Tests

```bash
python3 -m pytest tests/test_informative_shard_ordering.py \
  tests/test_mega_cruise_campaign.py tests/test_campaign_boundaries.py \
  tests/test_staged_posting_readout.py -v --tb=short
```
