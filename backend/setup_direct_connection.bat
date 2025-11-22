@echo off
REM Configure Ethernet adapter for direct connection to analyzer
REM Run as Administrator

echo ======================================================================
echo Direct Connection Setup - Ethernet Adapter Configuration
echo ======================================================================
echo.
echo This will configure your Ethernet adapter with static IP:
echo   PC IP: 10.10.17.223
echo   Analyzer IP: 10.10.16.34 (configure on analyzer)
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo Configuring Ethernet adapter...
netsh interface ip set address "Ethernet" static 10.10.17.223 255.255.240.0

echo.
echo Configuration complete!
echo.
echo ======================================================================
echo Current Ethernet Configuration:
echo ======================================================================
ipconfig | findstr /A:on /B:on "Ethernet" /C:"IPv4" /C:"Subnet"

echo.
echo ======================================================================
echo Next Steps:
echo ======================================================================
echo 1. Connect Ethernet cable between PC and analyzer
echo 2. Configure analyzer with:
echo    - IP Address: 10.10.16.34
echo    - Subnet Mask: 255.255.240.0
echo    - Host IP: 10.10.17.223
echo    - Port: 5150
echo 3. Test connection: ping 10.10.16.34
echo 4. Process a sample on analyzer
echo ======================================================================
echo.
pause

