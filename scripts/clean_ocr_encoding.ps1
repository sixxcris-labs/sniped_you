
# ----------------------------------
# Cleans bad encoding characters from OCR output JSON
$jsonPath = "data/output/marketplace_houston_search_cards_retry.json"
$cleanPath = "data/output/marketplace_houston_search_cards_clean.json"

if (!(Test-Path $jsonPath)) {
    Write-Host "File not found: $jsonPath"
    exit
}

$content = Get-Content $jsonPath -Raw -Encoding UTF8

# Replace common misencoded characters
$clean = $content `
    -replace "â", "'" `
    -replace "â", "-" `
    -replace "â", "-" `
    -replace "â", "'" `
    -replace "âœ", '"' `
    -replace "â", '"' `
    -replace "â", "" `
    -replace "Â", ""

$clean | Out-File -FilePath $cleanPath -Encoding UTF8 -Force

Write-Host "Cleaned file saved to: $cleanPath"

