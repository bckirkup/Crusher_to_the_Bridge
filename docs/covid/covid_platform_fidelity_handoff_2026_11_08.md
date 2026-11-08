# Platform-fidelity study handoff — 2026-11-08

> **Status:** Handoff record (2026-11-08). Reports no new numbers; every
> figure is quoted from the committed readout
> `docs/covid/covid_platform_fidelity_readout.md` or the ledger entries
> `docs/ledger/PLATFORM-FIDELITY-01.md` (measured at `e2eb7163`) and
> `docs/ledger/PLATFORM-FIDELITY-01B.md` (measured at `7d79b7d0`).

## 1. The question

How much does hull fidelity move the two frozen 2020 COVID event replays
when everything else is held fixed? Each event is replayed on its
event-faithful platform (Diamond Princess = training hull; Greg Mortimer =
held-out hull) versus the generic proxy platform (`mega_cruise_5000`) it
currently rides, at the event's frozen operating point (DP: Θ 7.9e6,
infection_age_days 6.8, imports 1, seeds 20200205–20200224; GM: same seeds,
Θ per the frozen GM design rows). Success is a pre-registered paired
contrast with its frozen criteria answered; not success — and explicitly
out of scope — is selecting or crowning a canonical platform, refitting Θ
on the faithful hulls, adapting Θ to GM outcomes, or reopening the
train/test split. The pre-registration of record is
`docs/covid/covid_platform_fidelity_prereg_v1.md`; the DP-only amendment
is `docs/covid/covid_platform_fidelity_01b_addendum.md`.

## 2. Current hypothesis

At 20 seeds/arm the hull choice moves the COVID replays by amounts the
frozen criteria cannot resolve. The one directional signal worth a
follow-up: on the corrected DP contrast the event-faithful hull has a
LOWER takeoff probability (0.30 vs 0.50) but LARGER outbreaks conditional
on takeoff (unconditional onset totals 1457 vs 1103), a split whose
paired endpoint rests on 5 both-takeoff seeds with a seedwise spread that
includes zero. GM shows no decisive hull effect at any frozen row, with
rare takeoff at Θ 7.9e6 reported as-is.

## 3. Evidence for

- Corrected DP contrast (PLATFORM-FIDELITY-01b, `7d79b7d0`, readout §01b):
  P(takeoff) proxy 0.50 vs dedicated 0.30; paired Δ median +114 onsets,
  q05–q95 [−66.6, +358.6] over n = 5 both-takeoff (seedwise spread, NOT a
  confidence interval); CRN ρ −0.137 → unpaired declared; unconditional
  medians 12.5 vs 2.0, totals 1103 vs 1457; asymptomatic share 0.367 vs
  0.427. Witness audit clean on all 20 cells (working crew 98–135 at
  activation, posted zones ⊆ the 7 hull-native essential IDs, boxed
  service active, SOP-017-MESSBOX fired, no `close_zones`).
- GM rows (PLATFORM-FIDELITY-01, `e2eb7163`): technical acceptance passed
  on all 40 canary cells and all 160 descriptive cells; SOP-017 exempts by
  class only, so the DP zone-ID defect never touched GM (working crew
  ~95/95 at activation on both hulls). At 7.9e6 takeoff is rare on both
  hulls (0.20 / 0.30); at 1e11 / 2.37e11 / 1e12 paired deltas are small
  (+3.5 to +8.0 onsets on ~50-onset medians) with intervals including
  zero. GM's statistical wording carries the same corrections as DP
  (seedwise spreads, not CIs; no equivalence-from-zero-crossing).
- Machinery proven end-to-end on both event pairs: the `platform_id` arm
  key reaches the engine, every cell echoes resolved platform, fired
  protocol ids, and input hashes; 0/220 technical failures across both
  campaigns; no `close_zones` firing anywhere.

## 4. Evidence against / unexplained

- The DP takeoff-probability gap and the outbreak-size reversal are both
  unresolved at n = 20 seeds/arm; the paired endpoint uses only the 5
  both-takeoff seeds, and CRN pairing is weak (ρ −0.137), so the paired
  Δ is hypothesis-grade, not a landed contrast.
- PF-01's original DP row hinted the same direction (conditional median
  243 dedicated vs 64 proxy) but was confounded; it is preserved as
  evidence of the zone-name-dependent intervention defect, not of hull
  fidelity (`docs/covid/covid_open_ledger.md` §1).
- GM @ 7.9e6's paired Δ interval excluded zero on 3 both-takeoff seeds
  with ρ −0.5 — flagged hypothesis-grade in the readout; not a landed
  contrast.
- No attribution of WHY the dedicated DP hull takeoff probability is
  lower was attempted (geometry vs HVAC vs zone-mix decomposition is
  unexplored).

## 5. PRs landed this session, in dependency order

1. #1176 — prereg `docs/covid/covid_platform_fidelity_prereg_v1.md` +
   campaign registration `campaigns/covid/platform_fidelity_01/` (the
   `platform_id` arm key, worker echoes) + declared data-consistency
   repairs (prereg §8).
2. #1177 — PF-01 complete: canonical readout
   `docs/covid/covid_platform_fidelity_readout.md` + ledger entry
   `docs/ledger/PLATFORM-FIDELITY-01.md` + campaign ledger §6–7.
3. #1182 — 01b addendum `docs/covid/covid_platform_fidelity_01b_addendum.md`
   (function-matched union of essential-workplace zone IDs, preflight
   evidence, corrected execution count, statistical corrections) + readout
   caveat marking the PF-01 DP row confounded/superseded.
4. #1184 — 01b campaign `campaigns/covid/platform_fidelity_01b/` (worker,
   entry, campaign.json digest-pinned, readout.py), 20/20 Batch cells,
   corrected DP readout section, `docs/ledger/PLATFORM-FIDELITY-01B.md`,
   campaign LEDGER.
5. This handoff PR — `docs/covid/covid_open_ledger.md` §1 withdrawal entry
   for the PF-01 DP row + this file + docs index rows.

## 6. Running jobs

None. All arrays are complete; nothing is burning capacity.

For the record (provenance only):

- PF-01 full array: 10 Batch jobs under queue `picard-analysis-queue`,
  image `picard-campaign:covid-platform-fidelity-01@sha256:cd59519a…`
  (built at `bba29d19`), jobdef revs :1–:10; cells at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01/`
  (200 objects). Job IDs in `campaigns/covid/platform_fidelity_01/LEDGER.md` §6.
- 01b array: job `5bd3f49c-3483-4a33-94fb-772f18f5c807`, jobdef rev :1,
  image `picard-campaign:covid-platform-fidelity-01b@sha256:ed4700c6…`
  (built at `7d79b7d0`), 20/20 SUCCEEDED; cells at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/`.
  Record in `campaigns/covid/platform_fidelity_01b/LEDGER.md` §5.
- Edison handoff: the collector index on issue #1077 was refreshed
  (2026-11-08, run 42497402462) BEFORE the 01b array ran, so it indexes
  `campaign/covid_platform_fidelity_01/` but NOT
  `campaign/covid_platform_fidelity_01b/`. Dispatch
  `.github/workflows/campaign-collect.yml` with `max_prefixes=250` (the
  default 50 does not reach these prefixes) to make the 01b cells visible;
  every run waits on the owner's aws-campaign approval.

## 7. What is now void

- The PLATFORM-FIDELITY-01 DP row's hull-fidelity interpretation — void
  for that purpose as of this PR (intervention defect; superseded by 01b).
  Recorded in `docs/covid/covid_open_ledger.md` §1 in this change. The
  cells themselves are preserved, not deleted, not re-scored.
- Nothing else. GM rows stand (unaffected by the DP defect), subject to
  the statistical-wording corrections in the 01b addendum §6.

## 8. The decision (RESOLVED 2026-11-08)

**DECIDED (Benjamin, 2026-11-08): commission the larger-seed DP follow-up.**
The corrected DP contrast — lower takeoff probability on the
event-faithful hull, larger outbreaks when takeoff occurs, unresolved at
n = 20 seeds/arm — is decision-relevant enough to resolve. The next stage,
in order, starting from this handoff:

1. **Pre-registered paired-seed power calculation** on the observed 01b
   effect sizes (analysis only, no new cells) to fix the seed count and
   the stopping rule BEFORE any run. Inputs: the 20 proxy + 20 dedicated
   01b cell payloads (S3 prefixes in §6), the readout
   `docs/covid/covid_platform_fidelity_readout.md` §01b, and Edison's
   statistical audit `platform-fidelity-01-statistical-audit-v47d`.
2. **If warranted: a larger-seed DP-only design** (next campaign id),
   pre-registered before any cell runs, reusing the 01b machinery
   (`campaigns/covid/platform_fidelity_01b/`, frozen Θ 7.9e6, extended seed
   set, union protocols file `data/config/protocols_covid_pf_dp_01b.json`).
   Whether the PF-01 proxy cells can be reused at the larger n or both
   arms rerun is settled by the power calculation's equivalence evidence,
   exactly as 01b resolved it. GM stays closed — no GM cells in the
   follow-up.

The options that were on the table (for the record): (a) this — commission
the power calculation and, if warranted, the larger-seed design; (b) close
the line with hull choice as a declared modeling assumption; (c) hand the
decision to Edison with the audit as input. Option (a) was chosen.

## 9. Do not reopen

- The prereg criteria in `docs/covid/covid_platform_fidelity_prereg_v1.md`
  and the 01b addendum: q05–q95 are seedwise spreads, not confidence
  intervals; no platform-equivalence conclusion from an interval crossing
  zero; unconditional onset burden reported alongside the takeoff-
  conditional endpoint; no "small relative to seed noise" conclusion.
- No Θ refit on the faithful hulls; no Θ adaptation to GM outcomes; the
  train/test split stays fixed (DP train, GM held-out, scored once).
- No platform is selected or crowned from this study.
- The 01b union `exempt_work_zones` list is function-matched and frozen —
  do not tune it until the dedicated hull reproduces any particular
  working-crew count; keep the real hull zone IDs (renaming hulls is the
  wrong repair); `SelfLaundry` stays excluded (passenger-facing).
- GM cells are not rerun for the DP defect; GM's protocols file declares
  no `exempt_work_zones` by design.
- USS Theodore Roosevelt is out of bounds as a comparator.
- New campaigns register under `campaigns/covid/<name>/` and submit through
  `scripts/campaign`; images are pinned by digest, never bare tags.
