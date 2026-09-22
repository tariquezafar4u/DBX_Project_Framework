<#
.SYNOPSIS
  Learning-project deployment script for DAT-EDIP.

.DESCRIPTION
  1. Reads the data contract (contract.yaml) for the given product from the
     data-contract-repo checkout.
  2. Reads this framework's config/framework_config.yaml.
  3. Calls scripts/register_job.py to create/update the Databricks Job made
     up of the three notebooks (volume_to_volume -> raw_manager -> stage_manager).
  4. Triggers a run of that job.

.PARAMETER ProductName
  Name of the data product to run (must match a folder under contracts/ in
  the data-contract-repo), e.g. "customer_orders".

.PARAMETER ContractRepoPath
  Local path to the data-contract-repo checkout. Defaults to the value in
  config/framework_config.yaml (contract_repo.local_path).

.EXAMPLE
  ./scripts/deploy_and_run.ps1 -ProductName customer_orders
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$ProductName,

    [string]$ContractRepoPath,

    [string]$FrameworkConfigPath = "config/framework_config.yaml",

    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $FrameworkConfigPath)) {
    throw "Framework config not found at $FrameworkConfigPath. Run this script from the dat-edip-framework repo root."
}

Write-Host "== DAT-EDIP learning deploy ==" -ForegroundColor Cyan
Write-Host "Product name       : $ProductName"
Write-Host "Framework config   : $FrameworkConfigPath"

if (-not $ContractRepoPath) {
    # crude YAML read for contract_repo.local_path without extra dependencies
    $line = Select-String -Path $FrameworkConfigPath -Pattern "local_path:" | Select-Object -First 1
    if ($line) {
        $ContractRepoPath = ($line.Line -split "local_path:")[1].Trim().Trim('"')
    } else {
        $ContractRepoPath = "../data-contract-repo"
    }
}

$contractFile = Join-Path $ContractRepoPath "contracts/$ProductName/contract.yaml"
if (-not (Test-Path $contractFile)) {
    throw "Contract file not found: $contractFile. Deploy the data-contract-repo first and check -ContractRepoPath."
}

Write-Host "Contract repo path : $ContractRepoPath"
Write-Host "Contract file      : $contractFile"
Write-Host ""
Write-Host "Step 1/2: Registering (creating/updating) the Databricks job..." -ForegroundColor Cyan

$notebookRoot = "/Shared/dat_edip_framework/notebooks"
$contractRepoRootOnWorkspace = "/Shared/data_contract_repo"

$registerArgs = @(
    "scripts/register_job.py",
    "--job-config", $FrameworkConfigPath,
    "--notebook-root", $notebookRoot,
    "--product-name", $ProductName,
    "--contract-repo-root", $contractRepoRootOnWorkspace
)
if ($PrintOnly) {
    $registerArgs += "--print-only"
}

python @registerArgs
if ($LASTEXITCODE -ne 0) {
    throw "register_job.py failed with exit code $LASTEXITCODE"
}

if ($PrintOnly) {
    Write-Host "PrintOnly set - skipping job trigger." -ForegroundColor Yellow
    return
}

Write-Host ""
Write-Host "Step 2/2: Triggering a run of the job via Databricks CLI..." -ForegroundColor Cyan

$jobName = "dat_edip_learning_pipeline_$ProductName"
databricks jobs run-now --job-name $jobName

Write-Host ""
Write-Host "Done. Check the Databricks Jobs UI for run progress." -ForegroundColor Green
