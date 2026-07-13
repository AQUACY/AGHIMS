"""
Simple script to verify analyzer server is actually running
Checks netstat and provides clear status
"""
import subprocess
import sys

def check_netstat():
    """Check if port 5150 is listening"""
    print("=" * 70)
    print("Analyzer Server Status Check")
    print("=" * 70)
    print()
    
    try:
        # Check netstat for port 5150
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
        
        lines = result.stdout.split('\n')
        listening_lines = [l for l in lines if ':5150' in l and 'LISTENING' in l]
        time_wait_lines = [l for l in lines if ':5150' in l and 'TIME_WAIT' in l]
        established_lines = [l for l in lines if ':5150' in l and 'ESTABLISHED' in l]
        
        print("Port 5150 Status:")
        print()
        
        if listening_lines:
            print("✓ PORT IS LISTENING (Server is running!)")
            for line in listening_lines:
                print(f"  {line.strip()}")
            print()
            print("The analyzer server IS running and ready to accept connections.")
            print()
            print("Next steps:")
            print("1. Configure analyzer to connect to: 10.10.17.223:5150")
            print("2. Process a sample on the analyzer")
            print("3. Watch server terminal for connection messages")
        else:
            print("✗ PORT IS NOT LISTENING (Server is NOT running)")
            print()
            print("The analyzer server is not running.")
            print()
            print("Troubleshooting:")
            print("1. Restart your FastAPI server")
            print("2. Check server terminal for startup messages")
            print("3. Look for: '✓ Analyzer server is now listening'")
            print("4. Check for any error messages")
        
        if time_wait_lines:
            print()
            print(f"Note: Found {len(time_wait_lines)} TIME_WAIT connections")
            print("(These are closed connections, not active)")
        
        if established_lines:
            print()
            print(f"✓ Found {len(established_lines)} ESTABLISHED connections")
            print("(Active connections to the server)")
            for line in established_lines:
                print(f"  {line.strip()}")
        
    except subprocess.TimeoutExpired:
        print("✗ Timeout checking netstat")
    except FileNotFoundError:
        print("✗ netstat command not found (Windows only)")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    print("=" * 70)
    print("To check server logs:")
    print("  Look at your FastAPI server terminal")
    print("  You should see: '✓ Analyzer server is now listening on 0.0.0.0:5150'")
    print("=" * 70)

if __name__ == "__main__":
    check_netstat()

