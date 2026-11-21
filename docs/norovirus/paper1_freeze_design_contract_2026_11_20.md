# Paper-1 freeze design contract (WP1)

> **Status:** Design contract proposed for Edison's pre-freeze review —
> **not a freeze declaration**. Candidate reference `b25cb0f2` (main HEAD when
> drafted, 2026-11-20); the named reference is whatever main HEAD is at freeze
> time (§1). The frozen block in §2 was verified at the candidate by
> `scripts/paper1_freeze_block_check.py` (57 pinned keys, 0 failures; no voyage
> epoch stepped). No simulation was run and no number in this document is a
> model result. Context:
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

## 2. Frozen config block

### 2.1 What the block is and how it is carried

The block is a `config_overrides` object, the shape NORO-GENO-02 carried on
every cell. It is pasted verbatim as the tier's `config_overrides` in a
campaign manifest. The loader path, verified rather than assumed, is:

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
  drops the other seven frozen `common_source` keys. WP2 cells apply an arm
  by editing a copy of the frozen block, never by layering a partial block
  over it.
- **Unknown keys are accepted.** The merge does not validate names, so a pin
  that parses can be dead. The check in §2.4 exists for that reason.
- **The runner adds its own overrides beneath the tier's**:
  `escalation` (0.02 / 0.03 / 0.05), the surveillance strategy's block,
  `initiation.boarding`, and `ship_graph.num_agents`. The block pins
  `escalation` explicitly because `crusher_labs/config.yaml` declares
  `lockdown_attack_rate: never`, so the value otherwise depends on which
  loader built the cell.

### 2.3 Pinned keys — default, pinned value, consumer

57 keys. "Config default" is the value in the merged config with no block
(`absent` means the YAML does not declare it and the engine default applies);
"resolved default" is what the engine resolved at `initialize()` with no
block. "Liveness" is the result of flipping that one key to another value:
`live` means the engine's resolved state followed the flip, `flip rejected`
means the consumer raised on the alternate (so it read the key), and
`cfg + consumer read` marks a key with nothing to probe after `initialize()` —
it is read inside the epoch loop, or, for `hvac.transport_engine`, the
alternate needs the ContamX binary and falls back to native without it.

| Key | Config default | Resolved default | Pinned | Consumer | Liveness |
|---|---|---|---|---|---|
| `transmission.contact_mode` | `"per_partner_contact"` | `'per_partner_contact'` | `"per_partner_contact"` | `engines/transmission_core.py` | live (flip rejected: ValueError) |
| `transmission.droplet_emission_mode` | `absent` | `'profile_conditioned'` | `"profile_conditioned"` | `engines/transmission_core.py` | live |
| `transmission.droplet_field_split.mode` | `absent` | `'partition'` | `"partition"` | `engines/transmission_core.py` | live |
| `transmission.droplet_field_split.far_field_share` | `absent` | `0.175` | `0.175` | `engines/transmission_core.py` | live |
| `transmission.droplet_field_split.settled_share` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | live |
| `transmission.near_field_air.mode` | `absent` | `'two_box'` | `"two_box"` | `engines/transmission_core.py` | live |
| `transmission.near_field_air.interzonal_airflow_m3_per_hour` | `absent` | `204.0` | `204.0` | `engines/transmission_core.py` | live |
| `transmission.near_field_air.neighbour_table_ratio` | `absent` | `0.43` | `0.43` | `engines/transmission_core.py` | live |
| `transmission.room_air_removal.mode` | `absent` | `'first_order'` | `"first_order"` | `engines/transmission_core.py` | live |
| `transmission.room_air_removal.map_arm` | `absent` | `'ambient_on'` | `"ambient_on"` | `engines/transmission_core.py` | live |
| `transmission.room_air_removal.default_ach_per_hour` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | live |
| `transmission.cabin_air_mode` | `"cabin_compartment"` | `'cabin_compartment'` | `"cabin_compartment"` | `engines/transmission_core.py` | live |
| `transmission.cabin_cooccupancy.mode` | `absent` | `'time_partitioned'` | `"time_partitioned"` | `engines/transmission_core.py` | live |
| `transmission.cabin_confined_fomite.mode` | `absent` | `'own_cabin'` | `"own_cabin"` | `engines/transmission_core.py` | live |
| `transmission.isolated_quarters_deposits.mode` | `absent` | `'deposits_only'` | `"deposits_only"` | `engines/transmission_core.py` | live |
| `transmission.caregiver.mode` | `absent` | `'on'` | `"on"` | `engines/transmission_core.py` | live |
| `transmission.caregiver.budget_mode` | `absent` | `'reallocate'` | `"reallocate"` | `engines/transmission_core.py` | live |
| `transmission.sanitary_visit_mode` | `"none"` | `'none'` | `"none"` | `engines/transmission_core.py` | live |
| `transmission.flush_aerosol_fraction` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | live |
| `transmission.flush_cabin_emission` | `absent` | `True` | `true` | `engines/transmission_core.py` | live |
| `transmission.blackwater_plumbing` | `true` | `'BlackwaterHoldingTank'` | `true` | `engines/transmission_core.py` | live |
| `transmission.hand_reservoir_mode` | `absent` | `'hygiene_cycle'` | `"hygiene_cycle"` | `engines/transmission_core.py` | live |
| `transmission.hand_redeposit_mode` | `absent` | `'shedders_only'` | `"shedders_only"` | `engines/transmission_core.py` | live |
| `transmission.contamination_solver` | `absent` | `'continuous'` | `"continuous"` | `engines/transmission_core.py` | live |
| `transmission.intra_epoch_causal_order` | `absent` | `'legacy'` | `"legacy"` | `engines/transmission_core.py` | live |
| `transmission.intra_epoch_substeps` | `absent` | `1` | `1` | `engines/transmission_core.py` | live (flip rejected: ValueError) |
| `transmission.high_touch_area_scale` | `absent` | `1.0` | `1.0` | `engines/transmission_core.py` | live |
| `transmission.dining_party_contact_share` | `absent` | `1.0` | `1.0` | `engines/transmission_core.py` | live |
| `transmission.contact_class_exponent` | `absent` | `0.0` | `0.0` | `engines/transmission_core.py` | live |
| `transmission.exposure_cap.enabled` | `true` | `True` | `true` | `engines/transmission_core.py` | live |
| `transmission.exposure_cap.include_fixed_rings` | `absent` | `False` | `false` | `engines/transmission_core.py` | live |
| `transmission.activity_contacts.enabled` | `true` | `{'cabin': {'passenger': 0.25, 'crew': 0.25}, 'corridor': {'passenger': 0.25, 'crew': 0.25}, 'work_service': {'passenger': 2.9, 'crew': 2.9}, 'work_other': {'passenger': 0.5, 'crew': 0.5}, 'dining_table': {'passenger': 2.0, 'crew': 2.0}, 'dining_venue': {'passenger': 2.0, 'crew': 2.0}, 'leisure': {'passenger': 1.0, 'crew': 1.0}, 'other': {'passenger': 0.0, 'crew': 0.0}}` | `true` | `engines/transmission_core.py` | live |
| `transmission.activity_contacts.rates_per_hour` | `{"cabin": 0.25, "corridor": 0.25, "work_service": 2.9, "work_other": 0.5, "dining_table": 2.0, "dining_venue": 2.0, "leisure": 1.0, "other": 0.0}` | `{'cabin': {'passenger': 0.25, 'crew': 0.25}, 'corridor': {'passenger': 0.25, 'crew': 0.25}, 'work_service': {'passenger': 2.9, 'crew': 2.9}, 'work_other': {'passenger': 0.5, 'crew': 0.5}, 'dining_table': {'passenger': 2.0, 'crew': 2.0}, 'dining_venue': {'passenger': 2.0, 'crew': 2.0}, 'leisure': {'passenger': 1.0, 'crew': 1.0}, 'other': {'passenger': 0.0, 'crew': 0.0}}` | `{"cabin": 0.25, "corridor": 0.25, "work_service": 2.9, "work_other": 0.5, "dining_table": 2.0, "dining_venue": 2.0, "leisure": 1.0, "other": 0.0}` | `engines/transmission_core.py` | live |
| `transmission.surface_cleaning.enabled` | `true` | `True` | `true` | `engines/transmission_core.py` | live |
| `transmission.surface_cleaning.routine` | `{"coverage": 0.37, "log10_reduction": 1.29, "events_per_day": 1.0}` | `0.37` | `{"coverage": 0.37, "log10_reduction": 1.29, "events_per_day": 1.0}` | `engines/transmission_core.py` | live |
| `transmission.surface_cleaning.outbreak_response` | `{"coverage": 0.58, "log10_reduction": 4.29, "events_per_day": 24.0, "by_zone_class": {"cabin": {"events_per_day": 1.0}}}` | `0.58` | `{"coverage": 0.58, "log10_reduction": 4.29, "events_per_day": 24.0, "by_zone_class": {"cabin": {"events_per_day": 1.0}}}` | `engines/transmission_core.py` | live |
| `transmission.common_source.mode` | `absent` | `'on'` | `"on"` | `engines/transmission_core.py` | live |
| `transmission.common_source.lot_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | live |
| `transmission.common_source.handler_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | live |
| `transmission.common_source.diner_mode` | `absent` | `'object'` | `"object"` | `engines/transmission_core.py` | live |
| `transmission.common_source.lot_mint_model` | `"provisioned_source"` | `'provisioned_source'` | `"provisioned_source"` | `engines/transmission_core.py` | live |
| `transmission.common_source.titre_draw_mode` | `absent` | `'two_mode'` | `"two_mode"` | `engines/transmission_core.py` | live |
| `transmission.common_source.lot_extent_mode` | `absent` | `'emergent'` | `"emergent"` | `engines/transmission_core.py` | live |
| `transmission.common_source.provisioned_source` | `{"source_id": "generic_cruise_port"}` | `'station_lots'` | `{"source_id": "generic_cruise_port", "lot_layer_mode": "station_lots"}` | `engines/transmission_core.py` | live |
| `hvac.pathogen_pool_transport` | `"airflow"` | `'airflow'` | `"airflow"` | `engines/py_contam_bridge.py` | live |
| `hvac.duty0_terminal_mode` | `absent` | `'extract'` | `"extract"` | `engines/py_contam_bridge.py` | live |
| `hvac.passive_link_mode` | `absent` | `'bidirectional'` | `"bidirectional"` | `engines/py_contam_bridge.py` | live |
| `hvac.transport_engine` | `"native"` | `cfg-read` | `"native"` | `engines/py_contam_bridge.py` | cfg + consumer read |
| `observation.enabled` | `true` | `cfg-read` | `true` | `picard_framework/simulation/ship_simulation.py` | cfg + consumer read |
| `observation.surface_swab_source` | `"surface_pool_density"` | `cfg-read` | `"surface_pool_density"` | `orchestrator_epoch.py` | cfg + consumer read |
| `observation.wastewater_assay_mode` | `"holding_tank"` | `'WastewaterHoldingTankAssay'` | `"holding_tank"` | `orchestrator_init.py` | live |
| `service_surface_knockout.enabled` | `false` | `False` | `false` | `engines/transmission_core.py` | live |
| `crew_duty_exclusion.enabled` | `false` | `False` | `false` | `picard_framework/simulation/ship_simulation.py` | live |
| `variant_surveillance.enabled` | `false` | `cfg-read` | `false` | `picard_framework/simulation/ship_simulation.py` | cfg + consumer read |
| `escalation.suspect_attack_rate` | `0.02` | `cfg-read` | `0.02` | `orchestrator_init.py` | cfg + consumer read |
| `escalation.confirm_attack_rate` | `0.03` | `cfg-read` | `0.03` | `orchestrator_init.py` | cfg + consumer read |
| `escalation.lockdown_attack_rate` | `0.05` | `cfg-read` | `0.05` | `orchestrator_init.py` | cfg + consumer read |

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

Keys added by walking the parsers against the ledger, beyond the brief's
list: the caregiver channel (`CAREGIVER-V1`, default-ON for `norwalk_gi`),
the hand-reservoir, hand-redeposit, solver and intra-epoch-order arms, the
exposure cap, activity contacts (`CONTACT-ARCH-01`, shipped on), surface
cleaning, blackwater plumbing, the common-source block, the passive-link
mode, the transport engine, crew duty exclusion, service-surface knockout,
variant surveillance and escalation.

### 2.4 Verification

```bash
python3 scripts/paper1_freeze_block_check.py            # exit 0 required
python3 scripts/paper1_freeze_block_check.py --markdown # regenerates §2.3 rows
```

The script reads the block out of this file, builds one cell through the
NORO-GENO-02 path, and for each key checks that the merged config carries the
pinned value, that the named consumer file reads the key, that the engine
resolves the pinned value itself (several parsers substitute their default
for an unknown mode name), and that flipping the key moves the resolved
state. It then parses and initialises the block on
`expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`,
`mega_cruise_5000` and `explorer_seas_06`. It steps no epoch. Result at
`b25cb0f2`: 57 keys, 0 failures, five hulls parse and initialise.

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
| Hulls and complements | `expedition_cruise_450` (450), `classic_cruise_1900` (1,910), `spirit_cruise_3000` (3,000), `mega_cruise_5000` (7,000) | Tier `platform` / `num_agents`; platform files at the named commit |
| Role split (added 2026-11-20, owner decision after WP2) | Per-hull `ship_graph.agent_classes`: the shipped class list re-weighted so the engine places the platform's declared `nominal_complement` — 300/150, 1,350/560, 2,100/900, 5,000/2,000 passengers/crew. The shipped 70/30 template alone places 316/134, 1,338/572, 2,100/900, 4,900/2,100 | Not in the §2 block, because one block cannot hold four mixes. Each joint-evaluation tier declares it as its one difference from the block (`campaigns/noro/paper1_joint_eval_01/design/build.py`, `class_mix`); `cell.py` asserts the counts on every bridge, pilot and reproduction run. The boarding census is the exception: it runs 100 agents through `supply_seed_scan.py`, so it carries the class list but neither places nor asserts the declared counts. The WP3 Explorer cell needs its own |
| Voyage grid (joint evaluation) | **168 / 288 / 504 epochs** (7 / 12 / 21 days) | Tier `epoch_durations`. 192 epochs belongs to the Explorer reconstruction (WP3) only and is not a joint-evaluation length |
| Hash seed | `PYTHONHASHSEED=1` | Job definition environment, as in the supply-solver screens |

Neither of the first two is a machinery gap that blocks the freeze, and no
new override path is proposed. They are recorded so that nobody reads the
block as pinning them.

### 2.6 Choices this block makes that the reviewer should confirm

1. **Sanitary visits and flush aerosol are pinned off** (`none`, `0.0`),
   which is the shipped default. NORO-GENO-02 and the flush sweeps pinned
   `dwell_weighted`. The ledger withdraws every flush-sweep result as a
   current-engine measurement, and records the structure-only arm as a null
   without a flush term, so no current measurement supports adopting a flush
   value. Pinning `dwell_weighted` instead is a one-key change.
2. **Escalation is pinned at the campaign runner's values** (suspect 0.02,
   confirm 0.03, lockdown 0.05) rather than the YAML's `lockdown: never`,
   because every norovirus campaign to date ran under the runner's values.
3. **The surveillance strategy is not in the block.** NORO-GENO-02 used
   `syndromic_comp65` (cascade off, quarantine compliance 0.65 with a class
   split). It sets `fred_behavior` and `diagnostic_cascade`, which the
   response-demonstration arm (WP5) varies. The contract proposes
   `syndromic_comp65` as the usual-recognition arm for WP2, restated on every
   cell.
4. **Common-source food events stay on** with the provisioned-source mint
   model and the registry's `generic_cruise_port` values. The supply-solver
   screens pinned additional rungs (`q_source`, station pin, venue arm);
   those are screen arms and are not adopted here.

## 3. Declared limitations

Each item cites `norovirus_open_ledger.md` (section or stamp) or the document
that records it. The count is 12.

1. **Every dose figure except one is void pending refit.** Only
   `environmental_faecal_release_log10_g_per_epoch` = 7.57 [7.14, 8.86]
   (`NORO-DOSE-REFIT-01`) is current. Attack rates, route shares, ladder
   tables and per-host dose tables measured before the refit are historical
   (§1, "Every dose figure in this repository is void").
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
10. **Earlier results that must not be reused as current**: every result
    before `COMPLEMENT-01` belongs to no ship class, every arrival prevalence
    and posting rate before `ARRIVE-01` is void, and caregiver-adjacent
    readings before `CAREGIVER-V1` are a labelled baseline (§1).
11. **SOP-007/009 `close_zones` name `mega_cruise_5000` zone ids** and skip
    Explorer's galley and crew mess. This affects only response arms run on
    Explorer; WP3 owns the decision
    ([WP0 readout](wp0_explorer_platform_session_prompt_2026_11_20.md)).
12. **Two reference properties have no config pin** (§2.5): the VSP
    either-channel rule and the shedding variance are fixed by the named
    commit alone.

None of these forces a change to the evaluation contract in §5. Items 2 and
5 limit what a pass can claim; item 4 is what the bridge measures.

## 4. Moratorium

From the freeze declaration until the WP2 bridge readout is delivered and a
go/no-go is recorded, and thereafter for as long as evaluation cells are
being run against the named commit.

| During evaluation | Examples |
|---|---|
| **Not allowed — mechanism work** | Any change under `engines/`, `orchestrator*.py`, `crusher_labs/` or `picard_framework/simulation/` that can move a norovirus run's output; any change to a default in `crusher_labs/config.yaml` or an engine `DEFAULT_*`; any change to `data/pathogens/` profiles or to the five platforms' data; any change to the scoring definitions of A1–A9; changing a value in the frozen block |
| **Allowed — config, campaign, documentation** | New `campaigns/noro/<name>/` directories (design, manifest, cell worker, readout); manifests that carry the block verbatim; readout and analysis code that reads archives; new output fields that do not consume random draws or change state; ledger entries and documents; tests; CI and tooling; work on other pathogens that does not touch shared defaults |
| **Allowed only as a declared exception** | A defect fix that moves norovirus output. It is recorded in the ledger, the named commit moves to the fix, §1's conditions are re-met, and every cell already run is either re-run or labelled as measured at the earlier commit |

A change is mechanism work if the same seed can produce a different archive
after it. When that cannot be decided by reading the diff, the test is a
paired-seed run of one bridge cell before and after.

## 5. Evaluation contract — summary for Edison

**What is scored.** Six outcome families, all harvested from one run per
cell (sources as verified in the assessment):

| Family | Source in run output |
|---|---|
| Routine and reported burden, by role | `rep_pax_n` / `rep_crew_n`, `cumulative_reported_cases_*`, census |
| Reaching the reporting threshold | `vsp_trigger_epoch` (either channel at 3% of that channel's complement) |
| Outbreak-size distribution and tails | Seed ensemble of the above |
| First role to threshold | Per-epoch `cumulative_reported_cases_{passenger,crew}` against the 0.03 line. Model-side outcome: the public series does not record which role crossed first |
| Daily onset and reporting curves | Onsets from `run.sentinel_line_list`; the reporting curve from the per-epoch `cumulative_reported_cases_*` series |
| Environmental observables | Surface swab (`surface_pool_density`) and holding-tank wastewater assay |

**Design.** Four hulls (450 / 1,910 / 3,000 / 7,000) × three voyage lengths
(168 / 288 / 504 epochs) × three bridge strata — quiet, near-threshold,
outbreak — on paired seeds, every cell carrying the §2 block verbatim.
Labelled-baseline arms that reproduce a prior draw give a bit-identity check
of the contract.

**Seeds per stratum.** The assessment fixes the first and last rows; the
middle rows apply its arithmetic and are proposals for review.

| Stratum | Seeds per cell | What that resolves |
|---|---|---|
| Outbreak (loud) | ~20 | Contract cleanliness and a posting rate that is not rare |
| Near-threshold | 100 (proposed) | A posting probability near one half to about ±0.10 |
| Quiet | 300 (proposed), or report a bound | Zero postings in 300 bounds the rate at ≤1.0%; zero in 20 bounds it only at ≲14% |
| Tail-resolution cells | ≥1,000 | Tail frequencies of outbreak size |

The 0.5% quiet event rate used in the planning arithmetic is illustrative and
unmeasured on the current engine; the bridge returns the actual rate per
stratum.

**Go/no-go reading.** The bridge is read before any ensemble cell is
committed.

- **Go** requires both: (a) the contract is clean — every cell completes, all
  six families are present, each archive records the frozen block and the
  named commit, and labelled-baseline arms reproduce; and (b) the mixture is
  present — quiet-stratum cells post rarely or not at all within their
  bound, outbreak-stratum cells post, and near-threshold cells sit between
  them, on every hull.
- **No-go** if the quiet stratum posts at a rate comparable to the outbreak
  stratum (every voyage takes off), if the outbreak stratum does not post,
  or if the contract is not clean. A no-go returns to mechanism work and
  voids the freeze; it is not repaired by changing the block.
- The numeric thresholds for "rarely", "post" and "between" are fixed in the
  WP2 design file before any cell runs. This contract does not set them.

**What a go does not establish.** It does not establish that A4, A8 or A9
pass (limitations 2 and 5), and it does not turn any withdrawn figure back
into a current one (limitations 1, 3, 10).

## 6. Out of scope for this contract

The WP2 campaign directory and its numeric admissibility criteria, the WP3
reconstruction campaign and its 192-epoch length, the response-demonstration
pairing (WP5), and any regeneration of platform data.
