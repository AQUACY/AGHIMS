#!/bin/bash
# Find ALL locations where sql_mode is set

echo "=========================================="
echo "Finding ALL sql_mode Locations"
echo "=========================================="
echo ""

# Search in all MySQL directories
echo "1. Searching /etc/mysql/ recursively:"
echo "-----------------------------------"
sudo find /etc/mysql -type f -name "*.cnf" -o -name "*.conf" 2>/dev/null | while read file; do
    if sudo grep -q "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null; then
        echo ""
        echo "File: $file"
        echo "---"
        sudo grep -i "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null
    fi
done
echo ""

# Search in /etc
echo "2. Searching /etc for MySQL configs:"
echo "-----------------------------------"
sudo find /etc -maxdepth 3 -type f \( -name "*.cnf" -o -name "*.conf" -o -name "my.cnf" -o -name "mysqld.cnf" \) 2>/dev/null | while read file; do
    if sudo grep -q "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null; then
        echo ""
        echo "File: $file"
        echo "---"
        sudo grep -i "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null
    fi
done
echo ""

# Check main config file for includes
echo "3. Checking for included config files:"
echo "-----------------------------------"
MAIN_CONFIG="/etc/mysql/mysql.conf.d/mysqld.cnf"
if [ -f "$MAIN_CONFIG" ]; then
    echo "Main config: $MAIN_CONFIG"
    echo "Looking for !includedir and !include directives:"
    sudo grep -i "!includedir\|!include" "$MAIN_CONFIG" 2>/dev/null || echo "  (none found)"
    
    # Check included directories
    INCLUDED_DIRS=$(sudo grep -i "!includedir" "$MAIN_CONFIG" 2>/dev/null | sed 's/.*!includedir[[:space:]]*//i' | tr -d ' ')
    for dir in $INCLUDED_DIRS; do
        if [ -d "$dir" ]; then
            echo ""
            echo "Checking included directory: $dir"
            sudo find "$dir" -type f -name "*.cnf" 2>/dev/null | while read inc_file; do
                if sudo grep -q "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$inc_file" 2>/dev/null; then
                    echo "  Found in: $inc_file"
                    sudo grep -i "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$inc_file" 2>/dev/null
                fi
            done
        fi
    done
fi
echo ""

# Check /etc/mysql/conf.d/ (common include directory)
echo "4. Checking /etc/mysql/conf.d/ directory:"
echo "-----------------------------------"
if [ -d "/etc/mysql/conf.d" ]; then
    sudo find /etc/mysql/conf.d -type f -name "*.cnf" 2>/dev/null | while read file; do
        if sudo grep -q "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null; then
            echo ""
            echo "File: $file"
            echo "---"
            sudo grep -i "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null
        fi
    done
else
    echo "  Directory does not exist"
fi
echo ""

# Check /etc/mysql/mysql.conf.d/ directory
echo "5. Checking /etc/mysql/mysql.conf.d/ directory:"
echo "-----------------------------------"
if [ -d "/etc/mysql/mysql.conf.d" ]; then
    sudo find /etc/mysql/mysql.conf.d -type f -name "*.cnf" 2>/dev/null | while read file; do
        if sudo grep -q "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null; then
            echo ""
            echo "File: $file"
            echo "---"
            sudo grep -i "sql_mode\|sql-mode\|NO_AUTO_CREATE_USER" "$file" 2>/dev/null
        fi
    done
else
    echo "  Directory does not exist"
fi
echo ""

echo "=========================================="
echo "Search Complete"
echo "=========================================="

