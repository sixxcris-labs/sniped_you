
# ----------------------------------
# ==============================
# SNIPED YOU - RUN SCORE
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Get-Location).Path
$env:PYTHONPATH = $repo

$inputFile  = "data\output\refined_complete.json"
$outputFile = "data\output\scored.json"
$configFile = "config\scoring.yaml"

if (-not (Test-Path $inputFile)) {
    Write-Host "[run_score] Missing $inputFile" -ForegroundColor Red
    exit 2
}

$env:SNIPER_REFINED_PATH = $inputFile
$env:SNIPER_SCORED_PATH  = $outputFile
$env:SNIPER_SCORING_CFG  = $configFile

Write-Host "[run_score] Starting profitability scoring..." -ForegroundColor Cyan
try {
    python -m app.scoring.profitability_scorer
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run_score] Scorer exited with code $LASTEXITCODE" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
    Write-Host "[run_score] Scoring complete âœ…" -ForegroundColor Green
} catch {
    Write-Host "[run_score] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

