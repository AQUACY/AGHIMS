# Fix CORS Error After Code Update

## Problem
After pushing new code, getting: "CORS request did not succeed" with status code (null)

## Root Cause
This usually means **the backend server crashed on startup** and isn't running.

## Quick Fix Steps

### 1. Check if Server is Running

```bash
# SSH into production server
ssh user@10.10.16.50

# Check if server is running
ps aux | grep uvicorn
# OR
systemctl status hms-api
```

### 2. Check Server Logs for Errors

```bash
# If using systemd
sudo journalctl -u hms-api -n 100 --no-pager
# OR
sudo journalctl -u hms-api -f  # Follow logs in real-time

# If running manually, check the terminal where you started it
```

### 3. Most Common Issue: Missing APScheduler

After the update, APScheduler is required. If it's not installed, the server will crash.

**Fix:**
```bash
cd /path/to/backend
source venv/bin/activate  # If using venv
pip install "apscheduler>=3.10.4"
```

### 4. Restart the Server

```bash
# If using systemd
sudo systemctl restart hms-api

# If running manually
# Stop the current process (Ctrl+C) and restart:
cd /path/to/backend
source venv/bin/activate  # If using venv
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify Server is Running

```bash
# Check if port 8000 is listening
netstat -tuln | grep :8000
# OR
ss -tlnp | grep :8000

# Test API
curl http://localhost:8000/api/health
```

## Common Startup Errors

### Error: "No module named 'apscheduler'"

**Solution:**
```bash
pip install "apscheduler>=3.10.4"
```

### Error: Import errors in backup_scheduler

The code now handles this gracefully - server should continue even if scheduler fails.

### Error: Port 8000 already in use

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :8000
# OR
sudo netstat -tlnp | grep :8000

# Kill the process if needed
sudo kill -9 <PID>
```

## Quick Diagnostic Script

Run this on your production server:

```bash
cd /path/to/backend
./CHECK_SERVER_STATUS.sh
```

This will check:
- If server is running
- If port 8000 is listening
- Recent error logs
- Python imports

## If Server Still Won't Start

1. **Check Python version:**
   ```bash
   python3 --version  # Should be 3.7+
   ```

2. **Reinstall dependencies:**
   ```bash
   cd /path/to/backend
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Test imports manually:**
   ```bash
   python3 -c "from app.main import app; print('OK')"
   ```

4. **Check for syntax errors:**
   ```bash
   python3 -m py_compile app/main.py
   python3 -m py_compile app/services/backup_scheduler.py
   ```

## After Fixing

Once the server is running, the CORS error should disappear. The server needs to be:
- Running and listening on port 8000
- Accessible from the frontend
- Not crashing on startup

