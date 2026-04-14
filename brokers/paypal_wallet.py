"""
PayPal Central Wallet Implementation for OMNIBOT
Acts as the bot's primary funding source for trading
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class PayPalWallet(BaseBroker):
    """
    PayPal Central Wallet - Primary funding source for OMNIBOT
    
    When enabled, this wallet:
    - Tracks available funds for trading
    - Provides capital allocation to brokers
    - Records all deposits/withdrawals
    - Can receive trading profits
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None, 
                 sandbox: bool = True, enabled: bool = False):
        """
        Initialize PayPal Central Wallet
        
        Args:
            client_id: PayPal REST API client ID
            client_secret: PayPal REST API client secret
            sandbox: Use PayPal sandbox environment
            enabled: Whether this wallet is active for trading
        """
        super().__init__('paypal')
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.enabled = enabled  # User can enable/disable
        
        # API endpoints
        if sandbox:
            self.base_url = "https://api.sandbox.paypal.com"
        else:
            self.base_url = "https://api.paypal.com"
        
        self.access_token = None
        self.token_expires = None
        
        # Trading capital tracking
        self.total_capital = 0.0
        self.allocated_capital = 0.0  # Capital allocated to brokers
        self.available_capital = 0.0  # Capital available for allocation
        
        # Transaction history
        self.transactions: List[Dict] = []
        self.allocations: Dict[str, float] = {}  # broker -> amount allocated
        
        logger.info(f"[PAYPAL] Wallet initialized (enabled={enabled}, sandbox={sandbox})")
    
    def connect(self) -> bool:
        """Authenticate with PayPal API"""
        if not self.enabled:
            logger.info("[PAYPAL] Wallet is disabled, skipping connection")
            return False
        
        try:
            if not self.client_id or not self.client_secret:
                logger.warning("[PAYPAL] No credentials provided, running in demo mode")
                self.connected = False
                self.configured = False
                return False
            
            auth_url = f"{self.base_url}/v1/oauth2/token"
            
            response = requests.post(
                auth_url,
                auth=(self.client_id, self.client_secret),
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "en_US"
                },
                data={"grant_type": "client_credentials"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']
                self.token_expires = datetime.now().timestamp() + data['expires_in']
                self.connected = True
                self.configured = True
                
                # Sync balance from PayPal
                self._sync_balance()
                
                logger.info("[PAYPAL] Successfully connected to PayPal API")
                return True
            else:
                logger.error(f"[PAYPAL] Authentication failed: {response.text}")
                self.connected = False
                return False
                
        except Exception as e:
            logger.error(f"[PAYPAL] Connection error: {e}")
            self.connected = False
            return False
    
    def _ensure_token(self) -> bool:
        """Ensure access token is valid"""
        if not self.enabled:
            return False
        if not self.access_token:
            return self.connect()
        if self.token_expires and datetime.now().timestamp() >= self.token_expires:
            logger.info("[PAYPAL] Token expired, refreshing...")
            return self.connect()
        return True
    
    def _sync_balance(self):
        """Sync wallet balance from PayPal"""
        try:
            url = f"{self.base_url}/v1/reporting/balances"
            
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                balances = data.get('balances', [])
                
                if balances:
                    usd_balance = next(
                        (b for b in balances if b.get('currency') == 'USD'),
                        balances[0]
                    )
                    self.total_capital = float(usd_balance.get('available_balance', 0))
                    self._update_available_capital()
                    
                    logger.info(f"[PAYPAL] Balance synced: ${self.total_capital:.2f}")
            
        except Exception as e:
            logger.error(f"[PAYPAL] Error syncing balance: {e}")
    
    def _update_available_capital(self):
        """Update available capital based on allocations"""
        self.allocated_capital = sum(self.allocations.values())
        self.available_capital = self.total_capital - self.allocated_capital
    
    # ===== Central Wallet Functions =====
    
    def allocate_to_broker(self, broker_name: str, amount: float) -> Dict:
        """
        Allocate capital from PayPal wallet to a broker
        
        Args:
            broker_name: Name of broker (alpaca, binance, etc.)
            amount: Amount to allocate
            
        Returns:
            Dict with allocation result
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        if amount > self.available_capital:
            return {
                'success': False, 
                'error': f'Insufficient funds. Available: ${self.available_capital:.2f}'
            }
        
        # Record allocation
        self.allocations[broker_name] = self.allocations.get(broker_name, 0) + amount
        self._update_available_capital()
        
        # Record transaction
        transaction = {
            'id': f"alloc_{datetime.now().timestamp()}",
            'type': 'allocation',
            'broker': broker_name,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Allocated ${amount:.2f} to {broker_name}")
        
        return {
            'success': True,
            'allocated': amount,
            'broker': broker_name,
            'available': self.available_capital
        }
    
    def release_from_broker(self, broker_name: str, amount: float = None) -> Dict:
        """
        Release capital back to PayPal wallet from a broker
        
        Args:
            broker_name: Name of broker
            amount: Amount to release (None = release all)
            
        Returns:
            Dict with release result
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        allocated = self.allocations.get(broker_name, 0)
        
        if amount is None:
            amount = allocated
        
        if amount > allocated:
            return {
                'success': False,
                'error': f'Cannot release more than allocated. Allocated: ${allocated:.2f}'
            }
        
        # Update allocation
        self.allocations[broker_name] = allocated - amount
        if self.allocations[broker_name] <= 0:
            del self.allocations[broker_name]
        
        self._update_available_capital()
        
        # Record transaction
        transaction = {
            'id': f"release_{datetime.now().timestamp()}",
            'type': 'release',
            'broker': broker_name,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Released ${amount:.2f} from {broker_name}")
        
        return {
            'success': True,
            'released': amount,
            'broker': broker_name,
            'available': self.available_capital
        }
    
    def record_profit(self, amount: float, source: str = "trading") -> Dict:
        """
        Record trading profit back to PayPal wallet
        
        Args:
            amount: Profit amount
            source: Source of profit (trading, dividend, etc.)
            
        Returns:
            Dict with profit record
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        self.total_capital += amount
        self._update_available_capital()
        
        transaction = {
            'id': f"profit_{datetime.now().timestamp()}",
            'type': 'profit',
            'amount': amount,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Profit recorded: ${amount:.2f} from {source}")
        
        return {
            'success': True,
            'profit': amount,
            'new_balance': self.total_capital
        }
    
    def record_loss(self, amount: float, source: str = "trading") -> Dict:
        """
        Record trading loss from PayPal wallet
        
        Args:
            amount: Loss amount
            source: Source of loss
            
        Returns:
            Dict with loss record
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        self.total_capital -= amount
        self._update_available_capital()
        
        transaction = {
            'id': f"loss_{datetime.now().timestamp()}",
            'type': 'loss',
            'amount': amount,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Loss recorded: ${amount:.2f} from {source}")
        
        return {
            'success': True,
            'loss': amount,
            'new_balance': self.total_capital
        }
    
    # ===== PayPal API Functions =====
    
    def get_balance(self) -> Dict:
        """Get PayPal wallet balance and capital status"""
        if self.enabled and self.connected:
            self._sync_balance()
        
        return {
            'total_capital': self.total_capital,
            'available_capital': self.available_capital,
            'allocated_capital': self.allocated_capital,
            'allocations': self.allocations,
            'currency': 'USD',
            'enabled': self.enabled,
            'connected': self.connected
        }
    
    def send_payout(self, recipient_email: str, amount: float, currency: str = "USD",
                   note: str = "OMNIBOT Trading Payout") -> Dict:
        """Send payout from PayPal wallet"""
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        if not self._ensure_token():
            return {'success': False, 'error': 'Not connected to PayPal'}
        
        if self.sandbox:
            logger.warning("[PAYPAL] Running in sandbox mode - no real money will be sent")
        
        try:
            url = f"{self.base_url}/v1/payments/payouts"
            
            payout_data = {
                "sender_batch_header": {
                    "sender_batch_id": f"OMNIBOT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "email_subject": "OMNIBOT Trading Payout",
                    "email_message": note
                },
                "items": [{
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": currency
                    },
                    "receiver": recipient_email,
                    "note": note,
                    "sender_item_id": f"payout_{datetime.now().timestamp()}"
                }]
            }
            
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json=payout_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                batch_id = data.get('batch_header', {}).get('payout_batch_id')
                
                # Deduct from balance
                self.total_capital -= amount
                self._update_available_capital()
                
                transaction = {
                    'id': batch_id,
                    'type': 'payout',
                    'recipient': recipient_email,
                    'amount': amount,
                    'currency': currency,
                    'status': 'PENDING',
                    'timestamp': datetime.now().isoformat()
                }
                self.transactions.append(transaction)
                
                logger.info(f"[PAYPAL] Payout initiated: {amount} {currency} to {recipient_email}")
                
                return {
                    'success': True,
                    'batch_id': batch_id,
                    'status': 'PENDING',
                    'amount': amount,
                    'currency': currency
                }
            else:
                error_msg = response.json().get('message', 'Unknown error')
                logger.error(f"[PAYPAL] Payout failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"[PAYPAL] Payout error: {e}")
            return {'success': False, 'error': str(e)}
    
    def deposit(self, amount: float, currency: str = "USD", 
                source: str = "manual") -> Dict:
        """
        Record a deposit to PayPal wallet
        
        Args:
            amount: Deposit amount
            currency: Currency code
            source: Source of deposit (manual, transfer, etc.)
            
        Returns:
            Dict with deposit info
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        self.total_capital += amount
        self._update_available_capital()
        
        transaction = {
            'id': f"deposit_{datetime.now().timestamp()}",
            'type': 'deposit',
            'amount': amount,
            'currency': currency,
            'source': source,
            'status': 'COMPLETED',
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Deposit recorded: {amount} {currency} from {source}")
        
        return {
            'success': True,
            'amount': amount,
            'currency': currency,
            'new_balance': self.total_capital
        }
    
    def withdraw(self, amount: float, currency: str = "USD") -> Dict:
        """
        Record a withdrawal from PayPal wallet
        
        Args:
            amount: Withdrawal amount
            currency: Currency code
            
        Returns:
            Dict with withdrawal info
        """
        if not self.enabled:
            return {'success': False, 'error': 'PayPal wallet is disabled'}
        
        if amount > self.available_capital:
            return {
                'success': False,
                'error': f'Insufficient available funds. Available: ${self.available_capital:.2f}'
            }
        
        self.total_capital -= amount
        self._update_available_capital()
        
        transaction = {
            'id': f"withdrawal_{datetime.now().timestamp()}",
            'type': 'withdrawal',
            'amount': amount,
            'currency': currency,
            'status': 'COMPLETED',
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        logger.info(f"[PAYPAL] Withdrawal recorded: {amount} {currency}")
        
        return {
            'success': True,
            'amount': amount,
            'currency': currency,
            'new_balance': self.total_capital
        }
    
    def get_transactions(self, transaction_type: str = None, limit: int = 100) -> List[Dict]:
        """
        Get transaction history
        
        Args:
            transaction_type: Filter by type (deposit, withdrawal, profit, loss, allocation)
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions
        """
        transactions = self.transactions
        
        if transaction_type:
            transactions = [t for t in transactions if t.get('type') == transaction_type]
        
        # Sort by timestamp (newest first)
        transactions = sorted(transactions, 
                            key=lambda x: x.get('timestamp', ''), 
                            reverse=True)
        
        return transactions[:limit]
    
    def get_allocations(self) -> Dict[str, float]:
        """Get current capital allocations to brokers"""
        return self.allocations.copy()
    
    # ===== BaseBroker Interface =====
    
    def get_positions(self) -> Dict[str, Dict]:
        """PayPal doesn't have trading positions"""
        return {}
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value (total capital in wallet)"""
        return self.total_capital
    
    def get_status(self) -> Dict:
        """Get wallet status"""
        return {
            'enabled': self.enabled,
            'connected': self.connected,
            'configured': self.configured and bool(self.client_id and self.client_secret),
            'sandbox': self.sandbox,
            'balance': self.get_balance()
        }
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = 'market', limit_price: float = None) -> Dict:
        """
        PayPal wallet doesn't place trading orders directly.
        Use allocate_to_broker() to fund a trading broker.
        """
        return {
            'success': False,
            'error': 'PayPal wallet does not place orders directly. Use allocate_to_broker() to fund trading.'
        }
