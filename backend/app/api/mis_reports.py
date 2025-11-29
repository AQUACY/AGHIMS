"""
MIS Reports endpoints for DHIMS platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.models.encounter import Encounter, EncounterStatus
from app.models.patient import Patient
from app.models.diagnosis import Diagnosis
from app.models.vital import Vital
from app.models.investigation import Investigation
from app.models.lab_result import LabResult
from app.models.scan_result import ScanResult
from app.models.xray_result import XrayResult
import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse
from app.api.mis_reports_morbidity import (
    MORBIDITY_DISEASES,
    map_icd10_to_morbidity_disease,
    get_morbidity_age_group
)

router = APIRouter(prefix="/mis-reports", tags=["mis-reports"])


def format_age_for_dhims(patient: Patient, encounter_date: date) -> str:
    """
    Format age in DHIMS format: "X Year(s)", "X Month(s)", etc.
    """
    if patient.date_of_birth:
        birth_date = patient.date_of_birth
        age_delta = encounter_date - birth_date
        
        years = age_delta.days // 365
        months = (age_delta.days % 365) // 30
        days = age_delta.days % 30
        
        if years > 0:
            return f"{years} Year(s)"
        elif months > 0:
            return f"{months} Month(s)"
        elif days > 0:
            return f"{days} Day(s)"
        else:
            return "0 Day(s)"
    elif patient.age is not None:
        # Fallback to stored age if DOB not available
        return f"{patient.age} Year(s)"
    else:
        return "N/A"


def check_pregnancy_status(diagnoses: List[Diagnosis]) -> str:
    """
    Check if patient is pregnant based on diagnoses
    Look for pregnancy-related ICD-10 codes:
    - Z34: Supervision of normal pregnancy
    - Z35: Supervision of high-risk pregnancy
    - Z36: Antenatal screening
    - Z37: Outcome of delivery
    - Z38: Liveborn infants
    - Z39: Postpartum care
    - O codes: Pregnancy, childbirth and the puerperium
    """
    pregnancy_prefixes = ['Z34', 'Z35', 'Z36', 'Z37', 'Z38', 'Z39']
    
    for diagnosis in diagnoses:
        icd10 = diagnosis.icd10 or ''
        # Check if ICD-10 code starts with O (obstetric codes) or Z34-Z39
        if icd10.startswith('O') or any(icd10.startswith(prefix) for prefix in pregnancy_prefixes):
            return "Yes"
    
    return "No"


def format_diagnosis_for_dhims(diagnosis: Diagnosis) -> str:
    """
    Format diagnosis as "ICD10_CODE [Description]"
    """
    icd10 = diagnosis.icd10 or ""
    description = diagnosis.diagnosis or ""
    
    if icd10 and description:
        return f"{icd10} [{description}]"
    elif icd10:
        return icd10
    elif description:
        return description
    else:
        return ""


@router.get("/consulting-room-register")
def get_consulting_room_register(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    department: Optional[str] = Query(None, description="Filter by department(s) - comma-separated for multiple"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records", "Doctor", "PA"]))
):
    """
    Get Consulting Room Register data for DHIMS export
    Returns finalized encounters within the date range
    """
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Parse departments if provided (comma-separated)
        department_list = None
        if department:
            department_list = [d.strip() for d in department.split(",")]
        
        # Build query
        query = db.query(Encounter).join(Patient).filter(
            Encounter.status == EncounterStatus.FINALIZED.value,
            Encounter.archived == False,
            func.date(Encounter.finalized_at) >= start,
            func.date(Encounter.finalized_at) <= end
        )
        
        if department_list:
            query = query.filter(Encounter.department.in_(department_list))
        
        # Order by finalized date and patient name
        encounters = query.order_by(
            Encounter.finalized_at.asc(),
            Patient.name.asc()
        ).all()
        
        # Build report data
        report_data = []
        for idx, encounter in enumerate(encounters, start=1):
            patient = encounter.patient
            
            # Get diagnoses
            diagnoses = db.query(Diagnosis).filter(
                Diagnosis.encounter_id == encounter.id
            ).order_by(
                Diagnosis.is_chief.desc(),  # Chief diagnosis first
                Diagnosis.created_at.asc()
            ).all()
            
            # Principal diagnosis (chief diagnosis or first diagnosis)
            principal_diagnosis = None
            additional_diagnoses = []
            
            for diag in diagnoses:
                formatted = format_diagnosis_for_dhims(diag)
                if formatted:
                    if diag.is_chief or not principal_diagnosis:
                        principal_diagnosis = formatted
                    else:
                        additional_diagnoses.append(formatted)
            
            # If no chief diagnosis, use first as principal
            if not principal_diagnosis and diagnoses:
                principal_diagnosis = format_diagnosis_for_dhims(diagnoses[0])
                additional_diagnoses = [format_diagnosis_for_dhims(d) for d in diagnoses[1:] if format_diagnosis_for_dhims(d)]
            
            # Get test results (lab, scan, xray)
            test_results = []
            
            # Lab results
            lab_investigations = db.query(Investigation).filter(
                Investigation.encounter_id == encounter.id,
                Investigation.investigation_type == "lab",
                Investigation.status == "completed"
            ).all()
            
            for inv in lab_investigations:
                lab_result = db.query(LabResult).filter(
                    LabResult.investigation_id == inv.id
                ).first()
                if lab_result:
                    # Use results_text if available, otherwise try to format template_data
                    if lab_result.results_text:
                        test_results.append(f"Lab: {lab_result.results_text[:100]}")  # Limit length
                    elif lab_result.template_data:
                        # Format template data as summary
                        template_data = lab_result.template_data
                        if isinstance(template_data, dict) and 'field_values' in template_data:
                            # Create a summary from key fields
                            field_values = template_data.get('field_values', {})
                            summary_parts = [f"{k}: {v}" for k, v in list(field_values.items())[:5]]  # First 5 fields
                            if summary_parts:
                                test_results.append(f"Lab: {', '.join(summary_parts)}")
            
            # Scan results
            scan_investigations = db.query(Investigation).filter(
                Investigation.encounter_id == encounter.id,
                Investigation.investigation_type == "scan",
                Investigation.status == "completed"
            ).all()
            
            for inv in scan_investigations:
                scan_result = db.query(ScanResult).filter(
                    ScanResult.investigation_id == inv.id
                ).first()
                if scan_result and scan_result.results_text:
                    # Limit length for display
                    result_text = scan_result.results_text[:100] if len(scan_result.results_text) > 100 else scan_result.results_text
                    test_results.append(f"Scan: {result_text}")
            
            # Xray results
            xray_investigations = db.query(Investigation).filter(
                Investigation.encounter_id == encounter.id,
                Investigation.investigation_type == "xray",
                Investigation.status == "completed"
            ).all()
            
            for inv in xray_investigations:
                xray_result = db.query(XrayResult).filter(
                    XrayResult.investigation_id == inv.id
                ).first()
                if xray_result and xray_result.results_text:
                    # Limit length for display
                    result_text = xray_result.results_text[:100] if len(xray_result.results_text) > 100 else xray_result.results_text
                    test_results.append(f"Xray: {result_text}")
            
            # Format encounter date
            encounter_date = encounter.finalized_at.date() if encounter.finalized_at else encounter.created_at.date()
            schedule_date = encounter_date.strftime("%d-%m-%Y")
            
            # Format age
            age_str = format_age_for_dhims(patient, encounter_date)
            
            # Check pregnancy
            is_pregnant = check_pregnancy_status(diagnoses)
            
            # NHIA status
            nhia_status = "Yes" if patient.insured else "No"
            
            # Insurance number (use insurance_id or ccc_number)
            insurance_no = patient.insurance_id or patient.ccc_number or encounter.ccc_number
            
            # Format patient name
            patient_name_parts = [part for part in [patient.name, patient.surname, patient.other_names] if part]
            patient_name = " ".join(patient_name_parts).upper()
            
            # Format telephone (remove leading zeros if needed)
            telephone = patient.contact or ""
            if telephone and telephone.startswith("0"):
                telephone = telephone[1:]
            
            report_data.append({
                "sr_no": idx,
                "schedule_date": schedule_date,
                "patient_no": patient.card_number,
                "insurance_no": str(insurance_no) if insurance_no else None,
                "patient_name": patient_name,
                "address": patient.address or "",
                "telephone": telephone,
                "age": age_str,
                "sex": "Male" if patient.gender.upper() == "M" else "Female",
                "test_results": "; ".join(test_results) if test_results else None,
                "principal_diagnosis": principal_diagnosis,
                "additional_diagnosis": ", ".join(additional_diagnoses) if additional_diagnoses else None,
                "pregnant_patient": is_pregnant,
                "nhia_patient": nhia_status
            })
        
        return {
            "data": report_data,
            "total_records": len(report_data),
            "start_date": start_date,
            "end_date": end_date,
            "department": department
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/consulting-room-register/export")
def export_consulting_room_register(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    department: Optional[str] = Query(None, description="Filter by department(s) - comma-separated for multiple"),
    clinic_name: str = Query("Asesewa Government Hospital", description="Clinic name for header"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records", "Doctor", "PA"]))
):
    """
    Export Consulting Room Register as Excel file matching DHIMS template format
    """
    try:
        # Get report data
        report_response = get_consulting_room_register(
            start_date=start_date,
            end_date=end_date,
            department=department,
            db=db,
            current_user=current_user
        )
        
        report_data = report_response["data"]
        
        # Format dates for header
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_formatted = start.strftime("%d-%m-%Y")
        end_formatted = end.strftime("%d-%m-%Y")
        
        # Create DataFrame with proper structure matching template
        # First, create header rows
        header_rows = [
            [f"MIAM's Consulting Room Register From {start_formatted} To {end_formatted}", None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Clinic : {clinic_name}", None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Report Generation Date: {start_formatted} to {end_formatted}", None, None, None, None, None, None, None, None, None, None, None, None, None],
            ["Sr.No.", "Schedule Date", "Patient No.", "Insurance No.", "Patient Name", "Address (Locality)", "Telephone Number of Patient", "Age", "Sex", "Test Result(s)", "Principal Diagnosis (New Case)", "Additional Diagnosis (New Case)", "Pregnant Patient", "NHIA Patient"]
        ]
        
        # Create data rows
        data_rows = []
        for record in report_data:
            data_rows.append([
                record["sr_no"],
                record["schedule_date"],
                record["patient_no"],
                record["insurance_no"],
                record["patient_name"],
                record["address"],
                record["telephone"],
                record["age"],
                record["sex"],
                record["test_results"],
                record["principal_diagnosis"],
                record["additional_diagnosis"],
                record["pregnant_patient"],
                record["nhia_patient"]
            ])
        
        # Combine header and data
        all_rows = header_rows + data_rows
        
        # Create DataFrame
        df = pd.DataFrame(all_rows)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Worksheet', index=False, header=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Worksheet']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        filename = f"CR_REGISTER_{start_formatted.replace('-', '_')}_TO_{end_formatted.replace('-', '_')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting report: {str(e)}"
        )


def get_age_group(patient: Patient, encounter_date: date) -> str:
    """
    Determine age group for DHIMS reporting
    Returns: "0-28 Days", "1-11 Months", "1-4", "5-9", "10-14", "15-17", "18-19", "20-34", "35-49", "50-59", "60-69", "70 & Above"
    """
    if patient.date_of_birth:
        birth_date = patient.date_of_birth
        age_delta = encounter_date - birth_date
        days = age_delta.days
        years = days // 365
        months = (days % 365) // 30
        
        if days <= 28:
            return "0-28 Days"
        elif days <= 365:
            if months <= 11:
                return "1-11 Months"
            else:
                return "1-4"  # 12 months = 1 year, falls into 1-4
        elif years < 5:
            return "1-4"
        elif years < 10:
            return "5-9"
        elif years < 15:
            return "10-14"
        elif years < 18:
            return "15-17"
        elif years < 20:
            return "18-19"
        elif years < 35:
            return "20-34"
        elif years < 50:
            return "35-49"
        elif years < 60:
            return "50-59"
        elif years < 70:
            return "60-69"
        else:
            return "70 & Above"
    elif patient.age is not None:
        years = patient.age
        if years < 1:
            return "1-11 Months"  # Approximation
        elif years < 5:
            return "1-4"
        elif years < 10:
            return "5-9"
        elif years < 15:
            return "10-14"
        elif years < 18:
            return "15-17"
        elif years < 20:
            return "18-19"
        elif years < 35:
            return "20-34"
        elif years < 50:
            return "35-49"
        elif years < 60:
            return "50-59"
        elif years < 70:
            return "60-69"
        else:
            return "70 & Above"
    else:
        return "Unknown"


@router.get("/statement-of-outpatient")
def get_statement_of_outpatient(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    departments: Optional[str] = Query(None, description="Comma-separated list of departments"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records"]))
):
    """
    Get Statement of Outpatient data for DHIMS export
    Returns age-grouped statistics for insured/non-insured, new/old patients
    """
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Parse departments if provided
        department_list = None
        if departments:
            department_list = [d.strip() for d in departments.split(",")]
        
        # Build query for finalized encounters in date range
        query = db.query(Encounter).join(Patient).filter(
            Encounter.status == EncounterStatus.FINALIZED.value,
            Encounter.archived == False,
            func.date(Encounter.finalized_at) >= start,
            func.date(Encounter.finalized_at) <= end
        )
        
        if department_list:
            query = query.filter(Encounter.department.in_(department_list))
        
        encounters = query.all()
        
        # Age groups in order
        age_groups = [
            "0-28 Days",
            "1-11 Months",
            "1-4",
            "5-9",
            "10-14",
            "15-17",
            "18-19",
            "20-34",
            "35-49",
            "50-59",
            "60-69",
            "70 & Above"
        ]
        
        # Initialize statistics structure
        stats = {}
        for age_group in age_groups:
            stats[age_group] = {
                "insured_new_male": 0,
                "insured_new_female": 0,
                "insured_old_male": 0,
                "insured_old_female": 0,
                "non_insured_new_male": 0,
                "non_insured_new_female": 0,
                "non_insured_old_male": 0,
                "non_insured_old_female": 0
            }
        
        # Get all patient IDs to check for first encounters
        patient_ids = set(e.patient_id for e in encounters)
        
        # For each patient, find their first encounter ever (to determine if new or old)
        first_encounter_dates = {}
        for patient_id in patient_ids:
            first_encounter = db.query(Encounter).filter(
                Encounter.patient_id == patient_id,
                Encounter.archived == False
            ).order_by(Encounter.created_at.asc()).first()
            
            if first_encounter:
                first_encounter_dates[patient_id] = first_encounter.created_at.date()
        
        # Process each encounter
        for encounter in encounters:
            patient = encounter.patient
            encounter_date = encounter.finalized_at.date() if encounter.finalized_at else encounter.created_at.date()
            
            # Determine age group
            age_group = get_age_group(patient, encounter_date)
            if age_group == "Unknown":
                continue  # Skip if age cannot be determined
            
            # Determine if new or old patient
            patient_first_date = first_encounter_dates.get(patient.id)
            is_new = patient_first_date and patient_first_date >= start
            
            # Determine gender
            is_male = patient.gender.upper() == "M"
            
            # Determine insurance status
            is_insured = patient.insured or bool(encounter.ccc_number)
            
            # Update statistics
            if is_insured:
                if is_new:
                    if is_male:
                        stats[age_group]["insured_new_male"] += 1
                    else:
                        stats[age_group]["insured_new_female"] += 1
                else:
                    if is_male:
                        stats[age_group]["insured_old_male"] += 1
                    else:
                        stats[age_group]["insured_old_female"] += 1
            else:
                if is_new:
                    if is_male:
                        stats[age_group]["non_insured_new_male"] += 1
                    else:
                        stats[age_group]["non_insured_new_female"] += 1
                else:
                    if is_male:
                        stats[age_group]["non_insured_old_male"] += 1
                    else:
                        stats[age_group]["non_insured_old_female"] += 1
        
        # Build report data
        report_data = []
        for idx, age_group in enumerate(age_groups, start=1):
            group_stats = stats[age_group]
            report_data.append({
                "sr_no": idx,
                "age_group": age_group,
                "insured_new_male": group_stats["insured_new_male"],
                "insured_new_female": group_stats["insured_new_female"],
                "insured_old_male": group_stats["insured_old_male"],
                "insured_old_female": group_stats["insured_old_female"],
                "non_insured_new_male": group_stats["non_insured_new_male"],
                "non_insured_new_female": group_stats["non_insured_new_female"],
                "non_insured_old_male": group_stats["non_insured_old_male"],
                "non_insured_old_female": group_stats["non_insured_old_female"],
                "total_male": (
                    group_stats["insured_new_male"] + group_stats["insured_old_male"] +
                    group_stats["non_insured_new_male"] + group_stats["non_insured_old_male"]
                ),
                "total_female": (
                    group_stats["insured_new_female"] + group_stats["insured_old_female"] +
                    group_stats["non_insured_new_female"] + group_stats["non_insured_old_female"]
                )
            })
        
        # Calculate totals
        totals = {
            "insured_new_male": sum(r["insured_new_male"] for r in report_data),
            "insured_new_female": sum(r["insured_new_female"] for r in report_data),
            "insured_old_male": sum(r["insured_old_male"] for r in report_data),
            "insured_old_female": sum(r["insured_old_female"] for r in report_data),
            "non_insured_new_male": sum(r["non_insured_new_male"] for r in report_data),
            "non_insured_new_female": sum(r["non_insured_new_female"] for r in report_data),
            "non_insured_old_male": sum(r["non_insured_old_male"] for r in report_data),
            "non_insured_old_female": sum(r["non_insured_old_female"] for r in report_data),
            "total_male": sum(r["total_male"] for r in report_data),
            "total_female": sum(r["total_female"] for r in report_data)
        }
        
        return {
            "data": report_data,
            "totals": totals,
            "start_date": start_date,
            "end_date": end_date,
            "departments": department_list
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/statement-of-outpatient/export")
def export_statement_of_outpatient(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    departments: Optional[str] = Query(None, description="Comma-separated list of departments"),
    clinic_name: str = Query("Asesewa Government Hospital", description="Clinic name for header"),
    clinic_city: str = Query("Asesewa", description="Clinic city for header"),
    clinic_region: str = Query("N/A", description="Clinic region for header"),
    clinic_district: str = Query("N/A", description="Clinic district for header"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records"]))
):
    """
    Export Statement of Outpatient as Excel file matching DHIMS template format
    """
    try:
        # Get report data
        report_response = get_statement_of_outpatient(
            start_date=start_date,
            end_date=end_date,
            departments=departments,
            db=db,
            current_user=current_user
        )
        
        report_data = report_response["data"]
        totals = report_response["totals"]
        
        # Format dates for header
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_formatted = start.strftime("%d-%m-%Y")
        end_formatted = end.strftime("%d-%m-%Y")
        
        # Get month and year
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month = month_names[start.month - 1]
        year = start.year
        
        # Get departments/modalities
        department_list = report_response.get("departments", [])
        if not department_list:
            # Get all unique departments from encounters
            dept_query = db.query(Encounter.department).filter(
                Encounter.status == EncounterStatus.FINALIZED.value,
                Encounter.archived == False,
                func.date(Encounter.finalized_at) >= start,
                func.date(Encounter.finalized_at) <= end
            ).distinct()
            department_list = [row[0] for row in dept_query.all()]
        
        modality_str = ", ".join(department_list) if department_list else "ALL DEPARTMENTS"
        
        # Get current date for report generation
        report_gen_date = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
        
        # Create header rows
        header_rows = [
            [f"MIAM's DHIMS Reports - Statement Of Out-Patient From {start_formatted} To {end_formatted}", None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Modality : {modality_str}", None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Report Generation Date: {report_gen_date}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Centre Name : {clinic_name}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Centre City : {clinic_city}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Centre Region : {clinic_region}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Centre District : {clinic_district}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Month : {month}", None, None, None, None, None, None, None, None, None, None, None],
            [f"Year : {year}", None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, "INSURED PATIENTS", None, None, None, "NON-INSURED PATIENTS", None, None, None, None, None],
            [None, None, "NEW", None, "OLD", None, "NEW", None, "OLD", None, "Total", None],
            ["Sr.No.", "Age Groups(Yrs.)", "Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female"]
        ]
        
        # Create data rows
        data_rows = []
        for record in report_data:
            data_rows.append([
                record["sr_no"],
                record["age_group"],
                record["insured_new_male"],
                record["insured_new_female"],
                record["insured_old_male"],
                record["insured_old_female"],
                record["non_insured_new_male"],
                record["non_insured_new_female"],
                record["non_insured_old_male"],
                record["non_insured_old_female"],
                record["total_male"],
                record["total_female"]
            ])
        
        # Add footer row
        footer_rows = [
            ["Medical Officer In-Charge :", None, None, None, None, None, None, None, None, None, None, None]
        ]
        
        # Combine all rows
        all_rows = header_rows + data_rows + footer_rows
        
        # Create DataFrame
        df = pd.DataFrame(all_rows)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Worksheet', index=False, header=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Worksheet']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        filename = f"STATEMENT_OF_OUTPATIENT_{start_formatted.replace('-', '_')}_TO_{end_formatted.replace('-', '_')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting report: {str(e)}"
        )


@router.get("/opd-morbidity")
def get_opd_morbidity(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    departments: Optional[str] = Query(None, description="Comma-separated list of departments"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records"]))
):
    """
    Get OPD Morbidity Report data for DHIMS export
    Returns disease statistics grouped by age and gender
    """
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Parse departments if provided
        department_list = None
        if departments:
            department_list = [d.strip() for d in departments.split(",")]
        
        # Build query for finalized encounters in date range
        query = db.query(Encounter).join(Patient).filter(
            Encounter.status == EncounterStatus.FINALIZED.value,
            Encounter.archived == False,
            func.date(Encounter.finalized_at) >= start,
            func.date(Encounter.finalized_at) <= end
        )
        
        if department_list:
            query = query.filter(Encounter.department.in_(department_list))
        
        encounters = query.all()
        
        # Age groups for morbidity report
        age_groups = ["0-28 Days", "1 - 11M", "1-4", "5-9", "10-14", "15-17", "18-19", "20-34", "35-49", "50-59", "60-69", "70+"]
        
        # Initialize statistics structure: disease -> age_group -> gender -> count
        stats = {}
        for disease in MORBIDITY_DISEASES:
            stats[disease] = {}
            for age_group in age_groups:
                stats[disease][age_group] = {"Male": 0, "Female": 0}
        
        # Process each encounter
        for encounter in encounters:
            patient = encounter.patient
            encounter_date = encounter.finalized_at.date() if encounter.finalized_at else encounter.created_at.date()
            
            # Get diagnoses for this encounter
            diagnoses = db.query(Diagnosis).filter(
                Diagnosis.encounter_id == encounter.id
            ).all()
            
            # Check if patient is pregnant
            is_pregnant = check_pregnancy_status(diagnoses)
            
            # Determine gender
            gender = "Male" if patient.gender.upper() == "M" else "Female"
            
            # Determine age group
            age_group = get_morbidity_age_group(patient, encounter_date)
            if age_group == "Unknown":
                continue  # Skip if age cannot be determined
            
            # Process each diagnosis
            for diagnosis in diagnoses:
                # Map ICD-10 to morbidity disease
                disease = map_icd10_to_morbidity_disease(
                    diagnosis.icd10 or "",
                    diagnosis.diagnosis or "",
                    is_pregnant
                )
                
                # Update statistics
                if disease in stats and age_group in stats[disease]:
                    stats[disease][age_group][gender] += 1
        
        # Build report data
        report_data = []
        for idx, disease in enumerate(MORBIDITY_DISEASES, start=1):
            disease_stats = stats[disease]
            
            # Calculate totals
            male_totals = {}
            female_totals = {}
            for age_group in age_groups:
                male_totals[age_group] = disease_stats[age_group]["Male"]
                female_totals[age_group] = disease_stats[age_group]["Female"]
            
            male_total = sum(male_totals.values())
            female_total = sum(female_totals.values())
            grand_total = male_total + female_total
            
            report_data.append({
                "sr_no": idx,
                "disease": disease,
                "male_0_28_days": male_totals["0-28 Days"],
                "male_1_11m": male_totals["1 - 11M"],
                "male_1_4": male_totals["1-4"],
                "male_5_9": male_totals["5-9"],
                "male_10_14": male_totals["10-14"],
                "male_15_17": male_totals["15-17"],
                "male_18_19": male_totals["18-19"],
                "male_20_34": male_totals["20-34"],
                "male_35_49": male_totals["35-49"],
                "male_50_59": male_totals["50-59"],
                "male_60_69": male_totals["60-69"],
                "male_70_plus": male_totals["70+"],
                "female_0_28_days": female_totals["0-28 Days"],
                "female_1_11m": female_totals["1 - 11M"],
                "female_1_4": female_totals["1-4"],
                "female_5_9": female_totals["5-9"],
                "female_10_14": female_totals["10-14"],
                "female_15_17": female_totals["15-17"],
                "female_18_19": female_totals["18-19"],
                "female_20_34": female_totals["20-34"],
                "female_35_49": female_totals["35-49"],
                "female_50_59": female_totals["50-59"],
                "female_60_69": female_totals["60-69"],
                "female_70_plus": female_totals["70+"],
                "male_total": male_total,
                "female_total": female_total,
                "grand_total": grand_total
            })
        
        return {
            "data": report_data,
            "start_date": start_date,
            "end_date": end_date,
            "departments": department_list
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/opd-morbidity/export")
def export_opd_morbidity(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    departments: Optional[str] = Query(None, description="Comma-separated list of departments"),
    clinic_name: str = Query("Asesewa Government Hospital", description="Clinic name for header"),
    clinic_city: str = Query("Asesewa", description="Clinic city for header"),
    clinic_region: str = Query("N/A", description="Clinic region for header"),
    clinic_district: str = Query("N/A", description="Clinic district for header"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Records"]))
):
    """
    Export OPD Morbidity Report as Excel file matching DHIMS template format
    """
    try:
        # Get report data
        report_response = get_opd_morbidity(
            start_date=start_date,
            end_date=end_date,
            departments=departments,
            db=db,
            current_user=current_user
        )
        
        report_data = report_response["data"]
        
        # Format dates for header
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_formatted = start.strftime("%d-%m-%Y")
        end_formatted = end.strftime("%d-%m-%Y")
        
        # Get month and year
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month = month_names[start.month - 1]
        year = start.year
        
        # Get current date for report generation
        report_gen_date = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
        
        # Create header rows
        header_rows = [
            [f"MIAM's DHIMS Monthly - Out-Patient Morbidity Returns From {start_formatted} To {end_formatted}", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Clinic : {clinic_name}", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Report Generation Date: {report_gen_date}", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"Month : {month}", None, f"Year : {year}", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [f"District : {clinic_district}", None, f"Location : {clinic_city}", None, f"Region : {clinic_region}", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, "Male", None, None, None, None, None, None, None, None, None, None, None, "Female", None, None, None, None, None, None, None, None, None, None, None, "Total", None, None],
            ["Sr.No.", "Diseases", "0-28 Days (Neonatal)", "1 - 11M (Post Neonatal)", "1-4", "5-9", "10-14", "15-17", "18-19", "20-34", "35-49", "50-59", "60-69", "70+", "0-28 Days (Neonatal)", "1 - 11M (Post Neonatal)", "1-4", "5-9", "10-14", "15-17", "18-19", "20-34", "35-49", "50-59", "60-69", "70+", "Male Total", "Female Total", "Grand Total"]
        ]
        
        # Create data rows
        data_rows = []
        for record in report_data:
            data_rows.append([
                record["sr_no"],
                record["disease"],
                record["male_0_28_days"],
                record["male_1_11m"],
                record["male_1_4"],
                record["male_5_9"],
                record["male_10_14"],
                record["male_15_17"],
                record["male_18_19"],
                record["male_20_34"],
                record["male_35_49"],
                record["male_50_59"],
                record["male_60_69"],
                record["male_70_plus"],
                record["female_0_28_days"],
                record["female_1_11m"],
                record["female_1_4"],
                record["female_5_9"],
                record["female_10_14"],
                record["female_15_17"],
                record["female_18_19"],
                record["female_20_34"],
                record["female_35_49"],
                record["female_50_59"],
                record["female_60_69"],
                record["female_70_plus"],
                record["male_total"],
                record["female_total"],
                record["grand_total"]
            ])
        
        # Add footer rows
        footer_rows = [
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            ["Signature", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            ["Rank", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            ["Date", datetime.now().strftime("%b %d %Y"), None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
        ]
        
        # Combine all rows
        all_rows = header_rows + data_rows + footer_rows
        
        # Create DataFrame
        df = pd.DataFrame(all_rows)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Worksheet', index=False, header=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Worksheet']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        filename = f"OPD_MORBIDITY_{start_formatted.replace('-', '_')}_TO_{end_formatted.replace('-', '_')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting report: {str(e)}"
        )

