"""
Comprehensive Event Matching System
Scans all markets across categories for arbitrage opportunities
"""

from __future__ import annotations

import asyncio
import re
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from bot.adapters.base import Adapter
from bot.models import Market
from bot.arbitrage import normalize_title, group_by_normalized_title, detect_cross_market_arbitrage
from bot.config import load_config


@dataclass
class EventMatch:
    """Represents a matching event across platforms"""
    normalized_title: str
    markets: List[Tuple[str, Market]]
    platforms: Set[str]
    category: str
    confidence_score: float
    created_at: datetime


class ComprehensiveEventMatcher:
    """
    Comprehensive event matching across all market categories
    Scans Polymarket, Azuro, Limitless, Manifold for matching events
    """
    
    def __init__(self):
        self.config = load_config()
        self.matches_cache: Dict[str, EventMatch] = {}
        self.last_scan_time: Optional[datetime] = None
        self.scan_interval_hours = 1  # Hourly scans
        
        # Category keywords for classification
        self.category_keywords = {
            'crypto': ['bitcoin', 'ethereum', 'eth', 'btc', 'solana', 'doge', 'crypto', 'blockchain', 'defi'],
            'politics': ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'vote', 'political'],
            'sports': ['nfl', 'nba', 'mlb', 'soccer', 'football', 'basketball', 'baseball', 'team', 'game', 'match'],
            'economy': ['fed', 'inflation', 'interest rates', 'recession', 'gdp', 'unemployment', 'economy'],
            'weather': ['hurricane', 'temperature', 'snow', 'rain', 'weather', 'climate', 'tornado'],
            'geopolitics': ['war', 'iran', 'china', 'russia', 'ukraine', 'israel', 'conflict', 'geopolitical'],
            'technology': ['apple', 'google', 'tesla', 'microsoft', 'tech', 'ai', 'chatgpt', 'innovation'],
            'entertainment': ['oscars', 'grammys', 'movie', 'music', 'celebrity', 'entertainment']
        }
    
    def normalize_title_advanced(self, title: str) -> str:
        """
        Advanced title normalization for better matching
        Handles various formats and removes platform-specific wording
        """
        # Convert to lowercase and remove extra whitespace
        normalized = " ".join(title.lower().split())
        
        # Remove common platform-specific prefixes/suffixes
        prefixes_to_remove = [
            'will ', 'will the ', 'will there be ', 'will we see ',
            'are ', 'are the ', 'are we going to have ',
            'is ', 'is the ', 'is there going to be ',
            'will ', 'would ', 'could ', 'should ',
            'do ', 'does ', 'did '
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove question marks and common question words
        normalized = re.sub(r'[?!.]', '', normalized)
        normalized = re.sub(r'\b(by|before|after|on|in|during|at|for|during|with|without|up to|more than|less than|above|below)\b', ' ', normalized)
        
        # Standardize common terms
        term_mappings = {
            'bitcoin': 'btc',
            'ethereum': 'eth', 
            'federal reserve': 'fed',
            'interest rate': 'rates',
            'united states': 'us',
            'america': 'us',
            'president trump': 'trump',
            'president biden': 'biden',
            'donald trump': 'trump',
            'joe biden': 'biden'
        }
        
        for old_term, new_term in term_mappings.items():
            normalized = normalized.replace(old_term, new_term)
        
        # Remove extra words that don't affect meaning
        noise_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'with', 
            'to', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
            'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
            'just', 'should', 'now', 'also', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'doing', 'would', 'should', 'could', 'may', 'might'
        }
        
        words = normalized.split()
        normalized = " ".join([word for word in words if word not in noise_words])
        
        return normalized.strip()
    
    def classify_category(self, title: str) -> str:
        """Classify market category based on title keywords"""
        title_lower = title.lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in title_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or 'other' if none
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'other'
    
    def calculate_match_confidence(self, markets: List[Tuple[str, Market]]) -> float:
        """Calculate confidence score for event match"""
        if len(markets) < 2:
            return 0.0
        
        # Base confidence from number of platforms
        platform_count = len(set(source for source, _ in markets))
        base_confidence = min(platform_count * 0.3, 0.9)  # Max 0.9 from platforms
        
        # Bonus for title similarity
        titles = [market.title for _, market in markets]
        if len(titles) >= 2:
            # Calculate similarity between first two titles
            title1_words = set(titles[0].lower().split())
            title2_words = set(titles[1].lower().split())
            similarity = len(title1_words.intersection(title2_words)) / len(title1_words.union(title2_words))
            similarity_bonus = similarity * 0.1
        else:
            similarity_bonus = 0.0
        
        return min(base_confidence + similarity_bonus, 1.0)
    
    async def get_all_markets(self) -> Dict[str, List[Market]]:
        """Fetch markets from all enabled adapters"""
        markets_by_source = {}
        
        # Polymarket
        if self.config.polymarket.enabled:
            try:
                from bot.adapters.polymarket import PolymarketAdapter
                poly = PolymarketAdapter(
                    gamma_base_url=self.config.polymarket.gamma_base_url,
                    clob_base_url=self.config.polymarket.clob_base_url,
                    data_base_url=self.config.polymarket.data_base_url
                )
                poly_markets = await poly.list_active_markets()
                markets_by_source['polymarket'] = poly_markets
                print(f"[MATCHER] Polymarket: {len(poly_markets)} markets")
            except Exception as e:
                print(f"[MATCHER] Polymarket error: {e}")
        
        # Azuro
        if self.config.azuro.enabled:
            try:
                from bot.adapters.azuro import AzuroAdapter
                azuro = AzuroAdapter(
                    graphql_base_url=self.config.azuro.graphql_base_url,
                    subgraph_base_url=self.config.azuro.subgraph_base_url,
                    rest_base_url=self.config.azuro.rest_base_url,
                    use_fallback=self.config.azuro.use_fallback
                )
                azuro_markets = await azuro.list_active_markets()
                markets_by_source['azuro'] = azuro_markets
                print(f"[MATCHER] Azuro: {len(azuro_markets)} markets")
            except Exception as e:
                print(f"[MATCHER] Azuro error: {e}")
        
        # Limitless
        if self.config.limitless.enabled:
            try:
                from bot.adapters.limitless import LimitlessAdapter
                limitless = LimitlessAdapter(base_url=self.config.limitless.base_url)
                limitless_markets = await limitless.list_active_markets()
                markets_by_source['limitless'] = limitless_markets
                print(f"[MATCHER] Limitless: {len(limitless_markets)} markets")
            except Exception as e:
                print(f"[MATCHER] Limitless error: {e}")
        
        # Manifold
        if self.config.manifold.enabled:
            try:
                from bot.adapters.manifold import ManifoldAdapter
                manifold = ManifoldAdapter(
                    base_url=self.config.manifold.base_url,
                    api_key=self.config.manifold.api_key
                )
                manifold_markets = await manifold.list_active_markets()
                markets_by_source['manifold'] = manifold_markets
                print(f"[MATCHER] Manifold: {len(manifold_markets)} markets")
            except Exception as e:
                print(f"[MATCHER] Manifold error: {e}")
        
        return markets_by_source
    
    async def find_comprehensive_matches(self) -> List[EventMatch]:
        """Find all matching events across platforms with advanced matching"""
        print("[MATCHER] Starting comprehensive event matching scan...")
        
        # Get all markets
        markets_by_source = await self.get_all_markets()
        total_markets = sum(len(markets) for markets in markets_by_source.values())
        print(f"[MATCHER] Scanning {total_markets} markets across {len(markets_by_source)} platforms")
        
        # Group by advanced normalized titles
        normalized_groups = {}
        for source, markets in markets_by_source.items():
            for market in markets:
                # Try both simple and advanced normalization
                simple_norm = normalize_title(market.title)
                advanced_norm = self.normalize_title_advanced(market.title)
                
                # Use advanced normalization, fallback to simple
                norm_title = advanced_norm if advanced_norm else simple_norm
                
                if norm_title not in normalized_groups:
                    normalized_groups[norm_title] = []
                normalized_groups[norm_title].append((source, market))
        
        # Find matches (2+ platforms)
        matches = []
        for norm_title, market_list in normalized_groups.items():
            platforms = set(source for source, _ in market_list)
            
            if len(platforms) >= 2:  # Match across 2+ platforms
                category = self.classify_category(market_list[0][1].title)
                confidence = self.calculate_match_confidence(market_list)
                
                event_match = EventMatch(
                    normalized_title=norm_title,
                    markets=market_list,
                    platforms=platforms,
                    category=category,
                    confidence_score=confidence,
                    created_at=datetime.now()
                )
                
                matches.append(event_match)
        
        # Sort by confidence score
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        
        print(f"[MATCHER] Found {len(matches)} matching events across platforms")
        for match in matches[:5]:  # Show top 5
            print(f"  - {match.normalized_title} ({match.category}) - {match.platforms} - {match.confidence_score:.2f}")
        
        return matches
    
    async def start_hourly_scan(self):
        """Start hourly scanning for new matches"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check if we should scan (hourly or first run)
                if (self.last_scan_time is None or 
                    current_time - self.last_scan_time >= timedelta(hours=self.scan_interval_hours)):
                    
                    print(f"[MATCHER] Starting hourly scan at {current_time}")
                    matches = await self.find_comprehensive_matches()
                    
                    # Update cache
                    for match in matches:
                        self.matches_cache[match.normalized_title] = match
                    
                    self.last_scan_time = current_time
                    
                    # Send alerts for new high-confidence matches
                    await self.alert_new_matches(matches)
                
                # Sleep for 10 minutes and check again
                await asyncio.sleep(600)  # 10 minutes
                
            except Exception as e:
                print(f"[MATCHER] Error in hourly scan: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
    
    async def alert_new_matches(self, matches: List[EventMatch]):
        """Send alerts for new high-confidence matches"""
        # Filter for high-confidence matches (0.7+)
        high_confidence_matches = [m for m in matches if m.confidence_score >= 0.7]
        
        if not high_confidence_matches:
            return
        
        # Check for truly new matches (not in cache)
        new_matches = []
        for match in high_confidence_matches:
            if match.normalized_title not in self.matches_cache:
                new_matches.append(match)
        
        if new_matches:
            await self.send_discord_alert(new_matches)
    
    async def send_discord_alert(self, new_matches: List[EventMatch]):
        """Send Discord alert for new matches"""
        try:
            from src.arbitrage_alerts import ArbitrageAlert
            
            webhook_url = self.config.discord_health_webhook_url or os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
            if not webhook_url:
                return
            
            async with ArbitrageAlert(webhook_url) as alerter:
                embed = {
                    "title": "🎯 New Cross-Platform Matches Found",
                    "description": f"Found {len(new_matches)} new matching events across platforms",
                    "color": 0x00ff00,
                    "fields": [],
                    "footer": {"text": "CPM Monitor | Comprehensive Event Matcher"},
                    "timestamp": datetime.now().isoformat()
                }
                
                for match in new_matches[:5]:  # Top 5 matches
                    platforms_str = ", ".join(match.platforms)
                    field = {
                        "name": f"{match.category.title()} - {match.confidence_score:.1%}",
                        "value": f"**{match.normalized_title}**\nPlatforms: {platforms_str}\nMarkets: {len(match.markets)}",
                        "inline": False
                    }
                    embed["fields"].append(field)
                
                await alerter.send_embed(embed)
                print(f"[MATCHER] Sent Discord alert for {len(new_matches)} new matches")
                
        except Exception as e:
            print(f"[MATCHER] Error sending Discord alert: {e}")
    
    def get_cached_matches(self) -> List[EventMatch]:
        """Get all cached matches"""
        return list(self.matches_cache.values())
    
    def get_matches_by_category(self, category: str) -> List[EventMatch]:
        """Get matches filtered by category"""
        return [m for m in self.matches_cache.values() if m.category == category]


# Global instance
_matcher = None

async def get_event_matcher() -> ComprehensiveEventMatcher:
    """Get or create the global event matcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = ComprehensiveEventMatcher()
    return _matcher

async def start_comprehensive_matching():
    """Start the comprehensive matching system"""
    matcher = await get_event_matcher()
    await matcher.start_hourly_scan()
