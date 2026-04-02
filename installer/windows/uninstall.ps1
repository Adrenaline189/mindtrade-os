param(
  [string]$InstallDir = "$env:USERPROFILE\TradingBot"
)

$ErrorActionPreference = 'Stop'
Write-Host "Uninstalling TradingBot from $InstallDir"

# Stop bot process if running
Get-Process -Name python -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "*$InstallDir*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue

# Remove scheduled tasks
schtasks /Delete /TN TradingBot_Autostart /F | Out-Null 2>$null
schtasks /Delete /TN TradingBot_HealthCheck /F | Out-Null 2>$null

# Remove install directory
if (Test-Path $InstallDir) {
  Remove-Item -Recurse -Force $InstallDir
}

Write-Host "Uninstall complete."
