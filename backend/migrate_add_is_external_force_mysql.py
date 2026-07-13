"""
Migration: Force add is_external column to prescriptions table (MySQL)
This will attempt to add the column even if it might exist
"""
import pymysql
from app.core.config import settings

def migrate():
    """Add is_external column to prescriptions table"""
    if settings.DATABASE_MODE.lower() != "mysql":
        print("This migration is for MySQL only. Current database mode:", settings.DATABASE_MODE)
        return
    
    try:
        # Connect directly to MySQL
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            charset=settings.MYSQL_CHARSET
        )
        
        with connection.cursor() as cursor:
            # Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'prescriptions' 
                AND COLUMN_NAME = 'is_external'
            """, (settings.MYSQL_DATABASE,))
            
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                print("Adding is_external column to prescriptions table...")
                cursor.execute("ALTER TABLE prescriptions ADD COLUMN is_external INT DEFAULT 0 NOT NULL")
                connection.commit()
                print("✓ Successfully added is_external column")
            else:
                print("✓ is_external column already exists")
        
        connection.close()
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

