"""
Migration: Create user_brand_preferences for per-user theme colors.
Works for both SQLite and MySQL.
"""
from sqlalchemy import text, inspect

from app.core.database import engine


def migrate():
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        if "user_brand_preferences" in tables:
            print("OK user_brand_preferences already exists")
            return

        dialect = engine.dialect.name
        print(f"Creating user_brand_preferences ({dialect})...")

        if dialect == "sqlite":
            ddl = """
            CREATE TABLE user_brand_preferences (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                bg_color_light VARCHAR(7),
                bg_color_dark VARCHAR(7),
                accent_color VARCHAR(7),
                text_color_light VARCHAR(7),
                text_color_dark VARCHAR(7),
                updated_at DATETIME,
                CONSTRAINT uq_user_brand_preferences_user_id UNIQUE (user_id),
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        else:
            ddl = """
            CREATE TABLE user_brand_preferences (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                bg_color_light VARCHAR(7) NULL,
                bg_color_dark VARCHAR(7) NULL,
                accent_color VARCHAR(7) NULL,
                text_color_light VARCHAR(7) NULL,
                text_color_dark VARCHAR(7) NULL,
                updated_at DATETIME NULL,
                CONSTRAINT uq_user_brand_preferences_user_id UNIQUE (user_id),
                CONSTRAINT fk_user_brand_preferences_user
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """

        with engine.connect() as conn:
            conn.execute(text(ddl))
            if dialect != "sqlite":
                conn.execute(
                    text(
                        "CREATE INDEX ix_user_brand_preferences_user_id "
                        "ON user_brand_preferences (user_id)"
                    )
                )
            conn.commit()

        print("OK user_brand_preferences created")
    except Exception as e:
        print(f"ERROR during migration: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()
