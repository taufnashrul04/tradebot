#!/usr/bin/env python3
"""
Check and report pending limit orders on Decibel
Note: Decibel API does NOT support canceling limit orders
"""

import os
import sys
from bot_trade.exchanges.decibel import DecibelExchange

def check_pending_orders():
    """Check for pending limit orders"""
    print("🔍 Checking for pending limit orders...")
    print("=" * 60)

    try:
        exchange = DecibelExchange()

        # Try to fetch open orders (not supported by Decibel API)
        print("⚠️  Decibel API does NOT provide endpoint to list open orders")
        print("   Cannot check for pending limit orders via API")
        print()
        print("📋 To check and cancel pending limit orders:")
        print("   1. Go to https://app.decibel.trade/")
        print("   2. Check 'Open Orders' tab")
        print("   3. Cancel any pending limit orders manually")
        print()
        print("💡 Tip: Limit orders that don't fill will remain open")
        print("   until canceled or filled by the market")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_pending_orders()
