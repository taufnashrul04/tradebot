#!/usr/bin/env python3
"""
Quick Start Script for CCXT + Decibel Bot
Test with 5 cycles to verify everything works
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ccxt_decibel_bot import CCXTDecibelBot


async def quick_start():
    """Run 5 test cycles"""
    print("🚀 Quick Start - CCXT + Decibel Bot")
    print("="*60)

    bot = CCXTDecibelBot(
        analysis_exchange="binance",
        symbol="BTC/USDT",
        timeframe="1m",
        leverage=40,
        balance_usd=20.0,
        per_position_usd=5.0,
    )

    try:
        await bot.run_strategy(
            target_volume_usd=100000.0,  # Target (won't reach in 5 cycles)
            hold_time_seconds=30.0,
            max_cycles=5,  # Only 5 cycles for testing
        )
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(quick_start())
