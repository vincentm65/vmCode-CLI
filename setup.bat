@echo off
REM bone-agent setup script for Windows (git clone installation)
REM This script sets up bone-agent as a system command

echo ==========================================
echo   bone-agent Setup
echo ==========================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo Project root: %PROJECT_ROOT%
echo.

REM Check Python
echo Checking for Python 3.9+...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.9 or later from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Install Python dependencies
echo.
echo Installing Python dependencies...
cd /d "%PROJECT_ROOT%"
pip install -q -r requirements.txt

if errorlevel 1 (
    echo Failed to install Python dependencies
    pause
    exit /b 1
)

echo Python dependencies installed
echo.

REM Setup config
if not exist "config.yaml" (
    if exist "config.yaml.example" (
        echo Creating config.yaml from example...
        copy config.yaml.example config.yaml >nul
        echo config.yaml created
        echo.
        echo IMPORTANT: Edit config.yaml and add your API keys!
        echo    Or set them via environment variables:
        echo    set OPENAI_API_KEY=sk-your-key-here
        echo.
    ) else (
        echo Warning: config.yaml.example not found
    )
) else (
    echo config.yaml already exists
)

REM Create bone command
echo.
echo Setting up bone-agent command...

REM Option 1: Create batch file in PATH
set "USER_BIN=%USERPROFILE%\bin"
if not exist "%USER_BIN%" mkdir "%USER_BIN%"

REM Create bone-agent.bat launcher
(
echo @echo off
echo REM bone-agent launcher
echo cd /d "%PROJECT_ROOT%"
echo python src/ui/main.py %%*
) > "%USER_BIN%\bone-agent.bat"

echo Created command: %USER_BIN%\bone-agent.bat

REM Check if USER_BIN is in PATH
echo %PATH% | find /i /c "%USER_BIN%" >nul
if errorlevel 1 (
    echo.
    echo WARNING: %USER_BIN% is not in your PATH
    echo.
    echo To add to PATH ^(recommended^):
    echo   1. Press Win key, search for "Environment Variables"
    echo   2. Click "Edit the system environment variables"
    echo   3. Click "Environment Variables..."
    echo   4. Under "User variables", select "Path" and click "Edit"
    echo   5. Click "New" and add: %%USERBIN%%
    echo   6. Click OK on all dialogs
    echo.
    echo   Or run this command in PowerShell ^(temporary^):
    echo   $env:Path += ";%%USERBIN%%"
) else (
    echo %USER_BIN% is already in PATH
)

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Run bone-agent:
echo   bone-agent
echo.
echo Or run directly:
echo   cd %PROJECT_ROOT%
echo   python src/ui/main.py
echo.

pause
