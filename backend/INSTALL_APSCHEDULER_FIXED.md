# Installing APScheduler - Fixed Command

## The Problem

The error `bash: =3.10.4: Permission denied` happens because bash interprets `>=` as a redirection operator. You need to **quote the package name**.

## The Solution

### Since you're in a virtual environment (venv), you DON'T need sudo!

```bash
# You're already in venv (see the (venv) prefix)
# Just use pip directly, no sudo needed:
pip install "apscheduler>=3.10.4"
```

### If you must use sudo (outside venv), quote it:

```bash
sudo pip install "apscheduler>=3.10.4"
# OR
sudo python3 -m pip install "apscheduler>=3.10.4"
```

## Correct Commands

### In Virtual Environment (Recommended - No sudo needed):
```bash
# Activate venv if not already active
source venv/bin/activate

# Install (no sudo!)
pip install "apscheduler>=3.10.4"
```

### Outside Virtual Environment (with sudo):
```bash
# Quote the package name!
sudo pip install "apscheduler>=3.10.4"
# OR
sudo python3 -m pip install "apscheduler>=3.10.4"
```

## Why This Happens

In bash, `>=` is a comparison operator. When you write:
```bash
pip install apscheduler>=3.10.4
```

Bash tries to interpret `>=3.10.4` as a command or redirection, causing the error.

## Quick Fix for Your Situation

Since you're already in `(venv)`, just run:

```bash
pip install "apscheduler>=3.10.4"
```

No sudo needed! Virtual environments don't require root permissions.

## Verify Installation

```bash
python -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
```

## Alternative: Install from requirements.txt

If you want to install all dependencies:

```bash
# In your venv
pip install -r requirements.txt
```

This will install APScheduler along with all other dependencies.

