"""
Test if analyzer server is listening and can accept connections
"""
import socket
import sys
from app.core.config import settings

def test_listening():
    """Test if server is listening on the port"""
    print("=" * 70)
    print("Analyzer Server Listening Test")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  ANALYZER_ENABLED: {settings.ANALYZER_ENABLED}")
    print(f"  ANALYZER_HOST: {settings.ANALYZER_HOST}")
    print(f"  ANALYZER_PORT: {settings.ANALYZER_PORT}")
    print()
    
    # Test 1: Check if we can bind to the port (would fail if already in use)
    print("Test 1: Checking if port is available...")
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        test_socket.bind((settings.ANALYZER_HOST if settings.ANALYZER_HOST != '0.0.0.0' else '127.0.0.1', settings.ANALYZER_PORT))
        test_socket.close()
        print(f"  ⚠️  Port {settings.ANALYZER_PORT} is AVAILABLE (server may not be running)")
    except OSError as e:
        if "Address already in use" in str(e) or "Only one usage" in str(e):
            print(f"  ✓ Port {settings.ANALYZER_PORT} is IN USE (server is likely running)")
        else:
            print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 2: Try to connect to the server
    print("Test 2: Attempting to connect to server...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(2)
    
    try:
        # Try connecting to the actual IP the analyzer would use
        test_ips = ['127.0.0.1', '10.10.17.223', '0.0.0.0']
        connected = False
        
        for ip in test_ips:
            if ip == '0.0.0.0':
                continue
            try:
                result = client_socket.connect_ex((ip, settings.ANALYZER_PORT))
                if result == 0:
                    print(f"  ✓ Successfully connected to {ip}:{settings.ANALYZER_PORT}")
                    connected = True
                    # Send a test message
                    test_msg = b'\x02P|1|TEST|Test^Patient|||\rO|1|TEST001|TEST001|FBC|R|\rL|1|N\x03'
                    client_socket.send(test_msg)
                    print(f"  ✓ Sent test message ({len(test_msg)} bytes)")
                    response = client_socket.recv(1024)
                    if response:
                        print(f"  ✓ Received response: {response[:20]}...")
                    break
            except Exception as e:
                print(f"  ✗ Could not connect to {ip}:{settings.ANALYZER_PORT} - {e}")
        
        if not connected:
            print(f"  ✗ Could not connect to server on any IP")
            print(f"     Make sure the server is running and listening")
        
        client_socket.close()
    except Exception as e:
        print(f"  ✗ Connection test failed: {e}")
    
    print()
    print("=" * 70)
    print("Troubleshooting:")
    print("=" * 70)
    print("1. Check if FastAPI server is running")
    print("2. Look for 'Analyzer server is now listening' in server logs")
    print("3. Check Windows Firewall - port 5150 must be allowed")
    print("4. Verify analyzer is configured to connect to: 10.10.17.223:5150")
    print("5. Check server terminal for connection messages")
    print("=" * 70)

if __name__ == "__main__":
    test_listening()

