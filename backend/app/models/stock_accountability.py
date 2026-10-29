"""
Weekly stocktaking sheets and GHIMS dispense reports.

GHIMS remains the store and the place where clients are dispensed.
This platform keeps the request, the paper-style sheet, and the balance.
"""
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class GhimsCatalogItem(Base):
    """A drug name from the GHIMS store. Requests use this name, not a local quantity."""

    __tablename__ = "ghims_catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    drug_id = Column(String(80), nullable=False, unique=True, index=True)
    drug_name = Column(String(500), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)


class StocktakingSheet(Base):
    """One week, one shift, one department. Matches the daily stocktaking sheet."""

    __tablename__ = "stocktaking_sheets"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    shift = Column(String(20), nullable=False, index=True)
    period_from = Column(Date, nullable=False, index=True)
    period_to = Column(Date, nullable=False, index=True)
    prepared_by = Column(String(200), nullable=True)
    checked_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)

    department = relationship("Ward", foreign_keys=[department_id])
    lines = relationship(
        "StocktakingLine",
        back_populates="sheet",
        cascade="all, delete-orphan",
        order_by="StocktakingLine.sort_order",
    )


class StocktakingLine(Base):
    """One medicine row. R = requisition received, ST = stocktaking, CB = closing balance."""

    __tablename__ = "stocktaking_lines"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(Integer, ForeignKey("stocktaking_sheets.id"), nullable=False, index=True)
    drug_id = Column(String(80), nullable=True, index=True)
    medicine_name = Column(String(500), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    mon_r = Column(Float, nullable=True)
    mon_st = Column(Float, nullable=True)
    tue_r = Column(Float, nullable=True)
    wed_r = Column(Float, nullable=True)
    thu_r = Column(Float, nullable=True)
    fri_r = Column(Float, nullable=True)
    fri_am_st = Column(Float, nullable=True)
    fri_cb = Column(Float, nullable=True)

    sheet = relationship("StocktakingSheet", back_populates="lines")


class DispenseReport(Base):
    """An uploaded GHIMS Dispense Statistics By Drug file."""

    __tablename__ = "dispense_reports"

    id = Column(Integer, primary_key=True, index=True)
    period_from = Column(Date, nullable=False, index=True)
    period_to = Column(Date, nullable=False, index=True)
    facility_name = Column(String(300), nullable=True)
    source_filename = Column(String(300), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)

    lines = relationship(
        "DispenseReportLine",
        back_populates="report",
        cascade="all, delete-orphan",
    )


class DispenseReportLine(Base):
    __tablename__ = "dispense_report_lines"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("dispense_reports.id"), nullable=False, index=True)
    payer_group = Column(String(80), nullable=True)
    payer_scheme = Column(String(200), nullable=True)
    drug_id = Column(String(80), nullable=False, index=True)
    drug_name = Column(String(500), nullable=False)
    quantity_sold = Column(Float, nullable=False, default=0)
    amount = Column(Float, nullable=False, default=0)

    report = relationship("DispenseReport", back_populates="lines")
