# Sentinel wastewater operations scan (`sentinel_ww_ops_scan_v1`)

Campaign + analysis design for the shipboard wastewater operating envelope of
port-attributed sentinel surveillance: **which sampling cadence and holding-tank
residence time a ship must run before wastewater buys port-hazard recovery**.

| Item | Value |
|---|---|
| Design | `picard_framework/runs/mega_cruise_campaign/sentinel_ww_ops_scan_v1_design.json` |
| Manifest | `picard_framework/runs/mega_cruise_campaign/sentinel_ww_ops_scan_v1_manifest.json` |
| Runs | **4230** |
| Tiers | `sr_one_hot_fleet_crossed`, `sr_last_port_hot_fleet_crossed`, `sr_null_fleet_crossed` |
| Generator | `_iter_sentinel_recovery_runs` in `campaign_runner.py` (shared with `sentinel_synthetic_recovery_v1`) |
| Simulator layer | `picard_framework/analysis/sentinel/wastewater_ops.py` |
| S3 prefix | `campaign/sentinel_ww_ops_scan_v1/` |

## Why these two knobs

The v1 sentinel recovery left the clinical-only model structurally biased
(~18.5% port-hazard coverage, hazards underestimated ~100×). Wastewater is a
second observation of the *same* latent incidence curve — it never receives a
port label of its own (`docs/sentinel_surveillance_spec.md` §1.3) — so its value
is entirely in timing, and timing is exactly what the plumbing degrades:

- **Sampling cadence** sets the temporal resolution the fit can ever recover: a
  24-epoch composite gives 7 looks at a 7-day voyage.
- **Holding-tank residence** smears a port-call spike. The regime that decides
  the answer is residence ≈ the ~24 h inter-port interval, where adjacent calls
  stop being separable no matter how often a bottle is drawn.

So the two interact rather than add, and the scan is a grid over their product
rather than two one-at-a-time sweeps.

## Cells

`expand_design.build_wastewater_cells` turns the design's `wastewater_scan`
block into 34 cells, each with its own seed replication, and
`campaign_runner` merges each cell's `wastewater_surveillance` block into the
run's `config_overrides`:

| Block | Cells | Grid | Seeds | Runs |
|---|---|---|---|---|
| `core` | 25 | cadence {1,3,6,12,24} × residence {0.5,2,4,8,12} h, depth 250 K, 1 tap | 15 | 3375 |
| `depth` | 6 | depth {50 K, 250 K, 1 M} × residence {2, 8} h, cadence 6 | 10 | 540 |
| `collection` | 2 | {1, 3} taps at cadence 6 / residence 4 h | 10 | 180 |
| `control` | 1 | wastewater **off** — clinical-only baseline | 15 | 135 |
| | | | | **4230** |

Each block count is × 3 hazard profiles × 3 ships (`fleet_crossed`) at
`R_onboard = 1.0`, norovirus, standard Caribbean 7-day itinerary — i.e. v1's
hardest cases held fixed so only the operating point moves.

Run ids carry their cell, so a result zip is self-locating without the manifest:

```text
sr_norovirus_mega_cruise_5000_one_hot_fleet_crossed_standard_R1p0_core_f6_r4_s500
sr_norovirus_mega_cruise_5000_one_hot_fleet_crossed_standard_R1p0_depth_d1000000_r2_s500
sr_norovirus_mega_cruise_5000_one_hot_fleet_crossed_standard_R1p0_collection_p3_f6_r4_s500
sr_norovirus_mega_cruise_5000_one_hot_fleet_crossed_standard_R1p0_control_clinical_only_s500
```

`campaign_parameters` (and therefore the aggregate CSV) additionally carries
`wastewater_cell`, `wastewater_block`, `wastewater_enabled`,
`ww_sampling_interval_epochs`, `ww_residence_hours`, `ww_sequencing_depth` and
`ww_collection_points`. The clinical-only arm names no cadence or residence and
labels both as `0` rather than leaving holes in a factorial table.

## What the simulator actually does

`wastewater_ops.py` is the generator side of the channel
`wastewater_signal.py` fits:

- The tank is a **first-order lag** on aboard shedder prevalence,
  `tank <- w * tank + (1 - w) * inflow` with `w = exp(-epoch_hours / tau)`. It
  advances on every epoch, sampled or not, because the smearing is physical.
  `tau -> 0` is a direct line tap.
- Cadence gates *emission* only: `epoch >= 1 and epoch % interval == 0`.
- `sequencing_depth` is the library size (`total_reads`); reads are a
  beta-binomial draw, so depth buys precision with **saturating** returns once
  extraction/sampling dispersion dominates. Depth never moves the expected read
  fraction.
- Collection points split the platform's zones into contiguous blocks
  (`assign_collection_points`) and each emits its own row for the same
  `sample_epoch`. They are correlated replicates: `pool_wastewater` collapses
  one epoch's rows into a single trial with a capped effective depth, so three
  taps sharpen one epoch rather than tripling the evidence.
- Shedder prevalence, not shedding mass, is the inflow — the fit's link is on
  prevalence, and `pathogen_shedding_to_reads_scale` /
  `background_read_fraction` place it on the read-fraction scale metagenomics
  reports (a fully shedding ship tops out at `1 - background`, i.e. 1e-4).
- Draws come from a dedicated RNG stream (`seed + 977`), so enabling the channel
  cannot change the epidemic it observes.

Configuration block (`crusher_labs/config.yaml`, default **disabled**; distinct
from the onboard-detection `wastewater_sequencing` grid modality):

```yaml
wastewater_surveillance:
  enabled: false
  sampling_interval_epochs: 6
  holding_tank_residence_hours: 4.0
  collection_points: ["aft_main"]
  sequencing_depth: 250000
  pathogen_shedding_to_reads_scale: 1.0
  background_read_fraction: 0.9999
  pathogen: "norovirus"       # delay-catalog key written on every sample
  pathogen_id: "norwalk_gi"   # ABM profile whose infections are counted
```

Samples reach the fit through the sentinel line list
(`run.sentinel_line_list` → `wastewater_samples`, `schemas/sentinel_observations.schema.json`).
A run with the channel off still writes clinical cases and exposure totals, which
is what makes the 135-run control a usable baseline.

## Regenerate and validate

```bash
# manifest is generated, never authored
python3 -m picard_framework.runs.mega_cruise_campaign.expand_design \
  --design picard_framework/runs/mega_cruise_campaign/sentinel_ww_ops_scan_v1_design.json

# fail on drift (also asserted by tests/test_wastewater_ops_scan.py)
python3 -m picard_framework.runs.mega_cruise_campaign.expand_design \
  --design picard_framework/runs/mega_cruise_campaign/sentinel_ww_ops_scan_v1_design.json \
  --check

# cartesian count + generator agreement: expect 4230
python3 -m picard_framework.runs.mega_cruise_campaign.campaign_runner \
  --manifest picard_framework/runs/mega_cruise_campaign/sentinel_ww_ops_scan_v1_manifest.json \
  --dry-run

python3 -m pytest tests/test_wastewater_ops_scan.py -q
```

## Per-cell fitting

Fit each cell with the residence time it was sampled under — fitting every cell
with the delay catalog's fleet-wide default confounds the channel's value with a
misspecified kernel:

```bash
python3 -m picard_framework.analysis.stan.fit_sentinel_fleet <fleet_manifest.json> \
  --out results/ww_ops/core_f6_r4 \
  --wastewater --wastewater-residence-hours 4 \
  --wastewater-max-effective-reads 200000

# clinical-only baseline for the same cells
python3 -m picard_framework.analysis.stan.fit_sentinel_fleet <fleet_manifest.json> \
  --out results/ww_ops/control --no-wastewater
```

## Outcomes to report

1. Port-hazard 90% CI coverage heatmap over cadence × residence, one panel per
   hazard profile.
2. Last-port (`KYGEC`) coverage heatmap — the censored port is where wastewater
   should help most, since shedding continues after clinical onsets are cut off.
3. CI-width ratio versus the clinical-only control at each operating point, read
   against operating cost (samples × depth).
4. Per-channel `evidence_loglik`: where the channel adds information rather than
   noise.
5. Depth and collection-point sensitivity arms: whether either buys anything at
   the sweet spot the core grid finds.
6. Operational recommendation curve: minimum cadence for a target coverage as a
   function of residence time.

A null result is a result: if coverage stays low even at 1-epoch cadence with a
0.5 h tank, the scan bounds the value of shipboard WBE for port attribution
instead of recommending it.

See also: `docs/sentinel_surveillance_spec.md` (§1.3 channel semantics, §6
validation), `docs/synthetic_recovery_and_vsp_degradation.md` (sibling
campaigns), `.agents/skills/mega-cruise-campaign-local/SKILL.md`.
