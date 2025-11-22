"""
Quick script to check if analyzer server is running and listening
"""
import socket
import sys
from app.core.config import settings

def check_server():
    """Check if analyzer server is listening"""
    print("=" * 60)
    print("Analyzer Server Connection Check")
    print("=" * 60)
    print(f"Expected Host: {settings.ANALYZER_HOST}")
    print(f"Expected Port: {settings.ANALYZER_PORT}")
    print(f"Enabled: {settings.ANALYZER_ENABLED}")
    print()
    
    # Check if port is listening
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    
    try:
        result = sock.connect_ex((settings.ANALYZER_HOST if settings.ANALYZER_HOST != '0.0.0.0' else '127.0.0.1', settings.ANALYZER_PORT))
        if result == 0:
            print("✓ Port is OPEN and accepting connections")
        else:
            print("✗ Port is CLOSED or not accessible")
    except Exception as e:
        print(f"✗ Error checking port: {e}")
    finally:
        sock.close()
    
    # Check if server is listening (netstat equivalent)
    import subprocess
    try:
        if sys.platform == 'win32':
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            if f":{settings.ANALYZER_PORT}" in result.stdout:
                print(f"✓ Port {settings.ANALYZER_PORT} appears in netstat (server may be listening)")
                # Show relevant lines
                lines = [l for l in result.stdout.split('\n') if f":{settings.ANALYZER_PORT}" in l]
                for line in lines[:5]:
                    print(f"  {line.strip()}")
            else:
                print(f"✗ Port {settings.ANALYZER_PORT} not found in netstat")
        else:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            if f":{settings.ANALYZER_PORT}" in result.stdout:
                print(f"✓ Port {settings.ANALYZER_PORT} appears in netstat")
            else:
                print(f"✗ Port {settings.ANALYZER_PORT} not found in netstat")
    except Exception as e:
        print(f"Could not check netstat: {e}")
    
    print()
    print("=" * 60)
    print("Next Steps:")
    print("1. Ensure FastAPI server is running")
    print("2. Check server logs for 'Analyzer server is now listening'")
    print("3. Configure analyzer to connect to: 10.10.17.223:5150")
    print("4. Process a sample on the analyzer")
    print("5. Check analyzer_raw_data/ folder for new files")
    print("=" * 60)

if __name__ == "__main__":
    check_server()

