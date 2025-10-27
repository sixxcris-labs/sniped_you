<#
.SYNOPSIS
  Verifies connectivity and permissions for all enabled Google APIs in Sniped You.
#>

# Load API key from .env
$envPath = Join-Path (Get-Location) ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "[error] .env file not found." -ForegroundColor Red
    exit 1
}

$GOOGLE_API_KEY = (Get-Content $envPath | Select-String "GOOGLE_API_KEY" | ForEach-Object { $_ -replace "GOOGLE_API_KEY=", "" }).Trim()
if (-not $GOOGLE_API_KEY) {
    Write-Host "[error] GOOGLE_API_KEY not set in .env." -ForegroundColor Red
    exit 1
}

Write-Host "`n[info] Testing Google APIs with key: $($GOOGLE_API_KEY.Substring(0,6))******" -ForegroundColor Cyan

function Test-Api {
    param ($name, $url)
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 10
        if ($r) {
            Write-Host "[$name] ✅ OK" -ForegroundColor Green
        } else {
            Write-Host "[$name] ⚠️ No data returned" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[$name] ❌ Failed -> $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 1. Custom Search API (sample query)
Test-Api "Custom Search" "https://www.googleapis.com/customsearch/v1?key=$GOOGLE_API_KEY&cx=017576662512468239146:omuauf_lfve&q=bike"

# 2. Knowledge Graph Search API
Test-Api "Knowledge Graph" "https://kgsearch.googleapis.com/v1/entities:search?query=Trek%20Bicycle&key=$GOOGLE_API_KEY&limit=1&indent=True"

# 3. Cloud Natural Language API (simple text)
$nlBody = @{
  document = @{ type = "PLAIN_TEXT"; content = "Cycling is an amazing sport with high energy and community." }
  encodingType = "UTF8"
} | ConvertTo-Json -Depth 3
try {
    $resp = Invoke-RestMethod -Uri "https://language.googleapis.com/v1/documents:analyzeSentiment?key=$GOOGLE_API_KEY" `
        -Method Post -Body $nlBody -ContentType "application/json" -TimeoutSec 10
    if ($resp) { Write-Host "[Cloud NLP] ✅ OK" -ForegroundColor Green } else { Write-Host "[Cloud NLP] ⚠️ Empty response" -ForegroundColor Yellow }
} catch {
    Write-Host "[Cloud NLP] ❌ Failed -> $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Google Analytics Admin API (list accounts)
Test-Api "Analytics Admin" "https://analyticsadmin.googleapis.com/v1beta/accounts?key=$GOOGLE_API_KEY"

# 5. YouTube Data API v3 (search query)
Test-Api "YouTube Data" "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q=cycling&maxResults=1&key=$GOOGLE_API_KEY"

Write-Host "`n[done] API connectivity test complete.`n"
