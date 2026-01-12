"""
Operations Security Implementation
Trade validation, timeouts, and operational security controls
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import aiohttp
from decimal import Decimal, InvalidOperation
from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

@dataclass
class TradeValidationResult:
    """Result of trade validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    risk_score: float  # 0.0 to 1.0
    execution_time: float

@dataclass
class MarketData:
    """Market data for validation"""
    market_id: str
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    spread: float
    liquidity: float
    volume_24h: float
    last_updated: datetime
    is_active: bool = True

@dataclass
class SecurityConfig:
    """Security configuration"""
    max_spread: float = 1.00
    min_liquidity: float = 100.0
    max_trade_size: float = 10000.0
    min_trade_size: float = 1.0
    timeout_seconds: int = 30
    max_slippage: float = 0.05  # 5%
    required_confirmations: int = 1
    price_deviation_threshold: float = 0.10  # 10%

class OperationsSecurity:
    """Comprehensive operations security"""
    
    def __init__(self):
        self.security = get_security_framework()
        self.config = SecurityConfig()
        
        # Market data cache
        self.market_data_cache = {}
        self.cache_timeout = 60  # seconds
        
        # Operation tracking
        self.active_operations = {}
        self.operation_history = []
        
        # Risk scoring weights
        self.risk_weights = {
            'spread_risk': 0.3,
            'liquidity_risk': 0.25,
            'size_risk': 0.2,
            'timing_risk': 0.15,
            'market_risk': 0.1
        }
        
        # Initialize executor for timeout operations
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def validate_trade(self, trade_data: Dict[str, Any], user_context: Dict[str, Any] = None) -> TradeValidationResult:
        """Comprehensive trade validation with risk scoring"""
        start_time = time.time()
        errors = []
        warnings = []
        risk_factors = {}
        
        try:
            # 1. Basic structure validation
            structure_errors = self._validate_trade_structure(trade_data)
            errors.extend(structure_errors)
            
            # 2. Market data validation
            market_errors, market_warnings, market_risk = await self._validate_market_data(trade_data)
            errors.extend(market_errors)
            warnings.extend(market_warnings)
            risk_factors['market_risk'] = market_risk
            
            # 3. Financial validation
            financial_errors, financial_warnings, financial_risk = self._validate_financials(trade_data)
            errors.extend(financial_errors)
            warnings.extend(financial_warnings)
            risk_factors['financial_risk'] = financial_risk
            
            # 4. Timing validation
            timing_errors, timing_warnings, timing_risk = await self._validate_timing(trade_data, user_context)
            errors.extend(timing_errors)
            warnings.extend(timing_warnings)
            risk_factors['timing_risk'] = timing_risk
            
            # 5. User context validation
            if user_context:
                user_errors, user_warnings, user_risk = await self._validate_user_context(trade_data, user_context)
                errors.extend(user_errors)
                warnings.extend(user_warnings)
                risk_factors['user_risk'] = user_risk
            
            # 6. Calculate overall risk score
            risk_score = self._calculate_risk_score(risk_factors)
            
            # 7. Apply risk-based rules
            risk_warnings = self._apply_risk_rules(risk_score, trade_data)
            warnings.extend(risk_warnings)
            
            execution_time = time.time() - start_time
            
            result = TradeValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                risk_score=risk_score,
                execution_time=execution_time
            )
            
            # Log validation result
            await self._log_validation_result(trade_data, result, user_context)
            
            return result
            
        except Exception as e:
            logger.error(f"Trade validation error: {e}")
            return TradeValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                risk_score=1.0,
                execution_time=time.time() - start_time
            )
    
    def _validate_trade_structure(self, trade_data: Dict[str, Any]) -> List[str]:
        """Validate basic trade structure"""
        errors = []
        
        required_fields = ['market_id', 'side', 'amount', 'price', 'user_address']
        for field in required_fields:
            if field not in trade_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate side
        if 'side' in trade_data and trade_data['side'] not in ['YES', 'NO']:
            errors.append("Side must be 'YES' or 'NO'")
        
        # Validate amount
        if 'amount' in trade_data:
            try:
                amount = float(trade_data['amount'])
                if amount <= 0:
                    errors.append("Amount must be positive")
                if amount < self.config.min_trade_size:
                    errors.append(f"Amount below minimum: ${self.config.min_trade_size}")
                if amount > self.config.max_trade_size:
                    errors.append(f"Amount above maximum: ${self.config.max_trade_size}")
            except (ValueError, TypeError):
                errors.append("Invalid amount format")
        
        # Validate price
        if 'price' in trade_data:
            try:
                price = float(trade_data['price'])
                if price <= 0 or price > 1:
                    errors.append("Price must be between 0 and 1")
            except (ValueError, TypeError):
                errors.append("Invalid price format")
        
        # Validate market_id
        if 'market_id' in trade_data:
            market_id = trade_data['market_id']
            if not isinstance(market_id, str) or len(market_id) > 100:
                errors.append("Invalid market ID format")
        
        return errors
    
    async def _validate_market_data(self, trade_data: Dict[str, Any]) -> Tuple[List[str], List[str], float]:
        """Validate against current market data"""
        errors = []
        warnings = []
        risk_score = 0.0
        
        try:
            market_id = trade_data.get('market_id')
            if not market_id:
                return errors, warnings, risk_score
            
            # Get market data
            market_data = await self._get_market_data(market_id)
            if not market_data:
                errors.append("Market not found or inactive")
                return errors, warnings, risk_score
            
            # Validate spread
            if market_data.spread > self.config.max_spread:
                errors.append(f"Spread too wide: {market_data.spread:.3f} > {self.config.max_spread}")
                risk_score += 0.5
            elif market_data.spread > self.config.max_spread * 0.8:
                warnings.append(f"Spread approaching limit: {market_data.spread:.3f}")
                risk_score += 0.3
            
            # Validate liquidity
            if market_data.liquidity < self.config.min_liquidity:
                errors.append(f"Insufficient liquidity: ${market_data.liquidity:.2f} < ${self.config.min_liquidity}")
                risk_score += 0.4
            elif market_data.liquidity < self.config.min_liquidity * 2:
                warnings.append(f"Low liquidity: ${market_data.liquidity:.2f}")
                risk_score += 0.2
            
            # Validate price against market
            trade_price = float(trade_data.get('price', 0))
            side = trade_data.get('side', '')
            
            if side == 'YES':
                market_price = (market_data.yes_bid + market_data.yes_ask) / 2
            else:
                market_price = (market_data.no_bid + market_data.no_ask) / 2
            
            price_deviation = abs(trade_price - market_price) / market_price
            if price_deviation > self.config.price_deviation_threshold:
                errors.append(f"Price deviation too high: {price_deviation:.2%}")
                risk_score += 0.3
            elif price_deviation > self.config.price_deviation_threshold * 0.5:
                warnings.append(f"Price deviation: {price_deviation:.2%}")
                risk_score += 0.1
            
            # Check for unusual market conditions
            if market_data.volume_24h < 1000:
                warnings.append("Low market volume")
                risk_score += 0.1
            
            return errors, warnings, min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Market data validation error: {e}")
            return ["Market data validation failed"], [], 1.0
    
    def _validate_financials(self, trade_data: Dict[str, Any]) -> Tuple[List[str], List[str], float]:
        """Validate financial aspects of trade"""
        errors = []
        warnings = []
        risk_score = 0.0
        
        try:
            amount = float(trade_data.get('amount', 0))
            price = float(trade_data.get('price', 0))
            
            # Calculate trade value
            trade_value = amount * price
            
            # Check for unusually large trades
            if trade_value > 5000:
                warnings.append(f"Large trade value: ${trade_value:.2f}")
                risk_score += 0.2
            elif trade_value > 1000:
                risk_score += 0.1
            
            # Check for precision issues
            if len(str(price).split('.')[-1]) > 4:
                warnings.append("High price precision may cause slippage")
                risk_score += 0.05
            
            # Validate against user balance (if available)
            if 'user_balance' in trade_data:
                balance = float(trade_data['user_balance'])
                if trade_value > balance * 0.9:  # Don't allow using more than 90% of balance
                    warnings.append("Trade uses high percentage of balance")
                    risk_score += 0.15
            
            return errors, warnings, min(risk_score, 1.0)
            
        except (ValueError, TypeError) as e:
            return ["Financial validation error"], [], 1.0
    
    async def _validate_timing(self, trade_data: Dict[str, Any], user_context: Dict[str, Any] = None) -> Tuple[List[str], List[str], float]:
        """Validate timing and frequency"""
        errors = []
        warnings = []
        risk_score = 0.0
        
        try:
            user_address = trade_data.get('user_address')
            if not user_address:
                return errors, warnings, risk_score
            
            # Check for rapid trading
            recent_trades_key = f"recent_trades:{user_address}"
            current_time = time.time()
            
            # Clean old trades (older than 5 minutes)
            await self.security.redis.zremrangebyscore(recent_trades_key, 0, current_time - 300)
            
            # Count recent trades
            recent_count = await self.security.redis.zcard(recent_trades_key)
            
            if recent_count > 10:  # More than 10 trades in 5 minutes
                errors.append("Too many trades in short time period")
                risk_score += 0.4
            elif recent_count > 5:
                warnings.append("High trading frequency")
                risk_score += 0.2
            
            # Check for pattern trading (same market repeatedly)
            market_id = trade_data.get('market_id')
            market_trades_key = f"market_trades:{user_address}:{market_id}"
            
            await self.security.redis.zremrangebyscore(market_trades_key, 0, current_time - 300)
            market_trade_count = await self.security.redis.zcard(market_trades_key)
            
            if market_trade_count > 3:  # More than 3 trades on same market in 5 minutes
                warnings.append("Repeated trading on same market")
                risk_score += 0.1
            
            return errors, warnings, min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Timing validation error: {e}")
            return ["Timing validation failed"], [], 1.0
    
    async def _validate_user_context(self, trade_data: Dict[str, Any], user_context: Dict[str, Any]) -> Tuple[List[str], List[str], float]:
        """Validate based on user context and history"""
        errors = []
        warnings = []
        risk_score = 0.0
        
        try:
            # Check user's historical performance
            if 'win_rate' in user_context:
                win_rate = float(user_context['win_rate'])
                if win_rate < 0.3:  # Low win rate
                    warnings.append("User has low historical win rate")
                    risk_score += 0.1
            
            # Check account age
            if 'account_age_days' in user_context:
                account_age = int(user_context['account_age_days'])
                if account_age < 7:  # New account
                    warnings.append("New user account")
                    risk_score += 0.15
                elif account_age < 30:
                    risk_score += 0.05
            
            # Check for suspicious patterns
            if 'failed_trades_24h' in user_context:
                failed_trades = int(user_context['failed_trades_24h'])
                if failed_trades > 10:
                    errors.append("High number of failed trades")
                    risk_score += 0.3
                elif failed_trades > 5:
                    warnings.append("Multiple failed trades")
                    risk_score += 0.1
            
            return errors, warnings, min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"User context validation error: {e}")
            return [], [], 0.0
    
    def _calculate_risk_score(self, risk_factors: Dict[str, float]) -> float:
        """Calculate overall risk score from individual factors"""
        total_score = 0.0
        total_weight = 0.0
        
        for factor, score in risk_factors.items():
            weight = self.risk_weights.get(factor.replace('_risk', '_risk'), 0.1)
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return min(total_score / total_weight, 1.0)
        return 0.0
    
    def _apply_risk_rules(self, risk_score: float, trade_data: Dict[str, Any]) -> List[str]:
        """Apply risk-based validation rules"""
        warnings = []
        
        if risk_score > 0.8:
            warnings.append("Very high risk trade - manual review recommended")
        elif risk_score > 0.6:
            warnings.append("High risk trade")
        elif risk_score > 0.4:
            warnings.append("Moderate risk trade")
        
        # Additional rules based on trade size and risk
        amount = float(trade_data.get('amount', 0))
        if amount > 1000 and risk_score > 0.3:
            warnings.append("Large trade with elevated risk")
        
        return warnings
    
    async def _get_market_data(self, market_id: str) -> Optional[MarketData]:
        """Get market data with caching"""
        try:
            # Check cache first
            cache_key = f"market_data:{market_id}"
            cached_data = await self.security.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return MarketData(**data)
            
            # Fetch fresh data (this would integrate with your market data API)
            market_data = await self._fetch_market_data(market_id)
            
            if market_data:
                # Cache the data
                await self.security.redis.setex(
                    cache_key, 
                    self.cache_timeout, 
                    json.dumps(asdict(market_data), default=str)
                )
                return market_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    async def _fetch_market_data(self, market_id: str) -> Optional[MarketData]:
        """Fetch market data from external API"""
        try:
            # This would integrate with your actual market data API
            # For now, return mock data
            return MarketData(
                market_id=market_id,
                yes_bid=0.45,
                yes_ask=0.47,
                no_bid=0.53,
                no_ask=0.55,
                spread=0.08,
                liquidity=5000.0,
                volume_24h=10000.0,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    async def execute_with_timeout(self, operation: Callable, timeout: int = None, *args, **kwargs) -> Any:
        """Execute operation with timeout protection"""
        timeout = timeout or self.config.timeout_seconds
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: asyncio.run_for_timeout(operation(*args, **kwargs), timeout)
            )
            return result
            
        except FutureTimeoutError:
            await self._log_security_event(
                'operation_timeout',
                'MEDIUM',
                'system',
                'system',
                {'timeout': timeout, 'operation': operation.__name__}
            )
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Operation execution error: {e}")
            raise
    
    async def _log_validation_result(self, trade_data: Dict[str, Any], result: TradeValidationResult, user_context: Dict[str, Any] = None):
        """Log validation result for monitoring"""
        severity = 'HIGH' if not result.is_valid else ('MEDIUM' if result.risk_score > 0.6 else 'LOW')
        
        await self.security.monitor.log_security_event(SecurityEvent(
            event_type='trade_validation',
            severity=severity,
            user_id=trade_data.get('user_address'),
            ip_address='system',
            timestamp=datetime.utcnow(),
            details={
                'market_id': trade_data.get('market_id'),
                'amount': trade_data.get('amount'),
                'price': trade_data.get('price'),
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'risk_score': result.risk_score,
                'execution_time': result.execution_time
            }
        ))
    
    async def _log_security_event(self, event_type: str, severity: str, user_id: str, ip_address: str, details: Dict[str, Any]):
        """Log security event"""
        await self.security.monitor.log_security_event(SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            details=details
        ))
    
    async def record_trade_execution(self, trade_data: Dict[str, Any], validation_result: TradeValidationResult):
        """Record successful trade execution"""
        try:
            user_address = trade_data.get('user_address')
            market_id = trade_data.get('market_id')
            current_time = time.time()
            
            # Record in user's recent trades
            recent_trades_key = f"recent_trades:{user_address}"
            await self.security.redis.zadd(recent_trades_key, {json.dumps(trade_data): current_time})
            await self.security.redis.expire(recent_trades_key, 300)  # 5 minutes
            
            # Record in market-specific trades
            market_trades_key = f"market_trades:{user_address}:{market_id}"
            await self.security.redis.zadd(market_trades_key, {json.dumps(trade_data): current_time})
            await self.security.redis.expire(market_trades_key, 300)
            
            # Log successful execution
            await self._log_security_event(
                'trade_executed',
                'LOW',
                user_address,
                'system',
                {
                    'market_id': market_id,
                    'amount': trade_data.get('amount'),
                    'risk_score': validation_result.risk_score
                }
            )
            
        except Exception as e:
            logger.error(f"Error recording trade execution: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        try:
            stats = {
                'config': asdict(self.config),
                'cache_size': len(self.market_data_cache),
                'active_operations': len(self.active_operations),
                'risk_weights': self.risk_weights
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting security stats: {e}")
            return {}
    
    async def shutdown(self):
        """Cleanup resources"""
        try:
            self.executor.shutdown(wait=True)
            logger.info("Operations security shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Initialize operations security
operations_security = OperationsSecurity()
