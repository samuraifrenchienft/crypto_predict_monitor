"""
Cross-Market Fee Calculator
Calculate ACTUAL profit after ALL costs for cross-market arbitrage
Filters out fake arbs (95% of "opportunities" disappear once fees are included)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("cross_market_fee_calculator")

@dataclass
class ArbProfitability:
    """Cross-market arb profitability analysis"""
    yes_platform: str
    no_platform: str
    yes_price: float
    no_price: float
    gross_cost: float
    fees_total: float
    slippage_estimate: float
    partial_fill_loss: float
    withdrawal_cost: float
    total_cost: float
    payout: float  # Always $1.00 for locked payout
    net_profit: float
    roi_percent: float
    is_profitable: bool
    min_margin_percent: float  # Recommended safety margin
    yes_liquidity: float = 0.0
    no_liquidity: float = 0.0
    liquidity_score: str = 'moderate'
    risk_factors: list = None
    confidence_level: float = 0.7
    
    def __post_init__(self):
        """Initialize defaults and calculate derived fields"""
        if self.risk_factors is None:
            self.risk_factors = []
        
        # Determine liquidity score based on total liquidity
        total_liquidity = self.yes_liquidity + self.no_liquidity
        if total_liquidity > 100000:
            self.liquidity_score = 'deep'
            self.confidence_level = 0.9
        elif total_liquidity > 20000:
            self.liquidity_score = 'moderate'
            self.confidence_level = 0.7
        else:
            self.liquidity_score = 'shallow'
            self.confidence_level = 0.5

class CrossMarketFeeCalculator:
    """
    Calculate ACTUAL profit after ALL costs
    This is the critical differentiator from "paper" arbs
    """
    
    def __init__(self):
        # Platform-specific taker fees (when you're buying)
        self.taker_fees = {
            'polymarket': 0.015,  # 1.5%
            'manifold': 0.020,    # 2.0%
            'limitless': 0.015,   # 1.5%
            'azuro_polygon': 0.025,  # 2.5%
            'azuro_gnosis': 0.025,
            'azuro_base': 0.025,
            'azuro_chiliz': 0.025,
        }
        
        # Slippage model by liquidity depth
        self.slippage_by_liquidity = {
            'deep': 0.005,      # >$100K liquidity = 0.5% slippage
            'moderate': 0.010,  # $20K-$100K = 1% slippage
            'shallow': 0.025,   # <$20K = 2.5% slippage
        }
        
        # Withdrawal fees (blockchain or platform)
        self.withdrawal_fees = {
            'polymarket': 0.001,  # ~$1 on USDC
            'manifold': 0.002,
            'limitless': 0.0015,
            'azuro_polygon': 0.002,  # Polygon gas minimal
            'azuro_gnosis': 0.001,   # Gnosis even cheaper
            'azuro_base': 0.0005,    # Base very cheap
            'azuro_chiliz': 0.002,
        }
        
        # Safety margin requirements by platform combo
        self.min_margin_threshold = 0.0025  # 0.25% minimum profit
        
        # Risk factors for analysis
        self.risk_factors = {
            'low_liquidity': 'Low liquidity may cause slippage',
            'high_fees': 'High platform fees reduce profitability',
            'deadline_risk': 'Short deadline increases execution risk',
            'platform_risk': 'Platform-specific risks (downtime, limits)',
            'gas_volatility': 'Blockchain gas fees may vary',
        }
        
        logger.info("💰 CrossMarketFeeCalculator initialized")

    def calculate_cross_market_profit(
        self,
        yes_platform: str,
        yes_price: float,
        yes_liquidity: float,
        no_platform: str,
        no_price: float,
        no_liquidity: float,
        position_size_usd: float = 1000.0
    ) -> ArbProfitability:
        """
        Calculate actual profit for cross-market arb (locked payout)
        
        Guaranteed payout structure:
        - Buy YES for $X on Platform A
        - Buy NO for $Y on Platform B
        - One leg pays $1.00 (the other pays $0)
        - Total payout = $1.00
        - Profit = $1.00 - (total_cost + all_fees)
        """
        
        # 1. TAKER FEES (buying on both sides)
        yes_fee = yes_price * self.taker_fees.get(yes_platform, 0.02)
        no_fee = no_price * self.taker_fees.get(no_platform, 0.02)
        total_taker_fees = yes_fee + no_fee
        
        # 2. SLIPPAGE (estimated by liquidity)
        yes_slippage = yes_price * self._estimate_slippage(yes_liquidity)
        no_slippage = no_price * self._estimate_slippage(no_liquidity)
        total_slippage = yes_slippage + no_slippage
        
        # 3. PARTIAL FILL RISK
        # Assume 50% chance of 1% miss (conservative)
        partial_fill_risk = (yes_price + no_price) * 0.005
        
        # 4. WITHDRAWAL/TRANSFER COSTS (if moving capital between platforms)
        withdrawal_cost = (
            self.withdrawal_fees.get(yes_platform, 0.001) +
            self.withdrawal_fees.get(no_platform, 0.001)
        )
        
        # 5. TOTAL COST
        gross_cost = yes_price + no_price
        total_fees = total_taker_fees + total_slippage + partial_fill_risk + withdrawal_cost
        total_cost = gross_cost + total_fees
        
        # 6. PAYOUT & PROFIT
        payout = 1.00  # Locked payout (one leg wins $1, other is $0)
        net_profit = payout - total_cost
        roi_percent = (net_profit / (yes_price + no_price)) * 100
        
        # 7. PROFITABILITY CHECK
        is_profitable = (
            net_profit > 0 and
            roi_percent >= (self.min_margin_threshold * 100)
        )
        
        # 8. MINIMUM SAFETY MARGIN
        # Recommended: add 0.25% buffer for execution risk
        min_margin_percent = self.min_margin_threshold * 100
        
        # 9. RISK ANALYSIS
        risk_factors = self._analyze_risk_factors(
            yes_platform, no_platform, yes_liquidity, no_liquidity
        )
        
        logger.debug(
            f"Arb Analysis: {yes_platform} YES ${yes_price:.4f} + "
            f"{no_platform} NO ${no_price:.4f} = ${total_cost:.4f} cost, "
            f"${net_profit:.4f} profit ({roi_percent:.2f}%), "
            f"Viable: {is_profitable}"
        )
        
        return ArbProfitability(
            yes_platform=yes_platform,
            no_platform=no_platform,
            yes_price=yes_price,
            no_price=no_price,
            gross_cost=gross_cost,
            fees_total=total_taker_fees,
            slippage_estimate=total_slippage,
            partial_fill_loss=partial_fill_risk,
            withdrawal_cost=withdrawal_cost,
            total_cost=total_cost,
            payout=payout,
            net_profit=net_profit,
            roi_percent=roi_percent,
            is_profitable=is_profitable,
            min_margin_percent=min_margin_percent,
            yes_liquidity=yes_liquidity,
            no_liquidity=no_liquidity,
            risk_factors=risk_factors
        )
    
    def _estimate_slippage(self, liquidity: float) -> float:
        """Estimate slippage based on order book depth"""
        if liquidity > 100000:
            return self.slippage_by_liquidity['deep']
        elif liquidity > 20000:
            return self.slippage_by_liquidity['moderate']
        else:
            return self.slippage_by_liquidity['shallow']
    
    def _analyze_risk_factors(
        self, 
        yes_platform: str, 
        no_platform: str, 
        yes_liquidity: float, 
        no_liquidity: float
    ) -> list[str]:
        """Analyze risk factors for the arbitrage opportunity"""
        risks = []
        
        # Liquidity risks
        if yes_liquidity < 20000 or no_liquidity < 20000:
            risks.append(self.risk_factors['low_liquidity'])
        
        # Fee risks
        yes_fee = self.taker_fees.get(yes_platform, 0.02)
        no_fee = self.taker_fees.get(no_platform, 0.02)
        if yes_fee > 0.02 or no_fee > 0.02:
            risks.append(self.risk_factors['high_fees'])
        
        # Platform-specific risks
        if 'azuro' in yes_platform or 'azuro' in no_platform:
            risks.append(self.risk_factors['gas_volatility'])
        
        # New platform risks
        if yes_platform not in ['polymarket', 'manifold'] or no_platform not in ['polymarket', 'manifold']:
            risks.append(self.risk_factors['platform_risk'])
        
        return risks
    
    def analyze_opportunity_batch(
        self, 
        opportunities: list[Dict]
    ) -> Tuple[list[ArbProfitability], Dict[str, any]]:
        """
        Analyze multiple opportunities and return statistics
        
        Returns:
            - List of profitability analyses
            - Statistics about the batch
        """
        profitable_opps = []
        total_analyzed = 0
        profitable_count = 0
        filtered_by_fees = 0
        
        for opp in opportunities:
            total_analyzed += 1
            
            analysis = self.calculate_cross_market_profit(
                yes_platform=opp['yes_platform'],
                yes_price=opp['yes_price'],
                yes_liquidity=opp['yes_liquidity'],
                no_platform=opp['no_platform'],
                no_price=opp['no_price'],
                no_liquidity=opp['no_liquidity']
            )
            
            profitable_opps.append(analysis)
            
            if analysis.is_profitable:
                profitable_count += 1
            else:
                filtered_by_fees += 1
        
        # Calculate statistics
        stats = {
            'total_analyzed': total_analyzed,
            'profitable_count': profitable_count,
            'filtered_by_fees': filtered_by_fees,
            'filter_rate': filtered_by_fees / total_analyzed if total_analyzed > 0 else 0,
            'average_roi': sum(opp.roi_percent for opp in profitable_opps) / len(profitable_opps) if profitable_opps else 0,
            'best_opportunity': max(profitable_opps, key=lambda x: x.roi_percent) if profitable_opps else None
        }
        
        logger.info(f"📊 Batch Analysis: {profitable_count}/{total_analyzed} profitable "
                   f"({(profitable_count/total_analyzed)*100:.1f}%), "
                   f"{filtered_by_fees} filtered by fees")
        
        return profitable_opps, stats
    
    def get_platform_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all platform costs"""
        summary = {}
        
        for platform in self.taker_fees.keys():
            summary[platform] = {
                'taker_fee': self.taker_fees[platform],
                'withdrawal_fee': self.withdrawal_fees.get(platform, 0.001),
                'total_fee_rate': self.taker_fees[platform] + self.withdrawal_fees.get(platform, 0.001)
            }
        
        return summary

# Test function
def test_cross_market_fee_calculator():
    """Test the fee calculator with realistic scenarios"""
    print("💰 Testing Cross-Market Fee Calculator")
    print("=" * 60)
    
    calculator = CrossMarketFeeCalculator()
    
    # Test scenarios
    test_scenarios = [
        # Scenario 1: Looks profitable on paper but loses money after fees
        {
            'name': 'Paper Profit - Actual Loss',
            'yes_platform': 'polymarket',
            'yes_price': 0.40,
            'yes_liquidity': 50000,
            'no_platform': 'manifold',
            'no_price': 0.62,
            'no_liquidity': 30000,
            'expected_profitable': False
        },
        # Scenario 2: Actually profitable after fees
        {
            'name': 'Real Profit After Fees',
            'yes_platform': 'polymarket',
            'yes_price': 0.38,
            'yes_liquidity': 80000,
            'no_platform': 'limitless',
            'no_price': 0.59,
            'no_liquidity': 60000,
            'expected_profitable': True
        },
        # Scenario 3: High fees eliminate profit
        {
            'name': 'High Fee Scenario',
            'yes_platform': 'azuro_polygon',
            'yes_price': 0.39,
            'yes_liquidity': 15000,
            'no_platform': 'manifold',
            'no_price': 0.61,
            'no_liquidity': 25000,
            'expected_profitable': False
        },
        # Scenario 4: Deep liquidity scenario
        {
            'name': 'Deep Liquidity Profit',
            'yes_platform': 'polymarket',
            'yes_price': 0.42,
            'yes_liquidity': 150000,
            'no_platform': 'limitless',
            'no_price': 0.55,
            'no_liquidity': 120000,
            'expected_profitable': True
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\n📊 {scenario['name']}")
        print("-" * 40)
        
        analysis = calculator.calculate_cross_market_profit(
            yes_platform=scenario['yes_platform'],
            yes_price=scenario['yes_price'],
            yes_liquidity=scenario['yes_liquidity'],
            no_platform=scenario['no_platform'],
            no_price=scenario['no_price'],
            no_liquidity=scenario['no_liquidity']
        )
        
        print(f"   YES: {analysis.yes_platform} @ ${analysis.yes_price:.4f}")
        print(f"   NO:  {analysis.no_platform} @ ${analysis.no_price:.4f}")
        print(f"   Gross Cost: ${analysis.gross_cost:.4f}")
        print(f"   Taker Fees: ${analysis.fees_total:.4f}")
        print(f"   Slippage: ${analysis.slippage_estimate:.4f}")
        print(f"   Partial Fill: ${analysis.partial_fill_loss:.4f}")
        print(f"   Withdrawal: ${analysis.withdrawal_cost:.4f}")
        print(f"   Total Cost: ${analysis.total_cost:.4f}")
        print(f"   Net Profit: ${analysis.net_profit:.4f}")
        print(f"   ROI: {analysis.roi_percent:.2f}%")
        print(f"   Profitable: {analysis.is_profitable}")
        print(f"   Liquidity: {analysis.liquidity_score}")
        print(f"   Risk Factors: {len(analysis.risk_factors)}")
        
        results.append(analysis)
        
        # Verify expectation
        if analysis.is_profitable == scenario['expected_profitable']:
            print(f"   ✅ Expected result: {scenario['expected_profitable']}")
        else:
            print(f"   ❌ Unexpected result! Expected: {scenario['expected_profitable']}")
    
    # Batch analysis test
    print(f"\n📈 BATCH ANALYSIS TEST")
    print("=" * 40)
    
    batch_opportunities = [
        {
            'yes_platform': 'polymarket', 'yes_price': 0.40, 'yes_liquidity': 50000,
            'no_platform': 'manifold', 'no_price': 0.62, 'no_liquidity': 30000
        },
        {
            'yes_platform': 'polymarket', 'yes_price': 0.38, 'yes_liquidity': 80000,
            'no_platform': 'limitless', 'no_price': 0.59, 'no_liquidity': 60000
        },
        {
            'yes_platform': 'azuro_polygon', 'yes_price': 0.39, 'yes_liquidity': 15000,
            'no_platform': 'manifold', 'no_price': 0.61, 'no_liquidity': 25000
        }
    ]
    
    batch_results, batch_stats = calculator.analyze_opportunity_batch(batch_opportunities)
    
    print(f"Total Analyzed: {batch_stats['total_analyzed']}")
    print(f"Profitable: {batch_stats['profitable_count']}")
    print(f"Filtered by Fees: {batch_stats['filtered_by_fees']}")
    print(f"Filter Rate: {batch_stats['filter_rate']*100:.1f}%")
    print(f"Average ROI: {batch_stats['average_roi']:.2f}%")
    
    if batch_stats['best_opportunity']:
        best = batch_stats['best_opportunity']
        print(f"Best Opportunity: {best.yes_platform}+{best.no_platform} @ {best.roi_percent:.2f}% ROI")
    
    # Platform summary
    print(f"\n🏢 PLATFORM COST SUMMARY")
    print("=" * 40)
    
    platform_summary = calculator.get_platform_summary()
    for platform, costs in platform_summary.items():
        print(f"{platform}:")
        print(f"  Taker Fee: {costs['taker_fee']*100:.1f}%")
        print(f"  Withdrawal: {costs['withdrawal_fee']*100:.2f}%")
        print(f"  Total Rate: {costs['total_fee_rate']*100:.1f}%")
    
    print(f"\n🎉 Fee Calculator Test Completed!")
    
    # Summary statistics
    profitable_count = len([r for r in results if r.is_profitable])
    print(f"\n📊 SUMMARY:")
    print(f"  Scenarios Tested: {len(results)}")
    print(f"  Actually Profitable: {profitable_count}")
    print(f"  Filtered by Fees: {len(results) - profitable_count}")
    print(f"  Filter Rate: {((len(results) - profitable_count) / len(results)) * 100:.1f}%")
    
    return results

if __name__ == "__main__":
    test_cross_market_fee_calculator()
