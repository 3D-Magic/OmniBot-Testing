#!/bin/bash
# OMNIBOT v2.6 Sentinel - Clean Install Script
# WARNING: This will DELETE all old OMNIBOT data!

set -e

echo "🧹 OMNIBOT v2.6 Sentinel - Clean Installer"
echo "=========================================="
echo ""
read -p "⚠️  This will DELETE all old OMNIBOT data! Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Installation cancelled"
    exit 1
fi

echo ""
echo "🛑 Stopping old OMNIBOT services..."

# Stop any running OMNIBOT services
sudo systemctl stop omnibot 2>/dev/null || true
sudo systemctl stop omnibot-v2.5 2>/dev/null || true
sudo systemctl disable omnibot 2>/dev/null || true
sudo systemctl disable omnibot-v2.5 2>/dev/null || true

# Kill any running Python processes related to OMNIBOT
pkill -f "omnibot" 2>/dev/null || true
pkill -f "main.py" 2>/dev/null || true

sleep 2

echo "🗑️  Removing old OMNIBOT files..."

# Remove old directories
rm -rf ~/OmniBot
rm -rf ~/OmniBot-v2.5
rm -rf ~/OmniBot-v2.5.1
rm -rf ~/OmniBot-v2.6
sudo rm -rf /opt/omnibot

# Remove old service files
sudo rm -f /etc/systemd/system/omnibot*.service
sudo systemctl daemon-reload

# Remove old logs and data (optional - comment out to keep)
rm -rf ~/omnibot_logs
rm -rf ~/.omnibot
sudo rm -rf /var/log/omnibot*

echo "📥 Downloading OMNIBOT v2.6 Sentinel..."

# Create new directory
mkdir -p ~/OmniBot-v2.6
cd ~/OmniBot-v2.6

# Download from GitHub (public repo)
wget -O omnibot-v2.6-sentinel.zip "https://github.com/3D-Magic/OmniBot-Testing/archive/refs/heads/main.zip"

echo "📦 Extracting..."

unzip -o omnibot-v2.6-sentinel.zip
mv OmniBot-Testing-main/* .
mv OmniBot-Testing-main/.* . 2>/dev/null || true
rmdir OmniBot-Testing-main
rm omnibot-v2.6-sentinel.zip

echo "🔧 Setting up Python environment..."

# Create fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

echo "📚 Installing dependencies..."

pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('vader_lexicon', quiet=True)" 2>/dev/null || true

echo "📁 Creating directories..."

mkdir -p data/cache
mkdir -p data/logs
mkdir -p data/backtests
mkdir -p backups
mkdir -p updates

echo "🔐 Setting permissions..."

chmod +x src/main.py
chmod +x setup.sh
chmod +x scripts/omnibot.sh

# Create symlink for easy access
ln -sf ~/OmniBot-v2.6 ~/OmniBot

echo ""
echo "✅ OMNIBOT v2.6 Sentinel installed!"
echo ""
echo "🚀 Next steps:"
echo "   1. Configure API keys: python src/main.py --setup"
echo "   2. Test dashboard:     python src/main.py --mode dashboard"
echo "   3. Start trading:      python src/main.py --mode trading"
echo "   4. Install service:    sudo cp scripts/omnibot.service /etc/systemd/system/"
echo ""
echo "📂 Location: ~/OmniBot-v2.6"
echo "🌐 Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "💡 For external access with ngrok:"
echo "   python src/main.py --mode dashboard --ngrok"
echo ""
