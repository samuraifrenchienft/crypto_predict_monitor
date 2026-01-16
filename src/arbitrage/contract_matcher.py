"""
Contract Matcher for Cross-Market Arbitrage
Ensures markets are actually the same event before trading
Prevents blown trades from different resolution sources, deadlines, or criteria
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

# Add path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'fetchers'))

from market_normalizer import NormalizedMarket

logger = logging.getLogger("contract_matcher")

@dataclass
class MatchedMarketPair:
    """Two markets confirmed as same event"""
    market_a: NormalizedMarket
    market_b: NormalizedMarket
    match_score: float  # 0-1 (confidence)
    is_safe: bool  # True only if match_score >= 0.95
    match_details: Dict[str, float]  # Individual component scores
    
    def __post_init__(self):
        """Calculate is_safe based on match_score"""
        self.is_safe = self.match_score >= 0.95

class ContractMatcher:
    """
    Ensure markets are actually the same event
    
    CRITICAL: Prevents blown trades from:
    - Different resolution sources
    - Different deadline times
    - Different criteria (> vs >=, etc)
    - Timezone mismatches
    """
    
    def __init__(self, min_match_score: float = 0.95):
        self.min_match_score = min_match_score
        self.matched_pairs_history = []
        
        # Known resolution sources
        self.resolution_sources = [
            'coinbase', 'coingecko', 'coinmarketcap', 'ap', 'reuters', 
            'bbc', 'espn', 'bloomberg', 'yahoo finance', 'tradingview'
        ]
        
        # Common text patterns for normalization
        self.text_replacements = {
            'end of year': 'eoy',
            'end of day': 'eod',
            'end of month': 'eom',
            'beginning of year': 'boy',
            'beginning of day': 'bod',
            'by ': '',
            'will ': '',
            'hits': 'reaches',
            'price': '',
            'cost': '',
            'value': '',
            'market cap': 'marketcap',
            'market capitalization': 'marketcap',
            '>': 'above',
            '<': 'below',
            '>=': 'above',
            '<=': 'below',
        }
        
        logger.info(f"🔍 ContractMatcher initialized (min_score={min_match_score})")

    async def find_all_matched_pairs(
        self,
        markets: List[NormalizedMarket]
    ) -> List[MatchedMarketPair]:
        """
        Find all markets that are definitely the same event
        
        Returns only high-confidence matches (95%+)
        Discards ambiguous markets
        """
        logger.info(f"🔍 Searching for matched pairs in {len(markets)} markets...")
        
        matched_pairs = []
        
        # Group by normalized event name
        event_groups = self._group_by_normalized_name(markets)
        
        logger.info(f"📊 Found {len(event_groups)} unique event groups")
        
        for event_name, market_list in event_groups.items():
            if len(market_list) < 2:
                continue  # Need at least 2 platforms for cross-market arb
            
            logger.info(f"🔍 Analyzing group '{event_name}' with {len(market_list)} markets")
            for market in market_list:
                logger.info(f"   - {market.source}: {market.name}")
            
            # Check all pairs within group
            for i, market_a in enumerate(market_list):
                for market_b in market_list[i+1:]:
                    
                    match_score, match_details = self._calculate_match_score(market_a, market_b)
                    
                    logger.info(f"🔍 Comparing {market_a.source} + {market_b.source}: {match_score:.3f}")
                    logger.info(f"   Details: {match_details}")
                    
                    if match_score >= self.min_match_score:
                        pair = MatchedMarketPair(
                            market_a=market_a,
                            market_b=market_b,
                            match_score=match_score,
                            is_safe=True,
                            match_details=match_details
                        )
                        matched_pairs.append(pair)
                        
                        logger.info(f"✅ MATCHED PAIR: {market_a.source} + {market_b.source}")
                        logger.info(f"   Event: {event_name}")
                        logger.info(f"   Score: {match_score:.3f} (title:{match_details['title']:.2f}, "
                                  f"resolution:{match_details['resolution']:.2f}, "
                                  f"deadline:{match_details['deadline']:.2f}, "
                                  f"criteria:{match_details['criteria']:.2f})")
                    else:
                        logger.info(f"❌ REJECTED PAIR: {market_a.source} + {market_b.source} "
                                   f"(score: {match_score:.3f})")
        
        # Store in history
        self.matched_pairs_history.extend(matched_pairs)
        
        logger.info(f"✅ Found {len(matched_pairs)} safe matched pairs from {len(markets)} markets")
        return matched_pairs

    def _calculate_match_score(
        self, 
        market_a: NormalizedMarket, 
        market_b: NormalizedMarket
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate confidence that markets are identical (0-1)
        
        Factors:
        - Title/name match (40%)
        - Resolution source match (30%)
        - Deadline match (20%)
        - Criteria match (10%)
        """
        
        scores = {
            'title': self._score_title_match(market_a.name, market_b.name) * 0.40,
            'resolution': self._score_resolution_source(market_a, market_b) * 0.30,
            'deadline': self._score_deadline_match(market_a.expires_at, market_b.expires_at) * 0.20,
            'criteria': self._score_criteria_match(market_a.source_data, market_b.source_data) * 0.10,
        }
        
        total_score = sum(scores.values())
        
        return total_score, scores

    def _score_title_match(self, title_a: str, title_b: str) -> float:
        """Fuzzy match market names"""
        normalized_a = self._normalize_text(title_a)
        normalized_b = self._normalize_text(title_b)
        
        ratio = SequenceMatcher(None, normalized_a, normalized_b).ratio()
        
        # 0-1 scale (only high matches count)
        # Use sharper cutoff to avoid false positives
        adjusted_score = max(0, ratio - 0.5) * 2
        
        logger.debug(f"📝 Title match: '{normalized_a}' vs '{normalized_b}' = {ratio:.3f} -> {adjusted_score:.3f}")
        
        return adjusted_score

    def _score_resolution_source(self, market_a: NormalizedMarket, market_b: NormalizedMarket) -> float:
        """
        Check if both use same resolution authority
        
        Examples of MISMATCH:
        - Coinbase feed vs CoinMarketCap
        - AP News vs Reuters
        """
        
        # Extract resolution source from descriptions
        source_a = self._extract_resolution_source(market_a.source_data)
        source_b = self._extract_resolution_source(market_b.source_data)
        
        logger.debug(f"📡 Resolution sources: '{source_a}' vs '{source_b}'")
        
        # If either is unknown, penalize
        if not source_a or not source_b:
            return 0.5  # Uncertain
        
        # Exact match = 1.0, no match = 0.0
        score = 1.0 if source_a.lower() == source_b.lower() else 0.0
        
        logger.debug(f"📡 Resolution score: {score:.3f}")
        
        return score

    def _score_deadline_match(self, deadline_a: datetime, deadline_b: datetime) -> float:
        """
        Timestamps must match (allow 1-minute window for clock skew)
        
        Dangerous: 59 seconds difference can cause entire arb to blow
        """
        
        if not deadline_a or not deadline_b:
            return 0.5  # Unknown deadline
        
        time_diff_seconds = abs((deadline_a - deadline_b).total_seconds())
        
        logger.debug(f"⏰ Deadline difference: {time_diff_seconds}s")
        
        # Allow max 60 seconds (1 minute)
        if time_diff_seconds <= 60:
            score = 1.0
        elif time_diff_seconds <= 300:  # 5 minutes
            score = 0.5
        else:
            score = 0.0  # Too different - reject
        
        logger.debug(f"⏰ Deadline score: {score:.3f}")
        
        return score

    def _score_criteria_match(self, source_data_a: Dict, source_data_b: Dict) -> float:
        """
        Event criteria must match exactly
        
        Differences:
        - > vs >= (can change outcome)
        - "by EOD" vs "by midnight UTC" (timezone issues)
        - "Bitcoin price" vs "Bitcoin spot price" (different sources)
        """
        
        # Extract descriptions from source data
        desc_a = source_data_a.get('description', source_data_a.get('title', ''))
        desc_b = source_data_b.get('description', source_data_b.get('title', ''))
        
        criteria_a = self._extract_criteria(desc_a)
        criteria_b = self._extract_criteria(desc_b)
        
        logger.debug(f"📋 Criteria: '{criteria_a}' vs '{criteria_b}'")
        
        if not criteria_a or not criteria_b:
            return 0.5
        
        # Must be exact match
        score = 1.0 if criteria_a == criteria_b else 0.0
        
        logger.debug(f"📋 Criteria score: {score:.3f}")
        
        return score

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        # Apply common replacements
        for old, new in self.text_replacements.items():
            text = text.replace(old, new)
        
        # Additional number normalization
        text = re.sub(r'(\d+)k', r'\g<1>000', text)  # 100k -> 100000
        text = re.sub(r'(\d+)m', r'\g<1>000000', text)  # 100m -> 1000000
        text = re.sub(r'(\d+)b', r'\g<1>000000000', text)  # 100b -> 1000000000
        
        # Clean up multiple spaces and trailing spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _extract_resolution_source(self, source_data: Dict) -> Optional[str]:
        """Extract resolution authority from market description"""
        # Look for known sources in description or title
        description = source_data.get('description', source_data.get('title', '')).lower()
        
        for source in self.resolution_sources:
            if source in description:
                return source
        
        # Also check for common resolution phrases
        resolution_phrases = [
            'according to', 'based on', 'determined by', 'settled by',
            'resolved by', 'using data from'
        ]
        
        for phrase in resolution_phrases:
            if phrase in description:
                # Extract the source after the phrase
                phrase_index = description.find(phrase)
                after_phrase = description[phrase_index + len(phrase):].strip()
                
                # Look for known source in the following text
                for source in self.resolution_sources:
                    if source in after_phrase:
                        return source
        
        return None

    def _extract_criteria(self, description: str) -> Optional[str]:
        """Extract criteria from description"""
        if not description:
            return None
        
        # Match patterns like "> 50000" or ">= 50k"
        patterns = [
            r'(?:>|>=|<|<=|==)\s*[\$]?\d+[kmb]?(?:\s*dollars?)?',
            r'(?:above|below|over|under)\s*[\$]?\d+[kmb]?(?:\s*dollars?)?',
            r'(?:reaches?|exceeds?|hits?)\s*[\$]?\d+[kmb]?(?:\s*dollars?)?',
            r'(?:falls?|drops?\s*below)\s*[\$]?\d+[kmb]?(?:\s*dollars?)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0).lower()
        
        # Look for percentage criteria
        percent_patterns = [
            r'(?:>|>=|<|<=|==)\s*\d+%',
            r'(?:above|below|over|under)\s*\d+%',
        ]
        
        for pattern in percent_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(0).lower()
        
        return None

    def _group_by_normalized_name(self, markets: List[NormalizedMarket]) -> Dict[str, List[NormalizedMarket]]:
        """Group markets by normalized event name"""
        groups = {}
        
        for market in markets:
            # Create canonical name
            normalized = self._normalize_text(market.name)
            
            logger.debug(f"📝 Normalizing '{market.name}' -> '{normalized}'")
            
            if normalized not in groups:
                groups[normalized] = []
            
            groups[normalized].append(market)
        
        # Log groups for debugging
        logger.debug(f"📊 Groups created:")
        for name, market_list in groups.items():
            logger.debug(f"  '{name}': {len(market_list)} markets")
            for market in market_list:
                logger.debug(f"    - {market.source}: {market.name}")
        
        return groups

    def get_statistics(self) -> Dict[str, any]:
        """Get matching statistics"""
        if not self.matched_pairs_history:
            return {
                'total_pairs_matched': 0,
                'average_match_score': 0.0,
                'highest_score': 0.0,
                'lowest_score': 0.0,
                'pairs_above_95': 0,
                'pairs_above_90': 0
            }
        
        scores = [pair.match_score for pair in self.matched_pairs_history]
        
        return {
            'total_pairs_matched': len(self.matched_pairs_history),
            'average_match_score': sum(scores) / len(scores),
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'pairs_above_95': len([s for s in scores if s >= 0.95]),
            'pairs_above_90': len([s for s in scores if s >= 0.90])
        }

# Test function
async def test_contract_matcher():
    """Test the contract matcher with sample data"""
    print("🎯 Testing Contract Matcher")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create sample markets
    markets = [
        # Perfect match
        NormalizedMarket(
            market_id="polymarket:btc-2024",
            source="polymarket",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",
            category="crypto",
            yes_price=0.42,
            no_price=0.61,
            spread=0.03,
            yes_liquidity=50000,
            no_liquidity=75000,
            total_liquidity=125000,
            volume_24h=250000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            source_data={
                'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'
            }
        ),
        # Same event on different platform - should match
        NormalizedMarket(
            market_id="manifold:btc-2024",
            source="manifold",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",  # Same name as polymarket
            category="crypto",
            yes_price=0.40,
            no_price=0.63,
            spread=0.03,
            yes_liquidity=30000,
            no_liquidity=45000,
            total_liquidity=75000,
            volume_24h=150000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 30, tzinfo=timezone.utc),  # Same deadline (within 1 min)
            source_data={
                'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'
            }
        ),
        # Different event (should not match)
        NormalizedMarket(
            market_id="polymarket:eth-2024",
            source="polymarket",
            chain="ethereum",
            name="Ethereum price above $5,000 by end of 2024",
            category="crypto",
            yes_price=0.35,
            no_price=0.68,
            spread=0.03,
            yes_liquidity=40000,
            no_liquidity=60000,
            total_liquidity=100000,
            volume_24h=200000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            source_data={
                'description': 'Will Ethereum price exceed $5,000 by end of 2024 according to CoinGecko data'
            }
        ),
        # Same event but different resolution source (should not match)
        NormalizedMarket(
            market_id="azuro:btc-2024",
            source="azuro_polygon",
            chain="polygon",
            name="Bitcoin price > $100,000 by end of year",
            category="crypto",
            yes_price=0.43,
            no_price=0.60,
            spread=0.03,
            yes_liquidity=35000,
            no_liquidity=52000,
            total_liquidity=87000,
            volume_24h=180000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 45, tzinfo=timezone.utc),  # Same deadline
            source_data={
                'description': 'Bitcoin price exceeds $100,000 by end of 2024 based on CoinMarketCap data'
            }
        ),
        # Edge case: very similar but different deadline (should not match)
        NormalizedMarket(
            market_id="limitless:btc-2024",
            source="limitless",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",
            category="crypto",
            yes_price=0.41,
            no_price=0.62,
            spread=0.03,
            yes_liquidity=28000,
            no_liquidity=42000,
            total_liquidity=70000,
            volume_24h=140000,
            status="active",
            expires_at=datetime(2024, 12, 31, 22, 59, 59, tzinfo=timezone.utc),  # 1 hour earlier
            source_data={
                'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'
            }
        )
    ]
    
    # Test contract matcher
    matcher = ContractMatcher(min_match_score=0.95)
    
    try:
        # Find matched pairs
        matched_pairs = await matcher.find_all_matched_pairs(markets)
        
        print(f"\n📊 Results:")
        print(f"  Total markets: {len(markets)}")
        print(f"  Matched pairs: {len(matched_pairs)}")
        print(f"  Safe pairs: {len([p for p in matched_pairs if p.is_safe])}")
        
        print(f"\n🎯 Matched Pairs:")
        for i, pair in enumerate(matched_pairs, 1):
            print(f"\n{i}. {pair.market_a.source} + {pair.market_b.source}")
            print(f"   Score: {pair.match_score:.3f}")
            print(f"   Safe: {pair.is_safe}")
            print(f"   Details: {pair.match_details}")
        
        # Show statistics
        stats = matcher.get_statistics()
        print(f"\n📈 Statistics:")
        print(f"  Total pairs matched: {stats['total_pairs_matched']}")
        print(f"  Average score: {stats['average_match_score']:.3f}")
        print(f"  Highest score: {stats['highest_score']:.3f}")
        print(f"  Lowest score: {stats['lowest_score']:.3f}")
        print(f"  Pairs above 95%: {stats['pairs_above_95']}")
        print(f"  Pairs above 90%: {stats['pairs_above_90']}")
        
        # Verify expectations
        print(f"\n✅ Expected Results:")
        print(f"  - Polymarket + Manifold: Should match (same event, same resolution)")
        print(f"  - Polymarket + Ethereum: Should NOT match (different asset)")
        print(f"  - Polymarket + Azuro: Should NOT match (different resolution source)")
        print(f"  - Polymarket + Limitless: Should NOT match (different deadline)")
        
        print(f"\n🎉 Contract matcher test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_contract_matcher())
