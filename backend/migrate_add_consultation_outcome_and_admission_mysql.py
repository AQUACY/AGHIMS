"""
Migration: add outcome to consultation_notes and create admission_recommendations table (MySQL version)
"""
import pymysql
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def migrate():
    """Add outcome column to consultation_notes and create admission_recommendations table"""
    print("=" * 60)
    print("Migration: Add outcome to consultation_notes and create admission_recommendations")
    print("=" * 60)
    print()
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        with connection.cursor() as cursor:
            # 1) Add outcome column to consultation_notes if not exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'consultation_notes'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] > 0:
                # Check if column exists
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.columns 
                    WHERE table_schema = %s 
                    AND table_name = 'consultation_notes'
                    AND column_name = 'outcome'
                """, (DB_CONFIG['database'],))
                
                result = cursor.fetchone()
                if result['count'] == 0:
                    print("Adding outcome column to consultation_notes...")
                    cursor.execute("""
                        ALTER TABLE consultation_notes 
                        ADD COLUMN outcome TEXT NULL
                    """)
                    print("✓ Added outcome column to consultation_notes")
                else:
                    print("✓ outcome column already exists in consultation_notes")
            else:
                print("⚠ consultation_notes table does not exist, skipping")
            
            # 2) Create admission_recommendations table if not exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'admission_recommendations'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("Creating admission_recommendations table...")
                cursor.execute("""
                    CREATE TABLE admission_recommendations (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        encounter_id INT NOT NULL UNIQUE,
                        ward VARCHAR(255) NOT NULL,
                        recommended_by INT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                        FOREIGN KEY (recommended_by) REFERENCES users(id),
                        INDEX idx_encounter_id (encounter_id),
                        INDEX idx_recommended_by (recommended_by)
                    )
                """)
                print("✓ Created admission_recommendations table")
            else:
                print("✓ admission_recommendations table already exists")
            
            connection.commit()
        
        connection.close()
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

