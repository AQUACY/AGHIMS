# Sysmex XN-330 Analyzer Setup Guide

This guide explains how to connect your Sysmex XN-330 analyzer to the HMS system and capture raw data for analysis.

## Step 1: Configure the Analyzer Server

The analyzer server is already configured in your `.env` file:
```env
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0  # Listen on all interfaces (allows connections from analyzer)
ANALYZER_PORT=5150
ANALYZER_EQUIPMENT_IP=10.10.16.34
```

**Development Setup:**
- Your PC IP: `10.10.17.223` (on network 10.10.16.0/20)
- Analyzer IP: `10.10.16.34`
- Server listens on: `0.0.0.0:5150` (all interfaces)
- Analyzer should connect to: `10.10.17.223:5150`

**Production Setup:**
- Production Server IP: `10.10.16.50`
- Analyzer should connect to: `10.10.16.50:5150`

## Step 2: Start the HMS Server

Start your FastAPI server:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see in the logs:
```
INFO: Analyzer server starting on 0.0.0.0:5150
INFO: ✓ Analyzer server is now listening on 0.0.0.0:5150
```

## Step 3: Configure the Sysmex XN-330 Analyzer

### On the Analyzer:

1. **Access System Settings**:
   - Navigate to: `System` → `Communication` → `Host Interface` (or `LIS/HIS`)

2. **Configure TCP/IP Settings**:
   
   **For Development:**
   - **Protocol**: TCP/IP
   - **Host IP Address**: `10.10.17.223` (your development PC IP)
   - **Port**: `5150`
   - **Connection Type**: Bidirectional (or as available)
   - **Transmission Mode**: Automatic (or Manual, depending on your workflow)
   
   **For Production:**
   - **Protocol**: TCP/IP
   - **Host IP Address**: `10.10.16.50` (your production server IP)
   - **Port**: `5150`
   - **Connection Type**: Bidirectional (or as available)
   - **Transmission Mode**: Automatic (or Manual, depending on your workflow)

3. **ASTM Settings** (if available):
   - **ASTM Version**: E1394-97 (or latest available)
   - **Frame Format**: Standard ASTM
   - **Delimiter**: Standard (| pipe character)
   - **Terminator**: CR/LF

4. **Test Connection**:
   - Some analyzers have a "Test Connection" option
   - Or process a sample and check if data is transmitted

## Step 4: Capture Raw Data

When the analyzer sends data, it will be automatically saved to:

```
backend/analyzer_raw_data/
├── raw_data_YYYYMMDD_HHMMSS.txt      # Raw binary data
├── hex_dump_YYYYMMDD_HHMMSS.txt       # Hex dump with ASCII view
└── parsed_YYYYMMDD_HHMMSS.txt        # Parsed frames (readable)
```

### File Descriptions:

1. **raw_data_*.txt**: Raw binary data as received (may contain non-printable characters)
2. **hex_dump_*.txt**: Hex dump showing:
   - Timestamp of each data chunk
   - Hex representation
   - ASCII representation (where applicable)
3. **parsed_*.txt**: Parsed ASTM frames showing:
   - Readable content
   - Hex representation
   - Timestamp

## Step 5: View Captured Data

### Option 1: View in Text Editor
```bash
# View hex dump (most readable)
cat analyzer_raw_data/hex_dump_*.txt

# View parsed frames
cat analyzer_raw_data/parsed_*.txt
```

### Option 2: View Latest File
```bash
# Get the latest hex dump file
ls -t analyzer_raw_data/hex_dump_*.txt | head -1 | xargs cat

# Get the latest parsed file
ls -t analyzer_raw_data/parsed_*.txt | head -1 | xargs cat
```

### Option 3: Monitor in Real-Time
```bash
# Watch for new files (Linux/Mac)
watch -n 1 'ls -lt analyzer_raw_data/ | head -10'

# Or use tail to follow a file
tail -f analyzer_raw_data/parsed_*.txt
```

## Step 6: Analyze the Data Structure

Once you have captured data, you can:

1. **Check the hex dump** to see:
   - Frame delimiters (STX `\x02`, ETX `\x03`)
   - Record structure
   - Field separators (usually `|`)
   - Checksum format

2. **Check the parsed file** to see:
   - Patient records (P|...)
   - Order records (O|...)
   - Result records (R|...)
   - Comment records (C|...)
   - Terminator records (L|...)

3. **Identify test codes** used by your analyzer:
   - Look for Result records (R|...)
   - Note the test ID format (e.g., `WBC`, `RBC`, `^WBC`, etc.)
   - Note the value format and units

## Step 7: Update Test Code Mapping

After analyzing the captured data, you may need to update the test code mapping in:
`backend/app/services/analyzer_mapper.py`

Add any test codes that don't match the current mapping in the `SYSMEX_TO_TEMPLATE_MAP` dictionary.

## Troubleshooting

### No Data Received

1. **Check server logs**:
   - Look for "Analyzer connection from..." messages
   - Check for any error messages

2. **Check firewall**:
   - Ensure port 5150 is open
   - Check if Windows Firewall is blocking connections

3. **Test connection**:
   ```bash
   # From analyzer network, test if port is accessible
   # Development:
   telnet 10.10.17.223 5150
   # Or
   nc -zv 10.10.17.223 5150
   
   # Production:
   telnet 10.10.16.50 5150
   # Or
   nc -zv 10.10.16.50 5150
   ```

4. **Check analyzer settings**:
   - Verify IP address and port are correct
   - Check if analyzer is set to send data automatically
   - Try manual transmission if available

### Data Received but Not Parsed

1. **Check raw data files**:
   - Look at `hex_dump_*.txt` to see what was received
   - Verify frame delimiters are present

2. **Check server logs**:
   - Look for "No records parsed" warnings
   - Check for parsing errors

3. **Verify ASTM format**:
   - Compare with ASTM E1394-97 standard
   - Check if analyzer uses a different format

### Connection Drops

1. **Check timeout settings**:
   - Increase `ANALYZER_TIMEOUT` in `.env` if needed

2. **Check network stability**:
   - Ensure stable network connection
   - Check for network interruptions

## Example: What to Look For

A typical ASTM message might look like:

```
STX
P|1|PAT001|Doe^John|||
O|1|251100001|251100001|FBC|R|20251121120000|
R|1|^WBC|4.79|10^3/uL|3.0-15.0|N|F|
R|2|^RBC|3.61|10^6/uL|3.5-5.5|L|F|
...
L|1|N
ETX<checksum>CRLF
```

Key things to note:
- **Sample ID**: Usually in Order record (O|1|**251100001**|...)
- **Test Codes**: In Result records (R|1|**^WBC**|...)
- **Values**: After test code (R|1|^WBC|**4.79**|...)
- **Units**: After value (R|1|^WBC|4.79|**10^3/uL**|...)

## Next Steps

After capturing and analyzing the data:
1. Review the captured files
2. Identify the exact test code format used by your analyzer
3. Update the mapping in `analyzer_mapper.py` if needed
4. Test with a real sample to verify mapping works correctly

