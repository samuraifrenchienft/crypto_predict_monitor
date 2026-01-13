"""
Security Module for Crypto Predict Monitor
Complete 9-layer protection system
"""

from .protection_layers import (
    # Layer 1: API & Webhook Security
    WebhookSignatureValidator,
    RateLimiter,
    
    # Layer 2: Fetcher Security
    FetcherHealthCheck,
    FetcherTimeout,
    
    # Layer 3: Alert Evaluation Security
    AlertValidator,
    AlertDuplicateDetector,
    AlertRateLimiter,
    IdempotentAlertTracker,
    
    # Layer 4: Data Protection
    DataEncryption,
    CredentialValidator,
    
    # Layer 5: Webhook & Discord Security
    WebhookRetryHandler,
    DiscordMessageValidator,
    
    # Layer 6: Monitoring
    HealthMonitor,
    
    # Layer 7: Market Config Validation
    MarketConfigValidator,
    
    # Layer 8: Price & Data Sanity
    PriceSanityValidator,
    PolymarketDataValidator,
    CoinbaseDataValidator,
    
    # Layer 9: Environment Validation
    EnvironmentValidator,
    
    # Main initialization
    initialize_protection_layers,
    
    # Utilities
    InputValidator,
)

__version__ = "1.0.0"
__all__ = [
    # Layer 1
    'WebhookSignatureValidator',
    'RateLimiter',
    
    # Layer 2
    'FetcherHealthCheck',
    'FetcherTimeout',
    
    # Layer 3
    'AlertValidator',
    'AlertDuplicateDetector',
    'AlertRateLimiter',
    'IdempotentAlertTracker',
    
    # Layer 4
    'DataEncryption',
    'CredentialValidator',
    
    # Layer 5
    'WebhookRetryHandler',
    'DiscordMessageValidator',
    
    # Layer 6
    'HealthMonitor',
    
    # Layer 7
    'MarketConfigValidator',
    
    # Layer 8
    'PriceSanityValidator',
    'PolymarketDataValidator',
    'CoinbaseDataValidator',
    
    # Layer 9
    'EnvironmentValidator',
    
    # Main
    'initialize_protection_layers',
    
    # Utilities
    'InputValidator',
]
