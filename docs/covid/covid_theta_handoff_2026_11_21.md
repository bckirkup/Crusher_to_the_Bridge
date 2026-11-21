# COVID Θ/DP handoff — 2026-11-21

> **Status:** Handoff record. Reports no new numbers — every figure is
> quoted from the ledger entry or readout that measured it, with that
> entry's `Measured at` SHA. Successor sessions read this before
> re-deriving anything.

Retires the session that carried the Θ-on-DP question through four
measured legs: capture (CAPTURE-01), the confined tail (QUAR-TAIL-01 +
QUAR-TAIL-SEAM-01 campaign), and ignition timing (IGNITION-01).

## 1. The question

Can Θ (the composite dose scale) be scored on the Diamond Princess
`boxed_s1s2` replay at the right-sized operating point θ=3.162e8
(`dp_theta_8p50`)? The scored contract is the record's observable
trajectory: 712 confirmed, ~0.85 confirmed-per-infection, a day-13-15
confinement-peak shape (before_share 0.173), and the during-quarantine
mass band [150,350]. The H5 serology band is declared held-out-forever
(owner decision, not negotiable by a session). Success = an admissible
θ on the scored contract; failure = a named structural blocker, not a
number tuned to an anchor.

## 2. Current hypothesis

Θ is scorable on DP once two structural facts are declared, neither of
them a constant: (a) the index's **boarding-window exposure** — the
late-ignition blocker is a founder-pool lottery on a droplet+caregiver
channel, i.e., where the drawn index spends embarkation day — and
SEED-RING-01 has now narrowed what that declaration must be: not the
index's dining-zone assignment (`placement.dining_service_type` is
measured NULL, founder median 2.0 vs frozen ≥10), but its realized
embarkation-day surge itinerary (muster/boarding-crowd exposure); and
(b) the **confined-service confinement composition** — only the joint
quarter-exempt × symptomatic-crew-removal arm lands the during band.
Per-infection capture is a timing readout, not machinery: on the
declared conditioned basis it already exceeds 0.80 on every arm
including the verbatim replay.

## 3. Evidence for

- `COVID-CAPTURE-01` (measured at `7b34405d`): capture is bimodal by
  incidence timing — record-timed cells confirm 0.911–0.930 as declared;
  unconditioned ~0.52 is the structural ~18% post-window pool.
  Declared contract consequence: `confirmed / infections_reachable`.
- `COVID-QUAR-TAIL-01` (measured at `6fa5e3bc`): the tail factorizes
  into late ignition × under-damped confinement (before 90 / during 415
  / after 187 medians; cabin 72%, droplet 56% + service_to_host 32% +
  caregiver 11%).
- `COVID-QUAR-TAIL-SEAM-01` (measured at `b4591170`): 80-cell
  fraction×duty factorial, audit clean, D0 bit-exact replay —
  FRAQMB 394, MB_DUTY 425, **FRAQMB_DUTY lands the band at 257**;
  conditioned capture 0.811–0.845 on every arm.
- `COVID-IGNITION-01` (measured at `b4591170`): founder yield
  discriminates ignition day with zero overlap — ≥10 aboard-window
  acquisitions → ign ≤9 (4 cells, 10/10/13/28); ≤5 → ign ≥10 or dead.
  Founder routes droplet+caregiver only; post-founder growth flat
  (~3.8×/5d). Verdict: boarding-window exposure lottery, not intrinsic
  dose timing.
- `COVID-SEED-RING-01` (measured at `87e8e3bb`): NULL-PLACEMENT on the
  declared buffet-placement arm (40 cells, audit clean) — founder
  median 2.0 vs committed drawn 2.5; D0 drift witness CLEAN (0/20
  paired deltas). Dining assignment is correlative; the surge
  participation that produced record-class pools (19/25 founders on
  20200214/15) rides the realized day-0 itinerary, not the seat. The
  under-declared structure is the embarkation-day crowd/muster
  geometry itself.

## 4. Evidence against / unexplained

- Founders gate ignition day, not the peak: 20200208 drew 13 founders,
  ignited day 9, yet its mass peaks at median day 23 (before 283).
  Record timing additionally needs sustained early growth — the
  SEED-RING-01 prediction is founder → ign AND trajectory, not founder
  alone.
- Whether the record's trajectory implies more than one effective
  boarder is hypothesis, not measurement; imports>1 is declared a
  falsification probe, never a fit axis.
- Why the founder channel carries no airborne/direct/fomite
  acquisition in any of 20 draws is measured but unexplained — it is
  what makes the channel structurally narrow.

## 5. PRs landed this session

- #1368 COVID-CAPTURE-01 — capture leg measured + declared seam.
- #1370 COVID-QUAR-TAIL-01 — tail decomposition, two factors named.
- #1374 QUAR-TAIL-SEAM-01 — campaign spec (80 cells frozen).
- #1377 QUAR-TAIL-SEAM-01 — MB_DUTY canary readout + submission record.
- #1378 QUAR-TAIL-SEAM-01 — full-campaign readout + ledger + close-out.
- #1379 COVID-IGNITION-01 — ignition decomposition + declared seam
  COVID-SEED-RING-01 + `tools/covid_ignition_readout.py`.
- #1381 COVID-SEED-RING-01 — placement seed constraint + frozen design
  + campaign registration (merged `87e8e3bb`).
- #1387 COVID-SEED-RING-01 — campaign close-out: 40-cell readout,
  NULL-PLACEMENT ledger, handoff update.

## 6. Running jobs

None. SEED-RING-01 arrays landed 40/40 (jobdef
`picard-covid-seed-ring-01:4`, image digest `sha256:87bc852a`, prefix
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_seed_ring_01/`,
array IDs in `campaigns/covid/seed_ring_01/LEDGER.md`).
All four QUAR-TAIL-SEAM-01 arrays landed (80/80 cells);
array job IDs, jobdef revision `picard-covid-quar-tail-01:3`, image
`sha256:39eb3d53` and the S3 prefix
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quar_tail_01/`
are recorded in `campaigns/covid/quar_tail_01/LEDGER.md` and
`docs/covid/covid_quar_tail_01_readout.md`.

## 7. What is now void

- The CW-02-derived ~0.96–0.99 exempt-share over-declaration does not
  carry to θ=3.162e8 — realized working share at activation is
  0.27–0.31 on the committed cells (corrected in COVID-QUAR-TAIL-01 and
  the SEAM-01 design; illness pre-confines the crew).
- Unconditioned confirmed-per-infection as a scored criterion: it
  measures the post-window timing residual, not machinery (declared in
  CAPTURE-01, vindicated in SEAM-01). Adoption of the conditioned basis
  is an owner call.
- The QUAR-TAIL-01 hypothesis that late ignition is "intrinsic to the
  right-sized dose": falsified by IGNITION-01 — the epidemic grows
  normally once a founder pool exists; the deficit is the pool draw.
- The "over-declared exempt population carries the tail" framing of
  the seam prediction: the joint-only landing (SEAM-01) supersedes it —
  the tail is crew-service-fed but only jointly.

## 8. The single open decision

SEED-RING-01 is resolved: **NULL-PLACEMENT** — and EARLY-GROWTH-01
(pure readout on its cells) has sharpened the blocker past the founder
question: on record-timed cells the overshoot is already in place by
day 15 (pre-quarantine infections median 1,292 vs the whole-voyage
band [712,960]; before-17 onsets 383 vs 34; all 8 cells end 1,268–3,136,
above the band), so the same θ that must lift the founder pool also
drives the growth that overshoots the mass.
The open decision is now **whether to declare voyage-stage contact
structure** — a dense embarkation-window field that relaxes after the
boarding days (the surge that expires), decoupling founder yield from
settled-voyage growth — versus **re-scoping the Θ contract** to
envelope/conditioned scoring. A founder-only arm is no longer an
honest probe: it predicts the founder leg lands and the mass leg still
fails. GM scoring stays gated; H5 stays held out.

Standing owner calls recorded in the ledger (not session decisions):
`confirmed / infections_reachable` as the scored capture basis, and
whether FRAQMB_DUTY becomes the boxed_s1s2 replay default.

## 9. Do not reopen

- No fitting Θ or any epidemiological constant to a scored anchor —
  arms are declarations, not fits.
- H5 is held-out-forever; it does not enter the scored contract.
- imports>1 is a falsification probe, not an axis: the record declares
  one index.
- The tail's joint-only damping (FRAQMB_DUTY) is measured — single-lever
  confinement fixes are falsified at this θ; do not re-propose them.
- Index dining-zone placement as a founder-pool lever: measured NULL at
  θ=3.162e8 (SEED-RING-01); do not re-run placement variants. The
  remaining lever is itinerary-level surge exposure, not venue
  assignment.
- Capture must be quoted on the conditioned basis; the unconditioned
  ~0.52 is the structural post-window residual, not a defect.
