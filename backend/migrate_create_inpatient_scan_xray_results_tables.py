"""
Migration script to create inpatient_scan_results and inpatient_xray_results tables
"""
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text
from sqlalchemy import inspect

def migrate():
    """Create inpatient_scan_results and inpatient_xray_results tables"""
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        try:
            # Detect database type
            db_url = str(engine.url)
            is_sqlite = 'sqlite' in db_url.lower()
            
            # Create inpatient_scan_results table
            table_exists = 'inpatient_scan_results' in inspector.get_table_names()
            if not table_exists:
                if is_sqlite:
                    conn.execute(text("""
                        CREATE TABLE inpatient_scan_results (
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
                    conn.execute(text("CREATE INDEX idx_inpatient_scan_result_investigation_id ON inpatient_scan_results(investigation_id)"))
                else:
                    conn.execute(text("""
                        CREATE TABLE inpatient_scan_results (
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
                print("Successfully created 'inpatient_scan_results' table.")
            else:
                print("Table 'inpatient_scan_results' already exists. Skipping.")
            
            # Create inpatient_xray_results table
            table_exists = 'inpatient_xray_results' in inspector.get_table_names()
            if not table_exists:
                if is_sqlite:
                    conn.execute(text("""
                        CREATE TABLE inpatient_xray_results (
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
                    conn.execute(text("CREATE INDEX idx_inpatient_xray_result_investigation_id ON inpatient_xray_results(investigation_id)"))
                else:
                    conn.execute(text("""
                        CREATE TABLE inpatient_xray_results (
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
                print("Successfully created 'inpatient_xray_results' table.")
            else:
                print("Table 'inpatient_xray_results' already exists. Skipping.")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating tables: {e}")
            raise

if __name__ == "__main__":
    migrate()

