@echo off
REM Run this as Administrator to fix firewall for analyzer
REM Right-click and "Run as Administrator"

echo ======================================================================
echo Configuring Windows Firewall for Analyzer Server
echo ======================================================================
echo.

REM Delete existing rule if it exists
netsh advfirewall firewall delete rule name="HMS Analyzer Server Port 5150" >nul 2>&1

REM Create new rule allowing connections from analyzer network
echo Creating firewall rule for port 5150...
netsh advfirewall firewall add rule name="HMS Analyzer Server Port 5150" dir=in action=allow protocol=TCP localport=5150 remoteip=10.10.16.0/20

echo.
echo Verifying rule...
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"

echo.
echo ======================================================================
echo Firewall rule created!
echo ======================================================================
echo.
echo The analyzer at 10.10.16.34 should now be able to connect.
echo.
pause

