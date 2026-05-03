#!/usr/bin/env python3
"""
Scalping Bot - Aggressive TP/SL for quick profits
- TP: 0.15% (quick wins)
- SL: 0.3% (tight stop loss)
- Hold time: 10s (fast cycles)
- Alternating LONG/SHORT for hedging
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimized_bot import OptimizedCCXTDecibelBot

async def test_scalping():
    """Test scalping bot with 5 cycles"""
    print("🧪 Testing Scalping Bot (5 cycles)...")
    print("=" * 60)
    print("📋 Settings:")
    print("   TP: 0.15% (quick wins)")
    print("   SL: 0.3% (tight stop loss)")
    print("   Hold Time: 10s (fast cycles)")
    print("   Check Interval: 1s (frequent monitoring)")
    print("=" * 60)

    bot = OptimizedCCXTDecibelBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
        take_profit_percent=0.15,  # 0.15% TP (quick wins)
        stop_loss_percent=0.3,  # 0.3% SL (tight)
        check_interval_seconds=1.0,  # Check every 1s
    )

    try:
        await bot.run_strategy(
            target_volume_usd=1000.0,  # Target $1k for testing
            hold_time_seconds=10.0,  # 10s hold time (fast)
            max_cycles=5,  # 5 cycles
        )

        print("\n✅ Test complete!")
        print("📋 Check Decibel UI for any pending limit orders:")
        print("   https://app.decibel.trade/")

    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(test_scalping())
