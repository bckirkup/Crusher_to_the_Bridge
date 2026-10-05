# FLU-OPEN-01 — open-voyage influenza census across the four ship classes

> **Status:** Specced — criteria frozen, no cells run. Design of record for
> `campaigns/flu/open_voyage_01`. Commit `de4441f3` era (post-HOST-AGE-02/03).

## 1. Question

Can the model at head depict `influenza_a` on a **free-running voyage** — no
declared confinement, no conditioned-cell scaffolding — on all four real
cruise classes, and do the **reporting-side surfaces** (ever-ill share,
reported share, age-band presentation, age-band severity mix) read sanely
now that HOST-AGE-02/03 made presentation and severity age-graded?

## 2. Measurement gap this closes

- Every four-class flu number on record is a **conditioned** cell: the
  `flu_rhythm_01` manifest (isolated `influenza_a`, explicit 2-passenger
  epoch-0 seed, SOP-017 declared day 1 → end, 288 epochs). The scored
  anchor — confined-cabinmate SAR vs the dose-derived CABIN-FLOOR-03
  band — is in-band on all four classes at `8c03e9d7` (FLU-SOCIAL-01
  census: mega 5.1–5.6 %, spr ~7.2–7.7 %, cls ~7.4–7.5 %, exp
  11.8–13.3 %).
- HOST-AGE-02 (`symptomatic_fraction_by_age_band`, Hoy 2022) and
  HOST-AGE-03 (`severity_model.base_probabilities_by_age_band`, CDC
  2023-24) are default-ON at head. The surfaces they directly shape —
  who presents, how severely, and therefore who enters the observation
  funnel — have never been measured on **any** class at head.
- FLU-AGE-01's expedition canary (`b4207e5f`) proved the confined
  endpoint invariant by construction (6/66 = 9.1 % identical; 18/20
  cells bit-identical) — but its only divergences were crew-scale
  `caregiver:influenza_a` acquisitions, and whether the larger hulls'
  crew scale amplifies that pathway is explicitly unmeasured.
- The `flu.F5` internal check (Ward 2010: reported/infected ≈ 0.08 on a
  voyage with flu circulating) has only ever been read on the
  conditioned surface — 0.18 there, attributed to conditioning. No
  open-voyage reading exists.

## 3. Cell definition (settled inputs — do not re-derive)

Each cell is `conditioned_spec(..., confinement="organic")` — byte-for-byte
the conditioned-census spec **minus** `scenario_schedule`:

- bundle `active_profiles`, arm isolated to `influenza_a` (other bundle
  members removed; `initial_infected` nulled);
- explicit index: 2 passengers at epoch 0 via `initiation.explicit_seeds`
  (the scenario's stated index mechanism);
- the profile's own **boarding prevalence draw runs as shipped**
  (passenger 0.008, crew 0.005) — real stochastic imports on top of the
  pair, which is the point of an open voyage;
- `k = 6e-4` shipped midpoint (FLU-DELIVERY-01 sourced interval
  2e-4..1e-3); **no constant overrides**;
- 288 epochs (12 days), `natural_history_clock` as declared;
- escalation/observation stack free-running — SOPs (including SOP-017
  itself) may fire organically from simulated surveillance; that is part
  of what is being measured;
- seeds 8105–8204 — the same 100-seed block as the conditioned censuses,
  keeping per-seed continuity for any paired lookback;
- four blocks, one per class: `expedition_cruise_450`,
  `spirit_cruise_3000`, `classic_cruise_1900`, `mega_cruise_5000`;
- **400 cells total, single arm** — this is a measurement census, not an
  A/B; comparisons ride on seeds, never on flags.

## 4. Frozen verdict frames (declared before any cell runs)

This is a census: **no selection criterion exists** — nothing here admits a
cell or rejects a run. The frames below are pre-declared reading rules. A
miss names a follow-up surface in the ledger; it is never a trigger to
retune a constant, per the repo's no-tuning rule.

| # | Surface | Frame |
|---|---------|-------|
| 1 | **F5 reporting check** — `ever_reported / ever_infected`, pooled per class and fleet (plus passenger-only cut) | pooled point inside **[0.03, 0.15]** reads consistent with the Ward 0.08 anchor (~2× commensurable slack each side). Outside → "anchor tension" filed against the observation funnel, not a parameter defect. |
| 2 | **ever_ill / ever_infected** — pooled per class | read against the **profile-implied** expectation `E = Σ_b infected_b · f_b / infected` from that cell's measured band mix (f_b = declared `symptomatic_fraction_by_age_band`, 0.965 / 0.909 / 0.734; fallback 0.669 for unbanded). Measured inside Wilson-95 of E → consistent. The conditioned-cell 0.31 (n = 45, onset-dominated) is historical, not a target. |
| 3 | **Presentation by age band** — `presented / infected` per band, bands with ≥ 5 infected only | Wilson-95 non-overlap vs the declared band fraction → flag the band. |
| 4 | **Severity mix by band** — `symptom_severity_peak` histogram per band vs `severity_model.base_probabilities_by_age_band` (states: asymptomatic, subclinical, mild, moderate, severe_critical) | per-state share vs declared vector, ≥5-n rule; severe_critical is the watched tail (senior bands carry 0.0786). |
| 5 | **Caregiver reach** — infections whose `acquired_particles_by_route` contains `caregiver` (any share) and where it is the argmax route, split pax/crew, per class | descriptive; answers the s8113 question — does crew scale on spirit/classic/mega amplify the crew-service-state cascade vs expedition. Hypothesis-generating, no threshold. |
| 6 | **Outbreak formation** — share of cells with ≥1 onboard-acquired infection (`infection_epoch > 0`) | expected near-1 (≥2 guaranteed index + prevalence imports over 288 epochs). A depressed rate is a transmission-blocker-class finding (prove the mechanism fired before claiming a blocker). |
| 7 | **Voyage attack** — `ever_infected` per cell per class | context for every rate above; reported as median/p90/max, never selected on. |

Diagnostics (reported, never selected on):

- **Organic confinement** — `len(quarantined_ids) + len(isolated_ids)` at
  voyage end and the share of cells where any confinement formed without
  a declared schedule;
- **final_trigger_status** histogram per class (how far organic
  escalation went);
- **dominant acquisition route** histogram (argmax of each infection's
  `acquired_particles_by_route`);
- **infection_epoch** distribution — import vs onboard spread across the
  voyage (onset-timing structure);
- `caregiver_telemetry` counters echoed per cell.

## 5. Audit invariants (deviation = defect, not a failed criterion)

- **Index present**: every cell must carry ≥2 `infection_epoch == 0`
  infections. A zero-index cell means the explicit seed did not land —
  investigate, do not silently drop.
- **Artifact contract**: each child emits exactly `cell_<seed>.json`
  under its block prefix; the readout consumes only the emitted payload
  paths (CREW-WINDOW-01 lesson — never reconstruct).
- **Determinism**: the same seed re-run at the same engine SHA must
  produce identical counts.
- **No k / constant refits**, no matter what the surfaces say.

## 6. Execution plan (approval-gated)

- Grammar: `campaigns/flu/open_voyage_01/` —
  `campaign.json` + `cell.py` + `readout.py` + `LEDGER.md`; submit via
  `scripts/campaign` (no bespoke `deploy/aws` files).
- Image: build at the merge SHA of this spec's PR, tag `flu-open-voy01`.
  Engine delta `b4207e5f..de4441f3` is inert for this arm
  (`susceptibility_age_mode` labels a baseline `influenza_a` does not
  arm — `influenza_a` carries no `susceptibility_by_age_band`; the rest
  is dashboard/ledger/tooling). `ENGINE_GIT_SHA` is echoed into every
  cell payload.
- Queue `picard-campaign-queue` (Spot); 4 blocks × 100 cells.
- Preflight order: `scripts/campaign describe` prints 400 cells over 4
  blocks → literal `Dockerfile.campaign` build + in-container layout
  check → image digest pinned → `--canary` on the exp block (one child),
  payload inspected → submit the four blocks with an announced ETA.
- Expected wall: ~3–9 min per cell (isolated flu voyage measured 5–9 min
  local); ~30–60 min fleet time at prior concurrency.
- Definition of done: `docs/flu/flu_open_voyage_01_readout.md` +
  `docs/ledger/FLU-OPEN-01.md` (Measured-at SHA), `docs/flu/flu_open_ledger.md`
  §2 row, and the verdict + next decision delivered to the user.

## 7. Non-goals

- No confined-SAR re-measurement — the conditioned census owns that
  surface; CABIN-FLOOR-03 band holds at `8c03e9d7`.
- No train/test enforcement — `flu_fit_targets.json` rows stay internal
  checks; this census adds no anchor and removes none.
- No A/B arm, no mechanism flags — the labelled baselines stay available
  for attribution follow-ups, not for the census itself.
- No other pathogens; `food_contamination` stays disabled on
  `influenza_a`; covid/noro arms untouched.
- No comparison against the withdrawn 15–25 % fixed floor — the
  dose-derived band is the only live frame (CABIN-FLOOR-03).
