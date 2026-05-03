"""
bot_trade/strategies/volume_generator.py

High Volume Generation Strategy

Generates trading volume via TWAP orders with randomized sizes.
Goal: accumulate volume for exchange incentive programs / points.

Techniques:
  - TWAP: split large order into small pieces over time
  - Randomized sizes: avoid pattern detection
  - Alternating sides: long→close→short→close to stay near flat
  - Multi-exchange: run on multiple exchanges simultaneously
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime
from typing import Optional

from loguru import logger

from ..models import (
    ExchangeName, OrderSide, OrderType, Order,
    SessionStats, TradingMode
)
from ..exchanges.base import BaseExchange
from ..config import get_config


class VolumeGeneratorStrategy:
    """
    Generates high trading volume with minimal directional exposure.

    Uses TWAP-style execution: slices total volume into many small
    trades executed at randomized intervals.
    """

    def __init__(
        self,
        exchange: BaseExchange,
        symbol: str = "BTC",
        target_volume_usd: float = 10_000.0,
        duration_seconds: int = 3600,
        num_slices: int = 20,
        leverage: int = 1,
        jitter_pct: float = 0.3,     # randomize slice size ±30%
        side_bias: float = 0.0,      # 0.0 = neutral, +1.0 = always long, -1.0 = always short
        use_twap: bool = True,       # use native TWAP if available
    ):
        self.exchange = exchange
        self.symbol = symbol
        self.target_volume_usd = target_volume_usd
        self.duration_seconds = duration_seconds
        self.num_slices = max(2, num_slices)
        self.leverage = min(leverage, get_config().risk.max_leverage)
        self.jitter_pct = jitter_pct
        self.side_bias = max(-1.0, min(1.0, side_bias))
        self.use_twap = use_twap

        self.session = SessionStats(
            session_id=str(uuid.uuid4())[:8],
            mode=TradingMode.VOLUME,
            exchange=exchange.name.value,
            symbol=symbol,
        )
        self._running = False
        self._orders: list[Order] = []

    # ─── Main Flow ────────────────────────────────────────────────────────────

    async def run(self):
        """
        Execute the volume generation strategy.
        Either uses native TWAP (Nado/Decibel) or simulates it.
        """
        self._running = True
        logger.info(
            f"📈 Volume Generator started | "
            f"Exchange: {self.exchange.name.value} | "
            f"Target: ${self.target_volume_usd:,.0f} | "
            f"Duration: {self.duration_seconds//60}min | "
            f"Slices: {self.num_slices}"
        )

        if self.use_twap and self.exchange.name in (
            ExchangeName.NADO, ExchangeName.DECIBEL
        ):
            await self._run_native_twap()
        else:
            await self._run_simulated_twap()

        logger.success(
            f"✅ Volume generation complete | "
            f"Total volume: ${self.session.total_volume_usd:,.2f} | "
            f"Trades: {self.session.total_trades}"
        )

    async def _run_native_twap(self):
        """
        Use native TWAP order from exchange SDK.
        Works best on Nado (TriggerClient) and Decibel (on-chain TWAP).
        Strategy: alternate long/short TWAP cycles.
        """
        ticker = await self.exchange.fetch_ticker(self.symbol)
        price = ticker.mid
        total_size = self.target_volume_usd / price / 2  # /2 because we do both sides

        cycles = 2  # long cycle + short cycle
        slice_duration = self.duration_seconds // cycles

        for cycle in range(cycles):
            if not self._running:
                break

            side = OrderSide.LONG if cycle % 2 == 0 else OrderSide.SHORT
            logger.info(
                f"⚡ TWAP cycle {cycle+1}/{cycles}: "
                f"{side.value.upper()} {total_size:.4f} {self.symbol} "
                f"over {slice_duration}s"
            )

            try:
                order = await self.exchange.place_twap_order(
                    symbol=self.symbol,
                    side=side,
                    total_size=total_size,
                    duration_seconds=slice_duration,
                    num_slices=self.num_slices // cycles,
                )
                self._orders.append(order)
                self.session.total_trades += 1
                self.session.total_volume_usd += self.target_volume_usd / cycles

                # Wait for TWAP to complete
                await asyncio.sleep(slice_duration)

                # Close position if still open
                try:
                    close_order = await self.exchange.close_position(self.symbol)
                    self._orders.append(close_order)
                    self.session.total_trades += 1
                    self.session.total_volume_usd += total_size * price
                except Exception as e:
                    logger.warning(f"Close error (may be already closed): {e}")

            except Exception as e:
                logger.error(f"TWAP cycle error: {e}")

    async def _run_simulated_twap(self):
        """
        Simulate TWAP by placing many small market orders.
        Used for Rise Trade or as fallback.
        """
        ticker = await self.exchange.fetch_ticker(self.symbol)
        price = ticker.mid
        slice_size_usd = self.target_volume_usd / self.num_slices
        slice_size_base = slice_size_usd / price
        interval = self.duration_seconds / self.num_slices

        completed_volume = 0.0
        last_side = None

        for i in range(self.num_slices):
            if not self._running:
                break

            # Determine side (alternate with bias)
            if self.side_bias > 0:
                p_long = 0.5 + self.side_bias * 0.5
            elif self.side_bias < 0:
                p_long = 0.5 + self.side_bias * 0.5
            else:
                p_long = 0.5

            # Alternate to stay delta neutral
            if last_side == OrderSide.LONG:
                side = OrderSide.SHORT
            elif last_side == OrderSide.SHORT:
                side = OrderSide.LONG
            else:
                side = OrderSide.LONG if random.random() < p_long else OrderSide.SHORT
            last_side = side

            # Randomize size ±jitter
            jitter = 1.0 + random.uniform(-self.jitter_pct, self.jitter_pct)
            actual_size = slice_size_base * jitter

            # Randomize timing ±20%
            sleep_time = interval * (1.0 + random.uniform(-0.2, 0.2))

            try:
                # Refresh price every 5 slices
                if i % 5 == 0:
                    ticker = await self.exchange.fetch_ticker(self.symbol)
                    price = ticker.mid
                    actual_size = (slice_size_usd * jitter) / price

                logger.info(
                    f"📊 [{i+1}/{self.num_slices}] "
                    f"{side.value.upper()} {actual_size:.4f} {self.symbol} "
                    f"@ ~${price:,.2f} | Vol so far: ${completed_volume:,.0f}"
                )

                order = await self.exchange.place_market_order(
                    symbol=self.symbol,
                    side=side,
                    size=actual_size,
                    leverage=self.leverage,
                )
                self._orders.append(order)
                self.session.total_trades += 1

                trade_usd = actual_size * price
                completed_volume += trade_usd
                self.session.total_volume_usd += trade_usd

            except Exception as e:
                logger.error(f"Slice {i+1} error: {e}")

            await asyncio.sleep(sleep_time)

        # Final: close any remaining position
        try:
            await self.exchange.close_position(self.symbol)
            self.session.total_trades += 1
        except Exception:
            pass

    def stop(self):
        self._running = False

    @property
    def progress_pct(self) -> float:
        if self.target_volume_usd == 0:
            return 0.0
        return min(100.0, self.session.total_volume_usd / self.target_volume_usd * 100)
