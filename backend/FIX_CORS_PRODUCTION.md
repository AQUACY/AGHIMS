# Fix CORS Errors in Production

## Problem
Getting "CORS request did not succeed" errors with status (null) in production.

## Root Cause
This error typically means:
1. **Server is not running** - The backend server crashed or didn't start
2. **Network issue** - Request never reached the server
3. **Firewall blocking** - Port 8000 is blocked

## Solution Steps

### 1. Check if Server is Running

On the production server, check:
```bash
# Check if uvicorn process is running
ps aux | grep uvicorn

# Check if port 8000 is listening
netstat -an | grep :8000
# Or
ss -tlnp | grep :8000
```

### 2. Check Server Logs

```bash
# If using systemd service
sudo journalctl -u backend -f
sudo journalctl -u backend -n 100 --no-pager

# If running manually, check the terminal output
# Look for errors during startup
```

### 3. Common Startup Errors

**Error: Analyzer server startup failed**
- The analyzer server startup is now non-blocking
- Server should continue even if analyzer server fails
- Check logs for analyzer server errors

**Error: Import errors**
- Check if all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

**Error: Port already in use**
- Check what's using port 8000: `lsof -i :8000` or `netstat -an | grep :8000`
- Kill the process or use a different port

### 4. Restart Server

```bash
# If using systemd
sudo systemctl restart backend

# If running manually
# Stop current server (Ctrl+C)
# Start again:
cd /path/to/backend
source venv/bin/activate  # If using virtual environment
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify Server is Accessible

From the production server:
```bash
# Test health endpoint
curl http://localhost:8000/health
curl http://127.0.0.1:8000/health

# Should return: {"status": "healthy"}
```

From another machine:
```bash
# Test from network
curl http://10.10.16.50:8000/health
```

### 6. Check Firewall

```bash
# Linux (ufw)
sudo ufw status
sudo ufw allow 8000/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Windows
netsh advfirewall firewall show rule name="Backend Port 8000"
netsh advfirewall firewall add rule name="Backend Port 8000" dir=in action=allow protocol=TCP localport=8000
```

### 7. Test CORS Configuration

The CORS configuration should include:
```python
cors_origins = [
    "http://10.10.16.50:9000",  # Frontend dev server
    "http://10.10.16.50",        # Production (if using Apache)
    # ... other origins
]
```

### 8. Quick Fix Script

Create a test script on production server:
```bash
#!/bin/bash
# test_backend.sh

echo "Testing backend server..."

# Check if running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Server is running"
else
    echo "✗ Server is NOT running"
    echo "Starting server..."
    # Add your server start command here
fi
```

## If Server Keeps Crashing

1. **Disable analyzer server temporarily**:
   ```env
   ANALYZER_ENABLED=false
   ```
   Restart server and see if it starts without analyzer server.

2. **Check for syntax errors**:
   ```bash
   python -m py_compile app/main.py
   python -c "import app.main"
   ```

3. **Check for import errors**:
   ```bash
   python -c "from app.services.analyzer_server import start_analyzer_server"
   ```

4. **Run with verbose logging**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
   ```

## Expected Startup Output

When server starts successfully, you should see:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
======================================================================
Application Startup - Initializing Analyzer Server...
======================================================================
Analyzer enabled: True
Starting analyzer server...
======================================================================
Starting Analyzer Server...
  Host: 0.0.0.0
  Port: 5150
======================================================================
✓ Analyzer server thread started successfully
======================================================================
Application startup complete.
======================================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

If you see errors before "Application startup complete", those are causing the crash.

