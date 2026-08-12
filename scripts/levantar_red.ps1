# Levanta los 9 routers (y opcionalmente el banco) como procesos
# independientes de verdad: no dependen de que esta terminal de PowerShell
# se quede abierta. El flooding y el calculo de rutas son automaticos, pasan
# solos en cuanto dos o mas routers estan corriendo.
#
# Uso:
#   .\scripts\levantar_red.ps1
#   .\scripts\levantar_red.ps1 -ConBanco
#   .\scripts\levantar_red.ps1 -Nodos A,B,C
#   .\scripts\levantar_red.ps1 -Nodos A,B,C -ConBanco
#
# Para bajar todo: .\scripts\detener_red.ps1

param(
    [switch]$ConBanco,
    [string[]]$Nodos = @("A", "B", "C", "D", "E", "F", "G", "H", "I")
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "No encontré 'python', 'python3' ni 'py' en el PATH de esta terminal."
    exit 1
}

New-Item -ItemType Directory -Force -Path logs, runtime | Out-Null

$pids = @()

foreach ($n in $Nodos) {
    $p = Start-Process -FilePath $python.Source -ArgumentList @("src/main.py", $n) `
        -RedirectStandardOutput "logs/$n.out.log" `
        -RedirectStandardError "logs/$n.err.log" `
        -WindowStyle Hidden -PassThru
    $pids += $p.Id
    Write-Host "[levantar_red] router $n -> PID $($p.Id)"
}

if ($ConBanco) {
    $p = Start-Process -FilePath $python.Source -ArgumentList @("src/endpoints/banco_servidor.py") `
        -RedirectStandardOutput "logs/banco.out.log" `
        -RedirectStandardError "logs/banco.err.log" `
        -WindowStyle Hidden -PassThru
    $pids += $p.Id
    Write-Host "[levantar_red] banco -> PID $($p.Id)"
}

$pids | Out-File -FilePath logs/pids.txt -Encoding ascii

Write-Host "[levantar_red] esperando convergencia (~12s)..."
Start-Sleep -Seconds 12

$csv = "runtime/$($Nodos[0])_tabla_enrutamiento.csv"
if (Test-Path $csv) {
    Write-Host "[levantar_red] listo. Tabla de $($Nodos[0]):"
    Get-Content $csv
} else {
    Write-Host "[levantar_red] todavia no existe $csv, dale unos segundos mas"
}

Write-Host ""
Write-Host "Estos procesos quedan vivos aunque cierres esta terminal."
Write-Host "Cliente ATM:   python src/endpoints/atm_cliente.py [--hamming]"
Write-Host "Bajar todo:    .\scripts\detener_red.ps1"
Write-Host "Ver un log:    Get-Content logs/A.out.log -Wait"
