#!/bin/bash
# Quick MySQL Diagnostic - Run all checks at once

echo "=========================================="
echo "MySQL Diagnostic - Complete Check"
echo "=========================================="
echo ""

# 1. Run pre-start check
echo "1. Running MySQL Pre-Start Check:"
echo "-----------------------------------"
sudo /usr/share/mysql/mysql-systemd-start pre
PRE_EXIT=$?
if [ $PRE_EXIT -eq 0 ]; then
    echo "✓ Pre-start check PASSED"
else
    echo "✗ Pre-start check FAILED (exit code: $PRE_EXIT)"
fi
echo ""

# 2. Check MySQL error log
echo "2. MySQL Error Log (last 50 lines):"
echo "-----------------------------------"
if [ -f "/var/log/mysql/error.log" ]; then
    sudo tail -50 /var/log/mysql/error.log
elif [ -f "/var/log/mysqld.log" ]; then
    sudo tail -50 /var/log/mysqld.log
else
    echo "MySQL error log file not found in standard locations"
    echo "Checking journalctl instead..."
    sudo journalctl -u mysql -n 50 --no-pager
fi
echo ""

# 3. Check systemd logs
echo "3. Systemd MySQL Logs (last 50 lines):"
echo "-----------------------------------"
sudo journalctl -u mysql -n 50 --no-pager
echo ""

# 4. Check service status
echo "4. MySQL Service Status:"
echo "-----------------------------------"
sudo systemctl status mysql --no-pager | head -15
echo ""

# 5. Check data directory
echo "5. Data Directory Check:"
echo "-----------------------------------"
if [ -d "/var/lib/mysql" ]; then
    echo "✓ Data directory exists: /var/lib/mysql"
    echo "Permissions:"
    sudo ls -ld /var/lib/mysql
    echo ""
    echo "First 10 files/directories:"
    sudo ls -la /var/lib/mysql | head -10
else
    echo "✗ Data directory does NOT exist: /var/lib/mysql"
fi
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="

