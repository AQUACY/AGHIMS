@echo off
REM Reset Ethernet adapter to DHCP (revert direct connection setup)
REM Run as Administrator

echo ======================================================================
echo Resetting Ethernet Adapter to DHCP
echo ======================================================================
echo.
echo This will reset the Ethernet adapter to obtain IP automatically.
echo.
pause

netsh interface ip set address "Ethernet" dhcp

echo.
echo Ethernet adapter reset to DHCP.
echo.
ipconfig | findstr /A:on /B:on "Ethernet" /C:"IPv4"
echo.
pause

