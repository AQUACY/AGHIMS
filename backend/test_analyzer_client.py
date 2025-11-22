"""
Test client for Sysmex XN-330 Analyzer integration
Simulates analyzer sending ASTM messages for development/testing

Usage:
    python test_analyzer_client.py [sample_id]
    
Example:
    python test_analyzer_client.py 251100001
"""
import socket
import sys
import time

# ASTM Frame delimiters
STX = '\x02'  # Start of text
ETX = '\x03'  # End of text
ACK = '\x06'  # Acknowledge
CR = '\r'     # Carriage return
LF = '\n'     # Line feed

# Default sample ID if not provided
DEFAULT_SAMPLE_ID = "251100001"

# Server configuration (development)
SERVER_HOST = "localhost"
SERVER_PORT = 5150


def create_astm_message(sample_id: str) -> str:
    """
    Create a sample ASTM E1394-97 message for Full Blood Count
    
    Format:
    P|1|PatientID|LastName^FirstName|||...
    O|1|SpecimenID|InstrumentSpecimenID|TestID|Priority|...
    R|1|TestID|Value|Units|ReferenceRange|AbnormalFlags|Status|...
    L|1|N
    
    This is a simplified example. Real Sysmex messages may vary.
    """
    # Patient record
    patient_record = f"P|1|PAT001|Doe^John|||"
    
    # Order record
    order_record = f"O|1|{sample_id}|{sample_id}|FBC|R|{time.strftime('%Y%m%d%H%M%S')}|"
    
    # Result records (example FBC values)
    result_records = [
        f"R|1|^WBC|4.79|10^3/uL|3.0-15.0|N|F",
        f"R|2|^RBC|3.61|10^6/uL|3.5-5.5|L|F",
        f"R|3|^HGB|9.4|g/dL|11.0-16.0|L|F",
        f"R|4|^HCT|29.8|%|35.0-50.0|L|F",
        f"R|5|^MCV|82.5|fL|80.0-100.0|N|F",
        f"R|6|^MCH|31.5|pg|27.0-33.0|N|F",
        f"R|7|^MCHC|31.5|g/dL|32.0-36.0|N|F",
        f"R|8|^PLT|150|10^3/uL|150-450|N|F",
        f"R|9|^NEUT#|2.5|10^3/uL|1.5-7.0|N|F",
        f"R|10|^LYMPH#|1.8|10^3/uL|1.0-4.0|N|F",
        f"R|11|^MONO#|0.3|10^3/uL|0.1-1.0|N|F",
        f"R|12|^EO#|0.15|10^3/uL|0.0-0.5|N|F",
        f"R|13|^BASO#|0.04|10^3/uL|0.0-0.2|N|F",
        f"R|14|^NEUT%|52.2|%|40.0-75.0|N|F",
        f"R|15|^LYMPH%|37.6|%|20.0-50.0|N|F",
        f"R|16|^MONO%|6.3|%|2.0-10.0|N|F",
        f"R|17|^EO%|3.1|%|0.0-6.0|N|F",
        f"R|18|^BASO%|0.8|%|0.0-2.0|N|F",
    ]
    
    # Terminator record
    terminator_record = "L|1|N"
    
    # Combine all records
    all_records = [patient_record, order_record] + result_records + [terminator_record]
    frame_content = CR.join(all_records)
    
    # Calculate checksum (simple sum of ASCII values modulo 256)
    checksum = sum(ord(c) for c in frame_content) % 256
    checksum_str = f"{checksum:02X}"
    
    # Build complete frame: STX + content + ETX + checksum + CR + LF
    frame = STX + frame_content + ETX + checksum_str + CR + LF
    
    return frame


def send_test_message(sample_id: str):
    """Send a test ASTM message to the analyzer server"""
    try:
        print(f"Connecting to analyzer server at {SERVER_HOST}:{SERVER_PORT}...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print("Connected!")
        
        # Create ASTM message
        message = create_astm_message(sample_id)
        print(f"\nSending ASTM message for sample ID: {sample_id}")
        print(f"Message length: {len(message)} bytes")
        print(f"Message preview (first 100 chars): {repr(message[:100])}")
        
        # Send message
        client_socket.sendall(message.encode('ascii'))
        print("Message sent, waiting for ACK...")
        
        # Wait for ACK
        response = client_socket.recv(1)
        if response == b'\x06':  # ACK
            print("✓ Received ACK from server")
        else:
            print(f"⚠ Received unexpected response: {repr(response)}")
        
        client_socket.close()
        print("\nConnection closed")
        print("\nCheck your server logs to see if the message was processed correctly.")
        print("You can also check the lab result in the database for sample ID:", sample_id)
    
    except ConnectionRefusedError:
        print(f"❌ Error: Could not connect to server at {SERVER_HOST}:{SERVER_PORT}")
        print("Make sure:")
        print("  1. The server is running")
        print("  2. ANALYZER_ENABLED=true in your .env file")
        print("  3. The port {SERVER_PORT} is not blocked by firewall")
        sys.exit(1)
    except socket.timeout:
        print("❌ Error: Connection timeout")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Get sample ID from command line or use default
    sample_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SAMPLE_ID
    
    print("=" * 60)
    print("Sysmex XN-330 Analyzer Test Client")
    print("=" * 60)
    print(f"Sample ID: {sample_id}")
    print(f"Server: {SERVER_HOST}:{SERVER_PORT}")
    print("=" * 60)
    print()
    
    send_test_message(sample_id)

