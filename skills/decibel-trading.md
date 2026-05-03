---
name: decibel-trading
description: |
  Skill for interacting with Decibel DEX perpetual exchange on Aptos blockchain.
  Use when user wants to: trade on Decibel, check Decibel funding, generate volume on Decibel,
  or use Decibel in cross-exchange delta-neutral strategies.
  IMPORTANT: Decibel REST API is READ-ONLY. All trading is done via on-chain Aptos transactions.
  Requires Aptos wallet with USDC collateral and delegated trading rights.
---

# Decibel Protocol Trading Skill

Decibel is a high-speed on-chain perpetual DEX on Aptos blockchain.

## Key Architecture

```
Decibel REST API → READ ONLY (market data, positions, balances)
Aptos On-chain   → WRITE (all trading: orders, open, close)

Bot uses: aptos-sdk to sign and submit Move transactions
```

## Available Markets (approximate)

| Symbol | Type | Collateral |
|--------|------|-----------|
| BTC | Perpetual | USDC |
| ETH | Perpetual | USDC |
| APT | Perpetual | USDC |
| SOL | Perpetual | USDC |

## Funding Rate Info

- Funding interval: **8 hours** (may vary, check API)
- REST endpoint: `GET /markets` → includes `fundingRate` per market
- Annualization: `rate * (8760 / interval_hours)`

## Delegation Model (Security)

Decibel uses a delegation system for bot trading:
```
Your Main Wallet (holds funds)
    │
    ▼ delegate trading rights
Bot Wallet (from .env DECIBEL_PRIVATE_KEY)
    │
    ▼ can place/close orders
    ✓ CANNOT: withdraw, transfer, change ownership
```

## Bot Commands for Decibel

```bash
# Working dir: d:\bot\bot trade

# Scan Decibel funding
python -m bot_trade funding --exchanges decibel --symbols BTC,ETH

# Volume generation on Decibel (uses on-chain TWAP)
python -m bot_trade volume --exchange decibel --symbol BTC --target 5000 --duration 3600

# Indicator trading on Decibel
python -m bot_trade indicator --exchange decibel --strategy rsi --timeframe 15m

# Account status
python -m bot_trade status --exchange decibel
```

## Prerequisites Before Trading

1. Aptos wallet with APT for gas fees
2. USDC deposited to Decibel subaccount
3. Bot wallet delegated trading rights via Decibel UI
4. `.env` has `DECIBEL_PRIVATE_KEY` and `DECIBEL_SUBACCOUNT_ADDR`

## API Endpoints (Reference)

```
Base URL: https://api.mainnet.aptoslabs.com/decibel/api/v1

GET /markets              → all markets with funding rates
GET /prices               → current mark/index prices
GET /subaccounts?owner=    → list subaccounts for a wallet
GET /account_positions?account=  → user's open positions
GET /candles              → OHLCV data
```

## Important Limitations

- Cannot cancel orders via bot (limitation of on-chain model)
- Each trade = on-chain Aptos transaction (costs APT gas)
- On-chain transactions take ~0.5-2s to confirm
- Slippage is higher than CEX due to on-chain oracle pricing
- Balance shows $0 via REST but web shows equity → on-chain confirms 0 USDC, equity = realized PnL

## Trading Implementation

**place_market_order** uses reference bot's `place_order_tx` from `/tmp/decibel_ref/DECIBEL/bot.py` directly (bypassing broken local SDK serialization).

Market config: px_decimals=6, sz_decimals=8, tick_size=100000, lot_size=1000
- Size: multiply by 10^8, must be divisible by lot_size=1000
- Price: multiply by 10^6, must be divisible by tick_size=100000

## Error Handling

If Decibel trade fails, bot will:
1. Log the error with transaction details
2. Attempt to close any orphaned positions on other exchanges
3. Alert user to check Decibel UI manually
