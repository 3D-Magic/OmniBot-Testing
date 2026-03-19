#!/bin/bash
# OMNIBOT v2.6 Sentinel - Helper Script
# Keeps terminal alive for ngrok/external access

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/data/logs"
PIDFILE="$PROJECT_DIR/.omnibot.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        error "Virtual environment not found. Run setup.sh first."
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
}

start_dashboard() {
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

    log "Starting OMNIBOT Dashboard..."

    NGROK_FLAG=""
    if [ "$1" == "--ngrok" ]; then
        NGROK_FLAG="--ngrok"
        log "ngrok tunnel enabled"
    fi

    # Use tmux to keep alive
    tmux kill-session -t omnibot 2>/dev/null || true
    tmux new-session -d -s omnibot "cd '$PROJECT_DIR' && python src/main.py --mode dashboard $NGROK_FLAG 2>&1 | tee -a '$LOG_DIR/dashboard.log'"

    sleep 3

    # Get tmux PID
    TMUX_PID=$(tmux list-panes -t omnibot -F '#{pane_pid}' 2>/dev/null | head -1)
    if [ -n "$TMUX_PID" ]; then
        echo "$TMUX_PID" > "$PIDFILE"
        log "Dashboard started in tmux session 'omnibot'"
        log "Local: http://localhost:8081"

        if [ -n "$NGROK_FLAG" ]; then
            sleep 2
            NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4)
            if [ -n "$NGROK_URL" ]; then
                log "External: $NGROK_URL"
            fi
        fi

        log "To view: tmux attach -t omnibot"
        log "To stop: $0 stop"
        return 0
    else
        error "Failed to start dashboard"
        return 1
    fi
}

stop_dashboard() {
    log "Stopping OMNIBOT..."

    tmux kill-session -t omnibot 2>/dev/null || true
    pkill -9 -f "python src/main.py" 2>/dev/null || true
    pkill -9 -f ngrok 2>/dev/null || true

    rm -f "$PIDFILE"

    log "OMNIBOT stopped"
}

status() {
    if tmux has-session -t omnibot 2>/dev/null; then
        log "OMNIBOT is RUNNING in tmux session 'omnibot'"

        # Check ngrok
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4)
        if [ -n "$NGROK_URL" ]; then
            log "External URL: $NGROK_URL"
        fi

        log "Local URL: http://localhost:8081"
        return 0
    else
        warn "OMNIBOT is NOT running"
        return 1
    fi
}

keep_alive() {
    log "Keep-alive monitor started..."
    while true; do
        if ! tmux has-session -t omnibot 2>/dev/null; then
            warn "OMNIBOT session lost, restarting..."
            start_dashboard "$1"
        fi

        # Check ngrok if enabled
        if [ "$1" == "--ngrok" ]; then
            if ! curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
                warn "ngrok tunnel down, restarting..."
                stop_dashboard
                sleep 2
                start_dashboard "$1"
            fi
        fi

        sleep 30
    done
}

case "${1:-}" in
    start)
        start_dashboard "${2:-}"
        ;;
    stop)
        stop_dashboard
        ;;
    restart)
        stop_dashboard
        sleep 2
        start_dashboard "${2:-}"
        ;;
    status)
        status
        ;;
    keep-alive)
        keep_alive "${2:-}"
        ;;
    attach)
        tmux attach -t omnibot
        ;;
    *)
        echo "OMNIBOT v2.6 Sentinel - Helper Script"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|attach|keep-alive} [--ngrok]"
        echo ""
        echo "Commands:"
        echo "  start       - Start dashboard in tmux (detached)"
        echo "  stop        - Stop dashboard and ngrok"
        echo "  restart     - Restart dashboard"
        echo "  status      - Check if running"
        echo "  attach      - Attach to tmux session"
        echo "  keep-alive  - Monitor and auto-restart if needed"
        echo ""
        echo "Options:"
        echo "  --ngrok     - Enable external access via ngrok"
        echo ""
        echo "Examples:"
        echo "  $0 start --ngrok    # Start with external access"
        echo "  $0 keep-alive       # Auto-restart on crash"
        exit 1
        ;;
esac
