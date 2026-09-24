@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "DatabricksProfile=dev"
set "BundleTarget=vscodedev"

if /I "%~1"=="plan" (
    echo == DAT-EDIP learning bundle plan ==
    databricks bundle plan --profile "%DatabricksProfile%" --target "%BundleTarget%"
    if errorlevel 1 (
        echo Databricks bundle plan failed with exit code !ERRORLEVEL!
        exit /b !ERRORLEVEL!
    )
    exit /b 0
)

if "%~1"=="" (
    echo == DAT-EDIP learning bundle deploy ==
    databricks bundle deploy --profile "%DatabricksProfile%" --target "%BundleTarget%"
    if errorlevel 1 (
        echo Databricks bundle deploy failed with exit code !ERRORLEVEL!
        exit /b !ERRORLEVEL!
    )
    exit /b 0
)

set "ProductName=%~1"
set "FrameworkConfigPath=config\framework_config.yaml"
set "ContractRepoPath="
set "PrintOnly="

if not "%~2"=="" (
    if /I "%~2"=="--print-only" (
        set "PrintOnly=--print-only"
    ) else (
        set "ContractRepoPath=%~2"
    )
)

if not "%~3"=="" (
    if /I "%~3"=="--print-only" (
        set "PrintOnly=--print-only"
    )
)

if not exist "%FrameworkConfigPath%" (
    echo Framework config not found at %FrameworkConfigPath%. Run this script from the dat-edip-framework repo root.
    exit /b 1
)

echo == DAT-EDIP learning deploy (legacy workflow) ==
echo Databricks profile  : %DatabricksProfile%
echo Product name       : %ProductName%
echo Framework config   : %FrameworkConfigPath%

if not defined ContractRepoPath (
    for /f "usebackq tokens=2 delims=: " %%A in (`findstr /R /C:"local_path:" "%FrameworkConfigPath%"`) do set "ContractRepoPath=%%A"
    if not defined ContractRepoPath set "ContractRepoPath=..\data-contract-repo"
)

set "ContractRepoPath=%ContractRepoPath:"=%"
if not "%ContractRepoPath:~1,1%"==":" if not "%ContractRepoPath:~0,1%"=="\" if not "%ContractRepoPath:~0,1%"=="/" (
    for %%I in ("%~dp0%ContractRepoPath%") do set "ContractRepoPath=%%~fI"
)

set "ContractFile=%ContractRepoPath%\contracts\%ProductName%\contract.yaml"
if not exist "%ContractFile%" (
    echo Contract file not found: %ContractFile%. Deploy the data-contract-repo first and check the contract repo path.
    exit /b 1
)

echo Contract repo path : %ContractRepoPath%
echo Contract file      : %ContractFile%
echo.
echo Step 1/2: Registering ^(creating/updating^) the Databricks job...

set "NotebookRoot=/Shared/dat_edip_framework/notebooks"
set "ContractRepoRootOnWorkspace=/Shared/data_contract_repo"

python scripts/register_job.py --job-config "%FrameworkConfigPath%" --notebook-root "%NotebookRoot%" --product-name "%ProductName%" --contract-repo-root "%ContractRepoRootOnWorkspace%" %PrintOnly%
if errorlevel 1 (
    echo register_job.py failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

if defined PrintOnly (
    echo PrintOnly set - skipping job trigger.
    exit /b 0
)

echo.
echo Step 2/2: Triggering a run of the job via Databricks CLI...

set "JobName=dat_edip_learning_pipeline_%ProductName%"
databricks jobs run-now --profile "%DatabricksProfile%" --job-name "%JobName%"
if errorlevel 1 (
    echo Databricks CLI failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo Done. Check the Databricks Jobs UI for run progress.
exit /b 0
