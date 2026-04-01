# Mata processo anterior na porta 3000
$conn = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Servidor anterior encerrado."
}

# Sobe servidor em nova janela (com logs visiveis)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$dir'; node server.mjs"

# Aguarda estar pronto
Write-Host "Aguardando servidor..."
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep 1
    try {
        Invoke-RestMethod -Uri http://localhost:3000/health -ErrorAction Stop | Out-Null
        $ready = $true
        break
    } catch {}
}

if (-not $ready) {
    Write-Host "Servidor nao respondeu em 20s."
    exit 1
}

Write-Host "Servidor pronto. Use .\test.ps1 para testar."
