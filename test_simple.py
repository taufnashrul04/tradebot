#!/usr/bin/env python3
"""
Test Simple Bot - No TP/SL, just hold and close
- Hold time: 3s (very fast)
- No TP/SL (just capture micro-movements)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_bot import SimpleBot

async def test_simple():
    """Test simple bot with 5 cycles"""
    print("🧪 Testing Simple Bot (5 cycles)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   Strategy: No TP/SL, just hold and close")
    print("   Hold Time: 3s (very fast)")
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
            hold_time_seconds=3.0,  # 3s hold time (very fast)
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_simple())
