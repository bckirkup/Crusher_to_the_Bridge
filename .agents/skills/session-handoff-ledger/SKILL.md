---
name: session-handoff-ledger
description: When to retire a long Crusher session (older than ~24h, more than ~5 PRs, or a campaign stage just closed), the handoff ledger template that must be committed under docs/ before retiring it — hypothesis, evidence for and against, PRs landed, running jobs with S3 prefixes and Batch job IDs, which previously reported results are now void, and the single open decision — the rule that nothing of value lives only in the conversation or in /home/ubuntu, and the recovery procedure for a session that crashed. Use when a session is getting long, before handing off, or when recovering from a crashed session.
---

# Session handoff ledger

Three Crusher sessions ran for days each, accumulated 29-46 PRs apiece, and
died. The analysis in all three was sound. What was lost was everything that
had not been written into the repository: findings observed in shell output and
never reported, campaign results produced and never written into a canonical
doc, and in each case the next decision, which existed only in the
conversation. This skill exists so that a session's death costs a restart, not
the work.

## Retire the session when any one of these is true

- **Age:** the session is older than about **24 hours**.
- **Volume:** more than about **5 PRs** have landed in it.
- **Stage boundary:** a campaign stage has just closed — the array finished,
  the readout is written, and the next stage is a new design.

Any one is enough; they are not a conjunction. Retiring early is cheap (write
the ledger, open a new session, read the ledger). Retiring late has repeatedly
cost days. `docs/covid/covid_theta_handoff_2026_09_19.md` is the worked
example of a good handoff record — read it before writing your first one.

## The handoff ledger

Write it as a committed Markdown file, `docs/<pathogen>/<topic>_handoff_<YYYY_MM_DD>.md`,
listed in `docs/README.md`, with a status line marking it a handoff record
that reports no new numbers (every figure quoted from the ledger entry or
readout that measured it, with that entry's `Measured at` SHA). Sections, in
this order:

1. **The question.** What is being decided, on what hull, against what
   observables — in enough detail that a successor with no context can restate
   it. Include what would count as success and what would not.
2. **Current hypothesis.** One paragraph. The thing you currently believe and
   would act on.
3. **Evidence for.** Each item with its ledger `<ID>` or readout path and the
   `Measured at` SHA. No number appears here that is not quoted from a
   committed artifact.
4. **Evidence against / unexplained.** The observations that do not fit, the
   diagnostics that came back null, and anything you could not attribute
   (`.agents/skills/stochastic-attribution/SKILL.md`).
5. **PRs landed this session,** in dependency order, each one line: number,
   what it changed, and the ledger entry it belongs to.
6. **Running jobs.** For each: parent AWS Batch array job ID, queue, job
   definition **revision**, image tag *and* digest, the S3 prefix results land
   under, cell count, and expected completion. A running job whose prefix is
   not written down is unrecoverable work.
7. **What is now void.** Every previously reported result invalidated by this
   session's changes, and why — with the same entry/SHA discipline. Update
   `docs/norovirus/norovirus_open_ledger.md` §1 or
   `docs/covid/covid_open_ledger.md` §1 in the same change; that is the live
   record of what is withdrawn, and a successor is required to read it before
   quoting any figure.
8. **The single open decision.** Exactly one. Not a backlog — the one choice
   the next session must make first, with the options and what evidence would
   settle it. If you have three, rank them and state the first.
9. **Do not reopen.** Criteria that may not be loosened, constants that may not
   be tuned to an anchor (`.agents/skills/model-parameter-provenance/SKILL.md`),
   and decisions already made with their reasons.

Then send the user the same thing in a few sentences: state of play, what is
running, the open decision. The ledger is for the successor; the message is
for the person who has to decide.

## Nothing of value lives only in the conversation or in `/home/ubuntu`

This is the rule that all three dead sessions broke.

- **Results:** a number that exists only in shell output is not a result. It
  goes into `docs/ledger/<ID>.md` (header per `docs/ledger/README.md`) or a
  readout under `docs/norovirus/` / `docs/covid/`, committed.
- **Designs and criteria:** into the design/manifest file under
  `picard_framework/runs/mega_cruise_campaign/`, before the run
  (`.agents/skills/campaign-preflight/SKILL.md` Rule A) — and, for a Batch run,
  inside the image.
- **Artifacts:** raw outputs to the S3 prefix; the merged surface committed
  (e.g. `docs/covid/covid_theta_screen_v7_surface.csv`).
- **Scripts:** a probe driver worth keeping goes in the repo; a throwaway must
  be reproducible from commands written into the handoff. Note that repo path
  I/O is confined to the process CWD by `simulation_utils.paths`
  (`tests/test_path_io_inviolate.py`), so `/tmp` is not where work lives
  anyway.
- **Findings:** a finding observed and not reported is indistinguishable from
  one never made. Report it to the user in the session where you see it, and
  write it down in the same change.

The test: *if this box were destroyed right now, what would be lost?* The
correct answer, at all times, is "nothing but the VM". The v7 handoff states
this explicitly for its own session, and that is the standard.

## Recovery from a crashed session

A session whose machine is gone is not a session whose work is gone.

1. **Read the session's event stream, not the box.** Shell output survives in
   the session event stream even when the machine does not. Open the dead
   session and read its events (via the session-inspection tooling) and scroll
   the tool outputs: run counts, attack rates, witness counters, job IDs and
   S3 URIs printed hours before the crash are all still there verbatim. This
   is the part that actually worked in recovery — **numbers can be recovered
   without waking the VM**, and waking it is usually slower and sometimes
   impossible.
2. **Recover the durable state in this order:** merged PRs on `main` (what
   landed); `docs/ledger/` and the open ledgers (what is measured and what is
   withdrawn); the S3 prefixes (raw results); `aws batch list-jobs` /
   `describe-jobs` for anything still running or recently finished; then the
   event stream for anything that was printed but never committed.
3. **Re-derive nothing you can quote.** A number recovered from the event
   stream is quotable only with the commit it was produced at; if you cannot
   establish the SHA, treat it as a lead, re-measure, and say so.
4. **Write the handoff ledger the dead session owed** — same template, in the
   new session, before doing any new work. Mark recovered items as recovered
   and unattributed items as unattributed.
5. **Check for orphaned running jobs** before submitting anything new: an
   array from the dead session may still be burning Spot capacity against a
   prefix you are about to reuse
   (`.agents/skills/campaign-preflight/SKILL.md` step 4).

## Related

- `.agents/skills/campaign-preflight/SKILL.md` — what must be frozen and recorded before a run.
- `.agents/skills/campaign-results-analysis/SKILL.md` — the readout that closes a campaign.
- `docs/ledger/README.md` — entry header, ID grammar, and the drafting order for quoting numbers.
- `docs/covid/covid_theta_handoff_2026_09_19.md` — a handoff record written to this standard.
