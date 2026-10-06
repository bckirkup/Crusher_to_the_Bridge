# Flu open-voyage session handoff (2026-10-06)

Status: handoff record. Reports no new numbers — every figure below is
quoted from the committed ledger entry or readout that measured it, with
that artifact's `Measured at` SHA.

Retires the session that ran FLU-OPEN-01 → FLU-VIS-01 → the sign-reversal
attribution → CAREGIVER-SVC-01 (the `service.contact_factor` fix) and the
diamond_princess_2020 detector repin, after seven PRs.

## 1. The question

Does the `influenza_a` arm credibly depict flu on all four ship classes
(expedition_cruise_450, spirit_cruise_3000, classic_cruise_1900,
mega_cruise_5000)? Two surfaces: (a) the conditioned confined cabinmate SAR
vs the dose-derived CABIN-FLOOR-03 band — settled in-band at `8c03e9d7`
before this session; (b) the open voyage — free-running importation + organic
confinement — scored against Ward 1982's presenting-attack (~0.7% of
population presenting while ~8.9% infected) and the declared reporting
vectors. Success was depiction within the frozen frames or a measured,
attributed gap; failure was an unattributed move or a frame breach with no
declared cause. The follow-on question the census opened: what drove the
expedition r200 sign-reversal (hotter reporting ⇒ *more* onboard infections),
and can the responsible channel be discounted honestly.

## 2. Current hypothesis

Flu depicts credibly on all four classes on both surfaces. The big-hull
Ward presenting-attack gap is incidence-side, not reporting-side — the
declared reporting layer saturates (even ceiling values can't reach 0.7% on
the three large hulls), so no reporting corner fixes the residual. The r200
sign-reversal is the serviced-quarantine crew bridge: confined cohort ×5 ⇒
cabin service deliveries ×2.6 ⇒ exempt crew caregiver infections ⇒ a late
passenger droplet wave on the never-confined pool. `service.contact_factor`
U[0.05,0.3] (Grade C, below R1's U[0.3,0.7] steward bound) now discounts the
R3 door-drop dose on every pathogen profile, default-ON.

## 3. Evidence for

- FLU-OPEN-01 — `docs/ledger/FLU-OPEN-01.md`, `docs/flu/flu_open_voyage_01_readout.md`,
  measured at `7f4702ef` (400/400 cells): outbreak forms on all four classes;
  onboard-acquired infections fire illness exactly as declared (0.750 vs
  implied 0.74); caregiver is 49–55% of onboard-acquired infections on every
  class.
- FLU-VIS-01 — `docs/ledger/FLU-VIS-01.md`, `docs/flu/flu_visibility_01_readout.md`,
  measured at `ca775a0b` (2400/2400 cells): presenting attack flat across the
  whole 8× reporting span (spr 0.21–0.22%, cls 0.22–0.25%, mega 0.13–0.16%)
  including the saturation arm; exp brackets Ward on every arm via its ~2×
  voyage attack.
- Sign-reversal attribution — `docs/flu/flu_visibility_01_readout.md` §4
  (amended in #934): paired probe re-runs at `ca775a0b`, crew-bridge
  mechanism verified (import cohorts identical; 2/59 surplus while confined;
  service deliveries 440 vs 167; Δinfected vs Δquarantined r=0.81 across 100
  paired seeds).
- CAREGIVER-SVC-01 — `docs/ledger/CAREGIVER-SVC-01.md`, measured at
  `f71b26bb`: 8-seed × 5-arm response surface; the `contact_factor: 1.0`
  labelled baseline is bit-identical to the pre-change engine (59 onboard,
  14 crew-caregiver, 440 deliveries on exp r200 s8188); the shipped default
  lands at 3 onboard / 1 crew-caregiver on that seed.

## 4. Evidence against / unexplained

- **Residual second channel (unattributed).** At `contact_factor: 0` (dose
  zero, deliveries + report stamps intact), seeds 8112/8184/8120 still carry
  +23/+40/+9 onboard infections vs the r100 baseline — a passenger/droplet
  wave, not crew. Candidate: confined cabin-mate pooling (CONFIRMED confines
  mates into shared 40 m³ cabins). Flagged in `docs/ledger/CAREGIVER-SVC-01.md`.
- Seed 8162's non-monotone bump under U[0.05,0.3] (73 vs 67) — single-seed
  tail re-realization on an 8-seed probe, noted, not chased.
- The DP slow-cell drift under the crew-window merges is unattributed
  per-merge (suspects `f8dd6c0a` / `1d4778f6` / `e8291a42`); see
  `tests/test_covid_hull_change_detector.py` comment and §5.
- Expedition keeps a ~⅓ no-transmission floor on open voyages — recorded as
  a small-ship property, not a defect (`docs/ledger/FLU-OPEN-01.md`).

## 5. PRs landed this session

- #921 — FLU-OPEN-01 design spec (campaigns/flu/open_voyage_01).
- #926 — FLU-OPEN-01 readout + ledger + execution log (400/400 measured).
- #928 — FLU-VIS-01 design spec (campaigns/flu/visibility_01).
- #933 — FLU-VIS-01 readout + ledger (2400/2400 measured); fleet-aware
  reporting conclusion.
- #934 — readout §4 amendment: sign-reversal attributed to the
  serviced-quarantine crew bridge.
- #936 — CAREGIVER-SVC-01: `service.contact_factor` U[0.05,0.3] default-ON,
  `1.0` labelled baseline, engine + tests + provenance + ledgers.
- #940 — diamond_princess_2020 slow-cell repin `(2765, 2587, 2702, 398, 333)`
  → `(2794, 2613, 2579, 429, 362)`: nightly 37461678535 already read the
  drifted `(2766, 2587, 2693, 400, 335)` pre-#936 (crew-window merges), the
  1.0 arm reproduced it exactly, shipped default added the factor hop.

## 6. Running jobs

None. FLU-OPEN-01 and FLU-VIS-01 fleets both completed clean (400/400 and
2400/2400, 0 failed) on `picard-analysis-queue` (On-Demand — the Spot
compute environment delivered zero capacity and was abandoned per the
drought playbook). Raw payloads remain under
`s3://.../campaign/flu_open_voyage_01/` (image `picard-campaign:flu-open-voy01`
@ `7f4702ef`) and `s3://.../campaign/flu_visibility_01/` (image
`picard-campaign:flu-vis01` @ `ca775a0b`, digest `sha256:1c0aa1d5…`,
jobdef `picard-flu-visibility-01` revs :2–:25).

## 7. What is now void

- F5's pooled reported/infected frame `[0.03, 0.15]` is void as a comparator
  shape — unreachable across the swept grid (minimum 0.19); Ward's
  presenting-attack surface replaced it as the scored comparator
  (`docs/ledger/FLU-VIS-01.md`).
- The confined cabin-mate co-confinement hypothesis for the sign-reversal
  was refuted before reaching ledger status (2/59 surplus while confined) —
  superseded by the crew-bridge attribution in `docs/flu/flu_visibility_01_readout.md` §4.
- The DP slow-tier pin `(2765, 2587, 2702, 398, 333)` is superseded by
  `(2794, 2613, 2579, 429, 362)` (#940).
- Pre-SVC-01 service-channel dose figures: `docs/flu/flu_open_ledger.md` §1
  and `docs/norovirus/norovirus_open_ledger.md` §1 carry the withdrawal
  pointers — R3 service deliveries ran undiscounted in every measurement
  before `f71b26bb`.

## 8. The single open decision

**Attribute the residual second channel first** (the +23/+40/+9 passenger/
droplet surplus at `contact_factor: 0` on seeds 8112/8184/8120 — candidate:
confined cabin-mate pooling). Ranked options for the next session:

1. Attribute it on paired probe re-runs (same 8-seed grid, per-route and
   per-zone decomposition of the surplus), then decide whether it is a
   fixable generic seam like SVC-01 or a declared small-hull property.
2. If it is declared property rather than defect, move to the incidence-side
   lever for the big-hull Ward gap (importation intensity × k corner, or
   voyage length) as a new bounded campaign spec.
3. Only after (1)–(2): a fleet-scale effect-size re-measurement of
   `contact_factor` (100-seed arm contrast — the 8-seed probe priced the
   mechanism, not the fleet distribution).

## 9. Do not reopen

- No fitting any constant to Ward, VSP, Park, or the passenger/crew anchors —
  `contact_factor` is Grade C declared and must not be tuned onto a target;
  the `[0.03, 0.15]` frame was a comparator, not a fitting target.
- Conditioned confined-SAR in-band on all four classes at `8c03e9d7` —
  settled, do not re-derive.
- The observation vector's ~2×-Ward reporting level is the declared hot
  surface — measured, not a defect; a reporting-corner pick is a modeling
  decision, not a calibration.
- `contact_factor: 1.0` stays as the labelled un-discounted baseline arm;
  the better mechanism stays default-ON.
- R2 `tending` (family bedside caregiver) was deliberately left at 1.0 —
  family does not glove; revisit only with a sourced bound.
