# Edison solver comparison return

> **Status** Measured existing-output reduction and verified collector fetch.
> Authored against `b925a99cfce4514346d1659cc260de4a43522543` on 2026-11-21.
> Protected Actions delivery still requires the `aws-campaign` reviewer.

## Automated access

The existing `campaign-collect` workflow accepts `solver_return=true`.
One dispatch fetches these two approved aggregate outputs into the
`edison-solver-comparison` Actions artifact. Edison can download it with
its GitHub connector. The environment retains its required reviewer,
`bckirkup`. This return has its own concurrency group because the weekly
inventory has been awaiting review since November 9.

| Output | Bytes | SHA-256 |
|---|---:|---|
| `contam_fleet_workup_77_package_02.tar.gz` | 4,575,643 | `3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d` |
| `seed_endpoints.csv` | 26,153 | `0a990ce55e71776b054c1d403ef6dac01be5c83df1fde67ddd47a9f2723cd8c8` |

Both objects remain in `crusherbucket-994254241749-us-east-1-an`.
Their exact keys are pinned in `scripts/campaign_collect_exact.py`.
The seed table was recovered from the 140 original payloads, matched the
2026-11-20 readout hash, and was stored at
`campaign/covid_transport_fit_01/return/paired_01/seed_endpoints.csv`
with create-only upload and a SHA-256 checksum. Each row describes one
seed's voyage-wide endpoints. The engineering archive supplies its own
standard-library verifier.

The fetch checks expected byte counts and SHA-256 digests and pins GET to
the version or ETag returned by HEAD. The reviewed return performs two
object fetches. It leaves the inventory and issue-posting steps idle.
The artifact expires after 30 days and can be regenerated from the
durable S3 objects.

```sh
gh workflow run campaign_collect.yml -f solver_return=true
```

For a review branch, add `--ref <branch>`. After the environment review
and successful run, download with
`gh run download <run-id> -n edison-solver-comparison`.

## Paired interpretation

The [paired readout](../campaigns/covid/transport_fit_01/READOUT_PAIRED.md)
already contains the endpoint means and pointwise paired-t 95% intervals,
observed arm and difference ranges, undefined-denominator handling,
leave-one-seed-out influence checks, and directional threshold
discordance. Its seed table and all six base-table hashes were reproduced
on 2026-11-21. Its verifier passed all 21 checks. The engineering
archive passed all 51 checks.

The TRANSPORT-FIT-01 respiratory replays used Mega as the DP substitution hull
and Expedition as the GM substitution hull. They retain their original
inputs, seeds and image identities. The specific `diamond_princess` and
`greg_mortimer` platforms are distinct models.

| Existing comparison | Paired mean difference, ContamX − native | Observed difference range | Threshold discordance |
|---|---|---|---|
| Mega / DP, 20 pairs, recorded onsets | +1.70, 95% interval −2.54 to +5.94 | −9 to +39 | 0/20 |
| Expedition / GM, 50 pairs, campaign positives | −0.48, 95% interval −1.83 to +0.87 | −15 to +10 | 0/50 |

The threshold is the original campaign's ≥10 recorded onsets. The
one-sided exact 95% upper bounds on the probability of discordance are
0.139 and 0.058. The DP onset mean changes sign when one influential
pair is omitted. These observations support low observed provider
sensitivity on these cases. No equivalence margin was declared.

Delivered-pathway relevance remains limited by the retained telemetry.
The original cells retain configuration echoes and attribution of
incident infections during the observation window. Both provider arms
contain HVAC-attributed events in the Expedition replay. The Mega
ContamX arm recorded none in its window. An event establishes that the
route contributed in that run. A zero tally does not establish zero
delivered exposure. The seed endpoint table lacks a
complete emitted-to-delivered mass budget across routes. Infection
attribution labels condition on infection and collapse competing
contributions. Pooled confirmations supply an observation endpoint.
Neither quantity establishes preserved delivered dose or determines
which repair changed outbreak frequency.

The handoff and ledgers have been corrected accordingly. A selected
historical outbreak provides one realized voyage and supplies no
empirical takeoff probability. The provider comparison and the separate
native-only repair-toggle experiment retain their own scopes.

## Four-hull timing and full-job accounting

The engineering timing table in the paired readout covers all four
generic cruise hulls. These medians are from five measured repeats on
the baseline, each after a warm-up. Units below are milliseconds.

| Hull | Cold pipeline native / ContamX | Whole cold process native / ContamX | Repeated aggregate native / ContamX | Paired respiratory full-job timing |
|---|---|---|---|---|
| Expedition | 15.2 / 70.6 | 839.7 / 900.5 | 6.2 / 5.3 | recovered |
| Classic | 37.6 / 157.8 | 864.4 / 984.3 | 27.6 / 23.5 | unavailable |
| Spirit | 89.4 / 316.6 | 923.1 / 1,151.6 | 74.6 / 71.7 | unavailable |
| Mega | 203.3 / 588.7 | 1,101.0 / 1,477.3 | 198.4 / 179.9 | recovered |

Compare within each row. Hosts and cohorts differ across hulls.
Repeated aggregate work reuses a built engine. A full respiratory voyage
has different computation and overhead.

AWS `DescribeJobs` recovered all original 140 child records on
2026-11-21. Every child requested 1 vCPU and 4,096 MiB and had one
successful attempt. Resource-hours below are requested allocation
multiplied by elapsed RUNNING time.

| Hull and provider | Children | RUNNING median seconds | Observed seconds range | Allocated vCPU-hours | Allocated GiB-hours |
|---|---:|---:|---|---:|---:|
| Mega native | 20 | 1,199.332 | 1,052.929–1,632.422 | 6.7294 | 26.9177 |
| Mega ContamX | 20 | 1,212.299 | 1,090.907–1,763.862 | 6.9119 | 27.6477 |
| Expedition native | 50 | 53.124 | 39.287–59.261 | 0.7173 | 2.8690 |
| Expedition ContamX | 50 | 53.603 | 38.656–58.362 | 0.7248 | 2.8993 |

For each row, vCPU-hours = sum(`stoppedAt − startedAt`) / 3,600,000.
GiB-hours = 4 × vCPU-hours. The independently rebuilt
`batch_children.csv` hash is
`01265430f1d8f1f56cea737a50e2a33ae14e484cb18dc0ad67ab4dc25f2622d2`.
The original four parent IDs are in the paired readout's `PARENT_JOBS`
constant and campaign ledger.

RUNNING time includes interpreter startup, design loading, the voyage,
ContamX binary fetch where applicable and upload. Queue delay and image
pull precede this interval. Median creation-to-start delays were 104.889
seconds for Mega native, 179.803 for Mega ContamX, 107.462 for Expedition
native and 127.130 for Expedition ContamX. These combine scheduling,
provisioning and image-pull effects. A per-phase voyage profile was not
retained.

Jobs shared hosts, ran at different times, and the Mega pair used two
image digests. Allocated resource-hours supply a reproducible accounting
unit. Dollar cost requires instance billing, utilization and allocation
rules. The existing evidence supports no cheapest-provider decision.

Classic also has a four-seed paired influenza probe at an earlier
revision (`FLU-CONTAMX-01`). It measured a different endpoint and
provides no matched Batch timing. Both Classic and Spirit have older
influenza campaigns, including
`flu/open_voyage_01`. Those observations are outside the common
paired-provider replay task. Bounded Batch listings under
`picard-flu-open-voyage*`, `flu-open-voyage*` and
`flu_open_voyage*` returned no retained records. The inspected S3
payloads contain no elapsed-time or job-id field. The Batch log group has
a 14-day retention policy, and this role lacks
`logs:DescribeLogStreams`. Recovery has therefore yielded no
Classic/Spirit full-job timing. Those cells remain unavailable in this
accounting.

## Current cruise-model coverage

The current tree has nine cruise platform directories. This inventory
describes existing coverage and creates no new disease run.

| Platform | Current CONTAM bundle | In original 77-hull engineering archive | TRANSPORT-FIT-01 replay |
|---|---|---|---|
| `classic_cruise_1900` | yes | yes | absent |
| `diamond_princess` | yes | yes | absent on this specific hull |
| `expedition_cruise_300` | absent | excluded | absent |
| `expedition_cruise_450` | yes | yes | GM substitution |
| `explorer_seas_06` | yes | absent from frozen roster | absent |
| `greg_mortimer` | yes | yes | absent on this specific hull |
| `mega_cruise_5000` | yes | yes | DP substitution |
| `messy_cruise_500` | absent | excluded | absent |
| `spirit_cruise_3000` | yes | yes | absent |

The requested all-cruise influenza campaign and a common Classic/Spirit
respiratory comparison remain unperformed. This return stage recovers and
interprets existing results. Museum and historical naval hull coverage
is confined to the whole-hull engineering archive.
