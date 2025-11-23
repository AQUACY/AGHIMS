#!/bin/bash
# Quick setup script for HMS on Ubuntu VM
# This script automates the initial setup process

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "HMS VM Quick Setup Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Get application directory
read -p "Enter application directory [/opt/hms]: " APP_DIR
APP_DIR=${APP_DIR:-/opt/hms}

# Get database password
read -sp "Enter MySQL password for hms_user: " DB_PASSWORD
echo ""

# Update system
echo ""
echo "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo ""
echo "Installing required packages..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    mysql-server \
    mysql-client \
    git \
    curl \
    wget \
    vim \
    htop \
    ntpdate

# Setup MySQL
echo ""
echo "Setting up MySQL..."
mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS hms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hms_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON hms.* TO 'hms_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# Create application directory
echo ""
echo "Creating application directory..."
mkdir -p "$APP_DIR"
chown $SUDO_USER:$SUDO_USER "$APP_DIR"

# Copy date management scripts
echo ""
echo "Installing date management scripts..."
cp "$(dirname "$0")/SET_OLD_DATE.sh" /usr/local/bin/
cp "$(dirname "$0")/RESET_DATE.sh" /usr/local/bin/
chmod +x /usr/local/bin/SET_OLD_DATE.sh
chmod +x /usr/local/bin/RESET_DATE.sh

echo ""
echo -e "${GREEN}✓ Quick setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Copy your application files to: $APP_DIR"
echo "2. Setup backend:"
echo "   cd $APP_DIR/backend"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   cp .env.example .env"
echo "   # Edit .env with MySQL credentials"
echo "   python run_migrations.py"
echo "   python init_db.py"
echo ""
echo "3. Use date management:"
echo "   sudo SET_OLD_DATE.sh 2024-01-01  # Set to old date"
echo "   sudo RESET_DATE.sh                # Reset to current date"
echo ""

