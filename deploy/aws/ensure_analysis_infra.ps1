#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure the EC2 scale-to-zero Batch infra for boundary analysis jobs.

.DESCRIPTION
  Creates the log group and both analysis pathways, then registers the
  analysis job definitions. Does NOT create campaign infra (use
  ensure_campaign_infra.sh for that).

  Two pathways, because the analysis jobs bottleneck differently:
    compute (picard-analysis-queue)        c7i/c7a, 1-2 GiB per vCPU:
                                           CmdStan fits, boundary MC,
                                           sentinel recovery/NUTS.
    memory  (picard-analysis-memory-queue) r7i/r7a, 8 GiB per vCPU:
                                           surface aggregation, which holds a
                                           whole campaign frame in RAM.
  Both sit at minvCpus 0, so neither holds an instance between runs.

  Requires: AWS_PROFILE=picard, ACCOUNT_ID/REGION/BUCKET (or deploy/aws/.env),
  and an existing VPC subnet + security group (same as campaign CE).
#>
param(
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [string]$AccountId = $env:ACCOUNT_ID,
  [string]$SubnetIds = $env:SUBNET_IDS,
  [string]$SecurityGroupIds = $env:SECURITY_GROUP_IDS,
  [string]$QueueName = 'picard-analysis-queue',
  [string]$MemoryQueueName = 'picard-analysis-memory-queue',
  [string]$LogGroup = '/aws/batch/picard-boundary-analysis',
  [ValidateSet('spot', 'on_demand')]
  [string]$Capacity = 'on_demand',
  [int]$MaxVcpus = 256,
  [string]$LaunchTemplate = $env:BATCH_LAUNCH_TEMPLATE,
  [switch]$RegisterOnly
)

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot

$envFile = Join-Path $here '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_ -split '=', 2
    $k = $k.Trim(); $v = $v.Trim().Trim('"').Trim("'")
    if ($k -in @('CAMPAIGN_BUCKET','BUCKET') -and -not $Bucket) { $Bucket = $v }
    if ($k -eq 'AWS_PROFILE' -and -not $env:AWS_PROFILE) { $AwsProfile = $v }
    if ($k -eq 'AWS_REGION' -and -not $env:AWS_REGION) { $Region = $v }
    if ($k -eq 'ACCOUNT_ID' -and -not $AccountId) { $AccountId = $v }
    if ($k -eq 'SUBNET_IDS' -and -not $SubnetIds) { $SubnetIds = $v }
    if ($k -eq 'SECURITY_GROUP_IDS' -and -not $SecurityGroupIds) { $SecurityGroupIds = $v }
  }
}

if (-not $Bucket) { throw 'Set -Bucket or CAMPAIGN_BUCKET in deploy/aws/.env' }
if (-not $AccountId) {
  $AccountId = aws --profile $AwsProfile sts get-caller-identity --query Account --output text --region $Region
}
if (-not $AccountId) { throw 'Could not resolve ACCOUNT_ID' }

function Render($file, $out) {
  (Get-Content -Raw $file).Replace('<ACCOUNT_ID>', $AccountId).Replace('<REGION>', $Region).Replace('<BUCKET>', $Bucket) | Set-Content -NoNewline $out
}

Write-Host "Ensuring boundary analysis infra:"
Write-Host "  profile=$AwsProfile account=$AccountId region=$Region bucket=$Bucket"
Write-Host "  capacity=$Capacity queues=$QueueName,$MemoryQueueName log=$LogGroup"

# Log group — create directly; do not rely on DescribeLogGroups (deploy role may
# lack logs:DescribeLogGroups on * until deploy_role_permissions_policy is reapplied).
$createLg = aws --profile $AwsProfile logs create-log-group --log-group-name $LogGroup --region $Region 2>&1
if ($LASTEXITCODE -eq 0) {
  Write-Host "  created log group $LogGroup"
} elseif ($createLg -match 'ResourceAlreadyExistsException') {
  Write-Host "  log group exists"
} else {
  throw "create-log-group failed: $createLg"
}

if (-not $RegisterOnly) {
  if (-not $SubnetIds -or -not $SecurityGroupIds) {
    throw 'Set -SubnetIds and -SecurityGroupIds (or SUBNET_IDS / SECURITY_GROUP_IDS in .env) to ensure the analysis compute environments'
  }
  $pathways = @(
    @{ Pathway = 'analysis_compute'; Queue = $QueueName },
    @{ Pathway = 'analysis_memory'; Queue = $MemoryQueueName }
  )
  foreach ($p in $pathways) {
    $ensureArgs = @(
      (Join-Path $here 'ensure_batch_pathways.py'),
      '--pathway', $p.Pathway,
      '--queue', $p.Queue,
      '--capacity', $Capacity,
      '--max-vcpus', $MaxVcpus,
      '--subnets', $SubnetIds,
      '--security-groups', $SecurityGroupIds,
      '--region', $Region,
      '--profile', $AwsProfile
    )
    if ($LaunchTemplate) { $ensureArgs += @('--launch-template', $LaunchTemplate) }
    python3 @ensureArgs
    if ($LASTEXITCODE -ne 0) { throw "ensure_batch_pathways.py failed for $($p.Pathway)" }
  }
}

foreach ($jd in @(
  'batch_job_definition_boundary_surface.json',
  'batch_job_definition_boundary_stan.json',
  'batch_job_definition_boundary_mc.json',
  'batch_job_definition_sentinel_recovery_stan.json',
  'batch_job_definition_sentinel_nuts.json'
)) {
  $src = Join-Path $here $jd
  $tmp = Join-Path $env:TEMP $jd
  Render $src $tmp
  aws --profile $AwsProfile batch register-job-definition --cli-input-json "file://$tmp" --region $Region --query 'jobDefinitionArn' --output text
}

Write-Host "Done. Submit boundary jobs with submit_boundary_analysis.ps1"
Write-Host "       Submit sentinel recovery Stan with submit_sentinel_recovery_stan.ps1"
