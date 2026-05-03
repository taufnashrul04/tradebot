#!/usr/bin/env python3
"""
Test Mean Reversion Bot with 5 cycles
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mean_reversion_bot import MeanReversionBot

async def test_mean_reversion():
    """Test mean reversion bot with 5 cycles"""
    print("🧪 Testing Mean Reversion Bot (5 cycles)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: Buy RSI<30, Sell RSI>70")
    print("   TP: 0.5%")
    print("   SL: 0.3%")
    print("   Hold Time: 15s")
    print("   Check Interval: 2s")
    print("   Order Type: Market (reliable)")
    print("=" * 60)

    bot = MeanReversionBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.5,  # 0.5% TP
        stop_loss_percent=0.3,  # 0.3% SL
        check_interval_seconds=2.0,  # Check every 2s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=15.0,  # 15s hold time
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_mean_reversion())
