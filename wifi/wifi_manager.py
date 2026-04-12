"""
WiFi Manager
Handles WiFi network scanning and connections
"""

import subprocess
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class WiFiManager:
    """Manages WiFi connections"""
    
    def __init__(self, interface='wlan0'):
        self.interface = interface
    
    def scan_networks(self) -> List[Dict]:
        """Scan for available WiFi networks"""
        try:
            result = subprocess.run(
                ['sudo', 'iwlist', self.interface, 'scan'],
                capture_output=True, text=True, timeout=30
            )
            
            networks = []
            current_network = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                # ESSID (network name)
                if 'ESSID:' in line:
                    essid = line.split('ESSID:')[1].strip().strip('"')
                    if essid and essid not in [n['ssid'] for n in networks]:
                        current_network = {'ssid': essid, 'secured': True}
                        networks.append(current_network)
                
                # Encryption/Security
                if 'Encryption key:' in line:
                    if 'off' in line:
                        current_network['secured'] = False
                
                # Signal quality
                if 'Quality=' in line:
                    try:
                        quality_str = line.split('Quality=')[1].split()[0]
                        num, denom = quality_str.split('/')
                        current_network['quality'] = int(int(num) / int(denom) * 100)
                    except:
                        current_network['quality'] = 0
            
            # Sort by quality
            networks.sort(key=lambda x: x.get('quality', 0), reverse=True)
            return networks[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"[WIFI SCAN ERROR] {e}")
            return []
    
    def get_status(self) -> Dict:
        """Get current WiFi connection status"""
        try:
            # Get SSID
            result = subprocess.run(
                ['iwgetid', '-r'],
                capture_output=True, text=True
            )
            ssid = result.stdout.strip()
            
            # Get IP address
            ip_result = subprocess.run(
                ['hostname', '-I'],
                capture_output=True, text=True
            )
            ip = ip_result.stdout.strip().split()[0] if ip_result.stdout else None
            
            return {
                'connected': bool(ssid),
                'ssid': ssid or 'Not Connected',
                'ip': ip or 'Unknown',
                'interface': self.interface
            }
            
        except Exception as e:
            logger.error(f"[WIFI STATUS ERROR] {e}")
            return {
                'connected': False,
                'ssid': 'Unknown',
                'ip': 'Unknown',
                'error': str(e)
            }
    
    def connect(self, ssid: str, password: str = '') -> Dict:
        """Connect to a WiFi network"""
        try:
            if not ssid:
                return {'success': False, 'error': 'SSID required'}
            
            if password:
                # Use wpa_passphrase for secure networks
                result = subprocess.run(
                    ['wpa_passphrase', ssid, password],
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0:
                    # Write to temp file and add to wpa_supplicant
                    with open('/tmp/wpa_supplicant_add.conf', 'w') as f:
                        f.write(result.stdout)
                    
                    subprocess.run(
                        ['sudo', 'wpa_cli', 'reconfigure'],
                        capture_output=True
                    )
                    
                    logger.info(f"[WIFI] Connected to {ssid}")
                    return {
                        'success': True,
                        'message': f'Connected to {ssid}'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Invalid password or network'
                    }
            else:
                # Open network
                subprocess.run(
                    ['sudo', 'iwconfig', self.interface, 'essid', ssid],
                    capture_output=True
                )
                
                logger.info(f"[WIFI] Connected to open network {ssid}")
                return {
                    'success': True,
                    'message': f'Connected to {ssid} (open network)'
                }
                
        except Exception as e:
            logger.error(f"[WIFI CONNECT ERROR] {e}")
            return {'success': False, 'error': str(e)}
    
    def disconnect(self) -> Dict:
        """Disconnect from current network"""
        try:
            subprocess.run(
                ['sudo', 'iwconfig', self.interface, 'essid', 'off/any'],
                capture_output=True
            )
            return {'success': True, 'message': 'Disconnected'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
