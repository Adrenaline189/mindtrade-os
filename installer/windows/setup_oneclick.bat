@echo off
setlocal

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting Administrator permission...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set INSTALL_DIR=%USERPROFILE%\TradingBot
echo Installing to %INSTALL_DIR%

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy current folder content into install dir if script is run from extracted package
xcopy "%~dp0..\..\*" "%INSTALL_DIR%\" /E /I /Y >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\installer\windows\bootstrap.ps1" -InstallDir "%INSTALL_DIR%" -RunNow

if %errorlevel% neq 0 (
  echo Setup failed. Please check output.
  pause
  exit /b 1
)

echo.
echo Setup complete!
echo Open dashboard: http://127.0.0.1:8000
echo Run wizard: powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\installer\windows\first_run_wizard.ps1" -InstallDir "%INSTALL_DIR%"
pause
