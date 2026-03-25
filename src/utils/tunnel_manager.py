"""
OMNIBOT Tunnel Manager - Multiple Remote Access Options
Supports: Tailscale, Cloudflare, ngrok, localhost.run
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import REMOTE_ACCESS, DASHBOARD

logger = logging.getLogger(__name__)


class TunnelManager:
    """Manages multiple tunnel options for 24/7 remote access"""

    def __init__(self):
        self.method = REMOTE_ACCESS.get("primary_method", "tailscale")
        self.port = DASHBOARD.get("port", 8081)
        self.active_tunnel = None
        self.url = None

    def start_tailscale(self) -> Optional[str]:
        """
        Start Tailscale - Best for 24/7 access with static IP
        https://tailscale.com
        """
        try:
            # Check if tailscale is installed
            result = subprocess.run(["which", "tailscale"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.info("Installing Tailscale...")
                install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
                subprocess.run(install_cmd, shell=True, check=True)

            # Check if tailscale is running
            status = subprocess.run(["tailscale", "status"], capture_output=True, text=True)

            if "Logged out" in status.stdout or status.returncode != 0:
                logger.info("Starting Tailscale...")
                print("\n🌐 Please authenticate Tailscale in your browser...")
                subprocess.run(["sudo", "tailscale", "up"], check=True)

            # Get Tailscale IP
            result = subprocess.run(
                ["tailscale", "ip", "-4"], 
                capture_output=True, 
                text=True
            )

            if result.returncode == 0:
                ip = result.stdout.strip()
                url = f"http://{ip}:{self.port}"
                self.url = url
                logger.info(f"Tailscale active: {url}")
                print(f"\n✅ Tailscale URL: {url}")
                print(f"   Access from any device with Tailscale installed")
                return url

        except Exception as e:
            logger.error(f"Tailscale error: {e}")
            print(f"❌ Tailscale failed: {e}")

        return None

    def start_cloudflare(self) -> Optional[str]:
        """
        Start Cloudflare Tunnel - Most professional option
        https://developers.cloudflare.com/cloudflare-one/connections/connect-apps
        """
        try:
            # Check if cloudflared is installed
            result = subprocess.run(["which", "cloudflared"], capture_output=True, text=True)

            if result.returncode != 0:
                logger.info("Installing cloudflared...")
                install_cmds = [
                    "wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb",
                    "sudo dpkg -i cloudflared-linux-amd64.deb",
                    "rm cloudflared-linux-amd64.deb"
                ]
                for cmd in install_cmds:
                    subprocess.run(cmd, shell=True, check=True)

            # Check if tunnel exists
            result = subprocess.run(
                ["cloudflared", "tunnel", "list"],
                capture_output=True,
                text=True
            )

            if "omnibot" not in result.stdout:
                print("\n⚠️  Cloudflare tunnel 'omnibot' not found.")
                print("   Run: cloudflared tunnel create omnibot")
                print("   Then: cloudflared tunnel route dns omnibot yourdomain.com")
                return None

            # Start tunnel
            print("\n🌐 Starting Cloudflare tunnel...")
            process = subprocess.Popen(
                ["cloudflared", "tunnel", "run", "omnibot"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.active_tunnel = process

            # Get URL from config
            config_path = Path.home() / ".cloudflared" / "config.yml"
            if config_path.exists():
                with open(config_path) as f:
                    for line in f:
                        if "hostname:" in line:
                            hostname = line.split(":")[1].strip()
                            url = f"https://{hostname}"
                            self.url = url
                            print(f"\n✅ Cloudflare URL: {url}")
                            return url

            print("✅ Cloudflare tunnel started (check dashboard for URL)")
            return "https://your-domain.com"

        except Exception as e:
            logger.error(f"Cloudflare error: {e}")
            print(f"❌ Cloudflare failed: {e}")

        return None

    def start_ngrok(self, authtoken: Optional[str] = None) -> Optional[str]:
        """
        Start ngrok - Easiest setup, but URL changes on restart
        https://ngrok.com
        """
        try:
            from pyngrok import ngrok

            # Configure if token provided
            if authtoken:
                ngrok.set_auth_token(authtoken)

            # Kill existing tunnels
            ngrok.kill()

            # Start tunnel
            public_url = ngrok.connect(self.port, "http")
            self.url = public_url

            logger.info(f"ngrok active: {public_url}")
            print(f"\n✅ ngrok URL: {public_url}")
            print(f"   ⚠️  URL changes on restart (use Tailscale for static URL)")

            return public_url

        except ImportError:
            logger.error("pyngrok not installed")
            print("❌ pyngrok not installed. Run: pip install pyngrok")
        except Exception as e:
            logger.error(f"ngrok error: {e}")
            print(f"❌ ngrok failed: {e}")

        return None

    def start_localhost_run(self) -> Optional[str]:
        """
        Start localhost.run tunnel - Free, no signup required
        https://localhost.run
        """
        try:
            print("\n🌐 Starting localhost.run tunnel...")
            print("   This creates an SSH tunnel (completely free)")

            # Start localhost.run via SSH
            process = subprocess.Popen(
                [
                    "ssh",
                    "-R", f"80:localhost:{self.port}",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ServerAliveInterval=60",
                    "localhost.run"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            self.active_tunnel = process

            # Wait for URL
            print("   Waiting for tunnel URL...")
            time.sleep(5)

            # Read output to get URL
            url = None
            for _ in range(10):
                line = process.stdout.readline()
                if "https://" in line or "http://" in line:
                    # Extract URL
                    import re
                    urls = re.findall(r'https?://[^\s]+', line)
                    if urls:
                        url = urls[0]
                        break
                time.sleep(1)

            if url:
                self.url = url
                print(f"\n✅ localhost.run URL: {url}")
                return url
            else:
                print("⚠️  Tunnel started but URL not detected")
                print("   Check terminal output for URL")
                return "https://check-terminal-output.localhost.run"

        except Exception as e:
            logger.error(f"localhost.run error: {e}")
            print(f"❌ localhost.run failed: {e}")

        return None

    def start_tunnel(self, method: Optional[str] = None) -> Optional[str]:
        """Start the configured tunnel method"""
        method = method or self.method

        print(f"\n🌐 Starting remote access: {method.upper()}")
        print("=" * 60)

        if method == "tailscale":
            return self.start_tailscale()
        elif method == "cloudflare":
            return self.start_cloudflare()
        elif method == "ngrok":
            return self.start_ngrok()
        elif method == "localhost_run":
            return self.start_localhost_run()
        else:
            logger.error(f"Unknown tunnel method: {method}")
            return None

    def stop_tunnel(self):
        """Stop active tunnel"""
        if self.active_tunnel:
            self.active_tunnel.terminate()
            self.active_tunnel = None
            logger.info("Tunnel stopped")

        # Also kill ngrok if running
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "method": self.method,
            "url": self.url,
            "active": self.active_tunnel is not None,
            "port": self.port
        }


def install_tailscale():
    """Install Tailscale automatically"""
    print("\n📦 Installing Tailscale...")
    try:
        cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
        subprocess.run(cmd, shell=True, check=True)
        print("✅ Tailscale installed!")
        print("\n🌐 Starting Tailscale...")
        subprocess.run(["sudo", "tailscale", "up"])
        return True
    except Exception as e:
        print(f"❌ Failed to install Tailscale: {e}")
        return False


def show_tunnel_options():
    """Display all tunnel options"""
    print("""
    🌐 REMOTE ACCESS OPTIONS (No Port Forwarding Needed)
    ═══════════════════════════════════════════════════════════

    🥇 TAILSCALE (Recommended for 24/7)
       • FREE personal plan
       • Static IP (never changes)
       • Full network access
       • Works even if your IP changes
       • Sign up: https://login.tailscale.com/start

    🥈 CLOUDFLARE TUNNEL (Most Professional)
       • FREE
       • Custom domain support
       • Most reliable
       • Requires domain name
       • Sign up: https://dash.cloudflare.com/sign-up

    🥉 NGROK (Easiest Setup)
       • FREE tier
       • Random URL (changes on restart)
       • Quick testing
       • Sign up: https://dashboard.ngrok.com/signup

    4️⃣ LOCALHOST.RUN (No Signup)
       • Completely FREE
       • No account needed
       • SSH-based
       • Command: ssh -R 80:localhost:8081 localhost.run

    ═══════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    show_tunnel_options()
