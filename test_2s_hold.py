#!/usr/bin/env python3
"""
Test Simple Bot with 2s hold time
- Hold time: 2s (ultra fast)
- No TP/SL (just capture micro-movements)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_bot import SimpleBot

async def test_2s_hold():
    """Test simple bot with 2s hold time"""
    print("🧪 Testing Simple Bot (2s Hold Time)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: Follow MACD trend")
    print("   Hold Time: 2s (ultra fast)")
    print("   Order Type: Market (reliable)")
    print("=" * 60)

    bot = SimpleBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=2.0,  # 2s hold time (ultra fast)
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_2s_hold())
