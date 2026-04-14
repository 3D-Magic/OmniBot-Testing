#!/bin/bash

#===============================================================================
# OMNIBOT v2.7.2 Titan - Uninstall Script
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

INSTALL_DIR="$HOME/omnibot"
SERVICE_NAME="omnibot"

echo -e "${RED}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              OMNIBOT Uninstaller                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo -e "${YELLOW}WARNING: This will completely remove OMNIBOT from your system!${NC}"
echo ""
echo "The following will be removed:"
echo "  - OMNIBOT installation directory: $INSTALL_DIR"
echo "  - Systemd service: $SERVICE_NAME"
echo "  - Launcher command: omnibot"
echo ""

read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo -e "${GREEN}Uninstall cancelled.${NC}"
    exit 0
fi

# Backup reminder
echo ""
echo -e "${YELLOW}Creating final backup...${NC}"
if [[ -d "$INSTALL_DIR" ]]; then
    BACKUP_FILE="$HOME/omnibot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "$BACKUP_FILE" -C "$HOME" omnibot/config omnibot/data 2>/dev/null || true
    echo -e "${GREEN}Backup saved to: $BACKUP_FILE${NC}"
fi

# Stop and disable service
echo ""
echo -e "${YELLOW}Stopping and removing service...${NC}"
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload
echo -e "${GREEN}Service removed${NC}"

# Remove launcher
echo ""
echo -e "${YELLOW}Removing launcher...${NC}"
sudo rm -f /usr/local/bin/omnibot
echo -e "${GREEN}Launcher removed${NC}"

# Remove installation directory
echo ""
echo -e "${YELLOW}Removing installation directory...${NC}"
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}Installation directory removed${NC}"

# Optional: Remove firewall rule
echo ""
read -p "Remove firewall rule for port 5000? (y/N): " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ufw delete allow 5000/tcp 2>/dev/null || true
    echo -e "${GREEN}Firewall rule removed${NC}"
fi

echo ""
echo -e "${GREEN}OMNIBOT has been completely uninstalled.${NC}"
echo ""
echo "Your backup is saved at: $BACKUP_FILE"
echo "To restore configuration later, extract it with:"
echo "  tar -xzf $BACKUP_FILE -C ~"
