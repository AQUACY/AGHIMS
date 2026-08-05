"""
Migration: Add facility branding color columns to facility_settings.
Works for both SQLite and MySQL.
"""
from sqlalchemy import text, inspect

from app.core.database import engine


COLUMNS = (
    ("bg_color_light", "VARCHAR(7)"),
    ("bg_color_dark", "VARCHAR(7)"),
    ("accent_color", "VARCHAR(7)"),
    ("text_color_light", "VARCHAR(7)"),
    ("text_color_dark", "VARCHAR(7)"),
)


def migrate():
    try:
        inspector = inspect(engine)
        existing = {col["name"] for col in inspector.get_columns("facility_settings")}

        with engine.connect() as conn:
            for name, col_type in COLUMNS:
                if name in existing:
                    print(f"OK {name} already exists")
                    continue
                print(f"Adding {name} to facility_settings...")
                conn.execute(text(f"ALTER TABLE facility_settings ADD COLUMN {name} {col_type} NULL"))
                print(f"OK Added {name}")
            conn.commit()

        print("OK Facility brand color migration complete")
    except Exception as e:
        print(f"ERROR during migration: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()
