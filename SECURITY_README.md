# Active Protection Layers Security Framework

## Overview

The Active Protection Layers (APL) Security Framework provides comprehensive security protection for the Crypto Predict Monitor system. It implements multiple layers of security controls including API security, wallet security, operations security, data security, webhook security, and advanced monitoring with threat detection.

## Architecture

The security framework consists of six main protection layers:

### 1. API Security Layer
- **Rate Limiting**: Redis-based sliding window rate limiting (100 req/min default)
- **Input Validation**: Comprehensive validation using Pydantic models
- **API Key Authentication**: Secure API key management with HMAC signatures
- **Request Sanitization**: Protection against SQL injection, XSS, and other attacks

### 2. Wallet Security Layer
- **Signature Verification**: Ethereum signature verification with nonces
- **Trade Limits**: $1000 per trade limit with volume controls
- **Nonce Management**: Cryptographically secure nonces with expiration
- **Address Validation**: Ethereum address format validation and suspicious address detection

### 3. Operations Security Layer
- **Trade Validation**: Spread validation (<1.00), liquidity checks (>$100)
- **Timeout Protection**: 30-second timeouts for all operations
- **Risk Scoring**: Comprehensive risk assessment for all trades
- **Pattern Detection**: Detection of suspicious trading patterns

### 4. Data Security Layer
- **Encryption**: AES-256 encryption for sensitive data
- **Credential Management**: Secure credential storage and rotation
- **Audit Logging**: Comprehensive audit trail for all operations
- **Data Classification**: Automatic data classification and sanitization

### 5. Webhook Security Layer
- **HMAC Verification**: SHA-256 HMAC signature verification
- **Deduplication**: Event deduplication with fingerprinting
- **Timeout Handling**: Configurable timeouts and retry logic
- **Source Validation**: Whitelist-based source validation

### 6. Monitoring & Threat Detection Layer
- **Real-time Monitoring**: Continuous security event monitoring
- **Threat Patterns**: Configurable threat detection patterns
- **Automated Response**: Automated blocking, suspension, and alerts
- **Metrics Dashboard**: Comprehensive security metrics and reporting

## Installation

1. Install security dependencies:
```bash
pip install -r security_requirements.txt
```

2. Set up environment variables:
```bash
# Core security
export MASTER_PASSWORD="your_secure_master_password"
export ENCRYPTION_SALT="your_encryption_salt"
export DATA_ENCRYPTION_KEY="your_data_encryption_key"

# Redis
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD="your_redis_password"

# Webhook security
export WEBHOOK_SECRET="your_webhook_secret"
export ALCHEMY_WEBHOOK_SECRET="your_alchemy_secret"

# Database
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_KEY="your_supabase_key"

# Discord alerts
export DISCORD_HEALTH_WEBHOOK_URL="your_discord_webhook_url"
```

3. Initialize Redis:
```bash
redis-server
```

## Quick Start

### Basic Integration

```python
from utils.security_integration import create_security_app, secure_endpoint

# Create secure FastAPI app
app = create_security_app()

@app.post("/api/trade")
@secure_endpoint(rate_limit_per_minute=10, require_wallet=True)
async def execute_trade(trade_data: TradeRequest):
    # Your trading logic here
    return {"status": "success"}
```

### Advanced Usage

```python
from utils.security_framework import get_security_framework
from utils.wallet_security import wallet_security
from utils.operations_security import operations_security

# Get security framework
security = get_security_framework()

# Verify wallet signature
is_valid, error = await wallet_security.verify_signature(
    user_address="0x...",
    message="trade_data",
    signature="0x...",
    nonce="nonce"
)

# Validate trade
validation_result = await operations_security.validate_trade(trade_data)
if not validation_result.is_valid:
    raise Exception(f"Trade validation failed: {validation_result.errors}")
```

## Configuration

### Security Configuration

```python
# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 100
RATE_LIMIT_REQUESTS_PER_HOUR = 1000
RATE_LIMIT_REQUESTS_PER_DAY = 10000

# Wallet security
MAX_TRADE_VALUE = 1000.0
NONCE_TIMEOUT = 300  # 5 minutes
SIGNATURE_TIMEOUT = 60  # 1 minute

# Operations security
MAX_SPREAD = 1.00
MIN_LIQUIDITY = 100.0
TIMEOUT_SECONDS = 30

# Webhook security
WEBHOOK_TIMEOUT = 30
MAX_PAYLOAD_SIZE = 10485760  # 10MB
SIGNATURE_TOLERANCE = 300  # 5 minutes
```

### Threat Detection Patterns

```python
# Custom threat patterns
CUSTOM_THREAT_PATTERNS = [
    {
        "pattern_id": "custom_large_trades",
        "name": "Large Trade Detection",
        "threat_level": "high",
        "conditions": {"event_type": "trade", "value": ">5000"},
        "time_window": 3600,
        "threshold": 3,
        "action": "require_mfa"
    }
]
```

## Security Features

### Rate Limiting
- **Sliding Window**: Redis-based sliding window rate limiting
- **Multiple Windows**: Per-minute, per-hour, per-day limits
- **User-based**: Individual user rate limits
- **IP-based**: IP address rate limiting
- **Burst Protection**: Burst size limits

### Authentication & Authorization
- **API Keys**: Secure API key management with rotation
- **Wallet Signatures**: Ethereum signature verification
- **Multi-factor**: MFA requirements for sensitive operations
- **Role-based**: Role-based access control

### Data Protection
- **Encryption**: AES-256 encryption for sensitive data
- **Key Rotation**: Automated encryption key rotation
- **Data Sanitization**: Automatic PII detection and masking
- **Audit Trail**: Comprehensive audit logging

### Threat Detection
- **Pattern Matching**: Configurable threat patterns
- **Anomaly Detection**: Statistical anomaly detection
- **Real-time Alerts**: Real-time threat notifications
- **Automated Response**: Automated blocking and suspension

### Monitoring & Metrics
- **Security Dashboard**: Real-time security metrics
- **Alert System**: Multi-channel alert notifications
- **Performance Metrics**: Security system performance
- **Compliance Reports**: Automated compliance reporting

## API Endpoints

### Security Management
- `GET /security/health` - System health status
- `GET /security/metrics` - Security metrics
- `GET /security/alerts` - Recent security alerts
- `POST /security/block-ip` - Block IP address
- `POST /security/suspend-user` - Suspend user

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Token refresh
- `POST /api/auth/mfa` - MFA verification

## Threat Detection Rules

### Built-in Patterns
1. **Brute Force Login**: 10 failed logins in 5 minutes
2. **Credential Stuffing**: 50 failed logins in 10 minutes
3. **Suspicious Trading**: 5 trades >$5000 in 1 hour
4. **API Abuse**: 1000 API calls in 1 minute
5. **Signature Attacks**: 15 failed signatures in 1 hour
6. **Rate Limit Evasion**: 50 rate limit violations in 1 hour
7. **Account Takeover**: 20 failed logins from different IPs
8. **Data Exfiltration**: 100 data accesses in 5 minutes
9. **Webhook Abuse**: 200 webhook requests in 1 minute
10. **Session Abuse**: 5 concurrent sessions in 5 minutes

### Custom Patterns
Add custom threat patterns via environment variables or configuration:

```python
threat_detector.add_threat_pattern(ThreatPattern(
    pattern_id="custom_pattern",
    name="Custom Threat",
    threat_level=ThreatLevel.HIGH,
    conditions={"event_type": "custom_event"},
    time_window=300,
    threshold=10,
    action=AlertAction.BLOCK_IP
))
```

## Automated Responses

### Response Actions
- **LOG_ONLY**: Log the event only
- **BLOCK_IP**: Block the IP address
- **SUSPEND_USER**: Suspend the user account
- **REQUIRE_MFA**: Require multi-factor authentication
- **NOTIFY_ADMIN**: Send notifications to administrators
- **EMERGENCY_SHUTDOWN**: Emergency system shutdown

### Response Triggers
- **High Severity Events**: Automatic blocking/suspension
- **Pattern Matches**: Pattern-based automated responses
- **Anomaly Detection**: Statistical anomaly responses
- **Manual Triggers**: Admin-triggered responses

## Monitoring & Alerting

### Discord Integration
- **Real-time Alerts**: Discord webhook notifications
- **Severity Levels**: Color-coded alerts by severity
- **Detailed Information**: Event details and context
- **Action Tracking**: Automated response tracking

### Metrics Dashboard
- **Event Statistics**: Event counts by type and severity
- **Response Times**: Average response times
- **Blocked Entities**: Blocked IPs and suspended users
- **System Health**: Overall system health status

### Audit Trail
- **Comprehensive Logging**: All security events logged
- **Data Access**: Data access and modification tracking
- **User Actions**: User action audit trail
- **System Changes**: System configuration changes

## Best Practices

### Security Configuration
1. **Strong Passwords**: Use strong master passwords
2. **Key Rotation**: Regularly rotate encryption keys
3. **Environment Variables**: Store secrets in environment variables
4. **Network Security**: Use firewalls and VPNs
5. **Regular Updates**: Keep dependencies updated

### Operational Security
1. **Monitor Logs**: Regularly review security logs
2. **Update Patterns**: Keep threat patterns updated
3. **Test Responses**: Test automated responses
4. **Backup Data**: Regular security data backups
5. **Incident Response**: Have incident response plans

### Development Security
1. **Code Review**: Security-focused code reviews
2. **Static Analysis**: Use security analysis tools
3. **Penetration Testing**: Regular penetration testing
4. **Dependency Scanning**: Scan for vulnerable dependencies
5. **Security Training**: Team security awareness training

## Troubleshooting

### Common Issues

#### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

#### Encryption Key Issues
```python
# Generate new encryption key
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"New key: {key.decode()}")
```

#### Rate Limiting Issues
```python
# Check rate limits
from utils.security_framework import get_security_framework
security = get_security_framework()
is_allowed, limits = await security.rate_limiter.is_allowed("user_id")
print(f"Allowed: {is_allowed}, Limits: {limits}")
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger('security').setLevel(logging.DEBUG)
```

## Performance Considerations

### Optimization Tips
1. **Redis Optimization**: Use Redis clustering for high load
2. **Connection Pooling**: Use connection pooling for databases
3. **Caching**: Cache frequently accessed data
4. **Async Operations**: Use async/await for I/O operations
5. **Memory Management**: Monitor memory usage and cleanup

### Scaling
1. **Horizontal Scaling**: Multiple security instances
2. **Load Balancing**: Distribute security load
3. **Database Sharding**: Shard security data
4. **CDN Integration**: Use CDN for static security assets

## Compliance

### Standards Compliance
- **GDPR**: Data protection and privacy
- **SOC 2**: Security controls and procedures
- **ISO 27001**: Information security management
- **PCI DSS**: Payment card industry standards

### Audit Requirements
- **Data Retention**: Configurable data retention policies
- **Access Logs**: Comprehensive access logging
- **Change Management**: Change tracking and approval
- **Incident Reporting**: Automated incident reporting

## Support

### Documentation
- **API Reference**: Complete API documentation
- **Configuration Guide**: Detailed configuration options
- **Troubleshooting Guide**: Common issues and solutions
- **Best Practices**: Security best practices

### Community
- **GitHub Issues**: Report bugs and request features
- **Discord Community**: Join our Discord community
- **Security Advisory**: Report security vulnerabilities
- **Contributing**: Contribute to the project

## License

This security framework is licensed under the MIT License. See LICENSE file for details.

## Changelog

### Version 2.0.0
- Complete Active Protection Layers implementation
- Advanced threat detection and response
- Comprehensive monitoring and metrics
- Enhanced webhook security
- Improved performance and scalability

### Version 1.0.0
- Initial security framework
- Basic rate limiting and authentication
- Simple monitoring and logging
