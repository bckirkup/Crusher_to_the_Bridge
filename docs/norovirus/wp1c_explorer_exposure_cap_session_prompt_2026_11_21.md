# Session prompt — Paper 1, WP1-correction: Explorer exposure-cap eligibility

**Status:** Planning — session brief, authored 2026-11-21. Bounded pre-freeze fix required by Edison's review (REVIEW.md required correction 2). One deliverable: the eligibility-correction PR.

Edison's review found the frozen block's exposure-cap request is not effective on `explorer_seas_06`: activation requires the platform identifier in the rhythm/event catalog, which lists the four archetypes but not Explorer. Same requested block → different resolved mechanism on the historical vessel. This must be resolved before the freeze, or Explorer becomes a labelled deferred exception.

## Read first

- `docs/norovirus/edison_freeze_review_2026_11_21/REVIEW.md` — required correction 2 (controlling document).
- `docs/norovirus/paper1_freeze_design_contract_2026_11_20.md` — §2 block and the mechanism list that pins the exposure cap.
- `scripts/paper1_freeze_block_check.py` — resolved-state probe location (currently Expedition-only).
- The rhythm/event catalog code that gates cap activation (find it from the block's consumer; Edison describes it as "rhythm/event catalog").

## Settled inputs (do not re-derive)

- Edison's preferred resolution: "an explicitly reviewed eligibility correction matching the intended cruise-platform scope, with per-hull effective-state assertions and no accidental import of another ship's activity schedule." The alternative — reserving Explorer as a labelled deferred exception — is the fallback only if the eligibility fix cannot be bounded.
- "A nominal platform-class label alone is not a fix" — do not paper over it.
- This is a bounded implementation/configuration issue, not evidence about the cap's epidemiological magnitude. Do not tune any constant.

## Deliverable (exactly one)

One PR: the smallest change that makes the exposure cap's REQUESTED state resolve identically on `explorer_seas_06` and the four archetypes — most likely adding Explorer to the eligibility catalog keyed on platform identity/scope (matching how the four archetypes are declared), NOT copying schedule data from another vessel — plus per-hull effective-state assertions: a test (or checker extension) that resolves the cap state under the frozen block on all five reference hulls and asserts equality. Update `docs/README.md`/ledger if a ledger entry is warranted (resolved-state divergence is a measurement-class discovery — check `docs/norovirus/norovirus_open_ledger.md` convention).

## Non-goals

- No changes to the cap's parameters, schedule, or magnitude — eligibility only.
- No other platforms added to the catalog.
- No freeze declaration, no campaign authoring, no contract edits (WP1b owns those).

## Report immediately if

- The eligibility check gates more than the exposure cap (i.e., adding Explorer flips other mechanism state) — enumerate what flips before writing the fix.
- The catalog carries schedule data Explorer legitimately lacks and the honest fix is a scoped eligibility flag rather than a catalog row — describe both options and pick the bounded one, flagging it in the PR for Edison.

## Validation gate before PR

- New per-hull effective-state assertions pass on all five reference hulls.
- pre-commit, sonar_guard.py, clock_guard.py, ruff, `pytest -m 'not slow'` on touched areas, sanity checker.

## Stop when

The PR is open with the per-hull resolution evidence in its description AND the reviewer's preferred-vs-deferred framing stated for Edison.
