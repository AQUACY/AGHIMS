#!/bin/bash
# Diagnose MySQL startup issues

echo "=========================================="
echo "MySQL Startup Diagnostic"
echo "=========================================="
echo ""

# Check service status
echo "1. MySQL Service Status:"
sudo systemctl status mysql --no-pager | head -20
echo ""

# Check recent MySQL logs
echo "2. Recent MySQL Error Logs:"
if [ -f "/var/log/mysql/error.log" ]; then
    echo "   Last 30 lines of MySQL error log:"
    sudo tail -30 /var/log/mysql/error.log
elif [ -f "/var/log/mysqld.log" ]; then
    echo "   Last 30 lines of MySQL error log:"
    sudo tail -30 /var/log/mysqld.log
else
    echo "   MySQL error log not found in standard locations"
    echo "   Checking journalctl..."
    sudo journalctl -u mysql -n 30 --no-pager
fi
echo ""

# Check systemd logs
echo "3. Systemd MySQL Logs:"
sudo journalctl -u mysql -n 50 --no-pager | tail -30
echo ""

# Check MySQL configuration
echo "4. Checking MySQL Configuration:"
if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    echo "   MySQL config file exists"
    sudo grep -E "^(bind-address|port|datadir)" /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null || echo "   Could not read config"
elif [ -f "/etc/my.cnf" ]; then
    echo "   MySQL config file exists at /etc/my.cnf"
    sudo grep -E "^(bind-address|port|datadir)" /etc/my.cnf 2>/dev/null || echo "   Could not read config"
else
    echo "   MySQL config file not found"
fi
echo ""

# Check data directory
echo "5. Checking MySQL Data Directory:"
MYSQL_DATADIR=$(sudo grep -E "^datadir" /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo "/var/lib/mysql")
if [ -d "$MYSQL_DATADIR" ]; then
    echo "   Data directory: $MYSQL_DATADIR"
    echo "   Permissions:"
    ls -ld "$MYSQL_DATADIR" 2>/dev/null || sudo ls -ld "$MYSQL_DATADIR"
    echo "   Owner:"
    ls -ld "$MYSQL_DATADIR" | awk '{print $3":"$4}' 2>/dev/null || sudo ls -ld "$MYSQL_DATADIR" | awk '{print $3":"$4}'
else
    echo "   ✗ Data directory not found: $MYSQL_DATADIR"
fi
echo ""

# Check if port is in use
echo "6. Checking if port 3306 is in use:"
if netstat -tlnp 2>/dev/null | grep -q ":3306 " || ss -tlnp 2>/dev/null | grep -q ":3306 "; then
    echo "   Port 3306 is in use:"
    sudo netstat -tlnp | grep ":3306 " 2>/dev/null || sudo ss -tlnp | grep ":3306 "
else
    echo "   Port 3306 is NOT in use"
fi
echo ""

# Check MySQL process
echo "7. Checking for MySQL processes:"
if pgrep -f mysqld > /dev/null; then
    echo "   MySQL processes found:"
    ps aux | grep mysqld | grep -v grep
else
    echo "   No MySQL processes running"
fi
echo ""

echo "=========================================="
echo "Common Fixes"
echo "=========================================="
echo ""
echo "If you see permission errors:"
echo "  sudo chown -R mysql:mysql /var/lib/mysql"
echo ""
echo "If you see 'datadir' errors:"
echo "  sudo mkdir -p /var/lib/mysql"
echo "  sudo chown -R mysql:mysql /var/lib/mysql"
echo ""
echo "If MySQL was installed but not initialized:"
echo "  sudo mysql_install_db --user=mysql --datadir=/var/lib/mysql"
echo "  OR for MySQL 8.0+:"
echo "  sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql"
echo ""

