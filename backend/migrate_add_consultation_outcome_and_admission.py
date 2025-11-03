"""
Migration: add outcome to consultation_notes and create admission_recommendations table
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, MetaData, Table, text
from sqlalchemy import create_engine
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "hms.db"


def upgrade():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    meta = MetaData()
    meta.reflect(bind=engine)

    # 1) Add outcome column to consultation_notes if not exists
    if "consultation_notes" in meta.tables:
        # SQLite needs a table rebuild for adding nullable columns in older versions,
        # but modern versions support simple ALTER for new nullable column.
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(consultation_notes)")).fetchall()
            existing_cols = {row[1] for row in result}
            if "outcome" not in existing_cols:
                conn.execute(text("ALTER TABLE consultation_notes ADD COLUMN outcome TEXT"))

    # 2) Create admission_recommendations table if not exists
    if "admission_recommendations" not in meta.tables:
        admission_recommendations = Table(
            "admission_recommendations",
            meta,
            Column("id", Integer, primary_key=True, index=True),
            Column("encounter_id", Integer, ForeignKey("encounters.id"), nullable=False, unique=True),
            Column("ward", String, nullable=False),
            Column("recommended_by", Integer, ForeignKey("users.id"), nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
            Column("updated_at", DateTime, default=datetime.utcnow),
        )
        admission_recommendations.create(bind=engine, checkfirst=True)


def downgrade():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    meta = MetaData()
    meta.reflect(bind=engine)

    # Drop admission_recommendations table
    if "admission_recommendations" in meta.tables:
        meta.tables["admission_recommendations"].drop(bind=engine)

    # Can't easily drop a column in SQLite without table rebuild; skipping drop of outcome
    # Leaving outcome column in consultation_notes.


if __name__ == "__main__":
    upgrade()


