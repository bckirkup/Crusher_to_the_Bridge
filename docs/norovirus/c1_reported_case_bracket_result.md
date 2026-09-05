# C1 reported-case bracket: the ladder measured nothing

Status: measurement, 2026-09-05. Design:
`picard_framework/runs/mega_cruise_campaign/c1_reported_case_refit_v1_manifest.json`.
Raw artifacts: AWS Batch array `9c94a301-e958-49da-878c-1fd9e98edb57`, 80/80
children succeeded, 2,880/2,880 runs in the resume ledger, under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/c1_reported_case_refit_trackA_20260905/`.

Nothing here adopts a dose. The campaign was asked whether one common
`dose_adjustment` can put all four hull classes inside their class-binned VSP
passenger attack-rate IQRs at once. The answer it returned is that the ladder it
swept cannot answer the question, in either direction.

---

## 1. What the campaign ran

Four hulls (`expedition_cruise_450`, `classic_cruise_1900`,
`spirit_cruise_3000`, `mega_cruise_5000`) x nine `dose_adjustment` rungs
(12.0 to 14.0 in steps of 0.25) x two surveillance arms (`none_true`,
`syndromic`) x 40 seeds (760-799) x 168 epochs = 2,880 runs.

Collection succeeded completely: 80 shard zips and 80 manifests (~29.2 MB)
flattened by `deploy/aws/aggregate_results.py` into 2,880 rows x 105 columns,
1,440 per arm, 72 hull x dose x arm cells of 40 seeds each.

## 2. The ladder has no resolution anywhere on it

Every one of the nine rungs produced **bit-identical output at every seed it
shares with every other rung**, across all 47 `derived.*` and `summary.*`
columns. Measured by `picard_framework/analysis/sweep_degeneracy.py`:

```
python3 -m picard_framework.analysis.sweep_degeneracy c1_summary.csv \
    --axis parameters.dose_adjustment \
    --outputs derived.infection_attack_rate_passenger ... \
    --group parameters.platform_id --group parameters.surveillance \
    --replicate parameters.seed

rungs: 9
resolved fraction: 0.111
collapsed rungs: 12.0, 12.25, 12.5, 12.75, 13.0, 13.25, 13.5, 13.75, 14.0
```

A resolved fraction of 1/9 means the ladder is one design point sampled nine
times: 2,880 runs are 320 distinct runs, each replicated across the axis. The
axis is `-log10` of the grams of stool released to the environment per epoch, so
12.0-14.0 is 1-100 fg per epoch; the environmental term has already gone to zero
across the whole span, and the runs differ only in a quantity the model rounds
away.

This is not a null result about the dose. A bracket read off these cells —
whether it came out empty or non-empty — would be reporting the replication, not
the dose. Single-seed probes outside the ladder do move the model (seed 761:
infection attack rate 0.4177 at 4.0, 0.2278 at 6.0, 0.0791 at 8.0, 0.0854 flat
across 9.0-12.0), so the axis is live somewhere below 9; the campaign simply did
not sample there.

## 3. What the arms show, and what it is not evidence for

Cell medians over 40 seeds, passenger attack rates, with the pre-era class IQRs
the design intended to hit. These are reported as **description of a degenerate
design**, and are not a scored verdict:

| hull | arm | median infection AR | median reported AR | take-off cells | pre-era VSP passenger IQR |
|------|-----|--------------------|--------------------|----------------|---------------------------|
| expedition | `none_true` | 0.0586 | 0.0 (no reporting) | 225/360 | 0.0400-0.1045 |
| expedition | `syndromic` | 0.0063 | 0.0032 | 45/360 | 0.0400-0.1045 |
| classic | `none_true` | 0.0422 | 0.0 (no reporting) | 270/360 | 0.0415-0.0782 |
| classic | `syndromic` | 0.0019 | 0.0007 | 72/360 | 0.0415-0.0782 |
| spirit | `none_true` | 0.0143 | 0.0 (no reporting) | 234/360 | 0.0418-0.0724 |
| spirit | `syndromic` | 0.0010 | 0.0005 | 54/360 | 0.0418-0.0724 |
| mega | `none_true` | 0.0323 | 0.0 (no reporting) | 279/360 | 0.0355-0.0749 |
| mega | `syndromic` | 0.0004 | 0.0002 | 126/360 | 0.0355-0.0749 |

Two things are worth carrying forward as questions rather than findings.

The scored arm is `syndromic`, because the target is a *reported* rate and
`none_true` sets the sick-call hazard to zero by construction; its reported rate
is 0.0 in every cell and is undefined against A4 rather than failing it. In the
syndromic arm the reported medians sit 10-100x below every class IQR — but at a
dose the model cannot distinguish from any other dose on the ladder, so the gap
is not attributable to the dose.

The two arms also differ by 6-80x in *infection* attack rate at the same dose
and seed, which is response, not observation: the syndromic arm detects, isolates
and confines. Whatever ladder replaces this one has to separate the dose axis
from that response, or a dose will be credited with the isolation the arm
performs.

The IQRs above are conditional on VSP posting; posting incidence is a separate
quantity and is not a per-voyage rate
(`telemetry_buffer/observation_model/vsp_class_era_scoring.py`).

## 4. The artifacts are also unscorable by the standard scorer

`telemetry_buffer/observation_model/score_anchors.py` refused all 1,440
syndromic runs:

```
RuntimeError: ...c1_norovirus_classic_cruise_1900_dose12_init1_syndromic_s760/
summary.json missing parameters: sick_call_probability
```

The campaign's `none_true` override declares `sick_call_probability: 0.0`
explicitly, so those runs carry it. The syndromic arm overrides nothing, inherits
`syndromic.sick_call_probability_per_day: 0.70` from `crusher_labs/config.yaml`
at runtime, and recorded nothing — and whether a run reports at all decides which
anchors it can be scored against, so the scorer cannot assume the value. Both
sides are now fixed (the runner records the effective hazard for every arm; the
scorer reads either unit name), but the fix does not retroactively annotate these
2,880 summaries. They stay unscored, which costs nothing extra here because §2
already voids the design.

## 5. Status

- C1 as run is **withdrawn as a bracket**: no dose interval, empty or non-empty,
  may be quoted from it.
- The 2,880 runs remain valid as 320 distinct runs at one unresolved
  environmental-release setting, and as the evidence for §2.
- A replacement ladder must be sited where the axis resolves — checked with
  `sweep_degeneracy` on a short probe before the campaign is submitted, not
  after — and must hold the surveillance response fixed while the dose moves.
- The `#37` feasibility gate has no C1 input until that re-run exists. An empty
  admissible region remains an admissible outcome of it; a degenerate sweep is
  not one.
