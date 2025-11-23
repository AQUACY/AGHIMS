#!/bin/bash
# Fix virtual environment permissions

echo "Fixing virtual environment permissions..."
cd /home/administrator/Desktop/AGHIMS/backend

# Fix ownership
sudo chown -R administrator:administrator venv/

# Fix permissions
chmod -R u+w venv/

echo "Permissions fixed!"
echo ""
echo "Now activate venv and install:"
echo "  source venv/bin/activate"
echo "  pip install \"apscheduler>=3.10.4\""
