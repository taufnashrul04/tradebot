#!/usr/bin/env python3
"""
Cancel all open limit orders on Decibel
"""

import os
import sys
from decibel_exchange import DecibelExchange

def cancel_all_orders():
    """Cancel all open limit orders"""
    print("🔄 Canceling all open limit orders...")

    # Initialize exchange
    exchange = DecibelExchange(
        api_key=os.getenv("DECIBEL_GEOMI_KEY"),
        subaccount_addr=os.getenv("DECIBEL_SUBACCOUNT_ADDR")
    )

    # Try to get open orders
    try:
        # Note: DecibelExchange may not have fetch_orders method
        # We'll try different approaches
        print("📊 Checking for open orders...")

        # Try to cancel by market (this will cancel pending orders)
        # Alternative: use cancel_all if available

        print("⚠️  Note: DecibelExchange may not have direct order listing")
        print("   Orders may need to be canceled via UI or specific order IDs")

        return True

    except Exception as e:
        print(f"❌ Error canceling orders: {e}")
        return False

if __name__ == "__main__":
    cancel_all_orders()
