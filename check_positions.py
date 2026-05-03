#!/usr/bin/env python3
"""
Check open positions on Decibel
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange


async def check_positions():
    """Check open positions"""
    print("🔍 Checking open positions on Decibel...")
    print("="*60)

    exchange = DecibelExchange()

    try:
        positions = await exchange.fetch_positions()

        if not positions:
            print("✅ No open positions")
        else:
            print(f"📊 Found {len(positions)} open position(s):")
            print()

            for pos in positions:
                print(f"Symbol: {pos.symbol}")
                print(f"Side: {pos.side}")
                print(f"Size: {pos.size:.6f}")
                print(f"Entry Price: ${pos.entry_price:.2f}")
                print(f"Mark Price: ${pos.mark_price:.2f}")
                print(f"PnL: ${pos.pnl:.4f}")
                print(f"Leverage: {pos.leverage}x")
                print("-"*40)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_positions())
