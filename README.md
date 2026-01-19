# Hospital Management System (HMS) - Windows Server 2022 Setup Guide

This guide will help you set up the Hospital Management System on Windows Server 2022.

## Table of Contents

- [Prerequisites](#prerequisites)
- [System Requirements](#system-requirements)
- [Installation Steps](#installation-steps)
  - [0. Install Git Bash (Recommended)](#0-install-git-bash-recommended)
  - [1. Install Python](#1-install-python)
  - [2. Install Node.js](#2-install-nodejs)
  - [3. Install MySQL (Optional)](#3-install-mysql-optional)
  - [4. Backend Setup](#4-backend-setup)
  - [5. Frontend Setup](#5-frontend-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Windows Firewall Configuration](#windows-firewall-configuration)
- [Running as Windows Service](#running-as-windows-service)
- [Troubleshooting](#troubleshooting)
- [Git Bash Quick Reference](#git-bash-quick-reference)

## Prerequisites

Before starting, ensure you have administrative access to the Windows Server 2022 machine.

**Note**: This guide uses Git Bash commands. If you're not familiar with Git Bash, you can install it (see step 0) or use PowerShell/Command Prompt with adapted commands.

## System Requirements

- **OS**: Windows Server 2022
- **Python**: 3.8 or higher
- **Node.js**: 18.0 or higher
- **npm**: 8.0 or higher
- **MySQL**: 5.7 or higher (optional, for production)
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: Minimum 2GB free space

## Installation Steps

### 0. Install Git Bash (Recommended)

Git Bash provides a Unix-like command-line environment on Windows, which many developers find more familiar.

1. Download Git for Windows from [git-scm.com](https://git-scm.com/download/win)
2. Run the installer
3. During installation:
   - Choose "Git from the command line and also from 3rd-party software"
   - Choose "Use bundled OpenSSH"
   - Choose "Use the OpenSSL library"
   - Choose "Checkout Windows-style, commit Unix-style line endings"
   - Choose "Use MinTTY (the default terminal of MSYS2)"
4. After installation, you can launch Git Bash from:
   - Start Menu → Git → Git Bash
   - Right-click in any folder → "Git Bash Here"
5. Verify installation:
   ```bash
   git --version
   ```

**Note**: All commands in this guide are written for Git Bash. If you prefer PowerShell or Command Prompt, you can adapt the commands accordingly.

### 1. Install Python

1. Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **Important**: Check "Add Python to PATH" during installation
4. Verify installation (in Git Bash):
   ```bash
   python --version
   pip --version
   ```

### 2. Install Node.js

1. Download Node.js 18+ from [nodejs.org](https://nodejs.org/)
2. Run the installer (LTS version recommended)
3. Verify installation (in Git Bash):
   ```bash
   node --version
   npm --version
   ```

### 3. Install MySQL (Optional)

For production deployments, MySQL is recommended over SQLite.

1. Download MySQL Community Server from [mysql.com](https://dev.mysql.com/downloads/mysql/)
2. Run the installer
3. During installation:
   - Choose "Server only" or "Full" installation
   - Set root password (remember this for configuration)
   - Configure MySQL to run as a Windows service
   - Set port to 3306 (default)
4. Verify installation (in Git Bash):
   ```bash
   mysql --version
   ```

### 4. Backend Setup

1. **Open Git Bash** (you can right-click in the project folder and select "Git Bash Here")

2. **Navigate to the backend directory**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/backend
   ```
   
   **Note**: In Git Bash, Windows paths use forward slashes and drive letters are mounted at `/c/`, `/d/`, etc.

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   ```bash
   source venv/Scripts/activate
   ```
   
   You should see `(venv)` at the beginning of your prompt when activated.

5. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Create environment configuration file**:
   
   Create a file named `.env` in the `backend` directory with the following content:
   ```env
   # Database Configuration
   DATABASE_MODE=sqlite
   SQLITE_DB_PATH=./hms.db
   
   # For MySQL (uncomment and configure if using MySQL):
   # DATABASE_MODE=mysql
   # MYSQL_HOST=localhost
   # MYSQL_PORT=3306
   # MYSQL_USER=root
   # MYSQL_PASSWORD=your_mysql_password
   # MYSQL_DATABASE=hms
   # MYSQL_CHARSET=utf8mb4
   
   # JWT Settings (CHANGE IN PRODUCTION!)
   SECRET_KEY=your-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   
   # Facility Settings
   FACILITY_CODE=ER-A25
   
   # Analyzer Integration (optional)
   ANALYZER_ENABLED=False
   ANALYZER_HOST=0.0.0.0
   ANALYZER_PORT=5150
   ANALYZER_EQUIPMENT_IP=10.10.16.34
   ANALYZER_TIMEOUT=30
   
   # Backup Settings (optional)
   BACKUP_ENABLED=True
   BACKUP_DIR=./backups
   BACKUP_RETENTION_DAYS=30
   SCHEDULED_BACKUP_ENABLED=False
   SCHEDULED_BACKUP_TIME=02:00
   
   # Online Sync Settings (optional)
   SYNC_ENABLED=False
   SYNC_REMOTE_HOST=
   SYNC_REMOTE_PORT=3306
   SYNC_REMOTE_USER=
   SYNC_REMOTE_PASSWORD=
   SYNC_REMOTE_DATABASE=
   SYNC_INTERVAL_MINUTES=60
   
   # Application Date Override (optional, leave empty to use system date)
   APPLICATION_REFERENCE_DATE=
   ```

7. **Initialize the database**:
   ```bash
   python init_db.py
   ```
   
   This will create the database tables and a default admin user:
   - Username: `admin`
   - Password: `admin123`
   - **IMPORTANT**: Change this password immediately in production!

### 5. Frontend Setup

1. **Navigate to the frontend directory** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Configure API URL** (if needed):
   
   Edit `quasar.config.js` and update the `API_BASE_URL` in the `env` section if your backend is not running on `http://localhost:8000/api`.

## Configuration

### Database Configuration

#### Using SQLite (Development/Testing)

SQLite is the default and requires no additional setup. The database file will be created at `backend/hms.db`.

#### Using MySQL (Production Recommended)

1. **Create the database** (in Git Bash):
   ```bash
   mysql -u root -p
   ```
   Then in MySQL:
   ```sql
   CREATE DATABASE hms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'hms_user'@'localhost' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON hms.* TO 'hms_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

2. **Update `.env` file** in the backend directory:
   ```env
   DATABASE_MODE=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=hms_user
   MYSQL_PASSWORD=your_secure_password
   MYSQL_DATABASE=hms
   MYSQL_CHARSET=utf8mb4
   ```

3. **Re-run database initialization** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/backend
   source venv/Scripts/activate
   python init_db.py
   ```

## Running the Application

### Development Mode

1. **Start the Backend**:
   
   Open Git Bash in the `backend` directory:
   ```bash
   cd /c/Users/Aquacy/Documents/last/backend
   source venv/Scripts/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   The API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`

2. **Start the Frontend** (in a new Git Bash window):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run dev
   ```
   
   The frontend will be available at `http://localhost:9000`

### Production Mode

1. **Build the Frontend** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```
   
   The production files will be in `frontend/dist/spa/`

2. **Run Backend in Production** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/backend
   source venv/Scripts/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## Frontend Production Deployment

Once you have the backend running and accessible to clients, you need to serve the frontend so clients can access it through a web browser. Here are several options:

> **Quick Start**: If you just want to get it running quickly, use **Option 1 (Python HTTP Server)** - it's the simplest and requires no additional software installation.

### Option 1: Using Python HTTP Server (Simplest)

This is the easiest option if you just want to get it running quickly.

1. **Build the frontend** (if not already done):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```

2. **Start a simple HTTP server** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend/dist/spa
   python -m http.server 9000
   ```

3. **Make it accessible on the network**:
   The server will start on `http://localhost:9000`. To make it accessible from other machines, you need to:
   - Use `--bind 0.0.0.0` to listen on all interfaces:
     ```bash
     python -m http.server 9000 --bind 0.0.0.0
     ```

4. **Set up as Windows Service** (using Task Scheduler):
   - Open Task Scheduler (Win + R → `taskschd.msc`)
   - Create Basic Task:
     - Name: "HMS Frontend Server"
     - Trigger: "When the computer starts"
     - Action: "Start a program"
     - Program: `C:\Python3x\python.exe` (or your Python path)
     - Arguments: `-m http.server 9000 --bind 0.0.0.0 --directory "C:\Users\Aquacy\Documents\last\frontend\dist\spa"`
     - Start in: `C:\Users\Aquacy\Documents\last\frontend\dist\spa`

**Access**: Clients can access the frontend at `http://YOUR_SERVER_IP:9000`

### Option 2: Using IIS (Internet Information Services)

IIS is Windows' built-in web server and is ideal for production.

1. **Install IIS** (if not already installed):
   - Open "Server Manager" → "Add Roles and Features"
   - Select "Web Server (IIS)"
   - Install with default features

2. **Build the frontend**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```

3. **Copy files to IIS directory**:
   ```bash
   # Create directory (if it doesn't exist)
   mkdir -p /c/inetpub/wwwroot/hms
   
   # Copy all files from dist/spa to IIS directory
   cp -r /c/Users/Aquacy/Documents/last/frontend/dist/spa/* /c/inetpub/wwwroot/hms/
   ```

4. **Configure IIS**:
   - Open IIS Manager (Win + R → `inetmgr`)
   - Right-click "Sites" → "Add Website"
   - Site name: `HMS`
   - Physical path: `C:\inetpub\wwwroot\hms`
   - Binding: Port `80` (or any port you prefer, e.g., `9000`)
   - Click OK

5. **Configure URL Rewrite** (for Vue Router history mode):
   - Install URL Rewrite module from [iis.net](https://www.iis.net/downloads/microsoft/url-rewrite)
   - In IIS Manager, select your HMS site
   - Double-click "URL Rewrite"
   - Click "Add Rule" → "Blank Rule"
   - Name: `Vue Router History Mode`
   - Pattern: `.*`
   - Conditions: `{REQUEST_FILENAME} !-f` and `{REQUEST_FILENAME} !-d`
   - Action: Rewrite to `/index.html`

6. **Set permissions**:
   - Right-click the `hms` folder → Properties → Security
   - Ensure `IIS_IUSRS` has "Read" permissions

**Access**: Clients can access at `http://YOUR_SERVER_IP` (or `http://YOUR_SERVER_IP:9000` if you used port 9000)

### Option 3: Using Nginx (Lightweight & Fast)

Nginx is a popular, lightweight web server.

1. **Download Nginx for Windows** from [nginx.org](http://nginx.org/en/download.html)

2. **Extract Nginx** to `C:\nginx`

3. **Build the frontend**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```

4. **Configure Nginx**:
   
   Edit `C:\nginx\conf\nginx.conf` and add a server block:
   ```nginx
   server {
       listen       9000;
       server_name  localhost;
       
       root   C:/Users/Aquacy/Documents/last/frontend/dist/spa;
       index  index.html;
       
       # Handle Vue Router history mode
       location / {
           try_files $uri $uri/ /index.html;
       }
       
       # Cache static assets
       location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   }
   ```

5. **Test Nginx** (optional, to verify it works):
   ```bash
   cd /c/nginx
   ./nginx.exe
   ```
   
   Then stop it (Ctrl+C) before setting up as a service.

6. **Set up as Windows Service** (using Task Scheduler):
   - Open Task Scheduler (Win + R → `taskschd.msc`)
   - Create Basic Task:
     - Name: "Nginx Web Server"
     - Trigger: "When the computer starts"
     - Action: "Start a program"
     - Program: `C:\nginx\nginx.exe`
     - Start in: `C:\nginx`
   - Click Finish
   
   The task will start Nginx automatically on server startup.

**Access**: Clients can access at `http://YOUR_SERVER_IP:9000`

### Option 4: Using Node.js http-server (Alternative)

If you prefer a Node.js-based solution:

1. **Install http-server globally**:
   ```bash
   npm install -g http-server
   ```

2. **Build the frontend**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```

3. **Start the server**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend/dist/spa
   http-server -p 9000 -a 0.0.0.0
   ```

4. **Set up as Windows Service** (using NSSM):
   ```bash
   cd /c/nssm/win64
   ./nssm.exe install HMSFrontend "C:\Program Files\nodejs\node.exe"
   ```
   - Arguments: `C:\Users\Aquacy\AppData\Roaming\npm\node_modules\http-server\bin\http-server -p 9000 -a 0.0.0.0`
   - Startup directory: `C:\Users\Aquacy\Documents\last\frontend\dist\spa`

**Access**: Clients can access at `http://YOUR_SERVER_IP:9000`

### Important Notes

1. **API Connection**: The frontend automatically detects the server hostname and connects to the backend on port 8000. Make sure:
   - Backend is running and accessible on port 8000
   - Firewall allows port 8000 (backend) and port 9000 (frontend, if using that port)

2. **Firewall Configuration**: 
   - Ensure port 9000 (or your chosen port) is open in Windows Firewall
   - See [Windows Firewall Configuration](#windows-firewall-configuration) section below

3. **HTTPS (Recommended for Production)**:
   - For production, consider setting up HTTPS using IIS with SSL certificate
   - Or use a reverse proxy (Nginx/IIS) with SSL termination

4. **Rebuilding After Updates**:
   - When you update the frontend code, rebuild and copy files again:
     ```bash
     cd /c/Users/Aquacy/Documents/last/frontend
     npm run build
     # Then copy files to your web server directory
     ```

## Windows Firewall Configuration

To allow access to the application from other machines on the network:

1. **Open Windows Defender Firewall**:
   - Press `Win + R`, type `wf.msc`, press Enter

2. **Create Inbound Rules**:
   - Click "New Rule" → "Port" → Next
   - Select "TCP" and enter port `8000` (backend)
   - Select "Allow the connection" → Next
   - Check all profiles (Domain, Private, Public) → Next
   - Name: "HMS Backend API" → Finish
   
   **For Frontend** (if using port 9000 or custom port):
   - Repeat the above steps for port `9000` (or your chosen frontend port)
   - Name: "HMS Frontend"

3. **Alternative: Allow through Windows Settings**:
   - Settings → Network & Internet → Windows Firewall
   - Advanced settings → Inbound Rules → New Rule
   - Follow the same steps as above

## Running as Windows Service

To run the backend as a Windows service for automatic startup:

### Option 1: Using NSSM (Non-Sucking Service Manager)

1. **Download NSSM** from [nssm.cc](https://nssm.cc/download)

2. **Extract and run** (in Git Bash or Command Prompt):
   ```bash
   # Extract to C:\nssm
   cd /c/nssm/win64
   ./nssm.exe install HMSBackend
   ```
   
   **Note**: NSSM GUI will open. You can also run it directly from Windows Explorer.

3. **Configure the service** (in NSSM GUI or command line):
   - Path: `C:\Python3x\python.exe` (or full path to your Python, e.g., `C:\Users\Aquacy\Documents\last\backend\venv\Scripts\python.exe`)
   - Startup directory: `C:\Users\Aquacy\Documents\last\backend`
   - Arguments: `-m uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Service name: `HMSBackend`

4. **Start the service** (in Git Bash or Command Prompt):
   ```bash
   cd /c/nssm/win64
   ./nssm.exe start HMSBackend
   ```
   
   Or use Windows Services (Win + R → `services.msc`) to start the service.

### Option 2: Using Task Scheduler

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Name: "HMS Backend"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: Full path to `python.exe` in your venv (e.g., `C:\Users\Aquacy\Documents\last\backend\venv\Scripts\python.exe`)
   - Arguments: `-m uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Start in: `C:\Users\Aquacy\Documents\last\backend`

**Note**: Task Scheduler uses Windows paths (backslashes), not Git Bash paths.

## Running Frontend as Windows Service

To run the frontend in development mode (`npm run dev`) as a Windows service for automatic startup:

### Using Task Scheduler

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Name: "HMS Frontend Dev Server"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: Full path to `node.exe` (e.g., `C:\Program Files\nodejs\node.exe`)
   - Arguments: `run dev`
   - Start in: `C:\Users\Aquacy\Documents\last\frontend`

3. **Configure Advanced Settings** (optional but recommended):
   - Right-click the task → Properties
   - **General tab**:
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges" (if needed)
   - **Conditions tab**:
     - Uncheck "Start the task only if the computer is on AC power" (if you want it to run on battery)
   - **Settings tab**:
     - Check "Allow task to be run on demand"
     - Check "Run task as soon as possible after a scheduled start is missed"
     - Set "If the task fails, restart every:" to `1 minute`
     - Set "Attempt to restart up to:" to `3 times`

4. **Test the Task**:
   - Right-click the task → "Run"
   - Check if the frontend starts on port 9000
   - Verify by accessing `http://localhost:9000` in a browser

**Note**: 
- The frontend dev server will be accessible at `http://YOUR_SERVER_IP:9000`
- Make sure port 9000 is open in Windows Firewall (see [Windows Firewall Configuration](#windows-firewall-configuration))
- The dev server will automatically reload when code changes are detected

### Alternative: Using npm.cmd (if node.exe path has issues)

If the direct path to `node.exe` doesn't work, you can use `npm.cmd`:

1. **Create Basic Task**:
   - Name: "HMS Frontend Dev Server"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: `C:\Program Files\nodejs\npm.cmd`
   - Arguments: `run dev`
   - Start in: `C:\Users\Aquacy\Documents\last\frontend`

### Running Frontend in Production Mode as Service

If you prefer to run the built frontend (production mode) instead of dev mode:

1. **First, build the frontend** (one-time setup):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run build
   ```

2. **Then use one of the production deployment options** (Option 1, 2, 3, or 4 from the [Frontend Production Deployment](#frontend-production-deployment) section above)

3. **Set up the chosen production server as a service** using Task Scheduler (instructions are included in each option)

## Troubleshooting

### Python Virtual Environment Issues

**Problem**: Virtual environment activation fails in Git Bash

**Solution**:
```bash
# Make sure you're using the correct activation script for Git Bash
source venv/Scripts/activate

# If that doesn't work, try:
source venv/bin/activate
```

**Note**: In Git Bash, use `source venv/Scripts/activate` (forward slashes), not PowerShell's `.\venv\Scripts\Activate.ps1`.

### Port Already in Use

**Problem**: Port 8000 or 9000 is already in use

**Solution** (in Git Bash):
```bash
# Find process using port 8000
netstat -ano | grep :8000

# Or use PowerShell command (works in Git Bash too):
cmd //c "netstat -ano | findstr :8000"

# Kill the process (replace PID with actual process ID)
# In Git Bash, you can use:
taskkill //PID <PID> //F

# Or use PowerShell:
powershell -Command "Stop-Process -Id <PID> -Force"
```

### Database Connection Issues

**Problem**: Cannot connect to MySQL

**Solutions**:
1. Verify MySQL service is running (use PowerShell or Windows Services):
   ```powershell
   # In PowerShell:
   Get-Service MySQL*
   ```
   
   Or check Windows Services (Win + R → `services.msc`)

2. Check MySQL credentials in `.env` file

3. Test connection (in Git Bash):
   ```bash
   mysql -u root -p
   ```

### CORS Errors

**Problem**: Frontend cannot connect to backend

**Solution**: 
- Verify backend is running on port 8000
- Check `API_BASE_URL` in `frontend/quasar.config.js`
- Ensure backend CORS settings allow your frontend origin

### Module Not Found Errors

**Problem**: Python modules not found

**Solution** (in Git Bash):
```bash
# Ensure virtual environment is activated
source venv/Scripts/activate

# Verify you're in the virtual environment (should see (venv) in prompt)
which python  # Should point to venv/Scripts/python

# Reinstall dependencies
pip install -r requirements.txt
```

### Node.js Build Errors

**Problem**: Frontend build fails

**Solution** (in Git Bash):
```bash
# Clear cache and reinstall
cd /c/Users/Aquacy/Documents/last/frontend
rm -rf node_modules
rm -rf .quasar
npm install
npm run build
```

### Vite Preload-Helper Error

**Problem**: Build fails with error: `Missing "./preload-helper" export in "vite" package`

**Solution** (in Git Bash):
```bash
cd /c/Users/Aquacy/Documents/last/frontend

# Clean Quasar cache
npx quasar clean

# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
npm install

# Try building again
npm run build
```

**If the above doesn't work**, the `package.json` has been updated with npm overrides to force a compatible Vite version:

1. **The fix is already in `package.json`**:
   ```json
   "devDependencies": {
     "@quasar/app-vite": "^1.4.0",
     "vite": "2.9.14"
   },
   "overrides": {
     "vite": "2.9.14"
   }
   ```
   
   The `overrides` field forces ALL packages (including nested dependencies) to use Vite 2.9.14, which includes the preload-helper export.

2. **Clean and reinstall** (in Git Bash):
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   
   # Remove everything
   rm -rf node_modules package-lock.json .quasar
   
   # Clear npm cache
   npm cache clean --force
   
   # Reinstall all dependencies (this will apply the overrides)
   npm install
   
   # Clean Quasar cache
   npx quasar clean
   
   # Try building again
   npm run build
   ```

**Note**: The `overrides` field in package.json ensures that even nested vite dependencies (like the one inside @quasar/app-vite) use the compatible version 2.9.14.

**Alternative**: If you're using an older Node.js version, ensure you're using Node.js 18+:
```bash
node --version  # Should be 18.0.0 or higher
```

### Git Bash Path Issues

**Problem**: Commands not found or path issues

**Solution**:
- Git Bash uses Unix-style paths: `/c/Users/...` instead of `C:\Users\...`
- Use forward slashes `/` instead of backslashes `\`
- Drive letters are mounted at `/c/`, `/d/`, etc.
- If you need to use Windows paths, prefix with `cmd //c` or use `cygpath`:
  ```bash
  # Convert Windows path to Git Bash path
  cygpath -u "C:\Users\Aquacy\Documents\last"
  ```

### Frontend Service Not Starting

**Problem**: Frontend dev server task in Task Scheduler doesn't start or fails

**Solutions**:

1. **Check Node.js path**:
   - Verify the path to `node.exe` is correct
   - Common locations:
     - `C:\Program Files\nodejs\node.exe`
     - `C:\Program Files (x86)\nodejs\node.exe`
   - Find it with:
     ```bash
     which node
     # Or in Command Prompt:
     where node
     ```

2. **Check npm path**:
   - If using `npm.cmd`, verify path:
     - `C:\Program Files\nodejs\npm.cmd`

3. **Check working directory**:
   - Ensure "Start in" field in Task Scheduler points to the frontend directory
   - Example: `C:\Users\Aquacy\Documents\last\frontend`

4. **Check task permissions**:
   - Right-click task → Properties → General
   - Select "Run whether user is logged on or not"
   - Check "Run with highest privileges" if needed

5. **View task history**:
   - In Task Scheduler, select your task
   - Click "History" tab to see error messages

6. **Test manually first**:
   ```bash
   cd /c/Users/Aquacy/Documents/last/frontend
   npm run dev
   ```
   - If this works, the issue is with Task Scheduler configuration
   - If this fails, fix the npm/node issue first

7. **Use full paths in Task Scheduler**:
   - Instead of `npm run dev`, try:
   - Program: `C:\Program Files\nodejs\npm.cmd`
   - Arguments: `run dev`
   - Start in: `C:\Users\Aquacy\Documents\last\frontend`

## Security Recommendations

1. **Change Default Passwords**:
   - Change the default admin password immediately
   - Use strong passwords for MySQL

2. **Update SECRET_KEY**:
   - Generate a strong secret key for JWT tokens
   - Use a random string generator

3. **Firewall Rules**:
   - Only open necessary ports
   - Consider restricting access to specific IP ranges

4. **SSL/TLS**:
   - For production, use HTTPS with a reverse proxy (IIS, Nginx)
   - Obtain SSL certificates (Let's Encrypt, etc.)

5. **Regular Backups**:
   - Configure automatic database backups
   - Store backups in a secure location

## Git Bash Quick Reference

### Path Conversion

Git Bash uses Unix-style paths. Here's how to convert Windows paths:

| Windows Path | Git Bash Path |
|-------------|---------------|
| `C:\Users\Aquacy\Documents\last` | `/c/Users/Aquacy/Documents/last` |
| `D:\Projects\hms` | `/d/Projects/hms` |
| `C:\Program Files\Python` | `/c/Program Files/Python` |

**Tips**:
- Use forward slashes `/` instead of backslashes `\`
- Drive letters become `/c/`, `/d/`, etc.
- Spaces in paths work fine (no need to escape)
- To convert a Windows path to Git Bash format:
  ```bash
  cygpath -u "C:\Users\Aquacy\Documents\last"
  ```

### Common Commands

```bash
# Navigate to a directory
cd /c/Users/Aquacy/Documents/last/backend

# List files
ls -la

# Create directory
mkdir -p backups

# Remove directory
rm -rf node_modules

# Copy file
cp .env.example .env

# Edit file (using nano, vim, or notepad)
nano .env
# or
notepad .env  # Opens in Windows Notepad
```

### Virtual Environment Activation

```bash
# Activate (Git Bash)
source venv/Scripts/activate

# Deactivate
deactivate

# Check if activated (you'll see (venv) in prompt)
which python  # Should show path to venv/Scripts/python
```

## Additional Resources

- Backend API Documentation: `http://localhost:8000/docs` (when backend is running)
- Backend README: See `backend/README.md`
- Frontend Setup: See `frontend/SETUP.md`
- Production Deployment: See `backend/DEPLOYMENT.md`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend and frontend specific documentation
3. Check application logs for error messages

---

**Last Updated**: 2024
**Compatible with**: Windows Server 2022
