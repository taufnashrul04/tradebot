# Decibel Trading Bot - Implementation Summary

## Current Status

✅ **Working Features:**
- Market data fetching (ticker, orderbook, funding rates)
- Position detection (now working via reference bot's `fetch_open_positions`)
- Market order placement (via reference bot's `place_order_tx`)
- PnL calculation with live mark price

✅ **Detected Position:**
- BTC LONG 0.0006
- Entry: $76,943.98
- Mark: $76,639.8
- Unrealized PnL: -$0.18

## Key Implementation Details

### 1. Position Detection

**Problem:** REST API `/account_positions` was returning empty array.

**Solution:** Use reference bot's `fetch_open_positions` from `/home/ubuntu/DECIBEL/bot.py`.

```python
import sys
sys.path.insert(0, '/home/ubuntu/DECIBEL')
from bot import fetch_open_positions

positions_data = fetch_open_positions(self.cfg.subaccount_addr)
```

### 2. Market Order Placement

**Problem:** Local `_submit_transaction` was failing with `80` deserialization error.

**Solution:** Use reference bot's `place_order_tx` directly.

```python
from bot import place_order_tx

tx_hash = await place_order_tx(
    client,
    self._account,
    self.cfg.subaccount_addr,
    market_addr,
    price_chain=price_scaled,
    size_chain=size_scaled,
    is_buy=is_long,
    is_reduce_only=reduce_only,
)
```

### 3. Market Config

**BTC Market:**
- Address: `0x5e0e16f34adfb4b316f8d532d68acbfa206826feaaa418d3938046bdc2044861`
- Price decimals: 6 (multiply by 10^6)
- Size decimals: 8 (multiply by 10^8)
- Tick size: 100,000
- Lot size: 1,000
- Min size: 2,000

### 4. Price/Size Alignment

```python
# Price: round to tick size
raw_price = float(ticker.last) * 1_000_000  # px_decimals=6
price_scaled = round(raw_price / 100_000) * 100_000  # tick_size=100000

# Size: round to lot size
size_scaled = int(size * 100_000_000)  # sz_decimals=8
```

## Reference Implementations

### 1. DECIBEL.zip (Reference Bot)

**Location:** `/home/ubuntu/DECIBEL/bot.py`

**Key Functions:**
- `fetch_open_positions(subaccount_addr)` - Get positions
- `place_order_tx(...)` - Place orders
- `fetch_current_price(market_addr)` - Get price
- `fetch_markets()` - Get market list

**API Endpoints:**
- `GET /markets` - Market list
- `GET /prices?market={addr}` - Current price
- `GET /subaccounts?owner={wallet}` - Subaccount list
- `GET /account_positions?account={subaccount}` - Positions

### 2. SeamMoney/decibrrr

**Location:** `/home/ubuntu/decibrrr/`

**Key Files:**
- `grid-mm-bot.ts` - Grid market maker bot
- `lib/decibel-client.ts` - Decibel client library
- `lib/decibel-sdk.ts` - SDK wrapper

**Features:**
- Grid market making strategy
- Symmetric bid/ask orders
- Auto-cancel and replace cycle
- PnL tracking

## Swift Router API Key Rotation

**Purpose:** Auto-rotate API keys when hitting rate limits.

**Implementation:** `/home/ubuntu/tradebot/bot_trade/utils/swiftrouter.py`

**Usage:**
```python
from bot_trade.utils.swiftrouter import get_swift_router_client

client = get_swift_router_client()
response = client.request("POST", "/chat/completions", json={...})
```

**Configuration:** `/home/ubuntu/tradebot/.env.swiftrouter`
```
SWIFT_ROUTER_KEYS=sk-xxx,sk-yyy,sk-zzz
```

**Features:**
- Automatic key rotation on 429 errors
- Error tracking and cooldown
- Status monitoring

## Account Details

**Wallet:** `0x7b4486ecc8f7133b08f6c13265d66e0f549726fb2fd672f4e7396ed5106a7771`
**Subaccount:** `0x4c0f9df4811861a3841a6162411ade52ee78f0e1ae06c0a2e148952d21f60be9`

**Contract:** `0x50ead22afd6ffd9769e3b3d6e0e64a2a350d68e8b102c4e72e33d0b8cfdfdb06`
**Module:** `dex_accounts_entry`

## Known Limitations

1. **REST API Unreliable:** `/account_positions` often returns empty, use reference bot's implementation
2. **No Cancel Orders:** Decibel doesn't support order cancellation via REST
3. **On-chain Only:** All trading requires Aptos transactions (gas fees)
4. **Balance Detection:** REST shows $0, must check on-chain or web UI

## Next Steps

1. ✅ Position detection working
2. ✅ PnL calculation working
3. ⏳ Implement auto-close on PnL threshold
4. ⏳ Implement funding rate arbitrage
5. ⏳ Add more markets (ETH, SOL, etc.)
6. ⏳ Implement grid market making strategy

## Testing Commands

```bash
# Check positions
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python -c "
import asyncio
from bot_trade.exchanges.decibel import DecibelExchange

async def check():
    d = DecibelExchange()
    pos = await d.fetch_positions()
    print('Positions:', len(pos))
    for p in pos:
        print(f'  {p.symbol} {p.side} size={p.size} entry={p.entry_price} mark={p.mark_price} pnl={p.unrealized_pnl}')

asyncio.run(check())
"

# Place market order
/home/ubuntu/tradebot/.venv/bin/python -c "
import asyncio
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide

async def trade():
    d = DecibelExchange()
    order = await d.place_market_order('BTC', OrderSide.LONG, 0.0001)
    print('Order:', order)

asyncio.run(trade())
"
```
