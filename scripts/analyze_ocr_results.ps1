# --- Load environment variables ---
if (Test-Path ".env") {
    . .\.env
}
# ----------------------------------
# Path to your OCR JSON file
$jsonPath = "data/output/marketplace_houston_search_cards_retry.json"

# Load JSON
if (!(Test-Path $jsonPath)) {
    Write-Host "File not found: $jsonPath"
    exit
}

$data = Get-Content $jsonPath | ConvertFrom-Json

$total = $data.Count
$valid = ($data | Where-Object { $_.title -and $_.title.Trim().Length -ge 3 }).Count
$failed = $total - $valid

Write-Host ""
Write-Host "OCR Result Summary"
Write-Host "----------------------"
Write-Host ("Total items: {0}" -f $total)
Write-Host ("Valid OCR titles: {0}" -f $valid)
Write-Host ("Failed OCR titles: {0}" -f $failed)
Write-Host ("Success rate: {0:P2}" -f ($valid / $total))

Write-Host ""
Write-Host "Sample Valid Titles:"
$data |
    Where-Object { $_.title -and $_.title.Trim().Length -ge 3 } |
    Select-Object -First 10 url, title |
    Format-Table -AutoSize

