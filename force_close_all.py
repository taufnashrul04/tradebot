#!/usr/bin/env python3
"""
Force close all positions and cancel any pending orders
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def force_close_all():
    """Force close all positions"""
    print("🔍 Checking and force closing all positions...")
    print("="*60)

    exchange = DecibelExchange()

    try:
        # Check positions multiple times
        for attempt in range(3):
            print(f"\nAttempt {attempt + 1}/3:")

            positions = await exchange.fetch_positions()

            if not positions:
                print("✅ No open positions")
                break

            print(f"📊 Found {len(positions)} open position(s)")

            for pos in positions:
                print(f"   {pos.side} {pos.size:.6f} BTC @ ${pos.entry_price:.2f}")

                # Close position
                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG

                try:
                    close_order = await exchange.place_market_order(
                        symbol='BTC',
                        side=close_side,
                        size=pos.size,
                        leverage=pos.leverage,
                        reduce_only=True,
                    )
                    print(f"   ✅ Closed: {close_order.order_id}")

                except Exception as e:
                    print(f"   ❌ Failed to close: {e}")

            # Wait before next attempt
            if attempt < 2:
                await asyncio.sleep(2)

        print("\n✅ Force close complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(force_close_all())
