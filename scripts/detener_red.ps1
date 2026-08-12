# Detiene todos los procesos levantados por scripts/levantar_red.ps1.

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path logs/pids.txt)) {
    Write-Host "[detener_red] no hay logs/pids.txt (¿ya está todo apagado?)"
    exit 0
}

Get-Content logs/pids.txt | ForEach-Object {
    $procId = $_.Trim()
    if ($procId) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "[detener_red] proceso $procId detenido"
        } catch {
            Write-Host "[detener_red] proceso $procId ya no existía"
        }
    }
}

Remove-Item logs/pids.txt -Force
Write-Host "[detener_red] listo"
