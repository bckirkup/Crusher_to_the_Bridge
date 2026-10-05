# Crew-window handoff — 2026-10-05

Status: handoff record. Reports no new numbers — every figure below is
quoted from the readout or ledger entry that measured it, with that
entry's `Measured at` SHA. Retires the "COVID DP Spread" session ahead
of the CREW-WINDOW-01 assessment campaign.

## 1. The question

On the verbatim `diamond_princess_2020` replay (3,711 aboard, SOP-017
days 16–30, infection_age 6.8, imports 1, `dwell_weighted`), at the two
clause-leg thetas {1e6, 7.9e6}: **which sourceable attenuation of the
during-quarantine working-crew channel lands the takeoff-conditional
median `infections_during_window` inside the record-informed band
[150, 350] while the before phase stays seed-paired unmoved?**

The mass is bracketed by two measured corners — the real world sits
strictly between them (crew kept working, but produced ~2–5× less
infection than the model's channel). Success = a CHANNEL-LANDED arm
per `picard_framework/runs/covid_crew_window_01_design.json`'s frozen
verdict grammar; the failure shapes (UNDER/OVER-ATTENUATED, UNMOVED)
each name a different next mechanism.

## 2. Current hypothesis

The during-window tail is the crew-exemption channel working an
unattenuated pooled mess bath onto the only population still mixing;
duty exclusion (sourced, VSP §4.4.1.1.1 — identified symptomatic crew
off duty) and a narrower essential-service exemption are the most
likely attenuations to land the band. If they land the median but not
the crew share (record 29%), the berth-ward compartment structure
(tranche 35) is the deeper suspect.

## 3. Evidence for

- D4 `covid_quar_suppression_v1` measured (`6ea3093d`, 80/80 cells):
  CONFINEMENT-CHANNEL — during-window medians D0 678/730 vs
  SOP017_ALLHANDS 27/105 (overshoots the band); during dated mass ~95%
  crew vs the record's 29%; crew_mess 54–58% of during acquisitions.
  Readout: `docs/covid/covid_quar_suppression_v1_readout.md`.
- Crew duty exclusion is already shipped, off by default:
  `engines/crew_duty_exclusion.py` implements VSP 2018 OM §4.4.1.1.1
  (tranche 33, Tr) — unconditional on escalation, identified-crew
  (`ever_reported_ids`) removal, release-to-work after 48 h food /
  24 h nonfood symptom-free + declared medical-clearance delay,
  `compliance_fraction` 1.0 declared as the enforced upper bound.
  Configured in `crusher_labs/config.yaml` at `enabled: false`.
- Berthing is class-level, not DP-unique: MLC 2006 caps passenger-ship
  crew rooms at 4; modern norm 2; the mega hull already declares
  `cabin_size: 2` on all 12 CC zones. Tranche 35's structural suspect is
  the corridor ward (~87 hosts/CC zone, cabin inert, roommate draws
  independent of work zone), not occupancy.
  `docs/literature/consensus_tranche_35_crew_berthing.md`.
- HOST-AGE-01 merged (PR #899): Ayoub decade susceptibility ladder +
  Wang presentation spline on `sars_cov2_resp`, profile-declared;
  detector cells repinned attributed.
- AGE-WITNESS-01 merged (PR #902): `infections_by_age_band`,
  `during_window_by_age_band`, `dated_onsets_by_age_band` on the cell
  payload — the NIID decade-curve shape witness.
- Local 2-seed armed-arm read (seeds 05/06 @7.9e6, uncommitted driver
  `telemetry_buffer/host_age_dp_read/run_cell_local.py`): infections
  849/938 in-band, during mass 630/795 still ~95–100% crew — age
  suppression defers acquisition into the window rather than preventing
  it under a saturated mess bath. Two seeds = hypothesis, not
  measurement; the in-design D0 row is the real drift witness.

## 4. Evidence against / unexplained

- The armed-age 2-seed preview did NOT dent the tail — if the D0 in-design
  row reads the same at n=20, the age term is a deferral-only witness on
  this replay and the believability budget sits entirely on channel
  attenuation.
- `ever_reported_ids` ascertainment gates CREWDUTY's bite: exclusion
  only removes crew the sick-call/infirmary path identified. If crew
  reporting is thin in replay, `excluded_hosts` ≈ 0 is a
  mechanism-didn't-fire witness, not a null — check the echo first.
- Seed-level before_share variance on the armed tree is wide
  (0.022–0.152 across two seeds): single-seed reads are uninformative.
- Berth-ward repair (tranche 35's compartment fix) is contact-graph
  restructuring — designed but not implemented; named follow-on only.

## 5. PRs landed this session (dependency order)

- #899 HOST-AGE-01: age-graded susceptibility + presentation on
  `sars_cov2_resp` (Ayoub ladder + Wang spline, register §3.2).
- #902 AGE-WITNESS-01: age-band tallies in the cell payload.
- #904 CREW-WINDOW-01 design doc (`docs/covid/covid_crew_window_01_design.md`).
- #906 CREW-WINDOW-01 implementation (open at closeout): `crew_duty_exclusion`
  arm key + echo block; `SOP-017-ENGMED`/`SOP-017-ESSENTIAL` protocols;
  `covid_crew_window_01_design.json` (240 cells = 2θ × 6 arms × 20 seeds);
  the design doc amended — SOP-018/`scheduled_protocol_add` superseded by
  the shipped `crew_duty_exclusion` block.

## 6. Running jobs

None. `telemetry_buffer/host_age_dp_read/cells_armed/` holds two local
cell payloads (seeds 05/06, pre-band + band formats) — untracked by
design, disposable once the in-design D0 row lands.

## 7. What is now void

Nothing withdrawn. D4's recorded rows stand at `6ea3093d` on the
pre-arm engine; the in-design D0_declared rows are the drift witness
against them under the armed tree (expected real movement: age ladder +
presentation spline reorder acquisition timing and onset recording).

## 8. The single open decision

Submit CREW-WINDOW-01 — yes/no, and which canary row. The
campaign-preflight gate is the same shape as D4's: thin overlay
Dockerfile at the current main generation, image + jobdef + manifest,
then ONE arm row (20 seeds) as the canary, read out and reported before
the 240-cell array. Recommended canary: CREWDUTY @Θ7.9e6 (the sourced
arm at the timing-leg theta — its `excluded_hosts` echo is also the
ascertainment-gate witness).

## 9. Do not reopen

- `SOP-017-ALLHANDS` is a historically-false counterfactual — never a
  score, never a candidate. Its corner is measured; it is not re-run.
- The [150,350] band is record-informed context for the verdict
  grammar, not a fit target; no constant is tuned to it or to the NIID
  decade curve (barred training set — shape witness only).
- `EXEMPT_*` subsets are non-scoring probes of the "essential service"
  wording, not replays of record — the shipped SOP-017 four-class
  exemption stays the declared configuration.
- `crew_duty_exclusion` durations (48 h/24 h) are the VSP-stated
  values; `compliance_fraction` 1.0 is the declared enforced upper
  bound, not a fit.
- DP replay contract is frozen: scenario_calendar SOP-017 days 16–30,
  infection_age 6.8, imports 1, seeds 20200205–20200224.
