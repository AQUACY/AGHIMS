#!/bin/bash
# Quick script to check and fix MySQL connection issues

echo "=========================================="
echo "MySQL Connection Diagnostic"
echo "=========================================="
echo ""

# Check MySQL service status
echo "1. Checking MySQL service status..."
if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mysqld 2>/dev/null; then
    echo "   ✓ MySQL service is running"
    systemctl status mysql --no-pager 2>/dev/null | head -5 || systemctl status mysqld --no-pager 2>/dev/null | head -5
else
    echo "   ✗ MySQL service is NOT running"
    echo ""
    echo "   Attempting to start MySQL..."
    sudo systemctl start mysql 2>/dev/null || sudo systemctl start mysqld 2>/dev/null
    sleep 2
    if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mysqld 2>/dev/null; then
        echo "   ✓ MySQL started successfully"
    else
        echo "   ✗ Failed to start MySQL. Please check MySQL installation."
        exit 1
    fi
fi
echo ""

# Check if MySQL is listening
echo "2. Checking if MySQL is listening on port 3306..."
if netstat -tln 2>/dev/null | grep -q ":3306 " || ss -tln 2>/dev/null | grep -q ":3306 "; then
    echo "   ✓ MySQL is listening on port 3306"
else
    echo "   ✗ MySQL is NOT listening on port 3306"
    echo "   MySQL may need to be restarted or configured"
fi
echo ""

# Test connection (if credentials available)
echo "3. Testing database connection..."
if [ -f ".env" ]; then
    source .env 2>/dev/null
    if [ -n "$MYSQL_USER" ] && [ -n "$MYSQL_PASSWORD" ] && [ -n "$MYSQL_DATABASE" ]; then
        mysql -h ${MYSQL_HOST:-localhost} -P ${MYSQL_PORT:-3306} -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" "$MYSQL_DATABASE" 2>&1 | head -3
        if [ $? -eq 0 ]; then
            echo "   ✓ Database connection successful"
        else
            echo "   ✗ Database connection failed"
            echo "   Check your .env file for correct MySQL credentials"
        fi
    else
        echo "   ⚠ MySQL credentials not found in .env file"
    fi
else
    echo "   ⚠ .env file not found"
fi
echo ""

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. If MySQL was not running, it should now be started"
echo "2. Restart your backend server:"
echo "   sudo systemctl restart hms-api"
echo "3. Check server status:"
echo "   sudo systemctl status hms-api"
echo ""

