# NORO-CHANNEL-04 design — observation-funnel re-measurement under the caregiver stack

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

NORO-CHANNEL-03 (measured at `d6c51c14`, 180 voyages over 9 cells) found
the conversion gap **shared**: infected -> symptomatic-course
0.170-0.413 against the declared 0.6 on all 9 cells, and
eligible -> reported 0.168-0.321 against the declared 0.4 on 8 of 9,
with symptomatic -> eligible intact at ~1.0. NORO-CAREGIVER-01 (merged
at `a78c942e`, default-ON) ships one mechanism aimed at both links: the
cleanup event is among the highest-dose exposures the engine can
express, feeding the dose-conditional symptom-course draw, and the
`caregiver_report_due_epoch` stamp routes the discovered case past the
self-report hazard. Does the funnel move on the same scored-voyage
harness — and if it does, on which channel (dose vs discovery)?

## Instrument delta over CHANNEL-03

Same harness: `tools/noro_diag/observation_channel_funnel.py --manifest`
runs each spec verbatim from
`generate_tier_runs(noro_outbreak_01_manifest.json, tier)` through
`ShipSimulation` with the read-only `ChannelCapture` epoch observer.
The capture now also collects (still read-only — it draws nothing, so
the voyage the spec would run is unchanged):

- `caregiver_report_ids` per epoch from the syndromic result, and the
  stamped hosts seen on the `caregiver_report_due_epoch` agent field;
- `rungs.reported_infirmary.via_caregiver` — the reported rung split by
  discovery channel;
- each infection record's `acquired_particles_by_route` -> dominant
  route, so the caregiver route's share of aboard transmissions is a
  count, not an estimate;
- the engine's `caregiver_telemetry` counters per dump (responses,
  steward responses, dose delivered/credited, reports).

The campaign measures the caregiver stack *as fixed* — this change also
carries the NORO-CAREGIVER-02 serialization fix
(`_copy_optional_agent_fields` dropped `caregiver_report_due_epoch`,
leaving the syndromic caregiver branch unreachable at `a78c942e`;
without it the discovery channel contributes nothing and the
re-measurement would read only the dose half).

The readout (`tools/noro_diag/channel_03_readout.py`) gains two columns
— `viaCG` (share of the reported rung attributed to the caregiver
stamp) and `CGtx` (caregiver share of aboard-acquired transmissions) —
and evaluates the frozen triggers below.

## Cells — identical to CHANNEL-03

Per hull, three cells at 12 d — the map's own cells, matched seeds:

| hull | tier | match tokens (cells) |
|---|---|---|
| expedition_cruise_450 | `fl_exp_12d_scr`, `fl_exp_12d_ren` | `rung-shipped,bp32p5c18p5` (scr-mid), `rung-shipped,bp40c30` (scr-hi), `rung-reportable` (ren) |
| classic_cruise_1900 | `fl_cls_12d_scr`, `fl_cls_12d_ren` | same three |
| spirit_cruise_3000 | `fl_spr_12d_scr`, `fl_spr_12d_ren` | same three |

9 cells x 20 seeds = 180 runs: expedition 8000-8019, classic and spirit
8105-8124 — the identical seed sets CHANNEL-03 paired with the map.

## Baseline pairing — fresh prefix, not overwrite

CHANNEL-03's 180 dumps under `campaign/noro_channel_03/` are the
labelled pre-caregiver baseline (bitwise-reproducible via
`transmission.caregiver.mode: off`). This campaign writes a **fresh**
prefix `campaign/noro_channel_04/` under the same
`<tier>/<matchtag>/..._seed<S>.json.gz` key scheme, so every new dump
pairs with exactly one baseline dump at the same spec+seed and
divergence between them is the mechanism's treatment effect. No mode:off
re-run: the baseline exists; re-measuring it burns array budget for
zero information.

## Determinism/join caveat — reframed

CHANNEL-03's determinism premise (same spec+seed => the funnel voyage IS
its scored map twin) does not carry: `assign_parties` draws no RNG, but
the mechanism changes event draws, so the new-stack voyage is the same
spec, not the same voyage. A `took_off` disagreement against the
OUTBREAK-01 map is therefore a measured change in outbreak frequency —
a treatment effect — not a join violation. The readout still runs the
join and reports the disagreement count per cell as a mechanism-effect
witness; it no longer voids attribution. (The paired baseline for the
rungs is the CHANNEL-03 prefix, not the map.)

## Reading

Per cell: the CHANNEL-03 rung table plus the caregiver columns, pooled
all-voyages and takeoff-conditional; then the paired table against the
baseline prefix — per-rung deltas, the via-caregiver share of reports,
caregiver share of transmissions, stamped hosts, stamped-not-reported,
and the engine counters.

## Admissibility / report-immediately triggers (frozen)

- Caregiver share of aboard transmissions > 10% on any pooled cell —
  the contact composition over-delivers; report immediately.
- Any caregiver report on a non-emetic course
  (`reports_on_nonemetic_course` non-empty) — the stamp fired outside
  an emesis course; report immediately.
- Voyages with vomiting courses but zero caregiver+steward responses,
  counted per cell — the responder pool is empty where it should not
  be; report the count.
- `reported/eligible` materially above ~0.6 on any cell — the channel
  over-reports at outbreak density (carried from CHANNEL-03).
- Infected -> symptomatic-course near zero on acquired hosts at
  takeoff — contradicts the shipped never_symptomatic reading
  (carried from CHANNEL-03).

Success looks like the two broken links rising toward their declared
thresholds with the lift visibly channel-attributed (viaCG for the
report link, the dose side for the course draw). Failure looks like a
flat funnel — the mechanism inert at campaign scale — or the over-
delivery trigger firing.

## Gates

1. This file and the ledger declaration committed before any cell runs.
2. Local smoke: `generate_tier_runs` resolves each declared
   (tier, seed, match) to exactly one spec, and one funnel voyage
   writes a dump carrying the caregiver block end-to-end.
3. Canary >= 20 seeds on `fl_exp_12d_scr` scr-mid on the merged-SHA
   image, read out and reported. (This session's prompt pre-authorizes
   the remaining 8 cells on canary pass; the canary verdict is still
   reported before the arrays submit.)
4. Jobdef digest-pinned to a fresh image built at the merge SHA of this
   declaration (`picard-campaign:noro-channel-04-<sha>`).

## Artifacts

- instrument: `tools/noro_diag/observation_channel_funnel.py`
  (caregiver-attribution capture)
- readout: `tools/noro_diag/channel_03_readout.py` (split + triggers)
- entrypoint: `deploy/aws/noro_channel_03_entrypoint.py` (unchanged)
- image: `deploy/aws/Dockerfile.noro_channel_04`
- jobdef: `deploy/aws/batch_job_definition_noro_channel_04.json`
  (`picard-noro-channel-04`)
- submit: `deploy/aws/submit_channel_04.sh`
- S3 prefix: `s3://<bucket>/campaign/noro_channel_04/`
- ledger: `docs/ledger/NORO-CHANNEL-04.md`

## Non-goals

- The anchor re-score (an OUTBREAK-01-scale rerun under the new stack) —
  the next decision after this readout, not part of it.
- mega_cruise_5000.
- Re-eliciting or changing any constant, including the five caregiver
  constants (frozen intervals + grades, register §3.1).
