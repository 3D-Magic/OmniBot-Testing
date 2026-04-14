#!/bin/bash
# OMNIBOT v2.7.2 Titan - Raspberry Pi 5 Install Script
# For Debian Trixie

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/omnibot"
SERVICE_USER="omnibot"
DASHBOARD_PORT=8081
VNC_PORT=5900

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  OMNIBOT v2.7.2 Titan - Raspberry Pi 5   ${NC}"
echo -e "${BLUE}         Installation Script              ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Check for Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Step 1/10: Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${BLUE}Step 2/10: Installing system dependencies...${NC}"
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nano \
    htop \
    i2c-tools \
    network-manager \
    x11-xserver-utils \
    xautolock \
    unclutter \
    chromium-browser \
    realvnc-vnc-server \
    realvnc-vnc-viewer

# Enable I2C and SPI for hardware features
echo -e "${BLUE}Step 3/10: Enabling hardware interfaces...${NC}"
raspi-config nonint do_i2c 0
raspi-config nonint do_spi 0

echo -e "${BLUE}Step 4/10: Creating service user...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
fi

echo -e "${BLUE}Step 5/10: Setting up installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/backups"

# Copy files if running from local directory
if [ -f "app.py" ]; then
    echo -e "${BLUE}Copying local files...${NC}"
    cp -r . "$INSTALL_DIR/"
else
    echo -e "${BLUE}Cloning from GitHub...${NC}"
    cd /tmp
    git clone -b Omnibot-v2.7.2-Titan https://github.com/3D-Magic/OmniBot-Testing.git omnibot_temp
    cp -r omnibot_temp/* "$INSTALL_DIR/"
    rm -rf omnibot_temp
fi

echo -e "${BLUE}Step 6/10: Setting up Python virtual environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install wheel

# Install Python dependencies
echo -e "${BLUE}Installing Python packages...${NC}"
pip install flask flask-socketio flask-session python-socketio
pip install alpaca-py
pip install python-binance
pip install paypalrestsdk
pip install pandas numpy
pip install ib-insync

echo -e "${BLUE}Step 7/10: Setting permissions...${NC}"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR"/*.sh 2>/dev/null || true

# Create systemd service for OMNIBOT
echo -e "${BLUE}Step 8/10: Creating systemd service...${NC}"
cat > /etc/systemd/system/omnibot.service << 'EOF'
[Unit]
Description=OMNIBOT v2.7.2 Titan Trading Bot
After=network.target

[Service]
Type=simple
User=omnibot
Group=omnibot
WorkingDirectory=/opt/omnibot
Environment=PATH=/opt/omnibot/venv/bin
Environment=PYTHONPATH=/opt/omnibot
Environment=FLASK_ENV=production
Environment=SECRET_KEY=change-this-in-production
ExecStart=/opt/omnibot/venv/bin/python /opt/omnibot/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=omnibot

[Install]
WantedBy=multi-user.target
EOF

# Create kiosk mode service for dashboard display
echo -e "${BLUE}Step 9/10: Setting up kiosk mode...${NC}"
cat > /etc/systemd/system/omnibot-kiosk.service << EOF
[Unit]
Description=OMNIBOT Dashboard Kiosk
After=omnibot.service graphical.target
Wants=omnibot.service

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium-browser \
    --noerrdialogs \
    --disable-infobars \
    --kiosk \
    --app=http://localhost:$DASHBOARD_PORT \
    --disable-features=TranslateUI \
    --disable-translate \
    --disable-save-password-bubble \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --no-first-run \
    --password-store=basic
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# Enable VNC Server
echo -e "${BLUE}Configuring VNC server...${NC}"
raspi-config nonint do_vnc 0

# Create autostart for desktop
echo -e "${BLUE}Creating desktop autostart...${NC}"
mkdir -p /home/pi/.config/autostart
cat > /home/pi/.config/autostart/omnibot.desktop << EOF
[Desktop Entry]
Type=Application
Name=OMNIBOT Dashboard
Exec=/usr/bin/chromium-browser --kiosk --app=http://localhost:$DASHBOARD_PORT
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
chown -R pi:pi /home/pi/.config

echo -e "${BLUE}Step 10/10: Enabling services...${NC}"
systemctl daemon-reload
systemctl enable omnibot.service
systemctl enable omnibot-kiosk.service

# Create update script
cat > "$INSTALL_DIR/update.sh" << 'EOF'
#!/bin/bash
# OMNIBOT Update Script

echo "Updating OMNIBOT..."
cd /opt/omnibot

# Backup current installation
echo "Creating backup..."
BACKUP_DIR="/opt/omnibot/backups/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r config "$BACKUP_DIR/" 2>/dev/null || true
cp -r data "$BACKUP_DIR/" 2>/dev/null || true

# Pull latest changes
echo "Pulling latest changes..."
git pull origin Omnibot-v2.7.2-Titan

# Update Python packages
echo "Updating Python packages..."
source venv/bin/activate
pip install --upgrade -r requirements.txt 2>/dev/null || pip install --upgrade alpaca-py python-binance paypalrestsdk pandas numpy flask flask-socketio

# Restart service
echo "Restarting OMNIBOT..."
systemctl restart omnibot

echo "Update complete!"
EOF
chmod +x "$INSTALL_DIR/update.sh"

# Create uninstall script
cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash
# OMNIBOT Uninstall Script

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Uninstalling OMNIBOT..."

# Stop and disable services
systemctl stop omnibot 2>/dev/null || true
systemctl stop omnibot-kiosk 2>/dev/null || true
systemctl disable omnibot 2>/dev/null || true
systemctl disable omnibot-kiosk 2>/dev/null || true

# Remove systemd services
rm -f /etc/systemd/system/omnibot.service
rm -f /etc/systemd/system/omnibot-kiosk.service
systemctl daemon-reload

# Remove installation directory
read -p "Remove all OMNIBOT data? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /opt/omnibot
    echo "All OMNIBOT data removed."
else
    echo "Keeping data at /opt/omnibot"
fi

# Remove user
read -p "Remove omnibot user? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    userdel omnibot 2>/dev/null || true
    echo "User removed."
fi

echo "Uninstall complete!"
EOF
chmod +x "$INSTALL_DIR/uninstall.sh"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation Complete!                  ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}OMNIBOT has been installed to:${NC} $INSTALL_DIR"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Start OMNIBOT:        sudo systemctl start omnibot"
echo "2. View status:           sudo systemctl status omnibot"
echo "3. View logs:             sudo journalctl -u omnibot -f"
echo "4. Open dashboard:        http://$(hostname -I | awk '{print $1}'):$DASHBOARD_PORT"
echo ""
echo -e "${YELLOW}Default login:${NC}"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo -e "${YELLOW}VNC Access:${NC}"
echo "  Address: $(hostname -I | awk '{print $1}'):$VNC_PORT"
echo ""
echo -e "${YELLOW}Kiosk Mode:${NC}"
echo "  Dashboard will auto-start on boot"
echo "  Screen will sleep after 10 minutes of inactivity"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  Update:   sudo /opt/omnibot/update.sh"
echo "  Uninstall: sudo /opt/omnibot/uninstall.sh"
echo ""
echo -e "${GREEN}Happy Trading!${NC}"
