#!/bin/bash
# Fix MySQL sql_mode error - Remove NO_AUTO_CREATE_USER

echo "=========================================="
echo "Fixing MySQL sql_mode Error"
echo "=========================================="
echo ""

# Find MySQL config file
CONFIG_FILE=""
if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    CONFIG_FILE="/etc/mysql/mysql.conf.d/mysqld.cnf"
    echo "Found config file: $CONFIG_FILE"
elif [ -f "/etc/mysql/my.cnf" ]; then
    CONFIG_FILE="/etc/mysql/my.cnf"
    echo "Found config file: $CONFIG_FILE"
elif [ -f "/etc/my.cnf" ]; then
    CONFIG_FILE="/etc/my.cnf"
    echo "Found config file: $CONFIG_FILE"
else
    echo "✗ MySQL config file not found"
    echo "Searching for config files..."
    sudo find /etc -name "*.cnf" -path "*/mysql/*" 2>/dev/null | head -5
    exit 1
fi

echo ""

# Backup config file
echo "1. Creating backup of config file..."
sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "   ✓ Backup created"
echo ""

# Check current sql_mode
echo "2. Current sql_mode setting:"
CURRENT_MODE=$(sudo grep -i "^sql_mode" "$CONFIG_FILE" 2>/dev/null || sudo grep -i "^sql-mode" "$CONFIG_FILE" 2>/dev/null)
if [ -n "$CURRENT_MODE" ]; then
    echo "   $CURRENT_MODE"
else
    echo "   No sql_mode found in config (might be in [mysqld] section or commented out)"
    # Check for commented lines
    sudo grep -i "sql_mode\|sql-mode" "$CONFIG_FILE" 2>/dev/null | head -3
fi
echo ""

# Fix sql_mode
echo "3. Fixing sql_mode (removing NO_AUTO_CREATE_USER)..."
echo ""

# Method 1: Use sed to remove NO_AUTO_CREATE_USER from existing line
if sudo grep -q "NO_AUTO_CREATE_USER" "$CONFIG_FILE" 2>/dev/null; then
    echo "   Removing NO_AUTO_CREATE_USER from sql_mode..."
    
    # Remove NO_AUTO_CREATE_USER from the line
    sudo sed -i.bak "s/NO_AUTO_CREATE_USER,//g" "$CONFIG_FILE"
    sudo sed -i.bak "s/,NO_AUTO_CREATE_USER//g" "$CONFIG_FILE"
    sudo sed -i.bak "s/NO_AUTO_CREATE_USER//g" "$CONFIG_FILE"
    
    # Clean up any double commas
    sudo sed -i.bak 's/,,/,/g' "$CONFIG_FILE"
    sudo sed -i.bak 's/^,//g' "$CONFIG_FILE"
    sudo sed -i.bak 's/,$//g' "$CONFIG_FILE"
    
    echo "   ✓ Removed NO_AUTO_CREATE_USER"
else
    echo "   ⚠ NO_AUTO_CREATE_USER not found in config file"
    echo "   Checking if sql_mode needs to be set..."
    
    # Check if [mysqld] section exists
    if sudo grep -q "^\[mysqld\]" "$CONFIG_FILE"; then
        echo "   Adding/updating sql_mode in [mysqld] section..."
        # Remove old sql_mode lines and add new one
        sudo sed -i.bak '/^sql_mode\|^sql-mode/d' "$CONFIG_FILE"
        # Add after [mysqld] line
        sudo sed -i.bak '/^\[mysqld\]/a sql_mode = "NO_ENGINE_SUBSTITUTION"' "$CONFIG_FILE"
        echo "   ✓ Set sql_mode to NO_ENGINE_SUBSTITUTION"
    else
        echo "   ⚠ [mysqld] section not found, adding it..."
        echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "[mysqld]" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "sql_mode = \"NO_ENGINE_SUBSTITUTION\"" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "   ✓ Added [mysqld] section with sql_mode"
    fi
fi

echo ""

# Show updated sql_mode
echo "4. Updated sql_mode setting:"
UPDATED_MODE=$(sudo grep -i "^sql_mode\|^sql-mode" "$CONFIG_FILE" 2>/dev/null | grep -v "^#")
if [ -n "$UPDATED_MODE" ]; then
    echo "   $UPDATED_MODE"
else
    echo "   (sql_mode not explicitly set - will use MySQL defaults)"
fi
echo ""

# Try to start MySQL
echo "5. Attempting to start MySQL..."
if sudo systemctl start mysql 2>&1; then
    echo "   ✓ MySQL started successfully!"
    echo ""
    echo "6. Checking MySQL status:"
    sudo systemctl status mysql --no-pager | head -10
else
    echo "   ✗ Failed to start MySQL"
    echo ""
    echo "   Check error logs:"
    sudo tail -20 /var/log/mysql/error.log 2>/dev/null || sudo journalctl -u mysql -n 20 --no-pager
fi

echo ""
echo "=========================================="
echo "Fix Complete"
echo "=========================================="
echo ""
echo "If MySQL still fails to start, check:"
echo "  sudo tail -50 /var/log/mysql/error.log"
echo "  sudo journalctl -u mysql -n 50 --no-pager"
echo ""

