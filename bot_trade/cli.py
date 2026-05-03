"""
bot_trade/cli.py — Main CLI entry point

Usage:
  python -m bot_trade funding          # Show live funding rates & opportunities
  python -m bot_trade delta-neutral    # Run delta-neutral cross-exchange strategy
  python -m bot_trade volume           # Run volume generation
  python -m bot_trade indicator        # Run indicator-based trading
  python -m bot_trade status           # Show account balances & positions
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

import os
import sys

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.align import Align
from loguru import logger

from .config import get_config
from .models import ExchangeName, TradingMode
from .exchanges import get_exchange, get_all_exchanges
from .strategies.funding_scanner import FundingScanner
from .strategies.delta_neutral import DeltaNeutralStrategy
from .strategies.volume_generator import VolumeGeneratorStrategy
from .strategies.indicator_trader import IndicatorTrader, IndicatorStrategy

app = typer.Typer(
    name="bot-trade",
    help="[DEX Trading Bot] Nado x Rise x Decibel",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console(force_terminal=True, highlight=True)

# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = """[bold cyan]
+======================================================+
|         [*] DEX TRADING BOT  v1.0                   |
|         Nado (Ink) x Rise Chain x Decibel (Aptos)   |
+======================================================+[/bold cyan]"""


def print_banner():
    console.print(BANNER)


# ─── Funding Rate Command ─────────────────────────────────────────────────────

@app.command("funding")
def cmd_funding(
    symbols: str = typer.Option("BTC,ETH,SOL", help="Comma-separated symbols to scan"),
    exchanges_str: str = typer.Option("nado,decibel,rise", "--exchanges", help="Exchanges to scan"),
    min_yield: float = typer.Option(3.0, "--min-yield", help="Min annual yield %% to highlight"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Auto-refresh every 60s"),
    interval: int = typer.Option(60, "--interval", help="Refresh interval in seconds (with --watch)"),
):
    """
    [bold]Scan & compare funding rates[/bold] across all exchanges.
    Highlights cross-exchange delta-neutral opportunities.
    """
    print_banner()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    exchange_list = [e.strip().lower() for e in exchanges_str.split(",")]

    async def _run():
        exs = {}
        for ex_name in exchange_list:
            try:
                ex = get_exchange(ex_name)
                exs[ex.name] = ex
            except Exception as e:
                console.print(f"[yellow]⚠ Skipping {ex_name}: {e}[/yellow]")

        if not exs:
            console.print("[red]❌ No exchanges configured![/red]")
            return

        scanner = FundingScanner(exs, symbols=symbol_list, min_annual_yield_pct=min_yield)

        if watch:
            with Live(console=console, refresh_per_second=0.5) as live:
                while True:
                    await scanner.scan_all()
                    live.update(_render_funding_dashboard(scanner, min_yield))
                    await asyncio.sleep(interval)
        else:
            with console.status("[bold cyan]Scanning funding rates...[/bold cyan]"):
                await scanner.scan_all()
            console.print(_render_funding_dashboard(scanner, min_yield))

    asyncio.run(_run())


def _render_funding_dashboard(scanner: FundingScanner, min_yield: float) -> Panel:
    """Render the funding rate dashboard as a Rich panel."""

    # ── Rates Table ──────────────────────────────────────────────────────────
    rates_table = Table(
        title="[bold]Current Funding Rates[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    rates_table.add_column("Exchange", style="bold white", width=10)
    rates_table.add_column("Symbol", style="bold yellow", width=8)
    rates_table.add_column("Rate/8h", justify="right", width=12)
    rates_table.add_column("Annual APR", justify="right", width=12)
    rates_table.add_column("Trend", justify="center", width=10)
    rates_table.add_column("Updated", justify="right", width=10, style="dim")

    for row in scanner.get_all_rates_table():
        rate_str = row["rate_8h"]
        rate_float = float(rate_str.replace("%", "").replace("+", ""))
        rate_color = "green" if rate_float > 0 else "red" if rate_float < 0 else "white"

        trend = scanner.get_rate_trend(
            ExchangeName(row["exchange"]),
            row["symbol"]
        )

        rates_table.add_row(
            row["exchange"].upper(),
            row["symbol"],
            f"[{rate_color}]{rate_str}[/{rate_color}]",
            row["annual"],
            trend,
            row["updated"],
        )

    # ── Opportunities Table ───────────────────────────────────────────────────
    opps = scanner.find_opportunities()
    opps_table = Table(
        title="[bold]Delta-Neutral Opportunities[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green",
        border_style="dim",
    )
    opps_table.add_column("Symbol", style="bold yellow", width=8)
    opps_table.add_column("LONG on", style="green", width=10)
    opps_table.add_column("SHORT on", style="red", width=10)
    opps_table.add_column("Long Rate", justify="right", width=12)
    opps_table.add_column("Short Rate", justify="right", width=12)
    opps_table.add_column("Net/interval", justify="right", width=14)
    opps_table.add_column("Annual Yield", justify="right", width=14)

    if not opps:
        opps_table.add_row(
            *["-"] * 5,
            "[dim]No profitable opportunities found[/dim]",
            ""
        )
    else:
        for o in opps[:8]:
            annual = o.annual_yield_pct
            yield_color = "bright_green" if annual >= min_yield else "yellow"
            status = "[OK]" if annual >= min_yield else "[LOW]"

            opps_table.add_row(
                o.symbol,
                o.long_exchange.value.upper(),
                o.short_exchange.value.upper(),
                f"[dim]{o.long_rate * 100:+.4f}%[/dim]",
                f"[dim]{o.short_rate * 100:+.4f}%[/dim]",
                f"{o.net_funding_per_interval * 100:+.4f}%",
                f"[{yield_color}]{status} {annual:.2f}%[/{yield_color}]",
            )

    # ── Layout ───────────────────────────────────────────────────────────────
    from rich.layout import Layout
    from rich.padding import Padding

    content = Columns([rates_table, opps_table], expand=True, equal=True)
    return Panel(
        content,
        title="[bold cyan]DEX Funding Rate Scanner[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )


# ─── Delta Neutral Command ────────────────────────────────────────────────────

@app.command("delta-neutral")
def cmd_delta_neutral(
    symbol: str = typer.Option("BTC", help="Trading symbol"),
    exchanges_str: str = typer.Option("nado,decibel", "--exchanges", help="Exchanges (2 required)"),
    size_usd: float = typer.Option(100.0, "--size", help="Position size in USD per leg"),
    min_yield: float = typer.Option(5.0, "--min-yield", help="Min annual yield %% to open position"),
    max_hours: float = typer.Option(24.0, "--max-hours", help="Max position duration in hours"),
    leverage: int = typer.Option(1, "--leverage", help="Leverage"),
    check_interval: int = typer.Option(60, "--interval", help="Check interval in seconds"),
):
    """
    [bold]Delta-Neutral cross-exchange strategy.[/bold]

    Searches for funding rate differences between exchanges.
    Opens LONG on the exchange with lower/negative funding,
    SHORT on the exchange with higher/positive funding.
    Collects the spread as profit while staying market-neutral.

    Example:
      Nado BTC funding: +0.05%/8h -> SHORT on Nado
      Decibel BTC funding: -0.01%/8h -> LONG on Decibel
      Net profit: 0.06%/8h = ~6.5% annual
    """
    print_banner()
    exchange_names = [e.strip().lower() for e in exchanges_str.split(",")]

    async def _run():
        console.print(f"[cyan]Setting up exchanges: {exchange_names}[/cyan]")
        exs = {}
        for ex_name in exchange_names:
            try:
                ex = get_exchange(ex_name)
                if not ex.is_configured:
                    console.print(f"[yellow]WARN: {ex_name} not configured (check .env)[/yellow]")
                else:
                    exs[ex.name] = ex
                    console.print(f"[green]OK: {ex_name} connected[/green]")
            except Exception as e:
                console.print(f"[red]ERR: {ex_name} error: {e}[/red]")

        if len(exs) < 2:
            console.print("[red]ERROR: Need at least 2 configured exchanges for delta-neutral![/red]")
            return

        scanner = FundingScanner(exs, symbols=[symbol], min_annual_yield_pct=min_yield)
        strategy = DeltaNeutralStrategy(
            exchanges=exs,
            scanner=scanner,
            symbol=symbol,
            size_usd=size_usd,
            min_annual_yield=min_yield,
            max_duration_hours=max_hours,
            leverage=leverage,
        )

        console.print(Panel(
            f"[bold]Symbol:[/bold] {symbol}\n"
            f"[bold]Exchanges:[/bold] {', '.join(exchange_names)}\n"
            f"[bold]Size per leg:[/bold] ${size_usd:,.2f}\n"
            f"[bold]Min annual yield:[/bold] {min_yield}%\n"
            f"[bold]Max duration:[/bold] {max_hours}h\n"
            f"[bold]Leverage:[/bold] {leverage}x",
            title="[bold green]Delta-Neutral Config[/bold green]",
            border_style="green",
        ))

        console.print("[bold cyan]Starting strategy... Press Ctrl+C to stop[/bold cyan]\n")

        try:
            await strategy.run(check_interval_seconds=check_interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping strategy...[/yellow]")
            await strategy.stop()
            _print_session_stats(strategy.session)

    asyncio.run(_run())


# ─── Volume Command ───────────────────────────────────────────────────────────

@app.command("volume")
def cmd_volume(
    exchange: str = typer.Option("nado", "--exchange", "-e", help="Exchange to use"),
    symbol: str = typer.Option("BTC", help="Symbol to trade"),
    target: float = typer.Option(10_000.0, "--target", help="Target volume in USD"),
    duration: int = typer.Option(3600, "--duration", help="Duration in seconds"),
    slices: int = typer.Option(20, "--slices", help="Number of order slices"),
    leverage: int = typer.Option(1, "--leverage", help="Leverage"),
    native_twap: bool = typer.Option(True, "--twap/--no-twap", help="Use native TWAP"),
):
    """
    [bold]High-volume generation bot.[/bold]

    Generates trading volume via TWAP orders with randomized sizing.
    Alternates long/short to stay near delta-neutral.
    """
    print_banner()

    async def _run():
        ex = get_exchange(exchange)
        if not ex.is_configured:
            console.print(f"[red]ERROR: {exchange} not configured. Check .env[/red]")
            raise typer.Exit(1)

        strategy = VolumeGeneratorStrategy(
            exchange=ex,
            symbol=symbol,
            target_volume_usd=target,
            duration_seconds=duration,
            num_slices=slices,
            leverage=leverage,
            use_twap=native_twap,
        )

        console.print(Panel(
            f"[bold]Exchange:[/bold] {exchange.upper()}\n"
            f"[bold]Symbol:[/bold] {symbol}\n"
            f"[bold]Target volume:[/bold] ${target:,.0f}\n"
            f"[bold]Duration:[/bold] {duration//60}min\n"
            f"[bold]Slices:[/bold] {slices}\n"
            f"[bold]TWAP:[/bold] {'Native' if native_twap else 'Simulated'}",
            title="[bold blue]Volume Generator Config[/bold blue]",
            border_style="blue",
        ))

        try:
            await strategy.run()
        except KeyboardInterrupt:
            strategy.stop()
            console.print("\n[yellow]Stopped.[/yellow]")

        _print_session_stats(strategy.session)

    asyncio.run(_run())


# ─── Indicator Command ────────────────────────────────────────────────────────

@app.command("indicator")
def cmd_indicator(
    exchange: str = typer.Option("nado", "--exchange", "-e"),
    symbol: str = typer.Option("BTC", help="Symbol"),
    strategy: str = typer.Option("rsi", "--strategy", "-s",
        help="Strategy: rsi, ema, macd, bb, vwap"),
    timeframe: str = typer.Option("15m", "--timeframe", "-t",
        help="Candle timeframe: 1m, 5m, 15m, 1h, 4h"),
    size_usd: float = typer.Option(100.0, "--size", help="Position size USD"),
    leverage: int = typer.Option(1, "--leverage"),
    interval: int = typer.Option(60, "--interval", help="Check interval seconds"),
    # RSI
    rsi_period: int = typer.Option(14, "--rsi-period"),
    rsi_low: float = typer.Option(30.0, "--rsi-low"),
    rsi_high: float = typer.Option(70.0, "--rsi-high"),
    # EMA
    ema_fast: int = typer.Option(9, "--ema-fast"),
    ema_slow: int = typer.Option(21, "--ema-slow"),
):
    """
    [bold]Technical indicator-based trading.[/bold]

    Strategies:
      [green]rsi[/green]   - RSI mean reversion (long <30, short >70)
      [green]ema[/green]   - EMA crossover (fast/slow EMA cross)
      [green]macd[/green]  - MACD histogram momentum
      [green]bb[/green]    - Bollinger Band bounce
      [green]vwap[/green]  - VWAP crossover
    """
    print_banner()

    strat_map = {
        "rsi": IndicatorStrategy.RSI,
        "ema": IndicatorStrategy.EMA_CROSS,
        "macd": IndicatorStrategy.MACD,
        "bb": IndicatorStrategy.BOLLINGER,
        "vwap": IndicatorStrategy.VWAP,
    }
    strat_enum = strat_map.get(strategy.lower())
    if not strat_enum:
        console.print(f"[red]Unknown strategy: {strategy}. Use: {list(strat_map.keys())}[/red]")
        raise typer.Exit(1)

    async def _run():
        ex = get_exchange(exchange)
        if not ex.is_configured:
            console.print(f"[red]ERROR: {exchange} not configured[/red]")
            raise typer.Exit(1)

        trader = IndicatorTrader(
            exchange=ex,
            symbol=symbol,
            strategy=strat_enum,
            timeframe=timeframe,
            size_usd=size_usd,
            leverage=leverage,
            rsi_period=rsi_period,
            rsi_oversold=rsi_low,
            rsi_overbought=rsi_high,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
        )

        console.print(Panel(
            f"[bold]Exchange:[/bold] {exchange.upper()}\n"
            f"[bold]Strategy:[/bold] {strategy.upper()}\n"
            f"[bold]Symbol:[/bold] {symbol} | [bold]Timeframe:[/bold] {timeframe}\n"
            f"[bold]Size:[/bold] ${size_usd} | [bold]Leverage:[/bold] {leverage}x",
            title="[bold magenta]Indicator Trader Config[/bold magenta]",
            border_style="magenta",
        ))

        try:
            await trader.run(check_interval_seconds=interval)
        except KeyboardInterrupt:
            trader.stop()
            console.print("\n[yellow]Stopped.[/yellow]")
        _print_session_stats(trader.session)

    asyncio.run(_run())


# ─── Status Command ───────────────────────────────────────────────────────────

@app.command("status")
def cmd_status(
    exchange: str = typer.Option("all", "--exchange", "-e",
        help="Exchange: nado, decibel, rise, or 'all'"),
):
    """
    [bold]Check account balances and open positions.[/bold]
    """
    print_banner()

    async def _run():
        exchanges_to_check = {}
        if exchange == "all":
            exchanges_to_check = get_all_exchanges()
        else:
            ex = get_exchange(exchange)
            exchanges_to_check[ex.name] = ex

        table = Table(
            title="Account Status",
            box=box.ROUNDED,
            header_style="bold cyan",
        )
        table.add_column("Exchange", style="bold white")
        table.add_column("Asset")
        table.add_column("Balance", justify="right")
        table.add_column("Free", justify="right")
        table.add_column("Configured", justify="center")

        for ex_name, ex in exchanges_to_check.items():
            is_cfg = "✅" if ex.is_configured else "❌"
            if ex.is_configured:
                try:
                    balance = await ex.fetch_balance()
                    assets = list(balance.keys())
                    for i, asset in enumerate(assets):
                        if asset == "free":
                            continue
                        table.add_row(
                            ex_name.value.upper() if i == 0 else "",
                            asset,
                            f"${balance[asset]:,.4f}",
                            f"${balance.get('free', 0):,.4f}" if i == 0 else "",
                            is_cfg if i == 0 else "",
                        )
                except Exception as e:
                    table.add_row(ex_name.value.upper(), "—", f"Error: {e}", "", is_cfg)
            else:
                table.add_row(ex_name.value.upper(), "—", "Not configured", "", is_cfg)

        console.print(table)

        # Open positions
        pos_table = Table(
            title="Open Positions",
            box=box.ROUNDED,
            header_style="bold green",
        )
        pos_table.add_column("Exchange")
        pos_table.add_column("Symbol")
        pos_table.add_column("Side")
        pos_table.add_column("Size", justify="right")
        pos_table.add_column("Entry", justify="right")
        pos_table.add_column("Mark", justify="right")
        pos_table.add_column("uPnL", justify="right")

        has_positions = False
        for ex_name, ex in exchanges_to_check.items():
            if ex.is_configured:
                try:
                    positions = await ex.fetch_positions()
                    for pos in positions:
                        has_positions = True
                        upnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                        pos_table.add_row(
                            ex_name.value.upper(),
                            pos.symbol,
                            f"[{'green' if pos.side.value == 'long' else 'red'}]{pos.side.value.upper()}[/]",
                            f"{pos.size:.4f}",
                            f"${pos.entry_price:,.2f}",
                            f"${pos.mark_price:,.2f}",
                            f"[{upnl_color}]${pos.unrealized_pnl:,.4f}[/{upnl_color}]",
                        )
                except Exception:
                    pass

        if not has_positions:
            pos_table.add_row("-", "-", "-", "No open positions", "", "", "")

        console.print(pos_table)

    asyncio.run(_run())


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _print_session_stats(session):
    """Print session summary."""
    console.print(Panel(
        f"[bold]Session ID:[/bold] {session.session_id}\n"
        f"[bold]Duration:[/bold] {session.duration_str}\n"
        f"[bold]Total Trades:[/bold] {session.total_trades}\n"
        f"[bold]Volume Generated:[/bold] ${session.total_volume_usd:,.2f}\n"
        f"[bold]Funding Collected:[/bold] ${session.funding_collected:.4f}\n"
        f"[bold]Realized PnL:[/bold] ${session.realized_pnl:,.4f}\n"
        f"[bold]Net PnL:[/bold] [{'green' if session.net_pnl >= 0 else 'red'}]"
        f"${session.net_pnl:,.4f}[/]",
        title="[bold]📋 Session Summary[/bold]",
        border_style="cyan",
    ))


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    app()


if __name__ == "__main__":
    main()
