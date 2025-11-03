"""
Claim ID and check code generation utilities
"""
import random
from sqlalchemy.orm import Session
from app.models.claim import Claim


def generate_claim_id(db: Session) -> str:
    """
    Generate a unique claim ID in format: CLA-XXXXX
    """
    while True:
        claim_id = f"CLA-{random.randint(10000, 99999)}"
        existing = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if not existing:
            return claim_id


def generate_claim_check_code() -> str:
    """
    Generate a random 5-digit claim check code
    """
    return str(random.randint(10000, 99999))

