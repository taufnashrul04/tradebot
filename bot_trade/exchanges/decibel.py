"""
bot_trade/exchanges/decibel.py — Decibel DEX adapter (Aptos blockchain)

Architecture:
 - Market data: REST API (read-only) at api.netna.aptoslabs.com/decibel/api/v1
 - Trading: On-chain via Aptos SDK (Move smart contracts)
 - Reference: SeamMoney/decibrrr bot, QuantProcessing/exchanges/decibel

Key contract module:
 dex_accounts::place_twap_order_to_subaccount(...)
 dex_accounts::place_market_order_to_subaccount(...)
 dex_accounts::delegate_trading_to_for_subaccount(...)
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import aiohttp
from curl_cffi import requests as cffi
import random

from ..config import get_config, DecibelConfig
from ..models import (
    ExchangeName, FundingRate, Ticker, OrderBook,
    Position, Order, OrderSide, OrderType
)
from .base import BaseExchange

# Known Decibel market addresses (fetched from /markets endpoint)
DECIBEL_MARKETS = {
    "BTC": "0x5e0e16f34adfb4b316f8d532d68acbfa206826feaaa418d3938046bdc2044861",
    "ETH": "0x96c3c2e77041264d082d03365e9c346fbc6be9c9428a401be8e70dcb60dc60c6",
    "SOL": "0xdf3f9b3241aaf20c47e99eac29f3ff2f736e40644c856e0db612a22e62b847f3",
}

# Decibel smart contract address on Aptos
DECIBEL_CONTRACT = "0x50ead22afd6ffd9769e3b3d6e0e64a2a350d68e8b102c4e72e33d0b8cfdfdb06"
DEX_ACCOUNTS_MODULE = f"{DECIBEL_CONTRACT}::dex_accounts_entry"


class DecibelExchange(BaseExchange):
    """
    Decibel Protocol adapter (Aptos blockchain).

    All reads use REST API.
    All writes use on-chain Aptos transactions via aptos-sdk.
    """

    name = ExchangeName.DECIBEL

    def __init__(self):
        self.cfg: DecibelConfig = get_config().decibel
        self._session: Optional[aiohttp.ClientSession] = None
        self._aptos_client = None  # lazy-loaded
        self._account = None

    IMPERSONATE_OPTIONS = [
        "chrome110", "chrome107", "chrome104", "chrome101",
        "chrome100", "chrome99", "edge99", "edge101",
    ]

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"}
            )
        return self._session

    def _get_cffi_session(self) -> cffi.Session:
        session = cffi.Session(impersonate=random.choice(self.IMPERSONATE_OPTIONS))
        session.headers.update({
            "Authorization": f"Bearer {self.cfg.geomi_api_key}",
            "Origin": "https://app.decibel.trade",
            "Referer": "https://app.decibel.trade/",
        })
        return session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_aptos_client(self):
        """Lazily initialize Aptos client for on-chain transactions."""
        if self._aptos_client is None:
            try:
                from aptos_sdk.async_client import RestClient, ClientConfig
                from aptos_sdk.account import Account

                # Create client with API key to avoid rate limits
                config = ClientConfig(api_key=self.cfg.geomi_api_key)
                self._aptos_client = RestClient(self.cfg.aptos_node, client_config=config)
                self._account = Account.load_key(self.cfg.private_key)
            except ImportError:
                raise RuntimeError(
                    "aptos-sdk not installed. Run: pip install aptos-sdk"
                )
        return self._aptos_client

    # ─── Market Data ─────────────────────────────────────────────────────────

    async def fetch_ticker(self, symbol: str) -> Ticker:
        market_addr = DECIBEL_MARKETS.get(symbol.upper().replace("-", "").replace("/", ""))
        if not market_addr:
            raise ValueError(f"Unknown market: {symbol}")
        session = self._get_cffi_session()
        resp = session.get(f"{self.cfg.effective_api_base}/prices")
        data = resp.json()

        for market in data:
            if market.get("market", "").lower() == market_addr.lower():
                mark = float(market.get("mark_px", 0))
                idx_p = float(market.get("oracle_px", mark))
                if mark == 0:
                    continue
                return Ticker(
                    exchange=self.name,
                    symbol=symbol,
                    bid=mark * 0.9999,
                    ask=mark * 1.0001,
                    last=mark,
                    mark_price=mark,
                    index_price=idx_p,
                )
        raise ValueError(f"Ticker not found for {symbol}")

    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        session = await self._get_session()
        async with session.get(
            f"{self.cfg.effective_api_base}/orderbook",
            params={"market": symbol}
        ) as resp:
            data = await resp.json()

        bids = [(float(b["price"]), float(b["size"])) for b in data.get("bids", [])[:depth]]
        asks = [(float(a["price"]), float(a["size"])) for a in data.get("asks", [])[:depth]]
        return OrderBook(exchange=self.name, symbol=symbol, bids=bids, asks=asks)

    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """
        Fetch funding rate from Decibel REST API.
        Decibel uses 1-hour or 8-hour funding intervals on Aptos.
        """
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.cfg.effective_api_base}/markets"
            ) as resp:
                data = await resp.json()

            sym = symbol.upper()
            markets = data if isinstance(data, list) else data.get("markets", [])
            for market in markets:
                if sym in market.get("symbol", "").upper():
                    rate = float(market.get("fundingRate", 0))
                    interval_h = float(market.get("fundingInterval", 8))
                    rate_annual = rate * (8760 / interval_h)
                    return FundingRate(
                        exchange=self.name,
                        symbol=symbol,
                        rate=rate,
                        rate_annual=rate_annual,
                        interval_hours=interval_h,
                    )
        except Exception:
            pass

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
        async with session.get(
            f"{self.cfg.effective_api_base}/candles",
            params={"market": symbol, "interval": interval, "limit": limit}
        ) as resp:
            data = await resp.json()

        candles = []
        for c in (data if isinstance(data, list) else data.get("candles", [])):
            candles.append({
                "timestamp": c.get("time", c.get("t", 0)),
                "open": float(c.get("open", c.get("o", 0))),
                "high": float(c.get("high", c.get("h", 0))),
                "low": float(c.get("low", c.get("l", 0))),
                "close": float(c.get("close", c.get("c", 0))),
                "volume": float(c.get("volume", c.get("v", 0))),
            })
        return candles

    # ─── Account Data ────────────────────────────────────────────────────────

    async def fetch_positions(self) -> list[Position]:
        """Fetch open positions from Decibel subaccount.

        Uses reference bot's fetch_open_positions implementation.
        API: GET /account_positions?account={subaccount_addr}
        """
        try:
            # Use reference bot's implementation
            import sys
            sys.path.insert(0, '/home/ubuntu/DECIBEL')
            from bot import fetch_open_positions

            positions_data = fetch_open_positions(self.cfg.subaccount_addr)
            positions = []

            for p in positions_data:
                market_addr = p.get("market") or p.get("market_addr", "")
                symbol = self._market_addr_to_symbol(market_addr)
                size_raw = float(p.get("size", 0))
                if size_raw == 0:
                    continue  # Skip empty positions

                is_long = size_raw >= 0
                side = OrderSide.LONG if is_long else OrderSide.SHORT

                # Calculate unrealized PnL
                entry_price = float(p.get("entry_price", 0))
                mark_price = float(p.get("mark_price", 0))
                funding = float(p.get("unrealized_funding", 0))

                # Fetch current price if mark_price not available
                if not mark_price:
                    try:
                        ticker = await self.fetch_ticker(symbol)
                        mark_price = float(ticker.last) if ticker and ticker.last else 0
                    except Exception:
                        mark_price = 0

                if entry_price and mark_price:
                    unrealized_pnl = (mark_price - entry_price) * size_raw + funding
                else:
                    unrealized_pnl = 0.0

                positions.append(Position(
                    exchange=self.name,
                    symbol=symbol,
                    side=side,
                    size=abs(size_raw),
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                ))

            return positions
        except Exception as e:
            # Fallback to REST API if reference bot fails
            session = await self._get_session()
            positions = []
            try:
                async with session.get(
                    f"{self.cfg.effective_api_base}/account_positions",
                    params={"account": self.cfg.subaccount_addr}
                ) as resp:
                    data = await resp.json()

                for p in (data if isinstance(data, list) else data.get("positions", [])):
                    market_addr = p.get("market", "")
                    symbol = self._market_addr_to_symbol(market_addr)
                    size_raw = float(p.get("size", 0))
                    if size_raw == 0:
                        continue

                    is_long = size_raw >= 0
                    side = OrderSide.LONG if is_long else OrderSide.SHORT
                    positions.append(Position(
                        exchange=self.name,
                        symbol=symbol,
                        side=side,
                        size=abs(size_raw),
                        entry_price=float(p.get("entry_price", 0)),
                        mark_price=float(p.get("mark_price", 0)),
                        unrealized_pnl=float(p.get("unrealized_pnl", 0)),
                    ))
            except Exception:
                pass
            return positions

    def _market_addr_to_symbol(self, market_addr: str) -> str:
        """Reverse lookup market address to symbol name."""
        for symbol, addr in DECIBEL_MARKETS.items():
            if addr.lower() == market_addr.lower():
                return symbol
        # Try to match via /prices endpoint data if not in static map
        return market_addr[:12] + "..."

    async def fetch_balance(self) -> dict[str, float]:
        """Fetch account balance from Decibel.
        
        Note: Decibel has no dedicated balance endpoint. We use:
        1. GET /subaccounts?owner={wallet} to verify subaccount exists
        2. GET /account_positions?account={subaccount} to check positions equity
        
        Balance must be fetched on-chain or via Decibel UI.
        Returns USDC = 0 if no position data available (subaccount may be empty).
        """
        try:
            # Try subaccounts endpoint first
            session = self._get_cffi_session()
            resp = session.get(
                f"{self.cfg.effective_api_base}/subaccounts",
                params={"owner": str(self._account.address()) if self._account else ""},
            )
            if resp.status_code == 200:
                data = resp.json()
                for sub in (data if isinstance(data, list) else data.get("subaccounts", [])):
                    sub_addr = sub.get("subaccount_address", "")
                    if sub_addr.lower() == self.cfg.subaccount_addr.lower():
                        is_active = sub.get("is_active", False)
                        if not is_active:
                            return {"USDC": 0.0, "free": 0.0}
            # Fallback: return empty, balance must be checked via UI
            return {"USDC": 0.0, "free": 0.0}
        except Exception:
            return {}

    async def _submit_transaction(self, client, payload):
        """
        Submit and wait for a BCS transaction.
        Matches the pattern used by friend and decibrrr reference bot.
        """
        from aptos_sdk.transactions import TransactionPayload, SignedTransaction
        raw_txn = await client.create_bcs_transaction(self._account, payload)
        authenticator = self._account.sign_transaction(raw_txn)
        signed_txn = SignedTransaction(raw_txn, authenticator)
        resp = await client.submit_bcs_transaction(signed_txn)
        await client.wait_for_transaction(resp)
        return resp

    # ─── Trading (On-chain via Aptos SDK) ────────────────────────────────────

    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> Order:
        """
        Place market order via Aptos on-chain transaction.
        Uses dex_accounts::place_order_to_subaccount with market price.
        
        Market config (BTC): px_decimals=6, sz_decimals=8, tick_size=100000, lot_size=1000
        - Size: multiply by 10^8, must be divisible by lot_size
        - Price: multiply by 10^6, must be divisible by tick_size
        """
        client = self._get_aptos_client()
        market_addr = DECIBEL_MARKETS.get(symbol.upper().replace("-", "").replace("/", ""))
        if not market_addr:
            raise ValueError(f"Unknown Decibel market: {symbol}")

        is_long = side == OrderSide.LONG

        # Get current price and align to tick size
        price_scaled = 0
        try:
            ticker = await self.fetch_ticker(symbol)
            if ticker and ticker.last:
                raw_price = float(ticker.last) * 1_000_000  # px_decimals=6
                price_scaled = round(raw_price / 100_000) * 100_000  # tick_size=100000
        except Exception:
            pass

        # Size: sz_decimals=8 for BTC, must be divisible by lot_size=1000
        size_raw = int(size * 100_000_000)
        lot_size = 1000  # BTC lot_size
        size_scaled = round(size_raw / lot_size) * lot_size

        # Use reference bot's working implementation directly
        try:
            import sys
            sys.path.insert(0, '/tmp/decibel_ref/DECIBEL')
            from bot import place_order_tx

            tx_hash = await place_order_tx(
                client,
                self._account,
                self.cfg.subaccount_addr,
                market_addr,
                price_chain=price_scaled,
                size_chain=size_scaled,
                is_buy=is_long,
                is_reduce_only=reduce_only,
            )

            return Order(
                exchange=self.name,
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                size=size,
                price=price_scaled / 1_000_000 if price_scaled else None,
                order_id=tx_hash,
                status="submitted",
            )
        except Exception as e:
            raise RuntimeError(f"Decibel market order failed: {e}")

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
        """
        Place limit order via Aptos on-chain transaction.
        Uses dex_accounts::place_order_to_subaccount
        """
        client = self._get_aptos_client()
        market_addr = DECIBEL_MARKETS.get(symbol.upper().replace("-", "").replace("/", ""))
        is_long = side == OrderSide.LONG

        # Size: sz_decimals=8 for BTC, must be divisible by lot_size=1000
        size_raw = int(size * 100_000_000)
        lot_size = 1000  # BTC lot_size
        size_scaled = round(size_raw / lot_size) * lot_size

        # Price: px_decimals=6, must be divisible by tick_size=100000
        price_raw = int(price * 1_000_000)
        tick_size = 100000
        price_scaled = round(price_raw / tick_size) * tick_size

        try:
            from aptos_sdk.transactions import EntryFunction, TransactionPayload, TransactionArgument
            from aptos_sdk.bcs import Serializer
            from aptos_sdk.account_address import AccountAddress

            # Use reference bot's working implementation
            import sys
            sys.path.insert(0, '/tmp/decibel_ref/DECIBEL')
            from bot import place_order_tx

            tx_hash = await place_order_tx(
                client,
                self._account,
                self.cfg.subaccount_addr,
                market_addr,
                price_chain=price_scaled,
                size_chain=size_scaled,
                is_buy=is_long,
                is_reduce_only=reduce_only,
            )

            return Order(
                exchange=self.name,
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                size=size,
                price=price,
                order_id=tx_hash,
                status="open",
            )
        except Exception as e:
            raise RuntimeError(f"Decibel limit order failed: {e}")

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
        Place TWAP order via Aptos on-chain.
        Uses dex_accounts::place_twap_order_to_subaccount
        """
        client = self._get_aptos_client()
        market_addr = DECIBEL_MARKETS.get(symbol.upper().replace("-", "").replace("/", ""))
        is_long = side == OrderSide.LONG
        size_scaled = int(total_size * 1_000_000)

        min_duration = duration_seconds
        max_duration = int(duration_seconds * 1.2)

        try:
            from aptos_sdk.transactions import EntryFunction, TransactionPayload, TransactionArgument
            from aptos_sdk.bcs import Serializer
            from aptos_sdk.account_address import AccountAddress

            payload = EntryFunction.natural(
                DEX_ACCOUNTS_MODULE,
                "place_twap_order_to_subaccount",
                [],
                [
                    TransactionArgument(AccountAddress.from_str(self.cfg.subaccount_addr), Serializer.struct),
                    TransactionArgument(AccountAddress.from_str(market_addr), Serializer.struct),
                    TransactionArgument(size_scaled, Serializer.u64),
                    TransactionArgument(is_long, Serializer.bool),
                    TransactionArgument(False, Serializer.bool),  # reduce_only
                    TransactionArgument(min_duration, Serializer.u64),
                    TransactionArgument(max_duration, Serializer.u64),
                    TransactionArgument(False, Serializer.bool),  # 6 padding args
                    TransactionArgument(False, Serializer.bool),
                    TransactionArgument(False, Serializer.bool),
                    TransactionArgument(False, Serializer.bool),
                    TransactionArgument(False, Serializer.bool),
                    TransactionArgument(False, Serializer.bool),
                ]
            )
            tx_hash = await self._submit_transaction(client, payload)

            return Order(
                exchange=self.name,
                symbol=symbol,
                side=side,
                order_type=OrderType.TWAP,
                size=total_size,
                price=max_price,
                order_id=tx_hash,
                status="active",
            )
        except Exception as e:
            raise RuntimeError(f"Decibel TWAP order failed: {e}")

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        # Decibel doesn't support cancel via REST; would need on-chain tx
        return False

    async def close_position(self, symbol: str, slippage_pct: float = 0.5) -> Order:
        """Close position by placing a market order in the opposite direction."""
        positions = await self.fetch_positions()
        for pos in positions:
            if pos.symbol.upper() == symbol.upper():
                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG
                return await self.place_market_order(
                    symbol, close_side, pos.size, reduce_only=True
                )
        raise RuntimeError(f"No open position found for {symbol} on Decibel")

    @property
    def is_configured(self) -> bool:
        return self.cfg.is_configured