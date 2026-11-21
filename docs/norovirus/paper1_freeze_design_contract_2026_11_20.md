# Paper-1 freeze design contract (WP1)

> **Status:** Design contract, **revision 2 (2026-11-21)** — revised in place
> per Edison's pre-freeze review
> ([`edison_freeze_review_2026_11_21/REVIEW.md`](edison_freeze_review_2026_11_21/REVIEW.md),
> reviewed at `73ad8724`). **Not a freeze declaration**; Edison reviews this
> revision and the freeze record is a separate later document. The §2.1 block
> is byte-identical to the reviewed one. Verified on the revision branch
> (main at `fb300d71`, which includes #1359) by `scripts/paper1_freeze_block_check.py`: 57 declared units,
> 70 scalar leaves (63 resolved-state, 7 configuration-only), 0 failures,
> 1 pending (Explorer rhythm-layer attachment, §2.8; the exposure-cap
> divergence was closed by #1359); output retained at
> [`paper1_freeze_block_check_output_2026_11_21.txt`](paper1_freeze_block_check_output_2026_11_21.txt).
> No voyage epoch was stepped and no number in this document is a model
> result. §7 maps each review correction to the section that resolves it; §8
> is the revision history. Context:
> [`paper1_simulation_plan_assessment_2026_11_20.md`](paper1_simulation_plan_assessment_2026_11_20.md).

The assessment's "one declared reference version is itself a work item" asks
for four things: a named commit, a frozen config block, a declared limitations
list, and a moratorium on mechanism work. This file proposes all four and
summarises, in §5, what the frozen reference will be scored on, so the freeze
can be judged against its own evaluation.

## 1. Named commit

**Rule (assessment, Decision item 1).** Head of `main` at freeze time is the
named reference. Edison's blocker findings on this contract gate the freeze;
the freeze is declared only after they are resolved, in a separate commit that
records the SHA.

**Candidate.** `b25cb0f22d80dc3118c8613563992f9de28e8e49` (merge of #1353, a documentation-only change after #1352).
It carries everything WP0/WP1 depend on: the `explorer_seas_06` platform
(merge `a175b5c9`, generated at `695df1b5`), the commissioning fold-back
(#1349) and the regeneration readout (#1351). Nothing WP0/WP1 need is
unmerged. Regenerating the other four recipe hulls is not part of the freeze:
their committed platform files at the named commit are the reference.

**Conditions the freeze declaration must meet.**

1. `python3 scripts/paper1_freeze_block_check.py` is re-run **on the final
   named commit** and exits 0. Head may move the config loader or a consumer
   between this review and the freeze; a check that passed at the candidate
   says nothing about the named commit.
2. Any commit between the candidate and the named commit that touches
   `engines/`, `orchestrator*.py`, `crusher_labs/config.yaml`,
   `data/pathogens/` or `data/platforms/` is listed in the declaration with a
   one-line statement of whether it moves norovirus behaviour.
3. Every campaign image used for evaluation is built from the named commit
   and referenced by digest.
4. The checker's output at the named commit is committed beside the freeze
   record, and the example run specifications (§2.10) are regenerated there
   with `--write-annex`; any diff against the committed annex is listed in
   the declaration.
5. No `PENDING` line remains in that output, or each one is recorded in the
   declaration as a deferred, labelled exception (§2.8).

## 2. Frozen config block

### 2.1 What the block is and how it is carried

The block is a `config_overrides` object, the shape NORO-GENO-02 carried on
every cell. It is the **invariant baseline**: every cell's tier
`config_overrides` starts from it, and an arm changes it only through
prospectively declared paths (§2.9). The loader path, verified rather than assumed, is:

`tiers[*].config_overrides` → `generate_tier_runs`
(`picard_framework/runs/mega_cruise_campaign/campaign_runner.py`) →
`PicardRunSpec.from_picard_dict` → `merge_config_overrides`
(`picard_framework/run_spec.py`) onto `crusher_labs/config.yaml`.

Registered campaigns under `campaigns/noro/<name>/` reach the same path:
`campaign.json` blocks name a tier in a manifest of this shape.

Every pinned value equals what a campaign cell resolves at the candidate
with no block (the check reports 0 keys whose resolved state differs). The
block changes no behaviour; it stops a later default flip from changing it
silently. The one place it departs from `crusher_labs/config.yaml` is
`escalation.lockdown_attack_rate` (§2.2).

<!-- paper1-frozen-config-block -->
```json
{
  "transmission": {
    "contact_mode": "per_partner_contact",
    "droplet_emission_mode": "profile_conditioned",
    "droplet_field_split": {
      "mode": "partition",
      "far_field_share": 0.175,
      "settled_share": 0.0
    },
    "near_field_air": {
      "mode": "two_box",
      "interzonal_airflow_m3_per_hour": 204.0,
      "neighbour_table_ratio": 0.43
    },
    "room_air_removal": {
      "mode": "first_order",
      "map_arm": "ambient_on",
      "default_ach_per_hour": 0.0
    },
    "cabin_air_mode": "cabin_compartment",
    "cabin_cooccupancy": {
      "mode": "time_partitioned"
    },
    "cabin_confined_fomite": {
      "mode": "own_cabin"
    },
    "isolated_quarters_deposits": {
      "mode": "deposits_only"
    },
    "caregiver": {
      "mode": "on",
      "budget_mode": "reallocate"
    },
    "sanitary_visit_mode": "none",
    "flush_aerosol_fraction": 0.0,
    "flush_cabin_emission": true,
    "blackwater_plumbing": true,
    "hand_reservoir_mode": "hygiene_cycle",
    "hand_redeposit_mode": "shedders_only",
    "contamination_solver": "continuous",
    "intra_epoch_causal_order": "legacy",
    "intra_epoch_substeps": 1,
    "high_touch_area_scale": 1.0,
    "dining_party_contact_share": 1.0,
    "contact_class_exponent": 0.0,
    "exposure_cap": {
      "enabled": true,
      "include_fixed_rings": false
    },
    "activity_contacts": {
      "enabled": true,
      "rates_per_hour": {
        "cabin": 0.25,
        "corridor": 0.25,
        "work_service": 2.9,
        "work_other": 0.5,
        "dining_table": 2.0,
        "dining_venue": 2.0,
        "leisure": 1.0,
        "other": 0.0
      }
    },
    "surface_cleaning": {
      "enabled": true,
      "routine": {
        "coverage": 0.37,
        "log10_reduction": 1.29,
        "events_per_day": 1.0
      },
      "outbreak_response": {
        "coverage": 0.58,
        "log10_reduction": 4.29,
        "events_per_day": 24.0,
        "by_zone_class": {
          "cabin": {
            "events_per_day": 1.0
          }
        }
      }
    },
    "common_source": {
      "mode": "on",
      "lot_mode": "object",
      "handler_mode": "object",
      "diner_mode": "object",
      "lot_mint_model": "provisioned_source",
      "titre_draw_mode": "two_mode",
      "lot_extent_mode": "emergent",
      "provisioned_source": {
        "source_id": "generic_cruise_port",
        "lot_layer_mode": "station_lots"
      }
    }
  },
  "hvac": {
    "pathogen_pool_transport": "airflow",
    "duty0_terminal_mode": "extract",
    "passive_link_mode": "bidirectional",
    "transport_engine": "native"
  },
  "observation": {
    "enabled": true,
    "surface_swab_source": "surface_pool_density",
    "wastewater_assay_mode": "holding_tank"
  },
  "service_surface_knockout": {
    "enabled": false
  },
  "crew_duty_exclusion": {
    "enabled": false
  },
  "variant_surveillance": {
    "enabled": false
  },
  "escalation": {
    "suspect_attack_rate": 0.02,
    "confirm_attack_rate": 0.03,
    "lockdown_attack_rate": 0.05
  }
}
```

### 2.2 Merge semantics that constrain every cell

- **The merge is one level deep.** `merge_config_overrides` and the runner's
  `merge_cfg` both replace a second-level key wholesale. A nested block
  (`near_field_air`, `common_source`, `surface_cleaning`, …) therefore carries
  every sub-key it needs, which is why the block restates rates the YAML
  already declares.
- **An arm that varies one sub-key restates the whole nested block.** An arm
  override of `{"transmission": {"common_source": {"mode": "off"}}}`
  drops the other seven frozen `common_source` keys. Cells apply an arm
  by editing a copy of the frozen block, never by layering a partial block
  over it (§2.9).
- **Unknown keys are accepted.** The merge does not validate names, so a pin
  that parses can be dead. The check in §2.4 exists for that reason.
- **The runner adds its own overrides beneath the tier's**:
  `escalation` (0.02 / 0.03 / 0.05), the surveillance strategy's block,
  `initiation.boarding`, and `ship_graph.num_agents`. The block pins
  `escalation` explicitly because `crusher_labs/config.yaml` declares
  `lockdown_attack_rate: never`, so the value otherwise depends on which
  loader built the cell.

### 2.3 Pinned keys — default, pinned value, consumer, evidence

57 declared units covering **70 scalar leaves**. Four units are grouped
dictionaries (`activity_contacts.rates_per_hour`, `surface_cleaning.routine`,
`surface_cleaning.outbreak_response`, `common_source.provisioned_source`);
each of their 17 leaves is listed and checked on its own row.

Two evidence categories, which are not added together:

- **resolved-state (63 leaves).** The engine's own attribute after
  `initialize()` equals the pin, and flipping that one leaf moves it.
- **configuration-only (7 leaves).** `hvac.transport_engine`,
  `observation.enabled`, `observation.surface_swab_source`,
  `variant_surveillance.enabled` and the three `escalation.*` rates. The
  merged config carries the pin and the consumer file names the key; nothing
  is probed, because the key is read inside the epoch loop or, for
  `transport_engine`, the alternate needs the ContamX binary. Runtime
  evidence for these seven comes from the bridge, not from this check.

"Config default" is the merged config with no block (`absent`: the YAML does
not declare it and the engine default applies); "resolved default" is what
the engine resolved with no block. "0 leaves differ from the no-block
default" is a statement about this representation, not a full runtime
behavioural comparison.

Liveness values:

- `live` — the resolved state followed the flip.
- `expected rejection (…)` — the engine refuses the alternate with the
  declared validation message. Two leaves: `contact_mode` (`legacy` is
  refused because `activity_contacts` requires `per_partner_contact`) and
  `intra_epoch_substeps` (`2` requires `intra_epoch_causal_order: ordered`).
- Any other exception during a flip **fails the check** (`UNEXPECTED …`), as
  does a declared rejection that does not occur.
- `conditional: …` — the leaf is read and honoured but cannot move a run
  while another pin holds. Three leaves: `intra_epoch_causal_order` and
  `intra_epoch_substeps` (the continuous solver replaces the discrete
  ordering) and `flush_cabin_emission` (no flush emission at fraction 0.0).
  They are live keys, not independently influential ones.

| Key | Config default | Resolved default | Pinned | Consumer | Evidence | Liveness |
|---|---|---|---|---|---|---|
| `transmission.contact_mode` | `"per_partner_contact"` | `'per_partner_contact'` | `"per_partner_contact"` | `engines/transmission_core.py` | resolved-state | expected rejection (ValueError: activity_contacts requires contact_mode per_partner_contact) |
| `transmission.droplet_emission_mode` | `absent` | `'profile_conditioned'` | `"profile_conditioned"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.droplet_field_split.mode` | `absent` | `'partition'` | `"partition"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.droplet_field_split.far_field_share` | `absent` | `0.175` | `0.175` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.droplet_field_split.settled_share` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.near_field_air.mode` | `absent` | `'two_box'` | `"two_box"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.near_field_air.interzonal_airflow_m3_per_hour` | `absent` | `204.0` | `204.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.near_field_air.neighbour_table_ratio` | `absent` | `0.43` | `0.43` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.room_air_removal.mode` | `absent` | `'first_order'` | `"first_order"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.room_air_removal.map_arm` | `absent` | `'ambient_on'` | `"ambient_on"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.room_air_removal.default_ach_per_hour` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.cabin_air_mode` | `"cabin_compartment"` | `'cabin_compartment'` | `"cabin_compartment"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.cabin_cooccupancy.mode` | `absent` | `'time_partitioned'` | `"time_partitioned"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.cabin_confined_fomite.mode` | `absent` | `'own_cabin'` | `"own_cabin"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.isolated_quarters_deposits.mode` | `absent` | `'deposits_only'` | `"deposits_only"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.caregiver.mode` | `absent` | `'on'` | `"on"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.caregiver.budget_mode` | `absent` | `'reallocate'` | `"reallocate"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.sanitary_visit_mode` | `"none"` | `'none'` | `"none"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.flush_aerosol_fraction` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.flush_cabin_emission` | `absent` | `True` | `true` | `engines/transmission_core.py` | resolved-state | live; conditional: inactive while flush_aerosol_fraction = 0.0 |
| `transmission.blackwater_plumbing` | `true` | `'BlackwaterHoldingTank'` | `true` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.hand_reservoir_mode` | `absent` | `'hygiene_cycle'` | `"hygiene_cycle"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.hand_redeposit_mode` | `absent` | `'shedders_only'` | `"shedders_only"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.contamination_solver` | `absent` | `'continuous'` | `"continuous"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.intra_epoch_causal_order` | `absent` | `'legacy'` | `"legacy"` | `engines/transmission_core.py` | resolved-state | live; conditional: inactive while contamination_solver = continuous |
| `transmission.intra_epoch_substeps` | `absent` | `1` | `1` | `engines/transmission_core.py` | resolved-state | expected rejection (ValueError: intra_epoch_substeps > 1 requires); conditional: inactive while contamination_solver = continuous |
| `transmission.high_touch_area_scale` | `absent` | `1.0` | `1.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.dining_party_contact_share` | `absent` | `1.0` | `1.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.contact_class_exponent` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.exposure_cap.enabled` | `true` | `True` | `true` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.exposure_cap.include_fixed_rings` | `absent` | `False` | `false` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.enabled` | `true` | `'dict'` | `true` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.cabin` | `0.25` | `0.25` | `0.25` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.corridor` | `0.25` | `0.25` | `0.25` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.work_service` | `2.9` | `2.9` | `2.9` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.work_other` | `0.5` | `0.5` | `0.5` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.dining_table` | `2.0` | `2.0` | `2.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.dining_venue` | `2.0` | `2.0` | `2.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.leisure` | `1.0` | `1.0` | `1.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.activity_contacts.rates_per_hour.other` | `0.0` | `0.0` | `0.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.enabled` | `true` | `True` | `true` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.routine.coverage` | `0.37` | `0.37` | `0.37` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.routine.log10_reduction` | `1.29` | `1.29` | `1.29` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.routine.events_per_day` | `1.0` | `1.0` | `1.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.outbreak_response.coverage` | `0.58` | `0.58` | `0.58` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.outbreak_response.log10_reduction` | `4.29` | `4.29` | `4.29` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.outbreak_response.events_per_day` | `24.0` | `24.0` | `24.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.surface_cleaning.outbreak_response.by_zone_class.cabin.events_per_day` | `1.0` | `1.0` | `1.0` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.mode` | `absent` | `'on'` | `"on"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.lot_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.handler_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.diner_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.lot_mint_model` | `"provisioned_source"` | `'provisioned_source'` | `"provisioned_source"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.titre_draw_mode` | `absent` | `'two_mode'` | `"two_mode"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.lot_extent_mode` | `absent` | `'emergent'` | `"emergent"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.provisioned_source.source_id` | `"generic_cruise_port"` | `'generic_cruise_port'` | `"generic_cruise_port"` | `engines/transmission_core.py` | resolved-state | live |
| `transmission.common_source.provisioned_source.lot_layer_mode` | `absent` | `'station_lots'` | `"station_lots"` | `engines/transmission_core.py` | resolved-state | live |
| `hvac.pathogen_pool_transport` | `"airflow"` | `'airflow'` | `"airflow"` | `engines/py_contam_bridge.py` | resolved-state | live |
| `hvac.duty0_terminal_mode` | `absent` | `'extract'` | `"extract"` | `engines/py_contam_bridge.py` | resolved-state | live |
| `hvac.passive_link_mode` | `absent` | `'bidirectional'` | `"bidirectional"` | `engines/py_contam_bridge.py` | resolved-state | live |
| `hvac.transport_engine` | `"native"` | `cfg-read` | `"native"` | `engines/py_contam_bridge.py` | configuration-only | cfg + consumer read |
| `observation.enabled` | `true` | `cfg-read` | `true` | `picard_framework/simulation/ship_simulation.py` | configuration-only | cfg + consumer read |
| `observation.surface_swab_source` | `"surface_pool_density"` | `cfg-read` | `"surface_pool_density"` | `orchestrator_epoch.py` | configuration-only | cfg + consumer read |
| `observation.wastewater_assay_mode` | `"holding_tank"` | `'WastewaterHoldingTankAssay'` | `"holding_tank"` | `orchestrator_init.py` | resolved-state | live |
| `service_surface_knockout.enabled` | `false` | `False` | `false` | `engines/transmission_core.py` | resolved-state | live |
| `crew_duty_exclusion.enabled` | `false` | `False` | `false` | `picard_framework/simulation/ship_simulation.py` | resolved-state | live |
| `variant_surveillance.enabled` | `false` | `cfg-read` | `false` | `picard_framework/simulation/ship_simulation.py` | configuration-only | cfg + consumer read |
| `escalation.suspect_attack_rate` | `0.02` | `cfg-read` | `0.02` | `orchestrator_init.py` | configuration-only | cfg + consumer read |
| `escalation.confirm_attack_rate` | `0.03` | `cfg-read` | `0.03` | `orchestrator_init.py` | configuration-only | cfg + consumer read |
| `escalation.lockdown_attack_rate` | `0.05` | `cfg-read` | `0.05` | `orchestrator_init.py` | configuration-only | cfg + consumer read |

Consumer detail for the keys the assessment and the WP1 brief named:
`sanitary_visit_mode`, `flush_aerosol_fraction`, `cabin_air_mode`,
`droplet_field_split`, `droplet_emission_mode`, `room_air_removal`,
`near_field_air` and `contact_mode` are each read by a dedicated parser in
`engines/transmission_core.py`; `pathogen_pool_transport`,
`duty0_terminal_mode` and `passive_link_mode` by `parse_*` functions in
`engines/py_contam_bridge.py`; `surface_swab_source` by
`orchestrator_epoch.py`; `wastewater_assay_mode` by `orchestrator_init.py`.
"Cabin-mates" is three keys: `cabin_cooccupancy`, `cabin_confined_fomite`
and `isolated_quarters_deposits`.

### 2.4 Verification

```bash
python3 scripts/paper1_freeze_block_check.py               # exit 0 required
python3 scripts/paper1_freeze_block_check.py --markdown    # regenerates §2.3 rows
python3 scripts/paper1_freeze_block_check.py --write-annex # regenerates §2.10
```

The script reads the block (§2.1) and the population block (§2.7) out of this
file and builds cells through the NORO-GENO-02 path, so everything is checked
on the cell **after the runner has applied its axes** (escalation, strategy,
boarding, `ship_graph.num_agents`). It steps no epoch.

| Check | Scope | Fails when |
|---|---|---|
| Merged config carries each pin | 70 leaves, all five hulls | any leaf differs after the runner's axes |
| Consumer file names the key | 70 leaves | the key string is absent |
| Resolved state equals the pin | 63 leaves, **all five hulls** | any hull resolves another value, unless declared pending |
| Flip moves resolved state | 63 leaves, Expedition | state does not move, an undeclared exception is raised, or a declared rejection does not occur |
| Grouped dictionaries complete | 4 units, 17 leaves | a pinned leaf has no probe, or a probe has no pinned leaf |
| Platform-gated state the block does not pin (rhythm-layer attachment) | all five hulls | a hull differs from Expedition, unless declared pending |
| Declared role counts | all five hulls, both allocations | initialized passengers, crew or class counts differ from §2.7 |
| Example run specifications | all five hulls | the committed annex differs from the generated cells |

Flips run on Expedition only: liveness is a property of the parser, and the
one pin whose effect is gated on the platform is covered by the per-hull
resolved-state probe. A `PENDING` line is a declared, known non-effective
pin; it does not fail the check, and an entry that stops reproducing does.

Result on the revision branch (main at `fb300d71`): 0 failures, 1 pending, 0
leaves differing from the no-block default. The verbatim output is
[`paper1_freeze_block_check_output_2026_11_21.txt`](paper1_freeze_block_check_output_2026_11_21.txt).
`tests/test_paper1_freeze_block_check.py` covers the exception
classification with initialization replaced (no simulation built).

### 2.5 Frozen outside `config_overrides`

These are part of the reference but cannot be, or are not, carried in the
block. The first two are named modes the WP1 brief asked to pin.

| Item | Where it lives | How it is frozen |
|---|---|---|
| VSP either-channel rule (`VSP-EITHER-CHANNEL-01`) | Unconditional code: `campaign_execution.py` (`vsp_trigger_epoch`), `score_anchors.py`. **No config key exists.** | Named commit only |
| Shedding variance | Profile key `shedding_variance_log10` = 1.0 on `norwalk_gi` (`data/pathogens/active_profiles.json`), read in `engines/infection_dynamics_bridge.py` | Named commit; a cell that must restate it uses `pathogen_overrides`, not `config_overrides` |
| Dose | `environmental_faecal_release_log10_g_per_epoch` 7.57 (profile `dose_adjustment`) | Tier `dose_adjustments: [7.57]` on every cell |
| Airborne emission arm | Profile key `airborne_emission_mode: emesis_conditioned` | Named commit |
| Pathogen bundle | `active_profiles`, `norwalk_gi`, `overrides.remove: ["sars_cov2_resp"]` | Manifest `pathogen_configs`, verbatim from NORO-GENO-02 |
| Natural-history clock | `hours` | Manifest `natural_history_clock` |
| Hulls and role counts | Four archetypes plus `explorer_seas_06`; passenger and crew counts in §2.7 | Tier `platform` / `num_agents` and exact `ship_graph.agent_classes` counts; platform files at the named commit |
| Recognition and reporting | `syndromic_comp65`, the reported-case counters and `syndromic` settings (§2.6 item 3) | Restated on every cell; resolved values in the annex (§2.10) |
| Introduction | `initiation.boarding` as the runner generates it for the cell's boarding rung | Recorded per cell; the rung is a declared axis (§2.9) |
| Output requests | `run.sentinel_line_list`; compact retention plus the environmental panel (§5.1) | Set by the cell worker; not a config override |
| Voyage grid (joint evaluation) | **168 / 288 / 504 epochs** (7 / 12 / 21 days) | Tier `epoch_durations`. 192 epochs belongs to the Explorer reconstruction (WP3) only and is not a joint-evaluation length |
| Hash seed | `PYTHONHASHSEED=1` | **Worker-side pin.** The campaign's `entry.py` `build_argv` hook sets it in the entrypoint's environment before `campaign_entrypoint` spawns the worker, as the supply-solver screens do. No shared job definition or campaign image sets it (corrected from revision 1, which said the job definition did), so a campaign without the hook runs with a random hash seed |

Neither of the first two is a machinery gap that blocks the freeze, and no
new override path is proposed. They are recorded so that nobody reads the
block as pinning them.

### 2.6 Affirmed baseline decisions

Edison's review affirms these four without reopening mechanism work. They are
recorded as decisions, not open questions.

1. **Sanitary visits `none`, flush aerosol `0.0`.** The shipped defaults stay
   as the baseline. A sourced alternative is a later declared comparison
   (§2.9); no value is chosen to obtain an outcome.
2. **Escalation 2% suspected / 3% confirmed / 5% lockdown.** These are the
   campaign runner's values (`_CAMPAIGN_ESCALATION_DEFAULTS`), which every
   norovirus campaign ran under. `crusher_labs/config.yaml` declares
   `lockdown_attack_rate: never` for small smokes, so a cell built by another
   loader would differ; the block pins all three so the loader does not
   decide. The complete effective `escalation` object, including decision
   latency and sick-call thresholds, is in the annex (§2.10).
3. **`syndromic_comp65` is the usual-recognition baseline**, restated on
   every cell: `diagnostic_cascade.enabled: false`, quarantine compliance
   0.65 with `compliance_by_class` crew 0.65, `passenger_elderly` 0.54,
   `passenger_young` 0.34. The baseline also includes the upstream settings
   that the hard-coded either-channel aggregation does not freeze:
   - the eight `ship_graph.infection_counters`, in particular
     `passenger_reported_case_rate` and `crew_reported_case_rate` (metric
     `reported_case_rate`, role filter, threshold 0.03, `on_exceed:
     confine_symptomatic`);
   - `counter_confinement_enabled: true`;
   - the `syndromic` block (sick-call probability 0.70 per day, detection
     delay 0 h, background noise 0.015).

   These are not in the §2.1 block; they are `crusher_labs/config.yaml`
   values at the named commit, and the annex records what each hull resolves.
   The response demonstration (WP5) declares its changes against them (§2.9).
   Recorded, not changed: `passenger_young` is not one of the seven
   initialized class ids.
4. **Generic registry source and station-lot formulation.**
   `source_id: generic_cruise_port`, `lot_layer_mode: station_lots`. The
   values the source resolves (`q_source` [0.00086, 0.0047] and the per-line
   prevalences in `data/config/provisioning_sources.json`) and the boarding
   block are saved in each hull's example specification (§2.10). The
   supply-solver screen rungs (`q_source` override, station pin, venue arm)
   remain screen arms. Selected-seed diagnostic strata and
   population-weighted voyage inference are different analyses and are not
   pooled.

### 2.7 Reference populations — declared role counts

The reference states passenger **and** crew counts for every scenario. They
are the platform's `nominal_complement`, delivered as exact per-class
`count` entries in `ship_graph.agent_classes` (the engine's
`_allocate_class_counts` facility), not as fractions.

| Hull | Agents | Reference passengers / crew | Template-fraction allocation (labelled baseline) |
|---|---:|---:|---:|
| `expedition_cruise_450` | 450 | 300 / 150 | 316 / 134 |
| `classic_cruise_1900` | 1,910 | 1,350 / 560 | 1,338 / 572 |
| `spirit_cruise_3000` | 3,000 | 2,100 / 900 | 2,100 / 900 |
| `mega_cruise_5000` | 7,000 | 5,000 / 2,000 | 4,900 / 2,100 |
| `explorer_seas_06` | 4,428 | 3,245 / 1,183 | 3,102 / 1,326 |

- **Why the template drifts.** With no class counts, the YAML's seven class
  fractions (passenger 0.50 / 0.10 / 0.10, crew 0.10 / 0.05 / 0.10 / 0.05)
  take precedence over `passenger_fraction`, each class is floored, and the
  remainder goes to the first class. Every norovirus campaign to date ran
  that allocation. Both columns were measured on initialized agents by the
  checker and match Edison's static arithmetic.
- **Explorer uses the investigation counts exactly**: 3,245 passengers and
  1,183 crew.
- **Within-role class allocation is declared**, not fitted: each role's count
  is split in the template's within-role ratio (passengers 5 : 1 : 1 general
  / family / elderly; crew 2 : 1 : 2 : 1 general / medical / engineering /
  galley) by largest remainder, ties to declaration order. The resulting
  class counts are in the block below.
- **Labelled baseline.** `archetype_template_baseline` is the allocation the
  earlier campaigns used. A bridge arm that reproduces a prior draw omits
  the class counts and is labelled with this name; it is a declared arm
  (§2.9), not the reference.
- **Asserted, not assumed.** The checker asserts both allocations on
  initialized agents on all five hulls. Every outcome payload must carry the
  same counts: `passenger_complement` / `crew_complement` in the run summary
  and `n_passengers` / `n_crew` in the Sentinel line list equal the declared
  reference counts, or the cell fails technical completion (§5.3).
- **Open reconciliation with WP2.** The WP2 design merged while this
  revision was in review
  (`campaigns/noro/paper1_joint_eval_01/DESIGN.md`) declares the
  template-fraction allocation (316 / 134, 1,338 / 572, 4,900 / 2,100) as
  its intended counts and treats nominal as a baseline change. That is this
  section's `archetype_template_baseline`, not its reference. One of the two
  documents changes before the freeze is declared; which one is a decision
  for Benjamin and Edison, and neither is run as "the reference" until then.
- **Explorer against the mega archetype (WP3).** Retained differences: total
  complement, role split and vessel geometry. Controlled: within-role class
  ratios, the §2.1 block, strategy, dose and source. WP3 states this in its
  design and owns the date-to-epoch convention.

<!-- paper1-reference-population -->
```json
{
  "class_template": "crusher_labs/config.yaml ship_graph.agent_classes",
  "within_role_allocation": "template_fraction_ratio_largest_remainder",
  "hulls": {
    "expedition_cruise_450": {
      "num_agents": 450,
      "reference": {
        "passenger": 300,
        "crew": 150,
        "class_counts": {
          "passenger_general": 214,
          "passenger_family": 43,
          "passenger_elderly": 43,
          "crew_general": 50,
          "crew_medical": 25,
          "crew_engineering": 50,
          "crew_galley": 25
        }
      },
      "archetype_template_baseline": {
        "passenger": 316,
        "crew": 134
      }
    },
    "classic_cruise_1900": {
      "num_agents": 1910,
      "reference": {
        "passenger": 1350,
        "crew": 560,
        "class_counts": {
          "passenger_general": 964,
          "passenger_family": 193,
          "passenger_elderly": 193,
          "crew_general": 187,
          "crew_medical": 93,
          "crew_engineering": 187,
          "crew_galley": 93
        }
      },
      "archetype_template_baseline": {
        "passenger": 1338,
        "crew": 572
      }
    },
    "spirit_cruise_3000": {
      "num_agents": 3000,
      "reference": {
        "passenger": 2100,
        "crew": 900,
        "class_counts": {
          "passenger_general": 1500,
          "passenger_family": 300,
          "passenger_elderly": 300,
          "crew_general": 300,
          "crew_medical": 150,
          "crew_engineering": 300,
          "crew_galley": 150
        }
      },
      "archetype_template_baseline": {
        "passenger": 2100,
        "crew": 900
      }
    },
    "mega_cruise_5000": {
      "num_agents": 7000,
      "reference": {
        "passenger": 5000,
        "crew": 2000,
        "class_counts": {
          "passenger_general": 3572,
          "passenger_family": 714,
          "passenger_elderly": 714,
          "crew_general": 667,
          "crew_medical": 333,
          "crew_engineering": 667,
          "crew_galley": 333
        }
      },
      "archetype_template_baseline": {
        "passenger": 4900,
        "crew": 2100
      }
    },
    "explorer_seas_06": {
      "num_agents": 4428,
      "reference": {
        "passenger": 3245,
        "crew": 1183,
        "class_counts": {
          "passenger_general": 2318,
          "passenger_family": 464,
          "passenger_elderly": 463,
          "crew_general": 395,
          "crew_medical": 197,
          "crew_engineering": 394,
          "crew_galley": 197
        }
      },
      "archetype_template_baseline": {
        "passenger": 3102,
        "crew": 1326
      }
    }
  }
}
```

### 2.8 Effective mechanism state per hull

A pin is *requested* in the block and *effective* only if the engine resolves
it on that hull. The checker probes all 63 resolved-state leaves on every
reference hull.

**Explorer exposure cap — resolved by WP1c.** The block requests
`transmission.exposure_cap.enabled: true`. Until #1359 the engine activated
the cap only for platforms in the rhythm/event catalog, which Explorer is
not in, so the same block gave a different state on the historical vessel.

| Hull | Cap requested | Effective at `af0640d4` | Effective at `70e833b6` (#1359) |
|---|---|---|---|
| Four archetypes | true | true | true |
| `explorer_seas_06` | true | **false** | true |

#1359 gives the cap its own platform scope
(`platform_in_exposure_cap_scope`: the catalogued classes plus
`explorer_seas_06` by id) and leaves the rhythm catalog untouched, so no
other ship's schedule is imported. The checker now requires the cap
effective on all five hulls. Ledger: `NORO-EXPOCAP-EXPLORER-01`. An Explorer
run made before `70e833b6` with the cap requested is a cap-off measurement.
This was a configuration-state finding; it says nothing about the size of
the cap's epidemiological effect.

**Explorer rhythm layer — open, decision for Edison.** WP1c found a second
divergence the review did not name. The four archetypes initialize with the
SHIP-RHYTHM-02 schedule layer attached; `explorer_seas_06` initializes with
none, because it has no catalog row. `crusher_labs/config.yaml` declares
`rhythm.enabled: true` and the §2.1 block has no `rhythm` key, so the block
neither requests nor records this state.

| Hull | Rhythm layer attached |
|---|---|
| Four archetypes | yes |
| `explorer_seas_06` | **no** |

The checker asserts attachment on every hull against Expedition's state and
carries Explorer as a declared `PENDING` entry, which fails once it stops
reproducing. The contract does not choose; the options are:

| Option | What it takes | Consequence |
|---|---|---|
| A. Explorer gets its own rhythm catalog row | A transcribed 2006 Explorer day program and venue map; mechanism-adjacent data work, separately reviewed | Same mechanism on all five hulls; no schedule imported from another ship |
| B. Rhythm-free reference | Add `rhythm.enabled: false` to the §2.1 block for all five hulls | Same mechanism on all five hulls, but the archetypes move off the shipped default (`rhythm.enabled: true`), **and it is a §2 block change that restarts this review** |
| C. Labelled deferred exception | Record Explorer as rhythm-free in the freeze record | Archetype reference is unchanged; Explorer's comparison with the mega archetype carries a declared mechanism difference in addition to population and geometry |

Until the decision is recorded, Explorer's same-mechanism comparison is
**reserved**: no Explorer cell runs as a reference cell. Attaching an
existing class's catalog to Explorer is not an option; it is the schedule
import the review ruled out.

**Unregistered source ids are accepted.** A `source_id` absent from the
registry initializes without error and resolves no registry values. The
annex therefore records the registry entry each hull resolved, and the
checker fails if the pinned id is not registered.

### 2.9 Invariant baseline and declared arm differences

The §2.1 block, the §2.5 items, the §2.6 decisions and the §2.7 reference
counts are the **invariant baseline**. The planned work includes
supply-structure, uncertainty, response, population and labelled-baseline
arms that change settings on purpose. Those are declared differences, not
default changes.

Every arm, in its design file and before any of its cells runs:

1. **Retains the baseline reference**: names this contract and the named
   commit.
2. **Declares its changed paths**: a list of dotted paths with baseline and
   arm value. Nothing outside the list may differ.
3. **Materializes complete effective nested objects.** Both merges are one
   level deep (§2.2), so a changed second-level object is written out whole.
   The runner adds its own objects after the tier's — `escalation`, the
   strategy's `diagnostic_cascade` and `fred_behavior`, `initiation.boarding`,
   `ship_graph.num_agents` — and a later generated override replaces a tier
   value at the same key.
4. **Records the resolved effective configuration** of each cell in its
   archive: the generated run specification and, for one cell per arm and
   hull, the resolved record in the annex's shape (§2.10).
5. **Validates after the runner has applied every axis**: the generated
   cell, not the tier block before generation, is compared with baseline
   plus declared paths. The checker's per-hull comparison is the template.

A difference in an approved arm is not an undeclared default change. A
difference outside an arm's declared paths fails the cell. An **unplanned
biological change restarts the reference/version decision** (§4).

Axes a design declares rather than inherits: voyage length, boarding rung
and the resulting `initiation.boarding` block, seed stratum, and population
allocation (reference counts or `archetype_template_baseline`).

### 2.10 Annex — example run specification per hull

[`paper1_reference_run_specs_2026_11_21.json`](paper1_reference_run_specs_2026_11_21.json)
holds one complete example cell for each of the five hulls, generated by the
checker (`--write-annex`) and compared with the generated cells on every
check run.

| Part | Content |
|---|---|
| `run_spec` | The run specification as the runner emits it after all axes: platform, bundle, seed, epochs, `pathogen_overrides`, full `config_overrides` (block, class counts, escalation, strategy, boarding), `campaign_parameters`, and the `run.sentinel_line_list` output request |
| `resolved.population` | Passengers, crew and class counts of the initialized agents |
| `resolved.introduction` | Effective `initiation` block |
| `resolved.reporting` | Infection counters, `counter_confinement_enabled`, `syndromic`, complete `escalation` |
| `resolved.strategy` | `syndromic_comp65`, complete effective `fred_behavior`, cascade state |
| `resolved.source` | Source id, lot layer, prevalence scale, preparation-survival mode, registry `q_source` values |
| `resolved.pathogen` | `norwalk_gi` dose adjustment 7.57, shedding variance, airborne emission arm |
| `resolved.mechanism_state` | All 63 resolved-state leaves as the engine holds them |
| `resolved.unpinned_platform_state` | Platform-gated state the block does not pin (rhythm-layer attachment) |
| `resolved.pending_effective_state` | Declared divergences (Explorer only) |

Conventions: archetype examples use 168 epochs (288 and 504 differ only in
`run.num_epochs`); Explorer uses 192, whose calendar convention WP3 owns.
The example boarding rung is `reportable`, seed 8105.
`campaign_parameters.engine_git_sha` is written as `<named commit>` and the
line-list path as `<run_dir>/…`, since both are filled at run time.

## 3. Declared limitations

Each item cites `norovirus_open_ledger.md` (section or stamp) or the document
that records it. The count is 13.

1. **Dose figures are dispositioned by version, not voided as a class.**
   The ledger's dose stamp (§1, "Every dose figure in this repository is
   void") withdraws figures measured **before** `NORO-DOSE-REFIT-01`
   (2026-09-27); the refit replaced the normaliser with
   `dose_adjustment` 7.57 [7.14, 8.86]. That amendment predates the November
   focal experiments. Results after it stand
   as development evidence at their producing commit and configuration unless
   a specific ledger stamp withdraws them (items 7 and 10).
2. **A4, A8 and A9 are scored as the ledger now defines them**, not as the
   September gate did. A4 is the reported passenger attack rate conditional
   on a posted outbreak, against the hull-class IQR. A8 and A9 are
   mixture-level anchors (`ANCHOR-MIXTURE-01`): reported-case incidence over
   every run's travel-days, and posting probability under the 3%
   passenger-or-crew rule on eligible voyages, scored over a heterogeneous
   voyage ensemble and never over a cell of identical voyages (§2).
3. **The #37 feasibility-gate verdict is not a current result.** "0 of 256
   admissible" was measured on a structure that is no longer run and may not
   be cited as evidence about the frozen reference (§1).
4. **The quiet/outbreak mixture is unmeasured at scale on the current
   engine.** `SYMP-EFF-01` supplies the term the September gate lacked; its
   effect on the mixture has not been measured (§4 item 0; assessment). This
   is the risk the bridge exists to resolve.
5. **Post-2020 scoring is partly unavailable.** The only MIDRS incidence
   analysis covers 2006–2019, and post-2020 classic and mega cells are
   withheld from A4 for insufficient postings. A pre-era A8 match plus a
   post-era A4 match is the most that can be claimed (§2).
6. **A5 is quoted per era.** The passenger/crew ratio is a range (about
   2.9–3.5) and falls by about a third across the COVID break; a pooled A5
   is an average of two ratios (§2).
7. **Flush aerosolisation has no current measurement.** Every flush-sweep
   result is withdrawn as a current-engine figure, and the block pins the
   route off (§1; §4 items 42, 49, 51).
8. **Inputs held fixed by assumption** (§5): route weights (the largest
   unsourced input), `shedding_duration_days` 15 within [12, 30],
   `HIGH_TOUCH_AREA_M2`, the emesis aerosol fraction interval with no point
   selected, confinement attenuation 0.05, and `immunocompromised_fraction`
   0.05 within [0.02, 0.074].
9. **Food-route signature is thin.** `NORO-FOOD-SCORE-01` records a
   posted-conditional passenger attack rate below the recovery edge and
   under-conversion of classic and spirit excursions to posting (§4).
10. **Specific earlier withdrawals remain specific.** Results before
    `COMPLEMENT-01` belong to no ship class; arrival prevalences and posting
    rates before `ARRIVE-01` are withdrawn; caregiver-adjacent readings
    before `CAREGIVER-V1` are a labelled baseline (§1). Each applies to the
    mechanism and versions its stamp names and to nothing else. Old
    campaigns are kept as version-specific evidence. The bridge measures
    transfer to the new reference; it does not restore, erase or re-run a
    historical output by declaration, and claims about the new reference
    rest on fresh measurements.
11. **SOP-007/009 `close_zones` name `mega_cruise_5000` zone ids** and skip
    Explorer's galley and crew mess. This affects only response arms run on
    Explorer; WP3 owns the decision
    ([WP0 readout](wp0_explorer_platform_session_prompt_2026_11_20.md)).
12. **Two reference properties have no config pin** (§2.5): the VSP
    either-channel rule and the shedding variance are fixed by the named
    commit alone.

13. **`explorer_seas_06` runs without the SHIP-RHYTHM-02 layer** that the
    four archetypes run with, and the block does not pin it (§2.8,
    `NORO-EXPOCAP-EXPLORER-01`). Explorer's same-mechanism comparison waits
    on the decision recorded there. The exposure-cap divergence on the same
    hull was closed by #1359.

None of these forces a change to the evaluation contract in §5. Items 2 and
5 limit what a pass can claim; item 4 is what the bridge measures.

## 4. Moratorium

**Scope.** The moratorium protects the **named reference and its effective
configuration**, from the freeze declaration for as long as evaluation cells
are run against it. It is not a repository-wide stop: unrelated work
continues on other revisions, and evaluation images are built from the named
commit by digest, so later commits on `main` do not reach them.

| Change | Status |
|---|---|
| Work on other revisions that no evaluation image is built from, including other pathogens and tooling | Allowed |
| New `campaigns/noro/<name>/` directories, manifests, cell workers, readouts; analysis code that reads archives; ledger entries, documents, tests, CI | Allowed |
| New telemetry or output fields that change an archive's metadata or contents but not its scientific outputs | Allowed; **not new biology**. Checked by scientific-output neutrality (same seed, same outcome families) and recorded with its version |
| A declared arm difference (§2.9) | Allowed; it is an experiment, not a default change |
| An unplanned change that moves norovirus scientific output: `engines/`, `orchestrator*.py`, `crusher_labs/`, `picard_framework/simulation/`, a default, a `data/pathogens/` profile, the five platforms' data, the scoring definitions of A1–A9, a value in the frozen block | Creates a **new reference**. Recorded in the ledger, the named commit moves, §1's conditions are re-met, and every cell already run gets an explicit disposition: re-run, or labelled as measured at the earlier reference |

A change is scientific-output-moving if the same seed can produce different
outcome-family values after it. When that cannot be decided by reading the
diff, the test is a paired-seed run of one bridge cell before and after.

## 5. Evaluation contract — summary for Edison

### 5.1 Output contract — six outcome families

An ordinary compact campaign cell does not collect all six. The worker
contract is therefore explicit.

| Family | Source | What the cell worker must request |
|---|---|---|
| Routine and reported burden, by role | Run summary: `rep_pax_n` / `rep_crew_n`, `cumulative_reported_cases_*`, `passenger_complement` / `crew_complement`, census | Compact record (default) |
| Reaching the reporting threshold | `vsp_trigger_epoch` (either channel at 3% of that role's complement) | Compact record |
| Outbreak-size distribution and tails | Seed ensemble of the two above | Compact record |
| First role to threshold | Derived from per-epoch `cumulative_reported_cases_{passenger,crew}` and the role complements (states below) | Compact record with the per-epoch role series retained |
| Daily onset and reporting curves | Clinical onsets from the Sentinel line list; reporting from the per-epoch role series | **`run.sentinel_line_list` set explicitly** |
| Environmental observables | Surface swab (`surface_pool_density`) and holding-tank wastewater assay records | **Environmental panel** (below) |

**Sentinel line-list request.** The runner arms the line list only when
shore exposure or `variant_surveillance` is enabled, and the block pins
`variant_surveillance.enabled: false`. The worker sets
`run.sentinel_line_list` on the run specification itself; no mechanism is
switched on to obtain a field. The line list survives compact retention.

**First role to threshold.** For each role, the crossing epoch is the first
epoch at which cumulative reported cases divided by that role's complement
reaches 0.03. Five states, each cell in exactly one:

| State | Definition |
|---|---|
| `passenger_first` | Passengers cross, and crew cross later or not at all |
| `crew_first` | Crew cross, and passengers cross later or not at all |
| `same_epoch` | Both roles cross in the same epoch; a tie is not broken |
| `neither` | Both series are complete over the observation window and neither crosses |
| `missing` | Either role series or either role denominator is absent or incomplete; never coerced to `neither` |

Both crossing epochs are recorded. The first crossing triggers symptomatic
confinement, so the second role's epoch is conditional on that response.
This is a model-side outcome: the public series does not record which role
crossed first.

**Environmental panel.** Compact records and generic summaries omit the
assay payload; full telemetry retains it. The contract declares a **core
compact outcome record for every cell plus a prospectively selected
environmental panel run with full telemetry**. The panel's cells are fixed
by seed index in the design file before any cell runs, never by outcome.
The panel record preserves, per swab: zone, epoch, recovered amount with its
density unit (copies per cm² of high-touch area), and the detection and
censoring flags; per wastewater sample: epoch, concentration in copies per
litre, and `censored_below_lod` (a below-LOD sample keeps its quantitative
value). The **holding-tank assay** (`observation.wastewater_assay_mode:
holding_tank`) is reported separately from the **wastewater sequencing**
channel (`wastewater_sequencing`); the two are not merged under one name.
An output-only compact harvest of the same fields is an acceptable
substitute if a later change adds one; it would be telemetry, not biology
(§4).

**Extraction fixtures before the bridge.** The bridge design is not executed
until fixtures on a real archive from the named commit show, for every
family: the field is present, onset and reporting coverage are stated (cases
with an onset epoch, cases with a report epoch, observation-window end), and
passenger and crew denominators equal §2.7. If the panel runs a seed that
also runs compact, the fixture shows the two agree on the compact families.

### 5.2 Design and bridge size

Four hulls × three voyage lengths (168 / 288 / 504 epochs) × three bridge
strata — quiet, near-threshold, outbreak — on paired seeds, every cell
carrying the §2.1 block as its invariant baseline (§2.9). Labelled-baseline
arms that reproduce a prior draw give a bit-identity check of the contract.
Explorer joins only after §2.8 is resolved.

**Arithmetic, stated plainly.** The seed table of revision 1 (20 outbreak,
100 near-threshold, 300 quiet per cell) is 4 × 3 × (20 + 100 + 300) =
**5,040 trajectories at one reference**, before any tail-resolution cell,
and 10,080 if duplicated across an old and a new reference. That is not a
modest bridge, and it is withdrawn as the bridge's size.

**Principle recorded here; WP2 owns the design.**

- A **small complete four-hull bridge first**, then the temporal pilot and a
  joint-outcome pilot; replication is allocated after those, where it
  improves a claim. All three voyage lengths stay in the scientific
  evaluation.
- WP2's design states endpoint-specific precision, batch and analysis rules,
  and source-stratum inclusion probabilities before any cell runs.
- **Zero-event convention.** Zero events in *n* independent voyages gives an
  exact one-sided 95% upper bound of 1 − 0.05^(1/n) on the per-voyage event
  probability: 0.994% for 0/300, 13.9% for 0/20. A reported bound names its
  sampling frame — the hull, voyage length and stratum, and how the seeds
  were drawn.
- A thousand voyages is not a thousand posted outbreaks: conditional tail
  precision follows the number of eligible events and their weights.
- Previously selected seeds are diagnostic evidence. Population estimates
  need independently sampled evaluation seeds and justified source weights.

### 5.3 Bridge gate — technical completion and scientific outcome

Two separate decisions. The bridge is read before any ensemble cell is
committed.

**Gate: technical completion.** The bridge passes when all four hold:

1. **Intended inputs were used.** Each archive records the named commit, the
   image digest, the invariant baseline and its arm's declared paths, and
   the generated cell validates after all runner axes (§2.9). Role counts in
   every outcome payload equal §2.7.
2. **Outcomes are extractable.** All six families are present with stated
   coverage and denominators (§5.1).
3. **Attempts are accounted for.** Every submitted cell is completed, failed
   with a recorded cause, or re-run under a recorded rule; no cell is
   dropped silently.
4. **Paired comparisons are meaningful.** Paired arms share seeds and differ
   only in declared paths; labelled-baseline arms reproduce their prior
   draw.

A technical failure is repaired and the affected cells re-run. It is not a
scientific result.

**Not a gate: the observed ordering.** Whether quiet strata stay quiet,
outbreak strata post and near-threshold strata fall between them is a
**measured result**. A zero-event stratum, including on a large hull, is
data with a bound (§5.2); it does not void the reference, and a reversal
does not automatically return the program to mechanism work.

**Predeclared continuation decision.** Before any cell runs, the WP2 design
fixes the rule that maps the measured rates to one of these continuations.
More than one is valid:

| Continuation | Chosen when the bridge shows |
|---|---|
| Temporal reconstruction | Outcome families extract cleanly and timing is the next informative contrast |
| Population / geometry comparison | Hull or role-composition differences dominate the measured rates |
| Targeted uncertainty evaluation | A named declared input plausibly accounts for a stratum's rate |
| Precision expansion | A rate needed for a claim is bounded too loosely |
| Justified defect correction | A specific defect is identified and evidenced; this creates a new reference (§4) |

All four hulls are retained under every continuation.

**Scientific adequacy stays a scientific criterion.** Splitting the gate
does not permit claiming adequate performance from an unfavourable result.
The numeric criteria for model utility and external comparison (A4, A8, A9
as the ledger defines them, limitations 2 and 5) are fixed in the WP2 design
before any cell runs and are judged there, not here.

**What technical completion does not establish.** It does not establish that
A4, A8 or A9 pass, and it does not turn any withdrawn figure back into a
current one (limitations 1, 3, 10).

## 6. Out of scope for this contract

The freeze declaration itself; the WP2 campaign directory, seed allocation
and numeric criteria; the WP3 reconstruction campaign, its 192-epoch length
and date-to-epoch convention; the response-demonstration pairing (WP5); the
choice among the §2.8 rhythm options; any mechanism change, campaign run or
regeneration of platform data.

## 7. Review corrections — where each is resolved

Edison's six required corrections and four affirmed decisions
(`REVIEW.md`), mapped to this revision.

| # | Correction | Resolved in | Verified by |
|---|---|---|---|
| 1 | Role populations stated and asserted | §2.7 (counts, exact class counts, labelled baseline, Explorer comparison); §2.5 row; §5.3 item 1 | Checker role-count check on five hulls, both allocations |
| 2 | Explorer exposure-cap eligibility | §2.8 (closed by WP1c, #1359); §1 condition 5. A second divergence found by WP1c — rhythm-layer attachment — is **open** in §2.8 and limitation 13 | Checker per-hull resolved-state probes on all five hulls; rhythm attachment asserted; one `PENDING` entry |
| 3 | Explicit six-family output contract | §5.1 | Annex `run.sentinel_line_list` request; fixtures required before the bridge |
| 4 | Bridge completion split from scientific outcome | §5.3; zero-event convention §5.2 | — (design rule) |
| 5 | Invariant baseline and declared arms | §2.9; §2.1 and §2.2 wording; annex §2.10 | Checker compares generated cells after all runner axes |
| 6 | Checker qualified and tightened | §2.3 (evidence categories, 57 units / 70 leaves, conditional pins); §2.4 | `scripts/paper1_freeze_block_check.py`, its retained output, `tests/test_paper1_freeze_block_check.py` |

| Affirmed decision | Recorded in |
|---|---|
| Sanitary visits `none`, flush aerosol `0.0` | §2.6 item 1 |
| Escalation 2% / 3% / 5%, YAML versus runner | §2.6 item 2; §2.2 |
| `syndromic_comp65` with class compliance and upstream counters | §2.6 item 3; annex `resolved.reporting`, `resolved.strategy` |
| Registry source and station-lot formulation | §2.6 item 4; annex `resolved.source`, `resolved.introduction` |

| Other review point | Recorded in |
|---|---|
| Example run specification per hull, post-runner-axes | §2.10 |
| Bridge-size arithmetic and small-bridge-first principle | §5.2 |
| Version-specific disposition of old results | Limitations 1 and 10 |
| Moratorium scope | §4 |

## 8. Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-20 | Proposed for Edison's review; merged #1355, reviewed at `73ad8724` |
| 2 | 2026-11-21 | Edison's six corrections and affirmed decisions applied. §2.1 block unchanged. Added §2.7–§2.10, §5.1–§5.3, §7, §8; rewrote §2.3, §2.4, §2.6, §4; limitations 1 and 10 reworded, 13 added. Checker tightened; output and annex committed. §2.5 hash-seed row corrected to the worker-side pin (WP3 review). §2.8 updated for #1359 and the rhythm-layer divergence |
