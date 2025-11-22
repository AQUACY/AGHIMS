"""
Test if the server can accept connections from external IPs
This simulates what the analyzer would do
"""
import socket
import sys

def test_external_connection():
    """Test connection from external IP perspective"""
    print("=" * 70)
    print("Testing External Connection (Simulating Analyzer)")
    print("=" * 70)
    print()
    
    # Your PC's IP that analyzer should connect to
    server_ip = "10.10.17.223"
    server_port = 5150
    
    print(f"Attempting to connect to: {server_ip}:{server_port}")
    print("(This simulates the analyzer connecting)")
    print()
    
    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5)
        
        print("Connecting...")
        client_socket.connect((server_ip, server_port))
        print("✓ Connected successfully!")
        print()
        
        # Send test data
        test_data = b"TEST_FROM_EXTERNAL_IP"
        print(f"Sending test data: {test_data}")
        bytes_sent = client_socket.send(test_data)
        print(f"✓ Sent {bytes_sent} bytes")
        
        client_socket.close()
        print("✓ Connection closed")
        print()
        print("=" * 70)
        print("✓ SUCCESS - External connection works!")
        print("=" * 70)
        print()
        print("If this works but analyzer can't connect:")
        print("1. Check analyzer IP configuration")
        print("2. Check analyzer network connectivity")
        print("3. Check if analyzer has firewall blocking outbound connections")
        print("=" * 70)
        
    except ConnectionRefusedError:
        print("✗ Connection refused!")
        print()
        print("Possible causes:")
        print("1. Server not running")
        print("2. Server only listening on localhost (127.0.0.1) not 0.0.0.0")
        print("3. Firewall still blocking (even though rule exists)")
        print("4. Network routing issue")
        print()
        print("Troubleshooting:")
        print("1. Check server is running: python verify_analyzer_running.py")
        print("2. Check server binds to 0.0.0.0: netstat -an | findstr :5150")
        print("3. Check firewall rule: netsh advfirewall firewall show rule name=\"HMS Analyzer Server Port 5150\"")
        print("4. Try disabling firewall temporarily for testing")
        sys.exit(1)
    except socket.timeout:
        print("✗ Connection timeout!")
        print("  Server may not be reachable from this IP")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_external_connection()

