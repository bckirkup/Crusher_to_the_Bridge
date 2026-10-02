# NORO-CHANNEL-03 design — the observation funnel under outbreak cells

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

NORO-OUTBREAK-01 measured (at `bc4de6f5`, 12,000 voyages) that every
scored anchor fails on the small hulls and that the deficit sits in the
infection -> illness -> report conversion, not transmission: A1 ever-ill
0.0-2.0% vs (10%, 22%), A2 ill/infected 6-17% vs (59%, 81%), A4 reported
AR ~0 vs class IQRs, while A8 acquisition incidence runs 2.4-9.5x above
its reference. Which link of that conversion carries the gap?

The instrument is `tools/noro_diag/observation_channel_funnel.py`
(NORO-CHANNEL-01/02's per-host funnel), which decomposes the chain into
rungs:

    infected (acquired, unseeded)
      -> symptomatic course drawn        <- the A2 link
      -> syndrome-eligible severity       <- eligibility, not hazard
      -> reported to the infirmary        <- the A4 link, split
           pre/post outbreak recognition
      -> lab-sampled -> lab-confirmed
      -> onset dated

plus the not-reported decomposition (never visible while symptomatic —
isolation/departure censoring — vs reporting hazard never fired) and
onset-dating fidelity. Same-voyage anchors are what CHANNEL-01/02 could
not read: their funnel ran the pooled default spec, so rung ratios
described the channel on quiet voyages, not on the outbreaks the
anchors score.

## Spec source — the outbreak cells themselves

The funnel consumes `generate_tier_runs(manifest, tier)` from
`picard_framework/runs/mega_cruise_campaign/noro_outbreak_01_manifest.json`
and runs each yielded spec verbatim through `ShipSimulation` with the
read-only `ChannelCapture` epoch observer attached (no RNG draws; the
run is identical to the map voyage at the same seed — deterministic
spec+seed, so each funnel voyage *is* the same voyage the anchor map
scored, and per-voyage join is exact, not statistical).

Per run the capture adds `peak_infected` (max concurrent `status ==
INFECTED` for `norwalk_gi`, the campaign `peak_prevalence` semantics)
and `took_off` (>= TAKEOFF_PEAK_PREVALENCE = 10). That is the one new
observer field; everything else is the instrument as shipped.

## Cells

Per hull, three cells at 12 d — the map's own cells, matched seeds:

| hull | tier | cells |
|---|---|---|
| expedition_cruise_450 | `fl_exp_12d_scr`, `fl_exp_12d_ren` | scr-mid (0.0325,0.0185), scr-hi (0.040,0.030), ren |
| classic_cruise_1900 | `fl_cls_12d_scr`, `fl_cls_12d_ren` | same three |
| spirit_cruise_3000 | `fl_spr_12d_scr`, `fl_spr_12d_ren` | same three |

scr-mid is the canonical license-mid cell; scr-hi is where the map's
postings concentrated (exp 12d posted only at scr-hi / ren); ren is the
shipped renewal mechanism, whose import illness-time mix differs from
the screening pool — a distinct censoring regime. 9 cells x 20 seeds =
180 runs:

- expedition: seeds 8000-8019
- classic: 8105-8124
- spirit: 8105-8124

At ~93-100% takeoff on scr-mid/scr-hi the ~20 seeds yield ~18-20
takeoff voyages per cell; pooled over ~200-800 acquired hosts each, the
rung ratios carry tight enough intervals to separate "conversion rung
near zero" from "conversion rung at half its anchor". ren cells take off
~2-13% (exp) / ~78% (cls), so ren reads are conditioned where realised,
stated as n per cell.

## Reading

Per cell: the rung table (counts + pax/crew split, ratios with per-seed
median/IQR) reported twice — all voyages, and takeoff-conditional — plus
the not-reported decomposition and dating-fidelity blocks. The link
attribution is pre-declared as:

- infected -> symptomatic course below ~0.6 while reporting works:
  the A2 mechanism (symptom-course draw / never_symptomatic) carries
  the gap;
- symptomatic -> eligible below ~0.7 while reporting works: the
  severity/AGE-eligibility wall;
- eligible -> reported below ~0.4 with hazard exposure present: the
  reporting hazard / trust scaling — the A4 link;
- eligible hosts absent while symptomatic (isolation, departure): the
  censoring path, with isolation-vs-departure split already recorded.

No rung is fitted; the decomposition attributes the measured gap to a
named link, and the constant under suspicion is stated as measured
versus declared, never selected on.

## Report-immediately triggers

- The infected -> symptomatic-course rung measures near zero on
  acquired hosts at takeoff — the anchor deficit would be symptom-course
  draw, contradicting the shipped never_symptomatic reading.
- Reported/eligible materially above ~0.6 on any cell — the channel
  would over-report at outbreak densities, a new defect direction.
- Any funnel run diverging from its map twin (takeoff flag disagrees
  with the map's took_off on the same seed) — the determinism premise
  fails and the join is void.

## Gates

1. This file committed with the manifest spirit tiers before any cell
   runs.
2. Local smoke: `generate_tier_runs` resolves the declared (tier, seed,
   match) into the spec whose `parameters` carry the cell axes, and the
   funnel writes the takeoff flag.
3. Canary >= 20 seeds on `fl_exp_12d_scr` scr-mid (the fastest hull),
   read out — then STOP and report; the full 180-run probe waits for
   the user's decision. The spirit map extension submits after its own
   canary on the same image.

## Artifacts

- instrument: `tools/noro_diag/observation_channel_funnel.py`
  (`--manifest`/`--tier`/`--seed`/`--match` mode; takeoff capture)
- entrypoint: `deploy/aws/noro_channel_03_entrypoint.py`
- manifest (spec source): `noro_outbreak_01_manifest.json`
- S3 prefix: `s3://<bucket>/campaign/noro_channel_03/`
- ledger: `docs/ledger/NORO-CHANNEL-03.md`

## Non-goals

- Re-eliciting or changing any channel constant (`eligibility`,
  `reporting_*`, `trust_medical`, severity table); this reads them.
- mega_cruise_5000.
- The import side (import pressure was settled by IMPORT-01/OUTBREAK-01).
