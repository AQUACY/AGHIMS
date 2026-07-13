# VM Deployment Guide - Running HMS with Date Control

This guide covers deploying the HMS application to a Virtual Machine (VM) on Ubuntu Server, with the ability to set the system date to an old date for working with historical data while maintaining the VM with the correct current date.

## Table of Contents

- [Overview](#overview)
- [VM Setup](#vm-setup)
- [Application Deployment](#application-deployment)
- [Date Management](#date-management)
- [Systemd Service Configuration](#systemd-service-configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

### Why Use a VM?

- **Isolation**: Run the old system with historical dates without affecting the main server
- **Date Control**: Easily switch between old dates (for historical data) and current date (for maintenance)
- **Testing**: Test date-dependent features without impacting production
- **Backup**: Keep a separate environment for data migration or historical analysis

### Use Cases

1. **Historical Data Access**: Access old records with their original dates
2. **Data Migration**: Migrate old data while maintaining current system
3. **Testing**: Test date-dependent features (billing, claims, reports)
4. **Maintenance**: Keep VM at current date for updates, backups, and maintenance

## VM Setup

### 1. Create Ubuntu Server VM

**Recommended VM Specifications:**
- **OS**: Ubuntu Server 22.04 LTS or 20.04 LTS
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 2+ cores
- **Storage**: 50GB+ (depends on data volume)
- **Network**: Bridge or NAT (depending on your needs)

### 2. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    mysql-server \
    mysql-client \
    git \
    curl \
    wget \
    vim \
    htop \
    ntpdate

# Install Node.js (for frontend, if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 3. Configure Network

```bash
# Set static IP (if needed)
sudo nano /etc/netplan/00-installer-config.yaml

# Example configuration:
# network:
#   version: 2
#   ethernets:
#     eth0:
#       dhcp4: false
#       addresses:
#         - 192.168.1.100/24
#       gateway4: 192.168.1.1
#       nameservers:
#         addresses:
#           - 8.8.8.8
#           - 8.8.4.4

# Apply network configuration
sudo netplan apply
```

### 4. Setup MySQL

```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p << EOF
CREATE DATABASE hms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hms_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON hms.* TO 'hms_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

## Application Deployment

### 1. Clone/Copy Application

```bash
# Create application directory
sudo mkdir -p /opt/hms
sudo chown $USER:$USER /opt/hms

# Copy application files (from your development machine or git)
cd /opt/hms
# Option 1: Clone from git
git clone <your-repo-url> .

# Option 2: Copy files via SCP
# scp -r backend/ user@vm-ip:/opt/hms/backend/
# scp -r frontend/ user@vm-ip:/opt/hms/frontend/
```

### 2. Setup Backend

```bash
cd /opt/hms/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env
```

**Configure `.env` for MySQL:**
```ini
DATABASE_MODE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=hms_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=hms
MYSQL_CHARSET=utf8mb4

SECRET_KEY=your-secret-key-change-this
FACILITY_CODE=ER-A25
```

### 3. Initialize Database

```bash
# Activate venv
source venv/bin/activate

# Run migrations
python run_migrations.py

# Initialize database
python init_db.py

# Change admin password (IMPORTANT!)
python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if admin:
    admin.hashed_password = get_password_hash('your_new_strong_password')
    db.commit()
    print('Admin password updated')
db.close()
"
```

### 4. Setup Frontend (Optional)

```bash
cd /opt/hms/frontend

# Install dependencies
npm install

# Build for production
npm run build

# Or run dev server (for testing)
npm run dev
```

## Date Management

### Understanding System Date vs Application Date

- **System Date**: The VM's operating system date (affects logs, file timestamps, etc.)
- **Application Date**: The date used by the application (from database records)

### Date Management Scripts

We'll create scripts to easily switch between old date and current date.

#### Script 1: Set Old Date

```bash
# Create script
sudo nano /usr/local/bin/set-old-date.sh
```

See `SET_OLD_DATE.sh` script below.

#### Script 2: Reset to Current Date

```bash
# Create script
sudo nano /usr/local/bin/reset-date.sh
```

See `RESET_DATE.sh` script below.

### Using Date Management

**Set VM to old date (e.g., 2024-01-01):**
```bash
sudo set-old-date.sh 2024-01-01
```

**Reset VM to current date:**
```bash
sudo reset-date.sh
```

**Check current date:**
```bash
date
```

### Important Notes

⚠️ **WARNING**: Changing system date can affect:
- SSL certificates (may appear expired)
- Log file timestamps
- Scheduled tasks (cron jobs)
- Database backups
- System logs

**Best Practice**: Only change date when working with historical data, then reset immediately after.

## Systemd Service Configuration

### 1. Create Backend Service

```bash
sudo nano /etc/systemd/system/hms-backend.service
```

```ini
[Unit]
Description=HMS Backend API Service
After=network.target mysql.service

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/opt/hms/backend
Environment="PATH=/opt/hms/backend/venv/bin"
EnvironmentFile=/opt/hms/backend/.env
ExecStart=/opt/hms/backend/venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --no-access-log
Restart=always
RestartSec=10
TimeoutStartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hms-backend
sudo systemctl start hms-backend
sudo systemctl status hms-backend
```

### 2. View Logs

```bash
# Follow logs
sudo journalctl -u hms-backend -f

# View recent logs
sudo journalctl -u hms-backend -n 50 --no-pager
```

## Best Practices

### 1. Date Management Workflow

1. **Before working with old data:**
   ```bash
   sudo set-old-date.sh 2024-01-01
   sudo systemctl restart hms-backend
   ```

2. **After finishing:**
   ```bash
   sudo reset-date.sh
   sudo systemctl restart hms-backend
   ```

### 2. Backup Strategy

- **Before changing date**: Backup database
- **After changing date**: Backup database again
- **Regular backups**: Schedule daily backups regardless of date

### 3. Network Isolation

Consider isolating the VM network if:
- You're working with sensitive historical data
- You want to prevent accidental access
- You're testing date-dependent features

### 4. Documentation

Keep a log of:
- When date was changed
- What date was set
- What work was done
- When date was reset

## Troubleshooting

### Issue: Service won't start after date change

**Solution:**
```bash
# Check service status
sudo systemctl status hms-backend

# Check logs
sudo journalctl -u hms-backend -n 50

# Restart service
sudo systemctl restart hms-backend
```

### Issue: SSL certificate errors

**Cause**: System date is in the past, certificates appear expired

**Solution**: Reset date or ignore SSL warnings (for internal use only)

### Issue: Database connection fails

**Solution:**
```bash
# Check MySQL is running
sudo systemctl status mysql

# Test connection
mysql -u hms_user -p hms

# Check .env configuration
cat /opt/hms/backend/.env | grep MYSQL
```

### Issue: Logs show wrong timestamps

**Cause**: System date was changed

**Solution**: Reset date and restart services

## Maintenance Schedule

### Daily
- Check service status
- Review logs for errors
- Verify backups

### Weekly
- Update system packages
- Review database size
- Check disk space

### Monthly
- Full system backup
- Review and clean old logs
- Update application if needed

## Security Considerations

1. **Firewall**: Configure UFW or iptables
2. **SSH**: Use key-based authentication
3. **Passwords**: Change all default passwords
4. **Updates**: Keep system updated
5. **Backups**: Encrypt sensitive backups

## Next Steps

1. Deploy application following this guide
2. Test date management scripts
3. Setup automated backups
4. Configure monitoring
5. Document your specific setup

For more details on specific components, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - General deployment guide
- [DATABASE_SYNC_SETUP.md](./DATABASE_SYNC_SETUP.md) - Database sync setup
- [CHECK_MYSQL_CONNECTION.md](./CHECK_MYSQL_CONNECTION.md) - MySQL troubleshooting

