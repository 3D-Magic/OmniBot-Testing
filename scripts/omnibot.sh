#!/bin/bash

# OMNIBOT v2.7 Titan - Control Script
# Usage: ./scripts/omnibot.sh [start|stop|status|url|logs|install-tailscale]

OMNIBOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$OMNIBOT_DIR/.omnibot.pid"
NGROK_URL_FILE="$OMNIBOT_DIR/.ngrok_url"
TUNNEL_URL_FILE="$OMNIBOT_DIR/.tunnel_url"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║   🤖 OMNIBOT v2.7 Titan - Multi-Market Trading Bot        ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

start_bot() {
    print_banner
    
    # Check if already running
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Bot is already running${NC}"
        show_status
        return
    fi
    
    cd "$OMNIBOT_DIR" || exit 1
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found. Run ./setup.sh first${NC}"
        exit 1
    fi
    
    # Determine tunnel method
    USE_NGROK=false
    if [ "$1" == "--ngrok" ] || [ "$1" == "-n" ]; then
        USE_NGROK=true
    fi
    
    # Start in background with nohup
    echo -e "${CYAN}🚀 Starting OMNIBOT v2.7 Titan...${NC}"
    
    if [ "$USE_NGROK" = true ]; then
        nohup python src/main.py --mode dashboard --ngrok > "$OMNIBOT_DIR/data/logs/omnibot.log" 2>&1 &
    else
        nohup python src/main.py --mode dashboard > "$OMNIBOT_DIR/data/logs/omnibot.log" 2>&1 &
    fi
    
    PID=$!
    echo $PID > "$PID_FILE"
    
    sleep 3
    
    # Check if started successfully
    if kill -0 $PID 2>/dev/null; then
        echo -e "${GREEN}✅ Bot started successfully (PID: $PID)${NC}"
        
        # Wait for ngrok URL if using ngrok
        if [ "$USE_NGROK" = true ]; then
            echo -e "${CYAN}🌐 Waiting for ngrok tunnel...${NC}"
            sleep 5
            
            if [ -f "$NGROK_URL_FILE" ]; then
                NGROK_URL=$(cat "$NGROK_URL_FILE")
                echo -e "${GREEN}🌍 Public URL: $NGROK_URL${NC}"
            fi
        fi
        
        # Show Tailscale IP if installed
        if command -v tailscale &> /dev/null; then
            TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
            if [ -n "$TAILSCALE_IP" ]; then
                echo -e "${GREEN}🔗 Tailscale URL: http://$TAILSCALE_IP:8081${NC}"
            fi
        fi
        
        echo -e "${CYAN}📊 Local URL: http://localhost:8081${NC}"
        
    else
        echo -e "${RED}❌ Failed to start bot${NC}"
        rm -f "$PID_FILE"
    fi
}

stop_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${CYAN}🛑 Stopping OMNIBOT (PID: $PID)...${NC}"
            kill -TERM "$PID" 2>/dev/null
            sleep 2
            
            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null
            fi
            
            echo -e "${GREEN}✅ Bot stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  Bot not running${NC}"
        fi
        rm -f "$PID_FILE" "$NGROK_URL_FILE" "$TUNNEL_URL_FILE"
    else
        # Try to find and kill any running instances
        pkill -f "python src/main.py" 2>/dev/null
        echo -e "${GREEN}✅ Stopped any running instances${NC}"
    fi
    
    # Stop ngrok
    pkill -f ngrok 2>/dev/null
}

show_status() {
    print_banner
    
    # Check if running
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Bot is running (PID: $PID)${NC}"
        
        # Show URLs
        echo -e "\n${CYAN}📊 Access URLs:${NC}"
        echo -e "   Local:    http://localhost:8081"
        
        # Tailscale
        if command -v tailscale &> /dev/null; then
            TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
            if [ -n "$TAILSCALE_IP" ]; then
                echo -e "   ${GREEN}Tailscale: http://$TAILSCALE_IP:8081${NC} (24/7 access)"
            fi
        fi
        
        # ngrok
        if [ -f "$NGROK_URL_FILE" ]; then
            NGROK_URL=$(cat "$NGROK_URL_FILE")
            echo -e "   ${GREEN}ngrok:     $NGROK_URL${NC}"
        fi
        
        # Show log tail
        echo -e "\n${CYAN}📋 Recent log entries:${NC}"
        if [ -f "$OMNIBOT_DIR/data/logs/omnibot.log" ]; then
            tail -5 "$OMNIBOT_DIR/data/logs/omnibot.log"
        fi
        
    else
        echo -e "${RED}❌ Bot is not running${NC}"
        echo -e "\n${CYAN}Start with:${NC}"
        echo -e "   ./scripts/omnibot.sh start       # Local only"
        echo -e "   ./scripts/omnibot.sh start --ngrok  # With ngrok"
    fi
}

show_url() {
    echo -e "${CYAN}🌐 OMNIBOT Access URLs:${NC}"
    echo -e "   Local: http://localhost:8081"
    
    if command -v tailscale &> /dev/null; then
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
        if [ -n "$TAILSCALE_IP" ]; then
            echo -e "   ${GREEN}Tailscale: http://$TAILSCALE_IP:8081${NC}"
        fi
    fi
    
    if [ -f "$NGROK_URL_FILE" ]; then
        cat "$NGROK_URL_FILE"
    fi
}

show_logs() {
    LOG_FILE="$OMNIBOT_DIR/data/logs/omnibot.log"
    if [ -f "$LOG_FILE" ]; then
        echo -e "${CYAN}📋 OMNIBOT Logs (press Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}⚠️  No log file found${NC}"
    fi
}

install_tailscale() {
    echo -e "${CYAN}📡 Installing Tailscale...${NC}"
    
    if command -v tailscale &> /dev/null; then
        echo -e "${GREEN}✅ Tailscale already installed${NC}"
    else
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
    
    echo -e "\n${CYAN}🔐 Starting Tailscale authentication...${NC}"
    sudo tailscale up
    
    echo -e "\n${GREEN}✅ Tailscale is ready!${NC}"
    TAILSCALE_IP=$(tailscale ip -4)
    echo -e "Your permanent URL: ${GREEN}http://$TAILSCALE_IP:8081${NC}"
    echo -e "\nInstall Tailscale on your other devices to access this URL."
}

# Main command handler
case "${1:-}" in
    start)
        start_bot "${2:-}"
        ;;
    stop)
        stop_bot
        ;;
    status)
        show_status
        ;;
    url)
        show_url
        ;;
    logs)
        show_logs
        ;;
    install-tailscale)
        install_tailscale
        ;;
    restart)
        stop_bot
        sleep 2
        start_bot "${2:-}"
        ;;
    *)
        print_banner
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start [--ngrok]    Start OMNIBOT (with optional ngrok)"
        echo "  stop               Stop OMNIBOT"
        echo "  status             Show status and URLs"
        echo "  url                Show access URLs"
        echo "  logs               View logs"
        echo "  install-tailscale  Install Tailscale for 24/7 access"
        echo "  restart            Restart OMNIBOT"
        echo ""
        echo "Examples:"
        echo "  $0 start           # Start locally"
        echo "  $0 start --ngrok   # Start with public URL"
        echo "  $0 install-tailscale  # Setup permanent access"
        ;;
esac