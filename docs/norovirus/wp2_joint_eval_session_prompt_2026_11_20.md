# WP2 session prompt — joint four-hull evaluation campaign (authoring leg)

> **Status:** Session brief. Authoring leg may start before the freeze is
> declared (campaign directories are moratorium-allowed work); the canary and
> any cell run are gated on the declared freeze.

Paste into a fresh Devin session on bckirkup/Crusher_to_the_Bridge. One deliverable,
one session (bounded-research-sessions rule).

```
Paper-1, work package WP2 — joint four-hull evaluation campaign authoring.
Read first: docs/norovirus/paper1_simulation_plan_assessment_2026_11_20.md
and docs/norovirus/paper1_freeze_design_contract_2026_11_20.md (the freeze
contract — your campaign carries its §2 block verbatim).

Settled inputs (do not re-derive):
- Frozen block: docs/norovirus/paper1_freeze_design_contract_2026_11_20.md §2
  has the verbatim JSON (delimited by <!-- paper1-frozen-config-block -->);
  every cell carries it as the tier's config_overrides. Loader path verified:
  tiers[*].config_overrides → generate_tier_runs → PicardRunSpec.
  from_picard_dict → merge_config_overrides onto crusher_labs/config.yaml.
- Campaign shape: campaigns/noro/<name>/{campaign.json, design/build.py,
  LEDGER.md} — age_food_01 and food_shapes_01 are the pattern. The
  campaign-preflight skill owns the submission gate; you are not submitting.
- Design (contract §5): four hulls expedition_cruise_450 /
  classic_cruise_1900 / spirit_cruise_3000 / mega_cruise_5000 × three voyage
  lengths 168/288/504 epochs × three bridge strata quiet / near-threshold /
  outbreak, paired seeds, every cell carrying the block verbatim. Explorer
  and the 192-epoch length are NOT in this grid (WP3 only).
- Six outcome families harvested from one run per cell: rep_pax_n/rep_crew_n
  + cumulative_reported_cases_* + census; vsp_trigger_epoch; the seed
  ensemble of both; first-role-to-threshold vs the 0.03 line; daily onset +
  reporting curves (onsets from run.sentinel_line_list, reporting curve from
  the per-epoch cumulative_reported_cases_* series — bucket zero carries
  pre-boarding AGE reports, label it); environmental observables
  (surface_pool_density swabs + holding-tank wastewater).
- Labelled-baseline arms that reproduce a prior draw give a bit-identity
  check of the contract — include them in the design.
- Seed counts per stratum (contract §5): ~20 loud, 100 near-threshold, 300
  quiet (or bound), >=1,000 tail cells. These are proposals Edison reviews;
  the design file records them as the contract's numbers.
- The go/no-go numeric thresholds for "rarely", "post" and "between" are
  YOUR design file's job — the contract explicitly does not set them. Fix
  them in the design file before any cell runs (ci-test-design /
  stochastic-attribution discipline: pre-declared criteria, no fitting to
  anchors).

Deliverable (exactly one):
- campaigns/noro/<name>/ committed: design file (strata, seed grid,
  admissibility/go-no-go criteria fixed up front, outcome-family harvest
  spec), campaign manifest carrying the frozen block verbatim, cell worker
  harvesting all six families from one run, readout script producing the
  go/no-go table, LEDGER.md. Local validation only: design build reproduces
  the manifest, --dry-run count matches the design, a local smoke cell
  proves the block reaches the engine (campaign-preflight's smoke rule —
  small epochs, no array work). PR to main.

Non-goals:
- No array submission, no canary, no cell runs beyond the local smoke. The
  canary (>=20 seeds at one cell) and the bridge readout wait for the
  declared freeze — report "authored and gated" and stop if the freeze is
  not declared during your session.
- No mechanism work, no engine/config.yaml changes, no regeneration of
  platform data, no Edison push.

Validation gate before PR:
- campaign-preflight local gates that apply to authoring: local smoke
  proving the frozen block reaches the engine, --dry-run count matching the
  design file, manifest carries the verbatim block. sanity/tests green on
  the diff, pre-commit clean.

Report immediately if:
- Any of the six outcome families cannot be harvested from one run's
  emitted outputs — that is a machinery gap; flag it, do not wire new
  telemetry silently (new output fields are moratorium-allowed only if they
  draw no randomness; flag before adding).
- The verbatim block cannot be carried through the manifest path.
- The strata cannot be specified without a mechanism change (e.g. the
  stratum knob you need is engine-side).

Stop when: the campaign PR is merged, LEDGER.md committed, and this file's
Result section records the campaign name, cell count, strata definition and
the fixed go/no-go thresholds (commit that update).
```

## Result
