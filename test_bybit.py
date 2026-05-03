#!/usr/bin/env python3
"""
Test Mean Reversion Bot with Bybit (supports smaller timeframes)
- TP: 0.2%
- SL: 0.15%
- Hold time: 10s
- Timeframe: 1m
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mean_reversion_bot import MeanReversionBot

async def test_bybit():
    """Test mean reversion bot with Bybit"""
    print("🧪 Testing Mean Reversion Bot (Bybit)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: Buy RSI<30, Sell RSI>70")
    print("   TP: 0.2%")
    print("   SL: 0.15%")
    print("   Hold Time: 10s")
    print("   Timeframe: 1m")
    print("   Check Interval: 1s")
    print("   Order Type: Market (reliable)")
    print("=" * 60)

    bot = MeanReversionBot(
        analysis_exchange="bybit",  # Bybit (supports smaller timeframes)
        symbol="BTC/USDT",
        timeframe="1m",  # 1m timeframe
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.2,  # 0.2% TP
        stop_loss_percent=0.15,  # 0.15% SL
        check_interval_seconds=1.0,  # Check every 1s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=10.0,  # 10s hold time
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_bybit())
