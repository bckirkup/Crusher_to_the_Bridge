#Requires -Version 5.1
<#
.SYNOPSIS
  Monitor an AWS Batch Fargate Spot campaign array job.

.DESCRIPTION
  Prints Batch array statusSummary plus an S3 zip count under the campaign
  prefix. Prefer S3 zip growth for early progress — children stay RUNNING
  until their entire shard finishes, so SUCCEEDED can stay 0 for a long time.

  Set AWS_PROFILE (e.g. picard or your SSO PowerUser profile) and pass
  -Bucket (or set CAMPAIGN_BUCKET). Never commit real account IDs / bucket
  names into the repo.

.EXAMPLE
  $env:AWS_PROFILE = 'picard'
  $env:CAMPAIGN_BUCKET = 'my-campaign-bucket'
  .\deploy\aws\monitor_campaign.ps1 -JobId <jobId> -Watch -IntervalSec 60
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$JobId,

  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Prefix = "campaign/",
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
  [string]$Profile = $env:AWS_PROFILE,
  [switch]$Watch,
  [int]$IntervalSec = 60,
  [switch]$Classify
)

$ErrorActionPreference = "Stop"

if (-not $Bucket) {
  throw "Set -Bucket or env CAMPAIGN_BUCKET (do not hardcode account-specific names in the repo)."
}

function AwsArgs {
  $a = @("--region", $Region)
  if ($Profile) { $a = @("--profile", $Profile) + $a }
  return $a
}

function Get-StatusSummary {
  $raw = aws @(AwsArgs) batch describe-jobs --jobs $JobId `
    --query "jobs[0].{status:status,statusReason:statusReason,summary:arrayProperties.statusSummary,size:arrayProperties.size,jobDefinition:jobDefinition}" `
    --output json
  if ($LASTEXITCODE -ne 0) { throw "describe-jobs failed for $JobId" }
  return ($raw | ConvertFrom-Json)
}

function Get-ZipCount {
  # `aws s3 ls --recursive` follows all pages. Avoid a list-objects-v2 JMESPath
  # count, which returns an error when a new prefix has no Contents property.
  $output = @(aws @(AwsArgs) s3 ls "s3://$Bucket/$Prefix" --recursive 2>&1)
  if ($LASTEXITCODE -ne 0) {
    # AWS CLI v2 returns 1 with no message for an empty prefix.
    if ($output.Count -eq 0) { return 0 }
    throw "S3 listing failed for s3://$Bucket/$Prefix`: $($output -join ' ')"
  }
  return @($output | Select-String '\.zip$').Count
}

function Show-Snapshot {
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $info = Get-StatusSummary
  $zips = Get-ZipCount
  $s = $info.summary
  Write-Host ("{0} status={1} size={2} SUBMITTED={3} PENDING={4} RUNNABLE={5} STARTING={6} RUNNING={7} SUCCEEDED={8} FAILED={9} zips={10}" -f `
    $ts, $info.status, $info.size, `
    $s.SUBMITTED, $s.PENDING, $s.RUNNABLE, $s.STARTING, $s.RUNNING, $s.SUCCEEDED, $s.FAILED, $zips)
  if ($info.statusReason) {
    Write-Host ("  statusReason: {0}" -f $info.statusReason)
  }
  Write-Host ("  jobDefinition: {0}" -f $info.jobDefinition)
  Write-Host ("  s3://{0}/{1}*.zip" -f $Bucket, $Prefix)
  return $info
}

Write-Host "Monitoring Batch array job $JobId (profile=$Profile region=$Region)"
do {
  $info = Show-Snapshot
  if ($Classify) {
    $root = Split-Path -Parent $PSScriptRoot
    if (-not $root) { $root = (Get-Location).Path }
    $clf = Join-Path $PSScriptRoot "classify_batch_failures.py"
    Write-Host "--- classify_batch_failures ---"
    $env:AWS_PROFILE = $Profile
    python $clf --job-id $JobId --region $Region --queue picard-campaign-queue
  }
  if (-not $Watch) { break }
  $done = $info.status -in @("SUCCEEDED", "FAILED")
  if ($done) {
    Write-Host "Parent job reached terminal status $($info.status)."
    break
  }
  Start-Sleep -Seconds $IntervalSec
} while ($true)
