"""
bot_trade/exchanges/base.py — Abstract base class for all exchange adapters
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import (
    ExchangeName, FundingRate, Ticker, OrderBook,
    Position, Order, OrderSide, OrderType
)


class BaseExchange(ABC):
    """
    Unified interface for all exchanges.
    Each exchange must implement these methods.
    """

    name: ExchangeName

    # ─── Market Data (Public — no auth needed) ────────────────────────────────

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """Fetch best bid/ask/last for a symbol."""
        ...

    @abstractmethod
    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        """Fetch order book."""
        ...

    @abstractmethod
    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """
        Fetch current funding rate for a perpetual market.
        Rate is expressed as a decimal (0.0001 = 0.01%).
        """
        ...

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> list[dict]:
        """
        Fetch OHLCV candles.
        Returns list of dicts with keys: timestamp, open, high, low, close, volume
        """
        ...

    # ─── Account Data (Private — requires auth) ───────────────────────────────

    @abstractmethod
    async def fetch_positions(self) -> list[Position]:
        """Get all open positions."""
        ...

    @abstractmethod
    async def fetch_balance(self) -> dict[str, float]:
        """Get account balances. Returns {asset: amount}."""
        ...

    # ─── Trading (Private) ────────────────────────────────────────────────────

    @abstractmethod
    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> Order:
        """Place a market order."""
        ...

    @abstractmethod
    async def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        price: float,
        leverage: int = 1,
        reduce_only: bool = False,
        post_only: bool = False
    ) -> Order:
        """Place a limit order."""
        ...

    @abstractmethod
    async def place_twap_order(
        self,
        symbol: str,
        side: OrderSide,
        total_size: float,
        duration_seconds: int,
        num_slices: int = 10,
        max_price: Optional[float] = None
    ) -> Order:
        """
        Place a TWAP order (time-weighted average price).
        Splits total_size into num_slices over duration_seconds.
        """
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an open order."""
        ...

    @abstractmethod
    async def close_position(self, symbol: str, slippage_pct: float = 0.5) -> Order:
        """Close an open position at market."""
        ...

    # ─── Utility ──────────────────────────────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        """Return True if credentials are available."""
        return False

    async def check_health(self) -> bool:
        """Check if exchange is reachable."""
        try:
            # Try fetching a common ticker as health check
            await self.fetch_ticker("BTC")
            return True
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(exchange={self.name.value})"
