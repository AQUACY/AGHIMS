#!/bin/bash
# Capture MySQL startup error in real-time

echo "=========================================="
echo "Capturing MySQL Startup Error"
echo "=========================================="
echo ""

# Clear any old error log entries (just to see fresh errors)
echo "1. Clearing error log tail position..."
# We'll use tail -f to follow the log

# Get the current error log file
ERROR_LOG=""
if [ -f "/var/log/mysql/error.log" ]; then
    ERROR_LOG="/var/log/mysql/error.log"
elif [ -f "/var/log/mysqld.log" ]; then
    ERROR_LOG="/var/log/mysqld.log"
else
    echo "✗ Error log file not found"
    exit 1
fi

echo "   Using error log: $ERROR_LOG"
echo ""

# Get current line count
CURRENT_LINES=$(sudo wc -l < "$ERROR_LOG" 2>/dev/null || echo "0")
echo "   Current log has $CURRENT_LINES lines"
echo ""

# Try to start MySQL and capture error
echo "2. Attempting to start MySQL..."
echo "-----------------------------------"
sudo systemctl start mysql 2>&1
START_EXIT=$?
echo "   Start command exit code: $START_EXIT"
echo ""

# Wait a moment for MySQL to attempt startup
sleep 3

# Check new log entries
echo "3. New Error Log Entries (after startup attempt):"
echo "-----------------------------------"
NEW_LINES=$(sudo wc -l < "$ERROR_LOG" 2>/dev/null || echo "0")
if [ "$NEW_LINES" -gt "$CURRENT_LINES" ]; then
    LINES_TO_SHOW=$((NEW_LINES - CURRENT_LINES + 5))
    sudo tail -n "$LINES_TO_SHOW" "$ERROR_LOG"
else
    echo "   No new log entries. Showing last 20 lines:"
    sudo tail -20 "$ERROR_LOG"
fi
echo ""

# Check for ERROR messages
echo "4. ERROR Messages in Log:"
echo "-----------------------------------"
sudo grep -i "ERROR" "$ERROR_LOG" | tail -10
echo ""

# Check systemd status
echo "5. Systemd Status:"
echo "-----------------------------------"
sudo systemctl status mysql --no-pager | head -25
echo ""

# Check journalctl for recent errors
echo "6. Recent Journalctl Logs:"
echo "-----------------------------------"
sudo journalctl -u mysql --since "30 seconds ago" --no-pager
echo ""

# Try to run mysqld directly to see error
echo "7. Testing mysqld Directly (dry-run):"
echo "-----------------------------------"
echo "   This will show configuration errors without starting:"
sudo /usr/sbin/mysqld --validate-config 2>&1 | head -20
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="

