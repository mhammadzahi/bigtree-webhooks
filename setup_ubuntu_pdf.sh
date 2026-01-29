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
echo -e "${YELLOW}[1/7] Updating package list...${NC}"
sudo apt-get update -qq

# Install LibreOffice core and writer
echo -e "${YELLOW}[2/7] Installing LibreOffice...${NC}"
sudo apt-get install -y \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-common

# Install Python UNO bridge (critical for unoconv) - Ubuntu 24.04 compatible
echo -e "${YELLOW}[3/7] Installing Python UNO bridge...${NC}"
sudo apt-get install -y python3-uno

# Install UNO libs for Ubuntu 24.04
echo -e "${YELLOW}[4/7] Installing UNO libraries...${NC}"
sudo apt-get install -y \
    libuno-sal3t64 \
    libuno-cppu3t64 \
    libuno-cppuhelpergcc3-3t64 \
    libuno-purpenvhelpergcc3-3t64 \
    libuno-salhelpergcc3-3t64 \
    uno-libs-private 2>/dev/null || echo "Some UNO libs already installed"

# Install unoconv
echo -e "${YELLOW}[5/7] Installing unoconv...${NC}"
sudo apt-get install -y unoconv

# Install additional dependencies
echo -e "${YELLOW}[6/7] Installing fonts...${NC}"
sudo apt-get install -y \
    fonts-liberation \
    fonts-liberation2 \
    fonts-dejavu-core \
    fonts-dejavu \
    fontconfig

# Accept MS fonts EULA automatically
echo -e "${YELLOW}Installing Microsoft fonts (optional)...${NC}"
echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | sudo debconf-set-selections
sudo apt-get install -y ttf-mscorefonts-installer 2>/dev/null || echo "MS fonts installation skipped (optional)"

# Clean up any existing LibreOffice processes
echo -e "${YELLOW}[7/7] Cleaning up LibreOffice processes...${NC}"
pkill -9 soffice 2>/dev/null || true
rm -rf ~/.config/libreoffice/4/user/uno_packages 2>/dev/null || true
rm -rf ~/.cache/libreoffice 2>/dev/null || true

# Update font cache
sudo fc-cache -f -v > /dev/null 2>&1

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

# Check fonts
echo ""
echo "Checking fonts..."
if fc-list | grep -qi "liberation"; then
    echo -e "${GREEN}✓${NC} Liberation fonts: Installed"
else
    echo -e "${YELLOW}⚠${NC} Liberation fonts: Not found (optional)"
fi

if fc-list | grep -qi "dejavu"; then
    echo -e "${GREEN}✓${NC} DejaVu fonts: Installed"
else
    echo -e "${YELLOW}⚠${NC} DejaVu fonts: Not found (optional)"
fi

# Test unoconv with a simple conversion
echo ""
echo "Testing unoconv..."
TEMP_TEST_DIR="/tmp/unoconv_test_$$"
mkdir -p "$TEMP_TEST_DIR"
TEMP_TEST_FILE="$TEMP_TEST_DIR/test.txt"
echo "Test document for unoconv" > "$TEMP_TEST_FILE"

# Try conversion with timeout
if timeout 30 unoconv -f pdf -o "$TEMP_TEST_DIR" "$TEMP_TEST_FILE" 2>&1; then
    if [ -f "$TEMP_TEST_DIR/test.pdf" ]; then
        echo -e "${GREEN}✓${NC} unoconv test successful"
        rm -rf "$TEMP_TEST_DIR"
    else
        echo -e "${RED}✗${NC} unoconv test failed: PDF not created"
        echo ""
        echo "Running diagnostics..."
        unoconv --verbose -f pdf "$TEMP_TEST_FILE" 2>&1 || true
        rm -rf "$TEMP_TEST_DIR"
    fi
else
    echo -e "${RED}✗${NC} unoconv test failed. Running diagnostics..."
    echo ""
    echo "Diagnostic information:"
    echo "1. Checking LibreOffice listener:"
    pgrep -a soffice || echo "  No LibreOffice process running"
    echo ""
    echo "2. Testing LibreOffice directly:"
    soffice --headless --convert-to pdf --outdir "$TEMP_TEST_DIR" "$TEMP_TEST_FILE" 2>&1 || echo "  Direct LibreOffice conversion also failed"
    echo ""
    echo "3. Python UNO import test:"
    python3 -c "import uno; print('  UNO module imported successfully')" 2>&1 || echo "  Failed to import UNO module"
    rm -rf "$TEMP_TEST_DIR"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. If unoconv test failed, try starting LibreOffice listener:"
echo "   unoconv --listener &"
echo ""
echo "2. Restart your Python application:"
echo "   sudo systemctl restart bigtree-webhooks"
echo ""
echo "3. Test PDF generation with a real product and check logs"
echo ""
echo "4. If issues persist, the system will fallback to LibreOffice"
echo ""

# Optional: Start LibreOffice listener for unoconv
read -p "Start LibreOffice listener for unoconv now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting LibreOffice listener..."
    unoconv --listener &
    sleep 2
    if pgrep -f "unoconv.*listener" > /dev/null; then
        echo -e "${GREEN}✓${NC} Listener started successfully"
    else
        echo -e "${RED}✗${NC} Failed to start listener"
    fi
fi

echo ""
echo "Setup script finished!"
