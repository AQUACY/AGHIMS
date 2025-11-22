"""
Python script to check analyzer logs from systemd service
Works on both Linux and Windows
"""
import subprocess
import sys
from pathlib import Path

def check_systemd_logs():
    """Check systemd service logs"""
    print("=" * 70)
    print("HMS Backend Service Logs - Analyzer Activity")
    print("=" * 70)
    print()
    
    service_name = "hms-backend"
    
    # Check service status
    print("1. Service Status:")
    print("-" * 70)
    try:
        result = subprocess.run(
            ['systemctl', 'status', service_name, '--no-pager', '-l'],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.split('\n')[:20]
        for line in lines:
            print(line)
    except FileNotFoundError:
        print("systemctl not found (not a systemd system or Windows)")
    except Exception as e:
        print(f"Error checking status: {e}")
    print()
    
    # Show recent logs
    print("2. Recent Analyzer Logs (last 50 lines, filtered):")
    print("-" * 70)
    try:
        result = subprocess.run(
            ['journalctl', '-u', service_name, '-n', '50', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Filter for analyzer-related messages
        keywords = ['analyzer', 'Analyzer', 'CONNECTION', 'NEW CONNECTION', 
                   'Receiving', 'Saving', 'sample', 'Sample', 'ACK', 'First data']
        for line in result.stdout.split('\n'):
            if any(keyword.lower() in line.lower() for keyword in keywords):
                print(line)
    except FileNotFoundError:
        print("journalctl not found (not a systemd system)")
    except Exception as e:
        print(f"Error reading logs: {e}")
    print()
    
    # Show all recent logs
    print("3. All Recent Logs (last 30 lines):")
    print("-" * 70)
    try:
        result = subprocess.run(
            ['journalctl', '-u', service_name, '-n', '30', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(result.stdout)
    except FileNotFoundError:
        print("journalctl not found")
        print()
        print("On Windows or non-systemd systems:")
        print("  Check the terminal where uvicorn is running")
        print("  Or check log files if configured")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Check captured data files
    print("4. Captured Data Files:")
    print("-" * 70)
    raw_data_dir = Path("analyzer_raw_data")
    if raw_data_dir.exists():
        files = sorted(raw_data_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            print(f"Found {len(files)} data files")
            print("Latest 5 files:")
            for f in files[:5]:
                size = f.stat().st_size
                from datetime import datetime
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"  {f.name} ({size} bytes, {mtime})")
        else:
            print("No data files found")
    else:
        print("No analyzer_raw_data directory found")
    print()
    
    print("=" * 70)
    print("Quick Commands:")
    print("=" * 70)
    print("Follow logs:        sudo journalctl -u hms-backend -f")
    print("Last 100 lines:     sudo journalctl -u hms-backend -n 100")
    print("Since today:        sudo journalctl -u hms-backend --since today")
    print("Search analyzer:    sudo journalctl -u hms-backend | grep -i analyzer")
    print("View data files:    python view_analyzer_data.py latest")
    print("=" * 70)

if __name__ == "__main__":
    check_systemd_logs()

