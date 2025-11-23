# Fix MySQL Startup Errors

## Problem
MySQL service fails to start: "the control process exited with error code"

## Step 1: Check Error Logs

```bash
# Check systemd logs
sudo journalctl -u mysql -n 50 --no-pager

# Check MySQL error log
sudo tail -50 /var/log/mysql/error.log
# OR
sudo tail -50 /var/log/mysqld.log
```

## Common Errors and Fixes

### Error 1: Permission Denied on Data Directory

**Error:** `Can't create/write to file '/var/lib/mysql/...' (Errcode: 13)`

**Fix:**
```bash
sudo chown -R mysql:mysql /var/lib/mysql
sudo chmod -R 755 /var/lib/mysql
sudo systemctl start mysql
```

### Error 2: Data Directory Not Found

**Error:** `datadir is set to /var/lib/mysql, but the directory does not exist`

**Fix:**
```bash
sudo mkdir -p /var/lib/mysql
sudo chown -R mysql:mysql /var/lib/mysql
sudo systemctl start mysql
```

### Error 3: MySQL Not Initialized

**Error:** `[ERROR] [MY-010119] [Server] Aborting`

**Fix:**
```bash
# For MySQL 5.7 and earlier
sudo mysql_install_db --user=mysql --datadir=/var/lib/mysql

# For MySQL 8.0+
sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql

# Then start
sudo systemctl start mysql
```

### Error 4: Port Already in Use

**Error:** `Can't start server: Bind on TCP/IP port: Address already in use`

**Fix:**
```bash
# Find what's using port 3306
sudo lsof -i :3306
# OR
sudo netstat -tlnp | grep 3306

# Kill the process if needed
sudo kill -9 <PID>

# Or change MySQL port in /etc/mysql/mysql.conf.d/mysqld.cnf
```

### Error 5: Corrupted Database

**Error:** `InnoDB: Database was not shut down normally`

**Fix:**
```bash
# Try to repair (BE CAREFUL - backup first!)
sudo systemctl stop mysql
sudo mysqld_safe --skip-grant-tables &
# Then repair tables
mysqlcheck --all-databases --repair
sudo systemctl start mysql
```

## Quick Diagnostic

Run the diagnostic script:

```bash
cd /home/administrator/Desktop/AGHIMS/backend
./DIAGNOSE_MYSQL_STARTUP.sh
```

This will show you:
- Service status
- Error logs
- Configuration issues
- Permission problems
- Port conflicts

## Most Common Fix

Usually it's a permission issue:

```bash
# Fix ownership
sudo chown -R mysql:mysql /var/lib/mysql

# Fix permissions
sudo chmod -R 755 /var/lib/mysql

# Start MySQL
sudo systemctl start mysql

# Check status
sudo systemctl status mysql
```

## If MySQL Was Never Initialized

If this is a fresh MySQL installation:

```bash
# For MySQL 8.0+
sudo mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql

# Set root password (optional but recommended)
sudo systemctl start mysql
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';"
```

## After Fixing

Once MySQL starts:

```bash
# Verify it's running
sudo systemctl status mysql

# Test connection
mysql -u root -p

# Restart your backend
sudo systemctl restart hms-api
```

