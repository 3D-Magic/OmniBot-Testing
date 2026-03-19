#!/bin/bash
# OMNIBOT v2.6 Sentinel - Setup Script
# Run this on your Raspberry Pi to install dependencies

set -e

echo "🤖 Setting up OMNIBOT v2.6 Sentinel..."

# Check if running on Raspberry Pi
if [[ $(uname -m) != "aarch64" && $(uname -m) != "armv7l" ]]; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11 if not present
if ! command -v python3.11 &> /dev/null; then
    echo "🐍 Installing Python 3.11..."
    sudo apt-get install -y python3.11 python3.11-venv python3.11-pip
fi

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libatlas-base-dev \
    gfortran

# Create virtual environment
echo "🌐 Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip wheel setuptools

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install -r requirements.txt

# Download NLTK data for sentiment analysis
echo "🧠 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/cache
mkdir -p data/logs
mkdir -p data/backtests
mkdir -p backups
mkdir -p updates

# Set permissions
chmod +x src/main.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Configure your API keys: python src/main.py --setup"
echo "  2. Start trading: python src/main.py --mode trading"
echo "  3. Start dashboard: python src/main.py --mode dashboard"
echo ""
echo "📖 For more information, see README.md"
