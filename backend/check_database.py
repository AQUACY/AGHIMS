#!/usr/bin/env python3
"""
Database Configuration Checker
Checks if the application is using MySQL or SQLite and shows connection details
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.database import engine, SessionLocal
from sqlalchemy import text, inspect

def check_database():
    """Check database configuration and connection"""
    print("=" * 70)
    print("DATABASE CONFIGURATION CHECKER")
    print("=" * 70)
    print()
    
    # Check configuration
    print("📋 Configuration:")
    print(f"   DATABASE_MODE: {settings.DATABASE_MODE}")
    print(f"   DATABASE_URL: {settings.DATABASE_URL}")
    print()
    
    # Check if SQLite file exists
    if settings.DATABASE_MODE.lower() == "sqlite":
        sqlite_path = Path(settings.SQLITE_DB_PATH)
        abs_path = sqlite_path.resolve()
        print("📁 SQLite Database:")
        print(f"   Configured Path: {settings.SQLITE_DB_PATH}")
        print(f"   Absolute Path: {abs_path}")
        print(f"   File Exists: {'✓ YES' if sqlite_path.exists() else '✗ NO'}")
        if sqlite_path.exists():
            file_size = sqlite_path.stat().st_size
            print(f"   File Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
        print()
        
        # Check for other SQLite files in common locations
        print("🔍 Checking for other SQLite files in common locations:")
        common_locations = [
            "./hms.db",
            "../hms.db",
            "./backend/hms.db",
            os.path.expanduser("~/hms.db"),
        ]
        found_files = []
        for loc in common_locations:
            loc_path = Path(loc)
            if loc_path.exists() and loc_path.is_file():
                abs_loc = loc_path.resolve()
                size = loc_path.stat().st_size
                found_files.append((abs_loc, size))
                print(f"   ✓ Found: {abs_loc} ({size:,} bytes)")
        
        if not found_files:
            print("   No other SQLite files found in common locations")
        print()
    
    # Check MySQL configuration
    elif settings.DATABASE_MODE.lower() == "mysql":
        print("🗄️  MySQL Configuration:")
        print(f"   Host: {settings.MYSQL_HOST}")
        print(f"   Port: {settings.MYSQL_PORT}")
        print(f"   User: {settings.MYSQL_USER}")
        print(f"   Database: {settings.MYSQL_DATABASE}")
        print(f"   Password: {'***' if settings.MYSQL_PASSWORD else '(empty)'}")
        print()
    
    # Test connection
    print("🔌 Testing Connection:")
    try:
        with engine.connect() as conn:
            # Get database type
            db_type = engine.dialect.name
            print(f"   Database Type: {db_type.upper()}")
            
            # Get database version
            if db_type == "sqlite":
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                print(f"   SQLite Version: {version}")
                
                # Get database file path
                result = conn.execute(text("PRAGMA database_list"))
                db_list = result.fetchall()
                for db_info in db_list:
                    if db_info[1] == "main":
                        print(f"   Database File: {db_info[2]}")
                        break
                        
            elif db_type == "mysql":
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
                print(f"   MySQL Version: {version}")
                
                result = conn.execute(text("SELECT DATABASE()"))
                current_db = result.scalar()
                print(f"   Current Database: {current_db}")
            
            # Test query
            result = conn.execute(text("SELECT 1"))
            result.scalar()
            print("   Connection Status: ✓ SUCCESS")
            
    except Exception as e:
        print(f"   Connection Status: ✗ FAILED")
        print(f"   Error: {str(e)}")
        return False
    
    print()
    
    # Check environment variables
    print("🌍 Environment Variables:")
    env_vars = [
        "DATABASE_MODE",
        "SQLITE_DB_PATH",
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ]
    found_env = False
    for var in env_vars:
        value = os.getenv(var)
        if value:
            found_env = True
            if "PASSWORD" in var:
                print(f"   {var}: ***")
            else:
                print(f"   {var}: {value}")
    
    if not found_env:
        print("   No database-related environment variables found")
        print("   Using default configuration from config.py")
    print()
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print(f"📄 .env file found: {env_file.resolve()}")
        with open(env_file, 'r') as f:
            lines = f.readlines()
            db_related = [line.strip() for line in lines if any(var in line.upper() for var in ["DATABASE", "MYSQL", "SQLITE"])]
            if db_related:
                print("   Database-related settings:")
                for line in db_related:
                    if "PASSWORD" in line.upper():
                        # Mask password
                        if "=" in line:
                            key, _ = line.split("=", 1)
                            print(f"      {key}=***")
                        else:
                            print(f"      {line}")
                    else:
                        print(f"      {line}")
            else:
                print("   No database-related settings found in .env")
    else:
        print("📄 .env file: Not found (using defaults)")
    print()
    
    # Check current working directory
    print("📂 Current Working Directory:")
    print(f"   {os.getcwd()}")
    print()
    
    # Check virtual environment
    print("🐍 Python Environment:")
    print(f"   Python Executable: {sys.executable}")
    print(f"   Virtual Environment: {'✓ ACTIVE' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else '✗ NOT ACTIVE'}")
    if hasattr(sys, 'real_prefix'):
        print(f"   Venv Path: {sys.real_prefix}")
    elif hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        print(f"   Venv Path: {sys.prefix}")
    print()
    
    # List tables if connection successful
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"📊 Database Tables ({len(tables)} found):")
            if tables:
                for table in sorted(tables):
                    print(f"   - {table}")
            else:
                print("   No tables found (database might be empty)")
    except Exception as e:
        print(f"   Could not list tables: {str(e)}")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if settings.DATABASE_MODE.lower() == "sqlite":
        sqlite_path = Path(settings.SQLITE_DB_PATH)
        abs_path = sqlite_path.resolve()
        print(f"✓ Using SQLite database")
        print(f"✓ Database file: {abs_path}")
        if not sqlite_path.exists():
            print("⚠ WARNING: Database file does not exist!")
            print("  This might be a new database or the path is incorrect.")
    elif settings.DATABASE_MODE.lower() == "mysql":
        print(f"✓ Using MySQL database")
        print(f"✓ Host: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
        print(f"✓ Database: {settings.MYSQL_DATABASE}")
    
    print()
    return True

if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

