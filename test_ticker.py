#!/usr/bin/env python3
import asyncio
from bot_trade.exchanges.decibel import DecibelExchange

async def test():
    ex = DecibelExchange()
    t = await ex.fetch_ticker('BTC')
    print(f"Type: {type(t)}")
    print(f"Dir: {[a for a in dir(t) if not a.startswith('_')]}")
    print(f"last: {t.last if hasattr(t, 'last') else 'N/A'}")
    print(f"mark_price: {t.mark_price if hasattr(t, 'mark_price') else 'N/A'}")

asyncio.run(test())
