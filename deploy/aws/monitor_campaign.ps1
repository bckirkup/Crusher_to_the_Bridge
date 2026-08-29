#Requires -Version 5.1
<#
.SYNOPSIS
  Monitor an AWS Batch EC2 Spot campaign array job.

.DESCRIPTION
  Prints Batch array statusSummary plus a completed-run count from the
  shard-scoped resume logs under the campaign prefix. Children stay RUNNING
  until their entire shard finishes, so SUCCEEDED can stay 0 for a long time.

  Set AWS_PROFILE (e.g. picard or your SSO PowerUser profile) and pass
  -Bucket (or set CAMPAIGN_BUCKET). Optionally copy deploy/aws/.env.example
  to deploy/aws/.env (gitignored); this script loads it automatically.
  Never commit real account IDs / bucket names into the repo.

.EXAMPLE
  $env:AWS_PROFILE = 'picard'
  $env:CAMPAIGN_BUCKET = 'my-campaign-bucket'
  .\deploy\aws\monitor_campaign.ps1 -JobId <jobId> -Watch -IntervalSec 60

.EXAMPLE
  .\deploy\aws\monitor_campaign.ps1 -JobId <jobId> -Bucket my-campaign-bucket `
    -Prefix campaign/mega_cruise_v4_bold/ -Watch
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$JobId,

  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Prefix = "campaign/",
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
  [Alias('Profile')]
  [string]$AwsProfile = $env:AWS_PROFILE,
  [switch]$Watch,
  [int]$IntervalSec = 60,
  [switch]$Classify
)

$ErrorActionPreference = "Stop"

# Load deploy/aws/.env (KEY=VALUE) into process env if present; do not override
# values already set in the shell or passed as parameters.
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path -LiteralPath $envFile) {
  Get-Content -LiteralPath $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $k = $line.Substring(0, $eq).Trim()
    $v = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
    if (-not [string]::IsNullOrWhiteSpace($k) -and -not [Environment]::GetEnvironmentVariable($k, "Process")) {
      [Environment]::SetEnvironmentVariable($k, $v, "Process")
    }
  }
  if (-not $Bucket) { $Bucket = $env:CAMPAIGN_BUCKET }
  if (-not $AwsProfile) { $AwsProfile = $env:AWS_PROFILE }
  if ($Region -eq "us-east-1" -and $env:AWS_REGION) { $Region = $env:AWS_REGION }
  elseif ($Region -eq "us-east-1" -and $env:AWS_DEFAULT_REGION) { $Region = $env:AWS_DEFAULT_REGION }
}

if (-not $Bucket) {
  throw "Set -Bucket or env CAMPAIGN_BUCKET (or create deploy/aws/.env from .env.example)."
}

$Prefix = $Prefix.TrimEnd('/') + '/'

function AwsArgs {
  $a = @("--region", $Region)
  if ($AwsProfile) { $a = @("--profile", $AwsProfile) + $a }
  return $a
}

function Get-StatusSummary {
  $raw = aws @(AwsArgs) batch describe-jobs --jobs $JobId `
    --query "jobs[0].{status:status,statusReason:statusReason,summary:arrayProperties.statusSummary,size:arrayProperties.size,jobDefinition:jobDefinition}" `
    --output json
  if ($LASTEXITCODE -ne 0) { throw "describe-jobs failed for $JobId" }
  return ($raw | ConvertFrom-Json)
}

function Get-CompletedRunCount {
  $resumePrefix = "s3://$Bucket/${Prefix}_resume/"
  $output = @(aws @(AwsArgs) s3 ls $resumePrefix --recursive 2>&1)
  if ($LASTEXITCODE -ne 0) {
    if ($output.Count -eq 0) { return 0 }
    throw "S3 listing failed for $resumePrefix`: $($output -join ' ')"
  }
  $keys = @(
    $output | ForEach-Object {
      $key = ($_ -split '\s+')[-1]
      if ($key -match 'completed_runs\.[^/]+\.txt$') { $key }
    }
  )
  $count = 0
  foreach ($key in $keys) {
    $lines = @(aws @(AwsArgs) s3 cp "s3://$Bucket/$key" - 2>&1)
    if ($LASTEXITCODE -ne 0) {
      if ($lines.Count -eq 0) { continue }
      throw "S3 download failed for s3://$Bucket/$key`: $($lines -join ' ')"
    }
    $count += @($lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count
  }
  return $count
}

function Show-Snapshot {
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $info = Get-StatusSummary
  $runs = Get-CompletedRunCount
  $shards = @(aws @(AwsArgs) s3 ls "s3://$Bucket/${Prefix}_resume/" --recursive 2>$null |
    Select-String 'completed_runs\.[^/]+\.txt$').Count
  $s = $info.summary
  Write-Host ("{0} status={1} size={2} SUBMITTED={3} PENDING={4} RUNNABLE={5} STARTING={6} RUNNING={7} SUCCEEDED={8} FAILED={9} runs={10} shards={11}" -f `
    $ts, $info.status, $info.size, `
    $s.SUBMITTED, $s.PENDING, $s.RUNNABLE, $s.STARTING, $s.RUNNING, $s.SUCCEEDED, $s.FAILED, $runs, $shards)
  if ($info.statusReason) {
    Write-Host ("  statusReason: {0}" -f $info.statusReason)
  }
  Write-Host ("  jobDefinition: {0}" -f $info.jobDefinition)
  Write-Host ("  s3://{0}/{1}<shard-*.zip|shard-*.manifest.json>" -f $Bucket, $Prefix)
  return $info
}

Write-Host "Monitoring Batch array job $JobId (profile=$AwsProfile region=$Region)"
do {
  $info = Show-Snapshot
  if ($Classify) {
    $root = Split-Path -Parent $PSScriptRoot
    if (-not $root) { $root = (Get-Location).Path }
    $clf = Join-Path $PSScriptRoot "classify_batch_failures.py"
    Write-Host "--- classify_batch_failures ---"
    $env:AWS_PROFILE = $AwsProfile
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
