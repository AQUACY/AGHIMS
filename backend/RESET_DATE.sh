#!/bin/bash
# Reset VM system date to current date
# Usage: sudo ./RESET_DATE.sh

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

echo "=========================================="
echo "Resetting System Date to Current Date"
echo "=========================================="
echo ""

# Get current (old) date
OLD_DATE=$(date +%Y-%m-%d)
OLD_TIME=$(date +%H:%M:%S)

echo "Current (old) date: $OLD_DATE $OLD_TIME"
echo ""

# Check if date backup exists
DATE_BACKUP_FILE="/tmp/hms_date_backup.txt"
if [ -f "$DATE_BACKUP_FILE" ]; then
    ORIGINAL_DATE=$(cat "$DATE_BACKUP_FILE")
    echo "Original date (before change): $ORIGINAL_DATE"
    echo ""
fi

# Confirm action
read -p "Reset system date to current date? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

# Enable NTP service for automatic date sync
echo ""
echo "Enabling NTP service..."
systemctl enable systemd-timesyncd 2>/dev/null || systemctl enable ntpd 2>/dev/null || systemctl enable chronyd 2>/dev/null || true
systemctl start systemd-timesyncd 2>/dev/null || systemctl start ntpd 2>/dev/null || systemctl start chronyd 2>/dev/null || true

# Sync date with NTP
echo "Syncing date with NTP servers..."
if command -v ntpdate >/dev/null 2>&1; then
    ntpdate -s pool.ntp.org 2>/dev/null || true
elif command -v chronyd >/dev/null 2>&1; then
    chronyd -q 2>/dev/null || true
elif command -v timedatectl >/dev/null 2>&1; then
    timedatectl set-ntp true 2>/dev/null || true
fi

# Wait a moment for sync
sleep 2

# Verify date was updated
NEW_DATE=$(date +%Y-%m-%d)
NEW_TIME=$(date +%H:%M:%S)

echo ""
echo -e "${GREEN}✓ Date reset complete${NC}"
echo "  Old date: $OLD_DATE $OLD_TIME"
echo "  New date: $NEW_DATE $NEW_TIME"
echo ""

# Clean up backup file
if [ -f "$DATE_BACKUP_FILE" ]; then
    rm "$DATE_BACKUP_FILE"
    echo "Cleaned up date backup file"
fi

echo ""
echo "=========================================="
echo "Date Reset Complete"
echo "=========================================="
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "1. NTP has been re-enabled for automatic date sync"
echo "2. Restart services to ensure they use the new date:"
echo "   sudo systemctl restart hms-backend"
echo "   sudo systemctl restart mysql"
echo ""
echo "Current system date: $(date)"
echo ""

