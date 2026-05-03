#!/usr/bin/env python3
"""
Check and report current status
"""

import os
import sys
from bot_trade.exchanges.decibel import DecibelExchange

def check_status():
    """Check current status"""
    print("🔍 Checking current status...")
    print("=" * 60)

    try:
        exchange = DecibelExchange()

        # Check positions
        print("\n📊 Checking positions...")
        import asyncio

        async def check():
            positions = await exchange.fetch_positions()
            if positions:
                print(f"   Found {len(positions)} open position(s):")
                for pos in positions:
                    print(f"   - {pos.side}: {pos.size:.6f} BTC @ ${pos.entry_price:.2f}")
            else:
                print("   ✅ No open positions")

            # Check ticker
            print("\n💰 Checking ticker...")
            try:
                ticker = await exchange.fetch_ticker('BTC')
                print(f"   BTC Price: ${ticker.last if ticker.last else ticker.mark_price:.2f}")
            except Exception as e:
                print(f"   ⚠️  Failed to fetch ticker: {e}")

        asyncio.run(check())

        print("\n" + "=" * 60)
        print("📋 Manual Actions Required:")
        print("   1. Go to https://app.decibel.trade/")
        print("   2. Check 'Open Orders' tab")
        print("   3. Cancel any pending limit orders")
        print("   4. Check 'Positions' tab")
        print("   5. Close any open positions")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_status()
