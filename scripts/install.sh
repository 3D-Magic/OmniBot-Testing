#!/bin/bash
# OMNIBOT TITAN v2.7.2 - Installation Script
# For Raspberry Pi with auto-start and kiosk mode

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

VERSION="2.7.2"
INSTALL_DIR="/opt/omnibot"
USER="omnibot"

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  OMNIBOT TITAN v${VERSION}${NC}"
echo -e "${CYAN}  Installation Script${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (sudo)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo -e "${CYAN}Detected OS: $OS $VER${NC}"
echo ""

# Step 1: Update system
echo -e "${CYAN}[1/10] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq 2>/dev/null || true

# Step 2: Install system dependencies
echo -e "${CYAN}[2/10] Installing system dependencies...${NC}"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3-pip \
    python3-venv \
    python3-full \
    python3-pyqt5 \
    python3-pyqt5.qtwebengine \
    xserver-xorg \
    lightdm \
    openbox \
    lxde-core \
    lxpanel \
    pcmanfm \
    unclutter \
    xdotool \
    x11-xserver-utils \
    avahi-daemon \
    git \
    curl \
    wget \
    nano \
    htop \
    2>/dev/null || true

# Step 3: Create omnibot user
echo -e "${CYAN}[3/10] Creating omnibot user...${NC}"
if ! id -u "$USER" &>/dev/null; then
    useradd -m -s /bin/bash "$USER"
    echo "$USER:$USER" | chpasswd
    usermod -aG sudo,video,audio,gpio,i2c,spi,input "$USER"
    echo -e "${GREEN}Created user: $USER (password: $USER)${NC}"
else
    echo -e "${YELLOW}User $USER already exists${NC}"
fi

# Step 4: Create directory structure
echo -e "${CYAN}[4/10] Creating directory structure...${NC}"
mkdir -p "$INSTALL_DIR"/{src,config,templates,static/css,static/js,logs}
mkdir -p /home/$USER/.config/{autostart,openbox,lxsession/LXDE}

# Step 5: Set up Python virtual environment
echo -e "${CYAN}[5/10] Setting up Python environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install -q flask==3.0.0 flask-socketio==5.3.0 eventlet==0.33.3 alpaca-py==0.15.0 python-binance==1.0.19 requests==2.31.0 websocket-client==1.6.0

deactivate

# Step 6: Copy files
echo -e "${CYAN}[6/10] Copying OMNIBOT files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cp "$SCRIPT_DIR/src/app.py" "$INSTALL_DIR/src/"
cp "$SCRIPT_DIR/src/kiosk.py" "$INSTALL_DIR/src/"
cp "$SCRIPT_DIR/config/settings.json" "$INSTALL_DIR/config/"
cp -r "$SCRIPT_DIR/templates/"* "$INSTALL_DIR/templates/"
cp -r "$SCRIPT_DIR/static/"* "$INSTALL_DIR/static/"

chmod +x "$INSTALL_DIR/src/app.py"
chmod +x "$INSTALL_DIR/src/kiosk.py"

# Step 7: Configure systemd services
echo -e "${CYAN}[7/10] Configuring systemd services...${NC}"

cat > /etc/systemd/system/omnibot.service << EOF
[Unit]
Description=OMNIBOT TITAN Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/omnibot-kiosk.service << EOF
[Unit]
Description=OMNIBOT Dashboard Kiosk
After=omnibot.service graphical.target
Wants=omnibot.service

[Service]
Type=simple
User=$USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USER/.Xauthority
Environment=OMNIBOT_URL=http://localhost:8081
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium-browser --kiosk http://localhost:8081 --incognito --disable-session-crashed-bubble --disable-infobars --no-first-run --no-default-browser-check --enable-features=VirtualKeyboard,TouchpadAndTouchscreen --touch-events=enabled
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# Step 8: Configure display
echo -e "${CYAN}[8/10] Configuring display settings...${NC}"

mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/10-autologin.conf << EOF
[LightDM]
logind-check-graphical=true

[Seat:*]
autologin-user=$USER
autologin-user-timeout=0
user-session=LXDE
greeter-hide-users=false
EOF

cat > /home/$USER/.config/lxsession/LXDE/autostart << EOF
@lxpanel --profile LXDE
@pcmanfm --desktop --profile LXDE
@xscreensaver -no-splash
@xset -dpms
@xset s off
@unclutter -idle 0.1 -root
EOF

mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/99-omnibot.conf << EOF
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF

# Step 9: Set permissions
echo -e "${CYAN}[9/10] Setting permissions...${NC}"
chown -R $USER:$USER $INSTALL_DIR
chown -R $USER:$USER /home/$USER/.config

# Step 10: Enable services
echo -e "${CYAN}[10/10] Enabling services...${NC}"
systemctl daemon-reload
systemctl enable omnibot
systemctl enable omnibot-kiosk
systemctl enable lightdm

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  INSTALLATION COMPLETE!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${CYAN}OMNIBOT TITAN v${VERSION} has been installed.${NC}"
echo ""
echo "Next steps:"
echo "  1. Reboot: sudo reboot"
echo "  2. Dashboard will open automatically"
echo "  3. Go to Settings page to add your API keys"
echo ""
echo "Access:"
echo "  - On Pi: Auto-opens in kiosk mode"
echo "  - Network: http://omnibot.local:8081"
echo "  - Login: admin / admin"
echo ""
echo "Commands:"
echo "  sudo systemctl start omnibot    # Start bot"
echo "  sudo systemctl stop omnibot     # Stop bot"
echo "  sudo journalctl -u omnibot -f   # View logs"
echo ""
