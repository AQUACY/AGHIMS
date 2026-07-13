#!/bin/bash
# Quick script to check if the backend server is running

echo "=========================================="
echo "Checking Backend Server Status"
echo "=========================================="
echo ""

# Check if server is listening on port 8000
echo "1. Checking if port 8000 is listening..."
if netstat -tuln 2>/dev/null | grep -q ":8000 " || ss -tuln 2>/dev/null | grep -q ":8000 "; then
    echo "   ✓ Port 8000 is listening"
else
    echo "   ✗ Port 8000 is NOT listening - server is not running!"
fi
echo ""

# Check if uvicorn process is running
echo "2. Checking for uvicorn process..."
if pgrep -f "uvicorn" > /dev/null; then
    echo "   ✓ uvicorn process found"
    pgrep -f "uvicorn" | head -1 | xargs ps -p
else
    echo "   ✗ No uvicorn process found"
fi
echo ""

# Check systemd service status (if applicable)
echo "3. Checking systemd service status..."
if systemctl is-active --quiet hms-api 2>/dev/null; then
    echo "   ✓ hms-api service is active"
    systemctl status hms-api --no-pager -l | head -10
else
    echo "   ⚠ hms-api service not found or not active"
fi
echo ""

# Test API endpoint
echo "4. Testing API endpoint..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null | grep -q "200\|404"; then
    echo "   ✓ API is responding"
else
    echo "   ✗ API is NOT responding"
    echo "   Trying to connect..."
    curl -v http://localhost:8000/api/health 2>&1 | head -10
fi
echo ""

# Check recent logs
echo "5. Checking recent application logs..."
if [ -f "/var/log/hms/app.log" ]; then
    echo "   Recent errors:"
    tail -20 /var/log/hms/app.log | grep -i error || echo "   No recent errors found"
elif [ -f "app.log" ]; then
    echo "   Recent errors:"
    tail -20 app.log | grep -i error || echo "   No recent errors found"
else
    echo "   ⚠ Log file not found"
fi
echo ""

# Check Python imports
echo "6. Testing Python imports..."
python3 -c "import apscheduler; print('   ✓ APScheduler imported successfully')" 2>&1 || echo "   ✗ APScheduler import failed!"
python3 -c "from app.main import app; print('   ✓ FastAPI app imported successfully')" 2>&1 || echo "   ✗ FastAPI app import failed!"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "If server is not running, check:"
echo "1. Server logs for startup errors"
echo "2. Missing dependencies (run: pip install -r requirements.txt)"
echo "3. Database connection issues"
echo "4. Port 8000 already in use"
echo ""

