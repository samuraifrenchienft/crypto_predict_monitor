"""
Bot Configuration Loader
Clean configuration management for the arbitrage bot
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from shared.logger import get_logger
from shared.utils import load_env_var, validate_url
from bot.models import TierConfig, PlatformConfig


class Config:
    """Centralized configuration management"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config = {}
        self.logger = get_logger(__name__)
        self.load()
    
    def load(self) -> None:
        """Load configuration from file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                self.logger.error(f"Config file not found: {self.config_path}")
                self._config = self._get_default_config()
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Expand environment variables
            self._config = self._expand_env_vars(self._config)
            
            # Validate configuration
            self._validate_config()
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self._config = self._get_default_config()
    
    def _expand_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Expand environment variables in configuration"""
        def expand_value(value):
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                return load_env_var(env_var, '')
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            return value
        
        return expand_value(config)
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Validate strategy
        strategy = self.get('strategy', {})
        min_spread = strategy.get('min_spread', 0.015)
        if not isinstance(min_spread, (int, float)) or min_spread <= 0:
            raise ValueError("Invalid min_spread in strategy configuration")
        
        # Validate tiers
        tiers = self.get('tiers', {})
        required_tiers = ['exceptional', 'excellent', 'very_good', 'good', 'fair', 'poor']
        for tier_name in required_tiers:
            if tier_name not in tiers:
                raise ValueError(f"Missing tier configuration: {tier_name}")
        
        # Validate platforms
        platforms = self.get('platforms', {})
        for platform_name, platform_config in platforms.items():
            base_url = platform_config.get('base_url', '')
            if not validate_url(base_url):
                raise ValueError(f"Invalid base_url for platform {platform_name}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'strategy': {
                'name': 'Spread-Only Arbitrage',
                'min_spread': 0.015,
                'prioritize_new_events': True,
                'new_event_hours': 24
            },
            'tiers': {
                'exceptional': {'min_spread': 3.0, 'emoji': '🔵', 'color': '#0066ff', 'action': 'IMMEDIATE ATTENTION', 'priority': 1, 'alert': True},
                'excellent': {'min_spread': 2.51, 'emoji': '🟢', 'color': '#00ff00', 'action': 'ACT QUICKLY', 'priority': 2, 'alert': True},
                'very_good': {'min_spread': 2.01, 'emoji': '💛', 'color': '#ffff00', 'action': 'STRONG YES', 'priority': 3, 'alert': True},
                'good': {'min_spread': 1.0, 'emoji': '🟠', 'color': '#ffa500', 'action': 'YOUR STRATEGY', 'priority': 4, 'alert': True},
                'fair': {'min_spread': 0.75, 'emoji': '⚪', 'color': '#808080', 'action': 'FILTERED OUT', 'priority': 5, 'alert': False},
                'poor': {'min_spread': 0.0, 'emoji': '⚫', 'color': '#808080', 'action': 'FILTERED OUT', 'priority': 6, 'alert': False}
            },
            'platforms': {
                'polymarket': {'enabled': True, 'base_url': 'https://polymarket.com', 'rate_limit': 100, 'timeout': 30, 'retry_attempts': 3, 'retry_delay': 1},
                'azuro': {'enabled': True, 'base_url': 'https://bookmaker.xyz', 'rate_limit': 100, 'timeout': 30, 'retry_attempts': 3, 'retry_delay': 1},
                'manifold': {'enabled': True, 'base_url': 'https://manifold.markets', 'rate_limit': 100, 'timeout': 30, 'retry_attempts': 3, 'retry_delay': 1},
                'limitless': {'enabled': True, 'base_url': 'https://limitless.exchange', 'rate_limit': 100, 'timeout': 30, 'retry_attempts': 3, 'retry_delay': 1}
            },
            'data_collection': {
                'refresh_interval': 300,
                'max_markets_per_platform': 1000,
                'cache_ttl': 600,
                'enable_caching': True
            },
            'discord': {
                'webhook_url': '',
                'health_webhook_url': '',
                'bot_token': '',
                'avatar_url': 'https://your-hosting.com/cpm_samurai_bulldog.png',
                'max_alerts_per_batch': 25,
                'alert_cooldown': 300
            },
            'dashboard': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'secret_key': '',
                'database_url': '',
                'session_timeout': 3600
            },
            'logging': {
                'level': 'INFO',
                'format': 'structured',
                'file_path': 'data/logs/cpm.log',
                'max_file_size': 10485760,
                'backup_count': 5,
                'enable_console': True
            },
            'database': {
                'url': '',
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'echo': False
            },
            'error_handling': {
                'max_retries': 3,
                'retry_delay': 1,
                'circuit_breaker_threshold': 5,
                'circuit_breaker_timeout': 60
            },
            'monitoring': {
                'enable_metrics': True,
                'metrics_port': 9090,
                'health_check_interval': 60,
                'alert_on_errors': True
            },
            'development': {
                'debug_mode': False,
                'mock_data': False,
                'enable_profiling': False,
                'log_all_requests': False
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by key path
        
        Args:
            key_path: Dot-separated key path (e.g., 'strategy.min_spread')
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        current = self._config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_tier_configs(self) -> Dict[str, TierConfig]:
        """Get tier configurations as TierConfig objects"""
        tier_configs = {}
        tiers = self.get('tiers', {})
        
        for tier_name, tier_data in tiers.items():
            tier_configs[tier_name] = TierConfig(
                name=tier_name,
                min_spread=tier_data.get('min_spread', 0.0),
                emoji=tier_data.get('emoji', '❓'),
                color=tier_data.get('color', '#808080'),
                action=tier_data.get('action', 'UNKNOWN'),
                priority=tier_data.get('priority', 99),
                alert=tier_data.get('alert', False)
            )
        
        return tier_configs
    
    def get_platform_configs(self) -> Dict[str, PlatformConfig]:
        """Get platform configurations as PlatformConfig objects"""
        from bot.models import Platform
        
        platform_configs = {}
        platforms = self.get('platforms', {})
        
        for platform_name, platform_data in platforms.items():
            try:
                platform_enum = Platform(platform_name)
                platform_configs[platform_name] = PlatformConfig(
                    platform=platform_enum,
                    enabled=platform_data.get('enabled', False),
                    base_url=platform_data.get('base_url', ''),
                    rate_limit=platform_data.get('rate_limit', 100),
                    timeout=platform_data.get('timeout', 30),
                    retry_attempts=platform_data.get('retry_attempts', 3),
                    retry_delay=platform_data.get('retry_delay', 1)
                )
            except ValueError:
                self.logger.warning(f"Unknown platform: {platform_name}")
        
        return platform_configs
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.load()
    
    def is_enabled(self, platform_name: str) -> bool:
        """Check if platform is enabled"""
        return self.get(f'platforms.{platform_name}.enabled', False)
    
    def get_strategy_min_spread(self) -> float:
        """Get strategy minimum spread"""
        return self.get('strategy.min_spread', 0.015)
    
    def get_discord_webhook_url(self) -> str:
        """Get Discord webhook URL"""
        return self.get('discord.webhook_url', '')
    
    def get_health_webhook_url(self) -> str:
        """Get health webhook URL"""
        return self.get('discord.health_webhook_url', '')
    
    def is_development_mode(self) -> bool:
        """Check if development mode is enabled"""
        return self.get('development.debug_mode', False)


# Global config instance
_config = None


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration singleton
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config
