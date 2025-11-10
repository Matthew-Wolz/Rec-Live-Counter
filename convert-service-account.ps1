# PowerShell script to convert service-account.json to single-line format for Vercel
# Run this script to prepare your service account credentials for Vercel environment variables

$inputFile = "service-account.json"
$outputFile = "service-account-oneline.txt"

if (-not (Test-Path $inputFile)) {
    Write-Host "Error: $inputFile not found!" -ForegroundColor Red
    Write-Host "Make sure you're running this script from the project root directory." -ForegroundColor Yellow
    exit 1
}

Write-Host "Reading $inputFile..." -ForegroundColor Green

# Read the JSON file
$jsonContent = Get-Content -Path $inputFile -Raw

# Parse and re-stringify to ensure valid JSON and remove formatting
try {
    $jsonObject = $jsonContent | ConvertFrom-Json
    $singleLine = $jsonObject | ConvertTo-Json -Compress -Depth 10
} catch {
    Write-Host "Error: Invalid JSON in $inputFile" -ForegroundColor Red
    exit 1
}

# Write to output file
$singleLine | Set-Content -Path $outputFile -NoNewline

Write-Host "`nSuccess! Single-line JSON saved to: $outputFile" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Open $outputFile" -ForegroundColor Cyan
Write-Host "2. Copy the entire contents (it's all on one line)" -ForegroundColor Cyan
Write-Host "3. Paste it as the value for GOOGLE_SERVICE_ACCOUNT in Vercel environment variables" -ForegroundColor Cyan
Write-Host "`nNote: The file contains sensitive credentials. Keep it secure and don't commit it to git." -ForegroundColor Yellow

