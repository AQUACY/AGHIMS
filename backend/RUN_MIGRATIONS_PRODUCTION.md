# Running Migrations in Production

## Quick Start

You need to run **two migrations** to fix the current errors:

1. `migrate_add_patient_other_names_mysql.py` - Adds `other_names` column to `patients` table
2. `migrate_add_discharge_fields_mysql.py` - Adds discharge fields to `ward_admissions` table

## Method 1: Using Python Scripts (Recommended)

### Step 1: SSH into your production server
```bash
ssh your-user@your-production-server
cd /path/to/your/backend
```

### Step 2: Set environment variables (if not already set)
```bash
export DB_HOST=your-db-host
export DB_PORT=3306
export DB_NAME=your-database-name
export DB_USER=your-db-user
export DB_PASSWORD=your-db-password
```

### Step 3: Run the migrations
```bash
# Run both migrations
python migrate_add_patient_other_names_mysql.py
python migrate_add_discharge_fields_mysql.py
```

Or use the centralized migration runner:
```bash
python run_migrations.py
```

## Method 2: Using MySQL Command Line

### Step 1: Connect to MySQL
```bash
mysql -h your-db-host -u your-db-user -p your-database-name
```

### Step 2: Run the SQL commands

```sql
-- Add other_names to patients table
ALTER TABLE patients ADD COLUMN other_names VARCHAR(255) NULL;

-- Add discharge fields to ward_admissions table
ALTER TABLE ward_admissions ADD COLUMN discharge_outcome VARCHAR(50) NULL;
ALTER TABLE ward_admissions ADD COLUMN discharge_condition VARCHAR(50) NULL;
ALTER TABLE ward_admissions ADD COLUMN partially_discharged_at DATETIME NULL;
ALTER TABLE ward_admissions ADD COLUMN partially_discharged_by INT NULL;
ALTER TABLE ward_admissions ADD COLUMN final_orders TEXT NULL;

-- Optional: Add foreign key constraint (can skip if you get constraint name conflicts)
-- ALTER TABLE ward_admissions
-- ADD CONSTRAINT fk_ward_admissions_partially_discharged_by
-- FOREIGN KEY (partially_discharged_by) REFERENCES users(id);
```

### Step 3: Verify the columns were added
```sql
-- Check patients table
DESCRIBE patients;

-- Check ward_admissions table
DESCRIBE ward_admissions;
```

## Method 3: Using a Database GUI Tool

If you use phpMyAdmin, MySQL Workbench, or another GUI tool:

1. Connect to your production database
2. Select your database
3. Go to the SQL tab/query editor
4. Copy and paste the SQL from `migrate_add_discharge_fields_mysql.sql`
5. Execute the statements

## Verification

After running the migrations, verify the columns exist:

```sql
-- Check if other_names exists in patients
SELECT COLUMN_NAME 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'your-database-name' 
  AND TABLE_NAME = 'patients' 
  AND COLUMN_NAME = 'other_names';

-- Check if discharge fields exist in ward_admissions
SELECT COLUMN_NAME 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'your-database-name' 
  AND TABLE_NAME = 'ward_admissions' 
  AND COLUMN_NAME IN ('discharge_outcome', 'discharge_condition', 'partially_discharged_at', 'partially_discharged_by', 'final_orders');
```

## Troubleshooting

### Error: "Column already exists"
- This is fine! The migration scripts check for existing columns and skip them.
- Your database is already up to date for that column.

### Error: "Table does not exist"
- Make sure you're connected to the correct database.
- Verify the table name matches exactly (case-sensitive in some MySQL configurations).

### Error: "Access denied"
- Check your database user has ALTER TABLE permissions.
- You may need to run as a user with higher privileges.

### Error: "Foreign key constraint fails"
- The foreign key constraint for `partially_discharged_by` is optional.
- If it fails, you can skip it - the column will still work without the constraint.

## Important Notes

- **Always backup your database before running migrations!**
- The migrations are idempotent (safe to run multiple times).
- They check if columns exist before adding them.
- All new columns are nullable, so existing data won't be affected.

