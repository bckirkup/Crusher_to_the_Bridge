# NORO-PROVISIONED-SENSITIVITY-01 — ledger

**Status: scout wave submitted 2026-11-07 — main remainder held for the user gate.** Paper-1
sensitivity screen, Child B: 16 Res-V profiles × 4 hulls × 3 venue
arms = 192 cells, seed-paired with NORO-PROVISIONED-VENUE-02, 1.5.0
emitter. Design: `DESIGN.md`; profile table: `PROFILE_TABLE.md`;
execution manifest: `SEED_MANIFEST.json`.

**Submit gate:** design PR merged → image built FROM the post-merge SHA
(must contain PR #1156's emitter AND this PR's `tier_pathogen_overrides`
/ `tier_illness_duration_draw` seams) → digest pinned here → manifest
mirrored to S3 → scout wave → STOP for the user.

Image: `picard-campaign:noro-provisioned-sensitivity01` built FROM merged
main `71794db5a177f37b207b04d289b4f134913e1bed` (#1157 merge, contains
#1156), pushed 2026-11-07 00:13 UTC, digest
`sha256:354ddfda0816abc10dca787f720b97e128a83db9ce1952f6e11c2ed64a8f5cef`,
ENGINE_GIT_SHA `71794db5` verified in-container together with
`campaigns/noro/provisioned_sensitivity_01{,_mega}/`, the manifest, and
`tier_illness_duration_draw` in `boarding_axis.py`; one in-container
`campaign_entrypoint.py --local` voyage (exp p01 crewv, seed 8000) wrote
the zip + growth census. Manifest mirrored to
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_sensitivity_01/manifest.json`
(and `…_01_mega/manifest.json`; both prefixes empty beforehand).
Jobdefs `picard-noro-provisioned-sensitivity-01` / `…-01-mega`, image by
tag (digest above is the pin of record), 1 vCPU, 4096 / 8192 MiB, Spot
queue `picard-campaign-queue`.

## Measured before submit (local, repo HEAD 76a44890 + branch)

- D override order: confirmed in code — `shipped` rung overwrote a
  tier-requested `empirical_survival` with `point` (`boarding_axis.
  IndexCaseAxis.pathogen_overrides`); venue02 therefore ran at D =
  `point`. Fixed by the tier-declared-draw seam (this PR); the paired
  probe below shows the flipped draw reaching the engine.
- Loaded values at spec level (`generate_tier_runs` →
  `apply_pathogen_overrides`): p16/p01/meg-p09 all resolve to the
  design values (DESIGN.md §5).
- Dry-run: manifest `--tier all` = 11,520 runs across 192 tiers
  (11,136 main + 384 reserve); `scripts/campaign list` = 288 blocks /
  9,984 cells (small hulls) + 96 blocks / 1,152 cells (mega).
- Local smoke, exp seed 8000, 288 epochs: `scout_fl_exp_12d_sens_p01_crewv`
  1m41 wall; `scout_fl_exp_12d_sens_p16_mixv` 1m44 wall; zip =
  summary.json 0.42 MB + growth_census.json.gz 9.7 MB + rss_samples.json;
  `role_checkpoints` schema 1.0 present with days 3/7/10/12.
- Paired D-probe (p01 coordinates, exp, seed 8000, 288 epochs, draw
  `point` vs `empirical_survival`, everything else identical): the two
  summaries differ (terminal infected 30 vs 29, symptomatic 4 vs 3,
  quarantined 4 vs 7; stamped `illness_duration_draw` follows the
  request), so the tier-declared draw reaches the engine under the
  `shipped` rung. Operational evidence only — one seed, no inference.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| scout | 192 × `scout_<tier>` (8 seeds each) | 1,536 | 144 small-hull arrays submitted 2026-11-07 00:20–00:38 UTC; mega arrays after the mega canary |
| main | 192 × `<tier>` (n−8 seeds each) | 9,600 | not submitted — user gate after scout |

### canary children — submitted 2026-11-07 00:15 UTC

| cell | jobdef | seed | job id |
|---|---|---|---|
| scout_fl_exp_12d_sens_p16_mixv index 0 | :1 | 8000 | 8ebe10ac-7abe-4541-bd60-4b5b1ba2044d (SUCCEEDED, 65 s container wall) |
| scout_fl_meg_12d_sens_p01_crewv index 0 | mega:1 | 8105 | db1f4e31-94e7-4034-b3b8-ace01bc7538e |

### scout arrays — small hulls, jobdef `picard-noro-provisioned-sensitivity-01` (array size 8 each)

| block | jobdef | job id |
|---|---|---|
| scout_fl_exp_12d_sens_p01_crewv | :2 | 095b514f-971a-4d35-97c2-e93c25c27a4d |
| scout_fl_exp_12d_sens_p01_paxv | :3 | 08201cc5-0875-4825-877f-d41a7ee2696d |
| scout_fl_exp_12d_sens_p01_mixv | :4 | 3769afeb-a99d-4983-9e8c-6f9c3da56dd0 |
| scout_fl_exp_12d_sens_p02_crewv | :5 | a096c712-498b-41fc-b60a-af44d90f313e |
| scout_fl_exp_12d_sens_p02_paxv | :6 | dd0ed529-cb8e-4d09-a56b-38cb077dd3d3 |
| scout_fl_exp_12d_sens_p02_mixv | :7 | 645f5502-4b20-44e4-ae47-0656a075e4a7 |
| scout_fl_exp_12d_sens_p03_crewv | :8 | ae5c9236-faed-4af0-99a0-f897c18ffd82 |
| scout_fl_exp_12d_sens_p03_paxv | :9 | 8fc953f0-a9ae-4553-84d6-810b9f40c708 |
| scout_fl_exp_12d_sens_p03_mixv | :10 | 6941bddd-a878-4345-b110-8163914cc5b3 |
| scout_fl_exp_12d_sens_p04_crewv | :11 | 22d27411-de2d-4f1e-8754-d3f33eefa9e5 |
| scout_fl_exp_12d_sens_p04_paxv | :12 | 50e09468-aff7-439a-936d-87294ec846a0 |
| scout_fl_exp_12d_sens_p04_mixv | :13 | 7dc157f7-ae6a-4cd6-9af5-d8f02ae0a655 |
| scout_fl_exp_12d_sens_p05_crewv | :14 | da6159b4-143a-4b27-a015-fef9ca8f5d0a |
| scout_fl_exp_12d_sens_p05_paxv | :15 | cf353abb-c1e3-4b3e-8b15-264bd69cdfac |
| scout_fl_exp_12d_sens_p05_mixv | :16 | bfc5af34-d024-4cb3-b81c-f04026cb9404 |
| scout_fl_exp_12d_sens_p06_crewv | :17 | f5c0a8c2-322a-48ef-923c-88941a6c6022 |
| scout_fl_exp_12d_sens_p06_paxv | :18 | a818810c-b5c9-479a-b9d5-9499e6f8e676 |
| scout_fl_exp_12d_sens_p06_mixv | :19 | 4b88756a-11d2-4bee-a608-764dff41508a |
| scout_fl_exp_12d_sens_p07_crewv | :20 | 2d6ab78e-53ee-49cc-949d-fe02f6142a1a |
| scout_fl_exp_12d_sens_p07_paxv | :21 | 4fecfa9e-cf26-4c4e-b8d5-3490722ae551 |
| scout_fl_exp_12d_sens_p07_mixv | :22 | 78851ecf-ab29-4c3e-acbb-f2d4f49364ee |
| scout_fl_exp_12d_sens_p08_crewv | :23 | 2c5ecb4d-6935-49fb-8249-111ab7588cd7 |
| scout_fl_exp_12d_sens_p08_paxv | :24 | 8ead76d7-6e86-4699-b350-8e6c61fcfdb1 |
| scout_fl_exp_12d_sens_p08_mixv | :25 | 681c5ea0-5ccc-43cb-b9d8-c132c551064b |
| scout_fl_exp_12d_sens_p09_crewv | :26 | 74b16261-7461-4c21-98a2-4aa1afc0987e |
| scout_fl_exp_12d_sens_p09_paxv | :27 | 60126a7c-7b80-43c1-bdab-8708d14b9100 |
| scout_fl_exp_12d_sens_p09_mixv | :28 | ee438705-a25c-4c10-8e3e-af96e9556413 |
| scout_fl_exp_12d_sens_p10_crewv | :29 | e933c465-d2be-49fc-8fa3-1daf34387397 |
| scout_fl_exp_12d_sens_p10_paxv | :30 | fd34390d-e413-44ed-b091-b20dfc546c51 |
| scout_fl_exp_12d_sens_p10_mixv | :31 | cd172f52-bd16-4e0f-b0e6-202af5edabd2 |
| scout_fl_exp_12d_sens_p11_crewv | :32 | 95534ebf-c717-4f4a-943e-a7d2a8f0d96b |
| scout_fl_exp_12d_sens_p11_paxv | :33 | 37c102aa-88e1-4ad5-ba45-aff59659794b |
| scout_fl_exp_12d_sens_p11_mixv | :34 | eb2d6f79-a299-4d57-af21-e7a1caee4cb8 |
| scout_fl_exp_12d_sens_p12_crewv | :35 | c5518381-5a2f-4b93-9dc9-298adab68d5b |
| scout_fl_exp_12d_sens_p12_paxv | :36 | b3c418d5-9cfa-4cfd-8fa1-c36d96a8ead5 |
| scout_fl_exp_12d_sens_p12_mixv | :37 | 662e8586-9c32-4cc4-96ab-7c67a85a9692 |
| scout_fl_exp_12d_sens_p13_crewv | :38 | 5f4c4900-2fb5-43ff-b982-69e2658efac8 |
| scout_fl_exp_12d_sens_p13_paxv | :39 | 43c32ff2-2587-4c05-bc86-7227bd5774f0 |
| scout_fl_exp_12d_sens_p13_mixv | :40 | 7f7fca86-76bd-4a4f-8626-bd12c3facc41 |
| scout_fl_exp_12d_sens_p14_crewv | :41 | 7d6b4db0-9bb6-45cd-9725-af6039c4bde3 |
| scout_fl_exp_12d_sens_p14_paxv | :42 | 92dae526-a0e8-4d4c-9656-1491e93e8740 |
| scout_fl_exp_12d_sens_p14_mixv | :43 | d135ac51-46c5-45c4-b5e8-ce2bbea04a80 |
| scout_fl_exp_12d_sens_p15_crewv | :44 | bd2eb8b1-18e4-4a9a-aa19-f278da13a1d4 |
| scout_fl_exp_12d_sens_p15_paxv | :45 | 769cf2d7-1d5c-477a-840c-e5297b403d09 |
| scout_fl_exp_12d_sens_p15_mixv | :46 | 7e666ee0-519b-43cc-8013-dc84ca34ef1e |
| scout_fl_exp_12d_sens_p16_crewv | :47 | e84dbc93-6841-4e45-9e21-17bef003ca41 |
| scout_fl_exp_12d_sens_p16_paxv | :48 | 5644a602-abde-450f-b553-66d682ae546a |
| scout_fl_exp_12d_sens_p16_mixv | :49 | 72948153-86ff-4e76-bf48-994a449013ef |
| scout_fl_cls_12d_sens_p01_crewv | :50 | ff3afec0-9ab1-4924-990b-a65e046ea69c |
| scout_fl_cls_12d_sens_p01_paxv | :51 | cd363e44-86b5-49ef-8099-cfe67c68cd20 |
| scout_fl_cls_12d_sens_p01_mixv | :52 | 91902276-88d4-4247-8a3b-25b4e1aa9763 |
| scout_fl_cls_12d_sens_p02_crewv | :53 | 0d4a47be-a242-4cd3-9fb4-b19c9ba95fc4 |
| scout_fl_cls_12d_sens_p02_paxv | :54 | 14a237c9-90fe-40ce-b87f-0011bc813bfe |
| scout_fl_cls_12d_sens_p02_mixv | :55 | ee9f654a-dd02-41ed-810d-972e0bd61654 |
| scout_fl_cls_12d_sens_p03_crewv | :56 | a64699b0-fa34-4dd5-a50c-bd87361e1791 |
| scout_fl_cls_12d_sens_p03_paxv | :57 | a795bca0-d095-4fc0-acf6-4e71a047beb9 |
| scout_fl_cls_12d_sens_p03_mixv | :58 | ca7e1b24-e8ca-467d-b850-722efc956cfc |
| scout_fl_cls_12d_sens_p04_crewv | :59 | 801b9fb3-8d4d-42e9-9dc7-5002a827a4bb |
| scout_fl_cls_12d_sens_p04_paxv | :60 | 05f43319-5035-420a-b941-7af5bc90c7d1 |
| scout_fl_cls_12d_sens_p04_mixv | :61 | b16fc30f-f686-4e5e-81bd-39b728f55f63 |
| scout_fl_cls_12d_sens_p05_crewv | :62 | d2282805-0476-4971-bd81-080ea087f317 |
| scout_fl_cls_12d_sens_p05_paxv | :63 | a7a8a21c-5ddf-4fcd-8089-5016d36f25b4 |
| scout_fl_cls_12d_sens_p05_mixv | :64 | 0c87065a-132f-457e-b210-eb17a07e2cec |
| scout_fl_cls_12d_sens_p06_crewv | :65 | cbfcbf73-d436-4d36-a39a-2329447b19d7 |
| scout_fl_cls_12d_sens_p06_paxv | :66 | 94a8eb22-d6e6-45c7-8abc-2bd7e784c8a5 |
| scout_fl_cls_12d_sens_p06_mixv | :67 | 9e4a60f7-2b2e-4a8f-9cb4-dd978444ebca |
| scout_fl_cls_12d_sens_p07_crewv | :68 | e8d96e4c-90e2-4dda-a24e-1a25692dc376 |
| scout_fl_cls_12d_sens_p07_paxv | :69 | afd6b739-a6c9-4b43-856a-2adcb8dfc270 |
| scout_fl_cls_12d_sens_p07_mixv | :70 | 309a2e75-7e99-4e98-a87e-2d0c3f0a6e29 |
| scout_fl_cls_12d_sens_p08_crewv | :71 | d9633884-e86a-4f10-ba15-e86a97e8c0f1 |
| scout_fl_cls_12d_sens_p08_paxv | :72 | e2dad1a5-1449-4a9e-9329-275bc0b4fbbb |
| scout_fl_cls_12d_sens_p08_mixv | :73 | 32a69cfc-6c44-4230-b084-2520ed0d56ae |
| scout_fl_cls_12d_sens_p09_crewv | :74 | e07587b5-b8a1-45ec-b29b-5e264c2db8cc |
| scout_fl_cls_12d_sens_p09_paxv | :75 | 5aca23dc-d786-47b4-8009-aad2ea2268bf |
| scout_fl_cls_12d_sens_p09_mixv | :76 | 396aa1a6-39cd-4ae0-85c4-8365cc6a0279 |
| scout_fl_cls_12d_sens_p10_crewv | :77 | 298e0e2a-0d02-43c3-afce-e927694b1915 |
| scout_fl_cls_12d_sens_p10_paxv | :78 | 503d3640-e4a0-4a8b-a4b0-22bb96d5d4e4 |
| scout_fl_cls_12d_sens_p10_mixv | :79 | b836e805-3fdd-4167-8d99-4fe8017c72c4 |
| scout_fl_cls_12d_sens_p11_crewv | :80 | 429ac903-c5b8-4c26-8bb3-6732f23d04cc |
| scout_fl_cls_12d_sens_p11_paxv | :81 | f55fefdb-f9c5-4370-8c78-ac86c4a01462 |
| scout_fl_cls_12d_sens_p11_mixv | :82 | a3cbe41b-5c6b-4f70-9cb6-fba4444d8ad3 |
| scout_fl_cls_12d_sens_p12_crewv | :83 | 7236e946-7efc-4243-a8d3-45fc5e950021 |
| scout_fl_cls_12d_sens_p12_paxv | :84 | 3625da2b-2b01-48ae-8b1a-9a4125d687dc |
| scout_fl_cls_12d_sens_p12_mixv | :85 | 08e32fd8-4487-4f75-a06f-81d4db563ffc |
| scout_fl_cls_12d_sens_p13_crewv | :86 | e9bf368b-4abe-472a-a00d-4c80529d537b |
| scout_fl_cls_12d_sens_p13_paxv | :87 | 8689b6ee-144b-4e3e-a845-c5fed70cdcb4 |
| scout_fl_cls_12d_sens_p13_mixv | :88 | 67c2defb-8523-40e4-8f68-111632c48845 |
| scout_fl_cls_12d_sens_p14_crewv | :89 | 3e896aff-5cad-4dfc-9613-2727e4167913 |
| scout_fl_cls_12d_sens_p14_paxv | :90 | 03dc326f-f0a9-409f-b879-733527558b1d |
| scout_fl_cls_12d_sens_p14_mixv | :91 | 13385107-c716-41cf-b1ce-ca3cb8014703 |
| scout_fl_cls_12d_sens_p15_crewv | :92 | f66da2fa-ba90-4b97-b964-cfefca612198 |
| scout_fl_cls_12d_sens_p15_paxv | :93 | 9e45955c-4e2b-4e6a-96b5-c6f756dea144 |
| scout_fl_cls_12d_sens_p15_mixv | :94 | 1e5d58fe-ae1f-4779-9832-0d2a3025e9a6 |
| scout_fl_cls_12d_sens_p16_crewv | :95 | 2dc9b9fb-36db-4431-be1f-62b0bbc537c5 |
| scout_fl_cls_12d_sens_p16_paxv | :96 | 92c8a755-20a1-4b29-880d-e9f12fffd0ce |
| scout_fl_cls_12d_sens_p16_mixv | :97 | 500723c7-ab36-406a-9623-5fb745a161dd |
| scout_fl_spr_12d_sens_p01_crewv | :98 | 0fe249ee-c612-4f08-90c7-f30770778310 |
| scout_fl_spr_12d_sens_p01_paxv | :99 | da61b08b-a767-46b6-9db0-1e3dd64bd5bc |
| scout_fl_spr_12d_sens_p01_mixv | :100 | 0d5094ed-9137-416d-b23d-633d20ee357b |
| scout_fl_spr_12d_sens_p02_crewv | :101 | 3cb37cb1-6edb-4429-b2ee-b94a97b44143 |
| scout_fl_spr_12d_sens_p02_paxv | :102 | 7f1699a3-35e5-4297-8940-afea97bd9c87 |
| scout_fl_spr_12d_sens_p02_mixv | :103 | 0383ef77-e093-4461-853a-7e7524a0cc87 |
| scout_fl_spr_12d_sens_p03_crewv | :104 | 3b8f1202-183d-4f97-9bde-ff14bbe1c03d |
| scout_fl_spr_12d_sens_p03_paxv | :105 | f0bee4f5-60c8-4b9d-83fa-562b75c195fe |
| scout_fl_spr_12d_sens_p03_mixv | :106 | 007b2847-5ab2-4a32-a3e6-966cc21496b0 |
| scout_fl_spr_12d_sens_p04_crewv | :107 | 638bd6ff-f1cd-4200-97dd-6cc7f23287f7 |
| scout_fl_spr_12d_sens_p04_paxv | :108 | ec3d5b2f-3a4b-47bd-9df6-d16e6c6ddae4 |
| scout_fl_spr_12d_sens_p04_mixv | :109 | 0d78d76e-f7b8-4854-ac2f-9fa0aaeed898 |
| scout_fl_spr_12d_sens_p05_crewv | :110 | 43460771-abb8-424b-93a8-05458f7f358f |
| scout_fl_spr_12d_sens_p05_paxv | :111 | 565399bb-e418-4ba4-a760-79b14fa53e65 |
| scout_fl_spr_12d_sens_p05_mixv | :112 | fdd58d73-e25c-4250-b2ce-b173db252af7 |
| scout_fl_spr_12d_sens_p06_crewv | :113 | 873f0dc8-9e9d-478e-9e32-3d802a9a1d0b |
| scout_fl_spr_12d_sens_p06_paxv | :114 | eae0d1d9-b316-41a4-8f50-b43e243b0b88 |
| scout_fl_spr_12d_sens_p06_mixv | :115 | 3dfe0dac-544e-46a5-8301-8a53a58d87ac |
| scout_fl_spr_12d_sens_p07_crewv | :116 | 35212f4a-d1fe-4b2d-9eb3-868cbf5ff423 |
| scout_fl_spr_12d_sens_p07_paxv | :117 | a54bf430-3381-49e7-aa56-c9006f9eb0b9 |
| scout_fl_spr_12d_sens_p07_mixv | :118 | a19cedc3-43dc-4531-a46d-8cffd77073f0 |
| scout_fl_spr_12d_sens_p08_crewv | :119 | 94a8c1a1-73b6-4659-88c3-4d3c4169f8a0 |
| scout_fl_spr_12d_sens_p08_paxv | :120 | 3170d514-5cab-4a0d-ab01-d9ec60a7cb5f |
| scout_fl_spr_12d_sens_p08_mixv | :121 | a4d9d85e-0a7b-4c24-913e-52310409e6a3 |
| scout_fl_spr_12d_sens_p09_crewv | :122 | c33c5c84-c2f4-4790-803c-30355b459115 |
| scout_fl_spr_12d_sens_p09_paxv | :123 | 1fbfc614-78f0-4b76-a7a7-f0da9a855e06 |
| scout_fl_spr_12d_sens_p09_mixv | :124 | cb3774ac-3294-4320-b79c-a65bf86dc9d3 |
| scout_fl_spr_12d_sens_p10_crewv | :125 | cc3bd84e-7861-4b5e-b319-b4a40918252c |
| scout_fl_spr_12d_sens_p10_paxv | :126 | dbf9d91e-c9bd-4c99-afd4-d76c0084c11b |
| scout_fl_spr_12d_sens_p10_mixv | :127 | 73fd8fbd-d22c-4547-a0de-b5388bc12238 |
| scout_fl_spr_12d_sens_p11_crewv | :128 | 4e2f3481-9fbd-44b8-a20c-d44a406f5a36 |
| scout_fl_spr_12d_sens_p11_paxv | :129 | 70cda954-8c68-42b5-bc7a-64976d93df10 |
| scout_fl_spr_12d_sens_p11_mixv | :130 | 47728532-b960-4dbc-a58b-eeba240925b9 |
| scout_fl_spr_12d_sens_p12_crewv | :131 | acf36929-2599-4d1b-9b1e-6c68ffffa659 |
| scout_fl_spr_12d_sens_p12_paxv | :132 | 7c85f77f-dc82-4a08-90b3-00e9713c7f2c |
| scout_fl_spr_12d_sens_p12_mixv | :133 | 01c7ff51-0de4-4ddf-9149-a008acb2572b |
| scout_fl_spr_12d_sens_p13_crewv | :134 | 4a9c9ccb-e30e-4ff4-8aec-e8f98a296faf |
| scout_fl_spr_12d_sens_p13_paxv | :135 | 32047c30-e368-462d-ab80-aa7d1d038c8c |
| scout_fl_spr_12d_sens_p13_mixv | :136 | db3d05ec-53e2-4366-a773-41284698876c |
| scout_fl_spr_12d_sens_p14_crewv | :137 | 3f821738-5867-4d85-afda-0e14051f50c8 |
| scout_fl_spr_12d_sens_p14_paxv | :138 | dbd2eb6c-2b85-43d9-8f27-4b263fa0c973 |
| scout_fl_spr_12d_sens_p14_mixv | :139 | 1664cf5c-71aa-4378-9a89-464b29233947 |
| scout_fl_spr_12d_sens_p15_crewv | :140 | b50cf564-2125-4835-9d8b-3e90a0536215 |
| scout_fl_spr_12d_sens_p15_paxv | :141 | cfa10c4b-546e-4d23-82b7-fd7e130f5e7e |
| scout_fl_spr_12d_sens_p15_mixv | :142 | 32649c30-80d7-44d2-b582-72d0c654684e |
| scout_fl_spr_12d_sens_p16_crewv | :143 | 81899586-8c5b-45ec-afc1-6b2d8ba36feb |
| scout_fl_spr_12d_sens_p16_paxv | :144 | e35907b1-b7ef-46d6-8449-0b79da991487 |
| scout_fl_spr_12d_sens_p16_mixv | :145 | 886fc569-102b-4bf2-853e-64fda9ddaedd |
