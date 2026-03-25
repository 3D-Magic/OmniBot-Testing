#!/bin/bash
# OMNIBOT v2.7 Titan - Control Script
# Multi-Market Trading with 24/7 Remote Access

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
PIDFILE="$PROJECT_DIR/.omnibot.pid"
LOG_FILE="$PROJECT_DIR/data/logs/omnibot.log"
TUNNEL_URL_FILE="$PROJECT_DIR/.tunnel_url"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')] $1${NC}"
}

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        error "Virtual environment not found. Run setup.sh first."
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
}

get_tunnel_method() {
    # Read from settings or default to tailscale
    if [ -f "$PROJECT_DIR/config/settings.py" ]; then
        METHOD=$(grep "primary_method" "$PROJECT_DIR/config/settings.py" | cut -d'"' -f4)
        echo "${METHOD:-tailscale}"
    else
        echo "tailscale"
    fi
}

start_bot() {
    check_venv

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            warn "OMNIBOT is already running (PID: $PID)"
            return 1
        else
            rm -f "$PIDFILE"
        fi
    fi

    TUNNEL_METHOD=$(get_tunnel_method)
    log "Starting OMNIBOT v2.7 Titan..."
    info "Tunnel method: $TUNNEL_METHOD"

    # Kill any existing processes
    pkill -9 -f "python src/main.py" 2>/dev/null || true
    pkill -9 -f ngrok 2>/dev/null || true
    sleep 2

    # Start in tmux session
    tmux kill-session -t omnibot 2>/dev/null || true

    if [ "$TUNNEL_METHOD" == "tailscale" ]; then
        # Check if tailscale is installed and running
        if command -v tailscale &> /dev/null; then
            TAILSCALE_STATUS=$(tailscale status 2>&1)
            if echo "$TAILSCALE_STATUS" | grep -q "Logged out"; then
                warn "Tailscale not logged in. Run: sudo tailscale up"
            else
                TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
                if [ -n "$TAILSCALE_IP" ]; then
                    echo "http://$TAILSCALE_IP:8081" > "$TUNNEL_URL_FILE"
                    log "Tailscale URL: http://$TAILSCALE_IP:8081"
                fi
            fi
        else
            warn "Tailscale not installed. Install with: python src/main.py --install-tailscale"
        fi

        tmux new-session -d -s omnibot "cd '$PROJECT_DIR' && source venv/bin/activate && python src/main.py --mode dashboard 2>&1 | tee -a '$LOG_FILE'"
    else
        tmux new-session -d -s omnibot "cd '$PROJECT_DIR' && source venv/bin/activate && python src/main.py --mode dashboard --tunnel $TUNNEL_METHOD 2>&1 | tee -a '$LOG_FILE'"
    fi

    sleep 3

    # Get PID
    TMUX_PID=$(tmux list-panes -t omnibot -F '#{pane_pid}' 2>/dev/null | head -1)
    if [ -n "$TMUX_PID" ]; then
        echo "$TMUX_PID" > "$PIDFILE"
        log "✅ OMNIBOT started in tmux session 'omnibot'"

        # Get tunnel URL if not tailscale
        if [ "$TUNNEL_METHOD" == "ngrok" ]; then
            sleep 3
            NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4)
            if [ -n "$NGROK_URL" ]; then
                echo "$NGROK_URL" > "$TUNNEL_URL_FILE"
                log "🌐 ngrok URL: $NGROK_URL"
            fi
        fi

        log "💡 Commands:"
        log "   View logs: $0 logs"
        log "   Attach: tmux attach -t omnibot"
        log "   Stop: $0 stop"
        log "   URL: $0 url"
        return 0
    else
        error "❌ Failed to start OMNIBOT"
        return 1
    fi
}

stop_bot() {
    log "Stopping OMNIBOT..."

    tmux kill-session -t omnibot 2>/dev/null || true
    pkill -9 -f "python src/main.py" 2>/dev/null || true
    pkill -9 -f ngrok 2>/dev/null || true
    pkill -9 -f cloudflared 2>/dev/null || true

    rm -f "$PIDFILE"
    rm -f "$TUNNEL_URL_FILE"

    log "✅ OMNIBOT stopped"
}

restart_bot() {
    stop_bot
    sleep 2
    start_bot
}

get_url() {
    if [ -f "$TUNNEL_URL_FILE" ]; then
        cat "$TUNNEL_URL_FILE"
    else
        # Try to get ngrok URL
        curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4
    fi
}

check_status() {
    if tmux has-session -t omnibot 2>/dev/null; then
        log "✅ OMNIBOT is RUNNING"

        TUNNEL_METHOD=$(get_tunnel_method)
        info "Tunnel method: $TUNNEL_METHOD"

        URL=$(get_url)
        if [ -n "$URL" ]; then
            log "🌐 Remote URL: $URL"
        fi

        # Show Tailscale IP if using tailscale
        if [ "$TUNNEL_METHOD" == "tailscale" ] && command -v tailscale &> /dev/null; then
            TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
            if [ -n "$TAILSCALE_IP" ]; then
                log "🔗 Tailscale: http://$TAILSCALE_IP:8081"
            fi
        fi

        log "📊 Local URL: http://localhost:8081"
        return 0
    else
        error "❌ OMNIBOT is NOT running"
        return 1
    fi
}

install_tailscale() {
    log "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sudo bash
    log "✅ Tailscale installed!"
    log "🌐 Starting Tailscale..."
    sudo tailscale up
}

show_help() {
    echo "OMNIBOT v2.7 Titan - Multi-Market Trading Bot"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|url|logs|install-tailscale|help}"
    echo ""
    echo "Commands:"
    echo "  start            - Start OMNIBOT with configured tunnel"
    echo "  stop             - Stop OMNIBOT"
    echo "  restart          - Restart OMNIBOT"
    echo "  status           - Check if running and show URLs"
    echo "  url              - Get remote access URL"
    echo "  logs             - View logs in real-time"
    echo "  install-tailscale - Install Tailscale for 24/7 access"
    echo "  help             - Show this help"
    echo ""
    echo "Remote Access Methods:"
    echo "  • Tailscale (Recommended) - Static IP, always accessible"
    echo "  • Cloudflare Tunnel       - Custom domain support"
    echo "  • ngrok                   - Easy setup, random URL"
    echo "  • localhost.run           - No signup required"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start with configured tunnel"
    echo "  $0 install-tailscale  # Install Tailscale"
    echo "  $0 status             # Check status and URLs"
}

case "${1:-}" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        check_status
        ;;
    url)
        URL=$(get_url)
        if [ -n "$URL" ]; then
            echo "$URL"
        else
            # Check for Tailscale
            if command -v tailscale &> /dev/null; then
                TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
                if [ -n "$TAILSCALE_IP" ]; then
                    echo "http://$TAILSCALE_IP:8081"
                else
                    error "No URL found. Is the bot running?"
                fi
            else
                error "No URL found. Is the bot running?"
            fi
        fi
        ;;
    logs)
        tail -f "$LOG_FILE"
        ;;
    install-tailscale)
        install_tailscale
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
