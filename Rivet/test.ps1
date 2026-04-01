param([string]$Cliente)

$testFile = "tests\$Cliente.json"

if (-not (Test-Path $testFile)) {
    Write-Host "Arquivo nao encontrado: $testFile"
    Write-Host "Disponiveis:"
    Get-ChildItem tests\*.json | ForEach-Object { Write-Host "  $($_.BaseName)" }
    exit 1
}

Invoke-RestMethod -Method POST -Uri http://localhost:3000 -ContentType "application/json" -Body (Get-Content $testFile -Raw)
