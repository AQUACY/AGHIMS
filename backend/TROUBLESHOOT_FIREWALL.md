# Troubleshooting Analyzer Connection - Firewall Issues

## Problem: "Unable to connect to TCP/IP with the host computer"

This error from the analyzer means it cannot establish a TCP connection to your PC. The most common cause is **Windows Firewall blocking the connection**.

## Solution 1: Create Firewall Rule (Command Line)

### Option A: Using netsh (Run as Administrator)

```bash
# Create the firewall rule
netsh advfirewall firewall add rule name="HMS Analyzer Server Port 5150" dir=in action=allow protocol=TCP localport=5150

# Verify it was created
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"
```

### Option B: Using PowerShell (Run as Administrator)

```powershell
# Run PowerShell as Administrator, then:
New-NetFirewallRule -DisplayName "HMS Analyzer Server Port 5150" `
    -Name "HMS Analyzer Server Port 5150" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5150 `
    -Action Allow `
    -Enabled True
```

Or use the provided script:
```powershell
powershell -ExecutionPolicy Bypass -File fix_firewall.ps1
```

## Solution 2: Windows Firewall GUI

1. **Open Windows Defender Firewall**:
   - Press `Win + R`
   - Type: `wf.msc`
   - Press Enter

2. **Create Inbound Rule**:
   - Click "Inbound Rules" in the left panel
   - Click "New Rule..." in the right panel
   - Rule Type: Select "Port"
   - Click Next
   - Protocol: Select "TCP"
   - Specific local ports: Enter `5150`
   - Click Next
   - Action: Select "Allow the connection"
   - Click Next
   - Profile: Check all (Domain, Private, Public)
   - Click Next
   - Name: Enter "HMS Analyzer Server Port 5150"
   - Click Finish

## Solution 3: Temporarily Disable Firewall (Testing Only)

⚠️ **WARNING**: Only for testing! Re-enable after testing.

```bash
# Disable firewall (Administrator required)
netsh advfirewall set allprofiles state off

# Re-enable firewall
netsh advfirewall set allprofiles state on
```

## Verify Firewall Rule

After creating the rule, verify it exists:

```bash
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"
```

Should show:
```
Rule Name:                            HMS Analyzer Server Port 5150
Enabled:                             Yes
Direction:                           In
Profiles:                            Domain,Private,Public
Action:                              Allow
```

## Test Connection

After creating the firewall rule:

1. **From your PC**, test if port is accessible:
   ```bash
   python test_raw_connection.py random
   ```

2. **From analyzer network**, test connectivity:
   - Ping your PC: `ping 10.10.17.223`
   - Test port (if you have telnet/nc): `telnet 10.10.17.223 5150`

3. **Try connecting from analyzer again**

## Additional Network Checks

### Check if PC and Analyzer are on same network

Your PC: `10.10.17.223` (subnet: 10.10.16.0/20)
Analyzer: `10.10.16.34` (same subnet)

They should be able to communicate. Verify:
```bash
# From your PC, ping the analyzer
ping 10.10.16.34
```

### Check if server is listening on all interfaces

The server should be bound to `0.0.0.0:5150` (all interfaces). Verify:
```bash
netstat -an | findstr :5150
```

Should show:
```
TCP    0.0.0.0:5150           0.0.0.0:0              LISTENING
```

If it shows `127.0.0.1:5150` instead, the server is only listening on localhost and won't accept external connections.

## Common Issues

### Issue: Rule created but still blocked
- **Solution**: Check if multiple firewall profiles are enabled (Domain, Private, Public)
- Make sure the rule applies to all profiles

### Issue: Corporate/Group Policy blocking
- **Solution**: Contact IT to allow port 5150
- May need to add exception to corporate firewall

### Issue: Antivirus blocking
- **Solution**: Add exception in antivirus software
- Some antivirus programs have their own firewall

### Issue: Network isolation
- **Solution**: Check if PC and analyzer are on same VLAN
- May need network administrator to configure routing

## Quick Test Commands

```bash
# Check firewall rule
netsh advfirewall firewall show rule name="HMS Analyzer Server Port 5150"

# Check if port is listening
netstat -an | findstr :5150

# Test local connection
python test_raw_connection.py random

# Verify server is running
python verify_analyzer_running.py
```

## Still Not Working?

If firewall is configured but analyzer still can't connect:

1. **Check Windows Event Viewer**:
   - Look for firewall blocks: `Windows Logs` → `Security`
   - Filter for "Blocked" events on port 5150

2. **Check server logs**:
   - Look for connection attempts in FastAPI terminal
   - Should see "NEW CONNECTION" messages if analyzer reaches server

3. **Test from another device**:
   - Try connecting from another PC on the same network
   - Use: `telnet 10.10.17.223 5150` or `nc 10.10.17.223 5150`

4. **Check network routing**:
   - Verify default gateway: `ipconfig`
   - Traceroute: `tracert 10.10.16.34` (from your PC)

