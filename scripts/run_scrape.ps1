# run_scrape.ps1
param(
    [Parameter(Mandatory = $true)][string]$site,
    [Parameter(Mandatory = $true)][string]$category,
    [int]$limit = 20,
    [string]$region = "houston",
    [switch]$headless
)

Write-Host "[info] Running scraper for site '$site' (category: $category, limit: $limit, region: $region)..."

# Activate virtual environment
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "[warn] Virtual environment not found at $venvPath"
}

# Determine flags
$headlessFlag = if ($headless) { "--headless" } else { "--visible" }

# Build Python command dynamically
if ($site -eq "craigslist" -or $site -eq "nextdoor") {
    python app/scrapers/market_scraper.py `
        --site $site `
        --category $category `
        --region $region `
        --limit $limit `
        $headlessFlag
} else {
    python app/scrapers/market_scraper.py `
        --site $site `
        --category $category `
        --limit $limit `
        $headlessFlag
}

Write-Host "[done] Scrape complete. Output should be in data/output/parsed_listings.json"
