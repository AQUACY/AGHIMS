"""
Create companion_inventory_debits for stock debits from Companion mode (department chosen at entry).
Run: python migrate_add_companion_inventory_debits_mysql.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    url = settings.DATABASE_URL
    if not url or "mysql" not in url.lower():
        print("Expected MySQL DATABASE_URL")
        sys.exit(1)
    engine = create_engine(url)
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'companion_inventory_debits'"
        ))
        if r.scalar() > 0:
            print("companion_inventory_debits already exists — skip")
            return
        conn.execute(text("""
            CREATE TABLE companion_inventory_debits (
                id INT AUTO_INCREMENT PRIMARY KEY,
                companion_visit_id INT NOT NULL,
                requesting_department VARCHAR(200) NOT NULL,
                product_code VARCHAR(50) NOT NULL,
                product_name VARCHAR(500) NOT NULL,
                quantity DOUBLE NOT NULL,
                unit_price DOUBLE NOT NULL,
                total_price DOUBLE NOT NULL,
                notes TEXT NULL,
                recorded_by_id INT NOT NULL,
                created_at DATETIME NULL,
                is_released TINYINT(1) NOT NULL DEFAULT 0,
                released_by_id INT NULL,
                released_at DATETIME NULL,
                charged_to_client TINYINT(1) NOT NULL DEFAULT 0,
                companion_visit_item_id INT NULL,
                charged_at DATETIME NULL,
                INDEX ix_companion_inv_debit_visit (companion_visit_id),
                CONSTRAINT fk_cid_visit FOREIGN KEY (companion_visit_id)
                    REFERENCES companion_visits(id) ON DELETE CASCADE,
                CONSTRAINT fk_cid_recorded FOREIGN KEY (recorded_by_id) REFERENCES users(id),
                CONSTRAINT fk_cid_released FOREIGN KEY (released_by_id) REFERENCES users(id),
                CONSTRAINT fk_cid_item FOREIGN KEY (companion_visit_item_id)
                    REFERENCES companion_visit_items(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        conn.commit()
        print("Created companion_inventory_debits")


if __name__ == "__main__":
    main()
