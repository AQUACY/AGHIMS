# Quick Start: Analyzer Server

## Important Notes

1. **Port 5150 is NOT HTTP** - It's a TCP socket server. Browsers won't work!
   - ❌ Don't try: `http://10.10.17.223:5150` in browser
   - ✅ Use: TCP connection from analyzer (configured on Sysmex device)

2. **Server starts automatically** when FastAPI starts, but you need to see the startup messages.

## Step-by-Step Startup

### 1. Start FastAPI Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Look for These Messages

When the server starts, you should see:

```
======================================================================
Application Startup - Initializing Analyzer Server...
======================================================================
Analyzer enabled: True
Starting analyzer server...
======================================================================
Starting Analyzer Server...
  Host: 0.0.0.0
  Port: 5150
  Equipment IP: 10.10.16.34
======================================================================
✓ Analyzer server thread started successfully
Attempting to bind analyzer server to 0.0.0.0:5150
✓ Analyzer server is now listening on 0.0.0.0:5150
  Equipment IP: 10.10.16.34
  Ready to receive data from analyzer
  Configure analyzer to connect to: 10.10.17.223:5150
======================================================================
Application startup complete.
```

### 3. If You Don't See These Messages

**Check 1: Verify .env file**
```bash
grep ANALYZER .env
```

Should show:
```
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0
ANALYZER_PORT=5150
```

**Check 2: Check server status via API**
```bash
# After server starts, check status (requires authentication)
curl http://localhost:8000/api/analyzer/status
```

Or use the Python script:
```bash
python check_server_status.py
```

**Check 3: Verify port is listening**
```bash
netstat -an | findstr :5150
```

Should show:
```
TCP    0.0.0.0:5150           0.0.0.0:0              LISTENING
```

### 4. Test Connection

```bash
python test_analyzer_listening.py
```

### 5. Configure Analyzer

On Sysmex XN-330:
- **Host IP**: `10.10.17.223`
- **Port**: `5150`
- **Protocol**: TCP/IP

### 6. Process a Sample

1. Generate sample ID in HMS (e.g., `251100001`)
2. Enter sample ID on analyzer
3. Process sample
4. Watch server terminal for connection messages:
   ```
   🔌 NEW CONNECTION from 10.10.16.34:xxxxx
   📥 First data from (10.10.16.34, xxxxx): XXX bytes
   💾 Receiving analyzer data...
   ```

### 7. View Captured Data

```bash
python view_analyzer_data.py latest
```

## Troubleshooting

### No Startup Messages

If you don't see analyzer server startup messages:
1. Check if `.env` file exists and has `ANALYZER_ENABLED=true`
2. Restart the server completely (stop and start again)
3. Check for errors in the startup logs

### Port Already in Use

```bash
# Find what's using the port
netstat -ano | findstr :5150

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Browser Shows "Not Found"

**This is normal!** Port 5150 is a TCP socket, not HTTP. Browsers use HTTP, so they won't work. The analyzer uses raw TCP/IP connections.

### No Data Received

1. Verify analyzer is configured correctly (IP: `10.10.17.223`, Port: `5150`)
2. Check Windows Firewall allows port 5150
3. Verify network connectivity: `ping 10.10.16.34` (from your PC)
4. Check server logs for connection attempts

## Quick Commands Reference

```bash
# Check server status
python check_server_status.py

# Test if port is listening
python test_analyzer_listening.py

# View captured data
python view_analyzer_data.py latest

# Analyze captured data
python analyze_captured_data.py

# Check configuration
python -c "from app.core.config import settings; print(f'Enabled: {settings.ANALYZER_ENABLED}, Host: {settings.ANALYZER_HOST}, Port: {settings.ANALYZER_PORT}')"
```

