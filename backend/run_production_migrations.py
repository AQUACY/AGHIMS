#!/usr/bin/env python3
"""
Quick script to run required production migrations
Run this script on your production server to add missing columns.
"""
import os
import sys
import getpass

def main():
    print("=" * 60)
    print("PRODUCTION MIGRATION RUNNER")
    print("=" * 60)
    print("\nThis script will run the following migrations:")
    print("1. Add 'other_names' column to 'patients' table")
    print("2. Add discharge fields to 'ward_admissions' table")
    print("\n" + "=" * 60)
    
    # Check environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_name = os.getenv('DB_NAME', 'hms')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    
    print(f"\nDatabase Configuration:")
    print(f"  Host: {db_host}")
    print(f"  Port: {db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    
    # Prompt for password if not set in environment
    if not db_password:
        db_password = getpass.getpass(f"Enter MySQL password for user '{db_user}': ")
        # Set it in environment so migration scripts can use it
        os.environ['DB_PASSWORD'] = db_password
    else:
        print(f"  Password: {'*' * len(db_password)} (from environment)")
    
    # Confirm before proceeding
    response = input("\nProceed with migrations? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    print("\n" + "=" * 60)
    print("Running Migrations...")
    print("=" * 60)
    
    # Import and run migrations
    try:
        print("\n[1/2] Running migrate_add_patient_other_names_mysql.py...")
        from migrate_add_patient_other_names_mysql import migrate as migrate_other_names
        migrate_other_names()
        
        print("\n[2/2] Running migrate_add_discharge_fields_mysql.py...")
        from migrate_add_discharge_fields_mysql import migrate as migrate_discharge_fields
        migrate_discharge_fields()
        
        print("\n" + "=" * 60)
        print("✓ ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now restart your application server.")
        
    except ImportError as e:
        print(f"\n✗ Error importing migration module: {e}")
        print("Make sure you're running this script from the backend directory.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

