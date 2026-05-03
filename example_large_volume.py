#!/usr/bin/env python3
"""
Example: Large Volume Trading on Decibel Exchange

This example shows how to execute large orders using different strategies
to minimize slippage and market impact.
"""
import asyncio
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def example_market_slice():
    """
    Example 1: Execute a large order using market slices.

    This splits a large order into smaller chunks and executes them
    as market orders with delays between slices.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Market Slice Execution")
    print("="*70)

    # Initialize exchange and trader
    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.001,  # Max 0.001 BTC per order
        slice_delay_seconds=2.0  # 2 second delay between slices
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.01 BTC LONG using market slices
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.01,
        strategy=ExecutionStrategy.MARKET_SLICE
    )

    # Check results
    print(f"\n📊 Results:")
    print(f"   Orders executed: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")

    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"   Average fill price: ${avg_price:.2f}")

        # Calculate slippage
        expected_price = 76000  # Example expected price
        slippage = trader.get_total_slippage(expected_price)
        if slippage is not None:
            print(f"   Slippage: {slippage:.3f}%")


async def example_limit_ladder():
    """
    Example 2: Execute a large order using a limit ladder.

    This places limit orders at multiple price levels to fill
    gradually as the market moves.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Limit Ladder Execution")
    print("="*70)

    # Initialize exchange and trader
    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.001,
        num_ladder_rungs=5,  # 5 price levels
        price_spread_percent=0.1  # 0.1% spread between levels
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.005 BTC SHORT using limit ladder
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.SHORT,
        total_size=0.005,
        strategy=ExecutionStrategy.LIMIT_LADDER
    )

    # Check results
    print(f"\n📊 Results:")
    print(f"   Orders placed: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")


async def example_twap():
    """
    Example 3: Execute a large order using TWAP.

    This spreads the order execution over time to achieve
    an average price close to the time-weighted average.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: TWAP Execution")
    print("="*70)

    # Initialize exchange and trader
    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.001
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.01 BTC LONG using TWAP (5-minute duration)
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.01,
        strategy=ExecutionStrategy.TWAP
    )

    # Check results
    print(f"\n📊 Results:")
    print(f"   Orders executed: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")

    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"   Average fill price: ${avg_price:.2f}")


async def example_quick_execution():
    """
    Example 4: Quick execution using convenience function.

    This shows the simplest way to execute a large volume order.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Quick Execution")
    print("="*70)

    from bot_trade.exchanges.decibel_large_volume import execute_large_volume

    # Execute 0.002 BTC SHORT with custom parameters
    orders = await execute_large_volume(
        symbol='BTC',
        side=OrderSide.SHORT,
        size=0.002,
        strategy=ExecutionStrategy.MARKET_SLICE,
        max_chunk_size=0.0005,
        slice_delay=1.0
    )

    print(f"\n📊 Results:")
    print(f"   Orders executed: {len(orders)}")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("LARGE VOLUME TRADING EXAMPLES")
    print("="*70)
    print("\nThese examples demonstrate different strategies for executing")
    print("large volume orders on Decibel Exchange.")
    print("\n⚠️  WARNING: These are examples with real trades!")
    print("   Adjust sizes and parameters for your needs.")

    try:
        # Example 1: Market Slice
        await example_market_slice()

        # Example 2: Limit Ladder
        await example_limit_ladder()

        # Example 3: TWAP
        await example_twap()

        # Example 4: Quick Execution
        await example_quick_execution()

        print("\n" + "="*70)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
