# WP3 session prompt — Explorer temporal-reconstruction campaign (authoring leg)

> **Status:** Session brief. Authoring leg may start before the freeze is
> declared (campaign directories are moratorium-allowed work); cell runs are
> gated on the declared freeze.

Paste into a fresh Devin session on bckirkup/Crusher_to_the_Bridge. One deliverable,
one session (bounded-research-sessions rule).

```
Paper-1, work package WP3 — Explorer-of-the-Seas temporal reconstruction,
campaign authoring. Read first:
docs/norovirus/paper1_simulation_plan_assessment_2026_11_20.md (item 2),
docs/norovirus/paper1_freeze_design_contract_2026_11_20.md (§2 block,
limitation 11), and the WP0 readout
docs/norovirus/wp0_explorer_platform_session_prompt_2026_11_20.md.

Settled inputs (do not re-derive):
- explorer_seas_06 is on main: 3,245 pax / 1,183 crew, 119 zones, 49 HVAC
  groups, commissioned Contam bundle, voyage_config 192 epochs (8 days,
  scoped to this study only — never touch the 168/288/504 grid).
- Empirical target is already transcribed in
  docs/norovirus/mega_voyage_source_evidence.md (snapshot 74a6eff3):
  Feb 26–Mar 5 2006 itinerary, daily onsets — passenger peak Feb 28, crew
  peak Mar 2 (the 2-day lag under test); investigation finals 252/3,245 +
  20/1,183; posting figures 243/3,245 + 19/1,184 for cross-posting
  comparisons. Convention: investigation figures for the curve, posting
  figures for cross-posting.
- Introduction block: five passengers reported pre-boarding illness; CDC
  judged person-to-person propagation; no common dining location among ill
  crew. Declare it, do not fit it. The embarkation-seeded report counter
  (preboarding_reportable_ids) is WANTED here — bucket zero of the
  reporting curve carries the five; label it, don't strip it.
- Comparison archetype: mega_cruise_5000 alongside on paired seeds — but
  mega differs in geometry AND complement, so the readout attributes the
  bundle, not geometry alone (assessment correction; separating the two is
  WP4's contrasts).
- Curve sources: onsets from run.sentinel_line_list (per-person
  onset_epoch + crew flag); reporting curve from per-epoch
  cumulative_reported_cases_{passenger,crew}.
- Frozen block: contract §2 verbatim on every cell.

Deliverable (exactly one):
- campaigns/noro/<name>/ committed: design file (Explorer + mega cells,
  paired seeds, 192 epochs, onset/reporting curve extraction spec, the
  empirical target table with its denominators, comparison metrics —
  peak-day per role, cumulative finals vs investigation figures, the 2-day
  lag), manifest carrying the frozen block, cell worker, readout script
  producing the reconstruction table, LEDGER.md. Local validation: design
  build reproduces the manifest, --dry-run matches, one local smoke run of
  explorer_seas_06 proves the cell spec executes (the WP0 192-epoch smoke
  already proves the platform). PR to main.
- Also record in the design file: (a) the SOP-007/009 decision — closure
  orders name mega zone ids and skip Explorer's galley/crew mess; decide
  whether the reconstruction relies on those SOPs at all, and if aliases
  are genuinely needed flag it as a moratorium-exception decision rather
  than editing protocols.json (mechanism-adjacent); (b) the fruit-cluster
  gate — run the Consensus literature check on whether Rispens et al.
  (AIDAdiva/AIDAluna Sep–Oct 2019) publish per-day onset curves, record the
  verdict and where in the paper; scope a second dedicated hull ONLY if the
  curves exist (Edison's condition).

Non-goals:
- No cell runs beyond the local smoke; the reconstruction campaign itself
  is gated on the declared freeze. No mechanism work, no SOP/protocol
  edits, no platform regeneration, no constant fitting (the reconstruction
  scores the frozen engine against the empirical curves — it does not tune
  to them).
- No second platform build (fruit-cluster hull is out until the gate passes
  and Edison says go).

Validation gate before PR:
- Manifest carries the verbatim block; dry-run count matches design;
  smoke cell completes; the empirical target table's numbers match
  mega_voyage_source_evidence.md exactly (no re-transcription — cite it);
  pre-commit clean.

Report immediately if:
- The SentinelLedger line list cannot emit per-person onset/crew for a
  4,428-agent run under the retention mode the campaign uses — machinery
  gap, flag it.
- The literature check finds the fruit-cluster curves are NOT published —
  that closes the conditional expansion; report the verdict at once.
- Anything in the empirical record can't be declared as a config input
  (e.g. the five pre-boarding ill passengers).

Stop when: the campaign PR is merged, LEDGER.md committed, and this file's
Result section records the campaign name, the SOP decision taken, and the
literature-gate verdict (commit that update).
```

## Result
