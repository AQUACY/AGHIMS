# Fixing Permission Issues with pip install

If you're getting "permission denied" even with sudo, try these solutions:

## Solution 1: Use --user flag (No sudo needed)

```bash
/usr/bin/python3 -m pip install --user apscheduler>=3.10.4
```

This installs to your user directory, no permissions needed.

## Solution 2: Fix pip cache permissions

```bash
# Clear pip cache
sudo rm -rf ~/.cache/pip

# Or fix permissions
sudo chown -R $USER:$USER ~/.cache/pip

# Then try again
sudo /usr/bin/python3 -m pip install apscheduler>=3.10.4
```

## Solution 3: Use virtual environment (Recommended for production)

```bash
cd /path/to/your/backend

# Create venv if it doesn't exist
/usr/bin/python3 -m venv venv

# Activate it
source venv/bin/activate

# Install (no sudo needed in venv)
pip install apscheduler>=3.10.4
```

## Solution 4: Check Python installation permissions

```bash
# Check who owns Python
ls -la /usr/bin/python3

# Check pip location
/usr/bin/python3 -m pip --version

# Check if pip directory is writable
ls -la $(/usr/bin/python3 -m pip show pip | grep Location | cut -d' ' -f2)
```

## Solution 5: Install to specific location

```bash
# Install to a writable location
sudo /usr/bin/python3 -m pip install --target=/opt/hms/venv/lib/python3.x/site-packages apscheduler>=3.10.4
```

## Solution 6: Use ensurepip to reinstall pip

```bash
# Reinstall pip
sudo /usr/bin/python3 -m ensurepip --upgrade

# Then try installation
sudo /usr/bin/python3 -m pip install apscheduler>=3.10.4
```

## Solution 7: Check for virtual environment in systemd service

If your app runs via systemd, check if it uses a virtual environment:

```bash
# Check your service file
cat /etc/systemd/system/hms-api.service

# Look for ExecStart - it might point to a venv
# If so, activate that venv and install there
```

## Solution 8: Install using apt/yum (if available)

```bash
# Ubuntu/Debian - check if available
apt search python3-apscheduler

# If not available, use pip with --break-system-packages (Python 3.12+)
sudo /usr/bin/python3 -m pip install --break-system-packages apscheduler>=3.10.4
```

## Solution 9: Check SELinux/AppArmor (if enabled)

```bash
# Check SELinux status
getenforce

# If enforcing, might need to allow pip
# Or temporarily set to permissive for installation
sudo setenforce 0
sudo /usr/bin/python3 -m pip install apscheduler>=3.10.4
sudo setenforce 1
```

## Solution 10: Use pipx (if available)

```bash
# Install pipx
sudo apt install pipx  # Ubuntu/Debian

# Use pipx
pipx install apscheduler
```

## Most Common Solution for Production

**Use virtual environment - this is the recommended approach:**

```bash
# 1. Navigate to your backend directory
cd /path/to/your/backend

# 2. Check if venv exists
ls -la venv/

# 3. If no venv, create it
/usr/bin/python3 -m venv venv

# 4. Activate it
source venv/bin/activate

# 5. Install (no sudo needed!)
pip install apscheduler>=3.10.4

# 6. Verify
python -c "import apscheduler; print(apscheduler.__version__)"

# 7. Make sure your systemd service uses this venv
# Check /etc/systemd/system/hms-api.service
# ExecStart should be: /path/to/backend/venv/bin/python -m uvicorn ...
```

## Debug: Get More Information

```bash
# See what error you're actually getting
sudo /usr/bin/python3 -m pip install -v apscheduler>=3.10.4

# Check pip configuration
/usr/bin/python3 -m pip config list

# Check where pip wants to install
/usr/bin/python3 -m pip show -f pip
```

## Quick Test

Try this sequence:

```bash
# 1. Try user install (no sudo)
/usr/bin/python3 -m pip install --user apscheduler>=3.10.4

# 2. If that works, verify
/usr/bin/python3 -c "import apscheduler; print('OK')"

# 3. If user install works, the issue is system-level permissions
# Use virtual environment instead
```

