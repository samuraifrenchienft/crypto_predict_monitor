"""
Security Framework Integration
Main integration point for all Active Protection Layers
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .security_framework import (
    SecurityFramework, 
    get_security_framework, 
    initialize_security, 
    shutdown_security,
    SecurityEvent,
    require_rate_limit,
    require_wallet_signature,
    validate_trade_operation
)
from .api_security import APISecurityMiddleware, APIKeyManager, api_key_manager
from .wallet_security import wallet_security, WalletTransaction
from .operations_security import operations_security
from .data_security import data_security
from .webhook_security import webhook_security
from .security_monitoring import threat_detector, ThreatLevel, AlertAction

logger = logging.getLogger(__name__)

class SecurityIntegration:
    """Main security integration coordinator"""
    
    def __init__(self):
        self.framework = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize all security components"""
        try:
            # Initialize core framework
            await initialize_security()
            self.framework = get_security_framework()
            
            # Initialize data security
            data_security._load_credentials()
            
            # Load threat patterns from environment
            await self._load_custom_threat_patterns()
            
            # Start background monitoring tasks
            asyncio.create_task(self._monitoring_loop())
            asyncio.create_task(self._cleanup_loop())
            
            self.initialized = True
            logger.info("Security integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Security integration initialization failed: {e}")
            raise
    
    async def _load_custom_threat_patterns(self):
        """Load custom threat patterns from environment"""
        try:
            # Load custom patterns from environment variable
            custom_patterns = os.getenv('CUSTOM_THREAT_PATTERNS', '')
            if custom_patterns:
                import json
                patterns = json.loads(custom_patterns)
                
                for pattern_data in patterns:
                    # Convert to ThreatPattern object
                    pattern = ThreatPattern(**pattern_data)
                    threat_detector.add_threat_pattern(pattern)
                
                logger.info(f"Loaded {len(patterns)} custom threat patterns")
                
        except Exception as e:
            logger.error(f"Error loading custom threat patterns: {e}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Process security events
                await self._process_security_events()
                
                # Check for system health
                await self._check_system_health()
                
                # Update metrics
                await self._update_metrics()
                
                # Sleep for monitoring interval
                await asyncio.sleep(30)  # 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                # Cleanup old data
                await threat_detector.cleanup_old_data()
                await webhook_security.cleanup_old_events()
                
                # Sleep for cleanup interval
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait longer on error
    
    async def _process_security_events(self):
        """Process queued security events"""
        try:
            # Get events from Redis queue
            events = await self.framework.redis.lrange('security_events_queue', 0, 100)
            
            for event_json in events:
                try:
                    event_data = json.loads(event_json)
                    event = SecurityEvent(
                        event_type=event_data['event_type'],
                        severity=event_data['severity'],
                        user_id=event_data['user_id'],
                        ip_address=event_data['ip_address'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        details=event_data['details']
                    )
                    
                    # Analyze for threats
                    alerts = await threat_detector.analyze_security_event(event)
                    
                    # Remove from queue
                    await self.framework.redis.lrem('security_events_queue', 1, event_json)
                    
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.error(f"Invalid security event data: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing security events: {e}")
    
    async def _check_system_health(self):
        """Check system health and security status"""
        try:
            health_status = {
                'timestamp': datetime.utcnow().isoformat(),
                'security_framework': self.framework is not None,
                'blocked_ips': len(threat_detector.blocked_ips),
                'suspended_users': len(threat_detector.suspended_users),
                'require_mfa_users': len(threat_detector.require_mfa_users),
                'recent_alerts': len(threat_detector.alert_notifications),
                'metrics': threat_detector.get_security_metrics()
            }
            
            # Store health status
            await self.framework.redis.setex(
                'security_health',
                300,  # 5 minutes
                json.dumps(health_status)
            )
            
            # Check for emergency conditions
            if health_status['recent_alerts'] > 100:  # Too many alerts
                await self._handle_emergency_condition("High alert volume")
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
    
    async def _update_metrics(self):
        """Update security metrics"""
        try:
            # Get current metrics
            metrics = threat_detector.get_security_metrics()
            
            # Store in Redis for dashboard
            await self.framework.redis.setex(
                'security_metrics',
                300,  # 5 minutes
                json.dumps(metrics)
            )
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    async def _handle_emergency_condition(self, condition: str):
        """Handle emergency security conditions"""
        try:
            # Create emergency alert
            await threat_detector._send_discord_alert(
                type('Alert', (), {
                    'alert_id': f"emergency_{int(datetime.utcnow().timestamp())}",
                    'threat_level': ThreatLevel.CRITICAL,
                    'message': f"Emergency condition: {condition}",
                    'details': {'condition': condition},
                    'timestamp': datetime.utcnow(),
                    'user_id': None,
                    'ip_address': None,
                    'action_taken': AlertAction.NOTIFY_ADMIN
                })()
            )
            
            logger.critical(f"Emergency condition detected: {condition}")
            
        except Exception as e:
            logger.error(f"Error handling emergency condition: {e}")
    
    async def shutdown(self):
        """Shutdown security integration"""
        try:
            await shutdown_security()
            logger.info("Security integration shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global security integration instance
security_integration = SecurityIntegration()

# FastAPI lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Startup
    await security_integration.initialize()
    yield
    # Shutdown
    await security_integration.shutdown()

# Security middleware
class ComprehensiveSecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware combining all protection layers"""
    
    def __init__(self, app):
        super().__init__(app)
        self.bearer = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """Process request through all security layers"""
        start_time = asyncio.get_event_loop().time()
        client_ip = self._get_client_ip(request)
        user_id = None
        
        try:
            # 1. Check if IP is blocked
            if threat_detector.is_ip_blocked(client_ip):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="IP address blocked"
                )
            
            # 2. Authenticate request
            user_id, credentials = await self._authenticate_request(request)
            
            # 3. Check if user is suspended
            if user_id and threat_detector.is_user_suspended(user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account suspended"
                )
            
            # 4. Check MFA requirement
            if user_id and threat_detector.does_user_require_mfa(user_id):
                # Check if MFA is completed
                mfa_header = request.headers.get("x-mfa-verified")
                if not mfa_header or mfa_header != "true":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Multi-factor authentication required"
                    )
            
            # 5. Process request
            response = await call_next(request)
            
            # 6. Log successful request
            await self._log_request(request, response, start_time, user_id, client_ip, None)
            
            return response
            
        except HTTPException:
            # Log security event
            await self._log_request(request, None, start_time, user_id, client_ip, "HTTP Exception")
            raise
        except Exception as e:
            # Log unexpected error
            await self._log_request(request, None, start_time, user_id, client_ip, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal security error"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host
    
    async def _authenticate_request(self, request: Request) -> tuple[str, Optional[Any]]:
        """Authenticate request using multiple methods"""
        # Try API key authentication
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            api_key = authorization[7:]
            
            # Validate API key
            for key_id, stored_key in api_key_manager.api_keys.items():
                if stored_key.key_hash == hashlib.sha256(api_key.encode()).hexdigest():
                    return stored_key.user_id, stored_key
        
        # Try wallet authentication (for trading endpoints)
        if request.url.path.startswith("/api/trade"):
            wallet_address = request.headers.get("x-wallet-address")
            signature = request.headers.get("x-wallet-signature")
            nonce = request.headers.get("x-wallet-nonce")
            
            if all([wallet_address, signature, nonce]):
                # Verify wallet signature
                is_valid, error = await wallet_security.verify_signature(
                    wallet_address, 
                    request.body.decode() if request.body else "",
                    signature,
                    nonce
                )
                
                if is_valid:
                    return wallet_address, None
        
        return None, None
    
    async def _log_request(self, request: Request, response, start_time: float, 
                          user_id: str, client_ip: str, error: Optional[str]):
        """Log request for security monitoring"""
        try:
            duration = asyncio.get_event_loop().time() - start_time
            status_code = response.status_code if response else 500
            
            # Determine if this is a security event
            security_events = [
                'blocked', 'suspended', 'mfa_required', 'authentication_failed',
                'rate_limit_exceeded', 'invalid_signature', 'security_error'
            ]
            
            is_security_event = any(event in str(error).lower() for event in security_events) if error else False
            
            if is_security_event or status_code >= 400:
                await data_security.log_audit_event(
                    user_id=user_id or 'anonymous',
                    action='api_request',
                    resource=request.url.path,
                    outcome='FAILURE' if error or status_code >= 400 else 'SUCCESS',
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent", ""),
                    details={
                        'method': request.method,
                        'path': request.url.path,
                        'status_code': status_code,
                        'duration': duration,
                        'error': error
                    },
                    risk_level='HIGH' if status_code >= 500 else 'MEDIUM'
                )
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")

# Security decorators for endpoints
def secure_endpoint(rate_limit_per_minute: int = 100, require_wallet: bool = False):
    """Decorator for securing API endpoints"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Rate limiting
            user_id = kwargs.get('user_id', 'anonymous')
            is_allowed, limits = await security_integration.framework.rate_limiter.is_allowed(
                user_id,
                type('Config', (), {'requests_per_minute': rate_limit_per_minute})()
            )
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            # Wallet verification if required
            if require_wallet:
                wallet_address = kwargs.get('wallet_address')
                signature = kwargs.get('signature')
                nonce = kwargs.get('nonce')
                
                if not all([wallet_address, signature, nonce]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Wallet authentication required"
                    )
                
                is_valid, error = await wallet_security.verify_signature(
                    wallet_address, str(kwargs), signature, nonce
                )
                
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid wallet signature"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Utility functions
async def create_security_app() -> FastAPI:
    """Create FastAPI app with comprehensive security"""
    app = FastAPI(
        title="Crypto Predict Monitor API",
        description="Secure prediction market monitoring API",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Add security middleware
    app.add_middleware(ComprehensiveSecurityMiddleware)
    
    # Add API security middleware
    app.add_middleware(APISecurityMiddleware, api_keys=api_key_manager.api_keys)
    
    # Add security endpoints
    @app.get("/security/health")
    async def security_health():
        """Get security system health"""
        health_data = await security_integration.framework.redis.get('security_health')
        if health_data:
            return json.loads(health_data)
        return {"status": "initializing"}
    
    @app.get("/security/metrics")
    async def security_metrics():
        """Get security metrics"""
        metrics_data = await security_integration.framework.redis.get('security_metrics')
        if metrics_data:
            return json.loads(metrics_data)
        return threat_detector.get_security_metrics()
    
    @app.get("/security/alerts")
    async def security_alerts(limit: int = 100):
        """Get recent security alerts"""
        return threat_detector.get_recent_alerts(limit)
    
    @app.post("/security/block-ip")
    async def block_ip(ip_address: str, reason: str):
        """Manually block an IP address"""
        alert = type('Alert', (), {
            'alert_id': f"manual_block_{int(datetime.utcnow().timestamp())}",
            'threat_level': ThreatLevel.MEDIUM,
            'message': f"Manual IP block: {reason}",
            'details': {'reason': reason},
            'timestamp': datetime.utcnow(),
            'user_id': None,
            'ip_address': ip_address,
            'action_taken': AlertAction.BLOCK_IP
        })()
        
        await threat_detector._execute_alert_action(alert)
        return {"message": f"IP {ip_address} blocked"}
    
    @app.post("/security/suspend-user")
    async def suspend_user(user_id: str, reason: str):
        """Manually suspend a user"""
        alert = type('Alert', (), {
            'alert_id': f"manual_suspend_{int(datetime.utcnow().timestamp())}",
            'threat_level': ThreatLevel.HIGH,
            'message': f"Manual user suspension: {reason}",
            'details': {'reason': reason},
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'ip_address': None,
            'action_taken': AlertAction.SUSPEND_USER
        })()
        
        await threat_detector._execute_alert_action(alert)
        return {"message": f"User {user_id} suspended"}
    
    return app

# Example secure endpoint usage
"""
@app.post("/api/trade")
@secure_endpoint(rate_limit_per_minute=10, require_wallet=True)
async def execute_trade(
    trade_data: TradeRequest,
    user_id: str = Depends(get_current_user),
    wallet_address: str = Header(...),
    signature: str = Header(...),
    nonce: str = Header(...)
):
    # Validate trade
    validation_result = await operations_security.validate_trade(trade_data.dict())
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Trade validation failed: {validation_result.errors}"
        )
    
    # Check trade limits
    limit_check, error = await wallet_security.check_trade_limits(wallet_address, trade_data.amount)
    if not limit_check:
        raise HTTPException(status_code=400, detail=error)
    
    # Execute trade
    # ... trading logic here
    
    return {"status": "success", "trade_id": "12345"}
"""

# Initialize security on import
try:
    asyncio.create_task(security_integration.initialize())
except RuntimeError:
    # Not in async context, will be initialized by FastAPI lifespan
    pass
