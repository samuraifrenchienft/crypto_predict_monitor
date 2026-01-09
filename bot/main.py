from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

from rich.console import Console
from rich.table import Table

from bot.alerts.discord import DiscordAlerter
from bot.config import load_config
from bot.models import Quote
from bot.adapters.polymarket import PolymarketAdapter
from bot.adapters.limitless import LimitlessAdapter

console = Console()


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def write_snapshot(snapshot_dir: Path, source: str, payload: dict) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"{source}_{utc_ts()}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def render_cycle_table(rows: list[tuple[str, str, str, str]]) -> None:
    t = Table(title="cycle quotes (top-of-book where available)")
    t.add_column("source")
    t.add_column("market")
    t.add_column("outcome")
    t.add_column("bid/ask (spread)")
    for r in rows:
        t.add_row(*r)
    console.print(t)


def fmt_quote(q: Quote) -> str:
    if q.bid is None and q.ask is None:
        return "n/a"
    spread = f"{q.spread:.4f}" if q.spread is not None else "n/a"
    bid = f"{q.bid:.4f}" if q.bid is not None else "n/a"
    ask = f"{q.ask:.4f}" if q.ask is not None else "n/a"
    return f"{bid}/{ask} ({spread})"


async def main() -> None:
    console.print("[cyan]boot:[/cyan] starting bot.main")
    cfg = load_config()
    console.print(f"[cyan]boot:[/cyan] loaded config. poll={cfg.bot.poll_interval_seconds}s")

    alerter = DiscordAlerter(
        webhook_url=cfg.discord_webhook_url,
        enabled=cfg.discord.enabled,
        min_seconds_between_same_alert=cfg.discord.min_seconds_between_same_alert,
    )

    adapters = []
    if cfg.polymarket.enabled:
        console.print("[cyan]boot:[/cyan] enabling Polymarket adapter")
        adapters.append(
            PolymarketAdapter(
                gamma_base_url=cfg.polymarket.gamma_base_url,
                clob_base_url=cfg.polymarket.clob_base_url,
                data_base_url=cfg.polymarket.data_base_url,
                events_limit=cfg.polymarket.events_limit,
            )
        )

    if cfg.limitless.enabled:
        console.print("[cyan]boot:[/cyan] enabling Limitless adapter")
        adapters.append(LimitlessAdapter(base_url=cfg.limitless.base_url))

    if cfg.discord.online_message:
        console.print("[cyan]boot:[/cyan] sending ONLINE (may silently fail if webhook invalid)")
        await alerter.send(key="bot_online", content="🟢 crypto_predict_monitor ONLINE (read-only monitor)")

    prev_quotes: Dict[Tuple[str, str, str], Quote] = {}

    while True:
        console.print("[cyan]cycle:[/cyan] starting cycle")
        cycle_rows: list[tuple[str, str, str, str]] = []

        for ad in adapters:
            source = ad.name
            console.print(f"[cyan]cycle:[/cyan] adapter={source} fetching markets...")
            try:
                markets = await ad.list_active_markets()
                console.print(f"[cyan]cycle:[/cyan] adapter={source} markets={len(markets)}")
                markets = markets[: cfg.bot.max_markets_per_adapter]

                snapshot_payload = {"source": source, "markets": []}

                for m in markets:
                    outcomes = await ad.list_outcomes(m)
                    quotes = await ad.get_quotes(m, outcomes)

                    snapshot_payload["markets"].append(
                        {
                            "market": m.model_dump(mode="json"),
                            "outcomes": [o.model_dump(mode="json") for o in outcomes],
                            "quotes": [q.model_dump(mode="json") for q in quotes],
                        }
                    )

                    for o in outcomes:
                        q = next((x for x in quotes if x.outcome_id == o.outcome_id), None)
                        if q is None:
                            continue
                        cycle_rows.append((source, m.title[:42], o.name, fmt_quote(q)))

                        k = (source, m.market_id, o.outcome_id)
                        prev_quotes[k] = q

                snap_path = write_snapshot(cfg.bot.snapshot_dir, source, snapshot_payload)
                console.print(f"[green]snapshot[/green] {source} -> {snap_path}")

            except Exception as e:
                console.print(f"[red]error[/red] {source}: {e}")

        render_cycle_table(cycle_rows)
        console.print(f"[cyan]cycle:[/cyan] sleeping {cfg.bot.poll_interval_seconds}s\n")
        await asyncio.sleep(cfg.bot.poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
