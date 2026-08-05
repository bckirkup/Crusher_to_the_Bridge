#Requires -Version 5.1
<#
.SYNOPSIS
  Submit the multi-platform calibration wave-1 campaign to AWS Batch Fargate Spot.

.DESCRIPTION
  Registers nothing — assumes picard-campaign job definition already includes
  Ref::manifest (see batch_job_definition.json) and that the ECR image contains
  calibration_manifest_v1.json + deferred C2 support.

  Wave-1 = c1 + c3 + c4 (~2360 runs). c2 stays deferred until dose is pinned.

.EXAMPLE
  $env:AWS_PROFILE = 'picard'
  .\deploy\aws\submit_calibration.ps1 -ShardCount 80

.EXAMPLE
  .\deploy\aws\submit_calibration.ps1 -ShardCount 80 -Bucket crusherbucket-994254241749-us-east-1-an
#>
param(
  [int]$ShardCount = 80,
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Prefix = 'campaign/calibration_v1/',
  [string]$JobQueue = 'picard-campaign-queue',
  [string]$JobDefinition = 'picard-campaign',
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [string]$Manifest = 'picard_framework/runs/mega_cruise_campaign/calibration_manifest_v1.json',
  [string]$JobName = ''
)

$ErrorActionPreference = 'Stop'

# Optional local secrets file (gitignored)
$envFile = Join-Path $PSScriptRoot '.env'
if ((-not $Bucket) -and (Test-Path $envFile)) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_ -split '=', 2
    $k = $k.Trim(); $v = $v.Trim().Trim('"').Trim("'")
    if ($k -eq 'CAMPAIGN_BUCKET' -or $k -eq 'BUCKET') { $Bucket = $v }
    if ($k -eq 'AWS_PROFILE' -and -not $env:AWS_PROFILE) { $AwsProfile = $v }
    if ($k -eq 'AWS_REGION' -and -not $env:AWS_REGION) { $Region = $v }
  }
}

if (-not $Bucket) {
  throw 'Set -Bucket or CAMPAIGN_BUCKET / BUCKET in deploy/aws/.env'
}
if ($ShardCount -lt 2 -or $ShardCount -gt 10000) {
  throw "AWS Batch array size must be 2..10000 (got $ShardCount)"
}

$s3Prefix = "s3://$Bucket/$($Prefix.TrimStart('/'))"
if (-not $JobName) {
  $JobName = "picard-calibration-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

Write-Host "Submitting calibration wave-1 array job:"
Write-Host "  name        : $JobName"
Write-Host "  queue       : $JobQueue"
Write-Host "  definition  : $JobDefinition"
Write-Host "  array size  : $ShardCount"
Write-Host "  s3 prefix   : $s3Prefix"
Write-Host "  manifest    : $Manifest"
Write-Host "  profile     : $AwsProfile"

$params = "shard_count=$ShardCount,s3_prefix=$s3Prefix,manifest=$Manifest"
$jobId = aws --profile $AwsProfile batch submit-job `
  --job-name $JobName `
  --job-queue $JobQueue `
  --job-definition $JobDefinition `
  --array-properties "size=$ShardCount" `
  --parameters $params `
  --region $Region `
  --query 'jobId' `
  --output text

if ($LASTEXITCODE -ne 0 -or -not $jobId) {
  throw 'submit-job failed'
}

Write-Host "jobId=$jobId"
Write-Host "Monitor:"
Write-Host "  .\deploy\aws\monitor_campaign.ps1 -JobId $jobId -Bucket $Bucket -Prefix $Prefix -Watch"
