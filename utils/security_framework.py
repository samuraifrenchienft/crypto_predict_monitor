"""
Active Protection Layers Security Framework
Comprehensive security system for API, Wallet, Operations, Data, Webhooks, and Monitoring
"""

import os
import json
import time
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from functools import wraps
import redis
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import asyncio
from collections import defaultdict, deque
import threading

# Configure security logging
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
handler = logging.FileHandler('security.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
security_logger.addHandler(handler)

@dataclass
class SecurityEvent:
    """Security event for monitoring"""
    event_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    user_id: Optional[str]
    ip_address: str
    timestamp: datetime
    details: Dict[str, Any]
    action_taken: Optional[str] = None

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10

@dataclass
class WalletSecurityConfig:
    """Wallet security configuration"""
    max_trade_value: float = 1000.0
    nonce_timeout: int = 300  # 5 minutes
    signature_timeout: int = 60  # 1 minute
    require_whitelist: bool = True

@dataclass
class OperationsConfig:
    """Operations security configuration"""
    max_spread: float = 1.00
    min_liquidity: float = 100.0
    timeout_seconds: int = 30
    max_trades_per_minute: int = 5

class EncryptionManager:
    """Handles encryption and decryption of sensitive data"""
    
    def __init__(self):
        self._cipher = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption with secure key derivation"""
        try:
            # Get encryption key from environment or derive from password
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                # Derive key from master password
                password = os.getenv('MASTER_PASSWORD', 'default_secure_password').encode()
                salt = os.getenv('ENCRYPTION_SALT', 'default_salt').encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                encryption_key = key.decode()
            
            self._cipher = Fernet(encryption_key.encode())
            security_logger.info("Encryption manager initialized successfully")
        except Exception as e:
            security_logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if not self._cipher:
                raise RuntimeError("Encryption not initialized")
            encrypted_data = self._cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            security_logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not self._cipher:
                raise RuntimeError("Encryption not initialized")
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            security_logger.error(f"Decryption failed: {e}")
            raise

class RateLimiter:
    """Redis-based rate limiting with sliding window"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.config = RateLimitConfig()
    
    def _get_key(self, identifier: str, window: str) -> str:
        """Generate rate limit key"""
        return f"rate_limit:{identifier}:{window}"
    
    async def is_allowed(self, identifier: str, config: Optional[RateLimitConfig] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        cfg = config or self.config
        current_time = int(time.time())
        
        # Check minute window
        minute_key = self._get_key(identifier, "minute")
        minute_count = await self._check_window(minute_key, current_time, 60, cfg.requests_per_minute)
        
        # Check hour window
        hour_key = self._get_key(identifier, "hour")
        hour_count = await self._check_window(hour_key, current_time, 3600, cfg.requests_per_hour)
        
        # Check day window
        day_key = self._get_key(identifier, "day")
        day_count = await self._check_window(day_key, current_time, 86400, cfg.requests_per_day)
        
        is_allowed = (
            minute_count <= cfg.requests_per_minute and
            hour_count <= cfg.requests_per_hour and
            day_count <= cfg.requests_per_day
        )
        
        return is_allowed, {
            'minute_count': minute_count,
            'hour_count': hour_count,
            'day_count': day_count,
            'limits': asdict(cfg)
        }
    
    async def _check_window(self, key: str, current_time: int, window_size: int, limit: int) -> int:
        """Check specific time window"""
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, current_time - window_size)
        
        # Count current entries
        count = await self.redis.zcard(key)
        
        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, window_size)
        
        return count

class WalletSecurity:
    """Wallet signature verification and security controls"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.config = WalletSecurityConfig()
        self.encryption = EncryptionManager()
    
    def generate_nonce(self, user_id: str) -> str:
        """Generate secure nonce for signature verification"""
        nonce = base64.urlsafe_b64encode(os.urandom(32)).decode()
        key = f"nonce:{user_id}:{nonce}"
        self.redis.setex(key, self.config.nonce_timeout, "1")
        return nonce
    
    async def verify_signature(self, user_id: str, message: str, signature: str, nonce: str) -> bool:
        """Verify cryptographic signature with nonce"""
        try:
            # Check if nonce exists and is valid
            nonce_key = f"nonce:{user_id}:{nonce}"
            if not self.redis.exists(nonce_key):
                security_logger.warning(f"Invalid or expired nonce for user {user_id}")
                return False
            
            # Verify signature (simplified - implement actual Web3 verification)
            # This would integrate with Web3.py for proper signature verification
            is_valid = self._verify_ethereum_signature(message, signature, user_id)
            
            if is_valid:
                # Consume nonce to prevent replay
                self.redis.delete(nonce_key)
                security_logger.info(f"Signature verified for user {user_id}")
            else:
                security_logger.warning(f"Invalid signature for user {user_id}")
            
            return is_valid
            
        except Exception as e:
            security_logger.error(f"Signature verification error: {e}")
            return False
    
    def _verify_ethereum_signature(self, message: str, signature: str, address: str) -> bool:
        """Verify Ethereum signature (simplified implementation)"""
        # This would use Web3.py's account.recover_message function
        # For now, return True as placeholder
        return True
    
    async def check_trade_limit(self, user_id: str, trade_value: float) -> bool:
        """Check if trade value exceeds limits"""
        if trade_value > self.config.max_trade_value:
            security_logger.warning(f"Trade value ${trade_value} exceeds limit for user {user_id}")
            return False
        
        # Check total trades in last minute
        minute_key = f"trades:{user_id}:minute"
        current_time = int(time.time())
        await self.redis.zremrangebyscore(minute_key, 0, current_time - 60)
        trade_count = await self.redis.zcard(minute_key)
        
        if trade_count >= 5:  # Max 5 trades per minute
            security_logger.warning(f"Too many trades for user {user_id} in last minute")
            return False
        
        # Record this trade
        await self.redis.zadd(minute_key, {str(current_time): trade_value})
        await self.redis.expire(minute_key, 60)
        
        return True

class OperationsSecurity:
    """Operations validation and security controls"""
    
    def __init__(self):
        self.config = OperationsConfig()
    
    def validate_trade(self, trade_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate trade parameters"""
        errors = []
        
        # Check spread
        if 'spread' in trade_data and trade_data['spread'] > self.config.max_spread:
            errors.append(f"Spread {trade_data['spread']} exceeds maximum {self.config.max_spread}")
        
        # Check liquidity
        if 'liquidity' in trade_data and trade_data['liquidity'] < self.config.min_liquidity:
            errors.append(f"Liquidity ${trade_data['liquidity']} below minimum ${self.config.min_liquidity}")
        
        # Check required fields
        required_fields = ['market_id', 'side', 'amount', 'price']
        for field in required_fields:
            if field not in trade_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate amount
        if 'amount' in trade_data:
            try:
                amount = float(trade_data['amount'])
                if amount <= 0:
                    errors.append("Trade amount must be positive")
            except (ValueError, TypeError):
                errors.append("Invalid trade amount")
        
        is_valid = len(errors) == 0
        if not is_valid:
            security_logger.warning(f"Trade validation failed: {errors}")
        
        return is_valid, errors

class WebhookSecurity:
    """Webhook signature verification and security"""
    
    def __init__(self):
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', 'default_webhook_secret')
        self.processed_nonces = deque(maxlen=10000)  # Prevent replay attacks
    
    def verify_webhook_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """Verify HMAC signature of webhook"""
        try:
            # Check timestamp to prevent replay attacks
            webhook_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - webhook_time) > 300:  # 5 minute window
                security_logger.warning("Webhook timestamp outside valid window")
                return False
            
            # Check for replay
            nonce = f"{timestamp}:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"
            if nonce in self.processed_nonces:
                security_logger.warning("Duplicate webhook detected")
                return False
            
            # Verify HMAC signature
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                f"{timestamp}.{payload}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if is_valid:
                self.processed_nonces.append(nonce)
                security_logger.info("Webhook signature verified")
            else:
                security_logger.warning("Invalid webhook signature")
            
            return is_valid
            
        except Exception as e:
            security_logger.error(f"Webhook signature verification error: {e}")
            return False

class SecurityMonitor:
    """Security monitoring and threat detection"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.suspicious_activities = defaultdict(list)
        self.alert_thresholds = {
            'login_attempts_per_5min': 10,
            'failed_logins_per_5min': 5,
            'large_trades_per_hour': 3,
            'api_calls_per_minute': 200,
        }
    
    async def log_security_event(self, event: SecurityEvent):
        """Log security event and check for threats"""
        # Store event
        event_data = asdict(event)
        event_data['timestamp'] = event.timestamp.isoformat()
        
        await self.redis.lpush('security_events', json.dumps(event_data))
        await self.redis.expire('security_events', 86400)  # Keep for 24 hours
        
        # Check for suspicious patterns
        await self._check_suspicious_activity(event)
        
        # Log based on severity
        if event.severity in ['HIGH', 'CRITICAL']:
            security_logger.critical(f"Security event: {event.event_type} - {event.details}")
        elif event.severity == 'MEDIUM':
            security_logger.warning(f"Security event: {event.event_type} - {event.details}")
        else:
            security_logger.info(f"Security event: {event.event_type} - {event.details}")
    
    async def _check_suspicious_activity(self, event: SecurityEvent):
        """Check for suspicious activity patterns"""
        current_time = datetime.utcnow()
        
        # Check for multiple login attempts
        if event.event_type == 'login_attempt':
            recent_logins = await self._count_recent_events(
                'login_attempt', event.user_id, current_time, timedelta(minutes=5)
            )
            
            if recent_logins > self.alert_thresholds['login_attempts_per_5min']:
                await self._trigger_security_alert(
                    'MULTIPLE_LOGIN_ATTEMPTS',
                    'HIGH',
                    event.user_id,
                    event.ip_address,
                    {'attempts': recent_logins, 'timeframe': '5 minutes'}
                )
        
        # Check for large trades
        if event.event_type == 'trade' and event.details.get('value', 0) > 5000:
            recent_large_trades = await self._count_recent_events(
                'large_trade', event.user_id, current_time, timedelta(hours=1)
            )
            
            if recent_large_trades >= self.alert_thresholds['large_trades_per_hour']:
                await self._trigger_security_alert(
                    'MULTIPLE_LARGE_TRADES',
                    'HIGH',
                    event.user_id,
                    event.ip_address,
                    {'trades': recent_large_trades, 'timeframe': '1 hour'}
                )
    
    async def _count_recent_events(self, event_type: str, user_id: str, current_time: datetime, timeframe: timedelta) -> int:
        """Count recent events for a user"""
        cutoff_time = current_time - timeframe
        events = await self.redis.lrange('security_events', 0, -1)
        
        count = 0
        for event_json in events:
            try:
                event = json.loads(event_json)
                event_time = datetime.fromisoformat(event['timestamp'])
                
                if (event['event_type'] == event_type and 
                    event['user_id'] == user_id and 
                    event_time > cutoff_time):
                    count += 1
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        return count
    
    async def _trigger_security_alert(self, alert_type: str, severity: str, user_id: str, ip_address: str, details: Dict[str, Any]):
        """Trigger security alert"""
        alert = SecurityEvent(
            event_type=alert_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            details=details,
            action_taken='ALERT_TRIGGERED'
        )
        
        await self.log_security_event(alert)
        
        # Here you could also send notifications, block IPs, etc.
        security_logger.critical(f"SECURITY ALERT: {alert_type} for user {user_id} from {ip_address}")

class SecurityFramework:
    """Main security framework orchestrator"""
    
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
            self.redis.ping()  # Test connection
        except Exception as e:
            security_logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        self.rate_limiter = RateLimiter(self.redis)
        self.wallet_security = WalletSecurity(self.redis)
        self.operations_security = OperationsSecurity()
        self.webhook_security = WebhookSecurity()
        self.monitor = SecurityMonitor(self.redis)
        self.encryption = EncryptionManager()
        
        security_logger.info("Security framework initialized successfully")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis:
            await self.redis.close()

# Decorators for easy integration
def require_rate_limit(identifier_func=None, config: Optional[RateLimitConfig] = None):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            framework = get_security_framework()
            identifier = identifier_func(*args, **kwargs) if identifier_func else kwargs.get('user_id', 'anonymous')
            
            is_allowed, limits = await framework.rate_limiter.is_allowed(identifier, config)
            if not is_allowed:
                await framework.monitor.log_security_event(SecurityEvent(
                    event_type='rate_limit_exceeded',
                    severity='MEDIUM',
                    user_id=identifier,
                    ip_address=kwargs.get('ip_address', 'unknown'),
                    timestamp=datetime.utcnow(),
                    details=limits
                ))
                raise Exception("Rate limit exceeded")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_wallet_signature():
    """Decorator for wallet signature verification"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            framework = get_security_framework()
            user_id = kwargs.get('user_id')
            message = kwargs.get('message')
            signature = kwargs.get('signature')
            nonce = kwargs.get('nonce')
            
            if not all([user_id, message, signature, nonce]):
                raise Exception("Missing wallet signature parameters")
            
            is_valid = await framework.wallet_security.verify_signature(user_id, message, signature, nonce)
            if not is_valid:
                await framework.monitor.log_security_event(SecurityEvent(
                    event_type='invalid_signature',
                    severity='HIGH',
                    user_id=user_id,
                    ip_address=kwargs.get('ip_address', 'unknown'),
                    timestamp=datetime.utcnow(),
                    details={'message': message[:100]}  # Log first 100 chars
                ))
                raise Exception("Invalid wallet signature")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def validate_trade_operation():
    """Decorator for trade validation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            framework = get_security_framework()
            trade_data = kwargs.get('trade_data', {})
            
            is_valid, errors = framework.operations_security.validate_trade(trade_data)
            if not is_valid:
                await framework.monitor.log_security_event(SecurityEvent(
                    event_type='invalid_trade',
                    severity='MEDIUM',
                    user_id=kwargs.get('user_id'),
                    ip_address=kwargs.get('ip_address', 'unknown'),
                    timestamp=datetime.utcnow(),
                    details={'errors': errors, 'trade_data': trade_data}
                ))
                raise Exception(f"Trade validation failed: {errors}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Global security framework instance
_security_framework = None

def get_security_framework() -> SecurityFramework:
    """Get or create security framework instance"""
    global _security_framework
    if _security_framework is None:
        _security_framework = SecurityFramework()
    return _security_framework

async def initialize_security():
    """Initialize security framework"""
    framework = get_security_framework()
    security_logger.info("Security system initialized")

async def shutdown_security():
    """Shutdown security framework"""
    global _security_framework
    if _security_framework:
        await _security_framework.shutdown()
        _security_framework = None
