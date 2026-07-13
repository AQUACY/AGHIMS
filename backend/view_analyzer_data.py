"""
Helper script to view captured analyzer data
Usage: python view_analyzer_data.py [latest|all|hex|parsed]
"""
import sys
from pathlib import Path
from datetime import datetime

RAW_DATA_DIR = Path("analyzer_raw_data")

def view_latest_hex():
    """View the latest hex dump file"""
    hex_files = sorted(RAW_DATA_DIR.glob("hex_dump_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not hex_files:
        print("No hex dump files found.")
        return
    latest = hex_files[0]
    print(f"\n=== Latest Hex Dump: {latest.name} ===")
    print(f"Modified: {datetime.fromtimestamp(latest.stat().st_mtime)}")
    print("=" * 80)
    with open(latest, 'r', encoding='utf-8') as f:
        print(f.read())

def view_latest_parsed():
    """View the latest parsed file"""
    parsed_files = sorted(RAW_DATA_DIR.glob("parsed_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not parsed_files:
        print("No parsed files found.")
        return
    latest = parsed_files[0]
    print(f"\n=== Latest Parsed Data: {latest.name} ===")
    print(f"Modified: {datetime.fromtimestamp(latest.stat().st_mtime)}")
    print("=" * 80)
    with open(latest, 'r', encoding='utf-8') as f:
        print(f.read())

def view_all_files():
    """List all captured files"""
    if not RAW_DATA_DIR.exists():
        print("No analyzer data directory found.")
        return
    
    files = sorted(RAW_DATA_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("No data files found.")
        return
    
    print(f"\n=== All Captured Files ({len(files)} files) ===")
    print("=" * 80)
    for f in files:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        print(f"{f.name:50} {size:>10} bytes  {mtime}")
    print("=" * 80)

def view_latest():
    """View latest hex and parsed files"""
    print("\n" + "=" * 80)
    print("LATEST CAPTURED ANALYZER DATA")
    print("=" * 80)
    view_latest_hex()
    print("\n" + "=" * 80)
    view_latest_parsed()

if __name__ == "__main__":
    if not RAW_DATA_DIR.exists():
        RAW_DATA_DIR.mkdir(exist_ok=True)
        print(f"Created directory: {RAW_DATA_DIR}")
        print("Waiting for analyzer data...")
        sys.exit(0)
    
    command = sys.argv[1] if len(sys.argv) > 1 else "latest"
    
    if command == "latest":
        view_latest()
    elif command == "hex":
        view_latest_hex()
    elif command == "parsed":
        view_latest_parsed()
    elif command == "all":
        view_all_files()
    else:
        print("Usage: python view_analyzer_data.py [latest|all|hex|parsed]")
        print("  latest - View latest hex dump and parsed data (default)")
        print("  hex    - View latest hex dump only")
        print("  parsed - View latest parsed data only")
        print("  all    - List all captured files")

