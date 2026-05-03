"""
bot_trade/strategies/funding_scanner.py

Funding Rate Scanner & Arbitrage Engine

Core logic:
  - Poll funding rates across Nado, Decibel, Rise simultaneously
  - Compare all pairs: (Nado vs Decibel), (Nado vs Rise), (Decibel vs Rise)
  - Find profitable cross-exchange delta-neutral opportunities:

    Example:
      Nado BTC funding = +0.05%/8h  (longs PAY shorts)
      Decibel BTC funding = -0.02%/8h (shorts PAY longs)

      Strategy:
        - SHORT on Nado → RECEIVE 0.05%/8h funding
        - LONG on Decibel → RECEIVE 0.02%/8h funding (shorts are paying us)
        - Net: +0.07%/8h = ~7.6% annualized

  - Display a live table of all funding rates and opportunities
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from itertools import combinations
from typing import Optional

from loguru import logger

from ..models import (
    ExchangeName, FundingRate, FundingDiff,
    OrderSide, DeltaNeutralPosition
)
from ..exchanges.base import BaseExchange


class FundingScanner:
    """
    Continuously scans funding rates across all configured exchanges
    and identifies cross-exchange delta-neutral arbitrage opportunities.
    """

    def __init__(
        self,
        exchanges: dict[ExchangeName, BaseExchange],
        symbols: list[str] = None,
        min_annual_yield_pct: float = 5.0,  # min annualized yield to flag
    ):
        self.exchanges = exchanges
        self.symbols = symbols or ["BTC", "ETH", "SOL"]
        self.min_annual_yield_pct = min_annual_yield_pct

        # Latest funding rates cache: {(exchange, symbol): FundingRate}
        self._rates: dict[tuple[ExchangeName, str], FundingRate] = {}

        # History of rate checks for trend analysis
        self._history: list[dict] = []

    # ─── Core Scan ────────────────────────────────────────────────────────────

    async def scan_all(self) -> dict[tuple[ExchangeName, str], FundingRate]:
        """
        Fetch funding rates from all exchanges for all symbols concurrently.
        Returns updated rates cache.
        """
        tasks = []
        for ex_name, exchange in self.exchanges.items():
            for symbol in self.symbols:
                tasks.append(self._fetch_one(exchange, symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, FundingRate):
                key = (result.exchange, result.symbol)
                self._rates[key] = result
            elif isinstance(result, Exception):
                logger.warning(f"Funding fetch error: {result}")

        # Record history snapshot
        self._history.append({
            "timestamp": datetime.utcnow(),
            "rates": dict(self._rates)
        })
        # Keep last 100 snapshots
        if len(self._history) > 100:
            self._history.pop(0)

        return self._rates

    async def _fetch_one(
        self, exchange: BaseExchange, symbol: str
    ) -> FundingRate:
        try:
            rate = await asyncio.wait_for(
                exchange.fetch_funding_rate(symbol),
                timeout=10.0
            )
            logger.debug(f"Fetched {rate}")
            return rate
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching funding from {exchange.name.value} {symbol}")
            return FundingRate(exchange=exchange.name, symbol=symbol, rate=0.0, rate_annual=0.0)
        except Exception as e:
            logger.warning(f"Error fetching {exchange.name.value} {symbol} funding: {e}")
            return FundingRate(exchange=exchange.name, symbol=symbol, rate=0.0, rate_annual=0.0)

    # ─── Opportunity Detection ────────────────────────────────────────────────

    def find_opportunities(self) -> list[FundingDiff]:
        """
        Analyze cached rates to find profitable delta-neutral opportunities.

        Logic:
          For each (exchange_A, exchange_B) pair and each symbol:
            net_funding = rate_A + rate_B (when we take opposing sides)

          If funding_A > 0:
            → SHORT on A (receive funding_A)
            → LONG on B (if funding_B < 0, also receive |funding_B|)
            → Total received = funding_A + |funding_B|  if B negative
            → Total received = funding_A - funding_B    if B positive

          Generalized:
            SHORT on the exchange with HIGHER funding rate
            LONG on the exchange with LOWER (or more negative) funding rate
            Net = rate_high - rate_low  (per interval)
        """
        opportunities: list[FundingDiff] = []
        exchange_names = list(self.exchanges.keys())

        for symbol in self.symbols:
            # Gather all rates for this symbol
            symbol_rates: list[FundingRate] = []
            for ex_name in exchange_names:
                key = (ex_name, symbol)
                if key in self._rates:
                    symbol_rates.append(self._rates[key])

            if len(symbol_rates) < 2:
                continue

            # Compare all pairs
            for rate_a, rate_b in combinations(symbol_rates, 2):
                # Determine which to short (higher funding = shorts collect)
                # and which to long (lower funding = longs pay less / collect)
                if rate_a.rate >= rate_b.rate:
                    short_rate = rate_a
                    long_rate = rate_b
                else:
                    short_rate = rate_b
                    long_rate = rate_a

                # Net funding per interval:
                # When rate > 0: longs pay shorts
                # When rate < 0: shorts pay longs
                # We SHORT on short_rate.exchange → collect short_rate (if positive)
                # We LONG on long_rate.exchange → collect |long_rate| (if negative)
                # Or pay long_rate (if positive, but less than short side)
                net_per_interval = short_rate.rate - long_rate.rate

                if net_per_interval <= 0:
                    continue  # No profit opportunity

                # Annualize: intervals per year = 8760 / interval_hours
                # Use the shorter interval (more conservative)
                interval_h = min(short_rate.interval_hours, long_rate.interval_hours)
                intervals_per_year = 8760 / interval_h
                annual_yield_pct = net_per_interval * intervals_per_year * 100

                diff = FundingDiff(
                    symbol=symbol,
                    long_exchange=long_rate.exchange,
                    short_exchange=short_rate.exchange,
                    long_rate=long_rate.rate,
                    short_rate=short_rate.rate,
                    net_funding_per_interval=net_per_interval,
                    annual_yield_pct=annual_yield_pct,
                )
                opportunities.append(diff)

        # Sort by best opportunity first
        opportunities.sort(key=lambda x: x.annual_yield_pct, reverse=True)
        return opportunities

    def get_best_opportunity(self, symbol: str = "BTC") -> Optional[FundingDiff]:
        """Get the single best funding arb opportunity for a symbol."""
        opps = [o for o in self.find_opportunities() if o.symbol == symbol]
        return opps[0] if opps else None

    def get_all_rates_table(self) -> list[dict]:
        """
        Return all current rates as a list of dicts for display.
        """
        rows = []
        for (ex, sym), rate in self._rates.items():
            rows.append({
                "exchange": ex.value,
                "symbol": sym,
                "rate_pct": f"{rate.rate * 100:+.4f}%",
                "rate_8h": f"{rate.rate * 100:+.4f}%",
                "annual": f"{rate.rate_annual * 100:.2f}%",
                "interval": f"{rate.interval_hours:.0f}h",
                "updated": rate.timestamp.strftime("%H:%M:%S"),
            })
        rows.sort(key=lambda x: (x["symbol"], x["exchange"]))
        return rows

    def get_opportunities_table(self) -> list[dict]:
        """Return opportunities as table rows for display."""
        opps = self.find_opportunities()
        rows = []
        for o in opps:
            rows.append({
                "symbol": o.symbol,
                "long_on": o.long_exchange.value,
                "short_on": o.short_exchange.value,
                "long_rate": f"{o.long_rate * 100:+.4f}%",
                "short_rate": f"{o.short_rate * 100:+.4f}%",
                "net_per_interval": f"{o.net_funding_per_interval * 100:+.4f}%",
                "annual_yield": f"{o.annual_yield_pct:.2f}%",
                "status": "✅ PROFITABLE" if o.annual_yield_pct >= self.min_annual_yield_pct else "⚠️ LOW",
            })
        return rows

    # ─── Rate History & Trend ────────────────────────────────────────────────

    def get_rate_trend(
        self, exchange: ExchangeName, symbol: str, lookback: int = 10
    ) -> str:
        """Compute simple trend: rising, falling, or stable."""
        rates = []
        for snap in self._history[-lookback:]:
            key = (exchange, symbol)
            r = snap["rates"].get(key)
            if r:
                rates.append(r.rate)

        if len(rates) < 3:
            return "~"

        # Compare first half vs second half
        mid = len(rates) // 2
        avg_early = sum(rates[:mid]) / mid
        avg_late = sum(rates[mid:]) / (len(rates) - mid)

        diff = avg_late - avg_early
        threshold = 0.0001  # 0.01%

        if diff > threshold:
            return "↑ Rising"
        elif diff < -threshold:
            return "↓ Falling"
        else:
            return "→ Stable"
