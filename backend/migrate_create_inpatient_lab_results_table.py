"""
Migration script to create inpatient_lab_results table
"""
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Create inpatient_lab_results table"""
    from sqlalchemy import inspect
    
    with engine.connect() as conn:
        try:
            # Check if table already exists (works for both SQLite and MySQL)
            inspector = inspect(engine)
            table_exists = 'inpatient_lab_results' in inspector.get_table_names()
            
            if table_exists:
                print("Table 'inpatient_lab_results' already exists. Skipping migration.")
                return
            
            # Detect database type
            db_url = str(engine.url)
            is_sqlite = 'sqlite' in db_url.lower()
            
            if is_sqlite:
                # SQLite syntax
                conn.execute(text("""
                    CREATE TABLE inpatient_lab_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        investigation_id INTEGER NOT NULL UNIQUE,
                        results_text TEXT,
                        attachment_path VARCHAR(500),
                        entered_by INTEGER NOT NULL,
                        updated_by INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (investigation_id) REFERENCES inpatient_investigations(id) ON DELETE CASCADE,
                        FOREIGN KEY (entered_by) REFERENCES users(id),
                        FOREIGN KEY (updated_by) REFERENCES users(id)
                    )
                """))
                # Create index separately for SQLite
                conn.execute(text("CREATE INDEX idx_inpatient_lab_result_investigation_id ON inpatient_lab_results(investigation_id)"))
            else:
                # MySQL syntax
                conn.execute(text("""
                    CREATE TABLE inpatient_lab_results (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        investigation_id INT NOT NULL UNIQUE,
                        results_text TEXT,
                        attachment_path VARCHAR(500),
                        entered_by INT NOT NULL,
                        updated_by INT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (investigation_id) REFERENCES inpatient_investigations(id) ON DELETE CASCADE,
                        FOREIGN KEY (entered_by) REFERENCES users(id),
                        FOREIGN KEY (updated_by) REFERENCES users(id),
                        INDEX idx_investigation_id (investigation_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            
            conn.commit()
            print("Successfully created 'inpatient_lab_results' table.")
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating table: {e}")
            raise

if __name__ == "__main__":
    migrate()

