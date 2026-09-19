# Devin session retrospective, September 2026

> **Status:** Historical. Operating lessons from three crashed sessions;
> the live rules derived from it are in `.agents/skills/` and the user's
> Devin playbook, not here.

## Sessions

| Session | Span | PRs | Suspensions | End |
|---|---|---|---|---|
| Crusher Norovirus Expeditions (`b7586824…`) | ~7 d | 46 | 25 | crashed |
| Crusher COVID (`87b19c26…`) | ~4 d | 29 | 13 | crashed |
| Crusher Noro2 (`40c2e15c…`) | ~1 d | 4 | 2 | crashed |
| Crusher COVID 2 (`baeb4547…`) | ~14 h | 5+ | — | retired cleanly |

All three crashed sessions did substantial correct technical work. The value
lost was almost entirely at **handoff boundaries** — finding → report,
code → PR, campaign → readout — not in the analysis itself. Session age
(days, dozens of PRs, tens of suspensions) predicted the crash far better
than task difficulty. COVID 2, run with an explicit end state, retired on its
own after committing a handoff record (`../covid/covid_theta_handoff_2026_09_19.md`).

## What went wrong, ranked by cost

1. **Findings not reported before continuing.** Noro2 measured "secondary
   transmission still zero after the disinfection repair, on every route" and
   went on to the next diagnostic instead of stopping to report; the result
   only survived because shell output is kept in the session event stream
   (`../ledger/NORO-DIAG-RECOVER-01.md`).
2. **No end state in the prompt.** Sessions ran until they crashed because
   nothing told them when the deliverable was complete.
3. **Campaigns launched before the seed geometry was validated.** The 3,080
   cell V7 screen was correct and useless: its admissible region was empty
   because `ExplicitSeed` redrew incubation (`../ledger/INDEX-GEOM-01.md`).
   A 40-cell canary at one Theta would have shown this in an hour.
4. **Single-trace conclusions.** Several route-blocker diagnoses rested on
   one seed; several were later overturned.
5. **State only on the VM.** Diagnostic libraries, readouts and interim
   documents lived in `/home/ubuntu` and were lost with the VM. Everything
   that was committed survived.
6. **Diagnostics that never exercised the pathway under test.** The emesis
   diagnostics ran with `emesis_event_count = 0`.

## What to do differently

- **One bounded deliverable per session**, stated in the prompt with an
  explicit stop condition. Retire at ~24 h, ~5 PRs, or the close of a campaign
  stage, whichever comes first.
- **Report on discovery.** A result that changes scope or invalidates an
  earlier conclusion is messaged the moment it is measured, before any further
  work.
- **Ledger file as the handoff medium** (`docs/ledger/<ID>.md`, or the
  pathogen handoff docs). Written *before* retiring; the successor prompt
  points at it and lists what is settled and must not be re-derived.
- **Canary before campaign.** ≥ 20 seeds at one cell, geometry gate checked,
  before an array job is submitted.
- **Paired-seed measurement** for any "this route is blocked" claim; a
  hypothesis from one trace is filed as a hypothesis.
- **Nothing durable in the home directory.** Scripts under `tools/` or
  `picard_framework/runs/`, results in `docs/`, or they do not exist.
- Sequential threads that share one engine (norovirus, SARS-CoV-2) run as
  **sibling sessions coordinated through committed files**, one sidekick each.
  Parent/child fan-out is for genuinely independent work only.

## Lifecycle template

```text
design brief → narrow diagnostic / local smoke → paired-seed measurement
→ implementation → changed-file validation → PR
→ campaign preflight → canary → full campaign → canonical readout
→ user decision → ledger written → session retired
```

## Prompt skeleton

```text
Settled inputs (do not re-derive): …
Deliverable (exactly one): …
Non-goals: …
Validation gate before PR: …
Campaign gate (if any): canary N seeds at one cell, then stop and report.
Report immediately if: …
Stop when: <deliverable> is merged/read out AND <ledger file> is committed.
```

## Recovered evidence

- Norovirus: `../ledger/NORO-DIAG-RECOVER-01.md`.
- SARS-CoV-2: `../ledger/THETA-V7-01.md`, `../ledger/INDEX-GEOM-01.md`,
  `../ledger/DOSE-FRAIL-01.md`, `../covid/covid_theta_handoff_2026_09_19.md`.
