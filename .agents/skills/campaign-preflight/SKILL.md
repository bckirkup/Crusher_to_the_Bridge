---
name: campaign-preflight
description: The fixed gate that must pass before any Crusher campaign array is submitted — local smoke proving the config override reaches the engine and the output contract is unchanged, --dry-run count matching the design file, explicit job-definition revision and image digest (never a bare tag), manifest present in S3, one canary child inspected, then the array with an ETA — plus the rule that admissibility criteria are frozen in the design file before any cell runs and that a campaign is not complete until its readout and decision are delivered. Use before every campaign submission, local or AWS Batch.
---

# Campaign preflight

`.agents/skills/mega-cruise-campaign-local/SKILL.md` owns local campaign
mechanics; `.agents/skills/aws-batch-campaign/SKILL.md` owns the AWS deploy;
`.agents/skills/campaign-results-analysis/SKILL.md` owns the readout. **Neither
of the first two owns the gate between them.** This skill is that gate: the
fixed sequence between "I have a design" and "the array is running", and the
two rules that bracket it.

Run the steps in order. Do not skip a step because the change looks small —
every step below exists because skipping it burned a full array.

## Rule A (before step 1): freeze the criteria in the design file

Every admissibility criterion, threshold, interval and selection rule must be
written into the design/manifest file **before the first cell runs**, along
with which quantities are reported-but-never-selected-on. This is the existing
practice: `covid_theta_screen_v7_readout.md` records that the criteria were "in
the design file before any cell ran", and that "no criterion in the design file
was altered after the surface was seen". A criterion invented after the surface
exists is not a criterion, it is a description of the surface.

Write into the design file:

- the selection criterion and its threshold (e.g. `covid.T1` as sole selector);
- the audit invariants that make a deviation a defect rather than a failed
  criterion (e.g. `index_onset_day == -1.0` on every seed);
- the diagnostics that are reported and never selected on;
- later stages and what gates them (e.g. stage 2 gated on a non-empty stage-1
  shortlist).

Design and manifest files live beside the runner in
`picard_framework/runs/mega_cruise_campaign/` (`*_design.json`,
`*_manifest.json`) and are expanded by `expand_design.py`. For a Batch run the
design must be **inside the image** — see step 3.

## Step 1: local smoke, proving two things

A smoke that merely exits 0 proves nothing. The smoke must prove **both**:

1. **The config override reaches the engine.** Run one cell of the actual
   design locally and assert the swept value is the value the engine used —
   read it back from `summary.json`'s `parameters`/`derived` block in the
   result zip, not from the spec you passed in. The
   campaign-results-analysis skill's "Check the swept axis resolved (do this
   first)" section exists because a sweep whose axis silently did not resolve
   produces a perfectly clean, perfectly meaningless surface.
2. **The output contract is unchanged.** The analysis step downstream reads
   fixed keys; assert the smoke's zip still contains `run_spec.json`,
   `summary.json` and `timeseries.json` and that any new field the readout
   needs is actually present. A campaign that runs to completion and then
   cannot be aggregated has to be re-run in full.

```bash
RUNNER=picard_framework/runs/mega_cruise_campaign/campaign_runner.py
python3 "$RUNNER" --smoke                    # destroyer, 2 epochs, 20 agents
python3 "$RUNNER" --tier t1 --limit 1 --epochs 6 --num-agents 100
```

Cost: seconds to a couple of minutes. There is no campaign small enough to
justify skipping it.

## Step 2: `--dry-run` count matches the design file

```bash
python3 "$RUNNER" --dry-run                  # expect the design's cell count
python3 "$RUNNER" --dry-run --shard-count 4 --shard-index 0
```

The printed count must equal the number of cells the design file says exist
(the full matrix is ~17,780; a screen is whatever its design declares — 770,
1,680, 3,080). If it does not, the manifest you are about to ship is not the
design you wrote, and every downstream number is about a different experiment.
`tests/test_mega_cruise_campaign.py` is the behaviour lock for the dry-run
cartesian; a count mismatch after an iterator edit usually shows there too.

Also dry-run the shard split you intend to submit: shards must be disjoint and
sum to the total.

## Step 3: resolve the job-definition revision and the image digest explicitly

**Never submit against a bare tag.** `submit-job --job-definition
picard-campaign` uses the latest ACTIVE revision *at submit time*, and a bare
`picard-campaign` image tag resolves to whatever was last pushed under that
name. A bare `picard-campaign` tag once resolved to a stale revision whose
image did not contain the campaign manifest, and **66 array children died** —
every one of them failing for the same reason, discovered only after the array
had run.

Before submitting:

```bash
# 1. register the new revision FIRST, then read back what exists
aws --profile picard batch describe-job-definitions \
  --job-definition-name picard-campaign --status ACTIVE --region us-east-1 \
  --query "jobDefinitions[-1].[revision,containerProperties.image,containerProperties.resourceRequirements]"

# 2. resolve the image to a digest, not a tag
aws --profile picard ecr describe-images --repository-name picard-campaign \
  --image-ids imageTag=<TAG> --region us-east-1 \
  --query "imageDetails[0].[imageDigest,imagePushedAt]"
```

Submit with the pinned revision (`picard-campaign:<REV>`), and record both the
revision and the `sha256:` digest in the design's handoff/readout header. Then
confirm the design file and manifest are actually *in* that image — build the
image from a `main` that contains them (the v8 Theta screen handoff records
exactly this requirement: "the design must be *inside* the image").

After submission, verify what the running job actually picked up:

```bash
aws --profile picard batch describe-jobs --jobs <jobId> --region us-east-1 \
  --query "jobs[0].jobDefinition"
```

## Step 4: confirm the manifest is present in S3

```bash
AWS_PROFILE=picard aws s3 ls s3://<bucket>/campaign/<design>/ --recursive | head
```

The shard uploader writes `<suffix>.zip` + `<suffix>.manifest.json` per shard;
the prefix must be empty of stale artifacts from a previous run of the same
design (or use a new prefix — prefix reuse silently mixes two experiments in
the aggregation step). Record the exact S3 prefix; it belongs in the handoff
ledger and the readout header.

## Step 5: one canary child, output inspected

Submit **one** array child (or one non-array job over one shard index), wait
for it to reach SUCCEEDED, sync its output, and open it:

```bash
AWS_PROFILE=picard aws s3 sync s3://<bucket>/campaign/<design>/ ./results/<design>/
python3 -c "import json,zipfile;z=zipfile.ZipFile('results/<design>/shard-0.zip');print(z.namelist()[:5])"
```

Check the same two things as step 1 — swept value resolved, output contract
intact — plus that the run is not degenerate (non-zero epochs, plausible
attack rate, the witness counters for whatever mechanism the design is about
are non-zero; see `.agents/skills/transmission-blocker-cascade/SKILL.md`
Hard rule 1). A canary costs one child's wall clock. An array costs all of it.

## Step 6: submit the array, and report the ETA at submission

```bash
AWS_PROFILE=picard ./deploy/aws/submit_array_job.sh <N> s3://<bucket>/campaign/<design>/
```

At submit time, send the user: the design name, the cell count, the parent
array job ID, the S3 prefix, the pinned job-definition revision and image
digest, and the **ETA** — cells ÷ concurrency × per-cell wall clock from the
canary. A campaign whose ETA is only discovered at completion cannot be
planned around, and a multi-hour array launched without an announced ETA has
repeatedly been the last thing a session did before it died.

While it runs, classify failures rather than eyeballing them:

```bash
AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \
  --job-id <parentArrayJobId> --region us-east-1 --out-json failure_report.json
```

## Rule B (after the last cell): the campaign is not complete at 100%

A campaign is complete when **all** of the following are true:

1. every cell has completed or been classified as a known failure mode;
2. the canonical readout section is written into `docs/` — a
   `docs/<pathogen>/<design>_readout.md` with its `main` SHA header, plus the
   ledger entry under `docs/ledger/<ID>.md` per `docs/ledger/README.md`
   (`Measured at:` SHA required for anything reporting numbers);
3. the open ledger (`docs/norovirus/norovirus_open_ledger.md` §1 or
   `docs/covid/covid_open_ledger.md` §1) is updated in the same change if the
   result voids a recorded measurement;
4. **the interpretation and the next decision have been sent to the user.**

A clean 770/770-cell campaign has been lost to exactly the gap between (1) and
(2): the cells ran, the numbers existed, and nothing was written down where the
next session could find it. Steps 2-4 are not paperwork; they are the only part
of the campaign that survives the session
(`.agents/skills/session-handoff-ledger/SKILL.md`).

## Related

- `.agents/skills/mega-cruise-campaign-local/SKILL.md` — local run mechanics.
- `.agents/skills/aws-batch-campaign/SKILL.md` — deploy gotchas; `deploy/aws/README.md` is the command reference.
- `.agents/skills/campaign-results-analysis/SKILL.md` — aggregation, Stan, failure classification, definition of done.
- `.agents/skills/stochastic-attribution/SKILL.md` — seed and replicate design, to be fixed in the design file at Rule A.
- `.agents/skills/informative-shard-ordering/SKILL.md` — `--order informative` and `--stop-rule` when wall clock may be cut short.
