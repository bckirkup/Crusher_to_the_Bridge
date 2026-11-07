# NORO-PROVISIONED-SENSITIVITY-01 — design of record

Paper-1 sensitivity screen (Edison ask; Devin-designed, Edison
reviews). **Question:** does the NORO-PROVISIONED-VENUE-02
role-specific-reporting / venue-placement result depend materially on
five uncertain inputs? Answered by a 2^(5-1) Resolution-V half-fraction
on the venue02 spec, seed-paired with venue02, read out through the
1.5.0 emitter (cumulative role checkpoints days 3/7/10/12, PR #1156).
Devin delivers raw per-cell counts; **Edison owns the factorial /
effect analysis, including aliasing and sparse-event uncertainty.**

Builder: `design/build.py` (every field declared there; this file
explains them). Generated artefacts: the manifest
`picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json`,
`campaign.json` (+ `../provisioned_sensitivity_01_mega/campaign.json`),
`SEED_MANIFEST.json`, `PROFILE_TABLE.md`.

## §1 Factors and levels (frozen by the plan of record — do not re-derive)

| factor | parameter | (-) | (+) | where it rides |
|---|---|---|---|---|
| A | `provisioned_source.q_source` (per station-voyage) | 0.00086 | 0.0047 | tier `config_overrides` (sourced interval, PR #1155 / tranche 55) |
| B | boarding passenger prevalence (screening_prevalence mode) | 0.025 | 0.040 | tier `boarding_prevalence_points` |
| C | boarding crew prevalence | 0.007 | 0.030 | tier `boarding_prevalence_points` |
| D | `norwalk_gi.illness_duration.draw` | `point` | `empirical_survival` (Harris IID2 table) | tier `pathogen_overrides` |
| E | `norwalk_gi.route_efficiency_multipliers`, joint scale on the five nonzero keys | ×0.5 | ×2.0 | tier `pathogen_overrides` |

Baseline route dict (profile): direct_contact 0.35, droplet 0.1,
hvac_airborne 0.05, fomite 0.3, food_contamination 0.2,
environmental_source 0.0. `environmental_source` is written explicitly
at 0.0 in both levels so the loaded dict is complete. venue02 ran at
q_source 0.003, prevalence 0.0325/0.0185, D = `point` (see §5), E = ×1.

## §2 Half-fraction

Generator **E = ABCD** (defining relation I = ABCDE, Resolution V):
no main effect is aliased with any two-factor interaction and no
two-factor interaction with another. Rows p01–p16 are the 2^4 full
factorial on A..D in standard order with E as the sign product. The
committed table is `PROFILE_TABLE.md` (also embedded in
`SEED_MANIFEST.json` → `design.profiles`); `build.py` asserts nothing,
the balance check (every factor 8/8, every pair 4 per sign
combination, every triple and quadruple balanced, ABCDE = +1 on every
row) was run on build and Edison re-audits on delivery.

## §3 Cells and replication

192 cells = 16 profiles × 4 hulls × 3 venue arms. Per-hull replication
`n` (seeds per cell), proposed from precision needs against venue02's
measured per-hull wall clock (mega ≈ 28 min/run at 1 vCPU, small hulls
minutes), with 12k as the order of magnitude, not a cap:

| hull | platform | agents | n / cell | scout / cell | main runs | scout runs | reserve seeds |
|---|---|---|---|---|---|---|---|
| exp | expedition_cruise_450 | 450 | 96 | 8 | 4,608 | 384 | 8096–8097 |
| cls | classic_cruise_1900 | 1,910 | 64 | 8 | 3,072 | 384 | 8169–8170 |
| spr | spirit_cruise_3000 | 3,000 | 48 | 8 | 2,304 | 384 | 8153–8154 |
| meg | mega_cruise_5000 | 7,000 | 24 | 8 | 1,152 | 384 | 8129–8130 |
| **total** | | | | | **11,136** | **1,536** | |

The scout (first 8 seeds of every cell) is nested in the main set: the
`scout_<tier>` blocks run first, the `<tier>` blocks carry seeds 9..n.
Per-hull `n` is revisited **only** on the scout's measured cost before
the main submit (recorded in LEDGER.md); the manifest tier seed list
already carries `n + reserve`, so a change in `n` is a `build.py` edit
and a `--dry-run` recount, nothing else.

Reserve: 2 ascending seeds per hull beyond the prefix (= 96 retry slots
per hull across its 48 cells). Used only by a hand-added retry block
recorded in LEDGER.md for a seed that failed/truncated; a cell still
short after the reserve is **published as missing**, never reseeded.
No automatic top-ups.

## §4 Venue arms, seeds, pairing

Arms and per-hull pins/weights are verbatim from venue02
`SEED_MANIFEST.json`: `crew_venue` (crew-mess pins), `passenger_venue`
(largest passenger dining room), `mixed_venue` (every served dining
venue, `station_zone_pin_weights` = seat capacity). Seeds are the
ascending prefix of venue02's blocks (exp 8000–8999; cls/spr/meg
8105–9104), so every (hull, profile, arm) cell pairs seed-for-seed with
the venue02 arm of the same hull and pin and with every other profile
on that hull. Baseline control = Child A's paired-seed emitter-active
replays of the venue02 baselines (reference only; one spot-check seed
at most here).

## §5 Machinery — what had to change and what was measured

Pattern: `campaigns/noro/provisioned_venue_02/` (generic worker
`tools/noro_diag/growth_chain_census.py`, `deploy/aws/campaign_entrypoint.py`,
`scripts/campaign`). Two campaign-runner seams were added for this
family (no engine or observation-model change):

1. **Tier-level `pathogen_overrides`** — `tier_iterators.tier_pathogen_overrides`
   deep-merges `tier.pathogen_overrides[pid]` over the manifest's
   `pathogen_configs.<pathogen>.overrides`, so one manifest carries 192
   tiers at different D/E coordinates.
2. **D override order (Edison's flag, confirmed in code).**
   `boarding_axis.IndexCaseAxis.pathogen_overrides` wrote the rung's
   `illness_duration_draw` *over* the tier patch (`{**base, **fields}`),
   so under the `shipped` rung any requested `empirical_survival` was
   silently replaced by `point`. **Consequence for pairing: venue02 ran
   at D = `point`**, so D(-) is the paired baseline level.
   `boarding_axis.tier_illness_duration_draw` now lets a tier-declared
   draw win over the rung, and the stamped `illness_duration_draw`
   factor follows the effective value (tests:
   `tests/test_boarding_axis.py::test_tier_declared_illness_draw_wins_over_the_rung`,
   `tests/test_tier_iterators.py::test_tier_pathogen_overrides_deep_merge_over_manifest_base`).

Loaded-value verification (measured, local, repo HEAD 76a44890 + this
branch): `generate_tier_runs` → `apply_pathogen_overrides` resolves, for
p16 (all +): draw `empirical_survival` with the 11-row survival table,
routes {0.7, 0.2, 0.1, 0.6, 0.4, 0.0}, q_source 0.0047, pin
[MainDining, CasualDining, CrewMess] weights [300, 150, 60], initiation
prevalence 0.04/0.03; for p01 (A–D −, E +): draw `point`, same ×2 routes,
q_source 0.00086, prevalence 0.025/0.007; for meg p09 (D +, E −): draw
`empirical_survival`, routes {0.175, 0.05, 0.025, 0.15, 0.1, 0.0}.
Local smoke (exp, seed 8000, 288 epochs, ~1m40 wall each) wrote the
venue02 zip layout (`summary.json` 0.42 MB, `growth_census.json.gz`
9.7 MB, `rss_samples.json`) with `role_checkpoints` schema 1.0 present
(days 3/7/10/12, epoch mapping 71/167/239/287) and `parameters`
stamping `illness_duration_draw`, both prevalences, `q_source`, pin,
`source_venue_arm`. The paired D-probe (same p01 cell, seed 8000, draw
flipped) is recorded in LEDGER.md.

Note for the audit: `summary.json` records the *stamped* factor labels
and the resolved initiation block; the route dict and the duration draw
the engine loads are resolved from the manifest tier + profile, which
is why the profile table and the manifest are both committed.

## §6 Held fixed (= venue02)

288 epochs, hours clock; `shipped` rung (boarding mode
`screening_prevalence`, age draw `engine_window`, symptomatic and
preboarding streams off); never_symptomatic 0.29; dose_adjustment 7.57
(void pending refit, per the norovirus open ledger — a fixed coordinate
here, not a claim); `syndromic_comp65` observation model (cascade off,
compliance 0.65 / 0.54 / 0.34); FOOD-01/02 transmission + hvac block;
shipped agent-class mix. Worker, zip layout and `first_paper_scalar`
contract unchanged except for the 1.5.0 additive columns.

## §7 Gates (campaign-preflight) and frozen admissibility criteria

Order: local smoke → `--dry-run` count = design (manifest 11,520 =
11,136 main + 384 reserve; `scripts/campaign list` 288 blocks / 9,984
cells small hulls, 96 blocks / 1,152 cells mega) → design PR merged →
image `picard-campaign:noro-provisioned-sensitivity01` built FROM the
post-merge SHA, digest pinned in LEDGER.md and passed to every jobdef →
manifest mirrored to S3 → **scout wave (1,536 runs) → STOP and report
measured operational evidence** (archive sizes, bytes read vs returned,
request counts, reducer time/memory, projected full-run cost, start
count) → user gates the main remainder → reducer materialize/return on
`first_paper_scalar/1.5.0` (`reducer-dispatch-pins` before any
dispatch) → Edison ingest + ack → run report under
`docs/campaign_reduction/`.

Admissibility, frozen before any cell runs:

- A run is admissible iff its zip has `summary.json` with
  `role_checkpoints.enabled = true` and all four days `available`,
  `parameters.engine_git_sha` = the pinned SHA, and
  `parameters.illness_duration_draw`, `boarding_*_prevalence`,
  `common_source.provisioned_source.q_source` / `station_zone_pin` /
  `source_venue_arm` equal the cell's design values.
- A cell is complete iff all `n` main seeds are admissible; a cell with
  a reserve-filled seed is complete-with-retry (recorded); a cell short
  after the reserve is published missing.
- Scout gate: fail → stop if any hull's measured mean wall or archive
  size projects the full run past the ~$60–80 simulation estimate, if a
  pin label is absent from a hull census (`actual_venues_used` ⊄ pin),
  or if any loaded value differs from the design.

## §8 Non-goals / report immediately

No factorial analysis, no COVID/flu arms, no census extraction, no
observation-model or engine change, no automatic top-ups. Report
immediately: loaded-config diffs from requested (D order, route dict
completeness, pin/weight presence per hull); scout cost past estimate
or reserve; a pin label absent from a hull census.
