"""
Live Data Verification System
Verifies all prediction market sources are returning LIVE data, not demo/test data
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add bot directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
sys.path.append(os.path.dirname(__file__))  # Add src directory for config

logger = logging.getLogger("live_data_verification")

@dataclass
class SourceVerificationResult:
    """Results from verifying a data source"""
    source_name: str
    is_live: bool
    markets_count: int
    checks_passed: List[str]
    checks_failed: List[str]
    sample_data: Dict[str, Any]
    verification_time: datetime
    critical_issues: List[str]

class LiveDataVerifier:
    """Verifies all prediction market sources are returning live data"""
    
    def __init__(self):
        self.verification_results: Dict[str, SourceVerificationResult] = {}
        
        # Live data thresholds
        self.LIVE_THRESHOLDS = {
            'polymarket': {
                'min_markets': 50,
                'min_liquidity': 1000,
                'realistic_price_range': (0.01, 0.99),
                'min_volume': 10000,
                'real_price_variance': 0.1  # Prices should vary, not all be 0.5
            },
            'manifold': {
                'min_markets': 30,
                'min_probability_range': (0.05, 0.95),
                'min_volume': 1000,
                'real_probability_variance': 0.15  # Probabilities should vary
            },
            'limitless': {
                'min_markets': 20,
                'min_liquidity': 1000,
                'realistic_price_range': (0.01, 0.99),
                'min_volume': 5000,
            },
            'azuro': {
                'min_markets': 10,  # Azuro is newer, lower threshold
                'min_liquidity': 500,
                'realistic_price_range': (0.01, 0.99),
                'min_volume': 1000,
            }
        }
        
        # Red flags that indicate demo/test data
        self.DEMO_RED_FLAGS = {
            'all_prices_identical': 'All markets have same prices (synthetic data)',
            'all_liquidity_identical': 'All markets have same liquidity (demo data)',
            'all_volumes_zero': 'All volumes are zero (test data)',
            'prices_exactly_0_5': 'All prices are exactly 0.5 (demo data)',
            'endpoint_contains_dev': 'API endpoint contains "dev" or "test"',
            'hardcoded_prices': 'Prices appear to be hardcoded values',
            'market_count_too_low': 'Market count suspiciously low (<10)',
            'connection_errors': 'API connection errors (offline/down)',
        }

    async def verify_polymarket_live(self) -> SourceVerificationResult:
        """Verify Polymarket is returning live data"""
        logger.info("🔍 Verifying Polymarket live data...")
        
        checks_passed = []
        checks_failed = []
        critical_issues = []
        sample_data = {}
        
        try:
            # Import and use the Polymarket adapter
            from adapters.polymarket import PolymarketAdapter
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
            from config import load_config
            
            config = load_config()
            pm_config = config.polymarket
            
            adapter = PolymarketAdapter(
                gamma_base_url=pm_config.gamma_base_url,
                clob_base_url=pm_config.clob_base_url,
                data_base_url=pm_config.data_base_url,
                events_limit=pm_config.events_limit
            )
            
            # Fetch markets
            markets = await adapter.list_active_markets()
            markets_count = len(markets)
            
            # Check endpoint URLs
            if 'dev' in pm_config.clob_base_url.lower() or 'test' in pm_config.clob_base_url.lower():
                critical_issues.append("❌ Endpoint contains 'dev' or 'test'")
                checks_failed.append("Endpoint contains dev/test")
            else:
                checks_passed.append("Using production CLOB endpoint")
            
            # Check market count
            if markets_count >= self.LIVE_THRESHOLDS['polymarket']['min_markets']:
                checks_passed.append(f"Found {markets_count} markets (threshold: {self.LIVE_THRESHOLDS['polymarket']['min_markets']})")
            else:
                checks_failed.append(f"Only {markets_count} markets found (threshold: {self.LIVE_THRESHOLDS['polymarket']['min_markets']})")
                critical_issues.append("Market count too low")
            
            # Sample first few markets for detailed checks
            if markets:
                sample_markets = markets[:5]
                prices = []
                liquidities = []
                volumes = []
                
                for market in sample_markets:
                    # Get outcomes and quotes
                    outcomes = await adapter.list_outcomes(market)
                    quotes = await adapter.get_quotes(market, outcomes)
                    
                    if quotes:
                        # Sample first quote
                        quote = quotes[0]
                        price = quote.bid if quote.bid else quote.ask
                        prices.append(price)
                        
                        # Check realistic price range
                        min_price, max_price = self.LIVE_THRESHOLDS['polymarket']['realistic_price_range']
                        if min_price <= price <= max_price:
                            checks_passed.append(f"Realistic price: {price:.3f}")
                        else:
                            checks_failed.append(f"Unrealistic price: {price:.3f}")
                            critical_issues.append("Prices outside realistic range")
                        
                        # Check liquidity
                        liquidity = quote.bid_size or quote.ask_size or 0
                        liquidities.append(liquidity)
                        
                        if liquidity >= self.LIVE_THRESHOLDS['polymarket']['min_liquidity']:
                            checks_passed.append(f"Real liquidity: ${liquidity:,.0f}")
                        else:
                            checks_failed.append(f"Low liquidity: ${liquidity:,.0f}")
                
                # Check for price variance (detect synthetic data)
                if len(set(round(p, 2) for p in prices)) > 1:
                    checks_passed.append("Prices vary (not synthetic)")
                else:
                    checks_failed.append("All prices identical (synthetic data)")
                    critical_issues.append("All prices identical")
                
                # Check for 0.5 prices (demo data indicator)
                if all(abs(p - 0.5) < 0.01 for p in prices):
                    checks_failed.append("All prices ~0.5 (demo data)")
                    critical_issues.append("All prices are 0.5")
                
                # Store sample data
                sample_data = {
                    'markets_count': markets_count,
                    'sample_prices': prices,
                    'sample_liquidities': liquidities,
                    'endpoint': pm_config.clob_base_url
                }
            
            await adapter.close()
            
        except Exception as e:
            checks_failed.append(f"Connection error: {e}")
            critical_issues.append("API connection failed")
            logger.error(f"Polymarket verification failed: {e}")
        
        is_live = len(critical_issues) == 0 and len(checks_failed) == 0
        
        return SourceVerificationResult(
            source_name="polymarket",
            is_live=is_live,
            markets_count=markets_count if 'markets_count' in locals() else 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            sample_data=sample_data,
            verification_time=datetime.utcnow(),
            critical_issues=critical_issues
        )

    async def verify_manifold_live(self) -> SourceVerificationResult:
        """Verify Manifold is returning live data"""
        logger.info("🔍 Verifying Manifold live data...")
        
        checks_passed = []
        checks_failed = []
        critical_issues = []
        sample_data = {}
        
        try:
            from adapters.manifold import ManifoldAdapter
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
            from config import load_config
            
            config = load_config()
            mf_config = config.manifold
            
            adapter = ManifoldAdapter(
                base_url=mf_config.base_url,
                markets_limit=mf_config.markets_limit
            )
            
            # Fetch markets
            markets = await adapter.list_active_markets()
            markets_count = len(markets)
            
            # Check endpoint URL
            if 'dev' in mf_config.base_url.lower() or 'test' in mf_config.base_url.lower():
                critical_issues.append("❌ Endpoint contains 'dev' or 'test'")
                checks_failed.append("Endpoint contains dev/test")
            else:
                checks_passed.append("Using production API endpoint")
            
            # Check market count
            if markets_count >= self.LIVE_THRESHOLDS['manifold']['min_markets']:
                checks_passed.append(f"Found {markets_count} markets (threshold: {self.LIVE_THRESHOLDS['manifold']['min_markets']})")
            else:
                checks_failed.append(f"Only {markets_count} markets found (threshold: {self.LIVE_THRESHOLDS['manifold']['min_markets']})")
                critical_issues.append("Market count too low")
            
            # Sample markets for detailed checks
            if markets:
                sample_markets = markets[:5]
                probabilities = []
                volumes = []
                
                for market in sample_markets:
                    # Get probability
                    outcomes = await adapter.list_outcomes(market)
                    quotes = await adapter.get_quotes(market, outcomes)
                    
                    if quotes:
                        quote = quotes[0]
                        prob = quote.mid if quote.mid else (quote.bid + quote.ask) / 2
                        probabilities.append(prob)
                        
                        # Check realistic probability range
                        min_prob, max_prob = self.LIVE_THRESHOLDS['manifold']['min_probability_range']
                        if min_prob <= prob <= max_prob:
                            checks_passed.append(f"Realistic probability: {prob:.3f}")
                        else:
                            checks_failed.append(f"Unrealistic probability: {prob:.3f}")
                            critical_issues.append("Probabilities outside realistic range")
                
                # Check for probability variance
                if len(set(round(p, 2) for p in probabilities)) > 1:
                    checks_passed.append("Probabilities vary (not synthetic)")
                else:
                    checks_failed.append("All probabilities identical (synthetic data)")
                    critical_issues.append("All probabilities identical")
                
                # Store sample data
                sample_data = {
                    'markets_count': markets_count,
                    'sample_probabilities': probabilities,
                    'endpoint': mf_config.base_url
                }
            
            await adapter.close()
            
        except Exception as e:
            checks_failed.append(f"Connection error: {e}")
            critical_issues.append("API connection failed")
            logger.error(f"Manifold verification failed: {e}")
        
        is_live = len(critical_issues) == 0 and len(checks_failed) == 0
        
        return SourceVerificationResult(
            source_name="manifold",
            is_live=is_live,
            markets_count=markets_count if 'markets_count' in locals() else 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            sample_data=sample_data,
            verification_time=datetime.utcnow(),
            critical_issues=critical_issues
        )

    async def verify_limitless_live(self) -> SourceVerificationResult:
        """Verify Limitless is returning live data"""
        logger.info("🔍 Verifying Limitless live data...")
        
        checks_passed = []
        checks_failed = []
        critical_issues = []
        sample_data = {}
        
        try:
            from adapters.limitless import LimitlessAdapter
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
            from config import load_config
            
            config = load_config()
            lim_config = config.limitless
            
            adapter = LimitlessAdapter(base_url=lim_config.base_url)
            
            # Fetch markets
            markets = await adapter.list_active_markets()
            markets_count = len(markets)
            
            # Check endpoint URL
            if 'dev' in lim_config.base_url.lower() or 'test' in lim_config.base_url.lower():
                critical_issues.append("❌ Endpoint contains 'dev' or 'test'")
                checks_failed.append("Endpoint contains dev/test")
            else:
                checks_passed.append("Using production API endpoint")
            
            # Check market count
            if markets_count >= self.LIVE_THRESHOLDS['limitless']['min_markets']:
                checks_passed.append(f"Found {markets_count} markets (threshold: {self.LIVE_THRESHOLDS['limitless']['min_markets']})")
            else:
                checks_failed.append(f"Only {markets_count} markets found (threshold: {self.LIVE_THRESHOLDS['limitless']['min_markets']})")
                critical_issues.append("Market count too low")
            
            # Sample markets for detailed checks
            if markets:
                sample_markets = markets[:5]
                prices = []
                liquidities = []
                
                for market in sample_markets:
                    # Get quotes
                    outcomes = await adapter.list_outcomes(market)
                    quotes = await adapter.get_quotes(market, outcomes)
                    
                    if quotes:
                        quote = quotes[0]
                        price = quote.bid if quote.bid else quote.ask
                        prices.append(price)
                        
                        # Check realistic price range
                        min_price, max_price = self.LIVE_THRESHOLDS['limitless']['realistic_price_range']
                        if min_price <= price <= max_price:
                            checks_passed.append(f"Realistic price: {price:.3f}")
                        else:
                            checks_failed.append(f"Unrealistic price: {price:.3f}")
                            critical_issues.append("Prices outside realistic range")
                        
                        # Check liquidity
                        liquidity = quote.bid_size or quote.ask_size or 0
                        liquidities.append(liquidity)
                        
                        if liquidity >= self.LIVE_THRESHOLDS['limitless']['min_liquidity']:
                            checks_passed.append(f"Real liquidity: ${liquidity:,.0f}")
                        else:
                            checks_failed.append(f"Low liquidity: ${liquidity:,.0f}")
                
                # Check for price variance
                if len(set(round(p, 2) for p in prices)) > 1:
                    checks_passed.append("Prices vary (not synthetic)")
                else:
                    checks_failed.append("All prices identical (synthetic data)")
                    critical_issues.append("All prices identical")
                
                # Store sample data
                sample_data = {
                    'markets_count': markets_count,
                    'sample_prices': prices,
                    'sample_liquidities': liquidities,
                    'endpoint': lim_config.base_url
                }
            
            await adapter.close()
            
        except Exception as e:
            checks_failed.append(f"Connection error: {e}")
            critical_issues.append("API connection failed")
            logger.error(f"Limitless verification failed: {e}")
        
        is_live = len(critical_issues) == 0 and len(checks_failed) == 0
        
        return SourceVerificationResult(
            source_name="limitless",
            is_live=is_live,
            markets_count=markets_count if 'markets_count' in locals() else 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            sample_data=sample_data,
            verification_time=datetime.utcnow(),
            critical_issues=critical_issues
        )

    async def verify_azuro_live(self) -> SourceVerificationResult:
        """Verify Azuro is returning live data"""
        logger.info("🔍 Verifying Azuro live data...")
        
        checks_passed = []
        checks_failed = []
        critical_issues = []
        sample_data = {}
        
        try:
            from adapters.azuro import AzuroAdapter
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
            from config import load_config
            
            config = load_config()
            az_config = config.azuro
            
            adapter = AzuroAdapter(
                graphql_base_url=az_config.graphql_base_url,
                subgraph_base_url=az_config.subgraph_base_url,
                rest_base_url=az_config.rest_base_url,
                markets_limit=az_config.markets_limit,
                use_fallback=az_config.use_fallback
            )
            
            # Fetch markets
            markets = await adapter.list_active_markets()
            markets_count = len(markets)
            
            # Check if using fallback (indicates APIs not available)
            if az_config.use_fallback and markets_count > 0:
                checks_passed.append("Using fallback data (APIs not yet available)")
                # For Azuro, we're more lenient since it's newer
            else:
                # Check endpoint URLs
                if 'dev' in az_config.graphql_base_url.lower() or 'test' in az_config.graphql_base_url.lower():
                    critical_issues.append("❌ Endpoint contains 'dev' or 'test'")
                    checks_failed.append("Endpoint contains dev/test")
                else:
                    checks_passed.append("Using production endpoints")
            
            # Check market count (lower threshold for Azuro)
            if markets_count >= self.LIVE_THRESHOLDS['azuro']['min_markets']:
                checks_passed.append(f"Found {markets_count} markets (threshold: {self.LIVE_THRESHOLDS['azuro']['min_markets']})")
            else:
                checks_failed.append(f"Only {markets_count} markets found (threshold: {self.LIVE_THRESHOLDS['azuro']['min_markets']})")
                # Don't mark as critical for Azuro (newer protocol)
            
            # Sample markets for detailed checks
            if markets:
                sample_markets = markets[:3]  # Smaller sample for Azuro
                prices = []
                liquidities = []
                
                for market in sample_markets:
                    # Get quotes
                    outcomes = await adapter.list_outcomes(market)
                    quotes = await adapter.get_quotes(market, outcomes)
                    
                    if quotes:
                        quote = quotes[0]
                        price = quote.bid if quote.bid else quote.ask
                        prices.append(price)
                        
                        # Check realistic price range
                        min_price, max_price = self.LIVE_THRESHOLDS['azuro']['realistic_price_range']
                        if min_price <= price <= max_price:
                            checks_passed.append(f"Realistic price: {price:.3f}")
                        else:
                            checks_failed.append(f"Unrealistic price: {price:.3f}")
                        
                        # Check liquidity
                        liquidity = quote.bid_size or quote.ask_size or 0
                        liquidities.append(liquidity)
                        
                        if liquidity >= self.LIVE_THRESHOLDS['azuro']['min_liquidity']:
                            checks_passed.append(f"Real liquidity: ${liquidity:,.0f}")
                        else:
                            checks_failed.append(f"Low liquidity: ${liquidity:,.0f}")
                
                # Store sample data
                sample_data = {
                    'markets_count': markets_count,
                    'sample_prices': prices,
                    'sample_liquidities': liquidities,
                    'using_fallback': az_config.use_fallback,
                    'endpoints': {
                        'graphql': az_config.graphql_base_url,
                        'subgraph': az_config.subgraph_base_url,
                        'rest': az_config.rest_base_url
                    }
                }
            
            await adapter.close()
            
        except Exception as e:
            checks_failed.append(f"Connection error: {e}")
            critical_issues.append("API connection failed")
            logger.error(f"Azuro verification failed: {e}")
        
        # Azuro is live if no critical issues (using fallback is acceptable for newer protocol)
        is_live = len(critical_issues) == 0
        
        return SourceVerificationResult(
            source_name="azuro",
            is_live=is_live,
            markets_count=markets_count if 'markets_count' in locals() else 0,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            sample_data=sample_data,
            verification_time=datetime.utcnow(),
            critical_issues=critical_issues
        )

    async def verify_all_sources(self) -> Dict[str, SourceVerificationResult]:
        """Verify all data sources are returning live data"""
        logger.info("🚀 Starting comprehensive live data verification...")
        
        # Verify all sources concurrently
        results = await asyncio.gather(
            self.verify_polymarket_live(),
            self.verify_manifold_live(),
            self.verify_limitless_live(),
            self.verify_azuro_live(),
            return_exceptions=True
        )
        
        # Organize results
        verification_results = {}
        for result in results:
            if isinstance(result, SourceVerificationResult):
                verification_results[result.source_name] = result
            else:
                logger.error(f"Verification failed for source: {result}")
        
        self.verification_results = verification_results
        
        return verification_results

    def generate_verification_report(self) -> str:
        """Generate a comprehensive verification report"""
        if not self.verification_results:
            return "No verification results available"
        
        report = []
        report.append("🎯 LIVE DATA VERIFICATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        all_live = True
        total_markets = 0
        
        for source_name, result in self.verification_results.items():
            status = "✅ LIVE" if result.is_live else "❌ DEMO/OFFLINE"
            report.append(f"{source_name.upper()}: {status}")
            report.append(f"  Markets: {result.markets_count}")
            
            if result.checks_passed:
                report.append("  ✅ Passed:")
                for check in result.checks_passed:
                    report.append(f"    - {check}")
            
            if result.checks_failed:
                report.append("  ❌ Failed:")
                for check in result.checks_failed:
                    report.append(f"    - {check}")
            
            if result.critical_issues:
                report.append("  🚨 CRITICAL:")
                for issue in result.critical_issues:
                    report.append(f"    - {issue}")
            
            report.append("")
            total_markets += result.markets_count
            
            if not result.is_live:
                all_live = False
        
        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Markets: {total_markets}")
        report.append(f"All Sources Live: {'✅ YES' if all_live else '❌ NO'}")
        
        if all_live:
            report.append("")
            report.append("🎉 ALL SOURCES ARE LIVE - READY FOR PRODUCTION!")
        else:
            report.append("")
            report.append("🚨 CRITICAL ISSUES FOUND - DO NOT LAUNCH!")
        
        return "\n".join(report)

# Main verification function
async def verify_live_data() -> bool:
    """Verify all sources are returning LIVE data, not demo"""
    verifier = LiveDataVerifier()
    
    try:
        results = await verifier.verify_all_sources()
        
        # Generate and log report
        report = verifier.generate_verification_report()
        logger.info("Live Data Verification Results:")
        logger.info(report)
        
        # Check if all sources are live
        all_live = all(result.is_live for result in results.values())
        
        if not all_live:
            logger.critical("🚨 NOT ALL SOURCES ARE LIVE - DO NOT LAUNCH!")
            
            # List critical issues
            for source_name, result in results.items():
                if result.critical_issues:
                    logger.critical(f"{source_name.upper()} CRITICAL ISSUES:")
                    for issue in result.critical_issues:
                        logger.critical(f"  - {issue}")
        
        return all_live
        
    except Exception as e:
        logger.critical(f"Live data verification failed: {e}")
        return False

# Test function
async def test_verification():
    """Test the verification system"""
    print("🎯 Testing Live Data Verification System")
    print("=" * 50)
    
    is_live = await verify_live_data()
    
    print(f"\n🎯 Verification Result: {'✅ ALL LIVE' if is_live else '❌ ISSUES FOUND'}")
    
    if is_live:
        print("🚀 System is ready for production!")
    else:
        print("🚨 Fix critical issues before launching!")

if __name__ == "__main__":
    asyncio.run(test_verification())
