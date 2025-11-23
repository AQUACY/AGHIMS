#!/bin/bash
# Check for sql_mode in all MySQL config files

echo "=========================================="
echo "Checking ALL MySQL Config Files for sql_mode"
echo "=========================================="
echo ""

# Check all possible config files
CONFIG_FILES=(
    "/etc/mysql/mysql.conf.d/mysqld.cnf"
    "/etc/mysql/my.cnf"
    "/etc/my.cnf"
    "/etc/mysql/conf.d/mysql.cnf"
    "/etc/mysql/conf.d/mysqld_safe_syslog.cnf"
    "/etc/mysql/debian.cnf"
    "~/.my.cnf"
)

echo "Searching for sql_mode in all config files:"
echo "-----------------------------------"
for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        echo ""
        echo "File: $config"
        echo "---"
        sudo grep -i "sql_mode\|sql-mode" "$config" 2>/dev/null || echo "  (not found)"
    fi
done

echo ""
echo "=========================================="
echo "Searching for NO_AUTO_CREATE_USER anywhere:"
echo "=========================================="
for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        if sudo grep -q "NO_AUTO_CREATE_USER" "$config" 2>/dev/null; then
            echo "✗ Found in: $config"
            sudo grep -i "NO_AUTO_CREATE_USER" "$config"
        fi
    fi
done

echo ""
echo "=========================================="
echo "Checking for duplicate [mysqld] sections:"
echo "=========================================="
for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        COUNT=$(sudo grep -c "^\[mysqld\]" "$config" 2>/dev/null || echo "0")
        if [ "$COUNT" -gt 1 ]; then
            echo "⚠ Multiple [mysqld] sections in: $config"
            sudo grep -n "^\[mysqld\]" "$config"
        fi
    fi
done

echo ""
echo "=========================================="
echo "Current MySQL Error (most recent):"
echo "=========================================="
if [ -f "/var/log/mysql/error.log" ]; then
    echo "Last 10 lines of error log:"
    sudo tail -10 /var/log/mysql/error.log
elif [ -f "/var/log/mysqld.log" ]; then
    echo "Last 10 lines of error log:"
    sudo tail -10 /var/log/mysqld.log
else
    echo "Error log not found, checking journalctl:"
    sudo journalctl -u mysql -n 10 --no-pager
fi

