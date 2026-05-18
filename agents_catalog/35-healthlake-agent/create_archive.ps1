# HealthLake AI Assistant - Create HTML Archive Package
# This script creates a self-contained ZIP archive with the HTML documentation

$archiveName = "HealthLake-Agent-Documentation.zip"
$tempFolder = "HealthLake-Agent-Documentation"

Write-Host "Creating HTML Archive Package..." -ForegroundColor Green

# Create temporary folder structure
if (Test-Path $tempFolder) {
    Remove-Item -Recurse -Force $tempFolder
}
New-Item -ItemType Directory -Path $tempFolder | Out-Null
New-Item -ItemType Directory -Path "$tempFolder/docs" | Out-Null
New-Item -ItemType Directory -Path "$tempFolder/docs/generated-diagrams" | Out-Null

# Copy files
Write-Host "Copying files..." -ForegroundColor Yellow
Copy-Item "README.html" -Destination "$tempFolder/"
Copy-Item "README_PACKAGE.txt" -Destination "$tempFolder/"
Copy-Item "docs/generated-diagrams/*.png" -Destination "$tempFolder/docs/generated-diagrams/"

# Create ZIP archive
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
if (Test-Path $archiveName) {
    Remove-Item $archiveName
}
Compress-Archive -Path "$tempFolder/*" -DestinationPath $archiveName

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $tempFolder

Write-Host "`nArchive created successfully: $archiveName" -ForegroundColor Green
Write-Host "Size: $((Get-Item $archiveName).Length / 1KB) KB" -ForegroundColor Cyan
Write-Host "`nTo use:" -ForegroundColor White
Write-Host "1. Extract the ZIP file" -ForegroundColor White
Write-Host "2. Open README.html in any web browser" -ForegroundColor White
