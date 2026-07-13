#!/bin/bash
# Fix Quasar ESM error on VM
# Usage: ./fix_quasar_esm.sh

set -e

echo "=========================================="
echo "Fixing Quasar ESM Error"
echo "=========================================="
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "Error: This script must be run from the frontend directory"
    echo "Usage: cd frontend && ./fix_quasar_esm.sh"
    exit 1
fi

# Check Node.js version
echo "1. Checking Node.js version..."
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠ Warning: Node.js version is less than 18"
    echo "  Current: $(node --version)"
    echo "  Required: >= 18.0.0"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Node.js version: $(node --version)"
fi
echo ""

# Clean Quasar cache
echo "2. Cleaning Quasar cache..."
npx quasar clean --qconf 2>/dev/null || npx quasar clean 2>/dev/null || true
echo "✓ Quasar cache cleaned"
echo ""

# Remove temporary compiled files
echo "3. Removing temporary files..."
rm -f quasar.config.js.temporary.compiled.*.mjs 2>/dev/null || true
echo "✓ Temporary files removed"
echo ""

# Remove node_modules and package-lock
echo "4. Removing node_modules and package-lock.json..."
read -p "Remove node_modules and package-lock.json? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf node_modules package-lock.json
    echo "✓ Removed node_modules and package-lock.json"
else
    echo "⚠ Skipping removal of node_modules"
fi
echo ""

# Verify quasar.config.js format
echo "5. Verifying quasar.config.js format..."
if grep -q "import.*quasar/wrappers" quasar.config.js 2>/dev/null; then
    echo "✓ quasar.config.js is using ESM format"
else
    echo "⚠ Warning: quasar.config.js might not be in ESM format"
    echo "  First line should be: import { configure } from 'quasar/wrappers';"
fi
echo ""

# Reinstall dependencies
echo "6. Reinstalling dependencies..."
read -p "Run npm install now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    npm install
    echo ""
    echo "✓ Dependencies installed"
else
    echo "⚠ Skipping npm install"
    echo "  Run manually: npm install"
fi
echo ""

echo "=========================================="
echo "Fix Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test the installation: npm run dev"
echo "2. If errors persist, check:"
echo "   - Node.js version: node --version"
echo "   - Quasar version: npm list @quasar/app-vite"
echo "   - Config file format: head -5 quasar.config.js"
echo ""

