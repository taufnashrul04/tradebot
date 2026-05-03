#!/usr/bin/env python3
"""
Test Mean Reversion Bot with tighter TP/SL
- TP: 0.2% (smaller wins)
- SL: 0.15% (tighter stop loss)
- Hold time: 10s (faster)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mean_reversion_bot import MeanReversionBot

async def test_tight_tp_sl():
    """Test mean reversion bot with tighter TP/SL"""
    print("🧪 Testing Mean Reversion Bot (Tighter TP/SL)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: Buy RSI<30, Sell RSI>70")
    print("   TP: 0.2% (smaller wins)")
    print("   SL: 0.15% (tighter stop loss)")
    print("   Hold Time: 10s (faster)")
    print("   Check Interval: 1s (frequent monitoring)")
    print("   Order Type: Market (reliable)")
    print("=" * 60)

    bot = MeanReversionBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.2,  # 0.2% TP (smaller wins)
        stop_loss_percent=0.15,  # 0.15% SL (tighter)
        check_interval_seconds=1.0,  # Check every 1s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=10.0,  # 10s hold time (faster)
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_tight_tp_sl())
