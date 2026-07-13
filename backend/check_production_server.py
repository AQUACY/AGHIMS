"""
Quick script to check if production server is running and accessible
"""
import requests
import sys

SERVER_URL = "http://10.10.16.50:8000"

def check_server():
    """Check if server is running"""
    print("=" * 70)
    print("Production Server Health Check")
    print("=" * 70)
    print(f"Server URL: {SERVER_URL}")
    print()
    
    # Test 1: Health endpoint
    print("Test 1: Health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Server is running (Status: {response.status_code})")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Server returned status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server")
        print("  Server may not be running or not accessible")
        print()
        print("Troubleshooting:")
        print("1. Check if backend server is running")
        print("2. Check if port 8000 is open")
        print("3. Check firewall rules")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("✗ Connection timeout")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    
    print()
    
    # Test 2: API endpoint (should return CORS headers even if auth fails)
    print("Test 2: API endpoint (checking CORS)...")
    try:
        response = requests.get(f"{SERVER_URL}/api/health", timeout=5)
        print(f"✓ API endpoint accessible (Status: {response.status_code})")
        
        # Check CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        if any(cors_headers.values()):
            print("✓ CORS headers present:")
            for key, value in cors_headers.items():
                if value:
                    print(f"  {key}: {value}")
        else:
            print("⚠ No CORS headers found (may be normal for some endpoints)")
    except Exception as e:
        print(f"⚠ Could not test API endpoint: {e}")
    
    print()
    print("=" * 70)
    print("If server is not accessible:")
    print("1. Check if uvicorn is running: ps aux | grep uvicorn")
    print("2. Check server logs for errors")
    print("3. Verify port 8000 is listening: netstat -an | grep :8000")
    print("4. Check firewall: sudo ufw status (Linux) or netsh advfirewall (Windows)")
    print("=" * 70)

if __name__ == "__main__":
    check_server()

