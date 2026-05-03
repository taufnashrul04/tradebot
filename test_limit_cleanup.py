#!/usr/bin/env python3
"""
Test 1 cycle with limit order cleanup
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccxt_decibel_bot import CCXTDecibelBot

async def test_one_cycle():
    """Test one trading cycle with limit order cleanup"""
    print("🧪 Testing 1 cycle with limit order cleanup...")
    print("=" * 60)

    bot = CCXTDecibelBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
    )

    try:
        await bot.initialize()

        # Run 1 cycle
        await bot.run_cycle(hold_time_seconds=10.0)

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_one_cycle())
