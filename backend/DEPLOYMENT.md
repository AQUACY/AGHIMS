# Hospital Management System (HMS) - Production Deployment Guide

This guide covers deploying the HMS backend and frontend to a production server using Apache web server, with the backend accessible at `localhost/backend` and frontend at `localhost/frontend` (or `10.10.16.50/frontend` for network access).

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
- **python3-venv**: Required for creating virtual environments (Debian/Ubuntu)
- **MySQL**: 5.7+ or MariaDB 10.3+
- **pip**: Python package manager

## Prerequisites

1. **Server Access**: SSH access to production server
2. **MySQL Installed**: MySQL or MariaDB should be installed and running
3. **Python Installed**: Python 3.8+ with pip and python3-venv
4. **Domain/Server IP**: Frontend URL for CORS configuration
5. **Firewall**: Ports 8000 (or your chosen port) should be accessible

### Installing Python and Required Packages

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip python3-devel
# Note: On CentOS/RHEL, venv is usually included with python3
```

**Verify Installation:**
```bash
python3 --version  # Should show Python 3.8 or higher
pip3 --version     # Should show pip version
python3 -m venv --help  # Should show venv help (not error)
```

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

Create application directories in `/var/www/html`:
```bash
sudo mkdir -p /var/www/html/backend
sudo mkdir -p /var/www/html/frontend
sudo chown -R $USER:$USER /var/www/html/backend
sudo chown -R $USER:$USER /var/www/html/frontend

# Ensure Apache can access the html directory
sudo chmod 755 /var/www/html
sudo chown www-data:www-data /var/www/html
```

**Note**: If `/var/www/html` already exists and contains other files (like `index.html`), that's fine. The backend and frontend will be in subdirectories.

### 2. Upload Backend Files

Upload the entire `backend` directory to `/var/www/html/backend`:

**Using SCP:**
```bash
# From your local machine
scp -r backend/* user@your-server:/var/www/html/backend/
```

**Using Git (recommended):**
```bash
# On server
cd /var/www/html
git clone your-repository-url repo
cp -r repo/backend/* /var/www/html/backend/
```

### 3. Create Virtual Environment

**First, ensure python3-venv is installed:**
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# Or for specific Python version (e.g., Python 3.8)
sudo apt install python3.8-venv
```

**Then create the virtual environment:**
```bash
cd /var/www/html/backend
python3 -m venv venv

# If the above fails, try with --without-pip (then install pip manually):
# python3 -m venv venv --without-pip
# source venv/bin/activate
# curl https://bootstrap.pypa.io/get-pip.py | python3

# Activate the virtual environment
# Note: Do NOT use 'sudo' with 'source' - it's a shell built-in command
# Just run 'source' directly (as your regular user)
source venv/bin/activate

# Verify activation (your prompt should show (venv))
which python  # Should point to /var/www/html/backend/venv/bin/python
```

**Important**: The `source` command is a shell built-in and cannot be used with `sudo`. Always activate the virtual environment as your regular user, not with `sudo`.

### 4. Install Dependencies

**Make sure your virtual environment is activated first:**
```bash
# If not already activated, activate it:
cd /var/www/html/backend
source venv/bin/activate  # No sudo here!

# Your prompt should show (venv) at the beginning
# Upgrade pip to latest version first (important for package compatibility)
pip install --upgrade pip setuptools wheel

# Check Python version (should be 3.9+ for pandas 2.3.0+)
python --version
```

**Install dependencies (excluding pandas first):**

**Option 1: Install all except pandas, then pandas separately (Recommended):**
```bash
# Install all requirements except pandas
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    openpyxl python-dotenv pymysql

# Check Python version first
python --version  # Should be 3.9+ for pandas 2.3.0+

# Then install pandas separately (quote the version to avoid shell errors)
# If Python 3.9+: pip install "pandas>=2.3.0"
# If Python 3.8: pip install "pandas>=2.0.0"
pip install "pandas>=2.0.0"  # Use this if you get version errors
```

**Option 2: Use requirements.txt with pandas commented out:**
```bash
# First, temporarily comment out pandas in requirements.txt:
# Comment line: pandas>=2.3.0

# Install dependencies
pip install -r requirements.txt

# Then install pandas separately (quote the version)
pip install "pandas>=2.3.0"

# Uncomment pandas in requirements.txt for future use
```

**Option 3: Install all at once (if Python 3.9+):**
```bash
pip install -r requirements.txt
```

**If you get errors installing pandas:**

**Step 1: Ensure build tools are installed:**
```bash
# Install build tools (required for pandas compilation)
sudo apt install python3-dev python3-pip build-essential
```

**Step 2: Check Python version:**
```bash
# Check which Python version you're using
python --version

# Pandas 2.3.0+ requires Python 3.9+
# If you see Python 3.8 or older, use pandas 2.0.0 instead
```

**Step 3: Install pandas separately (as done during local development):**
```bash
# Make sure other dependencies are installed first
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    openpyxl python-dotenv pymysql

# Then install pandas based on your Python version:
# For Python 3.9+: pip install "pandas>=2.3.0"
# For Python 3.8: pip install "pandas>=2.0.0"  (use this if you get version errors)
pip install "pandas>=2.0.0"
```

**If pandas still fails (Python version too old):**

**Option 1: Upgrade Python (recommended):**
```bash
# Install Python 3.10 (Ubuntu/Debian)
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev

# Recreate venv with Python 3.10
cd /var/www/html/backend
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install dependencies (excluding pandas)
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    openpyxl python-dotenv pymysql

# Then install pandas (quote the version)
pip install "pandas>=2.3.0"
```

**Option 2: Use compatible pandas version (if Python < 3.9):**
```bash
# Install compatible pandas version for Python 3.8 (quote the version)
pip install "pandas>=2.0.0"  # Works with Python 3.8+
# Or for older Python: pip install "pandas>=1.5.0"
```

**Note**: If you need to install packages that require system-level access, do it before activating the venv, or use `sudo pip install` (though this is not recommended - better to fix permissions).

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

### Initial Setup

First, initialize the database and create tables:

```bash
cd /var/www/html/backend
source venv/bin/activate
python init_db.py
```

### Running Migrations

The system uses a centralized migration runner that automatically detects and runs all new migrations. **Always run this after deploying updates:**

```bash
cd /var/www/html/backend
source venv/bin/activate
python run_migrations.py
```

This will:
- Automatically detect all migration files (migrate_*.py)
- Check which migrations have already been executed
- Run only new migrations in order
- Record successful executions in the database

**Options:**
- `python run_migrations.py` - Run all pending migrations
- `python run_migrations.py --status` - Show migration status without running
- `python run_migrations.py --dry-run` - Show what would be run without executing

**Important:** Run `python run_migrations.py` after every deployment to ensure the database schema is up to date.

### First-Time Migration Setup

If this is the first time using the migration runner, you need to create the migration tracker table:

```bash
python migrate_create_migration_tracker.py
```

After this, you can use `run_migrations.py` for all future migrations.

### Initialize Database Tables

**Activate your virtual environment first (no sudo):**
```bash
cd /var/www/html/backend
source venv/bin/activate  # Activate as regular user, not with sudo

# Now initialize the database
python init_db.py
```

This will:
- Create all database tables
- Create a default admin user:
  - **Username**: `admin`
  - **Password**: `admin123`

### **CRITICAL**: Change Default Admin Password

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

### Option 2: Production with Uvicorn (Behind Apache)

**Basic Production Command:**
```bash
cd /var/www/html/backend
source venv/bin/activate  # Activate as regular user (no sudo)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --no-access-log
```

**Or use the full path to avoid activating venv:**
```bash
cd /var/www/html/backend
/var/www/html/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --no-access-log
```

**Recommended Production Command:**
```bash
cd /var/www/html/backend
source venv/bin/activate  # Activate as regular user (no sudo)
uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --no-access-log \
  --timeout-keep-alive 5
```

**Note**: The `--worker-class` option is only used with Gunicorn, not with uvicorn directly. Uvicorn uses its own worker implementation.

**Note**: We use `127.0.0.1` instead of `0.0.0.0` since Apache will proxy requests to this local address.

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
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/backend
Environment="PATH=/var/www/html/backend/venv/bin"
ExecStart=/var/www/html/backend/venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --no-access-log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

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
        "http://localhost:9000",  # Development
        "http://localhost:3000",  # Development
        "http://localhost",  # Production (Apache)
        "http://10.10.16.50",  # Production (Network IP)
        "http://10.10.16.50/frontend",  # Production (Network IP with path)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note**: Since the frontend and backend are on the same domain (localhost), you may not need CORS, but it's good to have it configured for flexibility.

### 2. Apache Configuration

Since you're using `/var/www/html` and want the backend at `localhost/backend` and frontend at `localhost/frontend`, we'll configure Apache to proxy requests to the backend and serve the frontend.

**Enable Required Apache Modules:**
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
sudo a2enmod headers
sudo systemctl restart apache2
```

**Create Apache Configuration File:**

Create or edit `/etc/apache2/sites-available/000-default.conf` (or your site config):

```apache
<VirtualHost *:80>
    ServerName localhost
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/html

    # Backend API Proxy - /backend -> http://127.0.0.1:8000
    <LocationMatch "^/backend">
        ProxyPreserveHost On
        ProxyPass http://127.0.0.1:8000/
        ProxyPassReverse http://127.0.0.1:8000/
        
        # CORS Headers (if needed)
        Header always set Access-Control-Allow-Origin "*"
        Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        Header always set Access-Control-Allow-Headers "Authorization, Content-Type"
        
        # Timeouts for long-running requests
        ProxyTimeout 300
    </LocationMatch>

    # Frontend - Serve from /var/www/html/frontend
    Alias /frontend /var/www/html/frontend
    <Directory /var/www/html/frontend>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # Handle Vue Router history mode
        RewriteEngine On
        RewriteBase /frontend/
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /frontend/index.html [L]
    </Directory>

    # Default directory - Allow access to /var/www/html
    <Directory /var/www/html>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
        
        # Allow directory listing if needed
        DirectoryIndex index.html index.php
    </Directory>

    # For file uploads (adjust max size as needed)
    LimitRequestBody 52428800

    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

**Important Notes:**
- If your old applications are outside `/var/www/html`, they will continue to work as before
- The new backend and frontend should be placed in `/var/www/html/backend` and `/var/www/html/frontend`
- Make sure the `www-data` user (or Apache user) has read permissions on `/var/www/html`

**Enable Site and Restart Apache:**
```bash
sudo a2ensite 000-default.conf
sudo systemctl restart apache2
```

**Test Configuration:**
```bash
# Check Apache config syntax
sudo apache2ctl configtest

# Check if backend is accessible
curl http://localhost/backend/health

# Check if frontend is accessible
curl http://localhost/frontend/

# Check Apache error logs if you get "Forbidden" errors
sudo tail -f /var/log/apache2/error.log
```

**Troubleshooting "Forbidden" Errors:**

If you get "403 Forbidden" when accessing `localhost`:

1. **Check directory permissions:**
   ```bash
   sudo chmod 755 /var/www/html
   sudo chown www-data:www-data /var/www/html
   ```

2. **Check if SELinux is blocking (CentOS/RHEL):**
   ```bash
   sudo setsebool -P httpd_read_user_content 1
   sudo restorecon -R /var/www/html
   ```

3. **Check Apache error logs:**
   ```bash
   sudo tail -f /var/log/apache2/error.log
   # Look for permission denied messages
   ```

4. **Verify Apache user has access:**
   ```bash
   sudo -u www-data ls -la /var/www/html
   # Should list files without errors
   ```

**SSL/HTTPS Configuration (Optional but Recommended):**

If you want to enable HTTPS:
```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d your-domain.com
```

### 3. File Upload Directory

Ensure the `uploads` directory exists and has proper permissions:
```bash
mkdir -p /var/www/html/backend/uploads
sudo chmod 755 /var/www/html/backend/uploads
sudo chown -R www-data:www-data /var/www/html/backend/uploads
```

Create subdirectories for different file types:
```bash
mkdir -p /var/www/html/backend/uploads/{lab_results,scan_results,xray_results}
sudo chmod -R 755 /var/www/html/backend/uploads
sudo chown -R www-data:www-data /var/www/html/backend/uploads
```

**Set proper permissions for the entire backend directory:**
```bash
# Make sure Apache can read backend files
sudo chmod -R 755 /var/www/html/backend
sudo chown -R www-data:www-data /var/www/html/backend

# But keep .env file secure
sudo chmod 600 /var/www/html/backend/.env
sudo chown $USER:www-data /var/www/html/backend/.env
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

### 1. Build Frontend for Production

```bash
cd /var/www/html/frontend
# Or if you're building locally and copying:
cd frontend  # from your local machine
npm install
npm run build
```

### 2. Copy Build Output

**If building locally:**
```bash
# Copy the dist/spa directory contents to server
scp -r dist/spa/* user@your-server:/var/www/html/frontend/

# Then set permissions on server
ssh user@your-server
sudo chown -R www-data:www-data /var/www/html/frontend
sudo chmod -R 755 /var/www/html/frontend
```

**If building on server:**
```bash
cd /var/www/html/frontend
npm install
npm run build
# The build output should be in dist/spa/
sudo cp -r dist/spa/* /var/www/html/frontend/
sudo chown -R www-data:www-data /var/www/html/frontend
sudo chmod -R 755 /var/www/html/frontend
```

**Important**: Make sure all files in `/var/www/html/frontend` are owned by `www-data` and have proper permissions (755 for directories, 644 for files).

### 3. Update Frontend API Base URL

**Update `frontend/quasar.config.js`:**

```javascript
build: {
  vueRouterMode: 'history',
  env: {
    API_BASE_URL: ctx.dev
      ? 'http://localhost:8000/api'  // Development
      : '/backend/api'  // Production - relative path
  }
}
```

**Update `frontend/src/services/api.js`:**

```javascript
const API_BASE_URL = process.env.API_BASE_URL || '/backend/api';

// This will use:
// - Development: http://localhost:8000/api
// - Production: /backend/api (relative to current domain)
```

### 4. Set Correct Base Path for Vue Router

**Update `frontend/src/router/index.js`:**

```javascript
const router = createRouter({
  history: createWebHistory('/frontend/'),  // Add base path for production
  routes: [
    // ... your routes
  ]
});
```

**Or use environment-based configuration:**

```javascript
import { createRouter, createWebHistory } from 'vue-router';

const base = process.env.NODE_ENV === 'production' ? '/frontend/' : '/';

const router = createRouter({
  history: createWebHistory(base),
  routes: [
    // ... your routes
  ]
});
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

#### 1. Virtual Environment Creation Error

**Error**: `The virtual environment was not created successfully because ensurepip is not available`

**Solution**:
```bash
# Install python3-venv package
sudo apt install python3-venv

# Or for specific Python version
sudo apt install python3.8-venv  # Replace 3.8 with your Python version

# Then recreate the virtual environment
cd /var/www/html/backend
rm -rf venv  # Remove old failed venv
python3 -m venv venv

# Activate the venv (NO sudo - source is a shell built-in)
source venv/bin/activate
```

**Alternative (if python3-venv not available):**
```bash
# Create venv without pip
python3 -m venv venv --without-pip

# Activate and install pip manually (NO sudo with source)
source venv/bin/activate
curl https://bootstrap.pypa.io/get-pip.py | python3
```

**Note**: If you need to run commands as a different user (e.g., www-data), you can use:
```bash
# Use sudo -u to switch user, then activate venv
sudo -u www-data bash -c "cd /var/www/html/backend && source venv/bin/activate && python script.py"
```

Or better yet, use the full path to the Python interpreter:
```bash
sudo -u www-data /var/www/html/backend/venv/bin/python script.py
```

#### 2. Database Connection Error

**Error**: `Can't connect to MySQL server`

**Solutions**:
- Verify MySQL is running: `sudo systemctl status mysql`
- Check MySQL credentials in `.env`
- Verify MySQL user has correct privileges
- Check firewall rules
- Ensure MySQL is listening on the correct port

#### 3. Pandas Installation Error

**Error**: `ERROR: Could not find a version that satisfies the requirement pandas>=2.3.0`

**Solution** (Following the same approach as local development):

**Step 1: Install all dependencies except pandas:**
```bash
cd /var/www/html/backend
source venv/bin/activate

# Install all requirements except pandas
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    openpyxl python-dotenv pymysql
```

**Step 2: Ensure build tools are installed:**
```bash
# Install build tools (required for pandas)
sudo apt install python3-dev build-essential
```

**Step 3: Check Python version and install compatible pandas:**
```bash
# Check Python version
python --version

# Install pandas based on Python version:
# If Python 3.9+: pip install "pandas>=2.3.0"
# If Python 3.8: pip install "pandas>=2.0.0"  (use this if you get version errors)
pip install "pandas>=2.0.0"
```

**If pandas still fails (Python version too old):**

**Option 1: Upgrade Python (Recommended)**
```bash
# Install Python 3.10 (Ubuntu/Debian)
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev build-essential

# Recreate venv with Python 3.10
cd /var/www/html/backend
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install all except pandas
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart \
    openpyxl python-dotenv pymysql

# Then install pandas (quote the version)
pip install "pandas>=2.3.0"
```

**Option 2: Use Compatible Pandas Version**
```bash
# If Python < 3.9, use compatible pandas version (quote the version)
pip install "pandas>=2.0.0"  # Works with Python 3.8+
```

**Option 3: Upgrade pip and retry**
```bash
# Sometimes pip's index is outdated
pip install --upgrade pip setuptools wheel
pip install --upgrade --index-url https://pypi.org/simple pandas
```

#### 4. Import Error: pymysql

**Error**: `ModuleNotFoundError: No module named 'pymysql'`

**Solution**:
```bash
pip install pymysql
```

#### 5. Permission Denied on Uploads Directory

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
chmod 755 /opt/hms/backend/uploads
chown -R $USER:$USER /opt/hms/backend/uploads
```

#### 6. Port Already in Use

**Error**: `Address already in use`

**Solution**:
- Find process using port 8000: `sudo lsof -i :8000`
- Kill the process: `sudo kill -9 <PID>`
- Or change port in uvicorn command

#### 7. CORS Errors from Frontend

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

1. **Backend Health Check:**
   ```bash
   curl http://localhost/backend/health
   # Should return: {"status":"healthy"}
   ```

2. **Backend API Documentation:**
   Visit: `http://localhost/backend/docs`
   Or: `http://10.10.16.50/backend/docs`

3. **Frontend Access:**
   Visit: `http://localhost/frontend`
   Or: `http://10.10.16.50/frontend`

4. **Database Connection:**
   Check application logs for database connection errors:
   ```bash
   sudo journalctl -u hms-backend -f
   ```

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

