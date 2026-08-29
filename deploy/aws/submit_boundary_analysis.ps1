#Requires -Version 5.1
<#
.SYNOPSIS
  Submit a boundary analysis phase job (surface | stan | mc | report).

.EXAMPLE
  .\deploy\aws\submit_boundary_analysis.ps1 -Phase surface

.EXAMPLE
  .\deploy\aws\submit_boundary_analysis.ps1 -Phase stan -Pathogen norovirus

.EXAMPLE
  .\deploy\aws\submit_boundary_analysis.ps1 -Phase mc -Pathogen influenza
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('bundle', 'surface', 'stan', 'mc', 'report')]
  [string]$Phase,
  [string]$Pathogen = 'norovirus',
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$CampaignPrefix = 'campaign/boundary_surface_v1/',
  [string]$AnalysisPrefix = 'campaign/boundary_surface_v1/analysis/',
  [string]$JobQueue = '',
  [string]$ComputeQueue = 'picard-analysis-queue',
  [string]$MemoryQueue = 'picard-analysis-memory-queue',
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [int]$NMc = 2000,
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

$s3Campaign = "s3://$Bucket/$($CampaignPrefix.TrimStart('/'))"
$s3Analysis = "s3://$Bucket/$($AnalysisPrefix.TrimStart('/'))"

# Aggregation phases hold a whole campaign frame in RAM and take the
# memory-optimised pathway; the fits are core-bound and take the compute one.
if (-not $JobQueue) {
  $JobQueue = if ($Phase -in @('bundle', 'surface', 'report')) { $MemoryQueue } else { $ComputeQueue }
}

$jobDef = switch ($Phase) {
  'bundle' { 'picard-boundary-surface' }  # same sizing as surface export
  'surface' { 'picard-boundary-surface' }
  'stan' { 'picard-boundary-stan' }
  'mc' { 'picard-boundary-mc' }
  'report' { 'picard-boundary-mc' }
}

if (-not $JobName) {
  $JobName = "picard-boundary-$Phase-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

$params = "s3_campaign=$s3Campaign,s3_analysis=$s3Analysis,pathogen=$Pathogen,n_mc=$NMc,seed=$Seed,chains=4,iter_warmup=1000,iter_sampling=1000"

Write-Host "Submitting boundary analysis job:"
Write-Host "  phase=$Phase pathogen=$Pathogen def=$jobDef queue=$JobQueue"

# Job defs bake a default --phase; override when the phase is not the def default.
if ($Phase -in @('report', 'bundle')) {
  $overFile = Join-Path $env:TEMP 'boundary-container-overrides.json'
  ('{"command":["deploy/aws/boundary_analysis_entrypoint.py","--phase","' + $Phase + '","--pathogen","' + $Pathogen + '","--s3-campaign","' + $s3Campaign + '","--s3-analysis","' + $s3Analysis + '"]}') | Set-Content -NoNewline $overFile
  $jobId = aws --profile $AwsProfile batch submit-job `
    --job-name $JobName `
    --job-queue $JobQueue `
    --job-definition $jobDef `
    --parameters $params `
    --container-overrides "file://$overFile" `
    --region $Region `
    --query 'jobId' `
    --output text
} else {
  $jobId = aws --profile $AwsProfile batch submit-job `
    --job-name $JobName `
    --job-queue $JobQueue `
    --job-definition $jobDef `
    --parameters $params `
    --region $Region `
    --query 'jobId' `
    --output text
}

if ($LASTEXITCODE -ne 0 -or -not $jobId) { throw 'submit-job failed' }
Write-Host "jobId=$jobId"
