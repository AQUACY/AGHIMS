# How to Check Analyzer Logs

## Quick Commands

### 1. View Recent Logs (Last 50 lines)
```bash
sudo journalctl -u hms-backend -n 50
```

### 2. Follow Logs in Real-Time
```bash
sudo journalctl -u hms-backend -f
```
Press `Ctrl+C` to stop following.

### 3. View Logs Since Today
```bash
sudo journalctl -u hms-backend --since today
```

### 4. Search for Analyzer-Related Messages
```bash
# Search for analyzer connections
sudo journalctl -u hms-backend | grep -i "analyzer\|connection\|sample"

# Search for specific terms
sudo journalctl -u hms-backend | grep -i "NEW CONNECTION"
sudo journalctl -u hms-backend | grep -i "Receiving analyzer"
sudo journalctl -u hms-backend | grep -i "Sent ACK"
```

### 5. View Last 100 Lines with Timestamps
```bash
sudo journalctl -u hms-backend -n 100 --no-pager
```

### 6. View Logs Between Times
```bash
# Since 1 hour ago
sudo journalctl -u hms-backend --since "1 hour ago"

# Between two times
sudo journalctl -u hms-backend --since "2025-11-22 10:00:00" --until "2025-11-22 11:00:00"
```

## What to Look For

### Successful Connection
Look for these messages:
```
🔌 NEW CONNECTION #1 from 10.10.16.34:xxxxx
📥 First data from (10.10.16.34, xxxxx): XXX bytes
💾 Receiving analyzer data from (10.10.16.34, xxxxx)
   Saving to: analyzer_raw_data/raw_data_YYYYMMDD_HHMMSS.txt
Sent ACK to analyzer at (10.10.16.34, xxxxx)
```

### Data Processing
```
Parsed X ASTM records from (10.10.16.34, xxxxx)
Processing analyzer results for sample ID: 866
Successfully updated lab result X with analyzer data for sample 866
```

### Errors
```
ERROR: Failed to start analyzer server
ERROR: Error processing analyzer data
WARNING: No investigation found for sample ID
```

## Using the Helper Scripts

### Python Script (Works on any system)
```bash
python check_analyzer_logs.py
```

### Bash Script (Linux only)
```bash
bash check_analyzer_logs.sh
# Or
./check_analyzer_logs.sh
```

## Check Captured Data Files

### View Latest Captured Data
```bash
python view_analyzer_data.py latest
```

### List All Data Files
```bash
python view_analyzer_data.py all
```

### Analyze Data Structure
```bash
python analyze_captured_data.py
```

## Service Management

### Restart Service
```bash
sudo systemctl restart hms-backend
```

### Check Service Status
```bash
sudo systemctl status hms-backend
```

### Stop Service
```bash
sudo systemctl stop hms-backend
```

### Start Service
```bash
sudo systemctl start hms-backend
```

## Troubleshooting

### No Logs Appearing
1. Check if service is running: `sudo systemctl status hms-backend`
2. Check if analyzer is enabled: Look for "Analyzer enabled: True" in logs
3. Check if port is listening: `netstat -an | grep :5150`

### Logs Show Errors
1. Check the full error message in logs
2. Look for stack traces
3. Check if analyzer server started: Look for "Analyzer server is now listening"

### No Data Files Created
1. Check if analyzer connected: Look for "NEW CONNECTION" messages
2. Check if data was received: Look for "First data" messages
3. Verify directory exists: `ls -la analyzer_raw_data/`

