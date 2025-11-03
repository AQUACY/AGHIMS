"""
Migration: add extended vitals fields
Fields: respiration, bmi, spo2, rbs, fbs, upt, rdt_malaria, retro_rdt
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy import text
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hms.db"


def add_column_if_missing(conn, table: str, column_def: str, column_name: str):
    result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    cols = {row[1] for row in result}
    if column_name not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))


def upgrade():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    meta = MetaData()
    meta.reflect(bind=engine)
    if "vitals" not in meta.tables:
        return
    with engine.begin() as conn:
        add_column_if_missing(conn, "vitals", "respiration INTEGER", "respiration")
        add_column_if_missing(conn, "vitals", "bmi FLOAT", "bmi")
        add_column_if_missing(conn, "vitals", "spo2 INTEGER", "spo2")
        add_column_if_missing(conn, "vitals", "rbs FLOAT", "rbs")
        add_column_if_missing(conn, "vitals", "fbs FLOAT", "fbs")
        add_column_if_missing(conn, "vitals", "upt TEXT", "upt")
        add_column_if_missing(conn, "vitals", "rdt_malaria TEXT", "rdt_malaria")
        add_column_if_missing(conn, "vitals", "retro_rdt TEXT", "retro_rdt")


def downgrade():
    # SQLite does not support easy column drops; no-op
    pass


if __name__ == "__main__":
    upgrade()


