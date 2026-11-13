# Corrida diaria en Windows. Programarla a las 07:00 con el Programador de tareas, una sola vez,
# desde PowerShell en la carpeta del proyecto (la ruta no debe tener espacios):
#   schtasks /Create /TN PreciosBebe /SC DAILY /ST 07:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File $PWD\scripts\run_daily.ps1"
# Probarla ya: schtasks /Run /TN PreciosBebe      Ver el resultado: carpeta logs\
# La PC debe estar encendida a esa hora (o marcar "Ejecutar lo antes posible si se omitió" en la tarea).
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
New-Item -ItemType Directory -Force -Path logs | Out-Null
$log = "logs\$(Get-Date -Format yyyy-MM-dd).log"
$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
Start-Transcript -Path $log -Append | Out-Null
try {
    & $py main.py;       if ($LASTEXITCODE -ne 0) { throw "main.py terminó con código $LASTEXITCODE" }
    & $py build_site.py; if ($LASTEXITCODE -ne 0) { throw "build_site.py terminó con código $LASTEXITCODE" }
} finally {
    Stop-Transcript | Out-Null
}
