---
name: dex-trading-bot
description: |
  Use this skill when the user wants to trade on DEX perpetual exchanges including Nado, Rise Trade, or Decibel.
  Trigger this skill for requests involving: trading, volume generation, funding rate scanning, delta neutral strategy,
  indicator-based trading (RSI, EMA, MACD), opening/closing positions, checking account status or balances,
  or any cross-exchange arbitrage related to crypto perpetual futures.
  Keywords: nado, decibel, rise trade, funding rate, delta neutral, volume bot, perp trading, perpetual, long, short.
version: "1.0"
author: bot-trade
---

# DEX Trading Bot Skill

You have access to a powerful multi-exchange DEX trading bot that supports **Nado** (Ink chain), **Rise Trade** (Rise Chain), and **Decibel** (Aptos chain).

## Working Directory

All bot commands must be run from:
```
d:\bot\bot trade
```

## Available Commands

### 1. Scan Funding Rates
```powershell
python -m bot_trade funding [OPTIONS]
  --symbols     TEXT    Symbols to scan (default: BTC,ETH,SOL)
  --exchanges   TEXT    Exchanges (default: nado,decibel,rise)
  --min-yield   FLOAT   Min annual yield% to highlight (default: 3.0)
  --watch               Auto-refresh every 60s
```

### 2. Delta-Neutral Strategy
```powershell
python -m bot_trade delta-neutral [OPTIONS]
  --exchanges   TEXT    Two exchanges, e.g. nado,decibel
  --size        FLOAT   USD per leg (default: 100)
  --min-yield   FLOAT   Min annual yield% (default: 5.0)
  --max-hours   FLOAT   Max position duration in hours (default: 24)
  --leverage    INT     Leverage (default: 1)
  --interval    INT     Check interval in seconds (default: 60)
```

### 3. Volume Generation
```powershell
python -m bot_trade volume [OPTIONS]
  --exchange    TEXT    Exchange: nado, decibel, rise
  --symbol      TEXT    Symbol (default: BTC)
  --target      FLOAT   Target volume in USD
  --duration    INT     Duration in seconds
  --slices      INT     Number of order slices (default: 20)
```

### 4. Indicator Trading
```powershell
python -m bot_trade indicator [OPTIONS]
  --exchange    TEXT    Exchange to trade on
  --symbol      TEXT    Symbol (default: BTC)
  --strategy    TEXT    rsi | ema | macd | bb | vwap
  --timeframe   TEXT    1m | 5m | 15m | 1h | 4h | 1d
  --size        FLOAT   Position size in USD
  --rsi-low     FLOAT   RSI oversold level (default: 30)
  --rsi-high    FLOAT   RSI overbought level (default: 70)
  --ema-fast    INT     Fast EMA period (default: 9)
  --ema-slow    INT     Slow EMA period (default: 21)
```

### 5. Account Status
```powershell
python -m bot_trade status [--exchange nado|decibel|rise|all]
```

## Decision Tree for User Requests

```
User wants to...
├── "check funding rates" / "cek funding" / "lihat peluang"
│   → run: python -m bot_trade funding --watch
│
├── "delta neutral" / "arb funding" / "kumpul funding"
│   → scan dulu: python -m bot_trade funding
│   → jika ada opportunity: python -m bot_trade delta-neutral --exchanges [best_pair]
│
├── "generate volume" / "farming points" / "buat volume"
│   → run: python -m bot_trade volume --exchange [exchange] --target [amount]
│
├── "trade pakai indicator" / "RSI" / "EMA cross"
│   → run: python -m bot_trade indicator --strategy [rsi|ema|macd|bb|vwap]
│
└── "cek balance" / "lihat posisi" / "status"
    → run: python -m bot_trade status
```

## Important Notes

1. **Always run `funding` first** before starting `delta-neutral` to verify opportunities exist
2. **Credentials**: Bot requires `.env` file in `d:\bot\bot trade\` with exchange private keys
3. **Risk**: Default max position = $1000 USD, max leverage = 5x (configurable in .env)
4. **Exchanges**:
   - Nado: most mature, Python SDK + CLI available
   - Decibel: requires Aptos wallet with delegated trading rights
   - Rise: requires Rise Chain API key from developer.rise.trade

## Example Interaction Flows

### Flow 1: User asks to start delta-neutral

```
User: "cari funding arb di nado dan decibel untuk BTC"

Agent steps:
1. Run: python -m bot_trade funding --symbols BTC --exchanges nado,decibel
2. Read output: check if annual_yield > 3%
3. If profitable: 
   python -m bot_trade delta-neutral --exchanges nado,decibel --size 100 --min-yield 3.0
4. Monitor output and report position status to user
```

### Flow 2: User asks to generate volume

```
User: "generate 10k volume di nado untuk BTC dalam 1 jam"

Agent steps:
1. Run: python -m bot_trade volume --exchange nado --symbol BTC --target 10000 --duration 3600
2. Report progress every 5 minutes
3. Report final summary when done
```

### Flow 3: User asks to trade with RSI

```
User: "trade BTC pakai RSI di nado, 15 menit timeframe, size $200"

Agent steps:
1. Run: python -m bot_trade indicator \
   --exchange nado --symbol BTC \
   --strategy rsi --timeframe 15m \
   --size 200 --rsi-low 30 --rsi-high 70
2. Monitor and report signals/trades to user
```

## Skill References

- Full guide: `d:\bot\bot trade\GUIDE.md`
- Nado skill: `d:\bot\bot trade\skills\nado-trading.md`
- Decibel skill: `d:\bot\bot trade\skills\decibel-trading.md`
- Rise skill: `d:\bot\bot trade\skills\rise-trading.md`
- Delta neutral deep-dive: `d:\bot\bot trade\skills\delta-neutral.md`
