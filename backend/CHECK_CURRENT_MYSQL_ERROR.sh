#!/bin/bash
# Check the most recent MySQL error

echo "=========================================="
echo "Current MySQL Error Check"
echo "=========================================="
echo ""

# Get the most recent error log entries
echo "1. Most Recent MySQL Error Log (last 30 lines):"
echo "-----------------------------------"
if [ -f "/var/log/mysql/error.log" ]; then
    sudo tail -30 /var/log/mysql/error.log
elif [ -f "/var/log/mysqld.log" ]; then
    sudo tail -30 /var/log/mysqld.log
else
    echo "Error log file not found"
fi
echo ""

# Check for the most recent ERROR entries
echo "2. Recent ERROR Messages:"
echo "-----------------------------------"
if [ -f "/var/log/mysql/error.log" ]; then
    sudo grep -i "ERROR" /var/log/mysql/error.log | tail -10
elif [ -f "/var/log/mysqld.log" ]; then
    sudo grep -i "ERROR" /var/log/mysqld.log | tail -10
fi
echo ""

# Check systemd logs for current attempt
echo "3. Current Systemd MySQL Logs:"
echo "-----------------------------------"
sudo journalctl -u mysql --since "1 minute ago" --no-pager
echo ""

# Try to start and capture immediate error
echo "4. Attempting Start and Capturing Error:"
echo "-----------------------------------"
sudo systemctl start mysql 2>&1
sleep 2
sudo systemctl status mysql --no-pager | head -20
echo ""

# Check if there's a specific error in the latest log
echo "5. Latest Error Entry:"
echo "-----------------------------------"
if [ -f "/var/log/mysql/error.log" ]; then
    sudo tail -1 /var/log/mysql/error.log
    echo ""
    # Get last 5 lines that contain ERROR
    echo "Last 5 ERROR lines:"
    sudo grep -i "ERROR" /var/log/mysql/error.log | tail -5
elif [ -f "/var/log/mysqld.log" ]; then
    sudo tail -1 /var/log/mysqld.log
    echo ""
    echo "Last 5 ERROR lines:"
    sudo grep -i "ERROR" /var/log/mysqld.log | tail -5
fi
echo ""

