#!/bin/bash

# PDF Generation Dependencies Setup Script for Ubuntu
# This script installs all necessary tools for high-quality PDF generation

set -e  # Exit on any error

echo "=========================================="
echo "PDF Generation Setup for Ubuntu"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}Warning: Running as root. This is not recommended.${NC}"
    echo "Press Ctrl+C to cancel, or Enter to continue..."
    read
fi

# Update package list
echo -e "${YELLOW}[1/6] Updating package list...${NC}"
sudo apt-get update -qq

# Install LibreOffice core and writer
echo -e "${YELLOW}[2/6] Installing LibreOffice...${NC}"
sudo apt-get install -y \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-common

# Install Python UNO bridge (critical for unoconv)
echo -e "${YELLOW}[3/6] Installing Python UNO bridge...${NC}"
sudo apt-get install -y \
    python3-uno \
    uno-libs3

# Install unoconv
echo -e "${YELLOW}[4/6] Installing unoconv...${NC}"
sudo apt-get install -y unoconv

# Install additional dependencies
echo -e "${YELLOW}[5/6] Installing additional dependencies...${NC}"
sudo apt-get install -y \
    fonts-liberation \
    fonts-dejavu-core \
    ttf-mscorefonts-installer 2>/dev/null || echo "MS fonts installation skipped (optional)"

# Clean up any existing LibreOffice processes
echo -e "${YELLOW}[6/6] Cleaning up LibreOffice processes...${NC}"
pkill -9 soffice 2>/dev/null || true
rm -rf ~/.config/libreoffice/4/user/uno_packages 2>/dev/null || true

echo ""
echo -e "${GREEN}=========================================="
echo "Installation Complete!"
echo "==========================================${NC}"
echo ""

# Verify installations
echo "Verifying installations..."
echo ""

# Check LibreOffice
if command -v soffice &> /dev/null; then
    LIBREOFFICE_VERSION=$(soffice --version 2>/dev/null || echo "Unknown")
    echo -e "${GREEN}✓${NC} LibreOffice: $LIBREOFFICE_VERSION"
else
    echo -e "${RED}✗${NC} LibreOffice: Not found"
fi

# Check unoconv
if command -v unoconv &> /dev/null; then
    UNOCONV_VERSION=$(unoconv --version 2>&1 | head -n1 || echo "Unknown")
    echo -e "${GREEN}✓${NC} unoconv: $UNOCONV_VERSION"
else
    echo -e "${RED}✗${NC} unoconv: Not found"
fi

# Check Python UNO
if python3 -c "import uno" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Python UNO bridge: Installed"
else
    echo -e "${RED}✗${NC} Python UNO bridge: Not found"
    echo -e "   ${YELLOW}This may cause unoconv to fail. Try: sudo apt-get install python3-uno${NC}"
fi

# Test unoconv with verbose output
echo ""
echo "Testing unoconv..."
TEMP_TEST_FILE="/tmp/test_unoconv_$$.txt"
echo "Test document" > "$TEMP_TEST_FILE"

if unoconv -f pdf "$TEMP_TEST_FILE" 2>&1 | grep -q "Error"; then
    echo -e "${RED}✗${NC} unoconv test failed. Running diagnostics..."
    echo ""
    echo "Diagnostic information:"
    unoconv --verbose -f pdf "$TEMP_TEST_FILE" 2>&1 || true
else
    echo -e "${GREEN}✓${NC} unoconv test successful"
    rm -f "${TEMP_TEST_FILE%.*}.pdf" 2>/dev/null
fi

rm -f "$TEMP_TEST_FILE" 2>/dev/null

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart your Python application"
echo "2. Test PDF generation with a real product"
echo "3. Monitor the logs for conversion method used"
echo ""
echo "If unoconv still fails, LibreOffice will be used as fallback."
echo ""
