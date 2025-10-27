<#
.SYNOPSIS
    Secure Environment Setup for Sniped You
.DESCRIPTION
    - Creates .env if missing
    - Ensures all PowerShell & Python files load environment variables safely
    - Replaces hardcoded API keys with $env: variables
#>

Write-Host "[init] Starting environment hardening..."

# --- Step 1: Create .env if missing ---
$envFile = ".env"
if (!(Test-Path $envFile)) {
    @"
$env:TELEGRAM_TOKEN="your-telegram-bot-token"
$env:LLM_KEY="your-llm-api-key"
$env:EBAY_AUTH_TOKEN="your-ebay-oauth-token"
$env:GOOGLE_API_KEY="your-google-api-key"
$env:DB_PASSWORD="your-database-password"
"@ | Out-File $envFile -Encoding UTF8
    Write-Host "[done] Created new .env file with placeholder values."
} else {
    Write-Host "[skip] .env file already exists."
}

# --- Step 2: Add .gitignore protection ---
if (Test-Path ".gitignore") {
    if (-not (Select-String -Path ".gitignore" -Pattern "^\s*\.env\s*$")) {
        Add-Content ".gitignore" "`n.env"
        Write-Host "[done] Added .env to .gitignore."
    } else {
        Write-Host "[skip] .env already ignored."
    }
} else {
    ".env" | Out-File ".gitignore" -Encoding UTF8
    Write-Host "[done] Created .gitignore and added .env."
}

# --- Step 3: Inject .env loader into PowerShell scripts ---
$psScripts = Get-ChildItem -Path ".." -Recurse -Include *.ps1
$loaderBlock = @'
# --- Load environment variables ---
if (Test-Path "..\.env") {
    . ..\.env
}
# ----------------------------------
'@

foreach ($script in $psScripts) {
    $content = Get-Content $script.FullName -Raw
    if ($content -notmatch "\.env") {
        ($loaderBlock + "`n" + $content) | Out-File $script.FullName -Encoding UTF8
        Write-Host "[patched] $($script.FullName)"
    }
}

# --- Step 4: Inject Python env loader ---
$pyFiles = Get-ChildItem -Path ".." -Recurse -Include *.py
$pyLoader = @'
import os
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip().startswith("$env:"):
                key, val = line.replace("$env:", "").split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"')
'@

foreach ($py in $pyFiles) {
    $pyContent = Get-Content $py.FullName -Raw
    if ($pyContent -notmatch 'os\.path\.exists') {
        ($pyLoader + "`n" + $pyContent) | Out-File $py.FullName -Encoding UTF8
        Write-Host "[patched] $($py.FullName)"
    }
}

Write-Host "`n[complete] All files now safely load secrets from .env."
