# COVID quarantine attribution v2: post-REINFECT-01 rerun — crew exemption and pool transport are load-bearing at Θ 1e9

> **Status:** Findings (2026-09-20). Same 240-cell design as v1
> (`picard_framework/runs/covid_quarantine_attribution_v1_design.json`, six
> arms × two Θ × 20 seeds, criterion frozen before any cell ran), re-run on
> AWS Batch at `main` = `d62f10d` (merge of #636, REINFECT-01 fix), image
> `picard-campaign:quar-attr-v2-d62f10d`
> (`sha256:2ce4b13c5a32f0ee21f2cb4f094cde54547850d4482099592f448aa976b2fc5b`),
> job definition `picard-covid-boarding-screen:10`, canaries
> `31cc4ab3-4b20-41bb-8f94-f8d027b20767` (A0 Θ 1e5) and
> `d42369cb-5ca2-4878-853a-750e59dd3e68` (A0 Θ 1e9), array job
> `acae64f8-14df-45ad-8ba4-8e7d370aa552` (`picard-attribution-v2-d62f10d`) on
> `picard-campaign-queue`. 240 of 240 children SUCCEEDED, zero failures, ~30
> min wall clock; every payload has `invalid_reason == null`. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quarantine_attribution_v2/d62f10d/cells/`.
> Surface: `docs/covid/covid_quarantine_attribution_v2_surface.csv` (one row
> per (Θ, arm, seed) cell, same columns as v1). No Theta is claimed here;
> arms A1–A5 are counterfactuals and score no anchor.

This is the re-measurement the v1 readout's §7 asked for: the same design,
the same frozen criterion, on an engine where a cleared host keeps the
declared `immune_waning` refractory window (90 d at protection 1.0 for
`sars_cov2_resp`) and a second infection can no longer overwrite the first
episode's stamps (`docs/ledger/REINFECT-01.md`, fixed at `7f105a7`).

Every figure below is measured at `d62f10d` inside the campaign image, seeds
`20200205 + k`, k = 0..19, `diamond_princess_2020`, one declared import,
declared index onset day −1. §1–§3 are measurements; §4 is the comparison
against v1 at `861a0b9`; §5 separates measured from inferred.

## 1. Preflight and canary parity with the fix branch

Engine commits between `7f105a7` (v2 canary branch head) and `d62f10d`
(first-parent): only the #636 merge itself and #635 (NORO-EMESIS-SIZE-01,
docs + readout tool, no engine diff). Paired canary in-image, A0 seed
`20200205`:

| cell | 7f105a7 | d62f10d | match |
|---|---|---|---|
| Θ 1e5 total / AR / before-during-after | 950 / 0.2560 / 745-198-7 | 950 / 0.2560 / 745-198-7 | exact |
| Θ 1e9 total / AR / before-during-after | 3,458 / 0.9318 / 3,414-43-1 | 3,458 / 0.9318 / 3,414-43-1 | exact |

Dry-run array size 240; S3 prefix empty before submit.

## 2. The post-fix measure is the first-infection count — validated

In the v2 payload, `infections_during_quarantine` (truth channel) is
**identical to `ledger_events_during` (event-ledger first event per host) in
all 240 of 240 cells** — measured. That cell-for-cell identity is the
campaign-scale validation of REINFECT-01: the truth channel no longer dates
a later episode, and it retroactively validates v1 §5's post-hoc use of the
ledger as the first-infection count. The local probe on the saturated A0
Θ 1e9 cell reports `episode >= 2` = 0, zero negative onset lags, and zero
ledger events preceding `infection_epoch` (host trajectory; the mechanism
check, not the image's numbers).

## 3. The frozen criterion, applied verbatim — verdicts change

Takeoff is `recorded_onsets >= 10`; (i) is the all-20-seed median of
`infections_during_quarantine`, (ii) the median over seeds that took off in
both `A0` and the arm; load-bearing needs (ii) ≤ −50% with (i) also falling,
non-load-bearing is |shift| < 20%, indeterminate between, and no verdict
without takeoff overlap.

| Θ | Arm | takeoff | med (i) arm | n both | med (ii) arm | med (ii) A0 | shift (ii) | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1e5 | A0_declared | 3/20 | 0 | — | 198 | 198 | — | — |
| 1e5 | A1_crew_confined | 3/20 | 0 | 3 | 109 | 198 | −45% | indeterminate¹ |
| 1e5 | A2_pool_transport_off | 3/20 | 0 | 2 | 399 | 152 | +162% | indeterminate |
| 1e5 | A3_near_field_off | 4/20 | 0 | 3 | 207 | 198 | +5% | non-load-bearing¹ |
| 1e5 | A4_crew_confined_and_pool_off | 3/20 | 0 | 2 | 122.5 | 152 | −19% | non-load-bearing¹ |
| 1e5 | A5_all_shared_air_off | 0/20 | 0 | 0 | — | — | — | not eligible |
| 1e9 | A0_declared | 12/20 | 71.5 | — | 829.5 | 829.5 | — | — |
| 1e9 | A1_crew_confined | 12/20 | 60.5 | 12 | 212.5 | 829.5 | −74% | **load-bearing** |
| 1e9 | A2_pool_transport_off | 9/20 | 1.0 | 8 | 119 | 348.5 | −66% | **load-bearing** |
| 1e9 | A3_near_field_off | 12/20 | 90.0 | 8 | 553.5 | 466.5 | +19% | non-load-bearing |
| 1e9 | A4_crew_confined_and_pool_off | 8/20 | 1.5 | 7 | 59 | 119 | −50% | **load-bearing**² |
| 1e9 | A5_all_shared_air_off | 1/20 | 0.0 | 1 | 203 | 43 | +372% | no verdict³ |

¹ At Θ 1e5 only 3–4 of 20 seeds take off in any arm and both all-seed
medians are 0; the rows are reported for completeness, not as verdicts.
² A4 also suppresses takeoff (12 → 8 seeds); its conditional −50% is read
over the smaller, survivor-biased overlapping set — see §5.
³ One overlapping seed; not eligible for a verdict.

**Result at `d62f10d`: at Θ 1e9, confining the crew (A1) and removing
cross-zone HVAC pool transport (A2) are each load-bearing for infections
during enforced quarantine; near-field air (A3) is not.** At Θ 1e5 nothing
is decidable — 17/20 seeds go extinct in every arm.

## 4. v1 (861a0b9) vs v2 (d62f10d), side by side

Conditional-on-takeoff medians, A0's value read on the same overlapping
seeds. V2's truth channel and ledger columns are identical (§2) and are
shown once.

Θ 1e9:

| Arm | takeoff v1→v2 | dQ (ii) shift, v1 truth | dQ (ii) shift, v1 ledger | v2 (ii) shift |
|---|---|---|---|---|
| A0 | 12/20 → 12/20 | — | — | — |
| A1_crew_confined | 12 → 12 | −21% | −76% | **−74%** |
| A2_pool_transport_off | 9 → 9 | −16% | −65% | **−66%** |
| A3_near_field_off | 12 → 12 | +3% | +14% | +19% |
| A4_crew_confined_and_pool_off | 9 → 8 | −23% | −85% | **−50%** |
| A5_all_shared_air_off | 1 → 1 | −78% (n=1) | +400% (n=1) | +372% (n=1) |

Θ 1e5 (n ≤ 3; completeness only): A1 −73% (v1 truth) / −74% (v1 ledger) /
−45% (v2); A2 +51% / +63% / +162%; A3 −43% / −49% / +5%; A4 −45% / −53% /
−19%.

Whole-voyage attack rate (median over all seeds / conditional on takeoff at
Θ 1e9): A0 0.310 / 0.865; A1 0.092 / 0.824; A2 0.001 / 0.896; A3 0.289 /
0.790; A4 0.001 / 0.869; A5 0.000 / 0.071 (n=1). Conditional AR is *not*
arm-invariant to the letter (0.79–0.90 across A0–A4) — A1 moves it (0.310 →
0.092 all-seed; 0.865 → 0.824 conditional) — but the dominant AR lever is
takeoff itself: A2/A4's all-seed medians are ~0.001 because they suppress
the outbreak, not because the voyage differs once it starts (conditional
medians 0.87–0.90). At Θ 1e5 conditional ARs are 0.033–0.19 on n = 3–4.

During-quarantine first-infection events by route, takeoff cells pooled
(v2, measured):

| Θ | Arm | droplet | hvac_airborne | fomite | direct_contact |
|---|---|---:|---:|---:|---:|
| 1e5 | A0 | 938 | 17 | 0 | 0 |
| 1e5 | A1 | 281 | 0 | 0 | 0 |
| 1e5 | A2 | 806 | 0 | 0 | 0 |
| 1e5 | A3 | 1,139 | 0 | 0 | 0 |
| 1e5 | A4 | 252 | 0 | 0 | 0 |
| 1e9 | A0 | 7,853 | 819 | 0 | 0 |
| 1e9 | A1 | 3,431 | 1,208 | 0 | 0 |
| 1e9 | A2 | 3,028 | 66 | 0 | 0 |
| 1e9 | A3 | 7,244 | 485 | 0 | 0 |
| 1e9 | A4 | 1,609 | 0 | 0 | 0 |
| 1e9 | A5 | 0 | 0 | 199 | 4 |

The route profile is unchanged in kind from v1: droplet carries the during-
window infections, `hvac_airborne` is ~9% at Θ 1e9 and rises under A1, and
A5's single takeoff ran on fomite alone.

## 5. Interpretation

- (a) **Measured**: at Θ 1e9 the frozen criterion now calls exempt-crew
  confinement (A1, −74%, n = 12) and cross-zone pool transport (A2, −66%,
  n = 8) load-bearing. A4 (both removed) also suppresses takeoff 12 → 8, so
  its conditional −50% over n = 7 is computed on a smaller, survivor-biased
  seed set — do not read A4 < A1 in shift as antagonism between the two
  channels; A4 mostly prevents the outbreak rather than trimming the
  during-window count on a fixed outbreak.
- (b) **Measured**: near-field air (A3, +19%, n = 8) is non-load-bearing at
  Θ 1e9.
- (c) **Measured**: A5 kills takeoff (12 → 1 at 1e9, 3 → 0 at 1e5); its one
  surviving cell is a crew-only fomite outbreak and is uninterpretable for
  the quarantine window.
- (d) **Measured**: whole-voyage AR is reported per arm above. What barely
  moves once a seed takes off is the conditional AR (0.79–0.90 at 1e9);
  what moves the all-seed AR is the takeoff probability itself (A2, A4, A5)
  and, to a lesser degree, crew confinement (A1 conditional 0.824 vs 0.865).
- (e) **Measured**: at Θ 1e5 only 3/20 seeds take off; nothing is decidable
  at that Θ.
- (f) **Measured**: removing reinfection barely moved A0's Θ 1e9 AR
  (0.314 → 0.310) but cut the saturated seed's during-window count ~10×
  (973 → 43 at seed `20200205`) and collapsed the A0 conditional median
  1,035.5 → 829.5. The v9/handoff-§12 reading "the outbreak continues
  through enforced quarantine" at truth-channel scale is now quantitatively
  dead: on the repaired engine the median takeoff seed adds ~830 first
  infections during quarantine at Θ 1e9, and ~70% of those are carried by
  the two channels the criterion calls load-bearing.
- **Inferred**: v1's ledger-based post-hoc shifts (−76%/−65%/−85%) and v2's
  criterion shifts (−74%/−66%/−50%) agree within paired-seed noise for A1
  and A2, which is what §2's cell-for-cell identity predicts — v1 §5 was
  measuring the right thing on the broken engine.
- **Hypothesis**: the Θ 1e9 during-window residual under A4 (59 infections
  on n = 7 survivors) is consistent with cabin/corridor droplet spread
  among confined hosts, but the survivor-biased set means this cannot be
  read as "the remaining leak" without a dedicated arm.

## 6. Supersedes and limits

- **Superseded**: the v1 frozen-criterion verdicts at `861a0b9` ("no channel
  is load-bearing at either Θ") — the measure they were applied to counted
  second episodes. V1's §5 ledger numbers are **confirmed**, not superseded.
- **Not changed**: no Θ is admissible or fitted; covid.T1/T3 were not
  scored; counterfactual arms are not the historical scenario. All v2
  numbers are measured at `d62f10d` in-image; the local-host trajectory
  differs (CPython 3.12/numpy 2.5.0) and no local figure is quoted above.
- **Limit**: the cell payload carries no `episode`/`first_infection_epoch`
  field — first-infection counting in the window is asserted by the 240/240
  ledger identity and the local probe, not readable off the payload itself.
  Extending `_truth_window_counts`/`_attribution_block`
  (`picard_framework/covid_boarding_screen.py`) to read
  `first_infection_epoch` would make it explicit; not done.
