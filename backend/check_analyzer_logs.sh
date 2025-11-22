#!/bin/bash
# Script to check analyzer logs from systemd service

echo "======================================================================"
echo "HMS Backend Service Logs - Analyzer Activity"
echo "======================================================================"
echo ""

# Check service status
echo "1. Service Status:"
echo "----------------------------------------------------------------------"
systemctl status hms-backend --no-pager -l | head -20
echo ""

# Show recent logs (last 50 lines)
echo "2. Recent Logs (last 50 lines):"
echo "----------------------------------------------------------------------"
journalctl -u hms-backend -n 50 --no-pager | grep -E "(analyzer|Analyzer|CONNECTION|NEW CONNECTION|Receiving|Saving|sample|Sample)" -i
echo ""

# Show all recent logs
echo "3. All Recent Logs (last 100 lines):"
echo "----------------------------------------------------------------------"
journalctl -u hms-backend -n 100 --no-pager
echo ""

# Follow logs in real-time
echo "4. To follow logs in real-time, run:"
echo "   sudo journalctl -u hms-backend -f"
echo ""

# Check for analyzer-specific messages
echo "5. Analyzer Connection Messages:"
echo "----------------------------------------------------------------------"
journalctl -u hms-backend --no-pager | grep -E "(NEW CONNECTION|First data|Receiving analyzer|Sent ACK)" | tail -20
echo ""

# Check captured data files
echo "6. Captured Data Files:"
echo "----------------------------------------------------------------------"
if [ -d "analyzer_raw_data" ]; then
    echo "Latest files:"
    ls -lth analyzer_raw_data/ | head -10
    echo ""
    echo "Total files: $(ls -1 analyzer_raw_data/*.txt 2>/dev/null | wc -l)"
else
    echo "No analyzer_raw_data directory found"
fi
echo ""

echo "======================================================================"
echo "Quick Commands:"
echo "======================================================================"
echo "Follow logs:        sudo journalctl -u hms-backend -f"
echo "Last 100 lines:     sudo journalctl -u hms-backend -n 100"
echo "Since today:        sudo journalctl -u hms-backend --since today"
echo "Search analyzer:    sudo journalctl -u hms-backend | grep -i analyzer"
echo "View data files:    python view_analyzer_data.py latest"
echo "======================================================================"

