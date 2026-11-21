# WP1 session prompt — Paper-1 freeze design contract for Edison's pre-freeze review

> **Status:** Session brief. Launched 2026-11-20; the Result section records
> the outcome.

Paste into a fresh Devin session on bckirkup/Crusher_to_the_Bridge. One deliverable,
one session (bounded-research-sessions rule).

```
Paper-1 prepositioning, work package WP1 (context doc:
docs/norovirus/paper1_simulation_plan_assessment_2026_11_20.md — read it first;
WP0 readout: docs/norovirus/wp0_explorer_platform_session_prompt_2026_11_20.md).

Settled inputs (do not re-derive):
- WP0 is merged: explorer_seas_06 platform is on main (merge a175b5c9,
  generated at 695df1b5, 3,245 pax / 1,183 crew, 119 zones, 49 HVAC groups,
  192-epoch smoke passed). The commissioning fold-back is merged (#1349):
  generate_cruise_platform_layout.py emits the Contam commissioning layer and
  scripts/commission_platform_contam.py refills exchange_m3h after
  regeneration. #1351 records that --overwrite followed by the commission
  script is a no-op only for explorer_seas_06 (exchange_m3h is refilled by
  commission_platform_contam.py, not by the generator); the other four
  recipe hulls have small committed diffs — regeneration of them is NOT
  part of the freeze.
- The frozen-block pattern exists: NORO-GENO-02 carried a verbatim frozen
  dose_adjustments/config_overrides block on every cell. Reuse that shape.
- The freeze needs (assessment §"One declared reference version is itself a
  work item"): a named commit, a frozen config block pinning every mode whose
  default has flipped or may flip, a declared limitations list citing the
  open ledger, and a moratorium on mechanism work during evaluation.
- The mode list to pin is enumerated from the tree, not from memory: every
  default-ON refinement mode an artifact must pin — sanitary visit mode,
  flush aerosol fraction, cabin air mode, pathogen pool transport, droplet
  field split, droplet emission mode, room air removal, near-field air,
  contact mode, duty0_terminal_mode, surface_swab_source,
  wastewater_assay_mode, VSP either-channel, shedding variance, cabin-mates —
  plus any others you find by walking config defaults vs the ledger. Each
  pinned key must be verified against the config machinery: the consumer
  that reads the key is named (merge_config_overrides accepts unknown keys,
  so a key that merely parses can be dead), the path resolves, and the
  default value is recorded next to the pinned value.
- Declared limitations cite docs/norovirus/norovirus_open_ledger.md open
  items, including: every dose figure except the refit
  environmental_faecal_release_log10_g_per_epoch (7.57 [7.14, 8.86],
  NORO-DOSE-REFIT-01) is void pending refit; A4/A8/A9 are scored as the
  ledger now defines them, not as the September gate did; SOP-007/009
  close_zones name mega_cruise_5000 zone ids and skip Explorer's galley and
  crew mess (relevant only to response arms on Explorer; WP3 owns the
  decision).
- Named-commit rule from the assessment's Decision item 1: head at freeze
  time is the named reference; Edison's blocker findings gate the freeze.
  The contract proposes the current main HEAD as the candidate SHA and
  states the rule — it does not declare the freeze. The contract requires
  the frozen block's parse check to be re-run on the final named commit at
  freeze time: head may move the config loader between Edison's review and
  the freeze, and the final SHA must not run on a loader he never reviewed.
- Voyage grid: retained 168/288/504 epochs only; 192 is scoped to the
  reconstruction campaign and must NOT appear in the frozen joint-eval grid.

Deliverable (exactly one):
- A committed design contract doc under docs/norovirus/ (name it
  paper1_freeze_design_contract_2026_11_2X.md) carrying: the candidate
  named commit + head-at-freeze rule; the complete frozen config block as
  verbatim JSON (verified keys, default vs pinned value per row); the
  declared limitations list; the moratorium scope (what counts as mechanism
  work vs config/campaign/doc work during evaluation); and a one-page
  evaluation-contract summary for Edison (the six outcome families, paired
  bridge strata quiet/near-threshold/outbreak across the four hulls, seed
  counts per stratum from the assessment, go/no-go reading) so he can judge
  the freeze against what it will be scored on. Status line at top, docs
  index updated (docs/README.md). Open the PR to main; Edison reads it via
  PAT.

Non-goals:
- No freeze declaration (Edison review gates it), no campaign code
  (campaigns/ dirs are WP2+), no mechanism work, no engine default changes,
  no simulation runs beyond the smoke-level parse check below, no Edison
  push ingest.
- Do not modify tests, ledgers, or platform data.

Validation gate before PR:
- Every pinned key in the frozen block resolves against the config
  machinery; the block loads in a smoke-level config parse (whichever
  existing loader path the NORO-GENO-02 block used — verify, don't guess);
  JSON verbatim block is copy-pasteable into a cell spec; pre-commit clean.

Report immediately if:
- A mode that must be pinned cannot be expressed through config_overrides
  (machinery gap — flag it, don't wire a new override path).
- The ledger's open items force a scope change to the evaluation contract.
- Head at freeze time carries unmerged machinery WP0/WP1 depends on.

Stop when: the design-contract PR is merged and this file is updated with a
Result section (candidate SHA, pinned-key count, limitation count, PR
number — commit that update).
```

## Result
