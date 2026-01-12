"""
Data Security Implementation
Encryption, secure credential loading, audit logs, and data protection
"""

import os
import json
import logging
import hashlib
import hmac
import base64
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import redis
import asyncio
from pathlib import Path
import stat
import tempfile
import shutil

from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

@dataclass
class CredentialEntry:
    """Encrypted credential entry"""
    service: str
    encrypted_data: str
    checksum: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    is_active: bool = True

@dataclass
class AuditLogEntry:
    """Audit log entry"""
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    outcome: str  # SUCCESS, FAILURE, ERROR
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class DataClassification:
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataSecurity:
    """Comprehensive data security implementation"""
    
    def __init__(self):
        self.security = get_security_framework()
        self.encryption_key = None
        self.cipher_suite = None
        self.credentials = {}
        self.audit_log = []
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Load credentials securely
        self._load_credentials()
        
        # Data classification rules
        self.classification_rules = {
            'api_keys': DataClassification.RESTRICTED,
            'private_keys': DataClassification.RESTRICTED,
            'user_emails': DataClassification.CONFIDENTIAL,
            'user_addresses': DataClassification.CONFIDENTIAL,
            'trade_data': DataClassification.INTERNAL,
            'market_data': DataClassification.PUBLIC,
            'system_logs': DataClassification.INTERNAL
        }
        
        # Sensitive field patterns
        self.sensitive_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'private_key': r'\b0x[a-fA-F0-9]{64}\b'
        }
        
        logger.info("Data security initialized")
    
    def _initialize_encryption(self):
        """Initialize encryption with secure key derivation"""
        try:
            # Try to get existing key from environment
            key_b64 = os.getenv('DATA_ENCRYPTION_KEY')
            
            if key_b64:
                self.encryption_key = base64.urlsafe_b64decode(key_b64.encode())
            else:
                # Generate new key from master password
                master_password = os.getenv('MASTER_PASSWORD', 'secure_default_password')
                salt = os.getenv('ENCRYPTION_SALT', 'default_salt').encode()
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = kdf.derive(master_password.encode())
                self.encryption_key = base64.urlsafe_b64encode(key)
            
            # Initialize cipher
            self.cipher_suite = Fernet(self.encryption_key)
            
            # Store key for future use
            if not os.getenv('DATA_ENCRYPTION_KEY'):
                os.environ['DATA_ENCRYPTION_KEY'] = self.encryption_key.decode()
            
            logger.info("Encryption initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def _load_credentials(self):
        """Load credentials from secure sources"""
        try:
            # Load from environment variables
            self._load_from_environment()
            
            # Load from encrypted files
            self._load_from_encrypted_files()
            
            # Load from secure storage (if available)
            self._load_from_secure_storage()
            
            logger.info(f"Loaded {len(self.credentials)} credentials")
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise
    
    def _load_from_environment(self):
        """Load credentials from environment variables"""
        credential_mappings = {
            'DATABASE_URL': 'database',
            'REDIS_URL': 'redis',
            'WEBHOOK_SECRET': 'webhook',
            'DISCORD_WEBHOOK_URL': 'discord_webhook',
            'DISCORD_HEALTH_WEBHOOK_URL': 'discord_health',
            'ALCHEMY_API_KEY': 'alchemy',
            'POLYMARKET_API_KEY': 'polymarket',
            'KALSHI_API_KEY': 'kalshi'
        }
        
        for env_var, service in credential_mappings.items():
            value = os.getenv(env_var)
            if value:
                self.credentials[service] = CredentialEntry(
                    service=service,
                    encrypted_data=self.encrypt(value),
                    checksum=self._calculate_checksum(value),
                    created_at=datetime.utcnow(),
                    is_active=True
                )
    
    def _load_from_encrypted_files(self):
        """Load credentials from encrypted files"""
        try:
            credentials_dir = Path.home() / '.crypto_predict_monitor' / 'credentials'
            
            if not credentials_dir.exists():
                return
            
            # Set secure permissions
            os.chmod(credentials_dir, stat.S_IRWXU)
            
            for cred_file in credentials_dir.glob('*.enc'):
                try:
                    with open(cred_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    decrypted_data = self.decrypt(encrypted_data.decode())
                    cred_info = json.loads(decrypted_data)
                    
                    self.credentials[cred_info['service']] = CredentialEntry(
                        service=cred_info['service'],
                        encrypted_data=encrypted_data.decode(),
                        checksum=cred_info['checksum'],
                        created_at=datetime.fromisoformat(cred_info['created_at']),
                        last_accessed=datetime.fromisoformat(cred_info.get('last_accessed', cred_info['created_at'])),
                        access_count=cred_info.get('access_count', 0),
                        is_active=cred_info.get('is_active', True)
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to load credential file {cred_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading encrypted files: {e}")
    
    def _load_from_secure_storage(self):
        """Load credentials from secure storage (future implementation)"""
        # This would integrate with systems like:
        # - AWS Secrets Manager
        # - HashiCorp Vault
        # - Azure Key Vault
        # - Google Secret Manager
        pass
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if not self.cipher_suite:
                raise RuntimeError("Encryption not initialized")
            
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not self.cipher_suite:
                raise RuntimeError("Encryption not initialized")
            
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def get_credential(self, service: str) -> Optional[str]:
        """Get decrypted credential with audit logging"""
        try:
            if service not in self.credentials:
                logger.warning(f"Credential not found: {service}")
                return None
            
            cred_entry = self.credentials[service]
            
            if not cred_entry.is_active:
                logger.warning(f"Credential inactive: {service}")
                return None
            
            # Decrypt the credential
            decrypted_value = self.decrypt(cred_entry.encrypted_data)
            
            # Verify checksum
            calculated_checksum = self._calculate_checksum(decrypted_value)
            if calculated_checksum != cred_entry.checksum:
                logger.error(f"Credential checksum mismatch: {service}")
                return None
            
            # Update access tracking
            cred_entry.last_accessed = datetime.utcnow()
            cred_entry.access_count += 1
            
            # Log access
            asyncio.create_task(self._log_credential_access(service, 'SUCCESS'))
            
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Error getting credential {service}: {e}")
            asyncio.create_task(self._log_credential_access(service, 'FAILURE'))
            return None
    
    def store_credential(self, service: str, value: str, overwrite: bool = False) -> bool:
        """Store encrypted credential"""
        try:
            if service in self.credentials and not overwrite:
                logger.warning(f"Credential already exists: {service}")
                return False
            
            encrypted_data = self.encrypt(value)
            checksum = self._calculate_checksum(value)
            
            self.credentials[service] = CredentialEntry(
                service=service,
                encrypted_data=encrypted_data,
                checksum=checksum,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # Also save to encrypted file
            self._save_credential_to_file(service, value)
            
            logger.info(f"Credential stored: {service}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing credential {service}: {e}")
            return False
    
    def _save_credential_to_file(self, service: str, value: str):
        """Save credential to encrypted file"""
        try:
            credentials_dir = Path.home() / '.crypto_predict_monitor' / 'credentials'
            credentials_dir.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions
            os.chmod(credentials_dir, stat.S_IRWXU)
            
            cred_file = credentials_dir / f"{service}.enc"
            
            cred_info = {
                'service': service,
                'checksum': self._calculate_checksum(value),
                'created_at': datetime.utcnow().isoformat(),
                'last_accessed': datetime.utcnow().isoformat(),
                'access_count': 0,
                'is_active': True
            }
            
            # Encrypt the credential info
            encrypted_info = self.encrypt(json.dumps(cred_info))
            
            # Write to file with secure permissions
            with open(cred_file, 'wb') as f:
                f.write(encrypted_info.encode())
            
            os.chmod(cred_file, stat.S_IRUSR)  # Read-only for owner
            
        except Exception as e:
            logger.error(f"Error saving credential file: {e}")
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA-256 checksum"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def sanitize_data(self, data: Union[str, Dict[str, Any]], classification: str = None) -> Union[str, Dict[str, Any]]:
        """Sanitize data based on classification"""
        try:
            if isinstance(data, str):
                return self._sanitize_string(data, classification)
            elif isinstance(data, dict):
                return self._sanitize_dict(data, classification)
            else:
                return data
                
        except Exception as e:
            logger.error(f"Data sanitization error: {e}")
            return data
    
    def _sanitize_string(self, text: str, classification: str = None) -> str:
        """Sanitize string data"""
        if classification == DataClassification.PUBLIC:
            return text
        
        # Mask sensitive patterns
        sanitized = text
        
        for pattern_name, pattern in self.sensitive_patterns.items():
            import re
            matches = re.findall(pattern, sanitized)
            for match in matches:
                if pattern_name in ['email', 'phone']:
                    # Show first and last characters
                    masked = match[:2] + '*' * (len(match) - 4) + match[-2:]
                elif pattern_name in ['ssn', 'credit_card']:
                    # Show last 4 digits only
                    masked = '*' * (len(match) - 4) + match[-4:]
                else:
                    # Completely mask
                    masked = '*' * len(match)
                
                sanitized = sanitized.replace(match, masked)
        
        return sanitized
    
    def _sanitize_dict(self, data: Dict[str, Any], classification: str = None) -> Dict[str, Any]:
        """Sanitize dictionary data"""
        sanitized = {}
        
        for key, value in data.items():
            # Determine field classification
            field_classification = self._get_field_classification(key)
            
            if field_classification == DataClassification.RESTRICTED:
                # Completely mask restricted fields
                sanitized[key] = '***REDACTED***'
            elif field_classification == DataClassification.CONFIDENTIAL:
                # Partially mask confidential fields
                if isinstance(value, str) and len(value) > 4:
                    sanitized[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    sanitized[key] = '***MASKED***'
            else:
                # Sanitize normally
                sanitized[key] = self.sanitize_data(value, field_classification)
        
        return sanitized
    
    def _get_field_classification(self, field_name: str) -> str:
        """Get classification for a field"""
        field_name_lower = field_name.lower()
        
        # Check exact matches
        if field_name_lower in self.classification_rules:
            return self.classification_rules[field_name_lower]
        
        # Check pattern matches
        if any(pattern in field_name_lower for pattern in ['password', 'secret', 'key', 'token']):
            return DataClassification.RESTRICTED
        elif any(pattern in field_name_lower for pattern in ['email', 'address', 'phone']):
            return DataClassification.CONFIDENTIAL
        elif any(pattern in field_name_lower for pattern in ['user', 'account', 'profile']):
            return DataClassification.INTERNAL
        else:
            return DataClassification.PUBLIC
    
    async def log_audit_event(self, user_id: str, action: str, resource: str, 
                           outcome: str, ip_address: str, user_agent: str, 
                           details: Dict[str, Any] = None, risk_level: str = 'LOW'):
        """Log audit event"""
        try:
            audit_entry = AuditLogEntry(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource=resource,
                outcome=outcome,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                risk_level=risk_level
            )
            
            # Add to in-memory log
            self.audit_log.append(audit_entry)
            
            # Keep only last 10000 entries in memory
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-10000:]
            
            # Store in Redis for persistence
            audit_data = asdict(audit_entry)
            audit_data['timestamp'] = audit_entry.timestamp.isoformat()
            
            await self.security.redis.lpush('audit_log', json.dumps(audit_data, default=str))
            await self.security.redis.expire('audit_log', 86400 * 30)  # Keep for 30 days
            
            # Log to security monitor if high risk
            if risk_level in ['HIGH', 'CRITICAL']:
                await self.security.monitor.log_security_event(SecurityEvent(
                    event_type='audit_event',
                    severity=risk_level,
                    user_id=user_id,
                    ip_address=ip_address,
                    timestamp=datetime.utcnow(),
                    details={
                        'action': action,
                        'resource': resource,
                        'outcome': outcome,
                        'risk_level': risk_level
                    }
                ))
            
        except Exception as e:
            logger.error(f"Audit logging error: {e}")
    
    async def _log_credential_access(self, service: str, outcome: str):
        """Log credential access"""
        try:
            await self.log_audit_event(
                user_id='system',
                action='credential_access',
                resource=service,
                outcome=outcome,
                ip_address='system',
                user_agent='security_framework',
                details={'service': service},
                risk_level='MEDIUM' if outcome == 'SUCCESS' else 'HIGH'
            )
        except Exception as e:
            logger.error(f"Credential access logging error: {e}")
    
    async def get_audit_trail(self, user_id: str = None, start_time: datetime = None, 
                             end_time: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get audit trail with filtering"""
        try:
            # Get all audit entries from Redis
            all_entries = await self.security.redis.lrange('audit_log', 0, -1)
            
            filtered_entries = []
            
            for entry_json in all_entries:
                try:
                    entry = json.loads(entry_json)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    # Apply filters
                    if user_id and entry.get('user_id') != user_id:
                        continue
                    
                    if start_time and entry_time < start_time:
                        continue
                    
                    if end_time and entry_time > end_time:
                        continue
                    
                    filtered_entries.append(entry)
                    
                except (json.JSONDecodeError, ValueError):
                    continue
            
            # Sort by timestamp (newest first) and limit
            filtered_entries.sort(key=lambda x: x['timestamp'], reverse=True)
            return filtered_entries[:limit]
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'credentials': {
                    'total': len(self.credentials),
                    'active': sum(1 for c in self.credentials.values() if c.is_active),
                    'services': list(self.credentials.keys())
                },
                'encryption': {
                    'initialized': self.cipher_suite is not None,
                    'key_length': len(self.encryption_key) if self.encryption_key else 0
                },
                'audit_stats': {
                    'total_entries': len(self.audit_log),
                    'recent_entries': len([e for e in self.audit_log if (datetime.utcnow() - e.timestamp).hours < 24])
                },
                'data_classification': {
                    'rules_count': len(self.classification_rules),
                    'sensitive_patterns': len(self.sensitive_patterns)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {}
    
    async def rotate_encryption_key(self, new_key: str = None):
        """Rotate encryption key and re-encrypt all data"""
        try:
            old_key = self.encryption_key
            
            # Generate new key if not provided
            if new_key:
                self.encryption_key = base64.urlsafe_b64decode(new_key.encode())
            else:
                # Generate new random key
                self.encryption_key = Fernet.generate_key()
            
            # Re-initialize cipher
            self.cipher_suite = Fernet(self.encryption_key)
            
            # Re-encrypt all credentials
            for service, cred_entry in self.credentials.items():
                # Decrypt with old key
                old_cipher = Fernet(old_key)
                decrypted_value = old_cipher.decrypt(base64.urlsafe_b64decode(cred_entry.encrypted_data.encode())).decode()
                
                # Re-encrypt with new key
                new_encrypted = self.cipher_suite.encrypt(decrypted_value.encode())
                cred_entry.encrypted_data = base64.urlsafe_b64encode(new_encrypted).decode()
                
                # Update checksum
                cred_entry.checksum = self._calculate_checksum(decrypted_value)
                
                # Save to file
                self._save_credential_to_file(service, decrypted_value)
            
            # Update environment variable
            os.environ['DATA_ENCRYPTION_KEY'] = self.encryption_key.decode()
            
            # Log key rotation
            await self.log_audit_event(
                user_id='system',
                action='key_rotation',
                resource='encryption_key',
                outcome='SUCCESS',
                ip_address='system',
                user_agent='security_framework',
                risk_level='HIGH'
            )
            
            logger.info("Encryption key rotated successfully")
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise
    
    def secure_delete_file(self, file_path: str):
        """Securely delete file by overwriting multiple times"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return
            
            # Get file size
            file_size = path.stat().st_size
            
            # Overwrite with random data multiple times
            with open(path, 'wb') as f:
                for _ in range(3):  # 3 passes
                    random_data = os.urandom(file_size)
                    f.write(random_data)
                    f.flush()
                    f.seek(0)
            
            # Delete the file
            path.unlink()
            
            logger.info(f"Securely deleted file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error securely deleting file {file_path}: {e}")

# Initialize data security
data_security = DataSecurity()
