#!/usr/bin/env python3
"""
Check Decibel API directly for any open orders or positions
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

GEOMI_KEY = os.getenv('DECIBEL_GEOMI_KEY')
SUBACCOUNT = os.getenv('DECIBEL_SUBACCOUNT_ADDR')
BASE_URL = "https://api.mainnet.aptoslabs.com/decibel/api/v1"


async def check_decibel_api():
    """Check Decibel API directly"""
    print("🔍 Checking Decibel API directly...")
    print("="*60)

    headers = {
        'Authorization': f'Bearer {GEOMI_KEY}'
    }

    async with aiohttp.ClientSession() as session:
        # Check positions
        print("\n📊 Checking positions...")
        try:
            url = f"{BASE_URL}/account_positions?account={SUBACCOUNT}"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Status: {resp.status}")
                    print(f"   Positions: {len(data) if data else 0}")

                    if data:
                        for pos in data:
                            print(f"   - {pos}")
                    else:
                        print("   ✅ No positions")
                else:
                    text = await resp.text()
                    print(f"   ❌ Error {resp.status}: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Check subaccount
        print("\n📊 Checking subaccount...")
        try:
            # Need wallet address, not subaccount
            # Let's try without owner parameter first
            url = f"{BASE_URL}/subaccounts"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Status: {resp.status}")
                    print(f"   Subaccounts: {len(data) if data else 0}")

                    if data:
                        for sub in data:
                            print(f"   - {sub}")
                else:
                    text = await resp.text()
                    print(f"   ❌ Error {resp.status}: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Check markets
        print("\n📊 Checking markets...")
        try:
            url = f"{BASE_URL}/markets"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Status: {resp.status}")
                    print(f"   Markets: {len(data) if data else 0}")

                    btc_market = [m for m in data if 'BTC' in m.get('market_name', '')]
                    if btc_market:
                        print(f"   BTC Market: {btc_market[0].get('market_name')}")
                        print(f"   Mark Price: ${btc_market[0].get('mark_price', 0):.2f}")
                else:
                    text = await resp.text()
                    print(f"   ❌ Error {resp.status}: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    print("\n✅ API check complete!")


if __name__ == "__main__":
    asyncio.run(check_decibel_api())
