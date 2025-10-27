--------------------------
# ==============================
# SNIPED YOU - RUN NOTIFY
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Get-Location).Path
$env:PYTHONPATH = $repo

$scoredFile   = "data\output\scored.json"
$settingsFile = "config\settings.yaml"
$secretFile   = "config\webhook_secrets.yaml"

if (-not (Test-Path $scoredFile)) {
    Write-Host "[run_notify] Missing $scoredFile" -ForegroundColor Red
    exit 2
}

$env:SNIPER_SCORED_PATH     = $scoredFile
$env:SNIPER_SETTINGS_CFG    = $settingsFile
$env:SNIPER_WEBHOOK_SECRETS = $secretFile

Write-Host "[run_notify] Starting webhook dispatcher..." -ForegroundColor Cyan
try {
    python -m app.notifiers.webhook_dispatcher
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run_notify] Dispatcher exited with code $LASTEXITCODE" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
    Write-Host "[run_notify] Notifications sent successfully " -ForegroundColor Green
} catch {
    Write-Host "[run_notify] ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

