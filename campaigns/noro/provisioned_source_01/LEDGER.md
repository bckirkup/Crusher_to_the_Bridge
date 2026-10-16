# NORO-PROVISIONED-SOURCE-01 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Mechanism
contract: `docs/provisioned_source_01_design.md`. Frozen eval design:
`docs/norovirus/noro_provisioned_source_01_sweep_design.md`. Ledger
entry: `docs/ledger/PROVISIONED-SOURCE-01.md`. Mega spec:
`campaigns/noro/provisioned_source_01_mega/` (same manifest, elevated
memory — AGE-FOOD split precedent).

**Grid:** 3 small hulls × 12 arms + mega × 10 arms × 1,000 seeds =
46,000 cells + ~128 canary. Seeds exp 8000–8999, cls/spr/mega
8105–9104 (SCORE-01 lists). Fixed coordinates: shipped bp
0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65, dose 7.57,
embarkation 2026-01-10.

**Submit gate:** NO cells submit until the implementation leg lands
the `provisioned_source` mechanism + witness fields
(`common_source.provisioned_source` voyage block,
`provisioned_source_id` on object rows, `reported_cases_by_dominant_route`
summary) and the image pins a SHA containing them. Canary (~128
cells) then STOP — user gates wave 1.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 6 exp + 1 meg | 128 | submitted 2026-10-16 |
| 1 | exp ×12 arms | 12,000 | not submitted |
| 2 | cls + spr ×12 arms | 24,000 | not submitted |
| 3 | mega ×10 arms | 10,000 | not submitted |

## Readout log

### canary — submitted 2026-10-16, awaiting cells

Image `picard-campaign:noro-provisioned-source01@sha256:97d99be4c1abf362af1f9914f476740bd1086e7b73491b371f8741bfb1ac95de`
(pinned in campaign.json `image_tag`; ENGINE_GIT_SHA=a9f4a517).
Manifest mirrored to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_source_01/manifest.json`.

| block | jobdef | cells | job id |
|---|---|---|---|
| canary_exp_mint | picard-noro-provisioned-source-01:1 | 48 | 970ef763-ef33-4d65-830e-9451eb8860f3 |
| canary_exp_q30 | :2 | 24 | 69cbe84b-2bf5-4126-8f25-5289aba99ee2 |
| canary_exp_q03 | :3 | 24 | f270b39b-0e83-45f0-86b6-5b3fafdd0775 |
| canary_exp_ps_ship | :4 | 8 | 157f3d0a-a38e-45c8-8579-e6368c9640ab |
| canary_exp_ind | :5 | 8 | 84c16c5c-e3ed-49f1-a300-d9dd61a2638d |
| canary_exp_off | :6 | 4 | 9c70c1d1-45c4-4505-abe9-4f39fc7200f7 |
| canary_meg_q30 | picard-noro-provisioned-source-01-mega:1 | 12 | bf212817-ce81-4323-b269-421996164788 |

Canary gates (design §5.3-2 as amended A1): q-source echo present in
run provenance; provisioned_source witness blocks (stations/objects)
written; minted-set parity vs landed mint cells per shared seed;
objects-bind-stations consistency; mega cells RSS within 8192 MB.
