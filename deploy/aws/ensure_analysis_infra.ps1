#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure On-Demand Batch infra for boundary analysis jobs (surface / Stan / MC).

.DESCRIPTION
  Creates log group, On-Demand Fargate CE + queue if missing, and registers
  the three boundary analysis job definitions. Does NOT create Spot campaign
  infra (use ensure_campaign_infra.sh for that).

  Requires: AWS_PROFILE=picard, ACCOUNT_ID/REGION/BUCKET (or deploy/aws/.env),
  and an existing VPC subnet + security group (same as Spot CE).
#>
param(
  [string]$Bucket = $env:CAMPAIGN_BUCKET,
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { 'us-east-1' }),
  [Alias('Profile')]
  [string]$AwsProfile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'picard' }),
  [string]$AccountId = $env:ACCOUNT_ID,
  [string]$SubnetIds = $env:SUBNET_IDS,
  [string]$SecurityGroupIds = $env:SECURITY_GROUP_IDS,
  [string]$CeName = 'picard-analysis-ondemand',
  [string]$QueueName = 'picard-analysis-queue',
  [string]$LogGroup = '/aws/batch/picard-boundary-analysis',
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
Write-Host "  CE=$CeName queue=$QueueName log=$LogGroup"

# Log group
$lg = aws --profile $AwsProfile logs describe-log-groups --log-group-name-prefix $LogGroup --region $Region --query "logGroups[?logGroupName=='$LogGroup'].logGroupName" --output text
if (-not $lg) {
  aws --profile $AwsProfile logs create-log-group --log-group-name $LogGroup --region $Region
  Write-Host "  created log group $LogGroup"
} else {
  Write-Host "  log group exists"
}

if (-not $RegisterOnly) {
  $ceStatus = aws --profile $AwsProfile batch describe-compute-environments --compute-environments $CeName --region $Region --query 'computeEnvironments[0].status' --output text 2>$null
  if ($ceStatus -eq 'None' -or -not $ceStatus -or $ceStatus -eq 'INVALID') {
    if (-not $SubnetIds -or -not $SecurityGroupIds) {
      throw "CE missing; set -SubnetIds and -SecurityGroupIds (or SUBNET_IDS / SECURITY_GROUP_IDS in .env) to create $CeName"
    }
    $subnets = ($SubnetIds -split ',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $sgs = ($SecurityGroupIds -split ',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $subnetJson = ($subnets | ForEach-Object { "`"$_`"" }) -join ','
    $sgJson = ($sgs | ForEach-Object { "`"$_`"" }) -join ','
    $ceBody = @"
{
  "computeEnvironmentName": "$CeName",
  "type": "MANAGED",
  "state": "ENABLED",
  "computeResources": {
    "type": "FARGATE",
    "maxvCpus": 256,
    "subnets": [$subnetJson],
    "securityGroupIds": [$sgJson]
  }
}
"@
    $ceFile = Join-Path $env:TEMP 'picard-analysis-ce.json'
    Set-Content -NoNewline -Path $ceFile -Value $ceBody
    aws --profile $AwsProfile batch create-compute-environment --cli-input-json "file://$ceFile" --region $Region | Out-Null
    Write-Host "  creating CE $CeName …"
    do {
      Start-Sleep -Seconds 5
      $ceStatus = aws --profile $AwsProfile batch describe-compute-environments --compute-environments $CeName --region $Region --query 'computeEnvironments[0].status' --output text
      Write-Host "  CE status=$ceStatus"
    } while ($ceStatus -eq 'CREATING')
    if ($ceStatus -ne 'VALID') { throw "CE $CeName status=$ceStatus" }
  } else {
    Write-Host "  CE status=$ceStatus"
  }

  $qArn = aws --profile $AwsProfile batch describe-job-queues --job-queues $QueueName --region $Region --query 'jobQueues[0].jobQueueArn' --output text 2>$null
  if (-not $qArn -or $qArn -eq 'None') {
    aws --profile $AwsProfile batch create-job-queue --job-queue-name $QueueName --state ENABLED --priority 1 --compute-environment-order "order=1,computeEnvironment=$CeName" --region $Region | Out-Null
    Write-Host "  created queue $QueueName"
  } else {
    Write-Host "  queue exists"
  }
}

foreach ($jd in @(
  'batch_job_definition_boundary_surface.json',
  'batch_job_definition_boundary_stan.json',
  'batch_job_definition_boundary_mc.json'
)) {
  $src = Join-Path $here $jd
  $tmp = Join-Path $env:TEMP $jd
  Render $src $tmp
  aws --profile $AwsProfile batch register-job-definition --cli-input-json "file://$tmp" --region $Region --query 'jobDefinitionArn' --output text
}

Write-Host "Done. Submit analysis jobs with submit_boundary_analysis.ps1"
