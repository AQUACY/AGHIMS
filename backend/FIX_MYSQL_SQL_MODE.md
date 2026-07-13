# Fix MySQL sql_mode Error

## Problem
MySQL fails to start with error:
```
ERROR [MY-000077] [Server] /usr/sbin/mysqld: Error while setting value 'NO_ENGINE_SUBSTITUTION,NO_AUTO_CREATE_USER' to 'sql_mode'.
```

## Cause
The `NO_AUTO_CREATE_USER` SQL mode was **removed in MySQL 8.0**. If your config file still has this mode, MySQL will fail to start.

## Quick Fix

### Option 1: Use the Fix Script (Recommended)

```bash
cd /home/administrator/Desktop/AGHIMS/backend
./FIX_MYSQL_SQL_MODE.sh
```

### Option 2: Manual Fix

#### Step 1: Find MySQL Config File

```bash
# Usually one of these:
/etc/mysql/mysql.conf.d/mysqld.cnf
/etc/mysql/my.cnf
/etc/my.cnf
```

#### Step 2: Backup Config File

```bash
sudo cp /etc/mysql/mysql.conf.d/mysqld.cnf /etc/mysql/mysql.conf.d/mysqld.cnf.backup
```

#### Step 3: Edit Config File

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

#### Step 4: Find and Fix sql_mode

Look for a line like:
```ini
sql_mode = "NO_ENGINE_SUBSTITUTION,NO_AUTO_CREATE_USER"
```

Change it to:
```ini
sql_mode = "NO_ENGINE_SUBSTITUTION"
```

**OR** if you want to use MySQL 8.0 defaults, remove the line entirely or comment it out:
```ini
# sql_mode = "NO_ENGINE_SUBSTITUTION,NO_AUTO_CREATE_USER"
```

#### Step 5: Save and Start MySQL

```bash
# Save the file (Ctrl+X, then Y, then Enter in nano)

# Start MySQL
sudo systemctl start mysql

# Check status
sudo systemctl status mysql
```

### Option 3: Quick Command Fix

```bash
# Find and fix in one command
sudo sed -i.bak 's/NO_AUTO_CREATE_USER,//g' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo sed -i.bak 's/,NO_AUTO_CREATE_USER//g' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo sed -i.bak 's/NO_AUTO_CREATE_USER//g' /etc/mysql/mysql.conf.d/mysqld.cnf

# Clean up double commas
sudo sed -i.bak 's/,,/,/g' /etc/mysql/mysql.conf.d/mysqld.cnf

# Start MySQL
sudo systemctl start mysql
```

## Verify Fix

```bash
# Check MySQL is running
sudo systemctl status mysql

# Test connection
mysql -u root -p -e "SELECT @@sql_mode;"
```

You should see `sql_mode` without `NO_AUTO_CREATE_USER`.

## After Fixing

Once MySQL starts:

```bash
# Restart your backend
sudo systemctl restart hms-api

# Verify backend is running
sudo systemctl status hms-api
```

## Why This Happened

When you installed `mysql-client`, it might have updated MySQL configuration files or you might have upgraded from MySQL 5.7 to 8.0. The `NO_AUTO_CREATE_USER` mode was deprecated and removed in MySQL 8.0 because user creation is now handled differently.

