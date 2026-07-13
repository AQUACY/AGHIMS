"""
Script to analyze captured analyzer data and identify structure
"""
import sys
from pathlib import Path
from datetime import datetime

RAW_DATA_DIR = Path("analyzer_raw_data")

def analyze_file(file_path: Path):
    """Analyze a captured data file"""
    print(f"\n{'='*80}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*80}")
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print(f"First 100 bytes (hex): {data[:100].hex()}")
    print(f"\nFirst 200 bytes (readable):")
    try:
        readable = data[:200].decode('ascii', errors='replace')
        print(readable)
    except:
        print("(Could not decode as ASCII)")
    
    # Check for ASTM markers
    print(f"\n{'='*80}")
    print("ASTM Protocol Analysis:")
    print(f"{'='*80}")
    
    stx_count = data.count(b'\x02')  # STX
    etx_count = data.count(b'\x03')  # ETX
    pipe_count = data.count(b'|')    # Field separator
    
    print(f"STX (\\x02) count: {stx_count}")
    print(f"ETX (\\x03) count: {etx_count}")
    print(f"Pipe (|) count: {pipe_count}")
    
    # Check for record types
    if b'P|' in data:
        print("✓ Found Patient record (P|)")
    if b'O|' in data:
        print("✓ Found Order record (O|)")
    if b'R|' in data:
        print("✓ Found Result record (R|)")
    if b'L|' in data:
        print("✓ Found Terminator record (L|)")
    
    # Check if it's HTTP
    if data.startswith(b'GET ') or data.startswith(b'POST ') or data.startswith(b'HTTP/'):
        print("\n⚠ WARNING: This appears to be an HTTP request, not analyzer data!")
        print("   This is likely from a browser or health check.")
        print("   Real analyzer data should start with STX (\\x02) or contain ASTM records.")
        return False
    
    # Check for ASTM frame structure
    if stx_count > 0 and etx_count > 0:
        print("\n✓ Appears to be ASTM format (has STX and ETX)")
        
        # Try to extract frames
        frames = []
        start = 0
        while True:
            stx_pos = data.find(b'\x02', start)
            if stx_pos == -1:
                break
            etx_pos = data.find(b'\x03', stx_pos)
            if etx_pos == -1:
                break
            frame = data[stx_pos+1:etx_pos]  # Exclude STX and ETX
            frames.append(frame)
            start = etx_pos + 1
        
        print(f"Found {len(frames)} complete ASTM frames")
        
        if frames:
            print(f"\nFirst frame preview (first 200 chars):")
            try:
                print(frames[0][:200].decode('ascii', errors='replace'))
            except:
                print("(Could not decode)")
    
    elif pipe_count > 10:
        print("\n✓ Has many pipe separators (likely ASTM format without frame delimiters)")
        print("  This might be ASTM data without STX/ETX, or a different format")
    else:
        print("\n⚠ Does not appear to be standard ASTM format")
        print("   May be a different protocol or incomplete data")
    
    return True

def main():
    if not RAW_DATA_DIR.exists():
        print("No analyzer_raw_data directory found")
        return
    
    files = sorted(RAW_DATA_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not files:
        print("No data files found")
        return
    
    print(f"Found {len(files)} data files")
    
    # Analyze latest files
    for file in files[:5]:  # Analyze up to 5 most recent
        analyze_file(file)
        print()

if __name__ == "__main__":
    main()

