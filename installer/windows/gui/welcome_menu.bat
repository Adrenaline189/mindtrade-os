@echo off
setlocal
set INSTALL_DIR=%USERPROFILE%\TradingBot

:menu
cls
echo ======================================
echo   MindTrade OS Windows Quick Menu
echo ======================================
echo [1] Install / Repair
echo [2] First-run Wizard
echo [3] Start Bot
echo [4] Stop Bot
echo [5] Open Dashboard
echo [6] Uninstall
echo [0] Exit
echo.
set /p CHOICE=Choose: 

if "%CHOICE%"=="1" goto install
if "%CHOICE%"=="2" goto wizard
if "%CHOICE%"=="3" goto start
if "%CHOICE%"=="4" goto stop
if "%CHOICE%"=="5" goto open
if "%CHOICE%"=="6" goto uninstall
if "%CHOICE%"=="0" exit /b

goto menu

:install
call "%~dp0..\setup_oneclick.bat"
goto menu

:wizard
powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\installer\windows\first_run_wizard.ps1" -InstallDir "%INSTALL_DIR%"
goto menu

:start
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -WindowStyle Hidden -FilePath '%INSTALL_DIR%\venv\Scripts\python.exe' -ArgumentList '%INSTALL_DIR%\main.py' -WorkingDirectory '%INSTALL_DIR%'"
goto menu

:stop
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*TradingBot*' } | Stop-Process -Force -ErrorAction SilentlyContinue"
goto menu

:open
start "" http://127.0.0.1:8000
goto menu

:uninstall
powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\installer\windows\uninstall.ps1" -InstallDir "%INSTALL_DIR%"
goto menu
