"""
bot_trade/exchanges/rise.py — Rise Trade adapter (Rise Chain / EVM)

Rise Trade is built on Rise Chain, an EVM-compatible high-speed L2.
API docs: https://developer.rise.trade/reference

Trading via:
  - REST API (if available)
  - EVM smart contract calls (via web3.py) as fallback
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import aiohttp

from ..config import get_config, RiseConfig
from ..models import (
    ExchangeName, FundingRate, Ticker, OrderBook,
    Position, Order, OrderSide, OrderType
)
from .base import BaseExchange

# Rise Trade API endpoints (update when official docs become available)
RISE_MAINNET_API = "https://api.rise.trade"
RISE_TESTNET_API = "https://api.testnet.rise.trade"

# Rise Chain RPC
RISE_MAINNET_RPC = "https://mainnet.riselabs.xyz"
RISE_TESTNET_RPC = "https://testnet.riselabs.xyz"


class RiseExchange(BaseExchange):
    """
    Rise Trade perpetuals adapter.

    NOTE: Rise Trade API docs require login at developer.rise.trade/reference.
    This adapter implements the expected API surface based on common DEX perp
    patterns (similar to Hyperliquid/GMX). Update endpoint paths once you
    have API access.
    """

    name = ExchangeName.RISE

    def __init__(self):
        self.cfg: RiseConfig = get_config().rise
        self._api_base = (
            RISE_TESTNET_API if self.cfg.env == "testnet" else RISE_MAINNET_API
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._web3 = None  # lazy-loaded

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.cfg.api_key:
                headers["X-API-Key"] = self.cfg.api_key
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_web3(self):
        """Lazily initialize Web3 for EVM contract calls."""
        if self._web3 is None:
            try:
                from web3 import AsyncWeb3, AsyncHTTPProvider
                self._web3 = AsyncWeb3(
                    AsyncHTTPProvider(self.cfg.rpc_url or RISE_MAINNET_RPC)
                )
            except ImportError:
                raise RuntimeError("web3 not installed. Run: pip install web3")
        return self._web3

    # ─── Market Data ─────────────────────────────────────────────────────────

    async def fetch_ticker(self, symbol: str) -> Ticker:
        """
        Fetch ticker from Rise Trade API.
        Endpoint pattern: GET /v1/markets/{symbol}/ticker
        Update path once official docs are available.
        """
        session = await self._get_session()
        sym = symbol.upper()

        # Try common REST patterns for DEX perp APIs
        endpoints_to_try = [
            f"{self._api_base}/v1/markets/{sym}-PERP/ticker",
            f"{self._api_base}/v1/ticker?symbol={sym}",
            f"{self._api_base}/api/v1/prices?symbol={sym}",
        ]

        for endpoint in endpoints_to_try:
            try:
                async with session.get(endpoint) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        mark = float(
                            data.get("markPrice",
                            data.get("mark_price",
                            data.get("price", 0)))
                        )
                        bid = float(data.get("bid", data.get("bestBid", mark * 0.9999)))
                        ask = float(data.get("ask", data.get("bestAsk", mark * 1.0001)))

                        return Ticker(
                            exchange=self.name,
                            symbol=symbol,
                            bid=bid,
                            ask=ask,
                            last=float(data.get("lastPrice", data.get("last", mark))),
                            mark_price=mark,
                        )
            except Exception:
                continue

        # Fallback: raise informative error
        raise RuntimeError(
            f"Rise Trade API not reachable. Please verify your Rise API credentials "
            f"at developer.rise.trade and update RISE_API_KEY in .env"
        )

    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        session = await self._get_session()
        sym = symbol.upper()

        try:
            async with session.get(
                f"{self._api_base}/v1/orderbook/{sym}-PERP",
                params={"depth": depth}
            ) as resp:
                data = await resp.json()

            bids = [(float(b[0]), float(b[1])) for b in data.get("bids", [])[:depth]]
            asks = [(float(a[0]), float(a[1])) for a in data.get("asks", [])[:depth]]
        except Exception:
            bids, asks = [], []

        return OrderBook(exchange=self.name, symbol=symbol, bids=bids, asks=asks)

    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """
        Fetch funding rate from Rise Trade API.
        Rise uses perpetual funding (likely 8h interval based on chain).
        """
        session = await self._get_session()
        sym = symbol.upper()

        endpoints_to_try = [
            f"{self._api_base}/v1/markets/{sym}-PERP/funding",
            f"{self._api_base}/v1/funding?symbol={sym}",
            f"{self._api_base}/api/v1/markets/{sym}/funding_rate",
        ]

        for endpoint in endpoints_to_try:
            try:
                async with session.get(endpoint) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rate = float(
                            data.get("fundingRate",
                            data.get("funding_rate",
                            data.get("rate", 0)))
                        )
                        interval_h = float(data.get("interval", 8))
                        rate_annual = rate * (8760 / interval_h)

                        return FundingRate(
                            exchange=self.name,
                            symbol=symbol,
                            rate=rate,
                            rate_annual=rate_annual,
                            interval_hours=interval_h,
                        )
            except Exception:
                continue

        # Return zero if API unavailable (bot will skip this exchange for arb)
        return FundingRate(
            exchange=self.name,
            symbol=symbol,
            rate=0.0,
            rate_annual=0.0,
        )

    async def fetch_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> list[dict]:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._api_base}/v1/candles/{symbol.upper()}-PERP",
                params={"interval": interval, "limit": limit}
            ) as resp:
                data = await resp.json()

            candles = []
            for c in (data if isinstance(data, list) else data.get("candles", [])):
                candles.append({
                    "timestamp": c.get("t", c.get("time", 0)),
                    "open": float(c.get("o", c.get("open", 0))),
                    "high": float(c.get("h", c.get("high", 0))),
                    "low": float(c.get("l", c.get("low", 0))),
                    "close": float(c.get("c", c.get("close", 0))),
                    "volume": float(c.get("v", c.get("volume", 0))),
                })
            return candles
        except Exception:
            return []

    # ─── Account Data ────────────────────────────────────────────────────────

    async def fetch_positions(self) -> list[Position]:
        session = await self._get_session()
        try:
            async with session.get(f"{self._api_base}/v1/positions") as resp:
                data = await resp.json()

            positions = []
            for p in (data if isinstance(data, list) else data.get("positions", [])):
                side = OrderSide.LONG if p.get("side", "long") == "long" else OrderSide.SHORT
                positions.append(Position(
                    exchange=self.name,
                    symbol=p.get("symbol", "").replace("-PERP", ""),
                    side=side,
                    size=float(p.get("size", 0)),
                    entry_price=float(p.get("entryPrice", 0)),
                    mark_price=float(p.get("markPrice", 0)),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                ))
            return positions
        except Exception:
            return []

    async def fetch_balance(self) -> dict[str, float]:
        session = await self._get_session()
        try:
            async with session.get(f"{self._api_base}/v1/account") as resp:
                data = await resp.json()
            return {
                "USDC": float(data.get("balance", 0)),
                "free": float(data.get("freeCollateral", 0)),
            }
        except Exception:
            return {}

    # ─── Trading ─────────────────────────────────────────────────────────────

    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> Order:
        session = await self._get_session()
        payload = {
            "symbol": f"{symbol.upper()}-PERP",
            "side": "buy" if side == OrderSide.LONG else "sell",
            "type": "market",
            "size": str(size),
            "leverage": leverage,
            "reduceOnly": reduce_only,
        }
        try:
            async with session.post(
                f"{self._api_base}/v1/orders",
                json=payload
            ) as resp:
                data = await resp.json()

            return Order(
                exchange=self.name,
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                size=size,
                price=None,
                order_id=str(data.get("id", data.get("orderId", ""))),
                status=data.get("status", "submitted"),
            )
        except Exception as e:
            raise RuntimeError(f"Rise Trade order failed: {e}")

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
        session = await self._get_session()
        payload = {
            "symbol": f"{symbol.upper()}-PERP",
            "side": "buy" if side in (OrderSide.LONG, OrderSide.BUY) else "sell",
            "type": "limit",
            "size": str(size),
            "price": str(price),
            "leverage": leverage,
            "reduceOnly": reduce_only,
            "postOnly": post_only,
        }
        try:
            async with session.post(f"{self._api_base}/v1/orders", json=payload) as resp:
                data = await resp.json()
            return Order(
                exchange=self.name, symbol=symbol, side=side,
                order_type=OrderType.LIMIT, size=size, price=price,
                order_id=str(data.get("id", "")), status="open",
            )
        except Exception as e:
            raise RuntimeError(f"Rise limit order failed: {e}")

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
        Rise Trade may not have native TWAP. Simulate by scheduling
        smaller market orders. The bot engine handles timing.
        """
        # For Rise: return a placeholder and let VolumeStrategy handle slicing
        return Order(
            exchange=self.name, symbol=symbol, side=side,
            order_type=OrderType.TWAP, size=total_size, price=max_price,
            order_id="twap_simulated", status="pending",
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        session = await self._get_session()
        try:
            async with session.delete(
                f"{self._api_base}/v1/orders/{order_id}"
            ) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    async def close_position(self, symbol: str, slippage_pct: float = 0.5) -> Order:
        positions = await self.fetch_positions()
        for pos in positions:
            if pos.symbol.upper() == symbol.upper():
                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG
                return await self.place_market_order(
                    symbol, close_side, pos.size, reduce_only=True
                )
        raise RuntimeError(f"No open position found for {symbol} on Rise")

    @property
    def is_configured(self) -> bool:
        return self.cfg.is_configured
