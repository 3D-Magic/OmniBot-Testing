"""
OMNIBOT v2.6 Sentinel - Web Dashboard
Flask-based dashboard for monitoring and control
"""

import logging
from datetime import datetime, timedelta
from functools import wraps
import json
import os

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import pandas as pd

from config.settings import DASHBOARD, VERSION, VERSION_NAME

logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Mock data store (will be replaced with actual data sources)
class DataStore:
    """Simple data store for dashboard"""
    def __init__(self):
        self.portfolio = {
            "total_value": 100000.00,
            "cash": 25000.00,
            "positions_value": 75000.00,
            "day_pnl": 1250.50,
            "day_pnl_pct": 1.25,
            "total_pnl": 15000.00,
            "total_pnl_pct": 17.5
        }
        self.positions = [
            {"symbol": "AAPL", "quantity": 100, "avg_price": 150.00, "current_price": 175.50, "pnl": 2550.00, "pnl_pct": 17.0},
            {"symbol": "MSFT", "quantity": 50, "avg_price": 300.00, "current_price": 380.25, "pnl": 4012.50, "pnl_pct": 26.75},
            {"symbol": "GOOGL", "quantity": 25, "avg_price": 120.00, "current_price": 142.80, "pnl": 570.00, "pnl_pct": 19.0},
            {"symbol": "TSLA", "quantity": 40, "avg_price": 200.00, "current_price": 175.00, "pnl": -1000.00, "pnl_pct": -12.5},
            {"symbol": "NVDA", "quantity": 30, "avg_price": 400.00, "current_price": 875.00, "pnl": 14250.00, "pnl_pct": 118.75}
        ]
        self.trades = [
            {"timestamp": "2026-03-19 09:30:00", "symbol": "AAPL", "side": "buy", "quantity": 10, "price": 175.50, "value": 1755.00},
            {"timestamp": "2026-03-19 09:15:00", "symbol": "TSLA", "side": "sell", "quantity": 5, "price": 175.00, "value": 875.00},
            {"timestamp": "2026-03-18 15:45:00", "symbol": "NVDA", "side": "buy", "quantity": 5, "price": 870.00, "value": 4350.00},
            {"timestamp": "2026-03-18 14:30:00", "symbol": "MSFT", "side": "buy", "quantity": 10, "price": 378.00, "value": 3780.00}
        ]
        self.strategies = [
            {"name": "momentum", "enabled": True, "weight": 0.25, "trades": 45, "win_rate": 62.5, "profit": 5230.50},
            {"name": "mean_reversion", "enabled": True, "weight": 0.25, "trades": 38, "win_rate": 58.0, "profit": 3150.25},
            {"name": "breakout", "enabled": True, "weight": 0.25, "trades": 32, "win_rate": 65.5, "profit": 4125.75},
            {"name": "ml_ensemble", "enabled": True, "weight": 0.25, "trades": 28, "win_rate": 71.4, "profit": 2493.50}
        ]
        self.system_status = {
            "status": "running",
            "uptime": "5d 12h 30m",
            "cpu_usage": 25.5,
            "memory_usage": 45.2,
            "disk_usage": 32.8,
            "temperature": 52.3,
            "last_update": datetime.now().isoformat()
        }

    def get_portfolio_history(self, days=30):
        """Generate mock portfolio history"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
        base_value = 85000
        values = []
        current = base_value

        for i in range(days):
            change = (hash(str(dates[i])) % 1000 - 500) / 100
            current += change
            values.append({
                "date": dates[i].strftime("%Y-%m-%d"),
                "value": round(current, 2)
            })

        return values

data_store = DataStore()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if DASHBOARD["auth_required"] and not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def index():
    """Main dashboard page"""
    return render_template("index.html", 
                         version=VERSION, 
                         version_name=VERSION_NAME,
                         hardware_profile="pi5_8gb")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page"""
    if request.method == "POST":
        password = request.form.get("password")
        if password == "admin":
            session["logged_in"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Logout"""
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/api/portfolio")
@login_required
def api_portfolio():
    return jsonify(data_store.portfolio)

@app.route("/api/positions")
@login_required
def api_positions():
    return jsonify(data_store.positions)

@app.route("/api/trades")
@login_required
def api_trades():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(data_store.trades[:limit])

@app.route("/api/strategies")
@login_required
def api_strategies():
    return jsonify(data_store.strategies)

@app.route("/api/strategies/<name>/toggle", methods=["POST"])
@login_required
def api_toggle_strategy(name):
    for strategy in data_store.strategies:
        if strategy["name"] == name:
            strategy["enabled"] = not strategy["enabled"]
            return jsonify({"success": True, "enabled": strategy["enabled"]})
    return jsonify({"success": False, "error": "Strategy not found"}), 404

@app.route("/api/system")
@login_required
def api_system():
    return jsonify(data_store.system_status)

@app.route("/api/history")
@login_required
def api_history():
    days = request.args.get("days", 30, type=int)
    return jsonify(data_store.get_portfolio_history(days))

@app.route("/api/sentiment")
@login_required
def api_sentiment():
    return jsonify({
        "overall": 0.35,
        "trend": "positive",
        "sources": {
            "reddit": {"score": 0.42, "volume": 1250},
            "rss": {"score": 0.28, "volume": 450}
        },
        "symbols": {
            "AAPL": 0.55,
            "TSLA": 0.12,
            "NVDA": 0.78
        }
    })

@app.route("/api/emergency_stop", methods=["POST"])
@login_required
def api_emergency_stop():
    data_store.system_status["status"] = "stopped"
    socketio.emit("system_update", data_store.system_status)
    return jsonify({"success": True, "message": "Trading stopped"})

@app.route("/api/manual_trade", methods=["POST"])
@login_required
def api_manual_trade():
    data = request.json
    trade = {
        "timestamp": datetime.now().isoformat(),
        "symbol": data.get("symbol"),
        "side": data.get("side"),
        "quantity": data.get("quantity"),
        "price": data.get("price"),
        "value": data.get("quantity") * data.get("price")
    }
    data_store.trades.insert(0, trade)
    socketio.emit("new_trade", trade)
    return jsonify({"success": True, "trade": trade})

@socketio.on("connect")
def handle_connect():
    logger.info("Client connected to dashboard")
    emit("connected", {"status": "connected", "version": VERSION})

@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected from dashboard")

def run_dashboard(host=None, port=None, debug=False):
    """Run the dashboard server"""
    host = host or DASHBOARD["host"]
    port = port or DASHBOARD["port"]

    logger.info(f"Starting OMNIBOT Dashboard on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_dashboard()
