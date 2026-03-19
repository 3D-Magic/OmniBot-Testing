#!/bin/bash
# OMNIBOT v2.6 Sentinel Setup Script
# Run this on your Raspberry Pi to install dependencies

set -e

echo "🤖 OMNIBOT v2.6 Sentinel Setup"
echo "==============================="
echo ""

# Check if running on Raspberry Pi
if [[ $(uname -m) == "aarch64" ]] || [[ $(uname -m) == "armv7l" ]]; then
    echo "✅ Raspberry Pi detected"
else
    echo "⚠️  Not running on Raspberry Pi - some optimizations may not apply"
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    htop \
    nano \
    vim

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment exists, removing old one..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip wheel setuptools

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Download NLTK data
echo "🧠 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('vader_lexicon', quiet=True)" || echo "⚠️  NLTK download failed, will retry on first run"

# Create directories
echo "📁 Creating directories..."
mkdir -p data/cache data/logs data/backtests backups updates

# Set permissions
echo "🔐 Setting permissions..."
chmod +x src/main.py

# Create systemd service file
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/omnibot.service > /dev/null <<EOF
[Unit]
Description=OMNIBOT v2.6 Sentinel Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
Environment=PYTHONPATH=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/src/main.py --mode trading
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create ngrok service (optional)
sudo tee /etc/systemd/system/omnibot-dashboard.service > /dev/null <<EOF
[Unit]
Description=OMNIBOT v2.6 Sentinel Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
Environment=PYTHONPATH=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/src/main.py --mode dashboard
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "   1. Configure API keys:  python src/main.py --setup"
echo "   2. Test trading:        python src/main.py --mode trading"
echo "   3. Start dashboard:     python src/main.py --mode dashboard"
echo "   4. Enable auto-start:   sudo systemctl enable omnibot"
echo "   5. Start service:       sudo systemctl start omnibot"
echo ""
echo "📖 Documentation:"
echo "   - Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "   - Logs:      tail -f data/logs/omnibot.log"
echo ""
