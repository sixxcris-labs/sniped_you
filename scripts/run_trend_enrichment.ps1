# run_trend_enrichment.ps1
Write-Host "[info] Enriching data/output/parsed_listings.json with Google Trends data..."

$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) { & $venvPath }

# Absolute paths (no empty variables)
$inputFull = Join-Path (Get-Location) "data\output\parsed_listings.json"
$outputFull = Join-Path (Get-Location) "data\output\enriched_listings.json"

python app/adapters/google_trends_enricher.py --input "$inputFull" --output "$outputFull"

Write-Host "[done] Enrichment complete. Output → $outputFull"
