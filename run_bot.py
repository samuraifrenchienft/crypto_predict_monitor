#!/usr/bin/env python3
"""
Crypto Prediction Monitor Bot
Fetches real market data from all 4 platforms with tiered arbitrage filtering
"""

import os
import sys
import asyncio
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except ImportError:
    pass

from rich.console import Console
from rich.table import Table

console = Console()

# Import adapters
from bot.adapters.polymarket import PolymarketAdapter
from bot.adapters.limitless import LimitlessAdapter
from bot.adapters.azuro import AzuroAdapter
from bot.adapters.manifold import ManifoldAdapter
from bot.models import Quote, Market
from bot.tiered_arbitrage_filter import TieredArbitrageFilter, get_filter

# Load config from config.yaml
def load_yaml_config() -> Dict[str, Any]:
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

CONFIG = load_yaml_config()

# Configuration from config.yaml
STRATEGY = CONFIG.get('strategy', {})
MIN_SPREAD = STRATEGY.get('min_spread', 0.015)  # 1.5% default
POLL_INTERVAL = CONFIG.get('data_collection', {}).get('refresh_interval', 60)
MAX_MARKETS = CONFIG.get('data_collection', {}).get('max_markets_per_platform', 50)
SNAPSHOT_DIR = Path("data")

# Tier configuration from config.yaml
TIERS = CONFIG.get('tiers', {})

# Discord webhooks from environment
CPM_WEBHOOK_URL = os.getenv("CPM_WEBHOOK_URL", "")
HEALTH_WEBHOOK_URL = os.getenv("CPM_HEALTH_WEBHOOK_URL", os.getenv("DISCORD_HEALTH_WEBHOOK_URL", ""))


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def write_snapshot(source: str, payload: dict) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{source}_{utc_ts()}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def fmt_quote(q: Quote) -> str:
    if q.bid is None and q.ask is None:
        return "n/a"
    spread = f"{q.spread:.4f}" if q.spread is not None else "n/a"
    bid = f"{q.bid:.4f}" if q.bid is not None else "n/a"
    ask = f"{q.ask:.4f}" if q.ask is not None else "n/a"
    return f"{bid}/{ask} ({spread})"


def render_cycle_table(rows: list) -> None:
    t = Table(title="Market Quotes (Real Data)")
    t.add_column("Source", style="cyan")
    t.add_column("Market", style="white")
    t.add_column("Outcome", style="green")
    t.add_column("Bid/Ask (Spread)", style="yellow")
    for r in rows:
        t.add_row(*r)
    console.print(t)


def normalize_title(title: str) -> str:
    """Normalize market title for cross-platform matching"""
    import re
    title = title.lower().strip()
    # Remove common prefixes/suffixes
    title = re.sub(r'^will\s+', '', title)
    title = re.sub(r'\?$', '', title)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    return title


def find_cross_market_opportunities(all_markets: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """
    Find arbitrage opportunities across different platforms
    Returns opportunities with spread percentages
    """
    # Group markets by normalized title
    title_groups = {}
    
    for source, markets in all_markets.items():
        for market in markets:
            norm_title = normalize_title(market.get('title', ''))
            if norm_title not in title_groups:
                title_groups[norm_title] = []
            title_groups[norm_title].append({
                'source': source,
                'market': market,
            })
    
    # Find opportunities where same event exists on 2+ platforms
    opportunities = []
    
    for norm_title, market_list in title_groups.items():
        platforms = set(m['source'] for m in market_list)
        
        if len(platforms) >= 2:
            # Calculate spread between platforms
            yes_prices = []
            no_prices = []
            
            for m in market_list:
                quotes = m['market'].get('quotes', [])
                for q in quotes:
                    if 'YES' in str(q.get('outcome_id', '')).upper() or q.get('name', '').upper() == 'YES':
                        if q.get('mid'):
                            yes_prices.append((m['source'], q['mid']))
                    elif 'NO' in str(q.get('outcome_id', '')).upper() or q.get('name', '').upper() == 'NO':
                        if q.get('mid'):
                            no_prices.append((m['source'], q['mid']))
            
            # Calculate spread if we have prices from multiple platforms
            if len(yes_prices) >= 2:
                prices = [p[1] for p in yes_prices]
                spread = max(prices) - min(prices)
                spread_pct = spread * 100  # Convert to percentage
                
                # Don't filter here - let tiered filter handle it
                opportunities.append({
                    'normalized_title': norm_title,
                    'platforms': list(platforms),
                    'markets': market_list,
                    'spread_percentage': spread_pct,
                    'yes_prices': yes_prices,
                    'no_prices': no_prices,
                })
    
    return opportunities


async def send_discord_alert(opportunity: Dict[str, Any], tier_info: Dict[str, Any]) -> bool:
    """Send Discord alert for arbitrage opportunity"""
    if not CPM_WEBHOOK_URL:
        return False
    
    try:
        import aiohttp
        
        # Build embed
        embed = {
            'title': f"{tier_info['tier_emoji']} {tier_info['tier'].upper()} ARBITRAGE",
            'description': f"**{opportunity['normalized_title']}**",
            'color': int(tier_info['tier_color'].lstrip('#'), 16),
            'fields': [
                {'name': '💰 Spread', 'value': f"**{opportunity['spread_percentage']:.2f}%**", 'inline': True},
                {'name': '⭐ Score', 'value': f"**{tier_info['quality_score']:.1f}/10**", 'inline': True},
                {'name': '📊 Platforms', 'value': ', '.join(opportunity['platforms']), 'inline': True},
                {'name': '🎯 Action', 'value': tier_info['tier_action'], 'inline': False},
            ],
            'footer': {'text': f"CPM Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }
        
        payload = {
            'embeds': [embed],
            'username': 'CPM Arbitrage Bot',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(CPM_WEBHOOK_URL, json=payload) as response:
                return response.status == 204
    except Exception as e:
        console.print(f"[red]Discord alert error: {e}[/red]")
        return False


def render_arbitrage_table(opportunities: List[Dict[str, Any]]) -> None:
    """Display arbitrage opportunities in a table"""
    if not opportunities:
        return
    
    t = Table(title="🎯 ARBITRAGE OPPORTUNITIES (Tiered Filter Applied)")
    t.add_column("Tier", style="bold")
    t.add_column("Event", style="white")
    t.add_column("Spread", style="yellow")
    t.add_column("Score", style="cyan")
    t.add_column("Platforms", style="green")
    t.add_column("Action", style="magenta")
    
    for opp in opportunities:
        t.add_row(
            f"{opp.get('tier_emoji', '❓')} {opp.get('tier', 'unknown').upper()}",
            opp['normalized_title'][:35],
            f"{opp['spread_percentage']:.2f}%",
            f"{opp.get('quality_score', 0):.1f}/10",
            ', '.join(opp['platforms']),
            opp.get('tier_action', 'N/A')
        )
    
    console.print(t)


async def main():
    console.print("[bold cyan]🚀 Starting Crypto Prediction Monitor Bot[/bold cyan]")
    console.print(f"[cyan]Poll interval: {POLL_INTERVAL}s | Max markets per adapter: {MAX_MARKETS}[/cyan]")
    
    if CPM_WEBHOOK_URL:
        console.print(f"[green]✓ Discord webhook configured[/green]")
    else:
        console.print(f"[yellow]⚠ No Discord webhook configured[/yellow]")

    # Initialize adapters for all 4 platforms
    adapters = []
    
    # Polymarket
    console.print(f"[cyan]Initializing Polymarket adapter (limit: {MAX_MARKETS})...[/cyan]")
    adapters.append(PolymarketAdapter(
        gamma_base_url="https://gamma-api.polymarket.com",
        clob_base_url="https://clob.polymarket.com",
        data_base_url="https://data-api.polymarket.com",
        events_limit=MAX_MARKETS,
    ))
    
    # Limitless
    console.print("[cyan]Initializing Limitless adapter...[/cyan]")
    adapters.append(LimitlessAdapter(
        base_url="https://api.limitless.exchange"
    ))
    
    # Azuro
    console.print(f"[cyan]Initializing Azuro adapter (limit: {MAX_MARKETS})...[/cyan]")
    adapters.append(AzuroAdapter(
        graphql_base_url="https://api.onchainfeed.org/api/v1/public/gateway",
        subgraph_base_url="https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-polygon-v3",
        rest_base_url="https://api.onchainfeed.org/api/v1/public/gateway",
        markets_limit=MAX_MARKETS,
        use_fallback=True,
    ))
    
    # Manifold
    console.print(f"[cyan]Initializing Manifold adapter (limit: {MAX_MARKETS})...[/cyan]")
    adapters.append(ManifoldAdapter(
        base_url="https://api.manifold.markets/v0",
        markets_limit=MAX_MARKETS,
    ))
    
    console.print(f"[bold green]✓ All 4 adapters initialized[/bold green]")
    console.print("")

    # Initialize tiered filter with config
    tiered_filter = get_filter(MIN_SPREAD)
    console.print(f"[cyan]Strategy: {STRATEGY.get('name', 'Spread-Only')} | Min Spread: {MIN_SPREAD*100:.1f}%[/cyan]")
    console.print("")

    cycle_count = 0
    while True:
        cycle_count += 1
        console.print(f"[bold cyan]═══ Cycle {cycle_count} ═══[/bold cyan]")
        
        all_markets = {}  # Collect markets from all platforms
        cycle_rows = []
        
        for adapter in adapters:
            source = adapter.name
            console.print(f"[cyan]Fetching {source} markets...[/cyan]")
            
            try:
                markets = await adapter.list_active_markets()
                console.print(f"[green]  ✓ {source}: {len(markets)} markets[/green]")
                markets = markets[:MAX_MARKETS]
                
                source_markets = []
                
                for m in markets:
                    try:
                        outcomes = await adapter.list_outcomes(m)
                        quotes = await adapter.get_quotes(m, outcomes)
                        
                        market_data = {
                            "market_id": m.market_id,
                            "title": m.title,
                            "url": m.url,
                            "outcomes": [o.model_dump(mode="json") for o in outcomes],
                            "quotes": [q.model_dump(mode="json") for q in quotes],
                        }
                        source_markets.append(market_data)
                        
                        # Add to display rows (first 5 per source)
                        if len([r for r in cycle_rows if r[0] == source]) < 5:
                            for o in outcomes:
                                q = next((x for x in quotes if x.outcome_id == o.outcome_id), None)
                                if q:
                                    cycle_rows.append((source, m.title[:40], o.name, fmt_quote(q)))
                    except Exception as e:
                        pass  # Skip individual market errors silently
                
                all_markets[source] = source_markets
                
                # Write snapshot
                snap_path = write_snapshot(source, {"source": source, "markets": source_markets, "timestamp": utc_ts()})
                console.print(f"[dim]  Snapshot: {snap_path}[/dim]")
                
            except Exception as e:
                console.print(f"[red]  ✗ {source} error: {e}[/red]")
        
        # Display sample quotes
        if cycle_rows:
            console.print("")
            render_cycle_table(cycle_rows[:20])  # Show max 20 rows
        
        # Find cross-market arbitrage opportunities
        console.print("\n[bold yellow]🔍 Scanning for cross-market arbitrage...[/bold yellow]")
        raw_opportunities = find_cross_market_opportunities(all_markets)
        console.print(f"[cyan]Found {len(raw_opportunities)} potential opportunities[/cyan]")
        
        # Apply tiered filter
        if raw_opportunities:
            filtered_opportunities = tiered_filter.filter_and_tier_opportunities(raw_opportunities, MIN_SPREAD)
            
            if filtered_opportunities:
                console.print(f"[bold green]✓ {len(filtered_opportunities)} opportunities passed filter (≥{MIN_SPREAD*100:.1f}% spread)[/bold green]")
                render_arbitrage_table(filtered_opportunities)
                
                # Send Discord alerts for all opportunities that passed the filter
                for opp in filtered_opportunities:
                    success = await send_discord_alert(opp, opp)
                    if success:
                        console.print(f"[green]  📢 Alert sent: {opp['normalized_title'][:30]}[/green]")
                
                # Show tier breakdown
                breakdown = tiered_filter.get_tier_breakdown()
                console.print(f"\n[dim]Tier Summary: {breakdown['summary']}[/dim]")
            else:
                console.print(f"[yellow]No opportunities met the {MIN_SPREAD*100:.1f}% minimum spread threshold[/yellow]")
        else:
            console.print("[yellow]No cross-market matches found this cycle[/yellow]")
        
        console.print(f"\n[cyan]Sleeping {POLL_INTERVAL}s until next cycle...[/cyan]\n")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
