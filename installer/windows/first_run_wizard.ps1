param(
  [string]$InstallDir = "$env:USERPROFILE\TradingBot"
)

$envPath = Join-Path $InstallDir '.env'
if (!(Test-Path $envPath)) {
  Write-Host ".env not found at $envPath" -ForegroundColor Yellow
  exit 1
}

function Set-EnvValue($path, $key, $value) {
  $lines = @()
  if (Test-Path $path) { $lines = Get-Content $path }
  $found = $false
  for ($i=0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^$key=") {
      $lines[$i] = "$key=$value"
      $found = $true
    }
  }
  if (-not $found) { $lines += "$key=$value" }
  Set-Content -Path $path -Value $lines -Encoding ascii
}

Write-Host "=== Trading Bot First-Run Wizard ==="
$apiKey = Read-Host "BINANCE_API_KEY"
$apiSec = Read-Host "BINANCE_API_SECRET"
$symbols = Read-Host "Symbols (comma, e.g. BTC/USDT,ETH/USDT,SOL/USDT)"
$risk = Read-Host "Risk per trade (e.g. 0.01)"
$lev = Read-Host "Default leverage (e.g. 5)"
$tgToken = Read-Host "Telegram Bot Token (optional)"
$tgChat = Read-Host "Telegram Chat ID (optional)"

Set-EnvValue $envPath 'BINANCE_API_KEY' $apiKey
Set-EnvValue $envPath 'BINANCE_API_SECRET' $apiSec
if ($tgToken) { Set-EnvValue $envPath 'TELEGRAM_BOT_TOKEN' $tgToken }
if ($tgChat) { Set-EnvValue $envPath 'TELEGRAM_CHAT_ID' $tgChat }

$configPath = Join-Path $InstallDir 'bot\config_runtime.py'
if (Test-Path $configPath) {
  $c = Get-Content $configPath -Raw
  if ($symbols) { $c = [regex]::Replace($c, '"SYMBOLS"\s*:\s*\[[^\]]*\]', '"SYMBOLS": ["' + ($symbols -replace ',', '","') + '"]') }
  if ($risk)    { $c = [regex]::Replace($c, '"RISK_PER_TRADE"\s*:\s*[0-9\.]+', '"RISK_PER_TRADE": ' + $risk) }
  if ($lev)     { $c = [regex]::Replace($c, '"LEVERAGE"\s*:\s*[0-9]+', '"LEVERAGE": ' + $lev) }
  Set-Content $configPath $c -Encoding utf8
}

Write-Host "Saved. You can now run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $InstallDir\installer\windows\bootstrap.ps1 -InstallDir $InstallDir -RunNow"
