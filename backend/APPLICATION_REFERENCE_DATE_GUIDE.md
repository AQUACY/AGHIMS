# Application Reference Date Feature

## Overview

The Application Reference Date feature allows the HMS application to use a fixed reference date instead of the system date. This is particularly useful when:

- **Running alongside an old system**: When an old application requires the system date to be set to a past date (e.g., for license validation), but you want this application to use the actual current date
- The system date is changed for testing or working with historical data
- You need to run an old system while maintaining the original current date
- You want to ensure date-dependent logic uses a consistent date regardless of system date changes

**Key Benefit**: All new database records (patients, encounters, prescriptions, etc.) will use the reference date you set, not the system date. This means you can run the system with an old date for another application while this application continues to work with the correct date.

## How It Works

When `APPLICATION_REFERENCE_DATE` is configured in your `.env` file, the application will:

1. **Backend**: Use the reference date for all date/time operations instead of `datetime.now()`, `datetime.utcnow()`, and `date.today()`
2. **Frontend**: Fetch the application date from the backend API and use it for date comparisons
3. **Database**: New records will use the reference date for timestamps

## Configuration

### Setting the Reference Date

Add the following to your `.env` file:

```bash
# Use a specific date (date only - time will use current system time)
APPLICATION_REFERENCE_DATE=2024-01-15

# Or use a specific date and time
APPLICATION_REFERENCE_DATE=2024-01-15 10:30:00
```

### Disabling the Reference Date

To use the system date (default behavior), either:
- Leave `APPLICATION_REFERENCE_DATE` empty: `APPLICATION_REFERENCE_DATE=`
- Remove the line from your `.env` file

## Usage Examples

### Example 1: Running with Old System Date (Most Common Use Case)

**Scenario**: An old application on the same server requires the system date to be set to 2024-01-01 (e.g., for license validation), but you want this HMS application to use 2024-12-15 (the actual current date) for all its records.

1. Set the system date to the old date (required by the old application):
   ```bash
   sudo date -s "2024-01-01"
   ```

2. Configure this HMS application to use the actual current date:
   ```bash
   # In backend/.env file
   APPLICATION_REFERENCE_DATE=2024-12-15
   ```

3. Restart the HMS application:
   ```bash
   # The HMS application will now:
   # - Use 2024-12-15 for all new database records (patients, encounters, prescriptions, etc.)
   # - Show 2024-12-15 as "today" in the UI
   # - Use 2024-12-15 for all date comparisons
   # - Even though the system date is 2024-01-01
   ```

**Result**: 
- Old application runs with system date 2024-01-01 ✓
- HMS application uses 2024-12-15 for all its operations ✓
- All new HMS records are dated 2024-12-15 ✓

### Example 2: Testing Date-Dependent Features

**Scenario**: You want to test how the application behaves on a specific date without changing the system date.

1. Set the reference date in `.env`:
   ```bash
   APPLICATION_REFERENCE_DATE=2024-06-30
   ```

2. Restart the application - it will behave as if today is June 30, 2024

3. When done testing, remove or clear the setting and restart

## Technical Details

### Backend Implementation

The backend uses `app/core/datetime_utils.py` which provides:

- `now()` - Returns current datetime using reference date if configured
- `utcnow()` - Returns current UTC datetime using reference date if configured
- `today()` - Returns current date using reference date if configured
- `utcnow_callable()` - Callable for SQLAlchemy model defaults

**Key Files Updated:**
- `app/core/config.py` - Added `APPLICATION_REFERENCE_DATE` setting
- `app/core/datetime_utils.py` - Date utility functions
- `app/api/system.py` - API endpoint to expose application date
- `app/api/consultation.py` - Updated to use datetime_utils
- `app/api/patients.py` - Updated to use datetime_utils

### Frontend Implementation

The frontend uses `src/utils/dateUtils.js` which provides:

- `getApplicationDate()` - Async function to get application date from API
- `getApplicationToday()` - Async function to get today's date
- `getApplicationDateSync()` - Synchronous version (uses cache)
- `getApplicationTodaySync()` - Synchronous version for today
- `isTodaySync(date)` - Check if a date is today using application date

**Key Files Updated:**
- `src/services/api.js` - Added `systemAPI.getApplicationDate()` endpoint
- `src/utils/dateUtils.js` - Date utility functions
- `src/pages/Lab.vue` - Updated to use application date
- `src/pages/TreatmentSheet.vue` - Updated to use application date

### API Endpoint

The application exposes the current application date via:

```
GET /api/system/date
```

Response:
```json
{
  "application_datetime": "2024-12-15T10:30:00",
  "application_utc": "2024-12-15T10:30:00Z",
  "application_date": "2024-12-15",
  "system_datetime": "2024-01-01T10:30:00",
  "system_date": "2024-01-01",
  "reference_date_active": true,
  "reference_date": "2024-12-15",
  "using_system_date": false
}
```

## Important Notes

### Date Format

The reference date accepts these formats:
- `YYYY-MM-DD` (e.g., `2024-01-15`) - Date only, time will use current system time
- `YYYY-MM-DD HH:MM:SS` (e.g., `2024-01-15 10:30:00`) - Date and time

### Time Component

When only a date is provided (without time), the application will use the current system time of day. This means:
- The date portion comes from `APPLICATION_REFERENCE_DATE`
- The time portion comes from the system clock

This allows the application to progress through the day normally while using the reference date.

### Cache Behavior

- **Backend**: Reference date is parsed once at startup and cached
- **Frontend**: Application date is fetched from API and cached for 5 minutes

If you change `APPLICATION_REFERENCE_DATE` at runtime, you should restart the application for changes to take effect.

### Database Timestamps

**All database models have been updated** to use `utcnow_callable` from `datetime_utils`. This means:

- ✅ **All new records** (patients, encounters, prescriptions, investigations, bills, etc.) will use the reference date
- ✅ **All timestamps** (created_at, updated_at, service_date, etc.) will use the reference date
- ✅ **No code changes needed** - the models automatically use the reference date

The script `update_models_for_reference_date.py` has been run to update all 40+ model files. All models now import and use `utcnow_callable` instead of `datetime.utcnow`.

### Migration Path

Not all date operations have been migrated to use the reference date. The following have been updated:

**Backend:**
- ✅ `app/api/consultation.py` - All `datetime.utcnow()` and `date.today()` calls
- ✅ `app/api/patients.py` - Date filtering operations

**Frontend:**
- ✅ `src/pages/Lab.vue` - Today's encounter filtering
- ✅ `src/pages/TreatmentSheet.vue` - Date formatting

To migrate additional files, replace:
- `datetime.utcnow()` → `from app.core.datetime_utils import utcnow` then `utcnow()`
- `datetime.now()` → `from app.core.datetime_utils import now` then `now()`
- `date.today()` → `from app.core.datetime_utils import today` then `today()`
- `new Date()` (in frontend) → `getApplicationDateSync()` or `getApplicationTodaySync()`

## Troubleshooting

### Application Still Using System Date

1. Check that `APPLICATION_REFERENCE_DATE` is set in `.env`
2. Verify the format is correct (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
3. Restart the application after changing the setting
4. Check application logs for any date parsing errors

### Frontend Not Using Reference Date

1. Check browser console for API errors
2. Verify `/api/system/date` endpoint is accessible
3. Clear browser cache if needed
4. Check that frontend files are using `dateUtils` functions

### Date Comparisons Not Working

If date comparisons aren't working as expected:
1. Ensure the code is using `datetime_utils` functions (backend) or `dateUtils` functions (frontend)
2. Check that dates are being normalized (hours set to 0 for date-only comparisons)
3. Verify the reference date format is correct

## Best Practices

1. **Documentation**: Document when and why you're using a reference date
2. **Testing**: Test thoroughly when using a reference date, especially date-dependent features
3. **Reset**: Always reset `APPLICATION_REFERENCE_DATE` to empty after testing
4. **Backups**: Consider backing up data before working with historical dates
5. **Monitoring**: Monitor application behavior when using reference dates

## Related Documentation

- `VM_DEPLOYMENT_GUIDE.md` - Information about date management on VMs
- `SET_OLD_DATE.sh` - Script to set system date to old date
- `RESET_DATE.sh` - Script to reset system date to current

