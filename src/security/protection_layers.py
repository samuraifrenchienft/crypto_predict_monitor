"""
Complete Protection Layers Integration
9-Layer Security System for Crypto Predict Monitor
"""

import os
import json
import time
import hmac
import hashlib
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path
import statistics
import base64
from cryptography.fernet import Fernet
import re

logger = logging.getLogger(__name__)

# ============================================================================
# LAYER 1: API & Webhook Security
# ============================================================================

class WebhookSignatureValidator:
    """Validate webhook signatures and prevent replay attacks"""
    
    def __init__(self, secret: str = None):
        self.secret = secret or os.getenv('WEBHOOK_SECRET', 'default_webhook_secret')
        self.seen_nonces = deque(maxlen=10000)  # Track recent nonces
    
    def validate_signature(self, payload: str, signature: str, timestamp: str, nonce: str) -> Tuple[bool, str]:
        """Validate webhook signature with replay protection"""
        try:
            # Check timestamp (prevent replay attacks)
            try:
                event_time = int(timestamp)
                current_time = int(time.time())
                if abs(current_time - event_time) > 300:  # 5 minutes
                    return False, "Timestamp too old"
            except ValueError:
                return False, "Invalid timestamp"
            
            # Check nonce (prevent duplicate requests)
            if nonce in self.seen_nonces:
                return False, "Nonce already used"
            
            # Calculate expected signature
            message = f"{timestamp}.{nonce}.{payload}"
            expected_signature = hmac.new(
                self.secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                return False, "Invalid signature"
            
            # Record nonce
            self.seen_nonces.append(nonce)
            
            return True, "Signature valid"
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False, f"Validation error: {str(e)}"

class RateLimiter:
    """Redis-based rate limiting with sliding windows"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.local_limits = {}  # Fallback for when Redis is unavailable
    
    async def check_limit(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """Check if rate limit is exceeded"""
        try:
            if self.redis:
                return await self._redis_check_limit(key, limit, window)
            else:
                return self._local_check_limit(key, limit, window)
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow on error
    
    async def _redis_check_limit(self, key: str, limit: int, window: int) -> bool:
        """Redis-based rate limiting"""
        current_time = time.time()
        window_start = current_time - window
        
        # Clean old entries
        await self.redis.zremrangebyscore(f"rate_limit:{key}", 0, window_start)
        
        # Count current requests
        request_count = await self.redis.zcard(f"rate_limit:{key}")
        
        if request_count >= limit:
            return False
        
        # Add current request
        await self.redis.zadd(f"rate_limit:{key}", {str(current_time): current_time})
        await self.redis.expire(f"rate_limit:{key}", window)
        
        return True
    
    def _local_check_limit(self, key: str, limit: int, window: int) -> bool:
        """Local memory rate limiting (fallback)"""
        current_time = time.time()
        
        if key not in self.local_limits:
            self.local_limits[key] = deque()
        
        # Clean old entries
        while self.local_limits[key] and self.local_limits[key][0] < current_time - window:
            self.local_limits[key].popleft()
        
        # Check limit
        if len(self.local_limits[key]) >= limit:
            return False
        
        # Add current request
        self.local_limits[key].append(current_time)
        
        return True

# ============================================================================
# LAYER 2: Fetcher Security
# ============================================================================

class FetcherHealthCheck:
    """Monitor fetcher health and detect issues"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {'success': 0, 'failures': 0, 'last_success': None, 'last_failure': None})
        self.failure_threshold = 5  # Failures before marking unhealthy
        self.recovery_threshold = 3  # Successes before marking healthy
    
    def record_success(self, fetcher_id: str):
        """Record successful fetch"""
        stats = self.stats[fetcher_id]
        stats['success'] += 1
        stats['last_success'] = datetime.utcnow()
    
    def record_failure(self, fetcher_id: str, error: str = None):
        """Record failed fetch"""
        stats = self.stats[fetcher_id]
        stats['failures'] += 1
        stats['last_failure'] = datetime.utcnow()
        if error:
            stats['last_error'] = error
    
    def is_healthy(self, fetcher_id: str) -> bool:
        """Check if fetcher is healthy"""
        stats = self.stats[fetcher_id]
        
        # If we have recent successes, consider healthy
        if stats['last_success']:
            time_since_success = (datetime.utcnow() - stats['last_success']).total_seconds()
            if time_since_success < 300:  # 5 minutes
                return True
        
        # If too many failures, mark unhealthy
        return stats['failures'] < self.failure_threshold
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all fetchers"""
        summary = {}
        for fetcher_id, stats in self.stats.items():
            summary[fetcher_id] = {
                'healthy': self.is_healthy(fetcher_id),
                'success_count': stats['success'],
                'failure_count': stats['failures'],
                'last_success': stats['last_success'].isoformat() if stats['last_success'] else None,
                'last_failure': stats['last_failure'].isoformat() if stats['last_failure'] else None,
                'last_error': stats.get('last_error')
            }
        return summary

class FetcherTimeout:
    """Timeout protection for fetch operations"""
    
    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout
        self.active_operations = {}
    
    async def execute_with_timeout(self, coro, timeout: int = None, operation_id: str = None):
        """Execute coroutine with timeout protection"""
        timeout = timeout or self.default_timeout
        operation_id = operation_id or str(id(coro))
        
        try:
            self.active_operations[operation_id] = {
                'start_time': time.time(),
                'timeout': timeout
            }
            
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result, True
            
        except asyncio.TimeoutError:
            logger.warning(f"Operation {operation_id} timed out after {timeout}s")
            return None, False
        finally:
            self.active_operations.pop(operation_id, None)
    
    def get_active_operations(self) -> Dict[str, Any]:
        """Get currently active operations"""
        current_time = time.time()
        active = {}
        
        for op_id, info in self.active_operations.items():
            remaining = info['timeout'] - (current_time - info['start_time'])
            if remaining > 0:
                active[op_id] = {
                    'remaining_time': remaining,
                    'timeout': info['timeout']
                }
        
        return active

# ============================================================================
# LAYER 3: Alert Evaluation Security
# ============================================================================

class AlertValidator:
    """Validate alert structure and content"""
    
    def __init__(self):
        self.required_fields = ['market', 'trigger_type', 'yes_price', 'no_price', 'timestamp']
        self.valid_trigger_types = ['spread', 'movement', 'liquidity', 'volume']
    
    def validate_alert_message(self, alert: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate alert message structure"""
        try:
            # Check required fields
            for field in self.required_fields:
                if field not in alert:
                    return False, f"Missing required field: {field}"
            
            # Validate trigger type
            if alert['trigger_type'] not in self.valid_trigger_types:
                return False, f"Invalid trigger type: {alert['trigger_type']}"
            
            # Validate prices
            yes_price = float(alert['yes_price'])
            no_price = float(alert['no_price'])
            
            if not (0 <= yes_price <= 1) or not (0 <= no_price <= 1):
                return False, "Prices must be between 0 and 1"
            
            # Check price consistency
            if abs(yes_price + no_price - 1.0) > 0.01:
                return False, "Price inconsistency detected"
            
            # Validate timestamp
            try:
                timestamp = int(alert['timestamp'])
                current_time = int(time.time())
                if abs(current_time - timestamp) > 300:  # 5 minutes
                    return False, "Alert timestamp too old"
            except ValueError:
                return False, "Invalid timestamp"
            
            return True, "Alert valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class AlertDuplicateDetector:
    """Detect duplicate alerts to prevent spam"""
    
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.recent_alerts = defaultdict(lambda: deque())
    
    def is_duplicate(self, market: str, trigger_type: str) -> bool:
        """Check if alert is duplicate"""
        current_time = time.time()
        cutoff_time = current_time - (self.window_minutes * 60)
        
        # Clean old alerts
        while self.recent_alerts[(market, trigger_type)] and \
              self.recent_alerts[(market, trigger_type)][0] < cutoff_time:
            self.recent_alerts[(market, trigger_type)].popleft()
        
        # Check if recent alert exists
        if self.recent_alerts[(market, trigger_type)]:
            return True
        
        # Record this alert
        self.recent_alerts[(market, trigger_type)].append(current_time)
        return False

class AlertRateLimiter:
    """Rate limiting for alert sending"""
    
    def __init__(self, max_alerts_per_minute: int = 10):
        self.max_alerts_per_minute = max_alerts_per_minute
        self.alert_times = deque()
    
    async def can_send_alert(self) -> bool:
        """Check if alert can be sent"""
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute ago
        
        # Clean old alerts
        while self.alert_times and self.alert_times[0] < cutoff_time:
            self.alert_times.popleft()
        
        # Check rate limit
        return len(self.alert_times) < self.max_alerts_per_minute
    
    def record_alert_sent(self):
        """Record that an alert was sent"""
        self.alert_times.append(time.time())

class IdempotentAlertTracker:
    """Track sent alerts to prevent duplicates after retries"""
    
    def __init__(self):
        self.sent_alerts = set()
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def generate_alert_id(self, market: str, trigger_type: str, yes_price: float, no_price: float) -> str:
        """Generate unique alert ID"""
        content = f"{market}:{trigger_type}:{yes_price}:{no_price}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def is_already_sent(self, alert_id: str) -> bool:
        """Check if alert was already sent"""
        self._cleanup_old_alerts()
        return alert_id in self.sent_alerts
    
    def mark_sent(self, alert_id: str):
        """Mark alert as sent"""
        self.sent_alerts.add(alert_id)
    
    def _cleanup_old_alerts(self):
        """Clean up old alert IDs"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            # Simple cleanup - keep only recent alerts
            if len(self.sent_alerts) > 10000:
                # Keep only the most recent 5000
                self.sent_alerts = set(list(self.sent_alerts)[-5000:])
            self.last_cleanup = current_time

# ============================================================================
# LAYER 4: Data Protection
# ============================================================================

class DataEncryption:
    """Encrypt/decrypt sensitive configuration data"""
    
    def __init__(self, key: str = None):
        if key:
            self.key = key.encode()
        else:
            self.key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key()).encode()
        
        self.cipher_suite = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

class CredentialValidator:
    """Validate and manage credentials"""
    
    def __init__(self):
        self.credentials = {}
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from environment"""
        self.credentials = {
            'discord_webhook_url': os.getenv('CPM_WEBHOOK_URL'),
            'discord_bot_token': os.getenv('DISCORD_BOT_TOKEN'),
            'webhook_secret': os.getenv('WEBHOOK_SECRET'),
            'encryption_key': os.getenv('ENCRYPTION_KEY')
        }
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """Validate all required credentials"""
        errors = []
        
        if not self.credentials.get('discord_webhook_url'):
            errors.append("CPM_WEBHOOK_URL not set")
        
        if not self.credentials.get('discord_bot_token'):
            errors.append("DISCORD_BOT_TOKEN not set")
        
        return len(errors) == 0, errors
    
    def get_credential(self, key: str) -> Optional[str]:
        """Get credential with masking for logging"""
        value = self.credentials.get(key)
        if value and 'webhook_url' in key:
            # Mask webhook URL for logging
            return value[:20] + '...' + value[-10:] if len(value) > 30 else '***'
        return value

# ============================================================================
# LAYER 5: Webhook & Discord Security
# ============================================================================

class WebhookRetryHandler:
    """Handle webhook retries with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def send_with_retry(self, send_coro, operation_id: str) -> bool:
        """Send webhook with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await send_coro()
                if result:
                    logger.info(f"Webhook send successful: {operation_id}")
                    return True
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Webhook send failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Webhook send failed after {self.max_retries} retries: {e}")
        
        return False

class DiscordMessageValidator:
    """Validate Discord messages before sending"""
    
    def __init__(self):
        self.max_message_length = 2000
        self.max_embed_title = 256
        self.max_embed_description = 4096
        self.max_embed_fields = 25
    
    def validate_message(self, content: str, embeds: List[Dict] = None) -> Tuple[bool, str]:
        """Validate Discord message format"""
        try:
            # Check message length
            if len(content) > self.max_message_length:
                return False, f"Message too long: {len(content)} > {self.max_message_length}"
            
            # Validate embeds
            if embeds:
                if len(embeds) > 10:
                    return False, "Too many embeds (max 10)"
                
                for i, embed in enumerate(embeds):
                    # Validate embed structure
                    if 'title' in embed and len(embed['title']) > self.max_embed_title:
                        return False, f"Embed {i} title too long"
                    
                    if 'description' in embed and len(embed['description']) > self.max_embed_description:
                        return False, f"Embed {i} description too long"
                    
                    if 'fields' in embed:
                        if len(embed['fields']) > self.max_embed_fields:
                            return False, f"Embed {i} has too many fields"
                        
                        for field in embed['fields']:
                            if 'name' not in field or 'value' not in field:
                                return False, f"Embed {i} field missing name or value"
            
            return True, "Message valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

# ============================================================================
# LAYER 6: Monitoring
# ============================================================================

class HealthMonitor:
    """Comprehensive health monitoring"""
    
    def __init__(self):
        self.stats = {
            'start_time': time.time(),
            'alerts_sent': 0,
            'fetches_completed': 0,
            'errors': 0,
            'last_alert': None,
            'last_error': None
        }
        self.error_history = deque(maxlen=100)
    
    def record_alert(self):
        """Record successful alert"""
        self.stats['alerts_sent'] += 1
        self.stats['last_alert'] = datetime.utcnow()
    
    def record_fetch(self):
        """Record successful fetch"""
        self.stats['fetches_completed'] += 1
    
    def record_error(self, error: str = None):
        """Record error"""
        self.stats['errors'] += 1
        self.stats['last_error'] = datetime.utcnow()
        if error:
            self.error_history.append({
                'timestamp': datetime.utcnow(),
                'error': error
            })
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        uptime = time.time() - self.stats['start_time']
        
        # Calculate rates
        alert_rate = self.stats['alerts_sent'] / (uptime / 3600) if uptime > 0 else 0
        error_rate = self.stats['errors'] / max(self.stats['fetches_completed'], 1)
        
        # Determine health status
        if error_rate > 0.1:  # >10% error rate
            status = "CRITICAL"
        elif error_rate > 0.05:  # >5% error rate
            status = "WARNING"
        elif uptime < 60:  # Just started
            status = "STARTING"
        else:
            status = "HEALTHY"
        
        return {
            'status': status,
            'uptime_seconds': uptime,
            'alerts_sent': self.stats['alerts_sent'],
            'fetches_completed': self.stats['fetches_completed'],
            'errors': self.stats['errors'],
            'alert_rate_per_hour': alert_rate,
            'error_rate': error_rate,
            'last_alert': self.stats['last_alert'].isoformat() if self.stats['last_alert'] else None,
            'last_error': self.stats['last_error'].isoformat() if self.stats['last_error'] else None
        }

# ============================================================================
# LAYER 7: Market Config Validation
# ============================================================================

class MarketConfigValidator:
    """Validate market configuration file"""
    
    def __init__(self):
        self.required_fields = ['id', 'name', 'upstream', 'severity', 'cooldown_seconds', 'rules']
        self.valid_upstreams = ['polymarket', 'limitless', 'coinbase', 'price']
        self.valid_severities = ['low', 'medium', 'high', 'critical']
        self.valid_rule_types = ['spread', 'movement', 'liquidity', 'volume']
    
    def validate_market_config(self, config_path: str) -> Tuple[bool, List[str]]:
        """Validate market configuration file"""
        errors = []
        
        try:
            # Check file exists
            if not os.path.exists(config_path):
                errors.append(f"Config file not found: {config_path}")
                return False, errors
            
            # Load and parse JSON
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate top-level structure
            if 'markets' not in config:
                errors.append("Missing 'markets' array in config")
                return False, errors
            
            markets = config['markets']
            if not isinstance(markets, list):
                errors.append("'markets' must be an array")
                return False, errors
            
            if len(markets) == 0:
                errors.append("No markets defined in config")
                return False, errors
            
            # Validate each market
            for i, market in enumerate(markets):
                market_errors = self._validate_market(market, f"markets[{i}]")
                errors.extend(market_errors)
            
            return len(errors) == 0, errors
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in config file: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Error reading config file: {e}")
            return False, errors
    
    def _validate_market(self, market: Dict[str, Any], path: str) -> List[str]:
        """Validate individual market configuration"""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in market:
                errors.append(f"{path}: Missing required field '{field}'")
        
        # Validate upstream
        if 'upstream' in market and market['upstream'] not in self.valid_upstreams:
            errors.append(f"{path}: Invalid upstream '{market['upstream']}'")
        
        # Validate severity
        if 'severity' in market and market['severity'] not in self.valid_severities:
            errors.append(f"{path}: Invalid severity '{market['severity']}'")
        
        # Validate cooldown
        if 'cooldown_seconds' in market:
            try:
                cooldown = int(market['cooldown_seconds'])
                if cooldown < 0 or cooldown > 86400:  # Max 24 hours
                    errors.append(f"{path}: Invalid cooldown_seconds {cooldown}")
            except ValueError:
                errors.append(f"{path}: cooldown_seconds must be an integer")
        
        # Validate rules
        if 'rules' in market:
            if not isinstance(market['rules'], list):
                errors.append(f"{path}: 'rules' must be an array")
            else:
                for j, rule in enumerate(market['rules']):
                    rule_errors = self._validate_rule(rule, f"{path}.rules[{j}]")
                    errors.extend(rule_errors)
        
        return errors
    
    def _validate_rule(self, rule: Dict[str, Any], path: str) -> List[str]:
        """Validate individual rule"""
        errors = []
        
        # Check required fields
        if 'name' not in rule:
            errors.append(f"{path}: Missing rule 'name'")
        
        if 'threshold_type' not in rule:
            errors.append(f"{path}: Missing rule 'threshold_type'")
        elif rule['threshold_type'] not in self.valid_rule_types:
            errors.append(f"{path}: Invalid threshold_type '{rule['threshold_type']}'")
        
        if 'threshold_value' not in rule:
            errors.append(f"{path}: Missing rule 'threshold_value'")
        else:
            try:
                value = float(rule['threshold_value'])
                if value < 0:
                    errors.append(f"{path}: threshold_value must be positive")
            except ValueError:
                errors.append(f"{path}: threshold_value must be a number")
        
        return errors

# ============================================================================
# LAYER 8: Price & Data Sanity
# ============================================================================

class PriceSanityValidator:
    """Validate price data for sanity and consistency"""
    
    def __init__(self):
        self.price_history = defaultdict(lambda: deque(maxlen=100))  # Keep last 100 prices
        self.max_price_change = 0.5  # 50% max change
    
    def validate_price_movement(self, market_id: str, yes_price: float, no_price: float) -> Tuple[bool, str]:
        """Validate price movement is realistic"""
        try:
            # Get price history
            history = self.price_history[market_id]
            
            if len(history) < 2:
                # Not enough history, just record and accept
                self.price_history[market_id].append((yes_price, no_price, time.time()))
                return True, "Insufficient history"
            
            # Get last price
            last_yes, last_no, last_time = history[-1]
            
            # Calculate price changes
            yes_change = abs(yes_price - last_yes) / last_yes if last_yes > 0 else 0
            no_change = abs(no_price - last_no) / last_no if last_no > 0 else 0
            
            # Check for suspicious changes
            if yes_change > self.max_price_change:
                return False, f"Suspicious YES price jump: {yes_change:.1%} change"
            
            if no_change > self.max_price_change:
                return False, f"Suspicious NO price jump: {no_change:.1%} change"
            
            # Record current price
            self.price_history[market_id].append((yes_price, no_price, time.time()))
            
            return True, "Price movement valid"
            
        except Exception as e:
            return False, f"Price validation error: {str(e)}"
    
    def validate_price_consistency(self, market_id: str, yes_price: float, no_price: float) -> Tuple[bool, str]:
        """Validate price consistency (YES + NO ≈ 1.0)"""
        try:
            total = yes_price + no_price
            
            # Allow small deviation due to market inefficiencies
            if abs(total - 1.0) > 0.05:  # 5% tolerance
                return False, f"Price inconsistency: YES+NO={total:.3f} (should be ≈1.0)"
            
            return True, "Prices consistent"
            
        except Exception as e:
            return False, f"Price consistency check error: {str(e)}"

class PolymarketDataValidator:
    """Validate Polymarket-specific data"""
    
    def __init__(self):
        self.condition_id_pattern = re.compile(r'^0x[a-fA-F0-9]{64}$')
    
    def validate_condition_id(self, condition_id: str) -> Tuple[bool, str]:
        """Validate Polymarket condition ID format"""
        if not condition_id:
            return False, "Empty condition ID"
        
        if not self.condition_id_pattern.match(condition_id):
            return False, f"Invalid condition ID format: {condition_id}"
        
        return True, "Condition ID valid"
    
    def validate_order_book(self, order_book: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Polymarket order book structure"""
        try:
            # Check required fields
            if 'yes' not in order_book or 'no' not in order_book:
                return False, "Missing yes/no order book data"
            
            # Validate orders
            for side in ['yes', 'no']:
                orders = order_book[side]
                if not isinstance(orders, list):
                    return False, f"Invalid {side} orders format"
                
                for order in orders:
                    if 'price' not in order or 'size' not in order:
                        return False, f"Missing price/size in {side} order"
                    
                    try:
                        price = float(order['price'])
                        size = float(order['size'])
                        
                        if not (0 <= price <= 1):
                            return False, f"Invalid {side} order price: {price}"
                        
                        if size <= 0:
                            return False, f"Invalid {side} order size: {size}"
                        
                    except ValueError:
                        return False, f"Invalid {side} order price/size format"
            
            return True, "Order book valid"
            
        except Exception as e:
            return False, f"Order book validation error: {str(e)}"

class CoinbaseDataValidator:
    """Validate Coinbase price feed data"""
    
    def __init__(self):
        self.valid_symbols = {'BTC', 'ETH', 'USDT', 'USDC'}
    
    def validate_price_symbol(self, symbol: str) -> Tuple[bool, str]:
        """Validate Coinbase price symbol"""
        if not symbol:
            return False, "Empty symbol"
        
        # Remove -USD suffix if present
        clean_symbol = symbol.replace('-USD', '')
        
        if clean_symbol not in self.valid_symbols:
            return False, f"Invalid symbol: {symbol}"
        
        return True, "Symbol valid"
    
    def validate_price_feed(self, symbol: str, price: float) -> Tuple[bool, str]:
        """Validate Coinbase price feed"""
        try:
            # Validate symbol
            symbol_valid, symbol_msg = self.validate_price_symbol(symbol)
            if not symbol_valid:
                return False, symbol_msg
            
            # Validate price
            if not isinstance(price, (int, float)):
                return False, "Price must be a number"
            
            if price <= 0:
                return False, f"Invalid price: {price}"
            
            # Reasonable price ranges
            price_ranges = {
                'BTC': (1000, 1000000),
                'ETH': (50, 10000),
                'USDT': (0.9, 1.1),
                'USDC': (0.9, 1.1)
            }
            
            clean_symbol = symbol.replace('-USD', '')
            min_price, max_price = price_ranges.get(clean_symbol, (0, float('inf')))
            
            if not (min_price <= price <= max_price):
                return False, f"Price {price} outside reasonable range for {symbol}"
            
            return True, "Price feed valid"
            
        except Exception as e:
            return False, f"Price feed validation error: {str(e)}"

# ============================================================================
# LAYER 9: Environment Validation
# ============================================================================

class EnvironmentValidator:
    """Validate environment variables and configuration"""
    
    @staticmethod
    def validate_all() -> Tuple[bool, List[str]]:
        """Validate all environment variables"""
        errors = []
        
        # Required environment variables
        required_vars = {
            'CPM_WEBHOOK_URL': 'Discord webhook URL',
            'DISCORD_BOT_TOKEN': 'Discord bot token',
            'CPM_MODE': 'Operating mode',
            'CPM_UPSTREAM': 'Upstream source',
            'CPM_BASE_URL': 'Base URL'
        }
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                errors.append(f"{description} not set ({var})")
            else:
                # Validate specific formats
                if var == 'CPM_WEBHOOK_URL':
                    if not value.startswith('https://discord.com/api/webhooks/'):
                        errors.append(f"Invalid Discord webhook URL format")
                
                elif var == 'CPM_MODE':
                    valid_modes = ['monitor', 'alert', 'trade']
                    if value not in valid_modes:
                        errors.append(f"Invalid CPM_MODE: {value} (must be one of {valid_modes})")
                
                elif var == 'CPM_UPSTREAM':
                    valid_upstreams = ['polymarket', 'limitless', 'coinbase', 'multi']
                    if value not in valid_upstreams:
                        errors.append(f"Invalid CPM_UPSTREAM: {value} (must be one of {valid_upstreams})")
                
                elif var == 'CPM_BASE_URL':
                    if not (value.startswith('http://') or value.startswith('https://')):
                        errors.append(f"Invalid CPM_BASE_URL format: {value}")
        
        # Optional but recommended variables
        optional_vars = {
            'WEBHOOK_SECRET': 'Webhook signature secret',
            'ENCRYPTION_KEY': 'Data encryption key'
        }
        
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if not value:
                logger.warning(f"Optional {description} not set ({var})")
        
        return len(errors) == 0, errors

# ============================================================================
# MAIN INITIALIZATION
# ============================================================================

def initialize_protection_layers(config_path: str = None) -> Dict[str, Any]:
    """Initialize all protection layers"""
    logger.info("Initializing Active Protection Layers...")
    
    protection_layers = {}
    
    # Layer 1: API & Webhook Security
    protection_layers['webhook_validator'] = WebhookSignatureValidator()
    protection_layers['rate_limiter'] = RateLimiter()
    
    # Layer 2: Fetcher Security
    protection_layers['fetcher_health'] = FetcherHealthCheck()
    protection_layers['fetcher_timeout'] = FetcherTimeout()
    
    # Layer 3: Alert Evaluation
    protection_layers['alert_validator'] = AlertValidator()
    protection_layers['alert_duplicate_detector'] = AlertDuplicateDetector()
    protection_layers['alert_rate_limiter'] = AlertRateLimiter()
    protection_layers['idempotent_tracker'] = IdempotentAlertTracker()
    
    # Layer 4: Data Protection
    protection_layers['data_encryption'] = DataEncryption()
    protection_layers['credential_validator'] = CredentialValidator()
    
    # Layer 5: Webhook & Discord
    protection_layers['webhook_retry_handler'] = WebhookRetryHandler()
    protection_layers['discord_validator'] = DiscordMessageValidator()
    
    # Layer 6: Monitoring
    protection_layers['health_monitor'] = HealthMonitor()
    
    # Layer 7: Market Config Validation
    protection_layers['market_config_validator'] = MarketConfigValidator()
    
    # Layer 8: Price & Data Sanity
    protection_layers['price_sanity_validator'] = PriceSanityValidator()
    protection_layers['polymarket_validator'] = PolymarketDataValidator()
    protection_layers['coinbase_validator'] = CoinbaseDataValidator()
    
    # Layer 9: Environment Validation
    protection_layers['environment_validator'] = EnvironmentValidator()
    
    # Validate environment
    env_valid, env_errors = EnvironmentValidator.validate_all()
    if not env_valid:
        raise ValueError(f"Environment validation failed: {env_errors}")
    
    logger.info("Environment validation passed")
    
    # Validate credentials
    cred_valid, cred_errors = protection_layers['credential_validator'].validate_all()
    if not cred_valid:
        raise ValueError(f"Credential validation failed: {cred_errors}")
    
    logger.info(f"All {len(protection_layers['credential_validator'].credentials)} credentials loaded")
    
    # Validate market config if provided
    if config_path:
        config_valid, config_errors = protection_layers['market_config_validator'].validate_market_config(config_path)
        if not config_valid:
            raise ValueError(f"Market config validation failed: {config_errors}")
        
        logger.info("Market config validated")
    
    logger.info(f"Initialized {len(protection_layers)} protection layers")
    return protection_layers

# ============================================================================
# INPUT VALIDATORS
# ============================================================================

class InputValidator:
    """Generic input validation utilities"""
    
    @staticmethod
    def validate_market_event(event: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate market event structure"""
        try:
            required_fields = ['id', 'yes_price', 'no_price', 'timestamp']
            
            for field in required_fields:
                if field not in event:
                    return False, f"Missing required field: {field}"
            
            # Validate prices
            yes_price = float(event['yes_price'])
            no_price = float(event['no_price'])
            
            if not (0 <= yes_price <= 1) or not (0 <= no_price <= 1):
                return False, "Prices must be between 0 and 1"
            
            return True, "Event valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
