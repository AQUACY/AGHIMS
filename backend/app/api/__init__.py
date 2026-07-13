"""
API routers
"""
from app.api import auth, patients, encounters, vitals, consultation, billing, claims, price_list, staff

__all__ = [
    "auth",
    "patients",
    "encounters",
    "vitals",
    "consultation",
    "billing",
    "claims",
    "price_list",
    "staff",
]

