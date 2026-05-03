"""
Large Volume Trading Module for Decibel Exchange

Handles execution of large orders by splitting them into smaller chunks
to minimize slippage and market impact.
"""
import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from bot_trade.models import Order, OrderSide, OrderType
from bot_trade.exchanges.decibel import DecibelExchange


class ExecutionStrategy(Enum):
    """Order execution strategies for large volumes."""
    MARKET_SLICE = "market_slice"  # Split into market orders
    LIMIT_LADDER = "limit_ladder"  # Place limit orders at different prices
    TWAP = "twap"  # Time-Weighted Average Price


@dataclass
class LargeVolumeConfig:
    """Configuration for large volume trading."""
    max_single_order_size: float = 0.01  # Max size per single order (in BTC)
    slice_delay_seconds: float = 1.0  # Delay between slices
    slippage_tolerance_percent: float = 0.5  # Max acceptable slippage
    price_spread_percent: float = 0.1  # Spread for limit ladder
    num_ladder_rungs: int = 5  # Number of rungs in limit ladder


class LargeVolumeTrader:
    """
    Execute large volume orders with minimal market impact.

    Features:
    - Order slicing (split large orders into smaller chunks)
    - TWAP execution (spread orders over time)
    - Limit ladder (place orders at multiple price levels)
    - Slippage monitoring and protection
    """

    def __init__(
        self,
        exchange: DecibelExchange,
        config: Optional[LargeVolumeConfig] = None
    ):
        self.exchange = exchange
        self.config = config or LargeVolumeConfig()
        self._executed_orders: List[Order] = []

    async def execute_large_order(
        self,
        symbol: str,
        side: OrderSide,
        total_size: float,
        strategy: ExecutionStrategy = ExecutionStrategy.MARKET_SLICE,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> List[Order]:
        """
        Execute a large order using the specified strategy.

        Args:
            symbol: Trading pair (e.g., 'BTC')
            side: Order side (LONG or SHORT)
            total_size: Total size to execute
            strategy: Execution strategy
            leverage: Leverage multiplier
            reduce_only: If True, only reduce existing position

        Returns:
            List of executed orders
        """
        self._executed_orders = []

        if strategy == ExecutionStrategy.MARKET_SLICE:
            return await self._execute_market_slices(
                symbol, side, total_size, leverage, reduce_only
            )
        elif strategy == ExecutionStrategy.LIMIT_LADDER:
            return await self._execute_limit_ladder(
                symbol, side, total_size, leverage, reduce_only
            )
        elif strategy == ExecutionStrategy.TWAP:
            return await self._execute_twap(
                symbol, side, total_size, leverage, reduce_only
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    async def _execute_market_slices(
        self,
        symbol: str,
        side: OrderSide,
        total_size: float,
        leverage: int,
        reduce_only: bool
    ) -> List[Order]:
        """
        Execute large order as a series of market orders.

        Splits the total size into chunks of max_single_order_size
        and executes them with delays between slices.
        """
        chunk_size = self.config.max_single_order_size
        remaining = total_size
        executed_orders = []

        print(f"📊 Executing {total_size} {symbol} {side.value} via market slices")
        print(f"   Chunk size: {chunk_size}, Delay: {self.config.slice_delay_seconds}s")

        while remaining > 0:
            # Calculate slice size
            slice_size = min(remaining, chunk_size)

            # Execute slice
            try:
                order = await self.exchange.place_market_order(
                    symbol, side, slice_size, leverage, reduce_only
                )
                executed_orders.append(order)
                self._executed_orders.append(order)

                print(f"   ✅ Slice {len(executed_orders)}: {slice_size} {symbol} @ ${order.price}")

                remaining -= slice_size

                # Delay before next slice
                if remaining > 0:
                    await asyncio.sleep(self.config.slice_delay_seconds)

            except Exception as e:
                print(f"   ❌ Slice failed: {e}")
                # Continue with remaining size
                remaining -= slice_size

        return executed_orders

    async def _execute_limit_ladder(
        self,
        symbol: str,
        side: OrderSide,
        total_size: float,
        leverage: int,
        reduce_only: bool
    ) -> List[Order]:
        """
        Execute large order using a limit order ladder.

        Places limit orders at multiple price levels to fill
        gradually as the market moves.
        """
        # Get current market price
        ticker = await self.exchange.fetch_ticker(symbol)
        if not ticker or not ticker.last:
            raise ValueError(f"Could not fetch ticker for {symbol}")

        current_price = float(ticker.last)

        # Calculate price levels
        num_rungs = self.config.num_ladder_rungs
        spread = self.config.price_spread_percent / 100

        if side == OrderSide.LONG:
            # Buy ladder: prices below current
            prices = [
                current_price * (1 - spread * (i + 1))
                for i in range(num_rungs)
            ]
        else:
            # Sell ladder: prices above current
            prices = [
                current_price * (1 + spread * (i + 1))
                for i in range(num_rungs)
            ]

        # Calculate size per rung
        size_per_rung = total_size / num_rungs

        print(f"📊 Executing {total_size} {symbol} {side.value} via limit ladder")
        print(f"   Current price: ${current_price}")
        print(f"   Rungs: {num_rungs}, Size per rung: {size_per_rung}")

        executed_orders = []

        for i, price in enumerate(prices):
            try:
                order = await self.exchange.place_limit_order(
                    symbol, side, size_per_rung, price, leverage, reduce_only
                )
                executed_orders.append(order)
                self._executed_orders.append(order)

                print(f"   ✅ Rung {i+1}: {size_per_rung} {symbol} @ ${price}")

            except Exception as e:
                print(f"   ❌ Rung {i+1} failed: {e}")

        return executed_orders

    async def _execute_twap(
        self,
        symbol: str,
        side: OrderSide,
        total_size: float,
        leverage: int,
        reduce_only: bool
    ) -> List[Order]:
        """
        Execute large order using TWAP (Time-Weighted Average Price).

        Spreads the order execution over time to achieve
        an average price close to the time-weighted average.
        """
        chunk_size = self.config.max_single_order_size
        num_slices = int(total_size / chunk_size)
        if total_size % chunk_size > 0:
            num_slices += 1

        # Calculate delay between slices for 5-minute TWAP
        total_duration_seconds = 5 * 60  # 5 minutes
        delay = total_duration_seconds / num_slices

        print(f"📊 Executing {total_size} {symbol} {side.value} via TWAP")
        print(f"   Duration: {total_duration_seconds}s, Slices: {num_slices}")
        print(f"   Delay: {delay:.1f}s per slice")

        # Update config for TWAP
        original_delay = self.config.slice_delay_seconds
        self.config.slice_delay_seconds = delay

        try:
            return await self._execute_market_slices(
                symbol, side, total_size, leverage, reduce_only
            )
        finally:
            self.config.slice_delay_seconds = original_delay

    def get_executed_orders(self) -> List[Order]:
        """Get all orders executed by this trader."""
        return self._executed_orders.copy()

    def get_average_fill_price(self) -> Optional[float]:
        """
        Calculate the average fill price of all executed orders.

        Returns:
            Average fill price, or None if no orders executed
        """
        if not self._executed_orders:
            return None

        total_value = 0.0
        total_size = 0.0

        for order in self._executed_orders:
            if order.avg_fill_price and order.filled_size:
                total_value += order.avg_fill_price * order.filled_size
                total_size += order.filled_size

        if total_size == 0:
            return None

        return total_value / total_size

    def get_total_filled_size(self) -> float:
        """Get total filled size across all orders."""
        return sum(order.filled_size or 0 for order in self._executed_orders)

    def get_total_slippage(self, expected_price: float) -> Optional[float]:
        """
        Calculate total slippage relative to expected price.

        Args:
            expected_price: The expected average price

        Returns:
            Slippage in percent, or None if no orders executed
        """
        avg_fill = self.get_average_fill_price()
        if not avg_fill:
            return None

        slippage = ((avg_fill - expected_price) / expected_price) * 100
        return slippage


# Convenience function for quick large volume execution
async def execute_large_volume(
    symbol: str,
    side: OrderSide,
    size: float,
    strategy: ExecutionStrategy = ExecutionStrategy.MARKET_SLICE,
    max_chunk_size: float = 0.01,
    slice_delay: float = 1.0
) -> List[Order]:
    """
    Quick function to execute a large volume order.

    Args:
        symbol: Trading pair (e.g., 'BTC')
        side: Order side (LONG or SHORT)
        size: Total size to execute
        strategy: Execution strategy
        max_chunk_size: Max size per chunk
        slice_delay: Delay between slices (seconds)

    Returns:
        List of executed orders
    """
    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=max_chunk_size,
        slice_delay_seconds=slice_delay
    )
    trader = LargeVolumeTrader(exchange, config)

    return await trader.execute_large_order(symbol, side, size, strategy)
