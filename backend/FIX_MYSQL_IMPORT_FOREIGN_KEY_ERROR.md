# Fix MySQL Import Foreign Key Constraint Error

## Problem

When importing a MySQL backup, you get an error like:
```
ERROR 3730 (HY000): Cannot drop table 'additional_services' referenced by a foreign key constraint 
'inpatient_additional_services_ibfk_3' on table 'inpatient_additional_services'.
```

## Cause

MySQL backups often contain `DROP TABLE` statements that try to drop tables in an order that violates foreign key constraints. When a table is referenced by another table's foreign key, MySQL prevents dropping it until the referencing table is dropped first.

## Solution

The database backup service has been updated to automatically:
1. **Disable foreign key checks** before import (`SET FOREIGN_KEY_CHECKS=0;`)
2. **Import the SQL file** (tables can now be dropped in any order)
3. **Re-enable foreign key checks** after import (`SET FOREIGN_KEY_CHECKS=1;`)

This is handled automatically in the import process.

## Manual Fix (If Needed)

If you need to manually import a backup file:

### Option 1: Using mysql command line

```bash
# Disable foreign key checks, import, then re-enable
mysql -u hms_user -p hms << EOF
SET FOREIGN_KEY_CHECKS=0;
SOURCE /path/to/backup.sql;
SET FOREIGN_KEY_CHECKS=1;
EOF
```

### Option 2: Modify SQL file before import

```bash
# Add commands to beginning and end of SQL file
echo "SET FOREIGN_KEY_CHECKS=0;" | cat - backup.sql > temp.sql
echo "SET FOREIGN_KEY_CHECKS=1;" >> temp.sql

# Import modified file
mysql -u hms_user -p hms < temp.sql
```

### Option 3: Using Python fallback

If `mysql` command is not available, the Python fallback method also handles this automatically.

## Verification

After import, verify foreign keys are working:

```sql
-- Check foreign key constraints
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'hms'
AND REFERENCED_TABLE_NAME IS NOT NULL;
```

## Additional Safety Features

The updated import process also:
- Sets `SQL_MODE='NO_AUTO_VALUE_ON_ZERO'` for compatibility
- Wraps import in a transaction for atomicity
- Creates a pre-restore backup automatically
- Filters out password warnings from error messages

## Troubleshooting

### Issue: Still getting foreign key errors

**Solution**: Check if the SQL file has syntax errors or is corrupted:
```bash
# Test SQL file syntax
mysql -u hms_user -p hms --force < backup.sql 2>&1 | grep -i error
```

### Issue: Import succeeds but foreign keys are missing

**Solution**: The backup might not include foreign key definitions. Check the backup file:
```bash
grep -i "FOREIGN KEY" backup.sql
```

If missing, you may need to recreate foreign keys manually or use a backup that includes them.

### Issue: Import is very slow

**Solution**: For large databases, consider:
1. Disabling indexes during import
2. Using `--single-transaction` flag (if using mysqldump)
3. Importing during off-peak hours

## Best Practices

1. **Always backup before importing**: The import process creates a pre-restore backup automatically
2. **Test imports on a development server first**
3. **Verify data integrity after import**: Check record counts, run integrity checks
4. **Use compressed backups**: They're faster to transfer and import

## Related Files

- `backend/app/services/database_backup.py` - Contains the import logic
- `backend/app/api/database_management.py` - API endpoints for backup/restore

