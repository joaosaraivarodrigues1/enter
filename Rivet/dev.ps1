param(
    [string]$Test = "albert-2025-02"
)

$testFile = "tests\$Test.json"

if (-not (Test-Path $testFile)) {
    Write-Host "Arquivo nao encontrado: $testFile"
    Write-Host ""
    Write-Host "Casos de teste disponiveis:"
    Get-ChildItem tests\*.json | ForEach-Object { Write-Host "  $($_.BaseName)" }
    exit 1
}

# Mata processo na porta 3000
$conn = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Servidor anterior encerrado."
}

# Sobe servidor em background
$server = Start-Process node -ArgumentList "server.mjs" -PassThru -NoNewWindow
Write-Host "Servidor iniciando (PID $($server.Id))..."

# Aguarda estar pronto
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep 1
    try {
        Invoke-RestMethod -Uri http://localhost:3000/health -ErrorAction Stop | Out-Null
        $ready = $true
        break
    } catch {}
}

if (-not $ready) {
    Write-Host "Servidor nao respondeu em 15s."
    exit 1
}

Write-Host "Pronto. Enviando $Test..."
$body = Get-Content $testFile -Raw
Invoke-RestMethod -Uri http://localhost:3000 -Method POST -ContentType "application/json" -Body $body
Write-Host "Job enviado. Acompanhe no Rivet IDE."
