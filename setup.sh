#!/bin/bash

echo "🤖 Setting up OMNIBOT v2.7 Titan..."

# Check Python version
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Download NLTK data
echo "📚 Downloading NLTK data..."
python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); nltk.download('vader_lexicon', quiet=True)"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/cache data/logs data/backtests backups updates

# Make scripts executable
chmod +x src/main.py
chmod +x scripts/omnibot.sh
chmod +x scripts/setup_wizard.py

echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Edit config/settings.py with your API keys"
echo "2. Run: python src/main.py --setup"
echo "3. Start with: ./scripts/omnibot.sh start"