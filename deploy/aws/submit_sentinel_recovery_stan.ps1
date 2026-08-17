#Requires -Version 5.1
<#
.SYNOPSIS
  Submit the 72-cell sentinel recovery Stan array on On-Demand Fargate.

.DESCRIPTION
  Requires analysis extract already on S3 under
  campaign/sentinel_synthetic_recovery_v1/analysis/{cells.json,manifests,voyages}.

.EXAMPLE
  .\deploy\aws\submit_sentinel_recovery_stan.ps1

.EXAMPLE
  .\deploy\aws\submit_sentinel_recovery_stan.ps1 -Phase score
#>
param(
  [ValidateSet('fit', 'score')]
  [string]$Phase = 'fit',
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$AnalysisPrefix = 'campaign/sentinel_synthetic_recovery_v1/analysis/',
  [string]$JobQueue = 'picard-analysis-queue',
  [string]$JobDefinition = 'picard-sentinel-recovery-stan',
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [int]$ArraySize = 72,
  [int]$Chains = 2,
  [int]$IterWarmup = 400,
  [int]$IterSampling = 400,
  [int]$Seed = 1701,
  [string]$JobName = ''
)

$ErrorActionPreference = 'Stop'

$envFile = Join-Path $PSScriptRoot '.env'
if ((-not $Bucket) -and (Test-Path $envFile)) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_ -split '=', 2
    $k = $k.Trim(); $v = $v.Trim().Trim('"').Trim("'")
    if ($k -eq 'CAMPAIGN_BUCKET' -or $k -eq 'BUCKET') { $Bucket = $v }
  }
}
if (-not $Bucket) { throw 'Set -Bucket or CAMPAIGN_BUCKET' }

$s3Analysis = "s3://$Bucket/$($AnalysisPrefix.TrimStart('/'))"
if (-not $JobName) {
  $JobName = "picard-sentinel-recovery-$Phase-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

$params = "s3_analysis=$s3Analysis,chains=$Chains,iter_warmup=$IterWarmup,iter_sampling=$IterSampling,seed=$Seed"

Write-Host "Submitting sentinel recovery Stan:"
Write-Host "  phase=$Phase def=$JobDefinition queue=$JobQueue"
Write-Host "  s3=$s3Analysis"

if ($Phase -eq 'score') {
  $overFile = Join-Path $env:TEMP 'sentinel-recovery-score-overrides.json'
  ('{"command":["deploy/aws/sentinel_recovery_analysis_entrypoint.py","--phase","score","--s3-analysis","' + $s3Analysis + '"]}') | Set-Content -NoNewline $overFile
  $jobId = aws --profile $AwsProfile batch submit-job `
    --job-name $JobName `
    --job-queue $JobQueue `
    --job-definition $JobDefinition `
    --parameters $params `
    --container-overrides "file://$overFile" `
    --region $Region `
    --query 'jobId' `
    --output text
} else {
  $jobId = aws --profile $AwsProfile batch submit-job `
    --job-name $JobName `
    --job-queue $JobQueue `
    --job-definition $JobDefinition `
    --array-properties "size=$ArraySize" `
    --parameters $params `
    --region $Region `
    --query 'jobId' `
    --output text
}

if ($LASTEXITCODE -ne 0 -or -not $jobId) { throw 'submit-job failed' }
Write-Host "jobId=$jobId"
if ($Phase -eq 'fit') {
  Write-Host "arraySize=$ArraySize (AWS_BATCH_JOB_ARRAY_INDEX -> sorted cells.json)"
}
