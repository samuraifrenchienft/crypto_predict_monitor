"""
API Security Middleware
Implements rate limiting, input validation, and API key authentication
"""

import os
import json
import time
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import pydantic
from pydantic import BaseModel, validator
import re
import logging
from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

# API Key Models
class APIKey(BaseModel):
    key_id: str
    key_hash: str
    user_id: str
    permissions: List[str]
    rate_limit_multiplier: float = 1.0
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True

# Input Validation Models
class TradeRequest(BaseModel):
    market_id: str
    side: str  # 'YES' or 'NO'
    amount: float
    price: float
    nonce: str
    signature: str
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['YES', 'NO']:
            raise ValueError('Side must be YES or NO')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError('Amount must be between 0 and 10000')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0 or v > 1:
            raise ValueError('Price must be between 0 and 1')
        return v
    
    @validator('market_id')
    def validate_market_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid market ID format')
        return v

class WebhookPayload(BaseModel):
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    signature: str
    
    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = ['trade', 'market_update', 'price_change', 'alert']
        if v not in allowed_types:
            raise ValueError(f'Event type must be one of: {allowed_types}')
        return v

class APISecurityMiddleware(BaseHTTPMiddleware):
    """API Security Middleware for FastAPI"""
    
    def __init__(self, app, api_keys: Dict[str, APIKey] = None):
        super().__init__(app)
        self.security = get_security_framework()
        self.api_keys = api_keys or {}
        self.bearer = HTTPBearer(auto_error=False)
        
        # Input validation patterns
        self.safe_patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'ethereum_address': re.compile(r'^0x[a-fA-F0-9]{40}$'),
            'market_id': re.compile(r'^[a-zA-Z0-9_-]{1,50}$'),
            'user_id': re.compile(r'^[a-zA-Z0-9_-]{1,50}$'),
        }
        
        # Rate limiting by endpoint
        self.endpoint_limits = {
            '/api/trade': {'requests_per_minute': 10, 'requests_per_hour': 100},
            '/api/webhook': {'requests_per_minute': 50, 'requests_per_hour': 500},
            '/api/data': {'requests_per_minute': 200, 'requests_per_hour': 2000},
            '/default': {'requests_per_minute': 100, 'requests_per_hour': 1000},
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security layers"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_id = None
        
        try:
            # 1. Basic request validation
            await self._validate_basic_request(request)
            
            # 2. API Key Authentication
            user_id, api_key = await self._authenticate_request(request)
            
            # 3. Rate Limiting
            await self._check_rate_limit(request, user_id, api_key)
            
            # 4. Input Validation
            await self._validate_input(request)
            
            # 5. Process request
            response = await call_next(request)
            
            # 6. Log successful request
            await self._log_request(request, response, start_time, user_id, client_ip, None)
            
            return response
            
        except HTTPException as e:
            # Log security event
            await self._log_request(request, None, start_time, user_id, client_ip, e.detail)
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
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host
    
    async def _validate_basic_request(self, request: Request):
        """Basic request validation"""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Check user agent
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User agent too long"
            )
        
        # Check for suspicious headers
        suspicious_headers = ['x-forwarded-host', 'x-original-url']
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")
    
    async def _authenticate_request(self, request: Request) -> tuple[str, Optional[APIKey]]:
        """Authenticate request with API key"""
        # Skip authentication for health checks and public endpoints
        if request.url.path in ['/health', '/metrics', '/docs', '/openapi.json']:
            return 'anonymous', None
        
        # Get API key from header
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        try:
            scheme, credentials = authorization.split()
            if scheme.lower() != 'bearer':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        # Validate API key
        api_key = await self._validate_api_key(credentials)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Update last used timestamp
        api_key.last_used = datetime.utcnow()
        
        return api_key.user_id, api_key
    
    async def _validate_api_key(self, key: str) -> Optional[APIKey]:
        """Validate API key"""
        # Hash the provided key
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Check against stored keys
        for stored_key in self.api_keys.values():
            if (stored_key.key_hash == key_hash and 
                stored_key.is_active and
                stored_key.last_used and 
                (datetime.utcnow() - stored_key.last_used).days < 30):
                return stored_key
        
        return None
    
    async def _check_rate_limit(self, request: Request, user_id: str, api_key: Optional[APIKey]):
        """Check rate limits"""
        # Get endpoint-specific limits
        path = request.url.path
        limits = self.endpoint_limits.get(path, self.endpoint_limits['default'])
        
        # Apply API key multiplier if available
        if api_key:
            for key in limits:
                limits[key] = int(limits[key] * api_key.rate_limit_multiplier)
        
        # Check rate limit
        is_allowed, limit_info = await self.security.rate_limiter.is_allowed(user_id)
        
        if not is_allowed:
            await self.security.monitor.log_security_event(SecurityEvent(
                event_type='rate_limit_exceeded',
                severity='MEDIUM',
                user_id=user_id,
                ip_address=self._get_client_ip(request),
                timestamp=datetime.utcnow(),
                details={
                    'endpoint': path,
                    'limits': limit_info
                }
            ))
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )
    
    async def _validate_input(self, request: Request):
        """Validate input data"""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Get request body
                body = await request.body()
                
                # Parse JSON
                try:
                    data = json.loads(body.decode()) if body else {}
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON"
                    )
                
                # Validate based on endpoint
                await self._validate_endpoint_input(request.url.path, data)
                
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Input validation failed"
                )
    
    async def _validate_endpoint_input(self, path: str, data: Dict[str, Any]):
        """Validate input for specific endpoints"""
        if path == '/api/trade':
            try:
                TradeRequest(**data)
            except pydantic.ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Trade validation failed: {e.errors()}"
                )
        
        elif path == '/api/webhook':
            try:
                WebhookPayload(**data)
            except pydantic.ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Webhook validation failed: {e.errors()}"
                )
        
        # Generic validation for all endpoints
        await self._validate_generic_input(data)
    
    async def _validate_generic_input(self, data: Dict[str, Any]):
        """Generic input validation"""
        # Check for SQL injection patterns
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)',
            r'(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)',
            r'(--|\/\*|\*\/)',
        ]
        
        data_str = json.dumps(data)
        for pattern in sql_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Check for XSS patterns
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Validate specific fields
        for key, value in data.items():
            if key == 'email' and value:
                if not self.safe_patterns['email'].match(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid email format"
                    )
            
            elif key == 'address' and value:
                if not self.safe_patterns['ethereum_address'].match(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Ethereum address format"
                    )
            
            elif key == 'user_id' and value:
                if not self.safe_patterns['user_id'].match(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid user ID format"
                    )
    
    async def _log_request(self, request: Request, response: Optional[Response], 
                          start_time: float, user_id: str, client_ip: str, error: Optional[str]):
        """Log request for monitoring"""
        duration = time.time() - start_time
        status_code = response.status_code if response else 500
        
        # Determine if this is a security event
        security_events = [
            'rate_limit_exceeded',
            'invalid_signature',
            'invalid_api_key',
            'input_validation_failed',
            'unauthorized_access'
        ]
        
        is_security_event = any(event in str(error).lower() for event in security_events) if error else False
        
        if is_security_event or status_code >= 400:
            await self.security.monitor.log_security_event(SecurityEvent(
                event_type='api_request',
                severity='HIGH' if status_code >= 500 else 'MEDIUM',
                user_id=user_id,
                ip_address=client_ip,
                timestamp=datetime.utcnow(),
                details={
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': status_code,
                    'duration': duration,
                    'error': error
                }
            ))

# API Key Management
class APIKeyManager:
    """Manage API keys for authentication"""
    
    def __init__(self):
        self.api_keys = {}
        self.security = get_security_framework()
    
    def generate_api_key(self, user_id: str, permissions: List[str], rate_limit_multiplier: float = 1.0) -> str:
        """Generate new API key"""
        import secrets
        
        # Generate random key
        key = f"pk_{secrets.token_urlsafe(32)}"
        
        # Hash and store
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = APIKey(
            key_id=f"key_{int(time.time())}",
            key_hash=key_hash,
            user_id=user_id,
            permissions=permissions,
            rate_limit_multiplier=rate_limit_multiplier,
            created_at=datetime.utcnow()
        )
        
        self.api_keys[api_key.key_id] = api_key
        
        # Log key creation
        self.security.monitor.log_security_event(SecurityEvent(
            event_type='api_key_created',
            severity='LOW',
            user_id=user_id,
            ip_address='system',
            timestamp=datetime.utcnow(),
            details={'key_id': api_key.key_id, 'permissions': permissions}
        ))
        
        return key
    
    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys and self.api_keys[key_id].user_id == user_id:
            self.api_keys[key_id].is_active = False
            
            # Log key revocation
            self.security.monitor.log_security_event(SecurityEvent(
                event_type='api_key_revoked',
                severity='MEDIUM',
                user_id=user_id,
                ip_address='system',
                timestamp=datetime.utcnow(),
                details={'key_id': key_id}
            ))
            
            return True
        return False
    
    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List API keys for user"""
        user_keys = []
        for key_id, api_key in self.api_keys.items():
            if api_key.user_id == user_id:
                user_keys.append({
                    'key_id': key_id,
                    'permissions': api_key.permissions,
                    'rate_limit_multiplier': api_key.rate_limit_multiplier,
                    'created_at': api_key.created_at.isoformat(),
                    'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
                    'is_active': api_key.is_active
                })
        
        return user_keys

# Initialize API key manager
api_key_manager = APIKeyManager()
