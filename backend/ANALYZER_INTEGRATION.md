# Sysmex XN-330 Analyzer Integration

This document describes how to set up and use the TCP/IP integration with the Sysmex XN-330 hematology analyzer.

## Overview

The analyzer integration allows the Sysmex XN-330 to automatically push lab results to the HMS system via TCP/IP using the ASTM E1394-97 protocol. When results are received, they are automatically parsed, mapped to the appropriate lab result template, and saved to the database.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```env
# Analyzer Integration Settings
ANALYZER_ENABLED=true
ANALYZER_HOST=0.0.0.0
ANALYZER_PORT=5150
ANALYZER_EQUIPMENT_IP=10.10.16.34
ANALYZER_TIMEOUT=30
```

**Configuration Options:**
- `ANALYZER_ENABLED`: Set to `true` to enable the analyzer server (default: `false`)
- `ANALYZER_HOST`: Host to bind the TCP server (use `0.0.0.0` to listen on all interfaces)
- `ANALYZER_PORT`: TCP port to listen on (default: `5150`)
- `ANALYZER_EQUIPMENT_IP`: Equipment IP address (for reference/logging only)
- `ANALYZER_TIMEOUT`: Connection timeout in seconds (default: `30`)

### Production vs Development

**Development:**
- Use `ANALYZER_HOST=0.0.0.0` to accept connections from analyzer on your PC
- Your PC IP: `10.10.17.223` (on network 10.10.16.0/20)
- Analyzer IP: `10.10.16.34`
- Configure analyzer to connect to: `10.10.17.223:5150`
- Use port `5150` (or any available port)
- Test using the provided test client script
- Ensure Windows Firewall allows connections on port 5150

**Production:**
- Use `ANALYZER_HOST=0.0.0.0` to accept connections from the analyzer
- Production Server IP: `10.10.16.50`
- Configure analyzer to connect to: `10.10.16.50:5150`
- Use port `5150` (configured on the analyzer)
- Ensure firewall allows connections on port 5150

## How It Works

1. **Sample ID Generation**: When a lab investigation is confirmed, a sample ID is generated (format: `YYMMNNNNN`, e.g., `251100001`)

2. **Analyzer Processing**: The sample is processed on the Sysmex analyzer with the sample ID

3. **Data Transmission**: The analyzer sends ASTM E1394-97 protocol messages via TCP/IP to the HMS server

4. **Automatic Processing**:
   - The server receives and parses the ASTM messages
   - Extracts sample ID and test results
   - Finds the matching investigation by sample ID
   - Maps analyzer test codes to template field names
   - Updates the lab result with the analyzer data

5. **Result Available**: The lab result is automatically populated and available for review/validation

## Testing in Development

### 1. Enable the Analyzer Server

Add to your `.env` file:
```env
ANALYZER_ENABLED=true
ANALYZER_HOST=localhost
ANALYZER_PORT=5150
```

### 2. Start the Server

The analyzer server starts automatically when you start the FastAPI application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see in the logs:
```
INFO: Analyzer server started on localhost:5150
INFO: Analyzer server listening on localhost:5150
```

### 3. Generate a Sample ID

1. Go to the Lab Results page
2. Select an investigation
3. Click "Generate Sample ID"
4. Note the generated sample ID (e.g., `251100001`)

### 4. Test with Mock Client

Use the provided test client script to simulate analyzer data:

```bash
cd backend
python test_analyzer_client.py 251100001
```

This will:
- Connect to the analyzer server
- Send a sample ASTM message with FBC results
- Wait for ACK from server
- Show connection status

### 5. Verify Results

1. Check server logs for processing messages
2. Go to the Lab Results page
3. Load the investigation with the sample ID
4. Verify that the results have been automatically populated

## API Endpoints

### Get Analyzer Status
```
GET /api/analyzer/status
```
Returns the current status of the analyzer server.

**Response:**
```json
{
  "enabled": true,
  "host": "0.0.0.0",
  "port": 5150,
  "equipment_ip": "10.10.16.34",
  "running": true,
  "status": "running"
}
```

### Test ASTM Parsing
```
POST /api/analyzer/test-parse
Body: { "astm_data": "raw ASTM message string" }
```
Tests parsing of a raw ASTM message without saving to database.

### Test Result Mapping
```
POST /api/analyzer/test-map
Body: { "sample_id": "251100001" }
```
Tests mapping analyzer results to a lab result template for a given sample ID.

### Restart Analyzer Server
```
POST /api/analyzer/restart
```
Restarts the analyzer server (requires Lab Head or Admin role).

## Troubleshooting

### Server Not Starting

1. **Check if enabled**: Verify `ANALYZER_ENABLED=true` in `.env`
2. **Check port availability**: Ensure port 5150 is not in use:
   ```bash
   # Linux/Mac
   lsof -i :5150
   # Windows
   netstat -an | findstr :5150
   ```
3. **Check firewall**: Ensure firewall allows connections on port 5150

### Connection Refused

1. **Verify server is running**: Check logs for "Analyzer server listening..."
2. **Check host/port**: Ensure client connects to correct host and port
3. **Check firewall**: Ensure firewall allows connections

### Results Not Appearing

1. **Check sample ID match**: Ensure the sample ID in the ASTM message matches an existing investigation
2. **Check logs**: Look for error messages in server logs
3. **Verify template mapping**: Check if analyzer test codes match template field names
4. **Check investigation status**: Ensure the investigation is confirmed

### Sample ID Not Found

- The sample ID in the ASTM message must match an existing lab result's `sample_no` in `template_data`
- Ensure the sample ID was generated and saved before sending from analyzer
- Check database for existing sample IDs:
  ```sql
  SELECT investigation_id, template_data->>'$.sample_no' as sample_no 
  FROM lab_results 
  WHERE template_data IS NOT NULL;
  ```

## Test Code Mapping

The system maps Sysmex XN-330 test codes to template field names. Common mappings:

| Sysmex Code | Template Field | Description |
|------------|----------------|-------------|
| WBC | WBC | White Blood Cell Count |
| RBC | RBC | Red Blood Cell Count |
| HGB | HGB | Hemoglobin |
| HCT | HCT | Hematocrit |
| MCV | MCV | Mean Corpuscular Volume |
| MCH | MCH | Mean Corpuscular Hemoglobin |
| MCHC | MCHC | Mean Corpuscular Hemoglobin Concentration |
| PLT | PLT | Platelet Count |
| NEUT# | NEUT# | Neutrophils (Absolute) |
| LYMPH# | LYMPH# | Lymphocytes (Absolute) |
| MONO# | MONO# | Monocytes (Absolute) |
| EO# | EO# | Eosinophils (Absolute) |
| BASO# | BASO# | Basophils (Absolute) |
| NEUT% | NEUT% | Neutrophils (%) |
| LYMPH% | LYMPH% | Lymphocytes (%) |
| MONO% | MONO% | Monocytes (%) |
| EO% | EO% | Eosinophils (%) |
| BASO% | BASO% | Basophils (%) |

## Production Setup

1. **Configure Analyzer on Sysmex**:
   
   **Development:**
   - Set LIS/HIS connection to TCP/IP
   - Set server IP: `10.10.17.223` (your development PC)
   - Set port: `5150`
   - Enable automatic transmission
   
   **Production:**
   - Set LIS/HIS connection to TCP/IP
   - Set server IP: `10.10.16.50` (your production server)
   - Set port: `5150`
   - Enable automatic transmission

2. **Configure HMS Server**:
   - Set `ANALYZER_ENABLED=true`
   - Set `ANALYZER_HOST=0.0.0.0`
   - Set `ANALYZER_PORT=5150`
   - Ensure firewall allows port 5150

3. **Test Connection**:
   - Generate a sample ID in HMS
   - Process sample on analyzer
   - Verify results appear in HMS

4. **Monitor Logs**:
   - Check server logs for connection and processing messages
   - Monitor for errors or warnings

## Notes

- The analyzer server runs in a separate thread and does not block the main FastAPI application
- Multiple analyzer connections are supported (each handled in a separate thread)
- Results are automatically merged with existing lab result data (analyzer data takes precedence)
- The `sample_no` field is preserved if not present in analyzer data
- Existing `field_values` and `messages` are merged (analyzer data updates existing values)

