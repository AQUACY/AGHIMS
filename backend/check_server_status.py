"""
Check if analyzer server is actually running
This script checks the status via the API endpoint (which checks the actual running instance)
"""
import sys
import requests
import json

def check_status_via_api():
    """Check server status via API endpoint"""
    print("=" * 70)
    print("Analyzer Server Status Check (via API)")
    print("=" * 70)
    
    try:
        # Try to get status from API
        # Note: This requires authentication, so we'll also check the direct instance
        response = requests.get("http://localhost:8000/api/analyzer/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print("Status from API:")
            print(f"  Enabled: {data.get('enabled')}")
            print(f"  Running: {data.get('running')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Thread Alive: {data.get('thread_alive', 'N/A')}")
            print(f"  Socket Bound: {data.get('socket_bound', 'N/A')}")
            return
        else:
            print(f"API returned status code: {response.status_code}")
            print("(This might require authentication)")
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to API (server may not be running)")
    except Exception as e:
        print(f"Error connecting to API: {e}")
    
    print()
    print("=" * 70)
    print("Direct Instance Check (may show different instance)")
    print("=" * 70)
    
    # Also check direct instance (but note: this is a NEW instance, not the running one)
    try:
        from app.services.analyzer_server import get_analyzer_server
        from app.core.config import settings
        
        server = get_analyzer_server()
        
        print(f"Server Running: {server.running}")
        print(f"Thread Alive: {server.thread.is_alive() if server.thread else 'No thread'}")
        print(f"Server Socket: {server.server_socket}")
        
        print()
        print("Configuration:")
        print(f"  ANALYZER_ENABLED: {settings.ANALYZER_ENABLED}")
        print(f"  ANALYZER_HOST: {settings.ANALYZER_HOST}")
        print(f"  ANALYZER_PORT: {settings.ANALYZER_PORT}")
        
        print()
        print("⚠️  NOTE: Direct instance check shows a NEW instance, not the running one!")
        print("   The running server is in the FastAPI process.")
        print("   Check your server terminal logs to see if it's actually running.")
        
    except Exception as e:
        print(f"Error checking direct instance: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("Recommendations:")
    print("=" * 70)
    print("1. Check your FastAPI server terminal for startup messages")
    print("2. Look for: '✓ Analyzer server is now listening'")
    print("3. Check if port is listening: netstat -an | findstr :5150")
    print("4. If you see 'LISTENING' in netstat, the server IS running")
    print("=" * 70)

if __name__ == "__main__":
    check_status_via_api()
