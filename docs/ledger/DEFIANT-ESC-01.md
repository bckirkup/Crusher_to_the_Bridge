# DEFIANT-ESC-01
**Date:** 2026-10-06
**Commit:** 19040166
**Pathogens:** influenza_a (mechanism is generic — applies to all order types)
**Status:** measured
**Measured at:** 19040166

Escalation path for the absorbing-defiant refuser flagged by
`docs/ledger/FLU-SVC-RESIDUAL-01.md`: a host whose sticky compliance
class is `defiant` was never re-ordered and never admitted — free and
full-strength symptomatic for the rest of the voyage.

## Rationale (measured/inferred/literature)

- Measured (FLU-SVC-RESIDUAL-01): refused founders at r200 drove a
  free-pool droplet wave in dining venues — refusal is absorbing, no
  refused host is ever re-ordered.
- Literature (Consensus search, 2026-10-06): uniformed/public-health
  presence on Diamond Princess (MOHW quarantine officers, DMAT teams)
  did cabin-door/telephone triage, not compelled removal; **no
  documented case** of physically compelled cabin confinement — but
  equally no documented case of sustained overt refusal. Persistent
  noncompliance is documented *before* orders (symptom concealment;
  Mouchtouri 2024 Eurosurveillance review of 45 norovirus outbreaks)
  and in crew work-exemptions, not as post-order hold-out.
- Legal frame: maritime law compels confinement — captain's authority,
  security posted at the stateroom door, free-pratique denial
  pressuring the line to enforce. A permanently-free refuser is not a
  tenable shipboard state.

## Change

`fred_behavior.defiant_escalation_hours: 24` (Grade C declared bound —
hours of persuasion attempts: door knocks, PA calls, medical visits —
before compelled escort). In `step_fred_compliance` a defiant refuser
whose `epochs_since_order` meets the window is admitted via the
existing `_admit_enforced` path (`enforced_confinement` compliance-log
action). Applies to every refusal the orchestrator tracks —
quarantine, VSP isolation, general confinement all share
`quarantine_refusers`. Reluctant refusers unchanged (own delay/symptom
rules). `0` is the labelled instant-compulsion baseline. Stub
modalities without the attribute read never-compelled — pre-change
behaviour preserved for legacy fixtures.

## Measured — surplus collapse on 8112/8184/8120

Probe re-run on `19040166`, payload `reports/flu_svc_residual_esc01.json`:

| seed | r200_f0 onboard | r100_f0 onboard | surplus |
|------|----------------|-----------------|---------|
| 8112 | 1 (was 51) | 25 (was 24) | -24 (was +31) |
| 8184 | 1 (was 49) | 1 | 0 (was +48) |
| 8120 | 0 (was 11) | 1 | -1 (was +10) |
| pooled | 2 (was 111) | 27 (was 26) | **-25 (was +89)** |

The surplus pool is empty: `a_only` (r200-only infections) is `[]` on
all three seeds — every prior surplus channel is gone, and the
escalated arm now under-runs its own r100 baseline (the dining wave
that ran in *both* arms on 8112 dies in r200 only).

Mechanism fired where FLU-SVC-RESIDUAL-01 said ignition lived — the
enforced confinements land on the named refusing founders:

- 8184 r200: founder **85** refused ep 52 → `enforced_confinement` ep 76
  → onboard 49→1.
- 8120 r200: founders **94** and **121** refused ep 73 → both enforced
  ep 97 → onboard 11→0.
- 8112 r200: founder **255** refused a cascade order ep 53 → enforced
  ep 77 (inside the ep ~102-182 ignition window) → onboard 51→1. The
  other founders were never ordered; one compulsion at the ignition
  seed sufficed, consistent with the lottery framing — part of this
  seed's magnitude is trajectory churn, not a clean single-founder
  story.
- r100 arms enforce too (mechanism is arm-generic): 8112 r100 shows
  `enforced_confinement` on 240@198 and 121@256; its wave still runs
  (25 onboard) because it is fed by founders who are never ordered at
  all — enforcement can only reach hosts the order channel touches.

Verdict: the 24 h hold-out removes the admission lottery's exploding
branch on all three seeds. Refusal is now a short free window, not an
absorbing state; the surplus it generated is eliminated and slightly
overcorrected.

## Bounds and gaps

- The 24 h window is Grade C — declared, not measured. The admission
  lottery is not removed, only shortened: a founder ordered near voyage
  end still holds out the window; order timing is unchanged.
- n=1 replicate per seed; direction consistent on 3/3. The residual
  after escalation (~25 onboard on 8112 r100) is the never-ordered
  founder channel — a detection/`report_scale` question, not an
  enforcement one.
- A `defiant_escalation_hours` sweep axis exists via
  `config_overrides.fred_behavior.defiant_escalation_hours` (0 =
  instant-compulsion baseline) if the tail ever drives a decision.
