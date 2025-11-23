#!/bin/bash
# Check MySQL pre-start script errors

echo "=========================================="
echo "MySQL Pre-Start Error Diagnostic"
echo "=========================================="
echo ""

# Check the pre-start script directly
echo "1. Running MySQL pre-start check manually:"
if [ -f "/usr/share/mysql/mysql-systemd-start" ]; then
    sudo /usr/share/mysql/mysql-systemd-start pre
    PRE_START_EXIT=$?
    echo ""
    echo "   Exit code: $PRE_START_EXIT"
    if [ $PRE_START_EXIT -ne 0 ]; then
        echo "   ✗ Pre-start check FAILED"
    else
        echo "   ✓ Pre-start check PASSED"
    fi
else
    echo "   ✗ Pre-start script not found"
fi
echo ""

# Check MySQL error log
echo "2. MySQL Error Log (last 50 lines):"
if [ -f "/var/log/mysql/error.log" ]; then
    sudo tail -50 /var/log/mysql/error.log
elif [ -f "/var/log/mysqld.log" ]; then
    sudo tail -50 /var/log/mysqld.log
else
    echo "   MySQL error log not found. Checking journalctl..."
    sudo journalctl -u mysql -n 50 --no-pager | grep -i error
fi
echo ""

# Check data directory
echo "3. Checking MySQL Data Directory:"
MYSQL_DATADIR="/var/lib/mysql"
if [ -d "$MYSQL_DATADIR" ]; then
    echo "   Data directory exists: $MYSQL_DATADIR"
    echo "   Permissions:"
    ls -ld "$MYSQL_DATADIR" 2>/dev/null || sudo ls -ld "$MYSQL_DATADIR"
    echo "   Owner:"
    ls -ld "$MYSQL_DATADIR" | awk '{print $3":"$4}' 2>/dev/null || sudo ls -ld "$MYSQL_DATADIR" | awk '{print $3":"$4}'
    echo "   Contents:"
    ls -la "$MYSQL_DATADIR" 2>/dev/null | head -10 || sudo ls -la "$MYSQL_DATADIR" | head -10
else
    echo "   ✗ Data directory does NOT exist: $MYSQL_DATADIR"
fi
echo ""

# Check MySQL configuration
echo "4. Checking MySQL Configuration:"
if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    echo "   Config file: /etc/mysql/mysql.conf.d/mysqld.cnf"
    DATADIR=$(sudo grep -E "^datadir" /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo "not found")
    echo "   Configured datadir: $DATADIR"
    if [ "$DATADIR" != "not found" ] && [ "$DATADIR" != "$MYSQL_DATADIR" ]; then
        echo "   ⚠ Warning: Configured datadir ($DATADIR) differs from default ($MYSQL_DATADIR)"
        if [ ! -d "$DATADIR" ]; then
            echo "   ✗ Configured datadir does NOT exist"
        fi
    fi
elif [ -f "/etc/my.cnf" ]; then
    echo "   Config file: /etc/my.cnf"
    DATADIR=$(sudo grep -E "^datadir" /etc/my.cnf 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo "not found")
    echo "   Configured datadir: $DATADIR"
else
    echo "   ✗ MySQL config file not found"
fi
echo ""

# Check for socket file issues
echo "5. Checking MySQL Socket:"
SOCKET_FILE="/var/run/mysqld/mysqld.sock"
if [ -S "$SOCKET_FILE" ]; then
    echo "   ⚠ Socket file exists (might be stale): $SOCKET_FILE"
    ls -l "$SOCKET_FILE" 2>/dev/null || sudo ls -l "$SOCKET_FILE"
    echo "   Consider removing if stale: sudo rm $SOCKET_FILE"
else
    echo "   Socket file does not exist (this is normal if MySQL is not running)"
fi
echo ""

# Check if MySQL is initialized
echo "6. Checking if MySQL is initialized:"
if [ -d "$MYSQL_DATADIR" ]; then
    if [ -f "$MYSQL_DATADIR/mysql/user.MYD" ] || [ -f "$MYSQL_DATADIR/mysql/user.ibd" ] || [ -d "$MYSQL_DATADIR/mysql" ]; then
        echo "   ✓ MySQL appears to be initialized (mysql directory exists)"
    else
        echo "   ✗ MySQL does NOT appear to be initialized"
        echo "   The mysql system database is missing"
    fi
else
    echo "   ✗ Cannot check - data directory does not exist"
fi
echo ""

echo "=========================================="
echo "Common Fixes"
echo "=========================================="
echo ""
echo "If data directory doesn't exist or has wrong permissions:"
echo "  sudo mkdir -p /var/lib/mysql"
echo "  sudo chown -R mysql:mysql /var/lib/mysql"
echo "  sudo chmod -R 755 /var/lib/mysql"
echo ""
echo "If MySQL is not initialized:"
echo "  sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql"
echo ""
echo "If socket file is stale:"
echo "  sudo rm -f /var/run/mysqld/mysqld.sock"
echo "  sudo mkdir -p /var/run/mysqld"
echo "  sudo chown mysql:mysql /var/run/mysqld"
echo ""

