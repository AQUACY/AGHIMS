# Production Deployment - Analyzer Integration

## Overview
The analyzer integration is ready for production. The server will automatically receive and process ASTM data from the Sysmex XN-330 analyzer.

## Production Server Configuration

### 1. Environment Variables (.env)

```env
# Analyzer Integration Settings
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0          # Listen on all interfaces
ANALYZER_PORT=5150
ANALYZER_EQUIPMENT_IP=10.10.16.34
ANALYZER_TIMEOUT=30
```

### 2. Firewall Configuration

On the production server, ensure port 5150 is open:

```bash
# Linux (if using iptables)
sudo iptables -A INPUT -p tcp --dport 5150 -j ACCEPT

# Or using firewall-cmd (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=5150/tcp
sudo firewall-cmd --reload

# Windows
netsh advfirewall firewall add rule name="HMS Analyzer Server Port 5150" dir=in action=allow protocol=TCP localport=5150
```

### 3. Analyzer Configuration

On the Sysmex XN-330 analyzer:
- **Host IP Address**: `10.10.16.50` (production server IP)
- **Port**: `5150`
- **Protocol**: TCP/IP

## Data Format

The analyzer sends ASTM E1394-97 format messages:

### Message Structure:
- **Header (H)**: Equipment information
- **Patient (P)**: Patient demographics
- **Order (O)**: Sample information (contains sample ID like `866`)
- **Result (R)**: Test results with codes like `^^^^WBC^1`, `^^^^RBC^1`, etc.
- **Comment (C)**: Additional comments
- **Terminator (L)**: End of message

### Sample ID Extraction:
- Sample ID is extracted from the Order record
- Format: `^^                   866^M|` → extracts `866`
- The system will match this to the generated sample ID in HMS (e.g., `251100001`)

### Test Code Mapping:
- Analyzer sends: `^^^^WBC^1`, `^^^^RBC^1`, `^^^^HGB^1`, etc.
- System maps to template fields: `WBC`, `RBC`, `HGB`, etc.

## Testing on Production

### 1. Verify Server is Running

```bash
# Check if port is listening
netstat -an | grep :5150

# Should show:
# tcp    0.0.0.0:5150    0.0.0.0:*    LISTEN
```

### 2. Monitor Server Logs

Watch for connection messages:
```
🔌 NEW CONNECTION from 10.10.16.34:xxxxx
📥 First data from (10.10.16.34, xxxxx): XXX bytes
💾 Receiving analyzer data...
```

### 3. Check Captured Data

```bash
# View latest captured data
python view_analyzer_data.py latest

# Analyze data structure
python analyze_captured_data.py
```

### 4. Verify Data Processing

1. Generate sample ID in HMS (e.g., `251100001`)
2. Process sample on analyzer with that ID (or let analyzer use its own ID like `866`)
3. Check if lab result is updated automatically
4. Verify values are mapped correctly to template fields

## Troubleshooting

### Issue: No connection from analyzer
- Check firewall allows port 5150
- Verify analyzer IP configuration
- Check network connectivity: `ping 10.10.16.50` from analyzer network
- Verify server is listening: `netstat -an | grep :5150`

### Issue: Connection but no data saved
- Check server logs for parsing errors
- Verify sample ID matches between HMS and analyzer
- Check captured data files for raw messages
- Verify template mapping is correct

### Issue: Data received but not mapped
- Check test codes in captured data
- Verify mapping in `analyzer_mapper.py`
- Check if sample ID format matches expected format

## Sample Data Format Example

From the analyzer, you'll see messages like:
```
1H|\^&|||    XN-330^00-27^12722^^^^CX851950||||||||E1394-97
2P|1|||AAC6844|^OMU^MAHAMADU||19720101|F|||||^||||||||||||^^^
4O|1||^^                   866^M|^^^^WBC\^^^^RBC\...
6R|1|^^^^WBC^1|4.41|10*3/uL||L||F||||20251122111119
7R|2|^^^^RBC^1|3.59|10*6/uL||L||F||||20251122111119
...
2L|1|N
```

The system will:
1. Extract sample ID `866` from Order record
2. Find matching investigation in HMS
3. Map test codes (`^^^^WBC^1` → `WBC`)
4. Extract values and units
5. Update lab result automatically

## Monitoring

### Log Files
- Server logs show connection and processing messages
- Captured data saved to: `analyzer_raw_data/`

### API Endpoints
- `/api/analyzer/status` - Check server status
- `/api/analyzer/test-parse` - Test ASTM parsing
- `/api/analyzer/test-map` - Test result mapping

## Next Steps After Deployment

1. **Test with real sample**: Process a sample and verify data appears in HMS
2. **Verify mapping**: Check that all test codes map correctly
3. **Monitor for errors**: Watch server logs for any issues
4. **Adjust if needed**: Update mappings based on actual data received

