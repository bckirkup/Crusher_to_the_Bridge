#Requires -Version 5.1
<#
.SYNOPSIS
  Submit the boundary_surface_v1 Tier-1 Spot campaign to AWS Batch.

.DESCRIPTION
  Wave-1 = b1_* (10,000 runs; b2_* deferred). Uses existing picard-campaign
  job definition + Fargate Spot queue. Rebuild/push the ECR image after
  adding boundary_surface_v1_manifest.json.

.EXAMPLE
  $env:AWS_PROFILE = 'picard'
  .\deploy\aws\submit_boundary_surface.ps1 -ShardCount 200

.EXAMPLE
  .\deploy\aws\submit_boundary_surface.ps1 -ShardCount 200 -IncludeDeferred
#>
param(
  [int]$ShardCount = 200,
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Prefix = 'campaign/boundary_surface_v1/',
  [string]$JobQueue = 'picard-campaign-queue',
  [string]$JobDefinition = 'picard-campaign',
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [string]$Manifest = 'picard_framework/runs/mega_cruise_campaign/boundary_surface_v1_manifest.json',
  [string]$JobName = '',
  [switch]$IncludeDeferred
)

$ErrorActionPreference = 'Stop'

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
  $JobName = "picard-boundary-surface-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

Write-Host "Submitting boundary_surface_v1 array job:"
Write-Host "  name        : $JobName"
Write-Host "  queue       : $JobQueue"
Write-Host "  definition  : $JobDefinition"
Write-Host "  array size  : $ShardCount"
Write-Host "  s3 prefix   : $s3Prefix"
Write-Host "  manifest    : $Manifest"
Write-Host "  profile     : $AwsProfile"
Write-Host "  deferred    : included=$IncludeDeferred (default wave-1 = b1 only)"

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
if ($IncludeDeferred) {
  Write-Host "NOTE: -IncludeDeferred is informational; submit a dedicated deferred wave with containerOverrides --include-deferred if needed."
}
