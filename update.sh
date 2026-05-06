#!/bin/bash

#===============================================================================
# OMNIBOT v2.7.2 Titan - Update Script
#===============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="/opt/omnibot"
VENV_DIR="$INSTALL_DIR/venv"

# Default GitHub repo (can be overridden)
DEFAULT_REPO="https://github.com/3D-Magic/OmniBot-Testing"
DEFAULT_BRANCH="Omnibot-v2.7.2-Titan"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  OMNIBOT v2.7.2 Titan - Update Script     ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if installation exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo -e "${RED}Error: OMNIBOT not found at $INSTALL_DIR${NC}"
    echo "Please run the install script first."
    exit 1
fi

# Ask for GitHub repository URL
echo -e "${YELLOW}GitHub Repository Configuration${NC}"
echo "--------------------------------"
echo ""
echo -e "Default repository: ${BLUE}$DEFAULT_REPO${NC}"
echo -e "Default branch: ${BLUE}$DEFAULT_BRANCH${NC}"
echo ""
read -p "Enter GitHub repository URL (press Enter for default): " REPO_URL
REPO_URL=${REPO_URL:-$DEFAULT_REPO}

read -p "Enter branch name (press Enter for default '$DEFAULT_BRANCH'): " BRANCH_NAME
BRANCH_NAME=${BRANCH_NAME:-$DEFAULT_BRANCH}

echo ""
echo -e "Using repository: ${BLUE}$REPO_URL${NC}"
echo -e "Using branch: ${BLUE}$BRANCH_NAME${NC}"
echo ""

read -p "Continue with update? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Update cancelled.${NC}"
    exit 0
fi

cd "$INSTALL_DIR"

# Backup current configuration
echo ""
echo -e "${YELLOW}Step 1/6: Creating backup...${NC}"
BACKUP_DIR="$INSTALL_DIR/backups/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp config/settings.json "$BACKUP_DIR/" 2>/dev/null || true
cp config/settings.json "$BACKUP_DIR/settings.json.backup" 2>/dev/null || true
cp -r data "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}Backup created: $BACKUP_DIR${NC}"

# Stop the service
echo ""
echo -e "${YELLOW}Step 2/6: Stopping OMNIBOT service...${NC}"
systemctl stop omnibot 2>/dev/null || true
echo -e "${GREEN}Service stopped${NC}"

# Update from GitHub
echo ""
echo -e "${YELLOW}Step 3/6: Updating from GitHub...${NC}"

# Check if it's a git repo
if [[ -d ".git" ]]; then
    # Update existing repo
    git remote set-url origin "$REPO_URL"
    git fetch origin
    git reset --hard "origin/$BRANCH_NAME"
else
    # Clone fresh
    echo "Cloning fresh repository..."
    rm -rf /tmp/omnibot_update
    git clone --branch "$BRANCH_NAME" "$REPO_URL" /tmp/omnibot_update
    
    # Preserve config and data
    cp config/settings.json /tmp/omnibot_update/config/ 2>/dev/null || true
    cp -r data/* /tmp/omnibot_update/data/ 2>/dev/null || true
    
    # Replace files
    find . -mindepth 1 -maxdepth 1 ! -name 'venv' ! -name 'logs' -exec rm -rf {} +
    cp -r /tmp/omnibot_update/* .
    rm -rf /tmp/omnibot_update
fi

echo -e "${GREEN}Code updated from $REPO_URL ($BRANCH_NAME)${NC}"

# Update Python dependencies
echo ""
echo -e "${YELLOW}Step 4/6: Updating Python dependencies...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt --upgrade
echo -e "${GREEN}Dependencies updated${NC}"

# Restore configuration
echo ""
echo -e "${YELLOW}Step 5/6: Restoring configuration...${NC}"
if [[ -f "$BACKUP_DIR/settings.json" ]]; then
    cp "$BACKUP_DIR/settings.json" config/settings.json
    echo -e "${GREEN}Configuration restored${NC}"
else
    echo -e "${YELLOW}No previous configuration found${NC}"
fi

# Fix permissions
echo ""
echo -e "${YELLOW}Step 6/6: Fixing permissions...${NC}"
chown -R omnibot:omnibot "$INSTALL_DIR" 2>/dev/null || chown -R root:root "$INSTALL_DIR"
chmod +x *.sh 2>/dev/null || true
echo -e "${GREEN}Permissions updated${NC}"

# Restart service
echo ""
echo -e "${YELLOW}Restarting OMNIBOT service...${NC}"
systemctl daemon-reload
systemctl start omnibot
sleep 2

# Check status
echo ""
echo -e "${BLUE}Checking service status...${NC}"
if systemctl is-active --quiet omnibot; then
    echo -e "${GREEN}OMNIBOT is running!${NC}"
else
    echo -e "${RED}OMNIBOT failed to start.${NC}"
    echo "Check logs with: sudo journalctl -u omnibot -f"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Update Complete!                          ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Repository: ${BLUE}$REPO_URL${NC}"
echo -e "Branch: ${BLUE}$BRANCH_NAME${NC}"
echo -e "Backup saved to: ${BLUE}$BACKUP_DIR${NC}"
echo ""
echo "Your settings have been preserved."
