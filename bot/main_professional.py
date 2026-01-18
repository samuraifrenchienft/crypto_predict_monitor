"""
Professional Crypto Prediction Monitor Bot
Uses ProfessionalArbitrageSystem with quality scoring and rich Discord alerts
"""
from __future__ import annotations

import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dotenv import load_dotenv
    repo_root = Path(__file__).parent.parent
    for candidate in (repo_root / "env.txt", repo_root / ".env", repo_root / "env_credentials.txt"):
        if candidate.exists():
            load_dotenv(candidate, override=True)
            break
except ImportError:
    pass

from rich.console import Console

# Import professional arbitrage system
from arbitrage_main import ProfessionalArbitrageSystem
from arbitrage.complete_system import MarketData

# Import adapters
from bot.adapters.polymarket import PolymarketAdapter
from bot.adapters.limitless import LimitlessAdapter
from bot.adapters.azuro import AzuroAdapter
from bot.errors import FatalError, RetryableError, log_error_metrics

console = Console()


def load_yaml_config():
    """Load config.yaml"""
    import yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config.yaml: {e}[/yellow]")
        return {}


async def main() -> None:
    console.print("[bold cyan]>>> Starting CPM Professional Arbitrage Monitor[/bold cyan]")
    
    # Load config
    cfg = load_yaml_config()
    data_collection = cfg.get('data_collection', {})
    poll_interval = data_collection.get('refresh_interval', 300)  # 5 minutes default
    max_markets = data_collection.get('max_markets_per_platform', 50)
    platforms_cfg = cfg.get('platforms', {})
    
    # Verify webhook is set
    webhook_url = os.getenv("CPM_WEBHOOK_URL", "")
    if not webhook_url:
        console.print("[red][ERROR] CPM_WEBHOOK_URL not set in environment[/red]")
        console.print("[yellow]Set CPM_WEBHOOK_URL in your env.txt file[/yellow]")
        return
    
    console.print(f"[green][OK] Discord webhook configured[/green]")
    console.print(f"[cyan]Poll interval: {poll_interval}s | Max markets per platform: {max_markets}[/cyan]")
    
    # Initialize professional arbitrage system
    console.print("[cyan]Initializing Professional Arbitrage System...[/cyan]")
    system = ProfessionalArbitrageSystem()
    
    if not await system.initialize():
        console.print("[red][ERROR] Failed to initialize arbitrage system[/red]")
        return
    
    console.print("[bold green][OK] Professional Arbitrage System initialized[/bold green]")
    
    # Send startup alert
    await system.send_health_alert(
        "🚀 CPM Professional Arbitrage Monitor ONLINE\n"
        "✅ Quality scoring system active\n"
        "✅ Discord alerts enabled\n"
        "✅ Multi-platform monitoring ready",
        "success"
    )
    
    # Initialize adapters
    adapters = []
    
    if platforms_cfg.get('polymarket', {}).get('enabled', True):
        console.print("[cyan]Initializing Polymarket adapter...[/cyan]")
        adapters.append(PolymarketAdapter(
            gamma_base_url="https://gamma-api.polymarket.com",
            clob_base_url="https://clob.polymarket.com",
            data_base_url="https://data-api.polymarket.com",
            events_limit=max_markets,
        ))
    
    if platforms_cfg.get('limitless', {}).get('enabled', True):
        console.print("[cyan]Initializing Limitless adapter...[/cyan]")
        adapters.append(LimitlessAdapter(base_url="https://api.limitless.exchange"))
    
    if platforms_cfg.get('azuro', {}).get('enabled', True):
        console.print("[cyan]Initializing Azuro adapter...[/cyan]")
        adapters.append(AzuroAdapter(
            graphql_base_url="https://api.onchainfeed.org/api/v1/public/gateway",
            subgraph_base_url="https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-polygon-v3",
            rest_base_url="https://api.onchainfeed.org/api/v1/public/gateway",
            markets_limit=max_markets,
            use_fallback=True,
        ))
    
    # Manifold removed - uses play money (M$), not real crypto
    
    console.print(f"[bold green][OK] {len(adapters)} platform adapters initialized[/bold green]\n")
    
    # Main monitoring loop
    scan_count = 0
    while True:
        scan_count += 1
        console.print(f"[bold cyan]=== Scan #{scan_count} ===[/bold cyan]")
        
        # Fetch markets from all platforms
        all_market_data: List[MarketData] = []
        
        for adapter in adapters:
            source = adapter.name
            console.print(f"[cyan]Fetching {source} markets...[/cyan]")
            
            try:
                markets = await adapter.list_active_markets()
                console.print(f"[green]  [OK] {source}: {len(markets)} markets fetched[/green]")
                
                # Limit markets per platform
                markets = markets[:max_markets]
                
                # Convert to MarketData format for professional system
                for m in markets:
                    try:
                        outcomes = await adapter.list_outcomes(m)
                        quotes = await adapter.get_quotes(m, outcomes)
                        
                        if not quotes:
                            continue
                        
                        # Extract YES/NO prices and liquidity
                        yes_price = 0.0
                        no_price = 0.0
                        yes_bid = 0.0
                        yes_ask = 0.0
                        no_bid = 0.0
                        no_ask = 0.0
                        yes_liquidity = 0.0
                        no_liquidity = 0.0
                        
                        for q in quotes:
                            outcome_name = str(q.outcome_id).upper()
                            if 'YES' in outcome_name or q.name.upper() == 'YES':
                                yes_price = q.mid or 0.0
                                yes_bid = q.bid or yes_price
                                yes_ask = q.ask or yes_price
                                yes_liquidity = getattr(q, 'liquidity', 0.0) or 0.0
                            elif 'NO' in outcome_name or q.name.upper() == 'NO':
                                no_price = q.mid or 0.0
                                no_bid = q.bid or no_price
                                no_ask = q.ask or no_price
                                no_liquidity = getattr(q, 'liquidity', 0.0) or 0.0
                        
                        # Calculate spread
                        spread_pct = 0.0
                        if yes_price > 0 and no_price > 0:
                            theoretical_no = 1.0 - yes_price
                            spread_pct = abs(no_price - theoretical_no) * 100
                        
                        # Get market expiration
                        expires_at = None
                        if hasattr(m, 'end_date') and m.end_date:
                            expires_at = m.end_date
                        elif hasattr(m, 'close_time') and m.close_time:
                            expires_at = m.close_time
                        
                        # Create MarketData object
                        market_data = MarketData(
                            market_id=m.market_id,
                            market_name=m.title,
                            yes_price=yes_price,
                            no_price=no_price,
                            yes_bid=yes_bid,
                            yes_ask=yes_ask,
                            no_bid=no_bid,
                            no_ask=no_ask,
                            yes_liquidity=yes_liquidity,
                            no_liquidity=no_liquidity,
                            volume_24h=getattr(m, 'volume_24h', 0.0) or 0.0,
                            spread_percentage=spread_pct,
                            price_volatility=0.1,  # Default volatility
                            expires_at=expires_at or datetime.utcnow() + timedelta(days=7),
                            polymarket_link=m.url,
                            analysis_link=m.url,
                            market_source=source
                        )
                        
                        all_market_data.append(market_data)
                        
                    except Exception as e:
                        console.print(f"[dim]  Skipping market: {e}[/dim]")
                        continue
                
                console.print(f"[green]  [OK] {source}: {len([md for md in all_market_data if md.market_source == source])} markets processed[/green]")
                
            except FatalError as e:
                console.print(f"[red]FATAL {source}: {e.error_info.message}[/red]")
                log_error_metrics(e.error_info)
            except RetryableError as e:
                console.print(f"[yellow]RETRY {source}: {e.error_info.message}[/yellow]")
                log_error_metrics(e.error_info)
            except Exception as e:
                console.print(f"[red]ERROR {source}: {e}[/red]")
        
        console.print(f"\n[bold cyan]Total markets collected: {len(all_market_data)}[/bold cyan]")
        
        # Run professional arbitrage detection and send alerts
        if all_market_data:
            console.print("[bold yellow]>>> Running Professional Arbitrage Analysis...[/bold yellow]")
            
            try:
                results = await system.run_full_scan_and_alert(all_market_data)
                
                # Display results
                opp_count = results['scan_results']['opportunities_detected']
                alert_count = results['alerts_sent']
                
                if opp_count > 0:
                    console.print(f"[bold green]🎯 DETECTED {opp_count} quality arbitrage opportunities[/bold green]")
                    console.print(f"[bold green]📢 Sent {alert_count} Discord alerts[/bold green]")
                    
                    # Show top opportunities
                    for i, opp in enumerate(results['scan_results']['opportunities'][:5]):
                        console.print(f"  {i+1}. {opp.market_name[:50]} - {opp.quality_score:.1f}/10 quality - {opp.spread_percentage:.1f}% spread")
                else:
                    console.print("[yellow]📊 No quality arbitrage opportunities detected this scan[/yellow]")
                
                # Show system stats
                stats = results['system_stats']
                console.print(f"[dim]Total scans: {stats['total_scans']} | Total opportunities: {stats['total_opportunities']} | Total alerts: {stats['total_alerts']}[/dim]")
                
            except Exception as e:
                console.print(f"[red]ERROR during arbitrage analysis: {e}[/red]")
                import traceback
                traceback.print_exc()
        else:
            console.print("[yellow]No markets collected this cycle[/yellow]")
        
        # Health check every 10 scans
        if scan_count % 10 == 0:
            console.print("[cyan]Running system health check...[/cyan]")
            health = await system.monitor_system_health()
            console.print(f"[green]System health: {health['status']}[/green]")
        
        # Wait for next scan
        console.print(f"\n[cyan]Waiting {poll_interval}s until next scan...[/cyan]\n")
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
