"""
Migration script to backfill claim detail tables for existing claims
This populates claim_diagnoses, claim_investigations, claim_prescriptions, and claim_procedures
for claims that were created before the claim detail tables were added.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

def migrate():
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("Database not found!")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if claim detail tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='claim_diagnoses'")
        if not cursor.fetchone():
            print("Claim detail tables do not exist! Please run migrate_add_claim_details.py first.")
            return
        
        # Get all claims that don't have claim details yet
        cursor.execute("""
            SELECT DISTINCT c.id as claim_id, c.encounter_id
            FROM claims c
            LEFT JOIN claim_diagnoses cd ON cd.claim_id = c.id
            WHERE cd.id IS NULL
        """)
        claims_to_backfill = cursor.fetchall()
        
        if not claims_to_backfill:
            print("All claims already have claim details populated!")
            return
        
        print(f"Found {len(claims_to_backfill)} claims to backfill...")
        
        backfilled = 0
        for claim_id, encounter_id in claims_to_backfill:
            # Get diagnoses for this encounter
            cursor.execute("""
                SELECT id, diagnosis, icd10, gdrg_code, is_chief
                FROM diagnoses
                WHERE encounter_id = ?
                ORDER BY id
                LIMIT 4
            """, (encounter_id,))
            diagnoses = cursor.fetchall()
            
            # Insert diagnoses
            diagnosis_order = 0
            for diag_id, diagnosis, icd10, gdrg_code, is_chief in diagnoses:
                cursor.execute("""
                    INSERT INTO claim_diagnoses 
                    (claim_id, diagnosis_id, description, icd10, gdrg_code, is_chief, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    claim_id, diag_id, diagnosis or "", icd10 or "", gdrg_code or "", 
                    1 if is_chief else 0, diagnosis_order, datetime.now(), datetime.now()
                ))
                diagnosis_order += 1
            
            # Get investigations for this encounter (only completed)
            cursor.execute("""
                SELECT id, procedure_name, gdrg_code, service_date, investigation_type
                FROM investigations
                WHERE encounter_id = ? AND status = 'completed' AND gdrg_code IS NOT NULL AND gdrg_code != ''
                ORDER BY id
                LIMIT 5
            """, (encounter_id,))
            investigations = cursor.fetchall()
            
            # Insert investigations
            investigation_order = 0
            for inv_id, procedure_name, gdrg_code, service_date, investigation_type in investigations:
                cursor.execute("""
                    INSERT INTO claim_investigations
                    (claim_id, investigation_id, description, gdrg_code, service_date, investigation_type, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    claim_id, inv_id, procedure_name or "", gdrg_code or "", 
                    service_date or datetime.now(), investigation_type or "",
                    investigation_order, datetime.now(), datetime.now()
                ))
                investigation_order += 1
            
            # Get prescriptions for this encounter (only dispensed)
            cursor.execute("""
                SELECT id, medicine_name, medicine_code, quantity, service_date, dose, frequency, duration, unparsed
                FROM prescriptions
                WHERE encounter_id = ? AND dispensed_by IS NOT NULL AND medicine_code IS NOT NULL AND medicine_code != ''
                ORDER BY id
                LIMIT 5
            """, (encounter_id,))
            prescriptions = cursor.fetchall()
            
            # Get price for prescriptions - we'll need to calculate total_cost
            # For now, set price to 0 (it will be recalculated when claim is edited/saved)
            prescription_order = 0
            for presc_id, medicine_name, medicine_code, quantity, service_date, dose, frequency, duration, unparsed in prescriptions:
                # Note: price and total_cost will need to be calculated from price list
                # Setting to 0 for now - user can edit and save to get correct prices
                cursor.execute("""
                    INSERT INTO claim_prescriptions
                    (claim_id, prescription_id, description, code, price, quantity, total_cost, service_date, 
                     dose, frequency, duration, unparsed, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    claim_id, presc_id, medicine_name or "", medicine_code or "", 
                    0.0, quantity or 0, 0.0, service_date or datetime.now(),
                    dose or "", frequency or "", duration or "", unparsed or "",
                    prescription_order, datetime.now(), datetime.now()
                ))
                prescription_order += 1
            
            # Get procedure from encounter
            cursor.execute("""
                SELECT procedure_g_drg_code, procedure_name, created_at
                FROM encounters
                WHERE id = ?
            """, (encounter_id,))
            encounter_proc = cursor.fetchone()
            
            # Insert procedure if exists
            if encounter_proc and encounter_proc[0] and encounter_proc[0].strip():
                procedure_gdrg, procedure_name, encounter_created = encounter_proc
                cursor.execute("""
                    INSERT INTO claim_procedures
                    (claim_id, description, gdrg_code, service_date, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    claim_id, procedure_name or "", procedure_gdrg, 
                    encounter_created or datetime.now(),
                    0, datetime.now(), datetime.now()
                ))
            
            backfilled += 1
            if backfilled % 10 == 0:
                print(f"Backfilled {backfilled}/{len(claims_to_backfill)} claims...")
        
        conn.commit()
        print(f"\nMigration completed successfully!")
        print(f"- Backfilled {backfilled} existing claims with claim details")
        print("\nNote: Prescription prices are set to 0. They will be recalculated")
        print("      when you edit and save those claims (prices come from price lists).")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

