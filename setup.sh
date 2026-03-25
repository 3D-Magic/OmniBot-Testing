#!/bin/bash
# OMNIBOT v2.7 Titan - Automated Setup Script
# Multi-Market Trading with 24/7 Remote Access

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SETUP] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[SETUP] $1${NC}"
}

info() {
    echo -e "${CYAN}[SETUP] $1${NC}"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   🤖  OMNIBOT v2.7 Titan - Multi-Market Trading        ║"
    echo "║                                                          ║"
    echo "║   Stocks • Crypto • Forex | 24/7 Automated              ║"
    echo "║   Remote Access: Tailscale | Cloudflare | ngrok         ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    log "Checking Python..."
    if ! command -v python3 &> /dev/null; then
        error "❌ Python 3 is required"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log "✅ Found Python $PYTHON_VERSION"
}

setup_venv() {
    log "Setting up virtual environment..."

    if [ -d "venv" ]; then
        warn "Removing old venv..."
        rm -rf venv
    fi

    python3 -m venv venv
    source venv/bin/activate

    log "Upgrading pip..."
    pip install --upgrade pip
}

install_deps() {
    log "Installing dependencies..."
    pip install -r requirements.txt

    log "Downloading NLTK data..."
    python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)" 2>/dev/null || true
}

setup_dirs() {
    log "Creating directories..."
    mkdir -p data/cache data/logs data/backtests data/history backups updates
    chmod +x src/main.py 2>/dev/null || true
    chmod +x scripts/omnibot.sh 2>/dev/null || true
    chmod +x scripts/setup_wizard.py 2>/dev/null || true
}

install_tailscale() {
    info "Installing Tailscale (optional but recommended)..."
    echo "Tailscale provides a static IP for 24/7 remote access"
    read -p "Install Tailscale? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://tailscale.com/install.sh | sudo bash
        log "✅ Tailscale installed!"
        warn "Run 'sudo tailscale up' to authenticate"
    fi
}

show_next_steps() {
    echo ""
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════"
    echo "  ✅ SETUP COMPLETE!"
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1️⃣  Run Interactive Setup Wizard:"
    echo "   python src/main.py --setup"
    echo ""
    echo "2️⃣  Or manually configure APIs:"
    echo "   python src/main.py --api-links    # Get API signup URLs"
    echo "   nano config/settings.py           # Edit configuration"
    echo ""
    echo "3️⃣  Setup Remote Access (24/7):"
    echo "   • Tailscale (Recommended): ./scripts/omnibot.sh install-tailscale"
    echo "   • Cloudflare: python src/main.py --tunnel-options"
    echo "   • ngrok: Sign up at https://dashboard.ngrok.com"
    echo ""
    echo "4️⃣  Start OMNIBOT:"
    echo "   ./scripts/omnibot.sh start"
    echo ""
    echo "5️⃣  Access Dashboard:"
    echo "   Local: http://localhost:8081"
    echo "   Remote: ./scripts/omnibot.sh url"
    echo ""
    echo "📚 Documentation:"
    echo "   python src/main.py --help"
    echo "   ./scripts/omnibot.sh help"
    echo ""
}

main() {
    print_banner
    check_python
    setup_venv
    install_deps
    setup_dirs
    install_tailscale

    echo ""
    log "✅ Installation Complete!"

    show_next_steps
}

main "$@"
