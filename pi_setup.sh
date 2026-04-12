#!/bin/bash
# OMNIBOT v2.7 Titan - Pi Setup Script
# Run this on the Raspberry Pi to deploy from GitHub

set -e

echo "=========================================="
echo "OMNIBOT v2.7 Titan - Pi Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/omnibot"
GITHUB_URL="https://github.com/3D-Magic/OmniBot-Testing.git"
BRANCH="Omnibot-v2.7.2-Titan"
TEMP_DIR="/tmp/omnibot_install"

echo -e "${YELLOW}[1/7] Stopping existing OMNIBOT service...${NC}"
sudo systemctl stop omnibot-dashboard 2>/dev/null || true
echo -e "${GREEN}✓ Service stopped${NC}"

echo ""
echo -e "${YELLOW}[2/7] Backing up current installation...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    BACKUP_NAME="/opt/omnibot.backup.$(date +%Y%m%d_%H%M%S)"
    sudo mv "$INSTALL_DIR" "$BACKUP_NAME"
    echo -e "${GREEN}✓ Backed up to $BACKUP_NAME${NC}"
else
    echo -e "${GREEN}✓ No existing installation to backup${NC}"
fi

echo ""
echo -e "${YELLOW}[3/7] Installing git (if needed)...${NC}"
if ! command -v git &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y git
fi
echo -e "${GREEN}✓ Git ready${NC}"

echo ""
echo -e "${YELLOW}[4/7] Cloning from GitHub...${NC}"
sudo rm -rf "$TEMP_DIR"
sudo git clone --branch "$BRANCH" --single-branch "$GITHUB_URL" "$TEMP_DIR"
echo -e "${GREEN}✓ Cloned from GitHub${NC}"

echo ""
echo -e "${YELLOW}[5/7] Running installer...${NC}"
cd "$TEMP_DIR/omnibot_modular"
sudo bash install.sh
echo -e "${GREEN}✓ Installation complete${NC}"

echo ""
echo -e "${YELLOW}[6/7] Cleaning up...${NC}"
sudo rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Cleanup done${NC}"

echo ""
echo -e "${YELLOW}[7/7] Checking service status...${NC}"
sleep 2
if sudo systemctl is-active --quiet omnibot-dashboard; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs: sudo journalctl -u omnibot-dashboard -n 50"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
IP=$(hostname -I | awk '{print $1}')
echo "Dashboard URL: http://$IP:8081"
echo "Login: admin / admin"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status omnibot-dashboard"
echo "  sudo systemctl restart omnibot-dashboard"
echo "  sudo journalctl -u omnibot-dashboard -f"
echo ""
