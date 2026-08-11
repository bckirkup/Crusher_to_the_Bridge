#Requires -Version 5.1
<#
.SYNOPSIS
  Submit a mega-cruise campaign manifest as an AWS Batch Fargate Spot array.

.EXAMPLE
  .\deploy\aws\submit_campaign_manifest.ps1 `
    -Manifest picard_framework/runs/mega_cruise_campaign/synthetic_recovery_v1_manifest.json `
    -Prefix campaign/synthetic_recovery_v1/ -ShardCount 200
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$Manifest,
  [Parameter(Mandatory = $true)]
  [string]$Prefix,
  [int]$ShardCount = 200,
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$JobQueue = 'picard-campaign-queue',
  [string]$JobDefinition = 'picard-campaign',
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [string]$JobName = '',
  [string]$Tier = '',
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
if (-not (Test-Path $Manifest)) {
  throw "Manifest not found: $Manifest"
}

$s3Prefix = "s3://$Bucket/$($Prefix.TrimStart('/'))"
$stem = [IO.Path]::GetFileNameWithoutExtension($Manifest)
if (-not $JobName) {
  $JobName = "picard-$stem-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

Write-Host "Submitting campaign array job:"
Write-Host "  name        : $JobName"
Write-Host "  queue       : $JobQueue"
Write-Host "  definition  : $JobDefinition"
Write-Host "  array size  : $ShardCount"
Write-Host "  s3 prefix   : $s3Prefix"
Write-Host "  manifest    : $Manifest"
Write-Host "  profile     : $AwsProfile"

$params = "shard_count=$ShardCount,s3_prefix=$s3Prefix,manifest=$Manifest"

$needOverride = $true
$cmd = @(
  '--manifest', $Manifest,
  '--shard-count', "$ShardCount",
  '--s3-prefix', $s3Prefix,
  '--resume',
  '--timeout', '3600'
)
if ($Tier) { $cmd += @('--tier', $Tier) }
if ($IncludeDeferred) { $cmd += '--include-deferred' }
$cmdJson = ($cmd | ForEach-Object { '"' + ($_ -replace '\\','\\' -replace '"','\"') + '"' }) -join ','
$overFile = Join-Path $env:TEMP 'campaign-manifest-overrides.json'
('{"command":[' + $cmdJson + ']}') | Set-Content -NoNewline $overFile

$jobId = aws --profile $AwsProfile batch submit-job `
  --job-name $JobName `
  --job-queue $JobQueue `
  --job-definition $JobDefinition `
  --array-properties "size=$ShardCount" `
  --parameters $params `
  --container-overrides "file://$overFile" `
  --region $Region `
  --query 'jobId' `
  --output text

if ($LASTEXITCODE -ne 0 -or -not $jobId) {
  throw 'submit-job failed'
}

Write-Host "jobId=$jobId"
Write-Host "Monitor:"
Write-Host "  .\deploy\aws\monitor_campaign.ps1 -JobId $jobId -Bucket $Bucket -Prefix $Prefix -Watch"
