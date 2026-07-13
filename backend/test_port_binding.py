"""
Test if we can bind to port 5150
"""
import socket
from app.core.config import settings

def test_bind():
    """Test binding to the analyzer port"""
    print("=" * 70)
    print("Testing Port Binding")
    print("=" * 70)
    print(f"Host: {settings.ANALYZER_HOST}")
    print(f"Port: {settings.ANALYZER_PORT}")
    print()
    
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        print(f"Attempting to bind to {settings.ANALYZER_HOST}:{settings.ANALYZER_PORT}...")
        test_socket.bind((settings.ANALYZER_HOST, settings.ANALYZER_PORT))
        print("✓ Successfully bound to port!")
        
        test_socket.listen(1)
        print("✓ Successfully set up listener!")
        
        test_socket.close()
        print("✓ Socket closed successfully")
        print()
        print("Port is available and can be bound!")
        
    except OSError as e:
        print(f"✗ Failed to bind: {e}")
        if "Address already in use" in str(e) or "Only one usage" in str(e):
            print()
            print("Port is already in use!")
            print("Check what's using it:")
            print("  netstat -ano | findstr :5150")
            print()
            print("Or kill the process:")
            print("  taskkill /PID <PID> /F")
        else:
            print(f"Unknown error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)

if __name__ == "__main__":
    test_bind()

