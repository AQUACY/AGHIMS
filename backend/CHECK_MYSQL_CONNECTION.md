# Checking MySQL Connection Issues

## Problem
Backend can't connect to MySQL: `Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)`

## Quick Diagnosis

### 1. Check if MySQL is Running

```bash
# Check MySQL service status
sudo systemctl status mysql
# OR
sudo systemctl status mysqld
```

### 2. Start MySQL if Not Running

```bash
# Ubuntu/Debian
sudo systemctl start mysql

# CentOS/RHEL
sudo systemctl start mysqld

# Enable to start on boot
sudo systemctl enable mysql
# OR
sudo systemctl enable mysqld
```

### 3. Check MySQL Configuration

Verify your `.env` file has correct MySQL settings:

```bash
cd /home/administrator/Desktop/AGHIMS/backend
cat .env | grep MYSQL
```

Should show:
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=hms
```

### 4. Test MySQL Connection Manually

```bash
# Test connection
mysql -h localhost -P 3306 -u your_username -p your_database

# If that works, check if database exists
mysql -h localhost -u your_username -p -e "SHOW DATABASES;"
```

### 5. Check MySQL is Listening

```bash
# Check if MySQL is listening on port 3306
sudo netstat -tlnp | grep 3306
# OR
sudo ss -tlnp | grep 3306
```

### 6. Check MySQL Error Log

```bash
# Ubuntu/Debian
sudo tail -50 /var/log/mysql/error.log

# CentOS/RHEL
sudo tail -50 /var/log/mysqld.log
```

## Common Issues

### Issue 1: MySQL Not Running

**Solution:**
```bash
sudo systemctl start mysql
sudo systemctl enable mysql  # Start on boot
```

### Issue 2: Wrong Host in Configuration

If MySQL is on a different server, update `.env`:
```
MYSQL_HOST=10.10.16.50  # Or whatever your MySQL server IP is
```

### Issue 3: MySQL Not Listening on localhost

Check MySQL bind address:
```bash
sudo grep bind-address /etc/mysql/mysql.conf.d/mysqld.cnf
```

Should be:
```
bind-address = 127.0.0.1
# OR
bind-address = 0.0.0.0  # To allow remote connections
```

### Issue 4: Firewall Blocking

```bash
# Check if port 3306 is open
sudo ufw status | grep 3306
# OR
sudo iptables -L | grep 3306
```

## Quick Fix Script

```bash
#!/bin/bash
# Quick MySQL connection check

echo "Checking MySQL status..."
sudo systemctl status mysql --no-pager | head -5

echo ""
echo "Checking if MySQL is listening..."
sudo netstat -tlnp | grep 3306 || echo "MySQL is NOT listening on port 3306"

echo ""
echo "Testing connection..."
mysql -h localhost -u root -p -e "SELECT 1;" 2>&1 | head -3
```

## After Fixing

Once MySQL is running:

```bash
# Restart your backend
sudo systemctl restart hms-api

# Check status
sudo systemctl status hms-api
```

