#!/usr/bin/env python3
"""
Execute Very Large Volume Trades on Decibel Exchange

This script handles execution of very large orders (up to 100k+ volume)
by breaking them into small chunks and executing over time.
"""
import asyncio
import time
from typing import Optional
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def execute_very_large_volume(
    symbol: str,
    side: OrderSide,
    total_volume: float,
    volume_unit: str = "BTC",  # BTC, USD, or contracts
    strategy: ExecutionStrategy = ExecutionStrategy.TWAP,
    chunk_size: float = 0.001,  # Small chunks for large volumes
    delay_between_chunks: float = 2.0,
    max_execution_time_minutes: int = 60  # Max time to complete
) -> dict:
    """
    Execute a very large volume order.

    Args:
        symbol: Trading pair (e.g., 'BTC')
        side: Order side (LONG or SHORT)
        total_volume: Total volume to execute
        volume_unit: Unit of volume ('BTC', 'USD', or 'contracts')
        strategy: Execution strategy
        chunk_size: Size per chunk (in BTC)
        delay_between_chunks: Delay between chunks (seconds)
        max_execution_time_minutes: Maximum execution time

    Returns:
        Dict with execution results
    """
    print("\n" + "="*70)
    print(f"VERY LARGE VOLUME EXECUTION")
    print("="*70)
    print(f"Symbol: {symbol}")
    print(f"Side: {side.value}")
    print(f"Total Volume: {total_volume:,.2f} {volume_unit}")
    print(f"Strategy: {strategy.value}")
    print(f"Chunk Size: {chunk_size} BTC")
    print(f"Delay: {delay_between_chunks}s")
    print(f"Max Time: {max_execution_time_minutes} minutes")
    print("="*70)

    # Convert volume to BTC if needed
    if volume_unit == "USD":
        # Get current price
        exchange = DecibelExchange()
        ticker = await exchange.fetch_ticker(symbol)
        if not ticker or not ticker.last:
            raise ValueError(f"Could not fetch ticker for {symbol}")

        current_price = float(ticker.last)
        btc_volume = total_volume / current_price
        print(f"\n💰 Converting {total_volume:,.2f} USD to BTC @ ${current_price:,.2f}")
        print(f"   = {btc_volume:.6f} BTC")
    elif volume_unit == "contracts":
        # Assuming 1 contract = 1 BTC (adjust based on actual contract size)
        btc_volume = total_volume
        print(f"\n📊 Executing {total_volume:,.0f} contracts")
        print(f"   = {btc_volume:.6f} BTC")
    else:  # BTC
        btc_volume = total_volume
        print(f"\n📊 Executing {btc_volume:.6f} BTC")

    # Calculate number of chunks
    num_chunks = int(btc_volume / chunk_size)
    if btc_volume % chunk_size > 0:
        num_chunks += 1

    # Calculate estimated execution time
    estimated_time_seconds = num_chunks * delay_between_chunks
    estimated_time_minutes = estimated_time_seconds / 60

    print(f"\n📈 Execution Plan:")
    print(f"   Total BTC: {btc_volume:.6f}")
    print(f"   Chunks: {num_chunks}")
    print(f"   Estimated time: {estimated_time_minutes:.1f} minutes")

    # Check if execution time exceeds max
    if estimated_time_minutes > max_execution_time_minutes:
        print(f"\n⚠️  WARNING: Estimated time ({estimated_time_minutes:.1f} min) exceeds max ({max_execution_time_minutes} min)")
        print(f"   Consider increasing chunk size or reducing volume")

        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("❌ Execution cancelled")
            return {"status": "cancelled", "reason": "time_limit_exceeded"}

    # Configure trader
    exchange = DecibelExchange()
    config = LargeVolumeConfig(
        max_single_order_size=chunk_size,
        slice_delay_seconds=delay_between_chunks
    )
    trader = LargeVolumeTrader(exchange, config)

    # Execute
    start_time = time.time()
    print(f"\n🚀 Starting execution at {time.strftime('%H:%M:%S')}")

    try:
        orders = await trader.execute_large_order(
            symbol=symbol,
            side=side,
            total_size=btc_volume,
            strategy=strategy
        )

        execution_time = time.time() - start_time
        execution_time_minutes = execution_time / 60

        # Results
        total_filled = trader.get_total_filled_size()
        avg_price = trader.get_average_fill_price()

        print(f"\n✅ Execution completed at {time.strftime('%H:%M:%S')}")
        print(f"   Total time: {execution_time_minutes:.1f} minutes")
        print(f"   Orders executed: {len(orders)}")
        print(f"   Total filled: {total_filled:.6f} BTC")

        if avg_price:
            print(f"   Average price: ${avg_price:,.2f}")

            # Calculate total value
            total_value = avg_price * total_filled
            print(f"   Total value: ${total_value:,.2f}")

        return {
            "status": "completed",
            "orders": orders,
            "total_filled": total_filled,
            "avg_price": avg_price,
            "execution_time_minutes": execution_time_minutes,
            "num_orders": len(orders)
        }

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n❌ Execution failed after {execution_time/60:.1f} minutes")
        print(f"   Error: {e}")

        return {
            "status": "failed",
            "error": str(e),
            "execution_time_minutes": execution_time / 60
        }


async def execute_100k_btc(
    side: OrderSide = OrderSide.LONG,
    chunk_size: float = 0.001,
    delay: float = 2.0
) -> dict:
    """
    Execute 100k BTC volume (extremely large).

    WARNING: This is ~$7.6 billion worth of BTC.
    This will take a very long time and may not be practical.

    Args:
        side: Order side
        chunk_size: Size per chunk (BTC)
        delay: Delay between chunks (seconds)

    Returns:
        Execution results
    """
    print("\n" + "="*70)
    print("⚠️  WARNING: 100k BTC EXECUTION")
    print("="*70)
    print("This is an EXTREMELY large order (~$7.6 billion)")
    print("This will take a very long time to execute")
    print("="*70)

    response = input("\nAre you sure you want to continue? (type 'YES' to confirm): ")
    if response != "YES":
        print("❌ Execution cancelled")
        return {"status": "cancelled", "reason": "user_confirmation"}

    return await execute_very_large_volume(
        symbol='BTC',
        side=side,
        total_volume=100000,
        volume_unit="BTC",
        strategy=ExecutionStrategy.TWAP,
        chunk_size=chunk_size,
        delay_between_chunks=delay,
        max_execution_time_minutes=1440  # 24 hours
    )


async def execute_100k_usd(
    side: OrderSide = OrderSide.LONG,
    chunk_size: float = 0.001,
    delay: float = 2.0
) -> dict:
    """
    Execute $100k worth of BTC volume.

    This is a more manageable large volume.

    Args:
        side: Order side
        chunk_size: Size per chunk (BTC)
        delay: Delay between chunks (seconds)

    Returns:
        Execution results
    """
    return await execute_very_large_volume(
        symbol='BTC',
        side=side,
        total_volume=100000,
        volume_unit="USD",
        strategy=ExecutionStrategy.TWAP,
        chunk_size=chunk_size,
        delay_between_chunks=delay,
        max_execution_time_minutes=60
    )


async def main():
    """Main execution function."""
    import sys

    print("\n" + "="*70)
    print("VERY LARGE VOLUME TRADING")
    print("="*70)

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python execute_large_volume.py <volume> <unit> <side> [chunk_size] [delay]")
        print("\nExamples:")
        print("  python execute_large_volume.py 100000 USD LONG")
        print("  python execute_large_volume.py 100000 BTC LONG 0.001 2.0")
        print("  python execute_large_volume.py 100000 contracts SHORT")
        print("\nPresets:")
        print("  python execute_large_volume.py --100k-usd LONG")
        print("  python execute_large_volume.py --100k-btc LONG")
        return

    # Check for presets
    if sys.argv[1] == "--100k-usd":
        side = OrderSide.LONG if len(sys.argv) < 3 else OrderSide(sys.argv[2].upper())
        result = await execute_100k_usd(side=side)
        print(f"\n📊 Result: {result['status']}")
        return

    if sys.argv[1] == "--100k-btc":
        side = OrderSide.LONG if len(sys.argv) < 3 else OrderSide(sys.argv[2].upper())
        result = await execute_100k_btc(side=side)
        print(f"\n📊 Result: {result['status']}")
        return

    # Parse arguments
    volume = float(sys.argv[1])
    unit = sys.argv[2].upper()
    side = OrderSide(sys.argv[3].upper())
    chunk_size = float(sys.argv[4]) if len(sys.argv) > 4 else 0.001
    delay = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0

    # Execute
    result = await execute_very_large_volume(
        symbol='BTC',
        side=side,
        total_volume=volume,
        volume_unit=unit,
        strategy=ExecutionStrategy.TWAP,
        chunk_size=chunk_size,
        delay_between_chunks=delay,
        max_execution_time_minutes=60
    )

    print(f"\n📊 Result: {result['status']}")


if __name__ == "__main__":
    asyncio.run(main())
