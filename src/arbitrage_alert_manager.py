"""
Arbitrage-Focused Alert Manager
Reorganized alert priorities for top-tier arbitrage opportunities
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

from arbitrage.opportunity_detector import ArbitrageOpportunity, ArbitrageDetector

logger = logging.getLogger("arbitrage_alert_manager")

@dataclass
class ArbitrageAlert:
    """Arbitrage-focused alert structure"""
    opportunity: ArbitrageOpportunity
    alert_type: str  # "top_tier", "flash", "volume_anomaly", "liquidity_change"
    priority: int  # 1=highest, 4=lowest
    severity: str  # "critical", "warning", "info"
    timestamp: datetime
    deduplication_key: str
    reason: str

class ArbitrageAlertManager:
    """Manages arbitrage-focused alerts with quality-based prioritization"""
    
    def __init__(self):
        self.alert_history: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self.market_cooldowns: Dict[str, datetime] = {}  # Market -> last alert time
        self.deduplication_window: Dict[str, datetime] = {}  # Key -> last alert time
        self.alert_stats = defaultdict(int)
        
        # Alert priorities (1=highest priority)
        self.ALERT_PRIORITIES = {
            "top_tier": 1,           # Top-Tier Arbitrage Opportunities (efficiency + confidence > 7.0)
            "flash": 2,               # Flash Opportunities (high spread, closing fast)
            "volume_anomaly": 3,     # Volume Anomalies (unusual activity)
            "liquidity_change": 4     # Liquidity Changes (major depth updates)
        }
        
        # Cooldown periods
        self.MARKET_COOLDOWN_MINUTES = 30  # Minimum 30 minutes between alerts per market
        self.DEDUPLICATION_WINDOW_MINUTES = 5  # Same alert deduplication window
        
        # Quality thresholds
        self.TOP_TIER_MIN_EFFICIENCY = 7.0
        self.TOP_TIER_MIN_CONFIDENCE = 7.0
        self.FLASH_SPREAD_THRESHOLD = 0.04  # 4%+ spread for flash opportunities
        self.VOLUME_ANOMALY_MULTIPLIER = 3.0  # 3x normal volume
        self.LIQUIDITY_CHANGE_THRESHOLD = 0.5  # 50% liquidity change
        
    def classify_opportunity(self, opportunity: ArbitrageOpportunity, 
                           historical_volume: Optional[float] = None,
                           historical_liquidity: Optional[Dict[str, float]] = None) -> str:
        """Classify arbitrage opportunity by alert type"""
        
        # Check for top-tier arbitrage opportunities (highest priority)
        if (opportunity.efficiency_score >= self.TOP_TIER_MIN_EFFICIENCY and 
            opportunity.confidence_score >= self.TOP_TIER_MIN_CONFIDENCE):
            return "top_tier"
        
        # Check for flash opportunities (high spread, closing fast)
        if opportunity.spread >= self.FLASH_SPREAD_THRESHOLD:
            time_remaining = opportunity.expires_at - datetime.utcnow()
            if time_remaining.total_seconds() <= 3600:  # Closes within 1 hour
                return "flash"
        
        # Check for volume anomalies
        if historical_volume and opportunity.volume_24h > historical_volume * self.VOLUME_ANOMALY_MULTIPLIER:
            return "volume_anomaly"
        
        # Check for liquidity changes
        if historical_liquidity:
            current_min_liquidity = min(opportunity.yes_liquidity, opportunity.no_liquidity)
            historical_min_liquidity = min(historical_liquidity.get("yes", 0), historical_liquidity.get("no", 0))
            
            if historical_min_liquidity > 0:
                liquidity_change = abs(current_min_liquidity - historical_min_liquidity) / historical_min_liquidity
                if liquidity_change >= self.LIQUIDITY_CHANGE_THRESHOLD:
                    return "liquidity_change"
        
        # Default to top_tier if it passes minimum quality thresholds
        if opportunity.efficiency_score >= 6.0 and opportunity.confidence_score >= 6.0:
            return "top_tier"
        
        return "low_priority"  # Will be filtered out
    
    def determine_severity(self, alert_type: str, opportunity: ArbitrageOpportunity) -> str:
        """Determine alert severity based on type and quality"""
        
        if alert_type == "top_tier":
            combined_score = (opportunity.efficiency_score + opportunity.confidence_score) / 2
            if combined_score >= 8.5:
                return "critical"  # Immediate action required
            elif combined_score >= 7.5:
                return "warning"   # Consider trading
            else:
                return "info"      # Monitor
        
        elif alert_type == "flash":
            return "critical"  # Flash opportunities are always critical
        
        elif alert_type == "volume_anomaly":
            return "warning"   # Unusual activity worth investigating
        
        elif alert_type == "liquidity_change":
            return "info"      # Informational
        
        return "info"
    
    def create_deduplication_key(self, opportunity: ArbitrageOpportunity, alert_type: str) -> str:
        """Create deduplication key for opportunity"""
        # Key based on market ID, alert type, and core metrics
        key_data = f"{opportunity.market_id}:{alert_type}:{opportunity.spread:.3f}:{opportunity.efficiency_score:.1f}:{opportunity.confidence_score:.1f}"
        return key_data
    
    def check_cooldowns(self, opportunity: ArbitrageOpportunity, alert_type: str) -> Tuple[bool, str]:
        """Check if opportunity is within cooldown periods"""
        current_time = datetime.utcnow()
        
        # Check market cooldown (30 minutes minimum)
        market_id = opportunity.market_id
        if market_id in self.market_cooldowns:
            time_since_last = current_time - self.market_cooldowns[market_id]
            if time_since_last < timedelta(minutes=self.MARKET_COOLDOWN_MINUTES):
                remaining = timedelta(minutes=self.MARKET_COOLDOWN_MINUTES) - time_since_last
                return False, f"Market cooldown: {remaining.seconds//60} minutes remaining"
        
        # Check deduplication window (5 minutes for similar alerts)
        dedup_key = self.create_deduplication_key(opportunity, alert_type)
        if dedup_key in self.deduplication_window:
            time_since_last = current_time - self.deduplication_window[dedup_key]
            if time_since_last < timedelta(minutes=self.DEDUPLICATION_WINDOW_MINUTES):
                remaining = timedelta(minutes=self.DEDUPLICATION_WINDOW_MINUTES) - time_since_last
                return False, f"Deduplication window: {remaining.seconds//60} minutes remaining"
        
        return True, "No cooldown restrictions"
    
    def update_cooldowns(self, opportunity: ArbitrageOpportunity, alert_type: str):
        """Update cooldown periods after sending alert"""
        current_time = datetime.utcnow()
        
        # Update market cooldown
        self.market_cooldowns[opportunity.market_id] = current_time
        
        # Update deduplication window
        dedup_key = self.create_deduplication_key(opportunity, alert_type)
        self.deduplication_window[dedup_key] = current_time
    
    def create_alert(self, opportunity: ArbitrageOpportunity, 
                    historical_volume: Optional[float] = None,
                    historical_liquidity: Optional[Dict[str, float]] = None) -> Optional[ArbitrageAlert]:
        """Create arbitrage alert with priority classification"""
        
        # Classify opportunity
        alert_type = self.classify_opportunity(opportunity, historical_volume, historical_liquidity)
        
        # Skip low priority alerts
        if alert_type == "low_priority":
            logger.debug(f"Skipping low priority opportunity: {opportunity.market_name}")
            return None
        
        # Check cooldowns
        can_send, cooldown_reason = self.check_cooldowns(opportunity, alert_type)
        if not can_send:
            logger.debug(f"Cooldown active for {opportunity.market_name}: {cooldown_reason}")
            return None
        
        # Determine severity
        severity = self.determine_severity(alert_type, opportunity)
        
        # Get priority
        priority = self.ALERT_PRIORITIES.get(alert_type, 4)
        
        # Create deduplication key
        dedup_key = self.create_deduplication_key(opportunity, alert_type)
        
        # Generate alert reason
        reason = self._generate_alert_reason(alert_type, opportunity, severity)
        
        # Create alert
        alert = ArbitrageAlert(
            opportunity=opportunity,
            alert_type=alert_type,
            priority=priority,
            severity=severity,
            timestamp=datetime.utcnow(),
            deduplication_key=dedup_key,
            reason=reason
        )
        
        # Update cooldowns
        self.update_cooldowns(opportunity, alert_type)
        
        # Update stats
        self.alert_stats[alert_type] += 1
        self.alert_stats[severity] += 1
        
        # Add to history
        self.alert_history.append(alert)
        
        logger.info(f"🚨 Created {alert_type} alert for {opportunity.market_name} (Priority: {priority}, Severity: {severity})")
        
        return alert
    
    def _generate_alert_reason(self, alert_type: str, opportunity: ArbitrageOpportunity, severity: str) -> str:
        """Generate human-readable alert reason"""
        
        if alert_type == "top_tier":
            combined_score = (opportunity.efficiency_score + opportunity.confidence_score) / 2
            if severity == "critical":
                return f"🔥 CRITICAL: Top-tier arbitrage with {combined_score:.1f}/10 combined score - TRADE IMMEDIATELY"
            elif severity == "warning":
                return f"⚡ WARNING: Strong arbitrage opportunity with {combined_score:.1f}/10 combined score - CONSIDER TRADING"
            else:
                return f"📊 INFO: Quality arbitrage opportunity with {combined_score:.1f}/10 combined score - MONITOR"
        
        elif alert_type == "flash":
            time_remaining = opportunity.expires_at - datetime.utcnow()
            return f"⏰ FLASH: High spread ({opportunity.spread*100:.1f}%) closing in {time_remaining.seconds//60} minutes - ACT FAST"
        
        elif alert_type == "volume_anomaly":
            return f"📈 VOLUME ANOMALY: Unusual volume activity ({opportunity.volume_24h:,.0f} 24h volume) - INVESTIGATE"
        
        elif alert_type == "liquidity_change":
            return f"💰 LIQUIDITY CHANGE: Major liquidity depth update - MONITOR FOR OPPORTUNITIES"
        
        return f"🎯 ARBITRAGE: {opportunity.reason}"
    
    def filter_and_rank_alerts(self, opportunities: List[ArbitrageOpportunity],
                              historical_data: Optional[Dict[str, Any]] = None) -> List[ArbitrageAlert]:
        """Filter and rank arbitrage opportunities by priority"""
        
        alerts = []
        
        for opportunity in opportunities:
            # Get historical data for this market if available
            hist_volume = None
            hist_liquidity = None
            
            if historical_data and opportunity.market_id in historical_data:
                market_hist = historical_data[opportunity.market_id]
                hist_volume = market_hist.get("volume_24h")
                hist_liquidity = market_hist.get("liquidity")
            
            # Create alert
            alert = self.create_alert(opportunity, hist_volume, hist_liquidity)
            if alert:
                alerts.append(alert)
        
        # Sort by priority (1=highest), then by combined score
        alerts.sort(key=lambda x: (x.priority, -(x.opportunity.efficiency_score + x.opportunity.confidence_score)))
        
        logger.info(f"📊 Created {len(alerts)} arbitrage alerts from {len(opportunities)} opportunities")
        
        return alerts
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return {
            "total_alerts": len(self.alert_history),
            "alert_stats": dict(self.alert_stats),
            "active_cooldowns": len(self.market_cooldowns),
            "active_deduplication_keys": len(self.deduplication_window),
            "recent_alerts": [
                {
                    "market_name": alert.opportunity.market_name,
                    "alert_type": alert.alert_type,
                    "priority": alert.priority,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "reason": alert.reason
                }
                for alert in list(self.alert_history)[-10:]  # Last 10 alerts
            ]
        }
    
    def cleanup_old_cooldowns(self):
        """Clean up expired cooldown entries"""
        current_time = datetime.utcnow()
        
        # Clean market cooldowns
        expired_markets = []
        for market_id, last_alert in self.market_cooldowns.items():
            if current_time - last_alert > timedelta(minutes=self.MARKET_COOLDOWN_MINUTES):
                expired_markets.append(market_id)
        
        for market_id in expired_markets:
            del self.market_cooldowns[market_id]
        
        # Clean deduplication windows
        expired_keys = []
        for dedup_key, last_alert in self.deduplication_window.items():
            if current_time - last_alert > timedelta(minutes=self.DEDUPLICATION_WINDOW_MINUTES):
                expired_keys.append(dedup_key)
        
        for dedup_key in expired_keys:
            del self.deduplication_window[dedup_key]
        
        if expired_markets or expired_keys:
            logger.debug(f"🧹 Cleaned {len(expired_markets)} market cooldowns and {len(expired_keys)} deduplication keys")

# Example usage and testing
def test_arbitrage_alert_manager():
    """Test the arbitrage alert manager"""
    print("🎯 Arbitrage Alert Manager Test")
    print("=" * 50)
    
    # Create alert manager
    manager = ArbitrageAlertManager()
    
    # Create test opportunities
    from arbitrage.opportunity_detector import Market, create_test_markets
    from arbitrage.opportunity_detector_exact import ArbitrageDetector
    
    detector = ArbitrageDetector()
    markets = create_test_markets()
    opportunities = detector.detect_opportunities(markets)
    
    print(f"📊 Processing {len(opportunities)} opportunities through alert manager...")
    
    # Filter and rank alerts
    alerts = manager.filter_and_rank_alerts(opportunities)
    
    # Display results
    print(f"\n🚨 Generated {len(alerts)} arbitrage alerts:")
    for i, alert in enumerate(alerts):
        print(f"  {i+1}. {alert.opportunity.market_name}")
        print(f"     Type: {alert.alert_type} (Priority: {alert.priority})")
        print(f"     Severity: {alert.severity}")
        print(f"     Combined Score: {(alert.opportunity.efficiency_score + alert.opportunity.confidence_score) / 2:.1f}/10")
        print(f"     Reason: {alert.reason}")
        print()
    
    # Show stats
    stats = manager.get_alert_stats()
    print(f"📈 Alert Statistics:")
    print(f"  Total Alerts: {stats['total_alerts']}")
    print(f"  Alert Types: {stats['alert_stats']}")
    print(f"  Active Cooldowns: {stats['active_cooldowns']}")
    
    print(f"\n✅ Alert Manager Features:")
    print(f"  ✅ Priority-based classification (Top-tier > Flash > Volume > Liquidity)")
    print(f"  ✅ Quality score filtering (>= 6.0 efficiency + confidence)")
    print(f"  ✅ Market cooldowns (30 minutes minimum)")
    print(f"  ✅ Alert deduplication (5-minute window)")
    print(f"  ✅ Severity determination based on quality and type")
    print(f"  ✅ Historical data integration for anomaly detection")

if __name__ == "__main__":
    test_arbitrage_alert_manager()
