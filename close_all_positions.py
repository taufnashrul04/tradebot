#!/usr/bin/env python3
"""
Close all open positions on Decibel
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def close_all_positions():
    """Close all open positions"""
    print("🔍 Checking open positions on Decibel...")
    print("="*60)

    exchange = DecibelExchange()

    try:
        positions = await exchange.fetch_positions()

        if not positions:
            print("✅ No open positions")
            return

        print(f"📊 Found {len(positions)} open position(s):")
        print()

        for pos in positions:
            print(f"Symbol: {pos.symbol}")
            print(f"Side: {pos.side}")
            print(f"Size: {pos.size:.6f}")
            print(f"Entry Price: ${pos.entry_price:.2f}")
            print(f"Mark Price: ${pos.mark_price:.2f}")

            # Calculate PnL manually
            if pos.side == OrderSide.LONG:
                pnl = (pos.mark_price - pos.entry_price) * pos.size
            else:
                pnl = (pos.entry_price - pos.mark_price) * pos.size

            print(f"PnL: ${pnl:.4f}")
            print(f"Leverage: {pos.leverage}x")
            print("-"*40)

            # Close position
            print(f"🔄 Closing position...")
            close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG

            try:
                close_order = await exchange.place_market_order(
                    symbol='BTC',
                    side=close_side,
                    size=pos.size,
                    leverage=pos.leverage,
                    reduce_only=True,
                )
                print(f"✅ Position closed: {close_order.order_id}")
                print(f"   PnL: ${pnl:.4f}")
            except Exception as e:
                print(f"❌ Failed to close: {e}")

        print("\n✅ All positions closed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(close_all_positions())
