"""
Dashboard Server with Update/Restart API
"""

from flask import Flask, jsonify, request, send_from_directory
import os
import subprocess
import sys

app = Flask(__name__)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/status")
def status():
    return jsonify({
        "version": "v2.6.0 Enhanced",
        "mode": "aggressive",
        "update_available": False
    })

@app.route("/api/mode", methods=["POST"])
def set_mode():
    mode = request.json.get("mode", "aggressive")
    print(f"[API] Mode changed to: {mode}")
    return jsonify({"success": True, "mode": mode})

@app.route("/api/update/check")
def check_update():
    return jsonify({
        "updateAvailable": False,
        "currentVersion": "v2.6.0",
        "latestVersion": "v2.6.0"
    })

@app.route("/api/update/apply", methods=["POST"])
def apply_update():
    def update():
        import time
        time.sleep(2)
        subprocess.Popen([
            "bash", "-c",
            "cd ~/OmniBot-v2.6 && ./scripts/omnibot.sh restart --ngrok"
        ])
    import threading
    threading.Thread(target=update, daemon=True).start()
    return jsonify({"success": True, "message": "Updating..."})

@app.route("/api/restart", methods=["POST"])
def restart():
    def restart_app():
        import time
        time.sleep(2)
        os.execv(sys.executable, ["python"] + sys.argv)
    import threading
    threading.Thread(target=restart_app, daemon=True).start()
    return jsonify({"success": True})

@app.route("/api/emergency-stop", methods=["POST"])
def emergency_stop():
    print("[EMERGENCY] Trading stopped!")
    return jsonify({"success": True, "message": "Trading stopped"})

if __name__ == "__main__":
    print("[DASHBOARD] Starting on port 8081")
    app.run(host="0.0.0.0", port=8081, debug=False)
