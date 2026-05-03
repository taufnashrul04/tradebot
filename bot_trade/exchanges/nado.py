"""
bot_trade/exchanges/nado.py — Nado Protocol adapter (Ink blockchain)

Uses:
  - nado-python-sdk (pip install nado-protocol)
  - nado-cli for market data (subprocess fallback)
  - REST API at https://api.nado.xyz
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from datetime import datetime
from typing import Optional

import aiohttp

from ..config import get_config, NadoConfig
from ..models import (
    ExchangeName, FundingRate, Ticker, OrderBook,
    Position, Order, OrderSide, OrderType
)
from .base import BaseExchange

# Nado REST API base URLs
NADO_MAINNET_API = "https://api.nado.xyz"
NADO_TESTNET_API = "https://api.testnet.nado.xyz"


class NadoExchange(BaseExchange):
    """
    Nado Protocol adapter.

    Market data via REST API (no auth needed).
    Trading via nado-python-sdk (requires private key).

    Symbol convention: "BTC" maps to BTC-PERP (product_id=1)
    """

    name = ExchangeName.NADO

    # Known product IDs: even = spot, odd = perp
    SYMBOL_TO_PERP_ID: dict[str, int] = {
        "BTC": 1,
        "ETH": 3,
        "SOL": 5,
        "ARB": 7,
    }

    SYMBOL_TO_SPOT_ID: dict[str, int] = {
        "USDT": 0,
        "BTC": 2,
        "ETH": 4,
        "SOL": 6,
    }

    def __init__(self):
        self.cfg: NadoConfig = get_config().nado
        self._api_base = (
            NADO_TESTNET_API if "testnet" in self.cfg.env.lower()
            else NADO_MAINNET_API
        )
        self._client = None   # nado_protocol SDK client (lazy-loaded)
        self._session: Optional[aiohttp.ClientSession] = None

    # ─── Session management ───────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self._api_base,
                headers={"Content-Type": "application/json"}
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ─── SDK Client (lazy init) ───────────────────────────────────────────────

    def _get_sdk_client(self):
        """Lazily initialize the nado-protocol Python SDK client."""
        if self._client is None:
            try:
                from nado_protocol.client import create_nado_client, NadoClientMode
                mode_map = {
                    "nadoMainnet": NadoClientMode.MAINNET,
                    "nadoTestnet": NadoClientMode.TESTNET,
                    "devnet": NadoClientMode.DEVNET,
                }
                mode = mode_map.get(self.cfg.env, NadoClientMode.MAINNET)
                self._client = create_nado_client(mode, self.cfg.private_key)
            except ImportError:
                raise RuntimeError(
                    "nado-protocol SDK not installed. Run: pip install nado-protocol"
                )
        return self._client

    # ─── Market Data ─────────────────────────────────────────────────────────

    async def fetch_ticker(self, symbol: str) -> Ticker:
        """Fetch best bid/ask from Nado orderbook."""
        session = await self._get_session()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())
        if product_id is None:
            raise ValueError(f"Unknown symbol: {symbol}")

        async with session.get(f"/v1/perp/{product_id}/orderbook") as resp:
            data = await resp.json()

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        best_bid = float(bids[0][0]) if bids else 0.0
        best_ask = float(asks[0][0]) if asks else 0.0
        last = (best_bid + best_ask) / 2

        return Ticker(
            exchange=self.name,
            symbol=symbol,
            bid=best_bid,
            ask=best_ask,
            last=last,
        )

    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        session = await self._get_session()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())

        async with session.get(
            f"/v1/perp/{product_id}/orderbook",
            params={"depth": depth}
        ) as resp:
            data = await resp.json()

        bids = [(float(p), float(s)) for p, s in (data.get("bids") or [])[:depth]]
        asks = [(float(p), float(s)) for p, s in (data.get("asks") or [])[:depth]]

        return OrderBook(exchange=self.name, symbol=symbol, bids=bids, asks=asks)

    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """
        Fetch current funding rate for a perp market.
        Nado uses 8-hour funding intervals.
        """
        session = await self._get_session()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())

        # Try REST endpoint for funding
        try:
            async with session.get(f"/v1/perp/{product_id}/funding") as resp:
                data = await resp.json()

            rate = float(data.get("fundingRate", 0))
            # Nado may return rate as 8h rate. Annualize: rate * 3 * 365
            rate_annual = rate * 3 * 365

            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=rate,
                rate_annual=rate_annual,
                interval_hours=8.0,
            )
        except Exception:
            # Fallback: try via nado CLI subprocess
            return await self._fetch_funding_via_cli(symbol)

    async def _fetch_funding_via_cli(self, symbol: str) -> FundingRate:
        """Fallback: use nado-cli to get funding rate."""
        try:
            result = await asyncio.create_subprocess_exec(
                "nado", "market", "funding", symbol, "--format", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            data = json.loads(stdout.decode())
            rate = float(data.get("fundingRate", 0))
            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=rate,
                rate_annual=rate * 3 * 365,
                interval_hours=8.0,
            )
        except Exception:
            # Return zero rate if all fails (bot will skip this exchange)
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
        """Fetch OHLCV candles."""
        session = await self._get_session()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())

        # Map interval to seconds
        interval_map = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "4h": 14400, "1d": 86400,
        }
        period = interval_map.get(interval, 3600)

        async with session.get(
            f"/v1/perp/{product_id}/candles",
            params={"period": period, "limit": limit}
        ) as resp:
            data = await resp.json()

        candles = []
        for c in data:
            candles.append({
                "timestamp": c.get("t", 0),
                "open": float(c.get("o", 0)),
                "high": float(c.get("h", 0)),
                "low": float(c.get("l", 0)),
                "close": float(c.get("c", 0)),
                "volume": float(c.get("v", 0)),
            })
        return candles

    # ─── Account Data ────────────────────────────────────────────────────────

    async def fetch_positions(self) -> list[Position]:
        client = self._get_sdk_client()
        positions = []
        try:
            # Use SDK to get positions
            raw = client.account.get_positions()
            for p in (raw or []):
                side = OrderSide.LONG if p.get("isLong") else OrderSide.SHORT
                symbol = self._product_id_to_symbol(p.get("productId", 0))
                positions.append(Position(
                    exchange=self.name,
                    symbol=symbol,
                    side=side,
                    size=float(p.get("amount", 0)),
                    entry_price=float(p.get("avgEntryPrice", 0)),
                    mark_price=float(p.get("markPrice", 0)),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                ))
        except Exception:
            pass
        return positions

    async def fetch_balance(self) -> dict[str, float]:
        client = self._get_sdk_client()
        try:
            summary = client.account.get_summary()
            return {
                "USDT": float(summary.get("totalBalance", 0)),
                "free": float(summary.get("freeBalance", 0)),
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
        """
        Place market order via nado-cli subprocess (most reliable method).
        """
        cmd = ["nado", "trade"]
        side_cmd = "long" if side == OrderSide.LONG else "short"
        if reduce_only:
            side_cmd = "close"
            cmd.extend(["close", symbol, "--force", "--format", "json"])
        else:
            cmd.extend([
                side_cmd, symbol, str(size),
                "--leverage", str(leverage),
                "--force",   # skip confirmation
                "--format", "json"
            ])

        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise RuntimeError(f"Nado order failed: {stderr.decode()}")

        try:
            data = json.loads(stdout.decode())
        except Exception:
            data = {}

        return Order(
            exchange=self.name,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            size=size,
            price=None,
            order_id=data.get("digest", data.get("orderId", "")),
            status="submitted",
        )

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
        """Place limit order via nado-protocol SDK."""
        from nado_protocol.engine_client.types.execute import OrderParams, PlaceOrderParams, SubaccountParams
        from nado_protocol.utils.expiration import OrderType as NadoOrderType, get_expiration_timestamp
        from nado_protocol.utils.math import to_pow_10, to_x18
        from nado_protocol.utils.nonce import gen_order_nonce
        from nado_protocol.utils.order import build_appendix

        client = self._get_sdk_client()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())
        is_long = side == OrderSide.LONG

        appendix_type = NadoOrderType.POST_ONLY if post_only else NadoOrderType.DEFAULT
        amount = to_pow_10(size, 17)  # 0.1 BTC = 10^17
        if not is_long:
            amount = -amount  # negative for short

        order = OrderParams(
            sender=SubaccountParams(
                subaccount_owner=client.context.engine_client.signer.address,
                subaccount_name=self.cfg.subaccount_name,
            ),
            priceX18=to_x18(price),
            amount=amount,
            expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
            nonce=gen_order_nonce(),
            appendix=build_appendix(order_type=appendix_type),
        )

        res = client.market.place_order({"product_id": product_id, "order": order})

        return Order(
            exchange=self.name,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            size=size,
            price=price,
            order_id=str(res.get("id", "")),
            status="open",
        )

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
        Place TWAP order via nado-protocol TriggerClient.
        Splits total_size into num_slices over duration_seconds.
        """
        from nado_protocol.trigger_client import TriggerClient
        from nado_protocol.trigger_client.types import TriggerClientOpts
        from nado_protocol.utils.math import to_x18
        from nado_protocol.utils.expiration import get_expiration_timestamp

        client = self._get_sdk_client()
        product_id = self.SYMBOL_TO_PERP_ID.get(symbol.upper())
        is_long = side in (OrderSide.LONG, OrderSide.BUY)

        # Calculate interval
        interval_secs = max(30, duration_seconds // num_slices)

        trigger_url = (
            "https://trigger.nado.xyz"
            if "mainnet" in self.cfg.env.lower()
            else "https://trigger.testnet.nado.xyz"
        )

        trigger_client = TriggerClient(
            opts=TriggerClientOpts(
                url=trigger_url,
                signer=self.cfg.private_key
            )
        )

        # Amount: positive = buy/long, negative = sell/short
        amount_x18 = to_x18(total_size) if is_long else -to_x18(total_size)

        # Max price: use a wide limit to act like market
        price_x18 = to_x18(max_price) if max_price else to_x18(9_999_999)

        result = trigger_client.place_twap_order(
            product_id=product_id,
            sender=client.context.engine_client.signer.address,
            price_x18=str(price_x18),
            total_amount_x18=str(abs(amount_x18)),
            expiration=get_expiration_timestamp(duration_seconds // 60 + 60),
            nonce=client.order_nonce() if hasattr(client, 'order_nonce') else 0,
            times=num_slices,
            slippage_frac=0.005,
            interval_seconds=interval_secs,
        )

        return Order(
            exchange=self.name,
            symbol=symbol,
            side=side,
            order_type=OrderType.TWAP,
            size=total_size,
            price=max_price,
            order_id=str(result.get("id", "")),
            status="active",
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        cmd = ["nado", "trade", "cancel", symbol, order_id, "--force"]
        result = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await result.communicate()
        return result.returncode == 0

    async def close_position(self, symbol: str, slippage_pct: float = 0.5) -> Order:
        cmd = ["nado", "trade", "close", symbol,
               "--slippage", str(slippage_pct), "--force", "--format", "json"]
        result = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await result.communicate()
        try:
            data = json.loads(stdout.decode())
        except Exception:
            data = {}
        return Order(
            exchange=self.name, symbol=symbol,
            side=OrderSide.SELL, order_type=OrderType.MARKET,
            size=0, price=None, status="submitted",
            order_id=data.get("digest", ""),
        )

    @property
    def is_configured(self) -> bool:
        return self.cfg.is_configured

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _product_id_to_symbol(self, product_id: int) -> str:
        inv = {v: k for k, v in self.SYMBOL_TO_PERP_ID.items()}
        return inv.get(product_id, f"UNKNOWN_{product_id}")
