#!/bin/bash
# Fix sql_mode in ALL config files

echo "=========================================="
echo "Fixing sql_mode in ALL Config Files"
echo "=========================================="
echo ""

# Find all files with sql_mode or NO_AUTO_CREATE_USER
FILES_TO_FIX=$(sudo find /etc/mysql -type f \( -name "*.cnf" -o -name "*.conf" \) 2>/dev/null | xargs sudo grep -l "NO_AUTO_CREATE_USER\|sql_mode.*NO_AUTO_CREATE_USER" 2>/dev/null)

if [ -z "$FILES_TO_FIX" ]; then
    echo "No files found with NO_AUTO_CREATE_USER"
    echo "Searching more broadly..."
    FILES_TO_FIX=$(sudo find /etc/mysql -type f \( -name "*.cnf" -o -name "*.conf" \) 2>/dev/null | xargs sudo grep -l "sql_mode" 2>/dev/null)
fi

if [ -z "$FILES_TO_FIX" ]; then
    echo "✗ No config files found to fix"
    exit 1
fi

echo "Found files to fix:"
echo "$FILES_TO_FIX"
echo ""

for file in $FILES_TO_FIX; do
    echo "Processing: $file"
    
    # Backup
    sudo cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  ✓ Backup created"
    
    # Remove NO_AUTO_CREATE_USER
    sudo sed -i.bak 's/NO_AUTO_CREATE_USER,//g' "$file"
    sudo sed -i.bak 's/,NO_AUTO_CREATE_USER//g' "$file"
    sudo sed -i.bak 's/NO_AUTO_CREATE_USER//g' "$file"
    
    # Clean up double commas and empty quotes
    sudo sed -i.bak 's/,,/,/g' "$file"
    sudo sed -i.bak 's/^,//g' "$file"
    sudo sed -i.bak 's/,$//g' "$file"
    sudo sed -i.bak 's/""//g' "$file"
    sudo sed -i.bak 's/=","/="/g' "$file"
    
    # Show what changed
    echo "  Updated sql_mode:"
    sudo grep -i "sql_mode\|sql-mode" "$file" 2>/dev/null | head -3
    echo ""
done

echo "=========================================="
echo "Verification"
echo "=========================================="
echo ""

# Verify NO_AUTO_CREATE_USER is gone
REMAINING=$(sudo find /etc/mysql -type f \( -name "*.cnf" -o -name "*.conf" \) 2>/dev/null | xargs sudo grep -l "NO_AUTO_CREATE_USER" 2>/dev/null)

if [ -z "$REMAINING" ]; then
    echo "✓ NO_AUTO_CREATE_USER removed from all config files"
else
    echo "✗ Still found in:"
    echo "$REMAINING"
fi
echo ""

# Try to start MySQL
echo "Attempting to start MySQL..."
sudo systemctl start mysql 2>&1
sleep 2

if sudo systemctl is-active --quiet mysql; then
    echo "✓ MySQL started successfully!"
    sudo systemctl status mysql --no-pager | head -10
else
    echo "✗ MySQL still failed to start"
    echo ""
    echo "Check error:"
    sudo tail -10 /var/log/mysql/error.log 2>/dev/null || sudo journalctl -u mysql -n 10 --no-pager
fi

