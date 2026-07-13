# Installing MySQL Client Tools for Backups

## Problem
Getting error: "mysqldump not found. Please install MySQL client tools."

## Solution

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install mysql-client
```

### CentOS/RHEL

```bash
sudo yum install mysql
# OR for newer versions
sudo dnf install mysql
```

### Verify Installation

```bash
mysqldump --version
```

You should see: `mysqldump  Ver 8.0.x` or similar.

## Alternative: Python-Based Backup

If you can't install MySQL client tools, the system will automatically use a Python-based backup method. However, this is slower and may not include all database features (like stored procedures, triggers, etc.).

**For production, it's recommended to install MySQL client tools for complete backups.**

## After Installation

Once installed, restart your server:

```bash
sudo systemctl restart hms-api
```

Backup exports should now work correctly.

