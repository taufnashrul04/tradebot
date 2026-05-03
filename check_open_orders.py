#!/usr/bin/env python3
"""
Check open orders on Decibel
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange


async def check_open_orders():
    """Check open orders"""
    print("🔍 Checking open orders on Decibel...")
    print("="*60)

    exchange = DecibelExchange()

    try:
        # Decibel might not have fetch_open_orders method
        # Let's check what methods are available
        methods = [m for m in dir(exchange) if not m.startswith('_') and 'order' in m.lower()]
        print(f"Available order methods: {methods}")
        print()

        # Try to fetch positions (which might include pending orders)
        positions = await exchange.fetch_positions()

        if not positions:
            print("✅ No open positions")
        else:
            print(f"📊 Found {len(positions)} position(s):")
            print()

            for pos in positions:
                print(f"Symbol: {pos.symbol}")
                print(f"Side: {pos.side}")
                print(f"Size: {pos.size:.6f}")
                print(f"Entry Price: ${pos.entry_price:.2f}")
                print(f"Mark Price: ${pos.mark_price:.2f}")
                print(f"Leverage: {pos.leverage}x")
                print("-"*40)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_open_orders())
