# Paper-1 freeze declaration — 2026-11-21

> **Status:** Declared. Names the Paper-1 reference commit under the
> [freeze design contract](paper1_freeze_design_contract_2026_11_20.md) §1
> after Edison's 2026-11-21 finalization review items landed (#1369).

**Named commit.** `bf0ec16825ed15176fe0362459a72a7be1667f41`

Head of `main` at freeze time: the merge of #1369 (Edison finalization:
runner-added allowlist, expected-state guards, readout completeness). It
supersedes the contract's candidate `b25cb0f22d80dc3118c8613563992f9de28e8e49`
and is the source reference every campaign cell, readout `--expect-sha`,
image build and regenerated specification names.

## Contract §1 conditions

### 1. Checker re-run at the named commit

`python3 scripts/paper1_freeze_block_check.py` run on the named commit:
exit 0 — 0 failures, 1 pending, 0 resolved-state differences from the
no-block default; expected validation rejections 2; conditionally inactive
pins 3; annex matches. Output committed beside this record as
[paper1_freeze_block_check_output_bf0ec168_2026_11_21.txt](paper1_freeze_block_check_output_bf0ec168_2026_11_21.txt).

### 2. Intervening-commit record (candidate → named commit)

Commits between `b25cb0f22d80dc3118c8613563992f9de28e8e49` and the named
commit touching `engines/`, `orchestrator*.py`, `crusher_labs/config.yaml`,
`data/pathogens/` or `data/platforms/`:

| Commit | Statement |
|---|---|
| `70e833b6` EXPO-CAP-01 | **Moves norovirus behaviour, intentionally:** gives the exposure cap its own platform scope (catalogued classes plus `explorer_seas_06` by id) so the frozen block's cap request resolves active on Explorer; rhythm catalog untouched. The checker verifies the cap's effective state on all five hulls. |

All other intervening commits (including #1369's finalization changes, which
touch `campaigns/` and `tests/` only) are outside the scoped paths.

### 3. Image digests

The campaign image was built from the named commit in a clean worktree
(`ENGINE_GIT_SHA=bf0ec16825ed15176fe0362459a72a7be1667f41`), pushed to
`994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign`, and is
referenced by digest in both evaluation campaign specs:

| Campaign | Tag | Digest |
|---|---|---|
| `noro/explorer_reconstruction_01` | `noro-explorer-recon01` | `sha256:354b27b62076cfad6df13de899319d0b55e594a1a1edaf5bc3982bcf4ec55d82` |
| `noro/paper1_joint_eval_01` | `noro-paper1-joint-eval01` | `sha256:354b27b62076cfad6df13de899319d0b55e594a1a1edaf5bc3982bcf4ec55d82` |

Both tags name the same image manifest; the build layers
`deploy/aws/Dockerfile.campaign` on the root `Dockerfile` base, both built
at the named commit.

### 4. Checker output and annex regeneration

The checker's output at the named commit is committed (§1 above). The
example run specifications were regenerated with `--write-annex`; the diff
against the committed annex is **one line** — the Explorer
`rhythm.layer_attached` PENDING reason now reads "declared exception,
contract section 2.8: rhythm-free reference plus a declared rhythm_off
paired arm" in place of "decision open". No resolved-state leaf changed.

### 5. PENDING record

One `PENDING` line remains, held as the declared, labelled exception of
contract §2.8 (Edison 2026-11-21): `explorer_seas_06` has no
SHIP-RHYTHM-02 catalog row, so the unpinned `rhythm.layer_attached` state
diverges from the four catalogued hulls. Resolution: Explorer runs
rhythm-free as its reference state, and the divergence is measured by the
declared `rhythm_off` paired arms on both reconstruction hulls
(`fl_exp_8d_recon_*_rhythm_off`, `fl_meg_8d_recon_*_rhythm_off`), not left
open.

## Configuration-only settings held for execution evidence

Seven pins remain `configuration-only` — asserted as cfg-read, awaiting
execution evidence from the campaigns themselves (Edison finalization
review): `hvac.transport_engine`, `observation.enabled`,
`observation.surface_swab_source`, `variant_surveillance.enabled`,
`escalation.suspect_attack_rate`, `escalation.confirm_attack_rate`,
`escalation.lockdown_attack_rate`. They stay explicitly identified in the
checker output until campaign cell evidence upgrades them.

## Declared approximation approvals

- **Elapsed-time mapping (Explorer reconstruction).** The reconstruction's
  eight labelled dates map one model day each (an inclusive-day
  approximation of the 7-day investigation window); a defensible
  date-to-model-day mapping exists but this approximation is **explicitly
  approved**, with temporal comparators (peak day, crew–passenger lag)
  reported on both the eight-day and first-seven-day windows, and onset
  totals on both. Recorded per the DESIGN timing convention.
- **Introduction count.** The `declared_five` introduction is a labelled
  source-informed assumption: five pre-boarding ill passengers is survey
  evidence of pre-boarding illness, not a manifest count.

## What this freeze gates

Per the contract, evaluation under Paper-1 now requires cells built from
this commit (or a commit verified against it), the pinned image digest
above, and the frozen `config_overrides` block the checker covers. The
moratorium on mechanism work stands; fixes land as new commits and are
recorded against this declaration, never silently.
