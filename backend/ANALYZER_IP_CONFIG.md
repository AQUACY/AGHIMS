# Analyzer IP Configuration Guide

## Network Setup

### Your Network Configuration:
- **PC IP (Development)**: `10.10.17.223`
  - Subnet: `10.10.16.0/20` (255.255.240.0)
  - Network: `10.10.16.0` - `10.10.31.255`
  
- **PC IP (Alternative)**: `192.168.0.26`
  - Subnet: `192.168.0.0/24` (255.255.255.0)
  - Different network (not accessible by analyzer)

- **Analyzer IP**: `10.10.16.34`
  - Same network as `10.10.17.223` ✓

- **Production Server IP**: `10.10.16.50`
  - Same network as analyzer ✓

## Development Configuration

### On Your PC (.env file):
```env
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0          # Listen on all interfaces
ANALYZER_PORT=5150
ANALYZER_EQUIPMENT_IP=10.10.16.34
```

### On the Sysmex Analyzer:
- **Host IP Address**: `10.10.17.223`
- **Port**: `5150`
- **Protocol**: TCP/IP

### Testing Connection:
```bash
# From your PC, test if port is listening:
netstat -an | findstr :5150

# Should show:
# TCP    0.0.0.0:5150           0.0.0.0:0              LISTENING
```

## Production Configuration

### On Production Server (.env file):
```env
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0          # Listen on all interfaces
ANALYZER_PORT=5150
ANALYZER_EQUIPMENT_IP=10.10.16.34
```

### On the Sysmex Analyzer (Production):
- **Host IP Address**: `10.10.16.50`
- **Port**: `5150`
- **Protocol**: TCP/IP

## Windows Firewall Configuration

### For Development (Your PC):

1. **Open Windows Firewall**:
   - Press `Win + R`, type `wf.msc`, press Enter

2. **Create Inbound Rule**:
   - Click "Inbound Rules" → "New Rule"
   - Rule Type: Port
   - Protocol: TCP
   - Port: `5150`
   - Action: Allow the connection
   - Profile: All (Domain, Private, Public)
   - Name: "HMS Analyzer Server Port 5150"

3. **Verify Rule**:
   ```bash
   netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"
   ```

### Alternative: Allow via Command Line:
```bash
netsh advfirewall firewall add rule name="HMS Analyzer Server Port 5150" dir=in action=allow protocol=TCP localport=5150
```

## Network Connectivity Test

### Test from Analyzer Network:
```bash
# Test if your PC is reachable from analyzer network
ping 10.10.17.223

# Test if port 5150 is accessible (if you have telnet/nc)
telnet 10.10.17.223 5150
# Or
nc -zv 10.10.17.223 5150
```

### Test from Your PC:
```bash
# Test if analyzer is reachable
ping 10.10.16.34

# Check if analyzer server is listening
netstat -an | findstr :5150
```

## Troubleshooting

### Connection Refused:
1. **Check if server is running**:
   - Look for "Analyzer server is now listening" in server logs
   
2. **Check Windows Firewall**:
   - Ensure port 5150 is allowed in inbound rules
   
3. **Check IP address**:
   - Verify analyzer is configured to connect to `10.10.17.223` (not `10.10.16.50`)
   
4. **Check network connectivity**:
   - Ensure PC and analyzer are on the same network (10.10.16.0/20)
   - Test with `ping 10.10.16.34` from your PC

### No Data Received:
1. **Check server logs** for connection messages
2. **Check analyzer settings** - verify IP and port are correct
3. **Check captured files** in `analyzer_raw_data/` directory
4. **Test with mock client** first: `python test_analyzer_client.py 251100001`

## Quick Reference

| Environment | Server IP | Analyzer Connects To | Port |
|------------|-----------|---------------------|------|
| Development | 10.10.17.223 | 10.10.17.223 | 5150 |
| Production | 10.10.16.50 | 10.10.16.50 | 5150 |

**Important**: When switching between development and production, update the analyzer's Host IP Address setting on the Sysmex device.

