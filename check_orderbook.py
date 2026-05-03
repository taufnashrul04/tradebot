#!/usr/bin/env python3
"""
Check orderbook for pending limit orders
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange


async def check_orderbook():
    """Check orderbook"""
    print("🔍 Checking orderbook on Decibel...")
    print("="*60)

    exchange = DecibelExchange()

    try:
        orderbook = await exchange.fetch_orderbook('BTC')

        print(f"📊 Orderbook for BTC:")
        print()

        # Asks (sell orders)
        if orderbook.get('asks'):
            print(f"🔴 Asks (Sell Orders) - Top 5:")
            for i, ask in enumerate(orderbook['asks'][:5]):
                price, size = ask
                print(f"   {i+1}. ${price:.2f} - {size:.6f} BTC")
        else:
            print("🔴 No asks")

        print()

        # Bids (buy orders)
        if orderbook.get('bids'):
            print(f"🟢 Bids (Buy Orders) - Top 5:")
            for i, bid in enumerate(orderbook['bids'][:5]):
                price, size = bid
                print(f"   {i+1}. ${price:.2f} - {size:.6f} BTC")
        else:
            print("🟢 No bids")

        print()
        print(f"Spread: ${orderbook.get('spread', 0):.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_orderbook())
