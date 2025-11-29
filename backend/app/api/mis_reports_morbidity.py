"""
ICD-10 to Morbidity Disease Mapping for OPD Morbidity Report
This module contains the mapping logic and disease list
"""
from datetime import date

# List of all morbidity diseases in order (as per DHIMS template)
MORBIDITY_DISEASES = [
    "AFP (Polio)",
    "Meningitis",
    "Neo-natal Tetanus",
    "Pertussis (Whooping Cough)",
    "Diphtheria",
    "Measles",
    "Yellow Fever (YF)",
    "Tetanus",
    "Other Oral Conditions",
    "Septiceamia",
    "Traumtic Conditions (Oral and Maxillofacial Region)",
    "Gonorrhoea",
    "Severe Malaria (Lab-Confirmed)",
    "Severe Malaria (Non Lab-Confirmed)",
    "Uncomplicated Malaria Suspected",
    "Uncomplicated Malaria Suspected Tested",
    "Uncomplicated Malaria Suspected Tested Positive",
    "Uncomplicated Malaria tested negative but Treated",
    "Uncomplicated Malaria Not Tested But Treated As Malaria",
    "Typhoid Fever",
    "Diarrhoea Diseases",
    "Viral Hepatitis",
    "Schistosomiasis (Bilharzia)",
    "Onchocerciasis",
    "HIV/AIDS related conditions",
    "Mumps",
    "Intestinal Worms",
    "Chicken Pox",
    "Upper Respiratory tract infection",
    "Pneumonia",
    "Septicaemia",
    "Malnutrition",
    "Obesity",
    "Anaemia",
    "Other Nutritional Diseases",
    "Hypertension",
    "Cardiac Diseases",
    "Stroke",
    "Diabetes Mellitus",
    "Rheumatism / Other Joint Pains / Arthritis",
    "Sickle Cell Disease",
    "Asthma",
    "Chronic Obstructed Pulmonary Disease(COPD)",
    "Breast Cancer",
    "Cervical Cancer",
    "Lymphoma",
    "Prostate cancer",
    "Hepatocellular Carcinoma",
    "All other cancers",
    "Schizophrenia",
    "Acute Psychotic Disorder",
    "Mono symptoms Delusion",
    "Depression",
    "Substance Abuse",
    "Epilepsy",
    "Autism",
    "Mental Retardation",
    "Attention Deficit Hyperactivity Disorder",
    "Conversion Disorders",
    "Post Traumatic Stress Syndrome",
    "Generalized Anxiety",
    "Other Anxiety Disorders",
    "Acute Eye Infection",
    "Cataract",
    "Trachoma",
    "Otitis Media",
    "Other Acute Ear Infection",
    "Dental Caries",
    "Dental Swellings",
    "Tramatic Conditions (Oral and Maxillafacilal region)",
    "Peridontal diseases",
    "Cerebral palsy",
    "Liver diseases",
    "Acute Urinary Tract Infection",
    "Skin Diseases",
    "Ulcers",
    "Kidney Related Diseases",
    "Gynaecological conditions",
    "Pregnancy Related Complications",
    "Anaemia in Pregnancy",
    "Genital Ulcer",
    "Vaginal Discharge",
    "Urethral Discharge",
    "Other Disease of the Male Reproductive System",
    "Other Disease of the Female Reproductive System",
    "Transport injuries",
    "Home injuries",
    "Occupational / Industrial Injuries",
    "Burns",
    "Poisoning",
    "Dog bite",
    "Human bite",
    "Snake bite",
    "Sexual Abuse",
    "Domestic Violence",
    "Pyrexia of unknown origin (PUO)(not Malaria)",
    "Brought in Dead",
    "All Other Cases",
    "Uncomplicated Malaria Suspected In Pregnancy",
    "Uncomplicated Malaria Suspected Tested In Pregnancy",
    "Uncomplicated Malaria Suspected Tested Positive In Pregnancy",
    "Uncomplicated Malaria In Pregnancy tested negative but Treated",
    "Uncomplicated Malaria In Pregnancy Not Tested But Treated As Malaria",
    "Re-Attendance",
    "Referral"
]


def map_icd10_to_morbidity_disease(icd10_code: str, diagnosis_text: str = "", is_pregnant: bool = False) -> str:
    """
    Map ICD-10 code to DHIMS Morbidity Report disease category
    Returns the disease name from the morbidity report list, or "All Other Cases" if not mappable
    """
    if not icd10_code:
        return "All Other Cases"
    
    icd10_upper = icd10_code.upper().strip()
    diagnosis_upper = diagnosis_text.upper() if diagnosis_text else ""
    
    # Malaria-related (check first as it's common)
    if "B50" in icd10_upper or "B51" in icd10_upper or "B52" in icd10_upper or "B53" in icd10_upper or "B54" in icd10_upper:
        if is_pregnant:
            return "Uncomplicated Malaria Suspected In Pregnancy"
        if "severe" in diagnosis_upper or "complicated" in diagnosis_upper:
            return "Severe Malaria (Lab-Confirmed)"  # Default, could be enhanced with lab results
        else:
            return "Uncomplicated Malaria Suspected"
    
    # Typhoid
    if icd10_upper.startswith("A01"):
        return "Typhoid Fever"
    
    # Diarrhoea
    if icd10_upper.startswith("A09") or icd10_upper.startswith("K52") or "R19.7" in icd10_upper:
        return "Diarrhoea Diseases"
    
    # Upper Respiratory tract infection
    if icd10_upper.startswith("J00") or icd10_upper.startswith("J06"):
        return "Upper Respiratory tract infection"
    
    # Pneumonia
    if icd10_upper.startswith("J18") or icd10_upper.startswith("J12") or icd10_upper.startswith("J13") or icd10_upper.startswith("J14") or icd10_upper.startswith("J15") or icd10_upper.startswith("J16") or icd10_upper.startswith("J17"):
        return "Pneumonia"
    
    # Hypertension
    if icd10_upper.startswith("I10") or icd10_upper.startswith("I11") or icd10_upper.startswith("I12") or icd10_upper.startswith("I13") or icd10_upper.startswith("I15") or icd10_upper.startswith("I16"):
        return "Hypertension"
    
    # Diabetes
    if icd10_upper.startswith("E10") or icd10_upper.startswith("E11") or icd10_upper.startswith("E12") or icd10_upper.startswith("E13") or icd10_upper.startswith("E14"):
        return "Diabetes Mellitus"
    
    # Asthma
    if icd10_upper.startswith("J45") or icd10_upper.startswith("J46"):
        return "Asthma"
    
    # Acute Eye Infection
    if icd10_upper.startswith("H10") or icd10_upper.startswith("H11.0"):
        return "Acute Eye Infection"
    
    # Cataract
    if icd10_upper.startswith("H25") or icd10_upper.startswith("H26"):
        return "Cataract"
    
    # Otitis Media
    if icd10_upper.startswith("H65") or icd10_upper.startswith("H66") or icd10_upper.startswith("H67"):
        return "Otitis Media"
    
    # Acute Urinary Tract Infection
    if icd10_upper.startswith("N39.0") or icd10_upper.startswith("N30"):
        return "Acute Urinary Tract Infection"
    
    # Skin Diseases (broad category)
    if icd10_upper.startswith("L"):
        return "Skin Diseases"
    
    # Intestinal Worms
    if icd10_upper.startswith("B76") or icd10_upper.startswith("B77") or icd10_upper.startswith("B78") or icd10_upper.startswith("B79") or icd10_upper.startswith("B80") or icd10_upper.startswith("B81") or icd10_upper.startswith("B83"):
        return "Intestinal Worms"
    
    # Anaemia
    if icd10_upper.startswith("D50") or icd10_upper.startswith("D51") or icd10_upper.startswith("D52") or icd10_upper.startswith("D53"):
        if is_pregnant or "pregnancy" in diagnosis_upper or "pregnant" in diagnosis_upper:
            return "Anaemia in Pregnancy"
        return "Anaemia"
    
    # Epilepsy
    if icd10_upper.startswith("G40") or icd10_upper.startswith("G41"):
        return "Epilepsy"
    
    # Depression
    if icd10_upper.startswith("F32") or icd10_upper.startswith("F33"):
        return "Depression"
    
    # Rheumatism / Arthritis
    if icd10_upper.startswith("M25") or icd10_upper.startswith("M79") or "arthrit" in diagnosis_upper or "rheumat" in diagnosis_upper:
        return "Rheumatism / Other Joint Pains / Arthritis"
    
    # Meningitis
    if icd10_upper.startswith("G00") or icd10_upper.startswith("G01") or icd10_upper.startswith("G02") or icd10_upper.startswith("G03"):
        return "Meningitis"
    
    # Measles
    if icd10_upper.startswith("B05"):
        return "Measles"
    
    # Tetanus
    if icd10_upper.startswith("A35"):
        if "neonatal" in diagnosis_upper or "newborn" in diagnosis_upper:
            return "Neo-natal Tetanus"
        return "Tetanus"
    
    # Pertussis
    if icd10_upper.startswith("A37"):
        return "Pertussis (Whooping Cough)"
    
    # Diphtheria
    if icd10_upper.startswith("A36"):
        return "Diphtheria"
    
    # Viral Hepatitis
    if icd10_upper.startswith("B15") or icd10_upper.startswith("B16") or icd10_upper.startswith("B17") or icd10_upper.startswith("B18") or icd10_upper.startswith("B19"):
        return "Viral Hepatitis"
    
    # HIV/AIDS
    if icd10_upper.startswith("B20") or icd10_upper.startswith("B21") or icd10_upper.startswith("B22") or icd10_upper.startswith("B23") or icd10_upper.startswith("B24") or icd10_upper.startswith("Z21"):
        return "HIV/AIDS related conditions"
    
    # Mumps
    if icd10_upper.startswith("B26"):
        return "Mumps"
    
    # Chicken Pox
    if icd10_upper.startswith("B01"):
        return "Chicken Pox"
    
    # Schistosomiasis
    if icd10_upper.startswith("B65"):
        return "Schistosomiasis (Bilharzia)"
    
    # Onchocerciasis
    if icd10_upper.startswith("B73"):
        return "Onchocerciasis"
    
    # Gonorrhoea
    if icd10_upper.startswith("A54"):
        return "Gonorrhoea"
    
    # Malnutrition
    if icd10_upper.startswith("E40") or icd10_upper.startswith("E41") or icd10_upper.startswith("E42") or icd10_upper.startswith("E43") or icd10_upper.startswith("E44") or icd10_upper.startswith("E45") or icd10_upper.startswith("E46"):
        return "Malnutrition"
    
    # Obesity
    if icd10_upper.startswith("E66"):
        return "Obesity"
    
    # Stroke
    if icd10_upper.startswith("I60") or icd10_upper.startswith("I61") or icd10_upper.startswith("I62") or icd10_upper.startswith("I63") or icd10_upper.startswith("I64") or icd10_upper.startswith("I65") or icd10_upper.startswith("I66") or icd10_upper.startswith("I67") or icd10_upper.startswith("I69"):
        return "Stroke"
    
    # Cardiac Diseases
    if icd10_upper.startswith("I20") or icd10_upper.startswith("I21") or icd10_upper.startswith("I22") or icd10_upper.startswith("I23") or icd10_upper.startswith("I24") or icd10_upper.startswith("I25") or icd10_upper.startswith("I26") or icd10_upper.startswith("I27") or icd10_upper.startswith("I28") or icd10_upper.startswith("I30") or icd10_upper.startswith("I31") or icd10_upper.startswith("I32") or icd10_upper.startswith("I33") or icd10_upper.startswith("I34") or icd10_upper.startswith("I35") or icd10_upper.startswith("I36") or icd10_upper.startswith("I37") or icd10_upper.startswith("I38") or icd10_upper.startswith("I39") or icd10_upper.startswith("I40") or icd10_upper.startswith("I41") or icd10_upper.startswith("I42") or icd10_upper.startswith("I43") or icd10_upper.startswith("I44") or icd10_upper.startswith("I45") or icd10_upper.startswith("I46") or icd10_upper.startswith("I47") or icd10_upper.startswith("I48") or icd10_upper.startswith("I49") or icd10_upper.startswith("I50") or icd10_upper.startswith("I51"):
        return "Cardiac Diseases"
    
    # COPD
    if icd10_upper.startswith("J44"):
        return "Chronic Obstructed Pulmonary Disease(COPD)"
    
    # Sickle Cell
    if icd10_upper.startswith("D57"):
        return "Sickle Cell Disease"
    
    # Cancer categories
    if icd10_upper.startswith("C50"):
        return "Breast Cancer"
    if icd10_upper.startswith("C53"):
        return "Cervical Cancer"
    if icd10_upper.startswith("C81") or icd10_upper.startswith("C82") or icd10_upper.startswith("C83") or icd10_upper.startswith("C84") or icd10_upper.startswith("C85") or icd10_upper.startswith("C86") or icd10_upper.startswith("C88") or icd10_upper.startswith("C90") or icd10_upper.startswith("C91") or icd10_upper.startswith("C92") or icd10_upper.startswith("C93") or icd10_upper.startswith("C94") or icd10_upper.startswith("C95") or icd10_upper.startswith("C96"):
        return "Lymphoma"
    if icd10_upper.startswith("C61"):
        return "Prostate cancer"
    if icd10_upper.startswith("C22"):
        return "Hepatocellular Carcinoma"
    if icd10_upper.startswith("C"):
        return "All other cancers"
    
    # Mental health
    if icd10_upper.startswith("F20"):
        return "Schizophrenia"
    if icd10_upper.startswith("F23"):
        return "Acute Psychotic Disorder"
    if icd10_upper.startswith("F22"):
        return "Mono symptoms Delusion"
    if icd10_upper.startswith("F10") or icd10_upper.startswith("F11") or icd10_upper.startswith("F12") or icd10_upper.startswith("F13") or icd10_upper.startswith("F14") or icd10_upper.startswith("F15") or icd10_upper.startswith("F16") or icd10_upper.startswith("F18") or icd10_upper.startswith("F19"):
        return "Substance Abuse"
    if icd10_upper.startswith("F84.0"):
        return "Autism"
    if icd10_upper.startswith("F70") or icd10_upper.startswith("F71") or icd10_upper.startswith("F72") or icd10_upper.startswith("F73") or icd10_upper.startswith("F78") or icd10_upper.startswith("F79"):
        return "Mental Retardation"
    if icd10_upper.startswith("F90"):
        return "Attention Deficit Hyperactivity Disorder"
    if icd10_upper.startswith("F44"):
        return "Conversion Disorders"
    if icd10_upper.startswith("F43.1"):
        return "Post Traumatic Stress Syndrome"
    if icd10_upper.startswith("F41.1"):
        return "Generalized Anxiety"
    if icd10_upper.startswith("F41"):
        return "Other Anxiety Disorders"
    
    # Dental
    if icd10_upper.startswith("K02"):
        return "Dental Caries"
    if "dental" in diagnosis_upper and ("swelling" in diagnosis_upper or "abscess" in diagnosis_upper):
        return "Dental Swellings"
    if "periodontal" in diagnosis_upper or "gingivitis" in diagnosis_upper:
        return "Peridontal diseases"
    
    # Gynaecological
    if icd10_upper.startswith("N80") or icd10_upper.startswith("N81") or icd10_upper.startswith("N82") or icd10_upper.startswith("N83") or icd10_upper.startswith("N84") or icd10_upper.startswith("N85") or icd10_upper.startswith("N86") or icd10_upper.startswith("N87") or icd10_upper.startswith("N88") or icd10_upper.startswith("N89") or icd10_upper.startswith("N90") or icd10_upper.startswith("N91") or icd10_upper.startswith("N92") or icd10_upper.startswith("N93") or icd10_upper.startswith("N94") or icd10_upper.startswith("N95") or icd10_upper.startswith("N96") or icd10_upper.startswith("N97") or icd10_upper.startswith("N98") or icd10_upper.startswith("N99"):
        return "Gynaecological conditions"
    
    # Pregnancy related
    if icd10_upper.startswith("O"):
        return "Pregnancy Related Complications"
    
    # Genital conditions
    if "genital ulcer" in diagnosis_upper:
        return "Genital Ulcer"
    if "vaginal discharge" in diagnosis_upper or icd10_upper.startswith("N89"):
        return "Vaginal Discharge"
    if "urethral discharge" in diagnosis_upper:
        return "Urethral Discharge"
    
    # Injuries
    if icd10_upper.startswith("V") or icd10_upper.startswith("W") or icd10_upper.startswith("X") or icd10_upper.startswith("Y"):
        if "transport" in diagnosis_upper or "vehicle" in diagnosis_upper or "road" in diagnosis_upper:
            return "Transport injuries"
        elif "home" in diagnosis_upper or "domestic" in diagnosis_upper:
            return "Home injuries"
        elif "occupational" in diagnosis_upper or "industrial" in diagnosis_upper or "work" in diagnosis_upper:
            return "Occupational / Industrial Injuries"
        elif "burn" in diagnosis_upper:
            return "Burns"
        elif "poison" in diagnosis_upper:
            return "Poisoning"
        elif "dog bite" in diagnosis_upper or "dog" in diagnosis_upper:
            return "Dog bite"
        elif "human bite" in diagnosis_upper:
            return "Human bite"
        elif "snake bite" in diagnosis_upper:
            return "Snake bite"
        else:
            return "Home injuries"  # Default for injury codes
    
    # Pyrexia
    if "pyrexia" in diagnosis_upper or ("fever" in diagnosis_upper and "malaria" not in diagnosis_upper):
        return "Pyrexia of unknown origin (PUO)(not Malaria)"
    
    # Default fallback
    return "All Other Cases"


def get_morbidity_age_group(patient, encounter_date: date) -> str:
    """
    Get age group for morbidity report
    Returns: "0-28 Days", "1 - 11M", "1-4", "5-9", "10-14", "15-17", "18-19", "20-34", "35-49", "50-59", "60-69", "70+"
    """
    from datetime import date as date_type
    
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
                return "1 - 11M"
            else:
                return "1-4"
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
            return "70+"
    elif patient.age is not None:
        years = patient.age
        if years < 1:
            return "1 - 11M"
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
            return "70+"
    else:
        return "Unknown"

