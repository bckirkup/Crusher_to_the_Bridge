# NORO-CASCADE-ARMS-01
**Date:** 2026-11-22
**Commit:** 519c3e97a6ab380f780f32cf92a9df0a53840aca
**Pathogens:** norwalk_gi
**Status:** open

## D1′ verdict

The frozen Paper-1 cruise model has no arm in which a non-shedding carrier
can pass hand contamination directly to another person's hands. The available
`carriers` arm changes eligibility for environmental redeposition. Its
existing witness misses the continuous solver's surface and food deposits.
The comparison stopped at the arm-construction gate.

## Verified in the source

- **Direct donors.** In `engines/transmission_core.py`,
  `_direct_contact_unit` takes donors from `_get_shedders`, which requires
  positive shedding. `_direct_contact_target_dose` samples that list.
  `_per_partner_contact_dose` checks the carrier flag only after the hand
  transfer, when it records the strain on the recipient. Both arms therefore
  have the same direct-donor eligibility rule.
- **Redeposition witness.** The `carriers` override in
  `tools/noro_diag/hand_cascade_witness.py` changes only
  `hand_redeposit_mode`. `CascadeRecorder.wrappers` watches the discrete
  surface and food deposit methods, sanitary deposits, and strain recording.
  The [freeze contract, §2.1](../norovirus/paper1_freeze_design_contract_2026_11_20.md)
  selects the continuous solver and disables sanitary visits. Its
  `_contamination_flow_epoch` passes surface and food rates directly to
  `integrate_hand_flow`, bypassing the two discrete deposit methods.
  A populated strain counter would establish that the wrapper ran. It would
  leave carrier mass through those flow edges unknown.
- **Cell identity.** The named `noro_dose_refit_01_manifest.json` has tiers
  for Spirit, Mega and Expedition only. The classic hull and seeds 8000–8019
  plus 8105/8106 are declared in the [D0 artifact-worker block](../../campaigns/noro/noro_dose_ledger_01/campaign.json).
  `contact_binding_probe.py` selects a manifest tier and hard-codes
  `carriers_ordered`. Passing it the D0 block name cannot select a classic
  voyage. Adapting the worker arguments alone would still leave the
  direct-donor and witness limitations above.

## Measurement and interpretation

**Measured.** No D1′ voyages ran. The one-seed RNG-neutrality check, paired
delivery and secondary counts, and per-cell 10% reporting threshold are all
unevaluated. No Batch canary or array was submitted.

**Inference.** D2′ can proceed as an audit of how the model represents emesis
patches. Its rationale is the patch-dominant D0 finding supplied in the
handoff. The [D0 ledger at the reviewed revision](NORO-DOSE-LEDGER-01.md)
records the declared design and criteria. It contains no numerical readout.

**Hypothesis.** Whether allowing non-shedding hands to act as direct donors
would change delivered mass or secondary cases remains open. The observed
first hop in D0 provides no measured bound on that counterfactual.
