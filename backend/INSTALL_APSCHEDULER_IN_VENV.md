# Installing APScheduler in Virtual Environment

## Problem
APScheduler is installed in system Python but your app runs in a virtual environment, so it can't find it.

## Solution

### Step 1: Activate Your Virtual Environment

```bash
cd /home/administrator/Desktop/AGHIMS/backend
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### Step 2: Install APScheduler in the Virtual Environment

```bash
pip install "apscheduler>=3.10.4"
```

**No sudo needed** - virtual environments don't require root permissions.

### Step 3: Verify Installation

```bash
python -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
```

You should see: `APScheduler version: 3.11.1` or similar.

### Step 4: Restart Your Server

```bash
sudo systemctl restart hms-api
```

## Why This Happens

- **System Python**: `/usr/local/lib/python3.8/dist-packages` (where you installed it with sudo)
- **Virtual Environment**: `/home/administrator/Desktop/AGHIMS/backend/venv/lib/python3.8/site-packages` (where your app looks)

Your app uses the virtual environment, so packages must be installed there.

## Quick One-Liner

```bash
cd /home/administrator/Desktop/AGHIMS/backend && source venv/bin/activate && pip install "apscheduler>=3.10.4" && python -c "import apscheduler; print('OK')"
```

## After Installation

The server should now start without the "APScheduler not installed" warning, and scheduled backups will work.

