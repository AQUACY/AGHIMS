"""
Migration script to add claim_amount column to procedure, surgery, and unmapped DRG price tables
"""
from sqlalchemy import create_engine, text, inspect as sql_inspect
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

TABLES = ["procedure_prices", "surgery_prices", "unmapped_drg_prices"]


def migrate():
    """Adds the claim_amount column to service price list tables."""
    try:
        is_sqlite = "sqlite" in settings.DATABASE_URL

        for table_name in TABLES:
            if is_sqlite:
                with engine.connect() as connection:
                    result = connection.execute(text(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                    ))
                    if result.fetchone() is None:
                        print(f"SKIP: Table '{table_name}' does not exist.")
                        continue

                    result = connection.execute(text(f"PRAGMA table_info({table_name})"))
                    column_names = [row[1] for row in result.fetchall()]
            else:
                inspector = sql_inspect(engine)
                if table_name not in inspector.get_table_names():
                    print(f"✗ Table '{table_name}' does not exist, skipping.")
                    continue
                column_names = [col["name"] for col in inspector.get_columns(table_name)]

            if "claim_amount" in column_names:
                print(f"OK: 'claim_amount' already exists on '{table_name}'.")
                continue

            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN claim_amount FLOAT")
                )
            print(f"OK: Added 'claim_amount' to '{table_name}'.")

        print("Migration complete!")

    except Exception as e:
        print(f"ERROR during migration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting migration to add claim_amount to service price tables...")
    migrate()
