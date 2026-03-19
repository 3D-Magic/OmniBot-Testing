#!/bin/bash
# OMNIBOT v2.6 Sentinel - Setup Script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SETUP] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[SETUP] $1${NC}"
}

error() {
    echo -e "${RED}[SETUP] $1${NC}"
}

# Check Python version
check_python() {
    log "Checking Python..."
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log "Found Python $PYTHON_VERSION"

    # Check if Python 3.8+
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        error "Python 3.8+ required"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    log "Setting up virtual environment..."

    if [ -d "venv" ]; then
        warn "Virtual environment exists, removing..."
        rm -rf venv
    fi

    python3 -m venv venv
    source venv/bin/activate

    log "Upgrading pip..."
    pip install --upgrade pip
}

# Install dependencies
install_deps() {
    log "Installing dependencies..."

    # Fix for Python 3.13 - remove incompatible packages
    if [ -f "requirements.txt" ]; then
        # Remove tensorflow/keras (not compatible with Python 3.13 on ARM)
        grep -v -E "^(tensorflow|keras)" requirements.txt > requirements-fixed.txt || true
        mv requirements-fixed.txt requirements.txt
    fi

    pip install -r requirements.txt

    # Install additional dashboard dependencies if missing
    pip install flask-socketio eventlet pyngrok 2>/dev/null || true

    # Download NLTK data
    log "Downloading NLTK data..."
    python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)" 2>/dev/null || true
}

# Create directories
setup_dirs() {
    log "Creating directories..."
    mkdir -p data/cache data/logs data/backtests backups updates
    mkdir -p src/dashboard/templates
    chmod +x src/main.py 2>/dev/null || true
}

# Make scripts executable
setup_scripts() {
    log "Setting up scripts..."
    chmod +x scripts/omnibot.sh 2>/dev/null || true
    chmod +x clean-install.sh 2>/dev/null || true

    # Create global command symlink
    mkdir -p "$HOME/.local/bin"
    ln -sf "$(pwd)/scripts/omnibot.sh" "$HOME/.local/bin/omnibot" 2>/dev/null || true
}

# Main setup
main() {
    echo ""
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   🤖  OMNIBOT v2.6 Sentinel - Setup                    ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_python
    setup_venv
    install_deps
    setup_dirs
    setup_scripts

    echo ""
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   ✅  Setup Complete!                                    ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    log "To start OMNIBOT:"
    echo "  ./scripts/omnibot.sh start --ngrok"
    echo ""
    log "Or activate venv manually:"
    echo "  source venv/bin/activate"
    echo "  python src/main.py --mode dashboard --ngrok"
}

main "$@"
