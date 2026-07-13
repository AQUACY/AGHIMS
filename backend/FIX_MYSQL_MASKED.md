# Fix MySQL Service Masked Issue

## Problem
MySQL service is masked: `Unit mysql.service is masked`

This means the service is disabled and prevented from starting.

## Solution

### Step 1: Unmask MySQL Service

```bash
sudo systemctl unmask mysql
```

### Step 2: Enable MySQL Service

```bash
sudo systemctl enable mysql
```

### Step 3: Start MySQL Service

```bash
sudo systemctl start mysql
```

### Step 4: Verify MySQL is Running

```bash
sudo systemctl status mysql
```

You should see: `Active: active (running)`

## Alternative: If mysql.service doesn't exist

Sometimes MySQL uses a different service name:

```bash
# Try mysqld instead
sudo systemctl unmask mysqld
sudo systemctl enable mysqld
sudo systemctl start mysqld
sudo systemctl status mysqld
```

## Check Available MySQL Services

```bash
# List all MySQL-related services
systemctl list-unit-files | grep mysql

# You might see:
# mysql.service
# mysqld.service
# mysql@.service
```

## If MySQL is Installed via Different Method

If MySQL was installed via MySQL APT repository, it might use a different service:

```bash
# Check for MySQL 8.0
sudo systemctl unmask mysql@bootstrap
sudo systemctl enable mysql@bootstrap
sudo systemctl start mysql@bootstrap
```

## Quick Fix Script

```bash
#!/bin/bash
# Unmask and start MySQL

echo "Unmasking MySQL service..."
sudo systemctl unmask mysql 2>/dev/null || sudo systemctl unmask mysqld 2>/dev/null

echo "Enabling MySQL service..."
sudo systemctl enable mysql 2>/dev/null || sudo systemctl enable mysqld 2>/dev/null

echo "Starting MySQL service..."
sudo systemctl start mysql 2>/dev/null || sudo systemctl start mysqld 2>/dev/null

echo "Checking status..."
sudo systemctl status mysql --no-pager 2>/dev/null || sudo systemctl status mysqld --no-pager 2>/dev/null | head -10
```

## After Fixing

Once MySQL is running:

```bash
# Restart your backend
sudo systemctl restart hms-api

# Verify backend is running
sudo systemctl status hms-api
```

## Why This Happens

Installing `mysql-client` might have masked the MySQL server service to prevent conflicts. The client tools don't require the server to be running, but your application does.

