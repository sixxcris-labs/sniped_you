<#
.SYNOPSIS
  Removes old .env loader blocks from all Python files in the project.
  Creates .bak backups automatically.
#>

$projectRoot = Get-Location
$patternStart = 'if os\.path\.exists\("\.env"\):'
$pythonFiles = Get-ChildItem -Path $projectRoot -Filter *.py -Recurse

foreach ($file in $pythonFiles) {
    $content = Get-Content $file.FullName -Raw
    if ($content -match $patternStart) {
        Write-Host "[clean] Found .env loader in $($file.FullName)" -ForegroundColor Yellow

        # Backup original
        Copy-Item $file.FullName "$($file.FullName).bak" -Force

        # Remove the .env block
        $cleaned = $content -replace '(?s)import os\s*if os\.path\.exists\("\.env"\):.*?(?=(\n\s*from|\n\s*import|\Z))', 'import os`n'
        Set-Content -Path $file.FullName -Value $cleaned -Encoding UTF8

        Write-Host "         Cleaned and backed up." -ForegroundColor Green
    }
}

Write-Host "`n[done] Cleanup complete. Backups saved as *.bak in the same directories.`n"
