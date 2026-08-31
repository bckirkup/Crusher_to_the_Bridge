# Phylodynamic observables (Paper 3, PR 13)

> **Status:** Implemented

What a Paper 3 run can be asked, once lineages are heritable and sequencing is
imperfect: how much diversity was aboard, how fast a new genotype was seen, and
how much a surveillance channel actually knew about the mixture it sampled.

Every observable is reported per **physical hour**, never per epoch. The epoch
was the unit that hid a 24x timing error (`../history/epoch_time_unit_audit.md`), and
an axis labelled "epochs" hides it again.

## The two inputs

| channel | file | written when |
|---|---|---|
| truth | `lineage_census.json` | `run.lineage_census` is set; the campaign runner arms it for any run with `variant_surveillance.enabled` |
| observation | `sentinel_line_list.json` | `run.sentinel_line_list` is set; the campaign runner arms it for shore-exposure runs (the importation fit) **and** for `variant_surveillance.enabled` runs, because the observed half of every observable below lives there |

The census is a separate artifact rather than a slice of the simulation
history: a `compact` campaign run never persists epoch records, so at campaign
scale the observed lineages had nothing to be scored against. It carries its own
clock (`epoch_duration_hours`, `natural_history_clock`), because a phylodynamic
observable is a rate per hour and the reader must not assume the arm.

An arm with no bundle is analysable — every genotype is simply censored, which
is the correct reading of a run that sequenced nothing.

## Per-run report

```bash
python3 -m picard_framework.analysis.phylodynamics RUN_DIR_OR_ZIP --out analysis/
```

| artifact | contents |
|---|---|
| `lineage_diversity.csv` | per pathogen-epoch: richness, Shannon bits, effective lineages, dominant fraction, cumulative lineages, turnover, mean generation, mean mutations, recombinant fraction |
| `genotype_detection.csv` | per genotype: emergence hour, clinical and wastewater detection hours, lags, censoring |
| `information_gain_clinical.csv`, `information_gain_wastewater.csv` | per epoch: truth vs observed genotype composition, Jensen-Shannon distance, bits gained over a genotype-blind guess, completeness |
| `phylodynamic_summary.json` | arm labels, per-channel and per-pathogen summaries, detection-speed curve |
| `*_hours.png` | diversity, dominance, detection speed, detection lag, information gain — all on a `voyage hours (physical)` axis, titled with the clock arm |

Definitions worth stating once:

- **Effective lineages** is `exp(H)`, so four even lineages read as four and a
  99:1 pair reads as ~1: a rare variant is not a resolvable one.
- **Turnover** is Bray-Curtis dissimilarity between consecutive epochs, bounded
  in `[0, 1]`, so a lineage sweep is 1 and a growing clone is 0.
- **Detection speed** at hour *h* is the share of genotypes that had *emerged
  by h* and been seen by then. Genotypes that did not exist yet are out of the
  denominator, so the curve is not dragged down by the future.
- **Wastewater detection** is dated at collection **plus turnaround**: a library
  is evidence when it comes back.
- **The join key is the profile id, not the assay label.** A wastewater row
  carries both: `pathogen` is the delay-catalog key the Sentinel fit filters on
  (`norovirus`), and `pathogen_id` is the ABM profile the census is keyed on
  (`norwalk_gi`). Those are deliberately different vocabularies, so the
  truth-versus-observed join reads `pathogen_id`, falling back to `pathogen`
  only for bundles written before the id was carried. Joining on the label
  alone censors every genotype the sequencer actually typed and reports a flat
  0 bits gained.
- **Information gain** is the KL divergence of truth from a uniform genotype
  prior minus that from the reported composition, in bits, under Jeffreys
  smoothing over the union of genotypes. A silent channel scores exactly 0 (it
  is the uniform baseline); a confidently wrong channel scores negative, which
  is a real outcome and is reported as one.

## Campaign level

`campaign_bundle` writes `phylodynamic_runs.csv` (one row per pathogen per
armed run) and `phylodynamic_arms.json` (means **within** each arm) whenever the
campaign contains armed runs; unarmed runs are counted, not raised on.

An arm is `(natural_history_clock, incubation_arm, epoch_duration_hours)`, with
the incubation arm recovered from the PR 12 run id tag (`_dist_`, `_fixed_`).
Nothing is averaged across arms: pooling an hourly run with a
`legacy_epoch_day` one would average two data-generating processes, which is
what the PR 12 run-id labels exist to prevent.

## Not in this layer

Absolute case counts and detection times still ride on the `c1_*`
`dose_adjustment` refit under the hourly clock. Ratio-style observables
(detection lag *differences* between channels, diversity turnover, bits gained)
difference two arms carrying the same clock and are quotable before it.
