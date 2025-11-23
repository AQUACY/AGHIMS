@echo off
REM Quick install script for APScheduler dependency (Windows)
REM Use this if you only need to install the new dependency without reinstalling everything

echo ==========================================
echo Installing APScheduler (Database Management)
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

REM Check if virtual environment is active
if defined VIRTUAL_ENV (
    echo Virtual environment detected: %VIRTUAL_ENV%
    echo.
) else (
    echo WARNING: Virtual environment not detected.
    echo It's recommended to use a virtual environment.
    echo.
)

REM Install APScheduler
echo Installing APScheduler...
pip install apscheduler^>=3.10.4

if errorlevel 1 (
    echo.
    echo ==========================================
    echo Installation failed!
    echo ==========================================
    echo.
    echo Common issues:
    echo 1. Python version too old (needs 3.7+)
    echo 2. pip not installed or outdated
    echo 3. Network/firewall issues
    echo.
    echo See INSTALL_NEW_DEPENDENCIES.md for troubleshooting.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo APScheduler installed successfully!
echo ==========================================
echo.
echo Verifying installation...
python -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
echo.
echo Next steps:
echo 1. Restart your application server
echo 2. Navigate to Admin -^> Database Management to configure backups
echo.
pause

