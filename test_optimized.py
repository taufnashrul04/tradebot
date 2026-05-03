#!/usr/bin/env python3
"""
Test optimized bot with 5 cycles
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimized_bot import OptimizedCCXTDecibelBot

async def test_optimized():
    """Test optimized bot with 5 cycles"""
    print("🧪 Testing Optimized Bot (5 cycles)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   TP: 0.3%")
    print("   SL: 0.5%")
    print("   Hold Time: 20s")
    print("   Check Interval: 2s")
    print("=" * 60)

    bot = OptimizedCCXTDecibelBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.3,  # 0.3% TP
        stop_loss_percent=0.5,  # 0.5% SL
        check_interval_seconds=2.0,  # Check every 2s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=20.0,  # 20s hold time
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_optimized())
