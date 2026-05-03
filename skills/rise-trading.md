---
name: rise-trading  
description: |
  Skill for interacting with Rise Trade perpetual DEX on Rise Chain (EVM L2).
  Use when user wants to: trade on Rise, check Rise funding rates, generate volume on Rise,
  or combine Rise with Nado/Decibel in cross-exchange strategies.
  NOTE: Rise API docs require login at developer.rise.trade — update RISE_API_KEY in .env first.
---

# Rise Trade Skill

Rise Trade is a perpetual DEX on Rise Chain, an EVM-compatible high-speed L2.

## Key Facts

- **Chain**: Rise Chain (EVM-compatible L2)
- **Native gas token**: ETH
- **Collateral**: USDC (likely)
- **API**: REST at developer.rise.trade (requires API key)

## Bot Commands for Rise

```bash
# Working dir: d:\bot\bot trade

# Scan Rise funding
python -m bot_trade funding --exchanges rise --symbols BTC,ETH

# Volume generation on Rise
python -m bot_trade volume \
  --exchange rise \
  --symbol BTC \
  --target 5000 \
  --duration 3600

# Indicator trading on Rise
python -m bot_trade indicator \
  --exchange rise \
  --strategy rsi \
  --timeframe 15m \
  --size 100

# Account status
python -m bot_trade status --exchange rise
```

## Setup Requirements

1. Register at https://developer.rise.trade
2. Get API key
3. Prepare EVM wallet private key
4. Set in `.env`:
   ```env
   RISE_PRIVATE_KEY=0x...
   RISE_API_KEY=your_api_key
   RISE_RPC_URL=https://mainnet.riselabs.xyz
   ```

## Note on TWAP

Rise Trade may not have native TWAP orders. The bot simulates TWAP by:
- Splitting total order into N slices
- Executing each slice as a market order
- Randomizing timing ±20% to avoid pattern detection

```bash
# Rise uses simulated TWAP (--no-twap flag not needed, auto-detected)
python -m bot_trade volume --exchange rise --target 5000 --slices 20
```

## Delta Neutral with Rise

Rise can be paired with Nado or Decibel for cross-exchange funding arb:

```bash
# Scan Rise vs Nado opportunities
python -m bot_trade funding --exchanges rise,nado

# Run delta neutral if opportunity found
python -m bot_trade delta-neutral --exchanges rise,nado --size 200 --min-yield 4.0
```

## Current Status

Rise Trade API is partially documented. The bot implements:
- Multiple endpoint fallback patterns for auto-discovery
- Graceful degradation if API endpoint changes
- Read from `.env` for API key authentication

If you encounter connection errors:
1. Verify `RISE_API_KEY` is set
2. Check API docs at developer.rise.trade for current endpoints
3. Bot will report exact error in terminal output
