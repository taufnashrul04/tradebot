#!/usr/bin/env python3
"""
Quick test for large volume execution (no user input required).
"""
import asyncio
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def test_small_volume():
    """Test with small volume to verify functionality."""
    print("\n" + "="*70)
    print("TEST: Small Volume Execution")
    print("="*70)

    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=0.0001,
        slice_delay_seconds=1.0
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute 0.0002 BTC LONG (2 chunks of 0.0001)
    print(f"\n📊 Executing 0.0002 BTC LONG in 0.0001 BTC chunks")
    print(f"   Estimated chunks: 2")
    print(f"   Estimated time: 1.0 seconds")

    start_time = asyncio.get_event_loop().time()
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.0002,
        strategy=ExecutionStrategy.MARKET_SLICE
    )
    elapsed = asyncio.get_event_loop().time() - start_time

    print(f"\n✅ Execution completed in {elapsed:.1f} seconds")
    print(f"   Orders executed: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")

    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"   Average price: ${avg_price:.2f}")

    return orders


async def test_usd_volume():
    """Test with USD volume."""
    print("\n" + "="*70)
    print("TEST: USD Volume Execution")
    print("="*70)

    # Get current price
    exchange = DecibelExchange()
    ticker = await exchange.fetch_ticker('BTC')
    if not ticker or not ticker.last:
        print("❌ Could not fetch ticker")
        return []

    current_price = float(ticker.last)
    usd_amount = 100  # $100 worth
    btc_amount = usd_amount / current_price

    print(f"\n💰 Executing ${usd_amount} worth of BTC")
    print(f"   Current price: ${current_price:.2f}")
    print(f"   BTC amount: {btc_amount:.6f}")

    config = LargeVolumeConfig(
        max_single_order_size=0.0001,
        slice_delay_seconds=1.0
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=btc_amount,
        strategy=ExecutionStrategy.MARKET_SLICE
    )

    print(f"\n✅ Execution completed")
    print(f"   Orders executed: {len(orders)}")
    print(f"   Total filled: {trader.get_total_filled_size():.6f} BTC")

    avg_price = trader.get_average_fill_price()
    if avg_price:
        total_value = avg_price * trader.get_total_filled_size()
        print(f"   Average price: ${avg_price:.2f}")
        print(f"   Total value: ${total_value:.2f}")

    return orders


async def main():
    """Run tests."""
    print("\n" + "="*70)
    print("LARGE VOLUME EXECUTION TESTS")
    print("="*70)

    try:
        # Test 1: Small BTC volume
        await test_small_volume()

        # Test 2: USD volume
        await test_usd_volume()

        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
