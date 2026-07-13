# Database Sync Setup Guide

This guide will help you set up online database synchronization to backup your production database to a remote MySQL server.

## Prerequisites - Install New Dependencies

**IMPORTANT**: Before setting up database sync, ensure you have installed the required dependencies.

### Install APScheduler (Required for Scheduled Backups)

```bash
# Navigate to backend directory
cd backend

# Install APScheduler
pip install apscheduler>=3.10.4
```

**Python Version Requirement**: APScheduler requires Python 3.7 or higher.

Check your Python version:
```bash
python --version
```

If you have an older Python version, upgrade first.

**For detailed installation instructions and troubleshooting, see [INSTALL_NEW_DEPENDENCIES.md](./INSTALL_NEW_DEPENDENCIES.md)**

## Overview

The database sync feature allows you to automatically backup your production database to a remote MySQL server. This provides:
- **Disaster Recovery**: If your production server crashes, you can restore from the online backup
- **Automatic Backups**: Scheduled syncs ensure your online backup is always up-to-date
- **Data Safety**: Your data is stored in two locations (production + online backup)

## Additional Prerequisites

1. **Remote MySQL Server**: You need access to a MySQL server (can be on a cloud provider like AWS RDS, DigitalOcean, or a VPS)
2. **Network Access**: Your production server must be able to connect to the remote MySQL server
3. **MySQL Client Tools**: The production server needs `mysqldump` and `mysql` commands installed
4. **Python Dependencies**: Ensure APScheduler is installed (see Prerequisites section above)

## Step 1: Set Up Remote MySQL Database

### Option A: Cloud MySQL Service (Recommended)

#### AWS RDS
1. Create an RDS MySQL instance
2. Note the endpoint, port, username, and password
3. Ensure security group allows connections from your production server IP

#### DigitalOcean Managed Database
1. Create a MySQL database cluster
2. Note the connection details
3. Add your production server IP to trusted sources

#### Other Cloud Providers
Follow your provider's documentation to create a MySQL database instance.

### Option B: Self-Hosted MySQL Server

If you have your own MySQL server:

1. **Create Database**:
   ```sql
   CREATE DATABASE hms_backup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Create User** (if needed):
   ```sql
   CREATE USER 'hms_sync'@'%' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON hms_backup.* TO 'hms_sync'@'%';
   FLUSH PRIVILEGES;
   ```

3. **Configure Firewall**: Allow connections from your production server IP on port 3306

## Step 2: Test Connection from Production Server

Test that your production server can connect to the remote MySQL:

```bash
# Test connection
mysql -h YOUR_REMOTE_HOST -P 3306 -u YOUR_USERNAME -p YOUR_DATABASE

# If connection succeeds, you're ready to proceed
```

## Step 3: Configure Environment Variables

Add the following to your production server's `.env` file:

```env
# Online Sync Settings
SYNC_ENABLED=true
SYNC_REMOTE_HOST=your-remote-mysql-host.com
SYNC_REMOTE_PORT=3306
SYNC_REMOTE_USER=your_username
SYNC_REMOTE_PASSWORD=your_secure_password
SYNC_REMOTE_DATABASE=hms_backup
SYNC_INTERVAL_MINUTES=60
```

### Configuration Options

- **SYNC_ENABLED**: Set to `true` to enable online sync
- **SYNC_REMOTE_HOST**: IP address or hostname of your remote MySQL server
- **SYNC_REMOTE_PORT**: MySQL port (usually 3306)
- **SYNC_REMOTE_USER**: MySQL username with access to the database
- **SYNC_REMOTE_PASSWORD**: MySQL password
- **SYNC_REMOTE_DATABASE**: Name of the database to sync to (e.g., `hms_backup`)
- **SYNC_INTERVAL_MINUTES**: How often to sync (default: 60 minutes)

## Step 4: Install MySQL Client Tools (if needed)

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install mysql-client
```

### CentOS/RHEL
```bash
sudo yum install mysql
```

### Windows
Download MySQL Installer and install MySQL Client only.

## Step 5: Restart Application

After updating the `.env` file, restart your application:

```bash
# If using systemd
sudo systemctl restart hms-api

# Or if running manually
# Stop the current process and restart
```

## Step 6: Verify Sync is Working

1. **Check Application Logs**:
   ```bash
   # Check if sync service started
   tail -f /var/log/hms/app.log | grep -i sync
   ```

2. **Test Connection via UI**:
   - Navigate to Admin → Database Management
   - Click "Test Connection" in the Online Database Sync section
   - You should see "Connection test successful"

3. **Run Manual Sync**:
   - Click "Sync Now" in the Database Management page
   - Check the notification for success message

4. **Verify Data in Remote Database**:
   ```bash
   mysql -h YOUR_REMOTE_HOST -u YOUR_USERNAME -p YOUR_DATABASE
   mysql> SHOW TABLES;
   mysql> SELECT COUNT(*) FROM patients;
   ```

## How Sync Works

1. **Initial Sync**: On first sync, all tables are created in the remote database
2. **Incremental Sync**: Subsequent syncs update existing records and add new ones
3. **Scheduled Sync**: Automatic syncs run at the configured interval
4. **Manual Sync**: You can trigger syncs manually from the Database Management page

## Monitoring Sync Status

### Via UI
- Navigate to Admin → Database Management
- Check the "Online Database Sync" section for connection status

### Via Logs
```bash
# View sync logs
grep -i "sync" /var/log/hms/app.log

# View recent sync activity
tail -f /var/log/hms/app.log | grep -i "database sync"
```

## Troubleshooting

### Connection Refused
- **Check Firewall**: Ensure port 3306 is open on the remote server
- **Check MySQL Bind Address**: Ensure MySQL is listening on the correct interface
- **Check Security Groups**: If using cloud services, verify security group rules

### Authentication Failed
- **Verify Credentials**: Double-check username and password in `.env`
- **Check User Permissions**: Ensure the MySQL user has proper privileges
- **Check User Host**: Verify the user can connect from your production server IP

### Sync Fails Silently
- **Check Logs**: Review application logs for error messages
- **Test Connection**: Use the "Test Connection" button in the UI
- **Verify MySQL Client**: Ensure `mysqldump` and `mysql` commands are available

### Tables Not Created
- **Check Permissions**: User needs CREATE TABLE permission
- **Check Database**: Ensure the database exists and user has access
- **Review Logs**: Check for specific error messages

## Security Best Practices

1. **Use Strong Passwords**: Generate secure passwords for MySQL users
2. **Limit Network Access**: Only allow connections from your production server IP
3. **Use SSL/TLS**: Configure MySQL to use encrypted connections (if supported)
4. **Regular Backups**: Even with online sync, maintain local backups
5. **Monitor Access**: Regularly review MySQL access logs

## Restoring from Online Backup

If you need to restore from the online backup:

1. **Export from Remote Database**:
   ```bash
   mysqldump -h YOUR_REMOTE_HOST -u YOUR_USERNAME -p YOUR_DATABASE > restore.sql
   ```

2. **Import to Production**:
   ```bash
   mysql -u YOUR_USER -p YOUR_DATABASE < restore.sql
   ```

   Or use the Database Management UI:
   - Export backup from remote database
   - Use "Import Backup" in the Database Management page

## Backup Schedule

The sync runs automatically at the configured interval. You can also:
- **Manual Sync**: Trigger syncs manually from the UI
- **Scheduled Backups**: Configure local backups to run at specific times
- **Combined Approach**: Use both scheduled local backups and online sync for maximum safety

## Cost Considerations

- **Cloud Database**: Most cloud providers charge for database instances (typically $10-50/month)
- **Bandwidth**: Sync operations use bandwidth; monitor usage if on metered connections
- **Storage**: Remote database storage costs depend on data size

## Support

For issues or questions:
1. Check application logs
2. Review this guide
3. Test MySQL connection manually
4. Verify environment variables are correct

