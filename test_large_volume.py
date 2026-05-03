#!/usr/bin/env python3
"""
Test script for Large Volume Trading on Decibel Exchange.

Demonstrates different execution strategies for large orders.
"""
import asyncio
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy,
    execute_large_volume
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def test_market_slice_strategy():
    """Test market slice execution strategy."""
    print("\n" + "="*70)
    print("TEST 1: Market Slice Strategy")
    print("="*70)

    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.0001,  # Small chunks for testing
        slice_delay_seconds=2.0
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.0005 BTC LONG using market slices
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.0005,
        strategy=ExecutionStrategy.MARKET_SLICE
    )

    print(f"\n📊 Execution Summary:")
    print(f"   Total orders: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")
    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"   Average fill price: ${avg_price:.2f}")

    return orders


async def test_limit_ladder_strategy():
    """Test limit ladder execution strategy."""
    print("\n" + "="*70)
    print("TEST 2: Limit Ladder Strategy")
    print("="*70)

    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.0001,
        num_ladder_rungs=3,
        price_spread_percent=0.05  # 0.05% spread
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.0003 BTC SHORT using limit ladder
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.SHORT,
        total_size=0.0003,
        strategy=ExecutionStrategy.LIMIT_LADDER
    )

    print(f"\n📊 Execution Summary:")
    print(f"   Total orders: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")

    return orders


async def test_twap_strategy():
    """Test TWAP execution strategy."""
    print("\n" + "="*70)
    print("TEST 3: TWAP Strategy")
    print("="*70)

    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.0001,
        slice_delay_seconds=1.0  # Will be overridden by TWAP
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.0004 BTC LONG using TWAP
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.0004,
        strategy=ExecutionStrategy.TWAP
    )

    print(f"\n📊 Execution Summary:")
    print(f"   Total orders: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")
    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"   Average fill price: ${avg_price:.2f}")

    return orders


async def test_quick_execution():
    """Test quick execution function."""
    print("\n" + "="*70)
    print("TEST 4: Quick Execution Function")
    print("="*70)

    # Quick execution with custom parameters
    orders = await execute_large_volume(
        symbol='BTC',
        side=OrderSide.SHORT,
        size=0.0002,
        strategy=ExecutionStrategy.MARKET_SLICE,
        max_chunk_size=0.0001,
        slice_delay=1.5
    )

    print(f"\n📊 Execution Summary:")
    print(f"   Total orders: {len(orders)}")

    return orders


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("LARGE VOLUME TRADING TEST SUITE")
    print("="*70)

    try:
        # Test 1: Market Slice
        await test_market_slice_strategy()

        # Test 2: Limit Ladder
        await test_limit_ladder_strategy()

        # Test 3: TWAP
        await test_twap_strategy()

        # Test 4: Quick Execution
        await test_quick_execution()

        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
