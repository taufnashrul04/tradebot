#!/usr/bin/env python3
"""
Test script to verify CCXT + Decibel bot setup
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")

    try:
        import ccxt
        print(f"✅ ccxt {ccxt.__version__}")
    except ImportError as e:
        print(f"❌ ccxt: {e}")
        return False

    try:
        import pandas
        print(f"✅ pandas {pandas.__version__}")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        return False

    try:
        import numpy
        print(f"✅ numpy {numpy.__version__}")
    except ImportError as e:
        print(f"❌ numpy: {e}")
        return False

    try:
        import asyncio
        print(f"✅ asyncio")
    except ImportError as e:
        print(f"❌ asyncio: {e}")
        return False

    return True


def test_ccxt_connection():
    """Test CCXT connection to Binance"""
    print("\n🔍 Testing CCXT connection...")

    try:
        import ccxt.async_support as ccxt

        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

        print("✅ CCXT Binance initialized")
        return True

    except Exception as e:
        print(f"❌ CCXT connection failed: {e}")
        return False


def test_decibel_import():
    """Test Decibel import"""
    print("\n🔍 Testing Decibel import...")

    try:
        from bot_trade.exchanges.decibel import DecibelExchange
        print("✅ DecibelExchange imported")
        return True

    except ImportError as e:
        print(f"❌ Decibel import failed: {e}")
        return False


def test_bot_import():
    """Test bot import"""
    print("\n🔍 Testing bot import...")

    try:
        from ccxt_decibel_bot import CCXTDecibelBot
        print("✅ CCXTDecibelBot imported")
        return True

    except ImportError as e:
        print(f"❌ Bot import failed: {e}")
        return False


def test_env_vars():
    """Test environment variables"""
    print("\n🔍 Testing environment variables...")

    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        'DECIBEL_PRIVATE_KEY',
        'DECIBEL_SUBACCOUNT_ADDR',
        'DECIBEL_GEOMI_KEY',
    ]

    all_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * 10}...{value[-4:]}")
        else:
            print(f"❌ {var}: NOT SET")
            all_ok = False

    return all_ok


async def test_market_data_fetch():
    """Test fetching market data from CCXT"""
    print("\n🔍 Testing market data fetch...")

    try:
        import ccxt.async_support as ccxt

        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

        # Fetch BTC/USDT OHLCV
        ohlcv = await exchange.fetch_ohlcv('BTC/USDT', '1m', limit=10)

        if ohlcv and len(ohlcv) > 0:
            latest = ohlcv[-1]
            print(f"✅ Fetched {len(ohlcv)} candles")
            print(f"   Latest: ${latest[4]:.2f} (close)")
            return True
        else:
            print("❌ No data fetched")
            return False

    except Exception as e:
        print(f"❌ Market data fetch failed: {e}")
        return False
    finally:
        await exchange.close()


async def main():
    """Run all tests"""
    print("="*60)
    print("🧪 CCXT + Decibel Bot Setup Test")
    print("="*60)

    results = []

    # Test 1: Imports
    results.append(("Imports", test_imports()))

    # Test 2: CCXT connection
    results.append(("CCXT Connection", test_ccxt_connection()))

    # Test 3: Decibel import
    results.append(("Decibel Import", test_decibel_import()))

    # Test 4: Bot import
    results.append(("Bot Import", test_bot_import()))

    # Test 5: Environment variables
    results.append(("Environment Variables", test_env_vars()))

    # Test 6: Market data fetch
    results.append(("Market Data Fetch", await test_market_data_fetch()))

    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Bot is ready to use.")
        print("\nNext steps:")
        print("1. Run quick start: /home/ubuntu/tradebot/.venv/bin/python quick_start_ccxt.py")
        print("2. Or run full strategy: /home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
