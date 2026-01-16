"""
Wallet Security Implementation
Signature verification, nonces, trade limits, and secure wallet operations
"""

import os
import time
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import logging
from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

@dataclass
class WalletTransaction:
    """Wallet transaction data"""
    transaction_hash: str
    user_address: str
    amount: float
    gas_price: float
    gas_limit: int
    nonce: int
    timestamp: datetime
    signature: str
    message: str
    is_validated: bool = False

@dataclass
class TradeLimit:
    """Trade limit configuration"""
    max_single_trade: float = 1000.0
    max_daily_volume: float = 10000.0
    max_hourly_trades: int = 10
    max_daily_trades: int = 50
    cooldown_period: int = 30  # seconds between trades

class WalletSecurity:
    """Advanced wallet security implementation"""
    
    def __init__(self):
        self.security = get_security_framework()
        self.w3 = Web3()  # For signature verification
        self.trade_limits = TradeLimit()
        
        # Whitelist of approved contracts (for future use)
        self.approved_contracts = set()
        
        # Suspicious activity tracking
        self.suspicious_addresses = set()
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load wallet security configuration"""
        # Load approved contracts from environment
        contracts = os.getenv('APPROVED_CONTRACTS', '').split(',')
        self.approved_contracts = {c.strip() for c in contracts if c.strip()}
        
        # Load suspicious addresses
        suspicious = os.getenv('SUSPICIOUS_ADDRESSES', '').split(',')
        self.suspicious_addresses = {c.strip().lower() for c in suspicious if c.strip()}
    
    def generate_secure_message(self, user_address: str, trade_data: Dict[str, Any]) -> str:
        """Generate secure message for signing"""
        timestamp = int(time.time())
        nonce = os.urandom(16).hex()
        
        message_data = {
            'address': user_address.lower(),
            'trade': trade_data,
            'timestamp': timestamp,
            'nonce': nonce,
            'domain': 'crypto-predict-monitor.com'
        }
        
        message = json.dumps(message_data, separators=(',', ':'), sort_keys=True)
        return message
    
    def generate_nonce(self, user_address: str) -> str:
        """Generate cryptographically secure nonce"""
        timestamp = int(time.time())
        random_bytes = os.urandom(16)
        
        nonce_data = f"{user_address.lower()}:{timestamp}:{random_bytes.hex()}"
        nonce_hash = hashlib.sha256(nonce_data.encode()).hexdigest()
        
        # Store nonce with expiration
        key = f"wallet_nonce:{user_address.lower()}:{nonce_hash}"
        self.security.redis.setex(key, 300, json.dumps({
            'timestamp': timestamp,
            'used': False
        }))
        
        return nonce_hash
    
    async def verify_signature(self, user_address: str, message: str, signature: str, nonce: str) -> Tuple[bool, Optional[str]]:
        """Verify Ethereum signature with comprehensive checks"""
        try:
            # 1. Basic format validation
            if not self._validate_signature_format(signature):
                return False, "Invalid signature format"
            
            # 2. Check nonce validity
            nonce_valid, nonce_error = await self._verify_nonce(user_address, nonce)
            if not nonce_valid:
                return False, nonce_error
            
            # 3. Check message timestamp
            message_valid, message_error = self._validate_message_timestamp(message)
            if not message_valid:
                return False, message_error
            
            # 4. Check for suspicious address
            if user_address.lower() in self.suspicious_addresses:
                await self._log_security_event(
                    'suspicious_address_access',
                    'HIGH',
                    user_address,
                    'system',
                    {'message': 'Access from suspicious address'}
                )
                return False, "Address flagged as suspicious"
            
            # 5. Recover address from signature
            try:
                message_hash = encode_defunct(text=message)
                recovered_address = self.w3.eth.account.recover_message(message_hash, signature=signature)
                
                # Normalize addresses for comparison
                recovered_address = recovered_address.lower()
                user_address_normalized = user_address.lower()
                
                if recovered_address != user_address_normalized:
                    await self._log_security_event(
                        'signature_mismatch',
                        'HIGH',
                        user_address,
                        'system',
                        {
                            'expected': user_address_normalized,
                            'recovered': recovered_address,
                            'message_hash': message_hash.hex()
                        }
                    )
                    return False, "Signature verification failed"
                
            except Exception as e:
                await self._log_security_event(
                    'signature_recovery_error',
                    'HIGH',
                    user_address,
                    'system',
                    {'error': str(e)}
                )
                return False, "Signature recovery failed"
            
            # 6. Mark nonce as used
            await self._consume_nonce(user_address, nonce)
            
            # 7. Log successful verification
            await self._log_security_event(
                'signature_verified',
                'LOW',
                user_address,
                'system',
                {'nonce': nonce[:16]}  # Log partial nonce for privacy
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            await self._log_security_event(
                'signature_verification_error',
                'HIGH',
                user_address,
                'system',
                {'error': str(e)}
            )
            return False, "Verification error"
    
    def _validate_signature_format(self, signature: str) -> bool:
        """Validate signature format"""
        try:
            # Remove 0x prefix if present
            if signature.startswith('0x'):
                signature = signature[2:]
            
            # Check length (65 bytes for standard Ethereum signature)
            if len(signature) != 130:
                return False
            
            # Check if it's valid hex
            int(signature, 16)
            return True
            
        except ValueError:
            return False
    
    async def _verify_nonce(self, user_address: str, nonce: str) -> Tuple[bool, Optional[str]]:
        """Verify nonce is valid and not used"""
        try:
            key = f"wallet_nonce:{user_address.lower()}:{nonce}"
            nonce_data = await self.security.redis.get(key)
            
            if not nonce_data:
                return False, "Invalid or expired nonce"
            
            data = json.loads(nonce_data)
            if data.get('used', False):
                return False, "Nonce already used"
            
            # Check timestamp (5 minute window)
            timestamp = data.get('timestamp', 0)
            current_time = int(time.time())
            if current_time - timestamp > 300:
                await self.security.redis.delete(key)
                return False, "Nonce expired"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Nonce verification error: {e}")
            return False, "Nonce verification failed"
    
    async def _consume_nonce(self, user_address: str, nonce: str):
        """Mark nonce as used"""
        try:
            key = f"wallet_nonce:{user_address.lower()}:{nonce}"
            nonce_data = await self.security.redis.get(key)
            
            if nonce_data:
                data = json.loads(nonce_data)
                data['used'] = True
                await self.security.redis.setex(key, 300, json.dumps(data))
                
        except Exception as e:
            logger.error(f"Nonce consumption error: {e}")
    
    def _validate_message_timestamp(self, message: str) -> Tuple[bool, Optional[str]]:
        """Validate message timestamp"""
        try:
            message_data = json.loads(message)
            timestamp = message_data.get('timestamp', 0)
            current_time = int(time.time())
            
            # Message should be within 5 minutes
            if abs(current_time - timestamp) > 300:
                return False, "Message timestamp too old"
            
            return True, None
            
        except (json.JSONDecodeError, KeyError):
            return False, "Invalid message format"
    
    async def check_trade_limits(self, user_address: str, trade_value: float) -> Tuple[bool, Optional[str]]:
        """Comprehensive trade limit checking"""
        try:
            user_address = user_address.lower()
            current_time = datetime.utcnow()
            
            # 1. Check single trade limit
            if trade_value > self.trade_limits.max_single_trade:
                await self._log_security_event(
                    'trade_limit_exceeded',
                    'MEDIUM',
                    user_address,
                    'system',
                    {
                        'type': 'single_trade',
                        'value': trade_value,
                        'limit': self.trade_limits.max_single_trade
                    }
                )
                return False, f"Trade value ${trade_value} exceeds single trade limit ${self.trade_limits.max_single_trade}"
            
            # 2. Check cooldown period
            cooldown_key = f"trade_cooldown:{user_address}"
            last_trade_time = await self.security.redis.get(cooldown_key)
            
            if last_trade_time:
                last_time = datetime.fromisoformat(last_trade_time)
                if (current_time - last_time).seconds < self.trade_limits.cooldown_period:
                    remaining = self.trade_limits.cooldown_period - (current_time - last_time).seconds
                    return False, f"Cooldown period active. Wait {remaining} seconds"
            
            # 3. Check hourly trade count
            hourly_key = f"trades_hourly:{user_address}"
            await self._cleanup_old_trades(hourly_key, 3600)  # 1 hour
            hourly_count = await self.security.redis.zcard(hourly_key)
            
            if hourly_count >= self.trade_limits.max_hourly_trades:
                await self._log_security_event(
                    'trade_limit_exceeded',
                    'MEDIUM',
                    user_address,
                    'system',
                    {
                        'type': 'hourly_count',
                        'count': hourly_count,
                        'limit': self.trade_limits.max_hourly_trades
                    }
                )
                return False, f"Hourly trade limit exceeded ({hourly_count}/{self.trade_limits.max_hourly_trades})"
            
            # 4. Check daily trade count
            daily_key = f"trades_daily:{user_address}"
            await self._cleanup_old_trades(daily_key, 86400)  # 24 hours
            daily_count = await self.security.redis.zcard(daily_key)
            
            if daily_count >= self.trade_limits.max_daily_trades:
                await self._log_security_event(
                    'trade_limit_exceeded',
                    'MEDIUM',
                    user_address,
                    'system',
                    {
                        'type': 'daily_count',
                        'count': daily_count,
                        'limit': self.trade_limits.max_daily_trades
                    }
                )
                return False, f"Daily trade limit exceeded ({daily_count}/{self.trade_limits.max_daily_trades})"
            
            # 5. Check daily volume
            daily_volume = 0
            daily_trades = await self.security.redis.zrange(daily_key, 0, -1, withscores=True)
            
            for trade_json, score in daily_trades:
                try:
                    trade = json.loads(trade_json)
                    daily_volume += trade.get('value', 0)
                except json.JSONDecodeError:
                    continue
            
            if daily_volume + trade_value > self.trade_limits.max_daily_volume:
                await self._log_security_event(
                    'trade_limit_exceeded',
                    'HIGH',
                    user_address,
                    'system',
                    {
                        'type': 'daily_volume',
                        'current_volume': daily_volume,
                        'trade_value': trade_value,
                        'limit': self.trade_limits.max_daily_volume
                    }
                )
                return False, f"Daily volume limit exceeded (${daily_volume + trade_value}/${self.trade_limits.max_daily_volume})"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Trade limit check error: {e}")
            return False, "Trade limit check failed"
    
    async def record_trade(self, user_address: str, trade_value: float, trade_data: Dict[str, Any]):
        """Record trade for limit tracking"""
        try:
            user_address = user_address.lower()
            current_time = datetime.utcnow()
            
            # Record cooldown
            cooldown_key = f"trade_cooldown:{user_address}"
            await self.security.redis.setex(cooldown_key, self.trade_limits.cooldown_period, current_time.isoformat())
            
            # Record in hourly and daily tracking
            trade_record = {
                'value': trade_value,
                'timestamp': current_time.isoformat(),
                'data': trade_data
            }
            
            hourly_key = f"trades_hourly:{user_address}"
            daily_key = f"trades_daily:{user_address}"
            
            await self.security.redis.zadd(hourly_key, {json.dumps(trade_record): current_time.timestamp()})
            await self.security.redis.expire(hourly_key, 3600)
            
            await self.security.redis.zadd(daily_key, {json.dumps(trade_record): current_time.timestamp()})
            await self.security.redis.expire(daily_key, 86400)
            
            # Log successful trade
            await self._log_security_event(
                'trade_recorded',
                'LOW',
                user_address,
                'system',
                {'value': trade_value, 'data': trade_data}
            )
            
        except Exception as e:
            logger.error(f"Trade recording error: {e}")
    
    async def _cleanup_old_trades(self, key: str, max_age: int):
        """Clean up old trade records"""
        try:
            cutoff_time = time.time() - max_age
            await self.security.redis.zremrangebyscore(key, 0, cutoff_time)
        except Exception as e:
            logger.error(f"Trade cleanup error: {e}")
    
    async def validate_transaction(self, transaction: WalletTransaction) -> Tuple[bool, List[str]]:
        """Validate wallet transaction"""
        errors = []
        
        # 1. Basic validation
        if not transaction.transaction_hash:
            errors.append("Transaction hash required")
        
        if not transaction.user_address or not self.w3.is_address(transaction.user_address):
            errors.append("Invalid user address")
        
        if transaction.amount <= 0:
            errors.append("Amount must be positive")
        
        if transaction.gas_price <= 0:
            errors.append("Gas price must be positive")
        
        if transaction.gas_limit <= 0:
            errors.append("Gas limit must be positive")
        
        # 2. Check gas costs
        gas_cost = transaction.gas_price * transaction.gas_limit
        if gas_cost > 0.1:  # Max 0.1 ETH for gas
            errors.append(f"Gas cost too high: {gas_cost} ETH")
        
        # 3. Check transaction value
        if transaction.amount > self.trade_limits.max_single_trade:
            errors.append(f"Transaction amount exceeds limit: ${transaction.amount}")
        
        # 4. Check for replay attacks
        tx_key = f"transaction:{transaction.transaction_hash}"
        if await self.security.redis.exists(tx_key):
            errors.append("Transaction already processed")
        
        return len(errors) == 0, errors
    
    async def process_transaction(self, transaction: WalletTransaction) -> Tuple[bool, Optional[str]]:
        """Process validated transaction"""
        try:
            # Mark transaction as processed
            tx_key = f"transaction:{transaction.transaction_hash}"
            await self.security.redis.setex(tx_key, 86400, json.dumps(asdict(transaction)))
            
            # Record trade if applicable
            if transaction.amount > 0:
                await self.record_trade(
                    transaction.user_address,
                    transaction.amount,
                    {
                        'hash': transaction.transaction_hash,
                        'gas_price': transaction.gas_price,
                        'gas_limit': transaction.gas_limit
                    }
                )
            
            # Log successful processing
            await self._log_security_event(
                'transaction_processed',
                'LOW',
                transaction.user_address,
                'system',
                {'hash': transaction.transaction_hash, 'amount': transaction.amount}
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Transaction processing error: {e}")
            return False, str(e)
    
    async def _log_security_event(self, event_type: str, severity: str, user_address: str, 
                                 ip_address: str, details: Dict[str, Any]):
        """Log security event"""
        await self.security.monitor.log_security_event(SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_address,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            details=details
        ))
    
    def get_user_trade_stats(self, user_address: str) -> Dict[str, Any]:
        """Get user's trading statistics"""
        try:
            user_address = user_address.lower()
            current_time = datetime.utcnow()
            
            # Get daily trades
            daily_key = f"trades_daily:{user_address}"
            daily_trades = self.security.redis.zrange(daily_key, 0, -1, withscores=True)
            
            # Calculate stats
            daily_volume = 0
            daily_count = len(daily_trades)
            largest_trade = 0
            
            for trade_json, score in daily_trades:
                try:
                    trade = json.loads(trade_json)
                    value = trade.get('value', 0)
                    daily_volume += value
                    largest_trade = max(largest_trade, value)
                except json.JSONDecodeError:
                    continue
            
            # Get hourly trades
            hourly_key = f"trades_hourly:{user_address}"
            hourly_count = self.security.redis.zcard(hourly_key)
            
            # Check cooldown
            cooldown_key = f"trade_cooldown:{user_address}"
            last_trade = self.security.redis.get(cooldown_key)
            
            cooldown_remaining = 0
            if last_trade:
                last_time = datetime.fromisoformat(last_trade)
                elapsed = (current_time - last_time).seconds
                cooldown_remaining = max(0, self.trade_limits.cooldown_period - elapsed)
            
            return {
                'daily_volume': daily_volume,
                'daily_trades': daily_count,
                'hourly_trades': hourly_count,
                'largest_trade': largest_trade,
                'cooldown_remaining': cooldown_remaining,
                'limits': asdict(self.trade_limits)
            }
            
        except Exception as e:
            logger.error(f"Error getting trade stats: {e}")
            return {}

# Initialize wallet security
wallet_security = WalletSecurity()
