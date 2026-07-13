#!/bin/bash
# Set VM system date to an old date for working with historical data
# Usage: sudo ./SET_OLD_DATE.sh YYYY-MM-DD
# Example: sudo ./SET_OLD_DATE.sh 2024-01-01

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if date argument provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Date argument required${NC}"
    echo "Usage: sudo $0 YYYY-MM-DD"
    echo "Example: sudo $0 2024-01-01"
    exit 1
fi

OLD_DATE="$1"

# Validate date format
if ! date -d "$OLD_DATE" >/dev/null 2>&1; then
    echo -e "${RED}Error: Invalid date format. Use YYYY-MM-DD${NC}"
    echo "Example: 2024-01-01"
    exit 1
fi

# Get current date for reference
CURRENT_DATE=$(date +%Y-%m-%d)
CURRENT_TIME=$(date +%H:%M:%S)

echo "=========================================="
echo "Setting System Date to Old Date"
echo "=========================================="
echo ""
echo "Current date: $CURRENT_DATE $CURRENT_TIME"
echo "Target date:  $OLD_DATE"
echo ""

# Confirm action
read -p "Are you sure you want to set the system date to $OLD_DATE? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

# Save current date/time for restoration
DATE_BACKUP_FILE="/tmp/hms_date_backup.txt"
echo "$CURRENT_DATE $CURRENT_TIME" > "$DATE_BACKUP_FILE"
echo "Saved current date to $DATE_BACKUP_FILE"

# Stop NTP service to prevent automatic date sync
echo ""
echo "Stopping NTP service..."
systemctl stop systemd-timesyncd 2>/dev/null || systemctl stop ntpd 2>/dev/null || systemctl stop chronyd 2>/dev/null || true
systemctl disable systemd-timesyncd 2>/dev/null || systemctl disable ntpd 2>/dev/null || systemctl disable chronyd 2>/dev/null || true

# Set the date
echo "Setting system date to $OLD_DATE..."
date -s "$OLD_DATE 00:00:00" 2>/dev/null || timedatectl set-time "$OLD_DATE 00:00:00" 2>/dev/null || {
    echo -e "${RED}Error: Failed to set date. Try: timedatectl set-time '$OLD_DATE 00:00:00'${NC}"
    exit 1
}

# Verify date was set
NEW_DATE=$(date +%Y-%m-%d)
if [ "$NEW_DATE" = "$OLD_DATE" ]; then
    echo -e "${GREEN}✓ Date successfully set to $OLD_DATE${NC}"
else
    echo -e "${RED}✗ Warning: Date may not have been set correctly${NC}"
    echo "  Expected: $OLD_DATE"
    echo "  Actual: $NEW_DATE"
fi

echo ""
echo "=========================================="
echo "Date Change Complete"
echo "=========================================="
echo ""
echo -e "${YELLOW}IMPORTANT NOTES:${NC}"
echo "1. NTP has been disabled to prevent automatic date sync"
echo "2. SSL certificates may appear expired"
echo "3. Log timestamps will reflect the old date"
echo "4. Remember to reset the date when done: sudo reset-date.sh"
echo ""
echo "Current system date: $(date)"
echo ""
echo "To restart services with new date:"
echo "  sudo systemctl restart hms-backend"
echo "  sudo systemctl restart mysql"
echo ""

