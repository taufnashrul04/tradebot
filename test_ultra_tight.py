#!/usr/bin/env python3
"""
Test Mean Reversion Bot with Ultra-Tight TP/SL
- TP: 0.1% (micro wins)
- SL: 0.05% (ultra tight)
- Hold time: 5s (very fast)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mean_reversion_bot import MeanReversionBot

async def test_ultra_tight():
    """Test mean reversion bot with ultra-tight TP/SL"""
    print("🧪 Testing Mean Reversion Bot (Ultra-Tight TP/SL)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: Buy RSI<30, Sell RSI>70")
    print("   TP: 0.1% (micro wins)")
    print("   SL: 0.05% (ultra tight)")
    print("   Hold Time: 5s (very fast)")
    print("   Check Interval: 0.5s (very frequent)")
    print("   Order Type: Market (reliable)")
    print("=" * 60)

    bot = MeanReversionBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.1,  # 0.1% TP (micro wins)
        stop_loss_percent=0.05,  # 0.05% SL (ultra tight)
        check_interval_seconds=0.5,  # Check every 0.5s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=5.0,  # 5s hold time (very fast)
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_ultra_tight())
