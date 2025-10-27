<#
.SYNOPSIS
  Fetches an eBay OAuth token (Sandbox) and stores it in .env for Sniped You.

.PARAMETERS
  -AppID   Your eBay App ID (Client ID)
  -CertID  Your eBay Cert ID (Client Secret)
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$AppID,

    [Parameter(Mandatory = $true)]
    [string]$CertID
)

Write-Host "[info] Requesting eBay Sandbox token..."

# Combine and encode credentials
$pair = "$AppID`:$CertID"
$encoded = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))

# Build request body
$body = "grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"

# Request token
$response = Invoke-RestMethod -Uri "https://api.ebay.com/identity/v1/oauth2/token" `
    -Headers @{ "Authorization" = "Basic $encoded"; "Content-Type" = "application/x-www-form-urlencoded" } `
    -Body $body -Method Post

if (-not $response.access_token) {
    Write-Host "[error] Failed to retrieve token:" -ForegroundColor Red
    $response | ConvertTo-Json -Depth 5
    exit 1
}

$token = $response.access_token
Write-Host "[ok] Token retrieved successfully."

# Save or update .env file
$envPath = Join-Path (Get-Location) ".env"
if (Test-Path $envPath) {
    (Get-Content $envPath) | Where-Object {$_ -notmatch "^EBAY_AUTH_TOKEN="} | Set-Content $envPath
}
Add-Content $envPath "EBAY_AUTH_TOKEN=$token"

Write-Host "[done] Token saved to .env successfully."
