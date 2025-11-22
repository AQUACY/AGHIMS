# Direct Cable Connection Setup Guide

## Overview
Connecting the analyzer directly to your PC via Ethernet cable eliminates network routing issues.

## Step 1: Physical Connection

1. **Use an Ethernet cable** to connect:
   - Analyzer Ethernet port → PC Ethernet port
   - Use a standard Ethernet cable (modern ports auto-detect, no crossover needed)

2. **Disconnect from network** (optional but recommended for testing):
   - You can keep Wi-Fi connected for internet
   - The direct Ethernet connection will be separate

## Step 2: Configure Static IP on PC

### Option A: Using Windows GUI

1. **Open Network Settings**:
   - Press `Win + X` → `Network Connections`
   - Or: Settings → Network & Internet → Ethernet

2. **Configure Ethernet Adapter**:
   - Right-click on "Ethernet" adapter
   - Select "Properties"
   - Double-click "Internet Protocol Version 4 (TCP/IPv4)"

3. **Set Static IP**:
   - Select "Use the following IP address"
   - IP address: `192.168.1.1`
   - Subnet mask: `255.255.255.0`
   - Default gateway: (leave empty)
   - DNS: (leave empty or use `8.8.8.8`)
   - Click OK

### Option B: Using Command Line (Run as Administrator)

```bash
# Configure Ethernet adapter with static IP
netsh interface ip set address "Ethernet" static 192.168.1.1 255.255.255.0

# Verify configuration
ipconfig
```

## Step 3: Configure Analyzer

On the Sysmex XN-330 analyzer:

1. **Set Static IP**:
   - IP Address: `192.168.1.2`
   - Subnet Mask: `255.255.255.0`
   - Gateway: (leave empty or `192.168.1.1`)
   - DNS: (leave empty)

2. **Configure Host Connection**:
   - Host IP Address: `192.168.1.1` (your PC's direct connection IP)
   - Port: `5150`
   - Protocol: TCP/IP

## Step 4: Update HMS Server Configuration

The server is already configured to listen on `0.0.0.0:5150`, which means it will accept connections on ALL network interfaces, including the direct Ethernet connection. **No changes needed!**

However, if you want to be explicit, you can verify in `.env`:
```env
ANALYZER_HOST=0.0.0.0  # This is correct - listens on all interfaces
ANALYZER_PORT=5150
```

## Step 5: Test Connection

### From PC:
```bash
# Ping the analyzer
ping 192.168.1.2

# Test port connection
python test_raw_connection.py
# (Update SERVER_HOSTS in test_raw_connection.py to include 192.168.1.1)
```

### From Analyzer:
- Try to connect/send data
- Check server terminal for connection messages

## Step 6: Verify Connection

1. **Check IP configuration**:
   ```bash
   ipconfig
   ```
   Should show Ethernet adapter with `192.168.1.1`

2. **Check server is listening**:
   ```bash
   netstat -an | findstr :5150
   ```
   Should show: `TCP    0.0.0.0:5150           0.0.0.0:0              LISTENING`

3. **Test connectivity**:
   ```bash
   ping 192.168.1.2
   ```

## Troubleshooting

### Issue: Can't ping analyzer
- **Check**: Cable is properly connected
- **Check**: Both devices have static IPs configured
- **Check**: Subnet masks match (255.255.255.0)
- **Check**: No firewall blocking ICMP (ping)

### Issue: Connection still refused
- **Check**: Windows Firewall allows port 5150
- **Check**: Server is running and listening
- **Check**: Analyzer IP is exactly `192.168.1.2`
- **Check**: Analyzer Host IP is exactly `192.168.1.1`

### Issue: IP conflict
- If `192.168.1.1` is already in use, use:
  - PC: `192.168.1.10`
  - Analyzer: `192.168.1.20`
- Or any other IPs in the `192.168.1.0/24` range

## Quick Setup Script

Create a batch file to configure the Ethernet adapter (Run as Administrator):

```batch
@echo off
echo Configuring Ethernet adapter for direct connection...
netsh interface ip set address "Ethernet" static 192.168.1.1 255.255.255.0
echo.
echo Configuration complete!
echo PC IP: 192.168.1.1
echo Analyzer should be configured to: 192.168.1.2
echo.
ipconfig | findstr /i "ethernet"
pause
```

## Reverting to Network Connection

If you want to go back to network connection:

1. **Reset Ethernet adapter to DHCP**:
   ```bash
   netsh interface ip set address "Ethernet" dhcp
   ```

2. **Update analyzer configuration**:
   - Host IP: `10.10.17.223` (your PC's network IP)
   - Keep port: `5150`

## Notes

- **Direct connection**: PC (`192.168.1.1`) ↔ Analyzer (`192.168.1.2`)
- **Network connection**: PC (`10.10.17.223`) ↔ Analyzer (`10.10.16.34`)
- You can have both configured, but only one active at a time
- The server listens on `0.0.0.0:5150` so it works with either connection method

