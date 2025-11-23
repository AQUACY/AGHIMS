#!/bin/bash
# Quick install script for APScheduler dependency
# Use this if you only need to install the new dependency without reinstalling everything

echo "=========================================="
echo "Installing APScheduler (Database Management)"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo "ERROR: Python 3.7 or higher is required. You have Python $PYTHON_VERSION"
    echo "Please upgrade Python first."
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION (OK)"
echo ""

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Virtual environment not detected."
    echo "It's recommended to use a virtual environment."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
else
    echo "✓ Virtual environment detected: $VIRTUAL_ENV"
    echo ""
fi

# Install APScheduler
echo "Installing APScheduler..."
pip install apscheduler>=3.10.4

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ APScheduler installed successfully!"
    echo "=========================================="
    echo ""
    echo "Verifying installation..."
    python3 -c "import apscheduler; print('APScheduler version:', apscheduler.__version__)"
    echo ""
    echo "Next steps:"
    echo "1. Restart your application server"
    echo "2. Navigate to Admin → Database Management to configure backups"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "✗ Installation failed!"
    echo "=========================================="
    echo ""
    echo "Common issues:"
    echo "1. Python version too old (needs 3.7+)"
    echo "2. pip not installed or outdated"
    echo "3. Network/firewall issues"
    echo ""
    echo "See INSTALL_NEW_DEPENDENCIES.md for troubleshooting."
    exit 1
fi

