Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python was not found. Install Python 3 first, then rerun this script."
}

function Run-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==== $Message ====" -ForegroundColor Cyan
    & $Action
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Executable $($Arguments -join ' ')"
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

$pythonLauncher = Get-PythonLauncher
$pythonExe = $pythonLauncher[0]
$pythonArgs = if ($pythonLauncher.Length -gt 1) {
    $pythonLauncher[1..($pythonLauncher.Length - 1)]
} else {
    @()
}
$venvDir = Join-Path $repoRoot ".demo-venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Run-Step "Repository root" {
    Write-Host $repoRoot
}

Run-Step "Create virtual environment if needed" {
    if (-not (Test-Path $venvPython)) {
        $venvArgs = @()
        if ($pythonArgs.Length -gt 0) {
            $venvArgs += $pythonArgs
        }
        $venvArgs += @("-m", "venv", $venvDir)
        Invoke-External -Executable $pythonExe -Arguments $venvArgs
    }
    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment was not created successfully."
    }
    Write-Host "Using virtual environment at $venvDir"
}

Run-Step "Upgrade pip" {
    Invoke-External -Executable $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
}

Run-Step "Install project requirements" {
    Invoke-External -Executable $venvPython -Arguments @("-m", "pip", "install", "-r", (Join-Path $repoRoot "requirements.txt"))
}

Run-Step "Run experiment suite" {
    Invoke-External -Executable $venvPython -Arguments @((Join-Path $repoRoot "scripts\run_experiments.py"))
}

Run-Step "Verify report-ready results" {
    Invoke-External -Executable $venvPython -Arguments @((Join-Path $repoRoot "scripts\verify_demo_results.py"))
}

Run-Step "Run automated tests" {
    Invoke-External -Executable $venvPython -Arguments @("-m", "unittest", "discover", "-s", "tests", "-v")
}

Write-Host ""
Write-Host "Demo run completed successfully." -ForegroundColor Green
Write-Host "Show these files on screen next:" -ForegroundColor Green
Write-Host "  results\holdout_leaderboard.csv"
Write-Host "  results\cross_validation_summary.csv"
Write-Host "  results\experiment_summary.json"
Write-Host "  results\figures\baseline_svm_confusion_matrix.png"
Write-Host "  results\figures\random_forest_feature_importance.png"
