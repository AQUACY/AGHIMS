"""
Card number generation utility
"""
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.core.config import settings
import re


def generate_card_number(db: Session) -> str:
    """
    Generate next card number in format: ER-A25-AAA0001
    Facility code is from settings (e.g., ER-A25)
    Sequential format: AAA0001, AAA0002, ..., AAA9999, AAB0001, ...
    """
    facility_code = settings.FACILITY_CODE
    prefix = f"{facility_code}-"
    
    # Get all patients with this facility code
    all_patients = db.query(Patient).filter(
        Patient.card_number.like(f"{prefix}%")
    ).all()
    
    if not all_patients:
        # First patient
        return f"{facility_code}-AAA0001"
    
    # Find the highest number
    max_sequence = 0
    for patient in all_patients:
        if len(patient.card_number) == len(prefix) + 7:  # ER-A25-AAA0001 = 15 chars
            try:
                # Extract the numeric part (last 4 digits)
                number_str = patient.card_number[-4:]
                seq_num = int(number_str)
                # Extract letters and calculate full sequence
                letters = patient.card_number[len(prefix):len(prefix)+3]
                # Convert letters to base-26 number (AAA=0, AAB=1, etc.)
                letter_val = (ord(letters[0]) - ord('A')) * 676 + (ord(letters[1]) - ord('A')) * 26 + (ord(letters[2]) - ord('A'))
                full_seq = letter_val * 10000 + seq_num
                if full_seq > max_sequence:
                    max_sequence = full_seq
            except (ValueError, IndexError):
                pass
    
    # Increment sequence
    next_seq = max_sequence + 1
    
    # Convert back to letters + number
    letter_val = (next_seq - 1) // 10000
    number_val = ((next_seq - 1) % 10000) + 1
    
    # Convert letter value to AAA format
    first = letter_val // 676
    second = (letter_val % 676) // 26
    third = letter_val % 26
    letters = f"{chr(ord('A') + first)}{chr(ord('A') + second)}{chr(ord('A') + third)}"
    
    return f"{facility_code}-{letters}{number_val:04d}"


def increment_letters(letters: str) -> str:
    """Increment letter sequence (AAA -> AAB -> ... -> ZZZ)"""
    if letters == "ZZZ":
        raise ValueError("Card number sequence exhausted")
    
    letter_list = list(letters)
    
    # Increment from right to left (like counting)
    for i in range(len(letter_list) - 1, -1, -1):
        if letter_list[i] < 'Z':
            letter_list[i] = chr(ord(letter_list[i]) + 1)
            break
        else:
            letter_list[i] = 'A'
    
    return ''.join(letter_list)


def generate_ccc_number(db: Session) -> str:
    """
    Generate a 5-digit CCC number for the day
    CCC numbers are unique per day and reset daily
    """
    from datetime import date
    
    today = date.today()
    
    # Get today's encounters and find the highest CCC number
    from app.models.encounter import Encounter
    today_encounters = (
        db.query(Encounter)
        .filter(Encounter.ccc_number.isnot(None))
        .filter(Encounter.created_at >= today)
        .order_by(Encounter.ccc_number.desc())
        .first()
    )
    
    if today_encounters and today_encounters.ccc_number:
        try:
            next_number = int(today_encounters.ccc_number) + 1
            if next_number > 99999:
                next_number = 1  # Reset if exceeds 5 digits
        except ValueError:
            next_number = 1
    else:
        next_number = 1
    
    return f"{next_number:05d}"

