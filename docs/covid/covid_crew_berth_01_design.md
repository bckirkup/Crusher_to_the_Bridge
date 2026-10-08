# CREW-BERTH-01 design — crew berthing cohorts and work-shift pods under the confinement order

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

CREW-MESS-01 landed the crew-dining intervention: `sect_mess_boxed`
(boxed crew meals, section stewards, `contact_factor_to_host`
U(0.005,0.02), direction `both`) measured during-window crew share
**0.727** vs the record's 0.29 — the mess channel moved the share but
the residual rides elsewhere (`docs/covid/covid_crew_mess_01_readout.md`
once landed; the boxed row is this campaign's declared base).

Berth attribution on the boxed arm
(`tools/covid_berth_attribution.py`, merged at PR #957) decomposes the
remaining ~400 during-window crew acquisitions across three boxed
reruns:

- **Occupational (~73%):** galley 117, crew-mess posted staff 65,
  other exempt work zones 64 — working crew acquiring at their posts.
- **Corridor transit:** 47 (working crew moving through shared
  corridors).
- **Cabin/berth:** 107 — of which 74 confined-in-berth: 35 carry-home
  (berth mate infected during-window, carried to a confined mate), 8
  pre-window infected mate, 31 corridor-pool (no infected mate — the
  pooled cabin-block channels: shared stateroom air/fomite at corridor
  level).

The physical claim under test: on Diamond Princess, essential crew kept
working under the order but the response also re-organized how the crew
lived — status-matched berthing and split watches are the two readable
interventions that reach the berth block and the work-zone block without
touching the meal channel. **Where do status-separated crew berthing
(cabins never mixing confined and working crew) and split-shift
essential-service pods put the crew share — and can the family's
ceiling reach the declared (0.2, 0.4) band at all?**

The arithmetic is declared now: the berth-only arm caps at ~18.5% of
crew events (74 confined-in-berth of ~400); the occupational block is
~73%; a maximal combined arm may land ~0.45–0.55 — short of the band.
Partial verdicts are expected and are findings: the campaign measures
the ceiling, not just a landing.

## Placement mechanics (verified on the merged tree)

- Cabins are pairs inside `(home_zone, berth_group)` pools
  (`orchestrator_init.assign_cabin_mates`, `cabin_size` 2 on `CC_*`
  crew corridors); `cabin_mate_ids` gates the cabin direct-contact and
  cabin-air routes; the compartment key is
  `"{zone}|{min(cabin_mate_ids ∪ {self})}"`
  (`transmission_core._cabin_compartment_key`).
- `register_cabin_berths` reads the roster once at init into
  `_cabin_berths`/`_block_berths` (stateroom air shares, occupancy
  denominators) — a re-call rebuilds it verbatim from the current
  roster, and every consumer computes compartment keys live from
  `home_zone` + `cabin_mate_ids`.
- Epoch order: `_step_protocols` (modifier application) runs **before**
  `_step_record → step_quarantine_confinement`, so a rising-edge
  mechanism cannot read the realized `quarantined_ids` of that epoch.
  The partition therefore reads the order's **declared** exempt set:
  `role == "crew"` ∩ `exempt_classes` ∩ `exempt_work_zones` — the
  postings the order keeps working, deterministic from merged
  modifiers.
- Schedules are 24 hourly tokens; `Work → work_zone`,
  `Meal:* → dining_zone`, `Sleep → home_zone` (rhythm share draw), and
  **any unrecognized token resolves to `home_zone` with no draw**
  (`get_location_for_hour` tail; `rhythm_layer.location_for` returns
  `None` for non-Sleep/non-Meal tokens). Placement re-reads
  `home_zone` live every epoch, so a re-homed agent follows its new
  berth from the next placement on.
- The steward/delivery pool is `role == "crew"` ∩
  `_responder_available` (aboard, unconfined) — **not** schedule-gated,
  so splitting work shifts cannot starve the service channel, and
  confined hosts' `service_deliveries` are structurally unaffected by
  anything here.
- `MEAL-SVC-01`'s section partition (`_build_service_sections`) is
  built lazily at the first section delivery — after any rising-edge
  re-deal — so steward sections key on post-re-deal compartments
  automatically.

## Mechanism (frozen)

Two new protocol-modifier keys carried on SOP-017-family variants,
merged like every other modifier and applied in `_step_protocols`
beside `apply_crew_meal_service` — invoked ahead of the early-return so
the falling edge always clears. **Both mechanisms are fully
deterministic — they draw nothing on any RNG stream** (the
dedicated-stream rule is satisfied vacuously; off/baseline arms stay
bit-identical, and the pre-window phase stays bit-paired seed-for-seed
across the ladder).

### `crew_berthing`

`{"mode": "cohort" | "rezone", "berth_zones": [...]}` — declared on the
order, in force exactly while the order is in force.

At the rising edge:

1. The **working set** is every crew agent with `agent_class ∈
   exempt_classes` and `work_zone ∈ exempt_work_zones` of the merged
   modifiers (`exempt_work_zones` absent → `exempt_classes` alone).
   All other crew are **confined** for the partition.
2. `rezone` only — **berth swap:** working crew homed outside
   `berth_zones` re-home into `berth_zones`, dealt round-robin by
   ascending `agent_id`; confined crew homed inside `berth_zones`
   re-home out to the vacated berths in the other crew corridors
   (the zones crew are actually homed in, minus `berth_zones`), dealt
   round-robin by ascending `agent_id`. Physically: the declared deck
   block becomes essential-crew berthing; its non-essential occupants
   swap into the bunks the essential crew vacated.
3. **Status-pure re-deal**, `cohort` and `rezone` alike: every affected
   `(zone, berth_group)` crew pool re-deals cabins partitioned by the
   working/confined split — no cabin mixes the two statuses.
   *Anchor preservation:* each pre-existing cabin's minimum-id member
   that stays in the pool keeps its stateroom (the compartment key —
   `zone|min(members)` — survives, so the room's accumulated
   compartment pools stay filed under it); same-status free members
   deal to same-status anchors preferring `partner_id > anchor_id`
   (key-preserving); leftover free members pair among themselves into
   new staterooms by ascending id; unmatched anchors hold single
   occupancy. Non-cabin `home_zone`s and non-crew pools are untouched.

At the falling edge the original `home_zone` + `cabin_mate_ids` are
restored verbatim and the berth registry is rebuilt (the
`_saved_crew_schedules` restore precedent).

Witness: `crew_window.crew_berthing` echoes `{mode, berth_zones,
applied_epoch, restored_epoch, working_count, confined_count,
pools_redealt, cabins_formed, single_occupancy, keys_preserved,
relocated_to_work_zones, relocated_out}` — `keys_preserved` counts
compartment keys that survived the re-deal, `relocated_*` are rezone
moves (0 on cohort).

### `crew_work_cohorts`

`{"mode": "shift_split", "pods": P, "zones": [...]}` — `zones` absent →
the order's merged `exempt_work_zones` (the essential-service roster by
posting).

Rising-edge schedule surgery on crew whose `work_zone ∈ zones` —
`pod = agent_id % P`: each contiguous `Work` block splits into `P`
consecutive turns; the agent keeps `Work` only inside its pod's turn;
the other positions become `"Rest"` — an unrecognized token that
resolves to `home_zone` deterministically (off-watch under
`on_watch`, day-rate under the sanitary-visit bookkeeping, draws
nothing). Schedules restore verbatim at the falling edge. Physically:
P non-overlapping watches per essential venue — simultaneous posted
occupancy divides by P — with off-watch essential crew holding in
quarters (the boxed-meal state), not in public space.

Witness: `crew_window.crew_work_cohorts` echoes `{mode, pods, zones,
applied_epoch, restored_epoch, agents_split, work_hours_removed}`.

## Arm semantics (fixed here before cells run)

All arms ride the verbatim CW-02 replay contract and the landed
MEAL-SVC-02 + MESSBOX config: `scheduled_protocol_id` swaps of the
SOP-017 slot plus `transmission_overrides.caregiver.service`
`{direction: both, service_responder_mode: "section",
service_section_cabins: [10, 15], contact_factor_to_host: [0.005,
0.02]}`. Each new protocol is verbatim SOP-017-MESSBOX (unreachable
`scenario_calendar` trigger, identical confinement + exempt modifiers +
`crew_meal_service {mode: boxed}`) plus its berthing/cohort modifier:

| arm_id | protocol | modifiers |
|---|---|---|
| `shipped_baseline` | SOP-017 | shipped default verbatim — no zone narrowing, messes open, uniform stewards; the arm grammar's required empty-override first arm + widest crew-share corner |
| `mess_boxed_base` | SOP-017-MESSBOX | boxed meals only — the sect_mess_boxed corner verbatim; pairing base + drift witness |
| `berth_cohort` | SOP-017-BERTHCOH | boxed + `crew_berthing {mode: cohort}` |
| `berth_rezone` | SOP-017-BERTHRZ | boxed + `crew_berthing {mode: rezone, berth_zones: [CC_D4_F, CC_D4_M, CC_D4_A]}` |
| `work_pods` | SOP-017-PODSHFT | boxed + `crew_work_cohorts {mode: shift_split, pods: 2}` |
| `combined` | SOP-017-BERTHPODS | boxed + `crew_berthing {mode: rezone, berth_zones: […D4…]}` + `crew_work_cohorts {mode: shift_split, pods: 2}` |

`berth_rezone` subsumes `berth_cohort` (the re-deal runs in every
affected pool, so cabins are status-pure ship-wide either way); the
combined arm is therefore rezone + pods, the family ceiling.

6 arms × 20 seeds = **120** declared cells. `mess_boxed_base` is the
pairing base and the drift witness against the CREW-MESS-01 boxed
canary row (same arm definition, same seeds — NOT expected
bit-identical across intervening merges; the pre-window mass and the
confined-pax band are the binding comparisons).

## Replay contract (verbatim CW-02)

`diamond_princess_2020`, `voyage_mode: declared`, SOP-017 days 16–30,
`infection_age_days` 6.8, `imports` 1, `sanitary_visit_mode`
`dwell_weighted`, seeds 20200205–20200224 (the matched 20-seed set),
`takeoff_recorded_onsets` 10, `seed_ring_readout` true, Θ7.9e6 only.

## Scoring surface (frozen)

- **Primary:** during-window crew share vs the record's 0.29 — target
  band declared **(0.2, 0.4)** verbatim.
- **Guard:** confined-pax during-window mass in the landed band
  ([26,160] context; boxed-row median ~28) within seed-paired noise —
  the mechanisms touch crew only, so a passenger-side move is a
  shared-zone defect, not a finding.
- **Cadence parity:** `service_deliveries` per cell within 15% of the
  landed row's ~162k — berthing/cohort arms must not move the steward
  channel (structurally protected, verified: the responder pool is not
  schedule-gated).
- **Drift witnesses:** before-phase mass and `takeoff_recorded_onsets`
  on `mess_boxed_base` reproduce the CREW-MESS-01 boxed row's class —
  the mechanisms are order-window-only, so a pre-window move is an
  environment change, not an arm effect.
- **Mechanism witnesses:** `crew_berthing`/`crew_work_cohorts` echoes
  populated on armed cells; cross-status cabin pairs == 0 on armed
  cells (checked at rising edge + falling edge restore); `restored_
  epoch` set at the window close.
- **During-window total** reported beside [150,350] — not gating.

## Verdict grammar (frozen)

- **BERTH-CHANNEL-CLOSED** — `combined` lands crew share inside
  (0.2, 0.4) with the guards holding: the family's ceiling reaches the
  band; the decomposition (cohort vs rezone vs pods) is the follow-up.
- **CEILING-SHORT** — `combined` moves measurably but lands > 0.4:
  the berthing+occupational family is exhausted and a residual channel
  remains (a new mechanism class is the next question, not more cells).
- **OVER-CLOSED** — `combined` < 0.2: the family over-corrects;
  the weaker arms bracket where the truth lands.
- **UNMOVED** — `combined` within seed-paired noise of
  `mess_boxed_base`: the mechanism never reached the venue (audit the
  echoes first).
- **PAX-COLLATERAL** — confined-pax mass departs the landed band
  beyond seed-paired noise: a shared-zone defect; report immediately.
- **DRIFT** — `mess_boxed_base` departs the CREW-MESS-01 boxed row's
  class beyond seed-paired noise: the merged environment shifted under
  the arms; rerun the base before reading anything else.

## Audit invariants (halt the readout on failure)

- `quarantine_witness` echoes on every cell: window [16,30], activated;
  `exempt_classes` the shipped four; `exempt_work_zones` echoes the
  11-zone list on every SOP-017-family arm and is absent on
  `shipped_baseline` (SOP-017 narrows no zones).
- `crew_window.crew_berthing` echoes on every berthing arm
  (`applied_epoch`/`restored_epoch` set — the rising and falling edges
  both fire inside the 32-day voyage; `relocated_*` == 0 on cohort,
  > 0 on rezone/combined); absent or mismatched echo halts the readout.
- `crew_window.crew_work_cohorts` echoes on `work_pods`/`combined`
  (`applied_epoch`/`restored_epoch` set, `agents_split` ==
  realized exempt-set size, `work_hours_removed` > 0); absent halts.
- `mixed_status_cabins` == 0 on every berthing arm (cohort and
  rezone alike); a mixed cabin on an armed arm is a mechanism defect.
- `index_onset_day == -1.0`; `index_shedding_at_day0` true.
- Droplet split echo (0.175, 0.0) on every cell.
- Deliveries parity vs the landed row (~162k ±15%).
- `diner_redirects > 0` on every SOP-017-family cell (boxed rides
  every armed arm); `shipped_baseline` carries no meal-service
  directive (messes open).
- `mess_boxed_base` reproduces the CREW-MESS-01 boxed row's
  qualitative behaviour (crew share ~0.73 class, confined-pax band)
  or the run reports DRIFT.

## Report immediately if

- The mechanism cannot be expressed without consuming voyage RNG
  (frozen: it draws nothing — if implementation forces a draw, stop).
- `mess_boxed_base` departs the boxed row's behaviour on the current
  merge (drift) — stop and report before any array.
- PAX-COLLATERAL — berthing moved the passenger side (the mechanisms
  read and write crew state only; a passenger move is a defect).
- Confined-pax guard or deliveries parity breaks on the canary.
- The canary lands crew share inside (0.2, 0.4) — near-landing; stop
  and report before any further cells.
- The berth-attribution decomposition fails to reproduce on the
  canary seeds.
- Child failure rate > 5%.

## Execution (frozen)

AWS Batch via `campaigns/covid/crew_berth_01/` through
`scripts/campaign`: 5 blocks × 20 seeds; jobdefs
`picard-covid-crew-berth-01` (+ `-fargate` fallback), image
`covid-crew-berth-01` pinned by digest built at the implementation SHA,
S3 prefix `campaign/covid_crew_berth_01/`, queue `picard-analysis-queue`
(Fargate fallback `picard-analysis-fargate-queue`), 1 vCPU / 2048 MB
per cell.

Preflight per `campaign-preflight`: this file + the design JSON frozen
before any cell runs; local smoke on a window-retimed probe
(`scheduled_protocol_window` → days 2–3, `--num-epochs` capped) proving
the modifiers reach the engine (armed cell echoes both directives;
re-deal fires; cross-status pairs 0; off/baseline bit-identical;
voyage-RNG ordering unchanged on unarmed cells); `--dry-run` count =
100; pinned image digest + jobdef revision recorded; manifest in S3;
canary **`combined`** @Θ7.9e6 (20 seeds) read out and reported — STOP
after the canary; the full grid is the owner's call.

Canary pick (the brief's recommendation, recorded): **`combined`** —
the family ceiling. If the ceiling cannot reach the band the weaker
arms are moot; if it lands inside, the decomposition runs next; if it
over-corrects, the ladder brackets. Cheapest falsification first.

## Non-goals

- No fitting to the 0.29 record share: modes and parameters are
  declared interventions with physical rationales, not tuned values
  (pods=2, berth_zones=the D4 block are declared geometry, not fits).
- No physical-parameter changes anywhere — if reaching the band would
  require one, that is the finding; escalate, do not tune.
- No changes to the exempt set, the exempt lottery, the service
  channel, or the meal-service mechanism (all settled).
- The four unsubmitted CREW-MESS-01 blocks stay untouched — this
  campaign submits its own `combined` canary block only.
- The noro confined-host pickup-eligibility question is a separate
  seam — not picked up here.
- Engine defaults unchanged: every modifier lives on a protocol that
  activates only when a scenario schedule names it — shipped voyages
  that don't schedule these SOPs are untouched (default-ON semantics
  satisfied: the mechanism ships live, armed by the schedule).

## Rejected alternatives

- **Partition on realized `quarantined_ids` at the rising edge** —
  impossible on the epoch order (`_step_protocols` precedes
  `step_quarantine_confinement`); the declared exempt set is the
  readable partition and is deterministic.
- **RNG-shuffled re-deal** — a shuffled deal consumes a dedicated
  digest stream for no physical benefit; the deterministic anchor rule
  is more faithful (the roommate is re-berthed; the room keeps its
  staying occupant and its pool history).
- **Partition passengers too** — passengers are all confined under the
  order; a status-pure split is vacuous.
- **Re-deal without anchor preservation** — orphans pre-window
  compartment-pool mass under dead keys and understates the residual
  in-cabin hazard; anchors keep each room's history attached to the
  occupant who stayed.
- **Rezone into empty corridors** — the hull has none; the
  berth-for-berth swap is the honest expression.
- **`"Sleep"` as the off-shift pod token** — `Sleep` resolves through
  the rhythm share draw to `free_zone` in day hours (the awake
  minority leaks to public space) and burns a rhythm draw; `"Rest"`
  resolves `home_zone` unconditionally and draws nothing.
- **Pods as work-zone re-posting** (spread galley staff over the
  three kitchens) — changes venue identity and tangles the posted-zone
  witness; shift-split is the cleaner first read.
- **A 5-arm full-grid submission up front** — the canary answers the
  ceiling question on 20 cells; the ladder's remaining 80 cells wait
  on the verdict.
