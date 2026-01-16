"""
Webhook Security Implementation
HMAC signature verification, timeout handling, deduplication, and secure webhook processing
"""

import os
import json
import time
import hmac
import hashlib
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import aiohttp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hmac import HMAC
import base64

from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

@dataclass
class WebhookEvent:
    """Webhook event data"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    payload: Dict[str, Any]
    signature: str
    nonce: str
    processed: bool = False
    processing_attempts: int = 0
    error_message: Optional[str] = None

@dataclass
class WebhookConfig:
    """Webhook configuration"""
    secret_key: str
    allowed_sources: List[str]
    timeout_seconds: int = 30
    max_payload_size: int = 10 * 1024 * 1024  # 10MB
    signature_tolerance: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: int = 5  # seconds

@dataclass
class WebhookStats:
    """Webhook processing statistics"""
    total_received: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_duplicates: int = 0
    total_invalid_signature: int = 0
    total_timeouts: int = 0
    average_processing_time: float = 0.0
    last_event_time: Optional[datetime] = None

class WebhookSecurity:
    """Comprehensive webhook security implementation"""
    
    def __init__(self):
        self.security = get_security_framework()
        
        # Initialize webhook configurations
        self.configs = {
            'default': WebhookConfig(
                secret_key=os.getenv('WEBHOOK_SECRET', 'default_webhook_secret'),
                allowed_sources=os.getenv('ALLOWED_WEBHOOK_SOURCES', '').split(','),
                timeout_seconds=30,
                max_payload_size=10 * 1024 * 1024,
                signature_tolerance=300,
                max_retries=3,
                retry_delay=5
            ),
            'alchemy': WebhookConfig(
                secret_key=os.getenv('ALCHEMY_WEBHOOK_SECRET', ''),
                allowed_sources=['alchemy.com'],
                timeout_seconds=30,
                max_payload_size=5 * 1024 * 1024,
                signature_tolerance=300,
                max_retries=3,
                retry_delay=5
            ),
            'polymarket': WebhookConfig(
                secret_key=os.getenv('POLYMARKET_WEBHOOK_SECRET', ''),
                allowed_sources=['polymarket.com'],
                timeout_seconds=30,
                max_payload_size=5 * 1024 * 1024,
                signature_tolerance=300,
                max_retries=3,
                retry_delay=5
            )
        }
        
        # Deduplication tracking
        self.processed_events = deque(maxlen=10000)  # Keep last 10000 event IDs
        self.event_fingerprints = {}  # For content deduplication
        
        # Statistics tracking
        self.stats = defaultdict(WebhookStats)
        
        # Event processors
        self.event_processors = {}
        
        # Rate limiting per source
        self.source_rate_limits = {}
        
        logger.info("Webhook security initialized")
    
    def register_event_processor(self, event_type: str, processor: Callable):
        """Register event processor for specific event types"""
        self.event_processors[event_type] = processor
        logger.info(f"Registered processor for event type: {event_type}")
    
    async def process_webhook(self, source: str, headers: Dict[str, str], 
                            body: bytes, ip_address: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Process incoming webhook with comprehensive security checks"""
        start_time = time.time()
        event_id = None
        
        try:
            # Get configuration for this source
            config = self.configs.get(source, self.configs['default'])
            
            # Update statistics
            stats = self.stats[source]
            stats.total_received += 1
            stats.last_event_time = datetime.utcnow()
            
            # 1. Basic validation
            validation_result = await self._validate_basic_request(source, headers, body, config, ip_address)
            if not validation_result[0]:
                stats.total_failed += 1
                return False, validation_result[1]
            
            # 2. Parse and validate payload
            payload_result = await self._parse_and_validate_payload(body, headers, config)
            if not payload_result[0]:
                stats.total_failed += 1
                return False, payload_result[1]
            
            payload = payload_result[1]
            event_id = payload.get('event_id', self._generate_event_id())
            
            # 3. Signature verification
            signature_result = await self._verify_signature(source, payload, headers, config)
            if not signature_result[0]:
                stats.total_invalid_signature += 1
                await self._log_security_event(
                    'invalid_webhook_signature',
                    'HIGH',
                    source,
                    ip_address or 'unknown',
                    {
                        'event_id': event_id,
                        'event_type': payload.get('event_type'),
                        'error': signature_result[1]
                    }
                )
                stats.total_failed += 1
                return False, {'error': 'Invalid signature', 'details': signature_result[1]}
            
            # 4. Deduplication check
            deduplication_result = await self._check_deduplication(source, payload, event_id)
            if not deduplication_result[0]:
                stats.total_duplicates += 1
                return False, {'error': 'Duplicate event', 'details': deduplication_result[1]}
            
            # 5. Rate limiting check
            rate_limit_result = await self._check_rate_limit(source, ip_address)
            if not rate_limit_result[0]:
                await self._log_security_event(
                    'webhook_rate_limit_exceeded',
                    'MEDIUM',
                    source,
                    ip_address or 'unknown',
                    {'event_id': event_id}
                )
                stats.total_failed += 1
                return False, {'error': 'Rate limit exceeded', 'details': rate_limit_result[1]}
            
            # 6. Process event
            processing_result = await self._process_event(source, payload, config)
            
            # Update statistics
            processing_time = time.time() - start_time
            stats.average_processing_time = (
                (stats.average_processing_time * (stats.total_processed) + processing_time) / 
                (stats.total_processed + 1)
            )
            
            if processing_result[0]:
                stats.total_processed += 1
                await self._log_security_event(
                    'webhook_processed',
                    'LOW',
                    source,
                    ip_address or 'unknown',
                    {
                        'event_id': event_id,
                        'event_type': payload.get('event_type'),
                        'processing_time': processing_time
                    }
                )
            else:
                stats.total_failed += 1
                await self._log_security_event(
                    'webhook_processing_failed',
                    'MEDIUM',
                    source,
                    ip_address or 'unknown',
                    {
                        'event_id': event_id,
                        'event_type': payload.get('event_type'),
                        'error': processing_result[1],
                        'processing_time': processing_time
                    }
                )
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            stats.total_failed += 1
            
            await self._log_security_event(
                'webhook_processing_error',
                'HIGH',
                source,
                ip_address or 'unknown',
                {
                    'event_id': event_id,
                    'error': str(e),
                    'processing_time': time.time() - start_time
                }
            )
            
            return False, {'error': 'Processing error', 'details': str(e)}
    
    async def _validate_basic_request(self, source: str, headers: Dict[str, str], 
                                     body: bytes, config: WebhookConfig, ip_address: str) -> Tuple[bool, str]:
        """Validate basic webhook request"""
        try:
            # Check content length
            content_length = len(body)
            if content_length > config.max_payload_size:
                return False, f"Payload too large: {content_length} bytes"
            
            # Check required headers
            required_headers = ['content-type', 'x-webhook-signature', 'x-webhook-timestamp']
            for header in required_headers:
                if header not in headers:
                    return False, f"Missing required header: {header}"
            
            # Check content type
            content_type = headers.get('content-type', '').lower()
            if not content_type.startswith('application/json'):
                return False, f"Invalid content type: {content_type}"
            
            # Check timestamp
            timestamp_str = headers.get('x-webhook-timestamp')
            try:
                timestamp = int(timestamp_str)
                current_time = int(time.time())
                
                if abs(current_time - timestamp) > config.signature_tolerance:
                    return False, f"Timestamp too old: {timestamp}"
                    
            except ValueError:
                return False, "Invalid timestamp format"
            
            # Check source whitelist
            if config.allowed_sources and source not in config.allowed_sources:
                return False, f"Source not allowed: {source}"
            
            return True, "Basic validation passed"
            
        except Exception as e:
            logger.error(f"Basic validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def _parse_and_validate_payload(self, body: bytes, headers: Dict[str, str], 
                                        config: WebhookConfig) -> Tuple[bool, Dict[str, Any]]:
        """Parse and validate webhook payload"""
        try:
            # Parse JSON
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)}"
            
            # Validate required fields
            required_fields = ['event_type', 'timestamp']
            for field in required_fields:
                if field not in payload:
                    return False, f"Missing required field: {field}"
            
            # Validate event type
            event_type = payload['event_type']
            allowed_types = ['trade', 'market_update', 'price_change', 'alert', 'transaction']
            if event_type not in allowed_types:
                return False, f"Invalid event type: {event_type}"
            
            # Validate payload timestamp
            try:
                payload_timestamp = int(payload['timestamp'])
                current_time = int(time.time())
                
                if abs(current_time - payload_timestamp) > config.signature_tolerance:
                    return False, f"Payload timestamp too old: {payload_timestamp}"
                    
            except (ValueError, KeyError):
                return False, "Invalid payload timestamp"
            
            # Add metadata
            payload['received_at'] = datetime.utcnow().isoformat()
            payload['content_length'] = len(body)
            
            return True, payload
            
        except Exception as e:
            logger.error(f"Payload validation error: {e}")
            return False, f"Payload validation error: {str(e)}"
    
    async def _verify_signature(self, source: str, payload: Dict[str, Any], 
                              headers: Dict[str, str], config: WebhookConfig) -> Tuple[bool, str]:
        """Verify webhook HMAC signature"""
        try:
            # Get signature from headers
            signature = headers.get('x-webhook-signature')
            timestamp = headers.get('x-webhook-timestamp')
            
            if not signature or not timestamp:
                return False, "Missing signature or timestamp"
            
            # Create message to verify
            message = f"{timestamp}.{json.dumps(payload, separators=(',', ':'), sort_keys=True)}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                config.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            if not hmac.compare_digest(signature, expected_signature):
                return False, "Signature mismatch"
            
            return True, "Signature verified"
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False, f"Signature verification error: {str(e)}"
    
    async def _check_deduplication(self, source: str, payload: Dict[str, Any], event_id: str) -> Tuple[bool, str]:
        """Check for duplicate events"""
        try:
            # Check event ID
            if event_id in self.processed_events:
                return False, f"Duplicate event ID: {event_id}"
            
            # Create content fingerprint
            content_fingerprint = self._create_content_fingerprint(source, payload)
            
            # Check content fingerprint
            if content_fingerprint in self.event_fingerprints:
                original_event_id = self.event_fingerprints[content_fingerprint]
                return False, f"Duplicate content (original: {original_event_id})"
            
            # Record event
            self.processed_events.append(event_id)
            self.event_fingerprints[content_fingerprint] = event_id
            
            # Cleanup old entries (keep last 10000)
            if len(self.event_fingerprints) > 10000:
                # Remove oldest entries
                old_event_ids = list(self.processed_events)[:1000]
                for old_id in old_event_ids:
                    self.processed_events.remove(old_id)
                
                # Rebuild fingerprint map
                self.event_fingerprints = {
                    fp: eid for fp, eid in self.event_fingerprints.items() 
                    if eid in self.processed_events
                }
            
            return True, "Deduplication check passed"
            
        except Exception as e:
            logger.error(f"Deduplication check error: {e}")
            return False, f"Deduplication error: {str(e)}"
    
    def _create_content_fingerprint(self, source: str, payload: Dict[str, Any]) -> str:
        """Create content fingerprint for deduplication"""
        try:
            # Create normalized content for fingerprinting
            fingerprint_data = {
                'source': source,
                'event_type': payload.get('event_type'),
                'timestamp': payload.get('timestamp'),
                'data': payload.get('data', {})
            }
            
            # Create hash
            content_str = json.dumps(fingerprint_data, separators=(',', ':'), sort_keys=True)
            fingerprint = hashlib.sha256(content_str.encode()).hexdigest()
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Fingerprint creation error: {e}")
            return hashlib.sha256(str(time.time()).encode()).hexdigest()
    
    async def _check_rate_limit(self, source: str, ip_address: str) -> Tuple[bool, str]:
        """Check rate limiting for webhook source"""
        try:
            # Rate limit per source
            source_key = f"webhook_rate_limit:{source}"
            current_time = int(time.time())
            
            # Clean old entries (1 minute window)
            await self.security.redis.zremrangebyscore(source_key, 0, current_time - 60)
            
            # Count recent requests
            request_count = await self.security.redis.zcard(source_key)
            
            # Rate limits (adjust as needed)
            rate_limits = {
                'default': 100,  # 100 requests per minute
                'alchemy': 200,   # 200 requests per minute
                'polymarket': 150  # 150 requests per minute
            }
            
            max_requests = rate_limits.get(source, rate_limits['default'])
            
            if request_count >= max_requests:
                return False, f"Rate limit exceeded: {request_count}/{max_requests} per minute"
            
            # Record this request
            await self.security.redis.zadd(source_key, {str(current_time): current_time})
            await self.security.redis.expire(source_key, 60)
            
            return True, "Rate limit check passed"
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False, f"Rate limit error: {str(e)}"
    
    async def _process_event(self, source: str, payload: Dict[str, Any], config: WebhookConfig) -> Tuple[bool, str]:
        """Process webhook event with timeout"""
        event_type = payload.get('event_type')
        
        try:
            # Get processor for this event type
            processor = self.event_processors.get(event_type)
            
            if not processor:
                logger.warning(f"No processor for event type: {event_type}")
                return True, "No processor required"
            
            # Process with timeout
            try:
                result = await asyncio.wait_for(
                    processor(source, payload),
                    timeout=config.timeout_seconds
                )
                return True, result
                
            except asyncio.TimeoutError:
                logger.error(f"Event processing timeout: {event_type}")
                return False, f"Processing timeout after {config.timeout_seconds} seconds"
                
        except Exception as e:
            logger.error(f"Event processing error: {e}")
            return False, f"Processing error: {str(e)}"
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def _log_security_event(self, event_type: str, severity: str, source: str, 
                                 ip_address: str, details: Dict[str, Any]):
        """Log security event"""
        await self.security.monitor.log_security_event(SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=source,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            details=details
        ))
    
    def get_statistics(self, source: str = None) -> Dict[str, Any]:
        """Get webhook processing statistics"""
        try:
            if source:
                stats = self.stats.get(source, WebhookStats())
                return asdict(stats)
            
            # Return all stats
            return {
                source: asdict(stats) 
                for source, stats in self.stats.items()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    async def retry_failed_webhooks(self):
        """Retry failed webhook events"""
        try:
            # Get failed events from Redis
            failed_events = await self.security.redis.lrange('failed_webhooks', 0, -1)
            
            for event_json in failed_events:
                try:
                    event_data = json.loads(event_json)
                    
                    # Check if we should retry
                    if event_data.get('processing_attempts', 0) < 3:
                        # Retry the event
                        await self._retry_webhook_event(event_data)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Invalid failed webhook data: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error retrying failed webhooks: {e}")
    
    async def _retry_webhook_event(self, event_data: Dict[str, Any]):
        """Retry a single failed webhook event"""
        try:
            source = event_data.get('source')
            headers = event_data.get('headers', {})
            body = event_data.get('body', '').encode()
            
            # Increment attempt count
            event_data['processing_attempts'] += 1
            
            # Process the webhook
            result = await self.process_webhook(source, headers, body)
            
            if result[0]:
                # Success - remove from failed queue
                await self.security.redis.lrem('failed_webhooks', 1, json.dumps(event_data))
                logger.info(f"Successfully retried webhook from {source}")
            else:
                # Still failed - update in queue
                await self.security.redis.lrem('failed_webhooks', 1, json.dumps(event_data))
                await self.security.redis.rpush('failed_webhooks', json.dumps(event_data))
                logger.warning(f"Webhook retry failed for {source}: {result[1]}")
                
        except Exception as e:
            logger.error(f"Error retrying webhook: {e}")
    
    async def cleanup_old_events(self):
        """Clean up old event data"""
        try:
            # Clean up Redis keys
            keys_to_clean = [
                'webhook_rate_limit:*',
                'processed_events:*'
            ]
            
            for pattern in keys_to_clean:
                keys = await self.security.redis.keys(pattern)
                if keys:
                    await self.security.redis.delete(*keys)
            
            # Clean up in-memory data
            if len(self.processed_events) > 5000:
                # Keep only last 5000
                old_events = list(self.processed_events)[:-5000]
                for event_id in old_events:
                    self.processed_events.remove(event_id)
            
            logger.info("Webhook cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during webhook cleanup: {e}")

# Initialize webhook security
webhook_security = WebhookSecurity()

# Default event processors
async def default_trade_processor(source: str, payload: Dict[str, Any]) -> str:
    """Default processor for trade events"""
    try:
        # Log the trade event
        logger.info(f"Trade event from {source}: {payload.get('event_type')}")
        
        # Process trade data (integrate with your trading system)
        trade_data = payload.get('data', {})
        
        # Validate trade data
        if not trade_data:
            return "No trade data in payload"
        
        # Process the trade (this would integrate with your trading logic)
        # For now, just acknowledge
        return f"Trade processed: {trade_data.get('trade_id', 'unknown')}"
        
    except Exception as e:
        logger.error(f"Trade processing error: {e}")
        raise

async def default_market_processor(source: str, payload: Dict[str, Any]) -> str:
    """Default processor for market update events"""
    try:
        logger.info(f"Market update from {source}: {payload.get('event_type')}")
        
        # Process market data
        market_data = payload.get('data', {})
        
        if not market_data:
            return "No market data in payload"
        
        # Update market information (integrate with your market system)
        return f"Market updated: {market_data.get('market_id', 'unknown')}"
        
    except Exception as e:
        logger.error(f"Market processing error: {e}")
        raise

# Register default processors
webhook_security.register_event_processor('trade', default_trade_processor)
webhook_security.register_event_processor('market_update', default_market_processor)
