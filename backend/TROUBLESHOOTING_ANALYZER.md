# Analyzer Server Troubleshooting

## Issue: No Data Received from Analyzer

### Step 1: Verify Server is Running

Check if the analyzer server is actually running:
```bash
python check_server_status.py
```

**Expected output:**
```
Server Running: True
Thread Alive: True
```

**If it shows `False`:**
- Your FastAPI server needs to be restarted
- The analyzer server starts automatically when FastAPI starts

### Step 2: Restart FastAPI Server

1. **Stop the current server** (Ctrl+C in the terminal running uvicorn)

2. **Start it again:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Look for these messages in the logs:**
   ```
   ======================================================================
   Starting Analyzer Server...
     Host: 0.0.0.0
     Port: 5150
     Equipment IP: 10.10.16.34
   ======================================================================
   ✓ Analyzer server thread started successfully
   Attempting to bind analyzer server to 0.0.0.0:5150
   ✓ Analyzer server is now listening on 0.0.0.0:5150
   ```

### Step 3: Verify Port is Listening

```bash
netstat -an | findstr :5150
```

**Should show:**
```
TCP    0.0.0.0:5150           0.0.0.0:0              LISTENING
```

### Step 4: Test Connection

```bash
python test_analyzer_listening.py
```

**Should show:**
```
✓ Port 5150 is IN USE (server is likely running)
✓ Successfully connected to 127.0.0.1:5150
```

### Step 5: Check Windows Firewall

The firewall must allow incoming connections on port 5150:

```bash
# Check if rule exists
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"

# If it doesn't exist, create it:
netsh advfirewall firewall add rule name="HMS Analyzer Server Port 5150" dir=in action=allow protocol=TCP localport=5150
```

### Step 6: Verify Analyzer Configuration

On your Sysmex XN-330 analyzer:
- **Host IP Address**: `10.10.17.223` (your PC IP)
- **Port**: `5150`
- **Protocol**: TCP/IP (NOT HTTP)

### Step 7: Monitor Server Logs

When the analyzer sends data, you should see in your FastAPI server terminal:
```
🔌 NEW CONNECTION from 10.10.16.34:xxxxx
   Connection accepted, starting handler thread...
📥 First data from (10.10.16.34, xxxxx): XXX bytes
💾 Receiving analyzer data from (10.10.16.34, xxxxx)
   Saving to: analyzer_raw_data/raw_data_YYYYMMDD_HHMMSS.txt
```

### Step 8: Check for Captured Data

After processing a sample on the analyzer:
```bash
# View latest data
python view_analyzer_data.py latest

# Or list all files
python view_analyzer_data.py all
```

## Common Issues

### Issue: "Port already in use"
**Solution:**
- Find what's using the port: `netstat -ano | findstr :5150`
- Kill the process or use a different port

### Issue: "Server thread died immediately"
**Solution:**
- Check server logs for errors
- Verify `.env` file has correct settings
- Check if port binding failed

### Issue: "No connection from analyzer"
**Solution:**
- Verify analyzer IP is correct: `10.10.17.223`
- Check network connectivity: `ping 10.10.16.34` (from your PC)
- Verify Windows Firewall allows port 5150
- Check analyzer settings match exactly

### Issue: "Connection but no data"
**Solution:**
- Check if analyzer is configured for automatic transmission
- Verify sample ID matches between HMS and analyzer
- Check server logs for connection messages
- Look for HTTP requests being filtered (should see warning)

## Quick Diagnostic Commands

```bash
# Check server status
python check_server_status.py

# Test if port is listening
python test_analyzer_listening.py

# View captured data
python view_analyzer_data.py latest

# Analyze captured data
python analyze_captured_data.py

# Check network connectivity
ping 10.10.16.34

# Check firewall
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"
```

