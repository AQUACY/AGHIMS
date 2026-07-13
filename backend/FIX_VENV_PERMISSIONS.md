# Fix Virtual Environment Permission Issues

## Problem
Getting `Permission denied` when installing packages in virtual environment, even though you're the owner.

## Solution 1: Fix Ownership (Recommended)

```bash
cd /home/administrator/Desktop/AGHIMS/backend

# Fix ownership of entire venv directory
sudo chown -R administrator:administrator venv/

# Now try installing again
source venv/bin/activate
pip install "apscheduler>=3.10.4"
```

## Solution 2: Fix Permissions

```bash
cd /home/administrator/Desktop/AGHIMS/backend

# Make venv directory writable
chmod -R u+w venv/

# Now try installing
source venv/bin/activate
pip install "apscheduler>=3.10.4"
```

## Solution 3: Recreate Virtual Environment (If above don't work)

```bash
cd /home/administrator/Desktop/AGHIMS/backend

# Backup your .env file (important!)
cp .env .env.backup

# Remove old venv
rm -rf venv

# Create new venv (as your user, not sudo!)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Restore .env
cp .env.backup .env

# Verify APScheduler
python -c "import apscheduler; print('OK')"
```

## Solution 4: Use --user flag (Not recommended for venv, but works)

```bash
cd /home/administrator/Desktop/AGHIMS/backend
source venv/bin/activate

# This installs to user site-packages, not venv
pip install --user "apscheduler>=3.10.4"

# But this might not work if venv isolation is strict
```

## Quick Fix (Try This First)

```bash
cd /home/administrator/Desktop/AGHIMS/backend
sudo chown -R $USER:$USER venv/
source venv/bin/activate
pip install "apscheduler>=3.10.4"
```

## Verify After Fix

```bash
source venv/bin/activate
python -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
```

You should see: `APScheduler version: 3.11.1`

## Why This Happens

The virtual environment directory was likely created with `sudo` or has incorrect ownership, making it unwritable by your user account.

## After Fixing

Restart your server:
```bash
sudo systemctl restart hms-api
```

