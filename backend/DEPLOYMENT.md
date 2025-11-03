# Hospital Management System (HMS) - Production Deployment Guide

This guide covers deploying the HMS backend to a production server with MySQL database.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [MySQL Database Setup](#mysql-database-setup)
- [Application Installation](#application-installation)
- [Configuration](#configuration)
- [Database Initialization](#database-initialization)
- [Running the Application](#running-the-application)
- [Production Considerations](#production-considerations)
- [Frontend Configuration](#frontend-configuration)
- [Backup and Maintenance](#backup-and-maintenance)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Server Requirements
- **OS**: Linux (Ubuntu 20.04+ / Debian 10+ / CentOS 7+) or Windows Server
- **RAM**: Minimum 2GB (4GB+ recommended)
- **CPU**: 2+ cores recommended
- **Storage**: 10GB+ free space (varies based on data volume)

### Software Requirements
- **Python**: 3.8 or higher (3.10+ recommended)
- **MySQL**: 5.7+ or MariaDB 10.3+
- **pip**: Python package manager
- **virtualenv** (optional but recommended)

## Prerequisites

1. **Server Access**: SSH access to production server
2. **MySQL Installed**: MySQL or MariaDB should be installed and running
3. **Python Installed**: Python 3.8+ with pip
4. **Domain/Server IP**: Frontend URL for CORS configuration
5. **Firewall**: Ports 8000 (or your chosen port) should be accessible

### Installing MySQL (if not already installed)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
sudo systemctl start mysql
sudo systemctl enable mysql
```

**CentOS/RHEL:**
```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
sudo mysql_secure_installation
```

## MySQL Database Setup

### 1. Create Database and User

Log in to MySQL as root:
```bash
sudo mysql -u root -p
```

Create database and user:
```sql
-- Create database
CREATE DATABASE hms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create dedicated user (recommended for security)
CREATE USER 'hms_user'@'localhost' IDENTIFIED BY 'your_strong_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON hms.* TO 'hms_user'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
EXIT;
```

**Security Note**: 
- Replace `'your_strong_password_here'` with a strong password
- Consider using a more restrictive host (e.g., `'hms_user'@'127.0.0.1'`) if your app runs on the same server
- For remote MySQL connections, use `'hms_user'@'%'` but ensure firewall rules are configured

### 2. Verify MySQL Connection

Test connection with the new user:
```bash
mysql -u hms_user -p -h localhost hms
```

If successful, you'll see the MySQL prompt. Type `EXIT;` to leave.

## Application Installation

### 1. Prepare Directory Structure

Create application directory:
```bash
sudo mkdir -p /opt/hms
sudo chown $USER:$USER /opt/hms
cd /opt/hms
```

### 2. Upload Application Files

Upload the entire `backend` directory to `/opt/hms/backend`:

**Using SCP:**
```bash
# From your local machine
scp -r backend/ user@your-server:/opt/hms/
```

**Using Git (recommended):**
```bash
# On server
cd /opt/hms
git clone your-repository-url .
# Or if backend is a subdirectory
git clone your-repository-url repo
mv repo/backend .
```

### 3. Create Virtual Environment

```bash
cd /opt/hms/backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: If you encounter compilation errors (especially with `pandas` or `bcrypt`), you may need to install build tools:

**Ubuntu/Debian:**
```bash
sudo apt install python3-dev python3-pip build-essential
```

**CentOS/RHEL:**
```bash
sudo yum install python3-devel gcc gcc-c++
```

## Configuration

### 1. Create `.env` File

Copy the example environment file:
```bash
cp env.example .env
```

### 2. Edit `.env` File

Open `.env` in your preferred editor:
```bash
nano .env
# or
vi .env
```

Configure the following variables:

```env
# Database Configuration
DATABASE_MODE=mysql

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=hms_user
MYSQL_PASSWORD=your_strong_password_here
MYSQL_DATABASE=hms
MYSQL_CHARSET=utf8mb4

# JWT Settings - IMPORTANT: Change this in production!
SECRET_KEY=generate-a-very-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Facility Settings
FACILITY_CODE=ER-A25
```

**Critical Security Settings:**

1. **SECRET_KEY**: Generate a strong random secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Use the output as your `SECRET_KEY`.

2. **MYSQL_PASSWORD**: Use the same password you set when creating the MySQL user.

3. **FACILITY_CODE**: Set your actual facility code (e.g., `ER-A25`).

### 3. Secure `.env` File

Set restrictive permissions:
```bash
chmod 600 .env
```

## Database Initialization

### 1. Initialize Database Tables

With your virtual environment activated:
```bash
python init_db.py
```

This will:
- Create all database tables
- Create a default admin user:
  - **Username**: `admin`
  - **Password**: `admin123`

### 2. **CRITICAL**: Change Default Admin Password

**IMPORTANT**: Change the default admin password immediately after first login!

You can do this via the API or create a script:
```bash
python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if admin:
    admin.hashed_password = get_password_hash('your_new_strong_password')
    db.commit()
    print('Admin password updated successfully')
else:
    print('Admin user not found')
db.close()
"
```

Replace `'your_new_strong_password'` with your desired password.

## Running the Application

### Option 1: Development Mode (Testing)

For initial testing:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Production with Uvicorn

**Basic Production Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log
```

**Recommended Production Command:**
```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --log-level info \
  --no-access-log \
  --timeout-keep-alive 5
```

### Option 3: Systemd Service (Recommended for Linux)

Create a systemd service file for automatic startup:

```bash
sudo nano /etc/systemd/system/hms-backend.service
```

Add the following content:
```ini
[Unit]
Description=HMS Backend API Service
After=network.target mysql.service

[Service]
Type=notify
User=your_user
Group=your_user
WorkingDirectory=/opt/hms/backend
Environment="PATH=/opt/hms/backend/venv/bin"
ExecStart=/opt/hms/backend/venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --no-access-log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Important**: Replace `your_user` with your actual system username.

**Enable and Start Service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hms-backend
sudo systemctl start hms-backend
sudo systemctl status hms-backend
```

**Useful Commands:**
```bash
# View logs
sudo journalctl -u hms-backend -f

# Restart service
sudo systemctl restart hms-backend

# Stop service
sudo systemctl stop hms-backend
```

### Option 4: Using Gunicorn with Uvicorn Workers (Advanced)

If you need more control, use Gunicorn:

```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --log-level info
```

## Production Considerations

### 1. CORS Configuration

Update CORS origins in `app/main.py` to include your production frontend URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9000",  # Remove in production
        "https://your-frontend-domain.com",  # Add your frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Reverse Proxy (Nginx/Apache)

**Nginx Configuration Example:**

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # For file uploads (adjust max size as needed)
    client_max_body_size 50M;
}
```

**SSL/HTTPS Configuration (Recommended):**

Use Let's Encrypt with Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

Update Nginx config to redirect HTTP to HTTPS.

### 3. File Upload Directory

Ensure the `uploads` directory exists and has proper permissions:
```bash
mkdir -p /opt/hms/backend/uploads
chmod 755 /opt/hms/backend/uploads
```

Create subdirectories for different file types:
```bash
mkdir -p /opt/hms/backend/uploads/{lab_results,scan_results,xray_results}
```

### 4. Logging

Consider configuring proper logging. Create a logging configuration or use a logging service.

### 5. Environment Variables

For production, you might want to set environment variables at the system level instead of `.env` file:

```bash
# In /etc/environment or ~/.bashrc
export MYSQL_PASSWORD=your_password
export SECRET_KEY=your_secret_key
```

Then reference them in your service file:
```ini
Environment="MYSQL_PASSWORD=${MYSQL_PASSWORD}"
Environment="SECRET_KEY=${SECRET_KEY}"
```

## Frontend Configuration

Update your frontend API base URL to point to your production backend:

**In `frontend/src/services/api.js` or similar:**
```javascript
const API_BASE_URL = process.env.VUE_APP_API_URL || 'http://localhost:8000';

// Production: 'https://api.yourdomain.com'
// Development: 'http://localhost:8000'
```

**Or set via environment variable:**
```bash
# In frontend .env
VUE_APP_API_URL=https://api.yourdomain.com
```

## Backup and Maintenance

### 1. Database Backup Script

Create a backup script (`/opt/hms/backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/opt/hms/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="hms"
DB_USER="hms_user"
DB_PASS="your_mysql_password"

mkdir -p $BACKUP_DIR

mysqldump -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_DIR/hms_backup_$DATE.sql
gzip $BACKUP_DIR/hms_backup_$DATE.sql

# Keep only last 30 days of backups
find $BACKUP_DIR -name "hms_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: hms_backup_$DATE.sql.gz"
```

Make it executable:
```bash
chmod +x /opt/hms/backup.sh
```

### 2. Automated Backups (Cron)

Add to crontab (daily backup at 2 AM):
```bash
crontab -e

# Add this line:
0 2 * * * /opt/hms/backup.sh >> /opt/hms/backup.log 2>&1
```

### 3. Restore from Backup

```bash
# Uncompress backup
gunzip hms_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore
mysql -u hms_user -p hms < hms_backup_YYYYMMDD_HHMMSS.sql
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

**Error**: `Can't connect to MySQL server`

**Solutions**:
- Verify MySQL is running: `sudo systemctl status mysql`
- Check MySQL credentials in `.env`
- Verify MySQL user has correct privileges
- Check firewall rules
- Ensure MySQL is listening on the correct port

#### 2. Import Error: pymysql

**Error**: `ModuleNotFoundError: No module named 'pymysql'`

**Solution**:
```bash
pip install pymysql
```

#### 3. Permission Denied on Uploads Directory

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
chmod 755 /opt/hms/backend/uploads
chown -R $USER:$USER /opt/hms/backend/uploads
```

#### 4. Port Already in Use

**Error**: `Address already in use`

**Solution**:
- Find process using port 8000: `sudo lsof -i :8000`
- Kill the process: `sudo kill -9 <PID>`
- Or change port in uvicorn command

#### 5. CORS Errors from Frontend

**Solution**:
- Verify frontend URL is in `allow_origins` in `app/main.py`
- Check that frontend is making requests to the correct backend URL
- Ensure credentials are properly configured

### Viewing Logs

**Systemd Service Logs:**
```bash
sudo journalctl -u hms-backend -f
sudo journalctl -u hms-backend -n 100  # Last 100 lines
```

**Application Logs:**
Check if you have configured file-based logging, or monitor stdout/stderr of your process.

### Testing the Deployment

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **API Documentation:**
   Visit: `http://your-server-ip:8000/docs`

3. **Database Connection:**
   Check application logs for database connection errors.

## Migration from SQLite to MySQL

If you're migrating from SQLite (development) to MySQL (production):

1. **Export data from SQLite:**
   ```bash
   sqlite3 hms.db .dump > hms_export.sql
   ```

2. **Clean up SQLite-specific syntax** (if needed):
   - SQLite AUTOINCREMENT vs MySQL AUTO_INCREMENT
   - Other dialect-specific differences

3. **Import to MySQL:**
   ```bash
   mysql -u hms_user -p hms < hms_export.sql
   ```

**Note**: For complex migrations, consider using SQLAlchemy migration tools (Alembic) or manual migration scripts.

## Security Checklist

- [ ] Changed default admin password
- [ ] Generated strong SECRET_KEY
- [ ] Set restrictive `.env` file permissions (600)
- [ ] Configured MySQL user with minimal required privileges
- [ ] Enabled HTTPS/SSL with reverse proxy
- [ ] Updated CORS origins to production frontend URL only
- [ ] Configured firewall rules
- [ ] Set up automated database backups
- [ ] Configured log rotation
- [ ] Enabled fail2ban or similar intrusion prevention
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`

## Support

For issues or questions:
- Check application logs: `sudo journalctl -u hms-backend -f`
- Check API documentation: `http://your-server:8000/docs`
- Review database logs: `sudo tail -f /var/log/mysql/error.log`

---

**Last Updated**: 2025-01-07
**Version**: 1.0.0

