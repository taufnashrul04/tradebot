"""
bot_trade/models.py — Shared data models across all exchanges
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class OrderSide(str, Enum):
    LONG = "long"
    SHORT = "short"
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"


class ExchangeName(str, Enum):
    NADO = "nado"
    DECIBEL = "decibel"
    RISE = "rise"


class TradingMode(str, Enum):
    VOLUME = "volume"
    MARKET_MAKER = "mm"
    DELTA_NEUTRAL = "delta-neutral"
    INDICATOR = "indicator"
    FUNDING_ARB = "funding-arb"


@dataclass
class FundingRate:
    exchange: ExchangeName
    symbol: str
    rate: float                   # e.g. 0.0001 = 0.01%
    rate_annual: float            # annualized
    next_funding_time: Optional[datetime] = None
    interval_hours: float = 8.0   # funding interval in hours
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def rate_pct(self) -> float:
        return self.rate * 100

    def __repr__(self) -> str:
        return (
            f"FundingRate({self.exchange.value} {self.symbol} "
            f"rate={self.rate_pct:.4f}% annual={self.rate_annual:.2f}%)"
        )


@dataclass
class FundingDiff:
    """Funding rate comparison between two exchanges for the same symbol."""
    symbol: str
    long_exchange: ExchangeName    # exchange where we go LONG (pays funding or receives)
    short_exchange: ExchangeName   # exchange where we go SHORT
    long_rate: float               # funding rate on long exchange
    short_rate: float              # funding rate on short exchange
    net_funding_per_interval: float  # net funding collected per interval (positive = profit)
    annual_yield_pct: float        # annualized yield from this arb
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_profitable(self) -> bool:
        return self.net_funding_per_interval > 0

    @property
    def diff_pct(self) -> float:
        return abs(self.long_rate - self.short_rate) * 100

    def __repr__(self) -> str:
        direction = "→" if self.is_profitable else "✗"
        return (
            f"FundingDiff {direction} {self.symbol}: "
            f"LONG {self.long_exchange.value}({self.long_rate*100:.4f}%) "
            f"SHORT {self.short_exchange.value}({self.short_rate*100:.4f}%) "
            f"net={self.net_funding_per_interval*100:.4f}%/interval "
            f"annual={self.annual_yield_pct:.1f}%"
        )


@dataclass
class Ticker:
    exchange: ExchangeName
    symbol: str
    bid: float
    ask: float
    last: float
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    volume_24h: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / self.mid * 100


@dataclass
class OrderBook:
    exchange: ExchangeName
    symbol: str
    bids: list[tuple[float, float]]   # [(price, size), ...]
    asks: list[tuple[float, float]]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 0.0

    @property
    def mid(self) -> float:
        return (self.best_bid + self.best_ask) / 2


@dataclass
class Position:
    exchange: ExchangeName
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float = 0.0
    leverage: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def notional_usd(self) -> float:
        return self.size * self.mark_price


@dataclass
class Order:
    exchange: ExchangeName
    symbol: str
    side: OrderSide
    order_type: OrderType
    size: float
    price: Optional[float]
    order_id: Optional[str] = None
    status: str = "pending"
    filled_size: float = 0.0
    avg_fill_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeltaNeutralPosition:
    """Tracks a paired long/short across two exchanges."""
    symbol: str
    long_exchange: ExchangeName
    short_exchange: ExchangeName
    long_order: Optional[Order]
    short_order: Optional[Order]
    size: float
    target_funding_profit: float   # expected funding profit per interval
    session_id: str = ""
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


@dataclass
class SessionStats:
    session_id: str
    mode: TradingMode
    exchange: str
    symbol: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    total_volume_usd: float = 0.0
    total_trades: int = 0
    realized_pnl: float = 0.0
    funding_collected: float = 0.0
    fees_paid: float = 0.0

    @property
    def net_pnl(self) -> float:
        return self.realized_pnl + self.funding_collected - self.fees_paid

    @property
    def duration_str(self) -> str:
        delta = datetime.utcnow() - self.started_at
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
