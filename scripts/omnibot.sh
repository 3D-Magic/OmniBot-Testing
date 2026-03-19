#!/bin/bash
# OMNIBOT v2.6 Sentinel - Helper Script
# This script keeps the terminal alive for ngrok/external access

OMNIBOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$OMNIBOT_DIR"

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$OMNIBOT_DIR"

# Function to keep terminal alive
keep_alive() {
    echo "Keeping terminal alive for ngrok..."
    while true; do
        sleep 60
        # Ping ngrok API to keep connection alive
        curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1 || true
    done
}

# Parse arguments
MODE="${1:-trading}"
ENABLE_NGROK="${2:-false}"

case "$MODE" in
    trading)
        echo "🤖 Starting OMNIBOT Trading Engine..."
        python src/main.py --mode trading &
        TRADING_PID=$!

        # Keep terminal alive
        keep_alive &
        ALIVE_PID=$!

        # Wait for trading process
        wait $TRADING_PID
        kill $ALIVE_PID 2>/dev/null
        ;;

    dashboard)
        echo "🌐 Starting OMNIBOT Dashboard..."

        if [ "$ENABLE_NGROK" = "--ngrok" ] || [ "$ENABLE_NGROK" = "true" ]; then
            echo "   External access enabled (ngrok)"
            python src/main.py --mode dashboard --ngrok &
        else
            python src/main.py --mode dashboard &
        fi

        DASHBOARD_PID=$!

        # Keep terminal alive
        keep_alive &
        ALIVE_PID=$!

        # Wait for dashboard process
        wait $DASHBOARD_PID
        kill $ALIVE_PID 2>/dev/null
        ;;

    setup)
        echo "🔧 Running OMNIBOT Setup..."
        python src/main.py --setup
        ;;

    status)
        echo "📊 OMNIBOT Status"
        echo "================="

        # Check if processes are running
        if pgrep -f "omnibot" > /dev/null; then
            echo "✅ OMNIBOT is running"
            pgrep -f "omnibot" | xargs ps -fp
        else
            echo "❌ OMNIBOT is not running"
        fi

        # Check ngrok
        if pgrep -f "ngrok" > /dev/null; then
            echo ""
            echo "✅ ngrok is running"
            curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*"' | head -1
        fi
        ;;

    stop)
        echo "🛑 Stopping OMNIBOT..."
        pkill -f "omnibot"
        pkill -f "ngrok"
        echo "✅ Stopped"
        ;;

    *)
        echo "Usage: $0 {trading|dashboard|setup|status|stop} [--ngrok]"
        echo ""
        echo "Commands:"
        echo "  trading           Start trading engine"
        echo "  dashboard         Start dashboard"
        echo "  dashboard --ngrok Start dashboard with external access"
        echo "  setup             Run setup wizard"
        echo "  status            Check status"
        echo "  stop              Stop all OMNIBOT processes"
        exit 1
        ;;
esac
