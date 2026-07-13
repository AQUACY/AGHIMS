# Installing APScheduler in Production

This guide helps you install APScheduler in production environments where you might encounter permission issues.

## Quick Solutions

### Solution 1: Use `python -m pip` (Recommended)

Instead of `pip install`, use:
```bash
python -m pip install apscheduler>=3.10.4
```

Or if you have `python3`:
```bash
python3 -m pip install apscheduler>=3.10.4
```

### Solution 2: Use Virtual Environment

If you're using a virtual environment:

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Then install
pip install apscheduler>=3.10.4
# OR
python -m pip install apscheduler>=3.10.4
```

### Solution 3: Install with User Flag

If you don't have admin/sudo access:
```bash
python -m pip install --user apscheduler>=3.10.4
```

### Solution 4: Use sudo with python -m pip

If you need sudo:
```bash
sudo python -m pip install apscheduler>=3.10.4
# OR
sudo python3 -m pip install apscheduler>=3.10.4
```

## Linux Production Server

### If using systemd service:

1. **Find your Python path:**
   ```bash
   which python3
   # OR check your systemd service file
   cat /etc/systemd/system/hms-api.service | grep ExecStart
   ```

2. **Install using the correct Python:**
   ```bash
   /usr/bin/python3 -m pip install apscheduler>=3.10.4
   # OR if using virtual environment
   /path/to/venv/bin/pip install apscheduler>=3.10.4
   ```

### If using virtual environment:

```bash
# Navigate to your project
cd /path/to/your/backend

# Activate virtual environment
source venv/bin/activate

# Install
pip install apscheduler>=3.10.4

# Verify
python -c "import apscheduler; print(apscheduler.__version__)"
```

### If pip is not found:

```bash
# Install pip first (if not installed)
sudo apt-get update
sudo apt-get install python3-pip  # Ubuntu/Debian
# OR
sudo yum install python3-pip  # CentOS/RHEL

# Then install APScheduler
python3 -m pip install apscheduler>=3.10.4
```

## Windows Production Server

### Using Python directly:

```cmd
cd backend
python -m pip install apscheduler>=3.10.4
```

### Using virtual environment:

```cmd
cd backend
venv\Scripts\activate
python -m pip install apscheduler>=3.10.4
```

## Troubleshooting Permission Issues

### Error: "Permission denied" or "Access denied"

**Option 1: Use --user flag**
```bash
python -m pip install --user apscheduler>=3.10.4
```

**Option 2: Fix permissions**
```bash
# Check who owns the Python installation
ls -la $(which python3)

# If needed, use sudo
sudo python3 -m pip install apscheduler>=3.10.4
```

**Option 3: Use virtual environment (Best Practice)**
```bash
# Create virtual environment if it doesn't exist
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install
pip install apscheduler>=3.10.4
```

### Error: "pip: command not found"

Use `python -m pip` instead:
```bash
python -m pip install apscheduler>=3.10.4
python3 -m pip install apscheduler>=3.10.4
```

### Error: "No module named pip"

Install pip first:
```bash
# Linux
sudo apt-get install python3-pip  # Ubuntu/Debian
sudo yum install python3-pip      # CentOS/RHEL

# Or use ensurepip
python3 -m ensurepip --upgrade
```

## Verify Installation

After installation, verify it works:
```bash
python -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
```

You should see: `APScheduler version: 3.10.4` or higher

## Restart Your Service

After installing, restart your application:

```bash
# If using systemd
sudo systemctl restart hms-api

# If using supervisor
sudo supervisorctl restart hms-api

# If running manually
# Stop and restart your uvicorn process
```

## Production Best Practices

1. **Always use virtual environments** in production
2. **Use `python -m pip`** instead of `pip` directly
3. **Document your Python/pip paths** for your deployment
4. **Test installation** before deploying to production
5. **Keep requirements.txt updated** and use it for deployments

## Quick Reference

```bash
# Most common solution
python3 -m pip install apscheduler>=3.10.4

# With virtual environment
source venv/bin/activate && pip install apscheduler>=3.10.4

# With sudo (if needed)
sudo python3 -m pip install apscheduler>=3.10.4

# User installation (no sudo needed)
python3 -m pip install --user apscheduler>=3.10.4
```

