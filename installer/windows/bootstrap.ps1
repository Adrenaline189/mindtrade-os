param(
  [string]$InstallDir = "$env:USERPROFILE\TradingBot",
  [switch]$RunNow
)

$ErrorActionPreference = 'Stop'
Write-Host "[1/7] Preparing install dir: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Host "[2/7] Checking Python..."
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "Python launcher (py) not found. Please install Python 3.11+ first." -ForegroundColor Yellow
  exit 1
}

Write-Host "[3/7] Creating virtualenv..."
Set-Location $InstallDir
if (!(Test-Path "$InstallDir\venv")) {
  py -3 -m venv venv
}

Write-Host "[4/7] Installing dependencies..."
& "$InstallDir\venv\Scripts\python.exe" -m pip install --upgrade pip
if (Test-Path "$InstallDir\requirements.txt") {
  & "$InstallDir\venv\Scripts\pip.exe" install -r "$InstallDir\requirements.txt"
} else {
  Write-Host "requirements.txt not found in $InstallDir" -ForegroundColor Yellow
}

Write-Host "[5/7] Ensuring .env exists..."
if (!(Test-Path "$InstallDir\.env") -and (Test-Path "$InstallDir\.env.example")) {
  Copy-Item "$InstallDir\.env.example" "$InstallDir\.env"
}

Write-Host "[6/7] Registering startup + health tasks..."
$startBat = "$InstallDir\start_bot_windows.bat"
@"
@echo off
cd /d "$InstallDir"
start "" /min "$InstallDir\venv\Scripts\python.exe" "$InstallDir\main.py"
"@ | Set-Content -Path $startBat -Encoding ascii

$healthPs1 = "$InstallDir\windows_healthcheck.ps1"
@"
`$botDir = '$InstallDir'
`$pythonExe = Join-Path `$botDir 'venv\Scripts\python.exe'
try {
  `$r = Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 5
  if (`$r.StatusCode -ne 200) {
    Start-Process -WindowStyle Hidden -FilePath `$pythonExe -ArgumentList 'main.py' -WorkingDirectory `$botDir
  }
} catch {
  Start-Process -WindowStyle Hidden -FilePath `$pythonExe -ArgumentList 'main.py' -WorkingDirectory `$botDir
}
"@ | Set-Content -Path $healthPs1 -Encoding ascii

schtasks /Create /TN TradingBot_Autostart /TR "$startBat" /SC ONSTART /RU SYSTEM /RL HIGHEST /F | Out-Null
schtasks /Create /TN TradingBot_HealthCheck /TR "powershell -NoProfile -ExecutionPolicy Bypass -File $healthPs1" /SC MINUTE /MO 5 /RU SYSTEM /RL HIGHEST /F | Out-Null

Write-Host "[7/7] Done."
Write-Host "Dashboard: http://127.0.0.1:8000"

if ($RunNow) {
  Write-Host "Starting bot now..."
  Start-Process -WindowStyle Hidden -FilePath "$InstallDir\venv\Scripts\python.exe" -ArgumentList "$InstallDir\main.py" -WorkingDirectory $InstallDir
}
