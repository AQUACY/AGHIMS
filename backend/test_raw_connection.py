"""
Test script to send raw data to analyzer server
This will help verify the server is receiving connections and data
"""
import socket
import sys
import time

# Try localhost first, fallback to actual IPs
# Add direct connection IP if using direct cable connection
SERVER_HOSTS = ["127.0.0.1", "192.168.1.1", "10.10.17.223", "localhost"]
SERVER_PORT = 5150

def send_test_data(data_type="random", host=None):
    """Send test data to the analyzer server"""
    print("=" * 70)
    print("Testing Analyzer Server Connection")
    print("=" * 70)
    
    # Try multiple hosts
    hosts_to_try = [host] if host else SERVER_HOSTS
    
    client_socket = None
    connected_host = None
    
    for test_host in hosts_to_try:
        print(f"Trying to connect to: {test_host}:{SERVER_PORT}")
        try:
            # Create socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            
            print("Connecting...")
            client_socket.connect((test_host, SERVER_PORT))
            print(f"✓ Connected successfully to {test_host}!")
            connected_host = test_host
            print()
            break
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"✗ Failed to connect to {test_host}: {e}")
            if client_socket:
                client_socket.close()
            client_socket = None
            continue
    
    if not client_socket or not connected_host:
        print()
        print("✗ Could not connect to any host!")
        print("  Check:")
        print("  1. Server is running")
        print("  2. Port 5150 is correct")
        print("  3. Windows Firewall allows port 5150")
        print("  4. Try: python verify_analyzer_running.py")
        sys.exit(1)
    
    try:
        
        # Prepare test data based on type
        if data_type == "random":
            # Send random bytes
            test_data = b"TEST_DATA_12345_RANDOM_BYTES_" + b"X" * 100
            print(f"Sending random test data ({len(test_data)} bytes)...")
        elif data_type == "astm":
            # Send a simple ASTM-like message
            test_data = b"\x02P|1|TEST|Test^Patient|||\rO|1|TEST001|TEST001|FBC|R|\rL|1|N\x03"
            print(f"Sending ASTM-like test data ({len(test_data)} bytes)...")
        elif data_type == "text":
            # Send plain text
            test_data = b"Hello from analyzer test client!"
            print(f"Sending text test data ({len(test_data)} bytes)...")
        else:
            test_data = b"TEST_DATA"
            print(f"Sending default test data ({len(test_data)} bytes)...")
        
        # Send data
        print(f"Data (hex): {test_data[:50].hex()}...")
        print(f"Data (readable): {test_data[:50]}")
        print()
        
        bytes_sent = client_socket.send(test_data)
        print(f"✓ Sent {bytes_sent} bytes")
        
        # Wait a moment for server to process
        time.sleep(0.5)
        
        # Try to receive response (if any)
        try:
            client_socket.settimeout(1)
            response = client_socket.recv(1024)
            if response:
                print(f"✓ Received response: {len(response)} bytes")
                print(f"  Response (hex): {response.hex()}")
                print(f"  Response (readable): {response}")
            else:
                print("No response received (this is OK)")
        except socket.timeout:
            print("No response received (timeout - this is OK)")
        
        client_socket.close()
        print()
        print("✓ Connection closed")
        print()
        print("=" * 70)
        print("✓ TEST SUCCESSFUL - Server is receiving data!")
        print("=" * 70)
        print()
        print("Check your server terminal for:")
        print("  - Connection message: '🔌 NEW CONNECTION from ...'")
        print("  - Data received message: '📥 First data from ...'")
        print("  - File saved message: '💾 Receiving analyzer data...'")
        print()
        print("Check captured data:")
        print("  python view_analyzer_data.py latest")
        print()
        print("For analyzer connection:")
        print(f"  Configure analyzer to connect to: 10.10.17.223:{SERVER_PORT}")
        print("=" * 70)
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
        if client_socket:
            client_socket.close()
        sys.exit(1)
    
    # This shouldn't be reached due to the loop above, but keep for safety
    except ConnectionRefusedError:
        print("✗ Connection refused!")
        print("  The server is not accepting connections on this port")
        print("  Check:")
        print("  1. Server is running")
        print("  2. Port 5150 is correct")
        print("  3. Windows Firewall allows port 5150")
        sys.exit(1)
    except socket.timeout:
        print("✗ Connection timeout!")
        print("  Could not connect to server")
        sys.exit(1)

if __name__ == "__main__":
    # Get data type from command line or use default
    data_type = sys.argv[1] if len(sys.argv) > 1 else "random"
    
    print(f"Test type: {data_type}")
    print()
    
    send_test_data(data_type)

