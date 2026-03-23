#!/bin/bash
# OmniBot v2.6 Sentinel - Control Script

BOT_DIR="$HOME/OmniBot-v2.6"
PID_FILE="/tmp/omnibot.pid"
TMUX_SESSION="omnibot"

start_bot() {
    echo "🤖 Starting OmniBot v2.6 Sentinel..."

    cd "$BOT_DIR"

    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "⚠️  OmniBot is already running!"
        exit 1
    fi

    tmux new-session -d -s "$TMUX_SESSION" -n "bot"

    if [[ "$1" == "--ngrok" ]]; then
        tmux send-keys -t "$TMUX_SESSION:bot" "cd $BOT_DIR && python src/main.py --ngrok" C-m
        sleep 3
        tmux split-window -h -t "$TMUX_SESSION"
        tmux send-keys -t "$TMUX_SESSION:bot" "ngrok http 8081" C-m
    else
        tmux send-keys -t "$TMUX_SESSION:bot" "cd $BOT_DIR && python src/main.py" C-m
    fi

    echo $! > "$PID_FILE"

    echo "✅ OmniBot started!"
    echo "📊 Dashboard: http://localhost:8081"

    if [[ "$1" == "--ngrok" ]]; then
        sleep 2
        echo "🌐 Fetching ngrok URL..."
        curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4
    fi

    echo ""
    echo "Commands:"
    echo "  View logs:  tmux attach -t omnibot"
    echo "  Stop:       ./scripts/omnibot.sh stop"
}

stop_bot() {
    echo "🛑 Stopping OmniBot..."
    tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true
    pkill -f "python src/main.py" 2>/dev/null || true
    pkill -f ngrok 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "✅ OmniBot stopped"
}

restart_bot() {
    stop_bot
    sleep 2
    start_bot "$1"
}

check_status() {
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        echo "✅ OmniBot is running"
        echo "📊 Dashboard: http://localhost:8081"
        if curl -s http://localhost:4040/api/tunnels >/dev/null 2>&1; then
            echo "🌐 Ngrok: Active"
            curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4
        else
            echo "🌐 Ngrok: Not running"
        fi
    else
        echo "❌ OmniBot is not running"
    fi
}

update_bot() {
    echo "🔄 Checking for updates..."
    cd "$BOT_DIR"
    python -c "from src.core.auto_updater import AutoUpdater; from config.settings import Settings; u = AutoUpdater(Settings); u.check_for_updates()"
}

case "${1:-start}" in
    start)
        start_bot "${2:-}"
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot "${2:-}"
        ;;
    status)
        check_status
        ;;
    update)
        update_bot
        ;;
    attach)
        tmux attach -t "$TMUX_SESSION"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|update|attach} [--ngrok]"
        exit 1
        ;;
esac
