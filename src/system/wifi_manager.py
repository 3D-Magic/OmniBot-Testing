"""
WiFi Manager for Raspberry Pi
Handles WiFi connections, scanning, and network management
"""
import subprocess
import json
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WiFiManager:
    """Manage WiFi connections on Raspberry Pi"""
    
    def __init__(self):
        self.interface = "wlan0"  # Default WiFi interface
        self._check_nmcli()
    
    def _check_nmcli(self):
        """Check if nmcli is available"""
        import os
        if os.path.exists('/usr/bin/nmcli'):
            self.nmcli_available = True
        else:
            self.nmcli_available = False
            logger.warning("nmcli not available - WiFi management limited")
    
    def get_status(self) -> Dict:
        """Get current WiFi status"""
        try:
            if not self.nmcli_available:
                return {'connected': False, 'error': 'nmcli not available'}
            
            # Get active connection
            result = subprocess.run(
                ['/usr/bin/nmcli', '-t', '-f', 'NAME,DEVICE,TYPE', 'connection', 'show', '--active'],
                capture_output=True, text=True, timeout=10
            )
            
            active_connection = None
            for line in result.stdout.strip().split('\n'):
                if ':' in line and 'wireless' in line.lower():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        active_connection = parts[0]
                        break
            
            # Get signal strength if connected
            signal = None
            if active_connection:
                signal_result = subprocess.run(
                    ['/usr/bin/nmcli', '-t', '-f', 'ACTIVE,SIGNAL', 'dev', 'wifi'],
                    capture_output=True, text=True, timeout=10
                )
                for line in signal_result.stdout.strip().split('\n'):
                    if line.startswith('yes:'):
                        try:
                            signal = int(line.split(':')[1])
                        except:
                            pass
            
            # Get IP address
            ip_address = None
            if active_connection:
                ip_result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True, text=True, timeout=5
                )
                ip_address = ip_result.stdout.strip().split()[0] if ip_result.stdout.strip() else None
            
            return {
                'connected': active_connection is not None,
                'ssid': active_connection,
                'signal': signal,
                'ip_address': ip_address,
                'interface': self.interface
            }
            
        except Exception as e:
            logger.error(f"[WIFI] Error getting status: {e}")
            return {'connected': False, 'error': str(e)}
    
    def scan_networks(self) -> List[Dict]:
        """Scan for available WiFi networks"""
        try:
            if not self.nmcli_available:
                return []
            
            result = subprocess.run(
                ['/usr/bin/nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list', '--rescan', 'yes'],
                capture_output=True, text=True, timeout=30
            )
            
            networks = []
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                if ':' not in line:
                    continue
                
                parts = line.split(':')
                if len(parts) < 3:
                    continue
                
                ssid = parts[0]
                if not ssid or ssid in seen_ssids or ssid == '--':
                    continue
                
                seen_ssids.add(ssid)
                
                try:
                    signal = int(parts[1]) if parts[1] else 0
                except:
                    signal = 0
                
                security = parts[2] if len(parts) > 2 else ''
                
                networks.append({
                    'ssid': ssid,
                    'signal': signal,
                    'secured': security != '' and security != '--',
                    'security_type': security if security != '--' else 'Open'
                })
            
            # Sort by signal strength
            networks.sort(key=lambda x: x['signal'], reverse=True)
            return networks
            
        except Exception as e:
            logger.error(f"[WIFI] Error scanning: {e}")
            return []
    
    def connect(self, ssid: str, password: str = None) -> Dict:
        """Connect to a WiFi network"""
        try:
            if not self.nmcli_available:
                return {'success': False, 'error': 'nmcli not available'}
            
            # Check if already connected
            status = self.get_status()
            if status.get('connected') and status.get('ssid') == ssid:
                return {'success': True, 'message': 'Already connected'}
            
            # Disconnect first if connected to another network
            if status.get('connected'):
                subprocess.run(
                    ['/usr/bin/nmcli', 'connection', 'down', status['ssid']],
                    capture_output=True, timeout=10
                )
            
            # Connect to new network
            if password:
                cmd = ['/usr/bin/nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
            else:
                cmd = ['/usr/bin/nmcli', 'dev', 'wifi', 'connect', ssid]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"[WIFI] Connected to {ssid}")
                return {'success': True, 'message': f'Connected to {ssid}'}
            else:
                error = result.stderr.strip() or 'Connection failed'
                logger.error(f"[WIFI] Connection failed: {error}")
                return {'success': False, 'error': error}
                
        except Exception as e:
            logger.error(f"[WIFI] Error connecting: {e}")
            return {'success': False, 'error': str(e)}
    
    def disconnect(self) -> Dict:
        """Disconnect from current WiFi"""
        try:
            if not self.nmcli_available:
                return {'success': False, 'error': 'nmcli not available'}
            
            status = self.get_status()
            if not status.get('connected'):
                return {'success': True, 'message': 'Not connected'}
            
            result = subprocess.run(
                ['/usr/bin/nmcli', 'connection', 'down', status['ssid']],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                logger.info("[WIFI] Disconnected")
                return {'success': True, 'message': 'Disconnected'}
            else:
                return {'success': False, 'error': result.stderr.strip()}
                
        except Exception as e:
            logger.error(f"[WIFI] Error disconnecting: {e}")
            return {'success': False, 'error': str(e)}
    
    def forget_network(self, ssid: str) -> Dict:
        """Remove a saved network"""
        try:
            if not self.nmcli_available:
                return {'success': False, 'error': 'nmcli not available'}
            
            result = subprocess.run(
                ['/usr/bin/nmcli', 'connection', 'delete', ssid],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"[WIFI] Forgot network {ssid}")
                return {'success': True, 'message': f'Removed {ssid}'}
            else:
                return {'success': False, 'error': result.stderr.strip()}
                
        except Exception as e:
            logger.error(f"[WIFI] Error forgetting network: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_saved_networks(self) -> List[str]:
        """Get list of saved networks"""
        try:
            if not self.nmcli_available:
                return []
            
            result = subprocess.run(
                ['/usr/bin/nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                capture_output=True, text=True, timeout=10
            )
            
            networks = []
            for line in result.stdout.strip().split('\n'):
                if 'wireless' in line.lower():
                    parts = line.split(':')
                    if parts and parts[0]:
                        networks.append(parts[0])
            
            return networks
            
        except Exception as e:
            logger.error(f"[WIFI] Error getting saved networks: {e}")
            return []
