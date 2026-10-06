# Crew-window handoff — 2026-10-06

Status: handoff record. Reports no new numbers — every figure below is
quoted from the readout or ledger entry that measured it, with that
entry's `Measured at` SHA. Retires the CREW-WINDOW-02 session at the
close of the campaign.

## 1. The question

Same bracket as CW-01 — verbatim `diamond_princess_2020` replay,
{Θ1e6, Θ7.9e6}: **does the crew-duty channel have an interior — can a
fractional or activity-scoped confinement of `crew_general` land the
during-window median inside the record-informed band [150, 350] with
the before phase seed-paired unmoved and crew share moving toward the
record's 0.29?** CW-01 measured only the corners (exempt ~740 ↔
confined ~70) because the hull instantiates one crew class; CW-02
opened the interior with `exempt_work_zones` (posted-zone essential
lists) and `exempt_fraction` (sticky headcount draws).

## 2. Current hypothesis

The cliff was the class vocabulary, not the channel — measured: the
channel has an interior, and ~25–31% of crew working brackets the
band. The residual open question moved: the mass lands, but the
during-window attribution stays ~0.97 crew (record 0.29) because
confined crew are fed by R3 steward delivery and residual infections
stay crew-on-crew — a structural feature of the confinement
configuration, not a defect of the arms.

## 3. Evidence for

- CW-02 measured (`2df542ff`, 240/240 cells, 0 child failures,
  image `picard-campaign@sha256:2b481866`): FRAC_25 → 301 and
  ZONE_NARROW → 334 @7.9e6, CHANNEL-LANDED (band + before unmoved);
  monotone in realized exempt share at both thetas (7.9e6: 0.242→301,
  0.307→336, 0.482→487, 0.540→504, 0.722→632, 0.964→739). Readout:
  `docs/covid/covid_crew_window_02_readout.md`; ledger:
  `docs/ledger/CREW-WINDOW-02.md`.
- Realized shares track declarations: FRAC drawn counts exactly
  261/523/784/cell on a dedicated RNG stream (before mass Δ0.0 confirms
  no stream reordering); ZONE realized 0.31/0.54 vs posted-conditioned
  lottery 0.32/0.56; all working crew inside the essential lists.
- `service_deliveries` 128k–166k/cell on every arm — R3 steward cabin
  delivery does not starve under any confining arm.
- CW-01 D0 drift witness pairs seed-for-seed at median delta 0.0 on
  both thetas — the replay is bit-stable at `2df542ff` vs `ea9550ef`.

## 4. Evidence against / unexplained

- Crew share moves only marginally on the landing arms (0.973/0.978 vs
  D0 0.992). The mass lands without resolving the attribution; if the
  record's 0.29 is to be reached at all, the suspect is the confined-
  crew service structure (steward contact, cabin adjacency) or a
  passenger-side channel, not further crew confinement.
- At Θ1e6 crew share is 1.000 on every row including D0 — the low-theta
  surface cannot discriminate the share clause at all.
- **OPEN ITEM (unruled):** the frozen `realized_exempt_share ≈1` D0
  invariant flagged 4 seeds (0.68–0.87; worst 20200208 @7.9e6 = 0.678,
  a 2,252-before-infection seed). Attribution: symptomatic crew already
  confined through the isolation path when the order fires — D0
  exempts from the order's gate, not from isolation. Whether the ≈1
  expectation was ever physical on big before-phase seeds is the
  owner's call; recorded flagged in the readout, not amended.

## 5. PRs landed this session (dependency order)

- #927: CW-02 implementation + frozen design — `exempt_work_zones` /
  `exempt_fraction` confinement gates (`_order_exempt_ids`,
  `_exempt_fraction_draw`), `work_zone` on the dict projection,
  `crew_window` witness block, five SOP-017 variants, campaign spec
  + cell + readout + 11 tests.
- #930: CW-02 close-out — committed readout, `docs/ledger/
  CREW-WINDOW-02.md`, open-ledger §2 update, README index rows,
  campaign LEDGER ops record, readout falsy-zero fixes.

## 6. Running jobs / artifacts

None running. Results at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_window_02/`
(manifest + `design.json`/`design.md` at prefix root, 240 `cell_*.json`
under 12 block dirs). Arrays: 12 20-child jobs, all SUCCEEDED — IDs in
`campaigns/covid/crew_window_02/LEDGER.md`. Image
`picard-campaign:covid-crew-window-02` @ `sha256:2b481866`; jobdef
`picard-covid-crew-window-02` (rev 1 at registration; later submits
auto-revved).

## 7. What is now void / superseded

Nothing withdrawn. CW-01's CLIFF-STRUCTURE verdict stands as the
corner measurement — CW-02 supersedes it as the last measurement of
record on this channel (open ledger §2 updated). The crew-share gap
(reported at both θ) replaces "does the channel have an interior" as
the open sub-question.

## 8. The single open decision

Source the landing complement — does a ~25–31% essential working-crew
share correspond to a measured quantity (the record's essential-service
complement, VSP manning fractions)? And separately: decide whether the
≈1 D0 realized-share expectation in the frozen design is amended
(isolation-path confinement is physical) or kept as a strict witness.

## 9. Do not reopen

- The replay contract is frozen (SOP-017 days 16–30, infection_age
  6.8, imports 1, seeds 20200205–20200224, `dwell_weighted`).
- Arm fractions/zone lists were declared probes, Grade C — the landing
  share is a magnitude to source, never a fitted constant.
- `SOP-017-ALLHANDS` stays a counterfactual bound; the new
  `SOP-017-{NARROW,WIDE,QUARTER,HALF,THREEQ}` variants are CW-02 probe
  arms, not candidate shipped policy.
- `CREW_DUTY_MIX` subclassing is a separate structural stage — not
  implied by this landing.
- No new arms mid-campaign ran; none should be back-ported into this
  readout.
