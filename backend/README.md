# Hospital Management System (HMS) Backend

A lightweight Hospital Management System backend focused on OPD (Outpatient Department) clients, designed for quick billing and NHIA ClaimIT XML export.

## Quick Start

- **Development Setup**: Follow the [Setup](#setup) section below
- **Production Deployment**: See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive production deployment guide with MySQL

## Features

- **Patient Management**: Register and manage patients with automatic card number generation
- **Encounter Management**: Track patient encounters through workflow stages
- **Vitals Module**: Record and update patient vitals
- **Consultation Module**: Add diagnoses, prescriptions, and request investigations
- **Billing Module**: Generate bills based on price lists with automatic insurance/cash pricing
- **Service Confirmation**: Lab, pharmacy, and other services confirm requests before billing
- **Claims Management**: Generate, finalize, and export NHIA ClaimIT-compatible XML files
- **Price List Upload**: Upload Excel files for surgery, procedures, products, consumables, and DRG prices
- **Authentication & Authorization**: JWT-based auth with role-based access control

## Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Edit `.env` and configure:
   - `DATABASE_URL`: Database connection string (default: SQLite)
   - `SECRET_KEY`: Secret key for JWT tokens
   - `FACILITY_CODE`: Facility code for card numbers (e.g., ER-A25)

6. Initialize the database:
```bash
python init_db.py
```

This will create all database tables and a default admin user:
- Username: `admin`
- Password: `admin123`
**Change the admin password immediately in production!**

## Running the Server

### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info

### Patients
- `POST /api/patients` - Register new patient
- `GET /api/patients/card/{card_number}` - Get patient by card number
- `PUT /api/patients/{patient_id}` - Update patient
- `POST /api/patients/{patient_id}/encounter` - Create encounter

### Encounters
- `GET /api/encounters/{encounter_id}` - Get encounter
- `PUT /api/encounters/{encounter_id}/status` - Update encounter status
- `GET /api/encounters/patient/{patient_id}` - Get patient encounters

### Vitals
- `POST /api/vitals` - Record vitals
- `GET /api/vitals/encounter/{encounter_id}` - Get encounter vitals

### Consultation
- `POST /api/consultation/diagnosis` - Add diagnosis
- `GET /api/consultation/diagnosis/encounter/{encounter_id}` - Get diagnoses
- `POST /api/consultation/prescription` - Add prescription
- `GET /api/consultation/prescription/encounter/{encounter_id}` - Get prescriptions
- `POST /api/consultation/investigation` - Request investigation
- `PUT /api/consultation/investigation/{investigation_id}/confirm` - Confirm investigation

### Billing
- `POST /api/billing` - Create bill
- `POST /api/billing/receipt` - Create receipt
- `GET /api/billing/encounter/{encounter_id}` - Get encounter bills

### Claims
- `POST /api/claims` - Create claim
- `PUT /api/claims/{claim_id}/finalize` - Finalize claim
- `PUT /api/claims/{claim_id}/reopen` - Reopen claim
- `GET /api/claims/export/{claim_id}` - Export claim as XML
- `GET /api/claims/export/date-range` - Export claims by date range

### Price List
- `POST /api/price-list/upload/{category}` - Upload price list file
- `GET /api/price-list/search` - Search price items

## Workflow

1. **Records**: Register patient (generates card number) → Create encounter (generates CCC number)
2. **Nurse**: Record vitals (updates encounter from draft)
3. **Doctor**: Add diagnoses, prescriptions, request investigations → Mark encounter finalized
4. **Service Units**: Confirm investigations (lab/scan/x-ray)
5. **Billing**: Generate bills from confirmed services → Create receipts on payment
6. **Claims**: Create claim from finalized encounter → Finalize → Export XML

## Price List Upload

Price list Excel files should have the following columns:
- `item_code` - Item code (e.g., medicine code, procedure code)
- `item_name` - Item name
- `insured_price` - NHIA rate (for insured patients)
- `cash_price` - Cash price (for non-insured patients)

The `category` column is optional as it's determined by the upload endpoint path parameter.

Supported categories:
- `surgery` - Surgery price list
- `procedure` - Procedure price list
- `product` - Product/prescription price list
- `consumable` - Consumables price list
- `drg` - Unmapped DRG price list (diagnosis)

## Card Number Format

Card numbers follow the format: `{FACILITY_CODE}-{LETTERS}{NUMBER}`
- Example: `ER-A25-AAA0001`, `ER-A25-AAA0002`, ..., `ER-A25-ZZZ9999`

## CCC Number Format

CCC numbers are 5-digit numbers unique per day and reset daily:
- Example: `00001`, `00002`, ..., `99999`

## Claim XML Export

The system exports NHIA ClaimIT-compatible XML files with the following structure:
- Root element: `<claims>`
- Each claim in `<claim>` element
- Includes patient info, diagnoses, investigations, medicines, procedures
- Compatible with ClaimIT import format

## Roles

- **Records**: Patient registration, encounter creation
- **Nurse**: Vitals recording
- **Doctor**: Diagnosis, prescriptions, investigations, encounter finalization
- **Billing**: Bill creation, receipt generation
- **Pharmacist**: Dispense prescriptions (when implemented)
- **Lab**: Confirm lab investigations
- **Claims**: Claim creation, finalization, XML export
- **Admin**: Full access

## Database

By default, the system uses SQLite (`hms.db`) for development. **For production, use MySQL** as documented in [DEPLOYMENT.md](./DEPLOYMENT.md).

Database tables are automatically created on first run.

### Database Migrations

When deploying updates to production that include schema changes, you need to run migration scripts before starting the updated application.

**Important**: Always backup your production database before running migrations!

#### Migration Scripts Available

- `migrate_add_prescription_confirmation.py` - Adds `confirmed_by` and `confirmed_at` columns to prescriptions table (for pharmacy confirmation workflow)

#### Running Migrations

1. **Backup your database** (critical step!)
2. Run the migration script:
   ```bash
   python migrate_add_prescription_confirmation.py
   ```
3. Verify the migration completed successfully
4. Restart your application

For new installations, migrations are not needed as `init_db.py` creates all tables with the latest schema.

#### Production Migration Checklist

- [ ] Backup production database
- [ ] Run appropriate migration script(s)
- [ ] Verify migration success
- [ ] Deploy updated application code
- [ ] Restart application server
- [ ] Test critical workflows
- [ ] Monitor for errors

## Production Deployment

For production deployment with MySQL, comprehensive installation and setup instructions are available in [DEPLOYMENT.md](./DEPLOYMENT.md).

The deployment guide covers:
- MySQL database setup
- Production configuration
- Systemd service configuration
- Reverse proxy setup (Nginx)
- Backup and maintenance procedures
- Security best practices
- Troubleshooting

## Notes

- All encounters must have all bills paid before finalization
- Claims can only be created from finalized encounters
- XML exports are only available for finalized claims
- Price lists determine pricing (insured vs cash) automatically based on patient insurance status

