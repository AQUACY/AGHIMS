#!/bin/bash
# Unmask and start MySQL service

echo "=========================================="
echo "Fixing MySQL Masked Service"
echo "=========================================="
echo ""

# Try to unmask mysql service
echo "1. Unmasking MySQL service..."
if sudo systemctl unmask mysql 2>/dev/null; then
    echo "   ✓ mysql.service unmasked"
    SERVICE_NAME="mysql"
elif sudo systemctl unmask mysqld 2>/dev/null; then
    echo "   ✓ mysqld.service unmasked"
    SERVICE_NAME="mysqld"
else
    echo "   ✗ Could not unmask MySQL service"
    echo "   Checking available MySQL services..."
    systemctl list-unit-files | grep mysql
    exit 1
fi
echo ""

# Enable the service
echo "2. Enabling MySQL service..."
if sudo systemctl enable $SERVICE_NAME 2>/dev/null; then
    echo "   ✓ MySQL service enabled"
else
    echo "   ✗ Failed to enable MySQL service"
    exit 1
fi
echo ""

# Start the service
echo "3. Starting MySQL service..."
if sudo systemctl start $SERVICE_NAME 2>/dev/null; then
    echo "   ✓ MySQL service started"
else
    echo "   ✗ Failed to start MySQL service"
    echo "   Check MySQL logs:"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi
echo ""

# Check status
echo "4. Checking MySQL status..."
sudo systemctl status $SERVICE_NAME --no-pager | head -10
echo ""

# Test connection
echo "5. Testing MySQL connection..."
if netstat -tln 2>/dev/null | grep -q ":3306 " || ss -tln 2>/dev/null | grep -q ":3306 "; then
    echo "   ✓ MySQL is listening on port 3306"
else
    echo "   ✗ MySQL is NOT listening on port 3306"
    echo "   Check MySQL configuration and logs"
fi
echo ""

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. Restart your backend server:"
echo "   sudo systemctl restart hms-api"
echo ""
echo "2. Check backend status:"
echo "   sudo systemctl status hms-api"
echo ""

