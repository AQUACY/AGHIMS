# Installing New Dependencies

This guide helps you install new dependencies that were added to the system, especially when upgrading or when dependencies fail due to Python version issues.

## New Dependency: APScheduler

The database management feature requires **APScheduler** (Advanced Python Scheduler) for scheduled backups.

### Quick Install (Recommended)

**For Linux/Mac:**
```bash
cd backend
./QUICK_INSTALL_APSCHEDULER.sh
```

**For Windows:**
```cmd
cd backend
QUICK_INSTALL_APSCHEDULER.bat
```

### Manual Quick Install

If you prefer to install manually:

```bash
# Navigate to backend directory
cd backend

# Install APScheduler only
pip install apscheduler>=3.10.4
```

**One-liner (copy and paste):**
```bash
pip install apscheduler>=3.10.4
```

### For Production (with Virtual Environment)

```bash
# Activate your virtual environment first
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install APScheduler
pip install apscheduler>=3.10.4
```

### Python Version Requirements

**APScheduler 3.10.4 requires Python 3.7 or higher.**

Check your Python version:
```bash
python --version
# OR
python3 --version
```

If you have Python 3.6 or lower, you need to upgrade Python first.

### Troubleshooting

#### Issue: "No module named 'apscheduler'"
**Solution**: Install APScheduler
```bash
pip install apscheduler>=3.10.4
```

#### Issue: "ERROR: Could not find a version that satisfies the requirement apscheduler"
**Possible Causes**:
1. **Python version too old**: APScheduler 3.10.4 requires Python 3.7+
   - **Solution**: Upgrade Python to 3.7 or higher

2. **pip version too old**
   - **Solution**: Upgrade pip
   ```bash
   pip install --upgrade pip
   ```

3. **Network/firewall issues**
   - **Solution**: Check internet connection or use a different package index
   ```bash
   pip install --index-url https://pypi.org/simple/ apscheduler>=3.10.4
   ```

#### Issue: "ERROR: Failed building wheel for apscheduler"
**Solution**: Install build dependencies
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip

# CentOS/RHEL
sudo yum install python3-devel python3-pip

# Then retry
pip install apscheduler>=3.10.4
```

#### Issue: "Command 'pip' not found"
**Solution**: Use pip3 or install pip
```bash
# Try pip3 instead
pip3 install apscheduler>=3.10.4

# OR install pip
python -m ensurepip --upgrade
```

### Verify Installation

After installation, verify it works:
```bash
python -c "import apscheduler; print(apscheduler.__version__)"
```

You should see: `3.10.4` or higher

### Production Deployment

For production servers, install all dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Or install just the new one:
```bash
pip install apscheduler>=3.10.4
```

### Systemd Service Restart

After installing dependencies, restart your service:
```bash
# If using systemd
sudo systemctl restart hms-api

# Or if running manually, restart your uvicorn process
```

### All New Dependencies Added

The following dependencies were added for the database management feature:

1. **APScheduler** (>=3.10.4) - For scheduled backups

To install all new dependencies at once:
```bash
pip install apscheduler>=3.10.4
```

### Checking Current Installation

Check if APScheduler is installed:
```bash
pip show apscheduler
```

Check all installed packages:
```bash
pip list | grep -i scheduler
```

### Upgrading Existing Installation

If APScheduler is already installed but you need to upgrade:
```bash
pip install --upgrade apscheduler>=3.10.4
```

### Virtual Environment Best Practice

Always use a virtual environment in production:

```bash
# Create virtual environment (if not exists)
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependency
pip install apscheduler>=3.10.4

# Verify
python -c "import apscheduler; print('OK')"
```

### Docker Installation

If using Docker, add to your Dockerfile:
```dockerfile
RUN pip install apscheduler>=3.10.4
```

Or rebuild:
```bash
docker-compose build
docker-compose up -d
```

### Need Help?

If you encounter issues:
1. Check Python version: `python --version` (needs 3.7+)
2. Check pip version: `pip --version`
3. Try upgrading pip: `pip install --upgrade pip`
4. Check error messages for specific issues
5. Review the troubleshooting section above

