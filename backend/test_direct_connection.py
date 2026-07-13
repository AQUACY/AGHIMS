"""
Test direct connection to analyzer
Assumes direct cable connection with:
- PC IP: 192.168.1.1
- Analyzer IP: 192.168.1.2
"""
import socket
import sys

PC_IP = "10.10.17.223"
ANALYZER_IP = "10.10.16.34"
PORT = 5150

def test_direct_connection():
    """Test connection via direct cable"""
    print("=" * 70)
    print("Testing Direct Connection")
    print("=" * 70)
    print(f"PC IP: {PC_IP}")
    print(f"Expected Analyzer IP: {ANALYZER_IP}")
    print(f"Port: {PORT}")
    print()
    
    # Test 1: Check if we can ping analyzer (requires ping command)
    print("Step 1: Testing network connectivity...")
    import subprocess
    try:
        result = subprocess.run(['ping', '-n', '1', ANALYZER_IP], 
                              capture_output=True, text=True, timeout=5)
        if "TTL" in result.stdout or "time=" in result.stdout:
            print(f"✓ Analyzer at {ANALYZER_IP} is reachable")
        else:
            print(f"✗ Cannot reach analyzer at {ANALYZER_IP}")
            print("  Check:")
            print("  1. Cable is connected")
            print("  2. Analyzer IP is configured to 192.168.1.2")
            print("  3. PC Ethernet IP is configured to 192.168.1.1")
    except Exception as e:
        print(f"Could not test ping: {e}")
    
    print()
    
    # Test 2: Test server connection
    print("Step 2: Testing server connection...")
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5)
        
        print(f"Connecting to {PC_IP}:{PORT}...")
        client_socket.connect((PC_IP, PORT))
        print("✓ Connected to server successfully!")
        
        # Send test data
        test_data = b"TEST_DIRECT_CONNECTION"
        bytes_sent = client_socket.send(test_data)
        print(f"✓ Sent {bytes_sent} bytes")
        
        client_socket.close()
        print("✓ Connection closed")
        print()
        print("=" * 70)
        print("✓ Direct connection test successful!")
        print("=" * 70)
        print()
        print("Server is ready to receive data from analyzer.")
        print("Configure analyzer to connect to: 192.168.1.1:5150")
        print("=" * 70)
        
    except ConnectionRefusedError:
        print("✗ Connection refused!")
        print()
        print("Troubleshooting:")
        print("1. Check server is running")
        print("2. Check firewall allows port 5150")
        print("3. Verify server is listening: netstat -an | findstr :5150")
        sys.exit(1)
    except socket.timeout:
        print("✗ Connection timeout!")
        print("  Server may not be reachable")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_direct_connection()

