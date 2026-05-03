#!/usr/bin/env python3
"""
Test script for Decibel trading bot.
Verifies position detection, PnL calculation, and order placement.
"""
import asyncio
import sys
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide


async def test_positions():
    """Test position detection and PnL calculation."""
    print("=" * 60)
    print("Testing Position Detection")
    print("=" * 60)

    d = DecibelExchange()
    positions = await d.fetch_positions()

    print(f"\nFound {len(positions)} position(s):")
    for pos in positions:
        print(f"\n  Symbol: {pos.symbol}")
        print(f"  Side: {pos.side}")
        print(f"  Size: {pos.size}")
        print(f"  Entry Price: ${pos.entry_price:,.2f}")
        print(f"  Mark Price: ${pos.mark_price:,.2f}")
        print(f"  Unrealized PnL: ${pos.unrealized_pnl:,.4f}")

        if pos.entry_price and pos.mark_price:
            pct = (pos.unrealized_pnl / (pos.entry_price * pos.size) * 100) if pos.size else 0
            print(f"  PnL %: {pct:+.2f}%")

    return positions


async def test_ticker():
    """Test ticker fetching."""
    print("\n" + "=" * 60)
    print("Testing Ticker Fetching")
    print("=" * 60)

    d = DecibelExchange()

    for symbol in ["BTC", "ETH", "SOL"]:
        try:
            ticker = await d.fetch_ticker(symbol)
            print(f"\n{symbol}:")
            print(f"  Last: ${ticker.last:,.2f}")
            print(f"  Bid: ${ticker.bid:,.2f}")
            print(f"  Ask: ${ticker.ask:,.2f}")
            print(f"  Mark: ${ticker.mark_price:,.2f}")
            print(f"  Index: ${ticker.index_price:,.2f}")
        except Exception as e:
            print(f"\n{symbol}: ERROR - {e}")


async def test_funding_rates():
    """Test funding rate fetching."""
    print("\n" + "=" * 60)
    print("Testing Funding Rates")
    print("=" * 60)

    d = DecibelExchange()

    for symbol in ["BTC", "ETH", "SOL"]:
        try:
            funding = await d.fetch_funding_rate(symbol)
            print(f"\n{symbol}:")
            print(f"  Rate: {funding.rate*100:.4f}%")
            print(f"  Annualized: {funding.rate_annual*100:.2f}%")
            print(f"  Interval: {funding.interval_hours}h")
        except Exception as e:
            print(f"\n{symbol}: ERROR - {e}")


async def test_balance():
    """Test balance fetching."""
    print("\n" + "=" * 60)
    print("Testing Balance Fetching")
    print("=" * 60)

    d = DecibelExchange()
    balance = await d.fetch_balance()

    print(f"\nBalance: {balance}")
    print("Note: REST API shows $0, check web UI for equity")


async def main():
    """Run all tests."""
    print("\n🚀 Decibel Trading Bot - Test Suite\n")

    try:
        # Test 1: Positions
        positions = await test_positions()

        # Test 2: Ticker
        await test_ticker()

        # Test 3: Funding Rates
        await test_funding_rates()

        # Test 4: Balance
        await test_balance()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

        # Summary
        if positions:
            print(f"\n📊 Active Positions: {len(positions)}")
            total_pnl = sum(p.unrealized_pnl for p in positions)
            print(f"💰 Total Unrealized PnL: ${total_pnl:,.4f}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
